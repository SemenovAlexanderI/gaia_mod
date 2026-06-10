from pipeline.technique import Technique
from pipeline.breakpoints import BP, BPContext
import logging

logger = logging.getLogger(__name__)

class LoggingProbe(Technique):
    """
    Просто логирует state на каждом BP.
    Smoke test — убедиться что registry работает.
    """
    supported_bps = [BP.BEFORE_GENERATE, BP.AFTER_TOOL_CALL,
                     BP.AFTER_TOOL_RESULT, BP.AFTER_FINAL_ANSWER]

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    async def apply(self, ctx: BPContext) -> BPContext:
        n_messages = len(ctx.state.messages)
        last_role = ctx.state.messages[-1].role if ctx.state.messages else "none"
        logger.info(f"[BP={ctx.bp.name}] messages={n_messages}, last_role={last_role}")
        if self.verbose:
            logger.debug(f"  last message: {ctx.state.messages[-1]}")
        return ctx  # pass-through, state не меняем