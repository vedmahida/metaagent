"""
BRAIN — The master LangGraph orchestration graph.

This is MetaAgent's central nervous system. It wires all pipeline stages
into a stateful directed graph with conditional routing:

[START] --> ARCHITECT --> CRITIC --> SYNTHESIZER --> VALIDATOR --> WRITER --> [END]

The critique-revise loop implements the system's self-correction capability.
Maximum 2 iterations prevents runaway loops while allowing meaningful revision.
"""
import os
import json
from pathlib import Path
from datetime import datetime
from langgraph.graph import StateGraph, END
from ma.core.state import MetaAgentState
from ma.core.architect import run_architect
from ma.core.critic import run_critic, run_architect_revision, should_revise
from ma.core.synthesizer import run_synthesizer
from ma.core.validator import run_validator
from ma.utils.logger import get_logger

logger = get_logger(__name__)


def run_writer(state: MetaAgentState) -> dict:
    """
    Final node: writes all generated artifacts to disk.

    Outputs:
      output/<system_name>/
        ├── agent_system.py    — the generated LangGraph code
        ├── README.md          — documentation
        ├── architecture.json  — the full design blueprint
        └── metaagent_run.log  — pipeline event log
    """
    architecture = state["architecture"]
    output_base = Path(state.get("output_dir", "./output"))

    # Sanitize system name for filesystem
    safe_name = architecture.system_name.lower().replace(" ", "_").replace("-", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = output_base / f"{safe_name}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write generated agent system code
    code_path = output_dir / "agent_system.py"
    code_path.write_text(state["generated_code"])

    # Write README
    readme_path = output_dir / "README.md"
    readme_path.write_text(
        state.get("generated_readme", "# Generated Agent System"))

    # Write architecture blueprint as JSON
    arch_path = output_dir / "architecture.json"
    arch_path.write_text(architecture.model_dump_json(indent=2))

    # Write pipeline event log
    log_path = output_dir / "metaagent_run.log"
    events = state.get("events", [])
    errors = state.get("errors", [])
    log_content = "=== MetaAgent Pipeline Run Log ===\n\n"
    log_content += "\n".join(f"[EVENT] {e}" for e in events)
    if errors:
        log_content += "\n\n=== ERRORS ===\n"
        log_content += "\n".join(f"[ERROR] {e}" for e in errors)
    log_path.write_text(log_content)

    return {
        "final_output_path": str(output_dir),
        "events": [f"WRITER · Artifacts saved to {output_dir}"],
    }


def build_graph() -> StateGraph:
    """
    Constructs and compiles the MetaAgent LangGraph pipeline.
    Returns a compiled graph ready for .stream() or .invoke().
    """
    graph = StateGraph(MetaAgentState)

    ##### Register all nodes #####
    graph.add_node("architect",          run_architect)
    graph.add_node("critic",             run_critic)
    graph.add_node("architect_revision", run_architect_revision)
    graph.add_node("synthesizer",        run_synthesizer)
    graph.add_node("validator",          run_validator)
    graph.add_node("writer",             run_writer)

    ##### Wire edges #####
    graph.set_entry_point("architect")
    graph.add_edge("architect", "critic")

    ##### Conditional: critique result determines whether to revise or synthesize #####
    graph.add_conditional_edges(
        "critic",
        should_revise,
        {
            "revise":    "architect_revision",
            "synthesize": "synthesizer",
        }
    )

    # loop back for re-critique
    graph.add_edge("architect_revision", "critic")
    graph.add_edge("synthesizer",        "validator")
    graph.add_edge("validator",          "writer")
    graph.add_edge("writer",             END)

    return graph.compile()


# Module-level compiled graph — built once, reused across CLI calls
_compiled_graph = None


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
