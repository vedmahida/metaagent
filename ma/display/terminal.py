"""
TERMINAL — The sci-fi visual layer of MetaAgent.

Every print statement, every animation, every status update goes through here.
The goal: make the terminal feel like a living machine thinking in real time.

Design philosophy:
- Dark, urgent color palette (red, cyan, yellow — no pastels)
- Every stage has a distinct visual identity
- Progress feels earned, not instant
- Failures are dramatic but informative
- The final output feels like a reveal
"""
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.syntax import Syntax
from rich.columns import Columns
from rich.text import Text
from rich.rule import Rule
from rich import box
from rich.live import Live
from rich.layout import Layout
from rich.align import Align

from ma.core.state import SystemArchitecture, CritiqueResult, ValidationResult

console = Console(highlight=False)

########## Color palette ###########
C_PRIMARY = "bold cyan"
C_DANGER = "bold red"
C_WARN = "bold yellow"
C_SUCCESS = "bold green"
C_DIM = "dim white"
C_ACCENT = "bold magenta"
C_NEURAL = "bold bright_cyan"


def boot_sequence():
    """The opening boot sequence — sets the sci-fi tone."""
    console.clear()
    time.sleep(0.1)

    boot_lines = [
        ("METAAGENT SYSTEM INITIALIZING", C_PRIMARY, 0.05),
        ("▸ Loading cognitive architecture modules", C_DIM, 0.03),
        ("▸ Establishing Groq neural link", C_DIM, 0.03),
        ("▸ Compiling LangGraph state machine", C_DIM, 0.03),
        ("▸ Calibrating ARCHITECT subsystem", C_DIM, 0.02),
        ("▸ Calibrating CRITIC subsystem", C_DIM, 0.02),
        ("▸ Calibrating SYNTHESIZER subsystem", C_DIM, 0.02),
        ("▸ Calibrating VALIDATOR subsystem", C_DIM, 0.02),
        ("▸ All systems nominal", C_SUCCESS, 0.05),
    ]

    console.print()
    for text, style, delay in boot_lines:
        console.print(f"  [{style}]{text}[/{style}]")
        time.sleep(delay)

    console.print()
    console.print(Panel(
        Align.center(
            Text.from_markup(
                "[bold red]███╗   ███╗███████╗████████╗ █████╗  █████╗  ██████╗ ███████╗███╗   ██╗████████╗\n"
                "[bold red]████╗ ████║██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝\n"
                "[bold cyan]██╔████╔██║█████╗     ██║   ███████║███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   \n"
                "[bold cyan]██║╚██╔╝██║██╔══╝     ██║   ██╔══██║██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   \n"
                "[bold white]██║ ╚═╝ ██║███████╗   ██║   ██║  ██║██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   \n"
                "[bold white]╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   "
            )
        ),
        border_style="red",
        subtitle="[dim]AGENT FABRICATION SYSTEM v0.1.0 · POWERED BY GROQ LPU INFERENCE[/dim]",
        padding=(1, 2),
    ))
    console.print()


def print_job_received(job: str):
    """Display the job description in a mission briefing style."""
    console.print(
        Rule("[bold red]◈ MISSION PARAMETERS RECEIVED ◈[/bold red]", style="red"))
    console.print()
    console.print(Panel(
        f"[white]{job}[/white]",
        title="[bold yellow]⚡ JOB DESCRIPTION[/bold yellow]",
        border_style="yellow",
        padding=(1, 2),
    ))
    console.print()


def print_stage_header(stage_num: int, stage_name: str, description: str):
    """Print a dramatic stage transition header."""
    console.print()
    console.print(Rule(
        f"[bold cyan]STAGE {stage_num} · {stage_name.upper()}[/bold cyan]",
        style="cyan"
    ))
    console.print(f"  [dim]{description}[/dim]")
    console.print()


