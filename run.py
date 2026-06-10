from inspect_ai import eval
from pipeline.registry import TechniqueRegistry
from pipeline.breakpoints import BP
from techniques.logging_probe import LoggingProbe
from task import build_gaia_task

registry = (
    TechniqueRegistry()
    .register(LoggingProbe(verbose=True))  # на всех BP
)

task = build_gaia_task(
    registry=registry,
    split="validation",
    # max_turns=10,
)

# Запуск с Ollama
eval(task, model="ollama/qwen3.5:9b", limit=5)  # limit=5 для первого теста