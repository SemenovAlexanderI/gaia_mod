from abc import ABC, abstractmethod
from .breakpoints import BP, BPContext

class Technique(ABC):
    """
    Базовый класс для любой техники.
    
    Техника — это функция (BPContext → BPContext).
    Может модифицировать state, добавлять мета-информацию,
    или сигнализировать о необходимости rollback/retry через meta.
    """
    # Декларативно указываем, на каких BP техника может работать.
    # Registry использует это как дефолт, если явно не указаны bp при регистрации.
    supported_bps: list[BP] = []

    @abstractmethod
    async def apply(self, ctx: BPContext) -> BPContext:
        ...

    async def should_apply(self, ctx: BPContext) -> bool:
        """Гард — позволяет технике отказаться от применения."""
        return True

    def __repr__(self):
        return f"{self.__class__.__name__}(bps={self.supported_bps})"