def print_architecture(arch: SystemArchitecture):
    """Renders the designed architecture as a rich tree + stats table."""

    # Agent tree
    tree = Tree(
        f"[bold cyan]◈ {arch.system_name}[/bold cyan]  "
        f"[dim]({arch.topology.upper()} · {len(arch.agents)} agents)[/dim]",
        guide_style="dim cyan",
    )

    for agent in arch.agents:
        agent_branch = tree.add(
            f"[bold yellow]▸ {agent.name}[/bold yellow]  [dim]{agent.role}[/dim]"
        )
        if agent.tools:
            tools_branch = agent_branch.add("[dim cyan]Tools[/dim cyan]")
            for tool in agent.tools:
                tools_branch.add(f"[green]⚙ {tool}[/green]")
        if agent.handoff_to:
            handoff_branch = agent_branch.add("[dim cyan]Handoffs[/dim cyan]")
            for h in agent.handoff_to:
                handoff_branch.add(f"[magenta]→ {h}[/magenta]")
        if agent.failure_modes:
            fail_branch = agent_branch.add(
                "[dim cyan]Failure modes[/dim cyan]")
            for fm in agent.failure_modes:
                fail_branch.add(f"[red]⚠ {fm}[/red]")

    # Stats table
    stats = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    stats.add_column("key", style="dim")
    stats.add_column("val", style="bold white")
    stats.add_row("Entry point", arch.entry_point)
    stats.add_row("Est. cost/run", arch.estimated_token_cost_per_run)
    stats.add_row("Objective", arch.objective)
    stats.add_row("Data flow", arch.data_flow_summary)

    console.print(Panel(tree, border_style="cyan", padding=(1, 2)))
    console.print(Panel(
        stats, title="[dim]System Metadata[/dim]", border_style="dim", padding=(0, 1)))


def print_critique(critique: CritiqueResult, iteration: int):
    """Renders the critic's assessment with score gauge and color-coded findings."""

    # Score bar
    score_pct = int(critique.score * 100)
    bar_filled = int(critique.score * 30)
    bar_empty = 30 - bar_filled
    color = C_SUCCESS if critique.approved else (
        C_WARN if critique.score >= 0.5 else C_DANGER)
    bar = f"[{color}]{'█' * bar_filled}[/{color}][dim]{'░' * bar_empty}[/dim]"
    verdict = "[bold green]APPROVED ✓[/bold green]" if critique.approved else "[bold red]REJECTED ✗[/bold red]"

    score_panel_content = (
        f"  Score  {bar}  [{color}]{score_pct}/100[/{color}]    {verdict}\n"
        f"  [dim]Iteration {iteration}[/dim]"
    )

    console.print(Panel(
        score_panel_content,
        title=f"[bold red]◈ CRITIC ASSESSMENT[/bold red]",
        border_style="red",
        padding=(0, 1),
    ))

    # Findings table
    table = Table(box=box.SIMPLE_HEAD, show_header=True, padding=(0, 1))
    table.add_column("Category", style="bold", width=16)
    table.add_column("Findings", overflow="fold")

    for s in critique.strengths[:3]:
        table.add_row("[green]✓ Strength[/green]", s)
    for w in critique.weaknesses[:3]:
        table.add_row("[yellow]⚠ Weakness[/yellow]", w)
    for g in critique.critical_gaps:
        table.add_row("[red]✗ Critical Gap[/red]", g)

    console.print(table)


