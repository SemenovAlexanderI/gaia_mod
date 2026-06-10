import asyncio
from collections import defaultdict
from .breakpoints import BP, BPContext
from .technique import Technique
from inspect_ai.solver import TaskState

class TechniqueRegistry:
    """
    Оркестратор техник по breakpoints.
    
    Поддерживает:
    - Последовательное применение (sequential)
    - Параллельное применение (parallel) с агрегацией
    - Условное применение (через Technique.should_apply)
    """

    def __init__(self):
        # bp → [(technique, mode)]
        # mode: "sequential" | "parallel"
        self._registry: dict[BP, list[tuple[Technique, str]]] = defaultdict(list)

    def register(
        self,
        technique: Technique,
        bps: list[BP] | None = None,
        mode: str = "sequential"
    ) -> "TechniqueRegistry":
        """
        Fluent API:
            registry
                .register(RollbackTechnique(), bps=[BP.AFTER_TOOL_CALL])
                .register(LoggingProbe())
        """
        targets = bps if bps is not None else technique.supported_bps
        for bp in targets:
            self._registry[bp].append((technique, mode))
        return self

    async def trigger(self, bp: BP, state: TaskState) -> TaskState:
        """
        Срабатывает на конкретном breakpoint.
        Техники с mode="sequential" применяются одна за другой.
        Техники с mode="parallel" применяются все одновременно,
        затем агрегируются (дефолт: берём первый результат).
        """
        ctx = BPContext(bp=bp, state=state)

        # Группируем: сначала sequential, потом parallel-батчи
        sequential = [(t, m) for t, m in self._registry[bp] if m == "sequential"]
        parallel   = [(t, m) for t, m in self._registry[bp] if m == "parallel"]

        # Sequential pass
        for technique, _ in sequential:
            if await technique.should_apply(ctx):
                ctx = await technique.apply(ctx)

        # Parallel pass (если есть)
        if parallel:
            techniques = [t for t, _ in parallel]
            tasks = [
                t.apply(BPContext(bp=bp, state=ctx.state))
                for t in techniques
                if await t.should_apply(ctx)
            ]
            if tasks:
                results: list[BPContext] = await asyncio.gather(*tasks)
                # Дефолтная агрегация — можно переопределить
                ctx = self._aggregate(ctx, results)

        return ctx.state

    def _aggregate(self, original: BPContext, results: list[BPContext]) -> BPContext:
        """
        Дефолтная агрегация параллельных результатов.
        Здесь можно реализовать voting, best-of-n и т.д.
        Сейчас: берём первый результат.
        """
        return results[0] if results else original

    def has_techniques(self, bp: BP) -> bool:
        return bool(self._registry[bp])