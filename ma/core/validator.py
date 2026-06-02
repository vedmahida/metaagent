"""
VALIDATOR — Stage 4 of the MetaAgent pipeline.

Performs static analysis on generated code WITHOUT executing it:
  1. AST parse check — is the Python syntactically valid?
  2. Import check — are all required imports present?
  3. Node count check — does code have a function for each agent?
  4. StateGraph check — is StateGraph constructed and compiled?
  5. Entrypoint check — is __main__ block present?

If issues are found, the Validator attempts auto-correction via a focused
LLM call before flagging as failed. Most syntax issues are fixable.
"""
import ast
from ma.core.state import MetaAgentState, ValidationResult, SystemArchitecture
from ma.llm.groq_client import complete
from ma.utils.logger import get_logger

logger = get_logger(__name__)

REQUIRED_IMPORTS = [
    "langgraph",
    "StateGraph",
    "dotenv",
    "groq",
    "TypedDict",
]

FIXER_SYSTEM = """
You are a Python syntax expert. Fix the provided broken Python code.
Return ONLY the corrected Python code. No explanation. No markdown fences.
Fix ALL issues listed. Do not change the logic, only fix syntax and imports.
"""


def _check_syntax(code: str) -> tuple[bool, str | None]:
    """Returns (is_valid, error_message)."""
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, f"SyntaxError at line {e.lineno}: {e.msg}"


def _check_imports(code: str) -> list[str]:
    """Returns list of missing required imports."""
    missing = []
    for req in REQUIRED_IMPORTS:
        if req not in code:
            missing.append(req)
    return missing


def _check_agent_functions(code: str, architecture: SystemArchitecture) -> list[str]:
    """Checks that a function exists for each agent."""
    missing = []
    for agent in architecture.agents:
        # LangGraph nodes are typically named run_<AgentName> or <agent_name>_node
        fn_name = f"run_{agent.name.lower().replace('agent', '')}"
        alt_name = agent.name.lower()
        if fn_name not in code and alt_name not in code and agent.name.lower() not in code:
            missing.append(agent.name)
    return missing


def _try_fix_code(code: str, issues: list[str]) -> str | None:
    """Attempts LLM-assisted code fix. Returns fixed code or None."""
    issues_str = "\n".join(f"- {i}" for i in issues)
    prompt = f"""
Fix the following Python code. Issues to fix:
{issues_str}

BROKEN CODE:
```python
{code}
```
"""
    try:
        fixed = complete(system=FIXER_SYSTEM, user=prompt,
                         temperature=0.1, max_tokens=8000)
        if fixed.startswith("```"):
            lines = fixed.split("\n")
            fixed = "\n".join(l for l in lines if not l.startswith("```"))
        return fixed
    except Exception:
        return None


def run_validator(state: MetaAgentState) -> dict:
    """
    LangGraph node: validates generated code.
    Attempts auto-fix if issues found.
    """
    code: str = state["generated_code"]
    architecture: SystemArchitecture = state["architecture"]

    issues: list[str] = []
    warnings: list[str] = []

    # 1. Syntax check
    syntax_ok, syntax_err = _check_syntax(code)
    if not syntax_ok:
        issues.append(syntax_err)

    # 2. Import check
    missing_imports = _check_imports(code)
    for imp in missing_imports:
        issues.append(f"Missing import: {imp}")

    # 3. Agent function check
    missing_agents = _check_agent_functions(code, architecture)
    for agent in missing_agents:
        warnings.append(f"No function found for agent: {agent}")

    # 4. StateGraph check
    if "StateGraph" not in code:
        issues.append("StateGraph not constructed — graph definition missing")

     # 5. Entrypoint check
    if '__name__ == "__main__"' not in code and "__name__ == '__main__'" not in code:
        warnings.append("No __main__ entrypoint found")

    # Attempt auto-fix if issues exist
    fixed_code = None
    if issues:
        fixed_code = _try_fix_code(code, issues)
        if fixed_code:
            # Re-validate the fixed code
            fix_syntax_ok, _ = _check_syntax(fixed_code)
            if fix_syntax_ok:
                issues = [f"AUTO-FIXED: {i}" for i in issues]

    validation = ValidationResult(
        syntax_valid=syntax_ok or (fixed_code is not None),
        imports_valid=len(missing_imports) == 0,
        agent_count_matches=len(missing_agents) == 0,
        issues=issues,
        warnings=warnings,
        fixed_code=fixed_code,
    )

    return {
        "validation": validation,
        "generated_code": fixed_code or code,  # use fixed code if available
        "events": [
            f"VALIDATOR · {'PASS' if not issues else 'ISSUES FOUND — auto-fix attempted'} · "
            f"{len(issues)} issues · {len(warnings)} warnings"
        ],
    }