def print_synthesis_progress() -> Progress:
    """Returns a configured Progress bar for the synthesis stage."""
    return Progress(
        SpinnerColumn(spinner_name="dots12", style="cyan"),
        TextColumn("[bold cyan]{task.description}[/bold cyan]"),
        BarColumn(bar_width=40, style="cyan", complete_style="green"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )


def print_validation(validation: ValidationResult):
    """Renders the validation report as a pass/fail checklist."""
    checks = [
        ("Syntax valid",       validation.syntax_valid),
        ("Imports valid",      validation.imports_valid),
        ("Agent count match",  validation.agent_count_matches),
    ]

    check_lines = ""
    for label, passed in checks:
        icon = "[bold green]✓[/bold green]" if passed else "[bold red]✗[/bold red]"
        check_lines += f"  {icon}  {label}\n"

    if validation.issues:
        check_lines += "\n"
        for issue in validation.issues:
            check_lines += f"  [yellow]▸[/yellow] {issue}\n"

    if validation.warnings:
        for warn in validation.warnings:
            check_lines += f"  [dim]⚠ {warn}[/dim]\n"

    if validation.fixed_code:
        check_lines += "\n  [dim cyan]Auto-fix applied ✓[/dim cyan]"

    border = "green" if validation.syntax_valid else "yellow"
    console.print(Panel(
        check_lines,
        title="[bold]◈ VALIDATOR REPORT[/bold]",
        border_style=border,
        padding=(0, 1),
    ))


def print_code_preview(code: str, lines: int = 40):
    """Shows first N lines of generated code with syntax highlighting."""
    preview = "\n".join(code.splitlines()[:lines])
    if len(code.splitlines()) > lines:
        preview += f"\n\n[dim]... {len(code.splitlines()) - lines} more lines ...[/dim]"

    console.print(Panel(
        Syntax(preview, "python", theme="monokai", line_numbers=True),
        title="[bold cyan]◈ GENERATED CODE PREVIEW[/bold cyan]",
        border_style="cyan",
        padding=(0, 0),
    ))


def print_final_output(output_path: str, arch: SystemArchitecture, events: list[str]):
    """The grand finale — full summary of what was built."""
    console.print()
    console.print(
        Rule("[bold green]◈ FABRICATION COMPLETE ◈[/bold green]", style="green"))
    console.print()

    # Output files table
    files_table = Table(box=box.SIMPLE, show_header=True, padding=(0, 2))
    files_table.add_column("File", style="bold cyan")
    files_table.add_column("Description", style="dim")
    files_table.add_row("agent_system.py",
                        "Complete runnable LangGraph agent system")
    files_table.add_row(
        "README.md",        "Architecture docs and setup guide")
    files_table.add_row("architecture.json",
                        "Full design blueprint (machine-readable)")
    files_table.add_row("metaagent_run.log", "Full pipeline event log")

    # Event timeline
    timeline = "\n".join(
        f"  [dim cyan]▸[/dim cyan] [dim]{e}[/dim]" for e in events
    )

    console.print(Panel(
        f"[bold white]{arch.system_name}[/bold white]\n"
        f"[dim]{arch.objective}[/dim]\n\n"
        f"[bold]{len(arch.agents)} agents[/bold] · "
        f"[bold]{arch.topology.upper()}[/bold] topology\n\n"
        f"[bold green]Output:[/bold green] [cyan]{output_path}[/cyan]",
        title="[bold green]◈ SYSTEM FABRICATED[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))

    console.print(
        Panel(files_table, title="[dim]Generated Files[/dim]", border_style="dim"))
    console.print(
        Panel(timeline, title="[dim]Pipeline Event Log[/dim]", border_style="dim"))

    console.print()
    console.print(f"  [bold green]► Run your new agent system:[/bold green]")
    console.print(f"  [cyan]cd {output_path}[/cyan]")
    console.print(
        f"  [cyan]pip install langgraph langchain-groq rich python-dotenv[/cyan]")
    console.print(f"  [cyan]python agent_system.py[/cyan]")
    console.print()


def print_error(message: str, detail: str = ""):
    """Fatal error display."""
    console.print()
    console.print(Panel(
        f"[bold white]{message}[/bold white]\n"
        + (f"\n[dim]{detail}[/dim]" if detail else ""),
        title="[bold red]◈ SYSTEM ERROR[/bold red]",
        border_style="red",
        padding=(1, 2),
    ))
