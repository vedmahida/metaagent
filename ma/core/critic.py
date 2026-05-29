"""
CRITIC — Stage 2 of the MetaAgent pipeline.

The Critic is a separate agent that adversarially reviews the Architect's
design. It scores the architecture 0.0-1.0, identifies weaknesses and
critical gaps, and either approves or demands a revision.

If score < 0.75, the pipeline loops back to the Architect with the
Critic's feedback injected into the redesign prompt. This is the
"reflection loop" — the system's self-correction mechanism.

Max 2 critique iterations to prevent infinite loops.
"""
from ma.core.state import MetaAgentState, CritiqueResult, SystemArchitecture
from ma.llm.groq_client import complete_json
from ma.utils.logger import get_logger

logger = get_logger(__name__)

MAX_CRITIQUE_ITERATIONS = 2

CRITIC_SYSTEM = """
You are CRITIC — a ruthless AI systems auditor. You review multi-agent 
architectures for production readiness. You do NOT care about being nice.
You care about: correctness, completeness, failure resilience, and minimal complexity.

SCORING RUBRIC (0.0 - 1.0):
- 0.0-0.4: Fundamental design flaws. Cannot proceed. Redesign required.
- 0.4-0.6: Significant gaps. Missing agents, undefined handoffs, or tool hallucinations.
- 0.6-0.75: Acceptable but improvable. Proceed with warnings.
- 0.75-0.90: Good. Production-viable with minor fixes.
- 0.90-1.0: Excellent. Ship it.

CRITICAL GAPS (automatic score cap at 0.5):
- Undefined handoff target (agent hands off to nobody)
- Tool that cannot be implemented (e.g. "magic_database_connector")
- Missing error handling for network/API failures
- Single point of failure with no fallback
- Agent with zero tools trying to do real work

Set approved=true if and only if score >= 0.75.
If you have improved agent suggestions, populate revised_agents.
"""


def run_critic(state: MetaAgentState) -> dict:
    """
    LangGraph node: critiques the current architecture.
    Reads architecture, writes critique + events.
    """
    architecture: SystemArchitecture = state["architecture"]
    architecture_summary = architecture.model_dump_json(indent=2)

    prompt = f"""
Critique this multi-agent system architecture:

```json
{architecture_summary}
```

Be specific. Name the exact agents and tools that have problems.
Score it honestly. If it needs redesign, provide revised_agents with your fixes.
"""
    raw = complete_json(
        system=CRITIC_SYSTEM,
        user=prompt,
        schema=CritiqueResult,
        temperature=0.2,
        max_tokens=3000,
    )

    critique = CritiqueResult(**raw)
    iteration = state.get("critique_iterations", 0)

    events = [
        f"CRITIC · Score: {critique.score:.2f}/1.00 · "
        f"{'APPROVED ✓' if critique.approved else 'REJECTED — redesign required'} "
        f"(iteration {iteration + 1}/{MAX_CRITIQUE_ITERATIONS})"
    ]

    return {
        "critique": critique,
        "critique_iterations": 1,   # reducer adds this to existing count
        "events": events,
    }


def run_architect_revision(state: MetaAgentState) -> dict:
    """
    LangGraph node: Architect re-designs based on Critic's feedback.
    Only called when critique.approved is False and iterations < MAX.
    """
    critique: CritiqueResult = state["critique"]
    job = state["job_description"]

    feedback_lines = "\n".join(
        f"- {w}" for w in critique.weaknesses + critique.critical_gaps)

    prompt = f"""
Your previous architecture was rejected by the Critic with score {critique.score:.2f}/1.00.

ORIGINAL JOB:
{job}

CRITIC FEEDBACK:
{feedback_lines}

{"SUGGESTED FIXES:" + chr(10) + critique.revised_agents[0].model_dump_json(indent=2) if critique.revised_agents else ""}

Redesign the complete architecture addressing ALL of the critic's issues.
"""

    from ma.llm.groq_client import complete_json as cj
    from ma.core.state import SystemArchitecture

    raw = cj(
        system="""You are ARCHITECT. Redesign the system based on critic feedback.
Apply every fix. Do not repeat the same mistakes.""",
        user=prompt,
        schema=SystemArchitecture,
        temperature=0.3,
        max_tokens=4096,
    )

    architecture = SystemArchitecture(**raw)

    return {
        "architecture": architecture,
        "events": [
            f"ARCHITECT · Revision {state.get('critique_iterations', 1)} complete · "
            f"Redesigned with {len(architecture.agents)} agents"
        ],
    }


def should_revise(state: MetaAgentState) -> str:
    """
    LangGraph conditional edge: decides whether to loop back for revision
    or proceed to code synthesis.
    """
    critique: CritiqueResult = state["critique"]
    iterations = state.get("critique_iterations", 0)

    if critique.approved or iterations >= MAX_CRITIQUE_ITERATIONS:
        return "synthesize"   # proceed to code generation
    return "revise"           # loop back to architect revision


