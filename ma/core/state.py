"""
Shared LangGraph state — the bloodstream of MetaAgent's pipeline.

Every stage reads from and writes to this TypedDict. LangGraph's
reducer functions merge partial updates, so each node only touches
the fields it owns. Nothing is lost between stages.
"""
from typing import Any, TypedDict, Annotated
from pydantic import BaseModel
import operator

# === Pydantic schemas for structured LLM outputs =============================
class AgentSpec(BaseModel):
    """A single agent in the designed system."""
    name: str                        # e.g. "PriceMonitorAgent"
    role: str                        # e.g. "Scrapes competitor pricing pages"
    tools: list[str]                 # e.g. ["web_scrape", "price_parser"]
    inputs: list[str]                # what it receives
    outputs: list[str]               # what it produces
    failure_modes: list[str]         # what can go wrong
    handoff_to: list[str]            # which agents it passes work to


class SystemArchitecture(BaseModel):
    """Complete multi-agent system design."""
    system_name: str
    objective: str                   # one-sentence goal
    agents: list[AgentSpec]
    entry_point: str                 # which agent receives the first input
    topology: str                    # "pipeline" | "hierarchical" | "collaborative"
    estimated_token_cost_per_run: str
    data_flow_summary: str


class CritiqueResult(BaseModel):
    """Critic agent's assessment of the architecture."""
    score: float                     # 0.0 – 1.0
    strengths: list[str]
    weaknesses: list[str]
    critical_gaps: list[str]         # showstoppers
    revised_agents: list[AgentSpec] | None  # optional redesign suggestions
    approved: bool                   # True if score >= 0.75


class ValidationResult(BaseModel):
    """Code validator's report."""
    syntax_valid: bool
    imports_valid: bool
    agent_count_matches: bool
    issues: list[str]
    warnings: list[str]
    fixed_code: str | None           # auto-corrected code if fixable


# === LangGraph State ========================================================
class MetaAgentState(TypedDict):
    """The shared state object passed through the LangGraph pipeline."""
    ## Inputs
    job_description: str             # raw user input
    output_dir: str                  # where to write files
    
    ## STAGE 1: Architecture Design
    architecture: SystemArchitecture | None
    
    ## STAGE 2: Critique & Revision
    critique: CritiqueResult | None
    critique_iterations: Annotated[int, operator.add]  # auto-increments
    
    ## STAGE 3: Code Generation
    generated_code: str | None       # raw LangGraph Python code
    generated_readme: str | None
    
    ## STAGE 4: Code Validation
    validation: ValidationResult | None
    
    # === Pipeline Metadata ===================================
    # append-only log — every stage writes its events
    events: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]
    final_output_path: str | None
    
    
    
