"""
ARCHITECT — Stage 1 of the MetaAgent pipeline.

The Architect receives a plain-English job description and produces
a complete SystemArchitecture: every agent, its tools, its inputs/outputs,
its failure modes, and how agents hand off work to each other.
"""
from ma.core.state import MetaAgentState, SystemArchitecture
from ma.llm.groq_client import complete_json
from ma.utils.logger import get_logger

logger = get_logger(__name__)

ARCHITECT_SYSTEM = """
You are ARCHITECT — an elite AI systems designer with deep expertise in 
multi-agent LangGraph systems. You design minimal, production-grade agent 
architectures that separate concerns ruthlessly.

DESIGN PRINCIPLES:
1. Single Responsibility: each agent does exactly ONE thing
2. Minimal agents: never add an agent if one agent can do the job cleanly
3. Explicit handoffs: every agent knows exactly who receives its output
4. Failure mode awareness: anticipate what breaks and design around it
5. Tool specificity: name real, implementable tools (web_search, sql_query, send_email, etc.)

TOPOLOGY SELECTION:
- "pipeline": linear A→B→C. Use for sequential workflows.
- "hierarchical": orchestrator dispatches to specialists. Use for parallel workloads.
- "collaborative": agents message each other peer-to-peer. Use only for negotiation/consensus tasks.

AGENT NAMING: Use PascalCase + "Agent" suffix. e.g. PriceMonitorAgent, AlertDispatchAgent.

Always include:
- An Orchestrator/Planner agent for hierarchical systems
- An output/delivery agent (the one that produces the final artifact)
- Error handling specification in failure_modes
"""


def run_architect(state: MetaAgentState) -> dict:
    """
    LangGraph node: designs the full agent architecture.
    Reads job_description, writes architecture + events.
    """
    job = state["job_description"]
    prompt = f"""
Design a complete multi-agent LangGraph system for this job:

---
{job}
---

Produce a complete SystemArchitecture with all agents, tools, handoffs, and failure modes.
Be specific. Be minimal. Be production-grade.
"""

    raw = complete_json(
        system=ARCHITECT_SYSTEM,
        user=prompt,
        schema=SystemArchitecture,
        temperature=0.25,
        max_tokens=4096,
    )

    architecture = SystemArchitecture(**raw)

    return {
        "architecture": architecture,
        "events": [
            f"ARCHITECT · Designed {len(architecture.agents)}-agent {architecture.topology} system: {architecture.system_name}"
        ],
    }


