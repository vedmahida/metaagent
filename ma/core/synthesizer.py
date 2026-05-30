"""
SYNTHESIZER — Stage 3 of the MetaAgent pipeline.

Takes the approved SystemArchitecture and generates two artifacts:
  1. A complete, runnable LangGraph Python file for the agent system
  2. A README.md explaining the generated system

The Synthesizer is given the architecture as a strict blueprint.
It translates design → working code. It uses Black to auto-format output.

Key constraint: it generates REAL LangGraph code patterns, not pseudocode.
Every import, every StateGraph, every node function is syntactically correct.
"""
import black
from ma.core.state import MetaAgentState, SystemArchitecture
from ma.llm.groq_client import complete
from ma.utils.logger import get_logger

logger = get_logger(__name__)

SYNTHESIZER_SYSTEM = """
You are SYNTHESIZER — an expert Python engineer specializing in LangGraph 
multi-agent systems. You write COMPLETE, RUNNABLE Python code.

CODE STANDARDS:
- Python 3.11+, type hints everywhere
- LangGraph StateGraph with TypedDict state
- Each agent is a function node: def run_<agent_name>(state: State) -> dict
- Groq as the LLM backend (langchain_groq.ChatGroq)
- All tools as stub functions with clear docstrings explaining what to implement
- Main entry point: if __name__ == "__main__": with example usage
- Rich for terminal output in the generated system
- python-dotenv for GROQ_API_KEY loading
- Pydantic models for all structured data

IMPORTS REQUIRED AT TOP:
```python
import os
from typing import TypedDict, Annotated
import operator
from dotenv import load_dotenv
from groq import Groq
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from rich.console import Console
from rich.panel import Panel
```

NEVER use placeholder comments like "# implement this" without a stub function.
ALWAYS write the full state schema, all node functions, and the graph construction.
The code must be immediately executable after filling in tool stubs.
"""

README_SYSTEM = """
You are a technical writer creating documentation for a generated multi-agent system.
Write a README.md that covers: what the system does, the agent architecture, 
how to install and run it, what each agent does, and how to customize the tool stubs.
Be concise but complete. Use markdown headers and code blocks.
"""


def _format_with_black(code: str) -> str:
    """Auto-format generated code with Black. Returns original if formatting fails."""
    try:
        return black.format_str(code, mode=black.Mode(target_versions={black.TargetVersion.PY311}))
    except Exception:
        return code   # return unformatted rather than crashing


def run_synthesizer(state: MetaAgentState) -> dict:
    """
    LangGraph node: generates the full Python agent system + README.
    """
    architecture: SystemArchitecture = state["architecture"]
    critique = state.get("critique")

    # Build agent descriptions for the code prompt
    agent_descriptions = "\n".join(
        f"  - {a.name}: {a.role} | tools={a.tools} | handoffs={a.handoff_to}"
        for a in architecture.agents
    )

    warnings_block = ""
    if critique and critique.warnings if hasattr(critique, "warnings") else False:
        warnings_block = f"\nIMPORTANT WARNINGS FROM CRITIC:\n" + "\n".join(
            f"  - {w}" for w in critique.weaknesses
        )

    code_prompt = f"""
Generate a COMPLETE LangGraph Python implementation for this system:

SYSTEM NAME: {architecture.system_name}
OBJECTIVE: {architecture.objective}
TOPOLOGY: {architecture.topology}
ENTRY POINT: {architecture.entry_point}

AGENTS:
{agent_descriptions}

DATA FLOW: {architecture.data_flow_summary}
{warnings_block}

Requirements:
1. Full TypedDict state with all fields agents need
2. Every agent as a proper node function
3. StateGraph with all edges and conditional routing
4. Tool stubs as actual callable functions with type hints
5. compile() + stream() example in __main__
6. Rich console output showing agent activations
7. .env loading for GROQ_API_KEY

Write the COMPLETE Python file. No truncation. No "..." shortcuts.
"""

    raw_code = complete(
        system=SYNTHESIZER_SYSTEM,
        user=code_prompt,
        temperature=0.15,
        max_tokens=8000,
    )

    # Strip markdown code fences if model wrapped it
    if raw_code.startswith("```"):
        lines = raw_code.split("\n")
        raw_code = "\n".join(
            line for line in lines
            if not line.startswith("```")
        )

    formatted_code = _format_with_black(raw_code)

    # Generate README separately
    readme_prompt = f"""
Write a README.md for this generated multi-agent system:

System: {architecture.system_name}
Objective: {architecture.objective}
Agents: {[a.name for a in architecture.agents]}
Topology: {architecture.topology}

Include: overview, architecture diagram (text-based), setup instructions,
agent descriptions, tool stub implementation guide, and example usage.
"""

    readme = complete(
        system=README_SYSTEM,
        user=readme_prompt,
        temperature=0.3,
        max_tokens=2000,
    )

    return {
        "generated_code": formatted_code,
        "generated_readme": readme,
        "events": [
            f"SYNTHESIZER · Generated {len(formatted_code.splitlines())} lines of LangGraph Python"
        ],
    }



