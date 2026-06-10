from inspect_evals.gaia import gaia
from inspect_evals.gaia.gaia import DEFAULT_MESSAGE_LIMIT
from inspect_ai.tool import bash, python, web_browser
from inspect_ai.solver._chain import chain
from inspect_ai.solver._prompt import system_message
from pipeline.agent import instrumented_agent
from pipeline.registry import TechniqueRegistry
from pipeline.agent import instrumented_agent

SYSTEM_PROMPT = """You are a helpful assistant completing GAIA benchmark tasks.
Use available tools to find information and complete tasks accurately."""

GAIA_INSTRUCTIONS = """
                You are an autonomous AI agent, consisting of a large language model and a scaffolding program that runs on a linux VM.

                You have full control over your VM through the scaffolding program's provided functions, including: writing and editing files, running bash commands, installing packages etc.. From your VM, you can access the internet.

                You are state-of-the-art, and excellent at analysis, planning and programming. You possess encyclopedic knowledge of the world. You write in a very direct and concise style.

                You are resourceful and adaptive, and you never give up. Before deciding something can't be done, you try it out. You consider multiple options and choose the best one. If your current approach doesn't work, you formulate a new plan. You are given a task you need to solve completely on your own.

                Please think step by step before calling tools. When you are ready to answer, use the submit tool to provide your final answer.
                """

def build_gaia_task(registry, split="validation", max_attempts=1):
    solver = instrumented_agent(
        registry=registry,
        init=[system_message(GAIA_INSTRUCTIONS)],
        tools=[bash(180), python(180)] + web_browser(),  # ← те же что в default_solver
        max_attempts=max_attempts,
    )
    return gaia(solver=solver, split=split)