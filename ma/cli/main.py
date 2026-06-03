"""
MetaAgent CLI — the command-line interface for the agent fabrication system.

Commands:
  metaagent build  "your job description"  — full pipeline
  metaagent build  --file job.txt          — read from file
  metaagent design "job"                   — architecture only (no code)
  metaagent info                           — system info

The CLI streams LangGraph state updates in real time, rendering each
pipeline stage as it completes — the terminal feels live, not batched.
"""
import os
import sys
import time
from pathlib import Path
from typing import Optional
import typer
from dotenv import load_dotenv
from ma.display.terminal import (
    console,
    boot_sequence,
    print_job_received,
    print_stage_header,
    print_architecture,
    print_critique,
    print_synthesis_progress,
    print_validation,
    print_code_preview,
    print_final_output,
    print_error,
)
from ma.core.brain import get_compiled_graph
from ma.core.state import MetaAgentState

load_dotenv()

app = typer.Typer(
    name="metaagent",
    help="AGI-adjacent system that designs and fabricates multi-agent AI architectures",
    add_completion=False,
    rich_markup_mode="rich",
)


def _validate_env():
    """Check required environment variables before running."""
    if not os.getenv("GROQ_API_KEY"):
        print_error(
            "GROQ_API_KEY not configured",
            "Add GROQ_API_KEY=gsk_... to your .env file\n"
            "Free API key: https://console.groq.com"
        )
        raise typer.Exit(1)


def _run_pipeline(job_description: str, output_dir: str, design_only: bool = False):
    """
    Core pipeline runner. Streams LangGraph events and renders each
    stage with the appropriate terminal display.
    """
    graph = get_compiled_graph()

    initial_state: MetaAgentState = {
        "job_description": job_description,
        "output_dir": output_dir,
        "architecture": None,
        "critique": None,
        "critique_iterations": 0,
        "generated_code": None,
        "generated_readme": None,
        "validation": None,
        "events": [],
        "errors": [],
        "final_output_path": None,
    }

    print_job_received(job_description)

    # Stream events from LangGraph — each yielded chunk is a node completion
    final_state = None
    try:
        for chunk in graph.stream(initial_state, stream_mode="updates"):
            node_name = list(chunk.keys())[0]
            node_output = chunk[node_name]

            ### Stage 1: Architect completes ###
            if node_name == "architect":
                print_stage_header(
                    1, "ARCHITECT", "Designing agent topology from job description...")
                arch = node_output.get("architecture")
                if arch:
                    print_architecture(arch)
                time.sleep(0.3)

            ### Stage 2: Critic assessment ###
            elif node_name == "critic":
                print_stage_header(
                    2, "CRITIC", "Adversarially reviewing the architecture...")
                critique = node_output.get("critique")
                iteration = node_output.get("critique_iterations", 1)
                if critique:
                    print_critique(critique, iteration)
                time.sleep(0.3)

            ### Architect revision ###
            elif node_name == "architect_revision":
                print_stage_header(2, "ARCHITECT REVISION",
                                   "Applying critic feedback — redesigning...")
                arch = node_output.get("architecture")
                if arch:
                    print_architecture(arch)
                time.sleep(0.3)

            ### Stage 3: Synthesizer ###
            elif node_name == "synthesizer":
                if not design_only:
                    print_stage_header(
                        3, "SYNTHESIZER", "Translating architecture → LangGraph Python code...")
                    with print_synthesis_progress() as progress:
                        task = progress.add_task(
                            "Synthesizing agent system code...", total=100)
                        # Fake progress while LLM generates (no streaming from inner call)
                        for i in range(85):
                            time.sleep(0.04)
                            progress.update(task, advance=1)
                        # Synthesis has already completed by here (synchronous)
                        progress.update(task, completed=100)

                    code = node_output.get("generated_code", "")
                    if code:
                        console.print()
                        print_code_preview(code, lines=35)

            ### Stage 4: Validator ###
            elif node_name == "validator":
                print_stage_header(
                    4, "VALIDATOR", "Static analysis of generated code...")
                validation = node_output.get("validation")
                if validation:
                    print_validation(validation)

            ### Final: Writer ###
            elif node_name == "writer":
                pass   # output handled by print_final_output below

            # Accumulate final state
            if final_state is None:
                final_state = dict(initial_state)
            final_state.update(node_output)

    except KeyboardInterrupt:
        console.print("\n  [bold red]Pipeline interrupted by user.[/bold red]")
        raise typer.Exit(1)
    except Exception as e:
        print_error("Pipeline execution failed", str(e))
        raise typer.Exit(1)

    # Final output reveal
    if final_state and final_state.get("final_output_path"):
        print_final_output(
            output_path=final_state["final_output_path"],
            arch=final_state["architecture"],
            events=final_state.get("events", []),
        )
    elif design_only and final_state and final_state.get("architecture"):
        console.print()
        console.print(
            "  [bold green]Architecture design complete.[/bold green]")
        console.print(
            "  [dim]Run without --design-only to generate the full agent system code.[/dim]")
        console.print()


@app.command()
def build(
    job: Optional[str] = typer.Argument(
        None,
        help="Plain-English description of the agent system to build",
        show_default=False,
    ),
    file: Optional[Path] = typer.Option(
        None, "--file", "-f",
        help="Path to a .txt file containing the job description",
    ),
    output: str = typer.Option(
        "./output", "--output", "-o",
        help="Output directory for generated agent system",
    ),
    design_only: bool = typer.Option(
        False, "--design-only", "-d",
        help="Run only the Architect + Critic stages (no code generation)",
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m",
        help="Groq model to use (default: llama-3.3-70b-versatile)",
    ),
):
    """
    [bold cyan]Build a complete multi-agent AI system from a plain-English job description.[/bold cyan]

    MetaAgent will:
    1. Design the full agent architecture (ARCHITECT)
    2. Adversarially critique and optionally revise it (CRITIC)
    3. Generate complete LangGraph Python code (SYNTHESIZER)
    4. Validate and auto-fix the generated code (VALIDATOR)
    5. Write all artifacts to the output directory (WRITER)

    Examples:

    [cyan]metaagent build "Monitor competitor pricing daily and alert on changes"[/cyan]

    [cyan]metaagent build --file jobs/support_triage.txt --output ./my_agents[/cyan]

    [cyan]metaagent build "Research assistant that finds papers" --design-only[/cyan]
    """
    _validate_env()

    # Override model if specified
    if model:
        os.environ["METAAGENT_MODEL"] = model

    # Get job description from argument or file
    job_description = ""
    if file:
        if not file.exists():
            print_error(f"File not found: {file}")
            raise typer.Exit(1)
        job_description = file.read_text().strip()
    elif job:
        job_description = job.strip()
    else:
        # Interactive input if neither provided
        console.print(
            "\n  [bold cyan]Enter job description[/bold cyan] [dim](press Enter twice when done)[/dim]\n")
        lines = []
        try:
            while True:
                line = input("  > ")
                if line == "" and lines and lines[-1] == "":
                    break
                lines.append(line)
            job_description = "\n".join(lines).strip()
        except (KeyboardInterrupt, EOFError):
            raise typer.Exit(0)

    if not job_description:
        print_error("No job description provided",
                    "Pass a description as argument or use --file")
        raise typer.Exit(1)

    boot_sequence()
    _run_pipeline(job_description, output, design_only=design_only)


@app.command()
def info():
    """
    [bold cyan]Display MetaAgent system information and configuration.[/bold cyan]
    """
    from rich.table import Table
    from rich import box

    console.print()
    console.print("  [bold cyan]MetaAgent System Information[/bold cyan]")
    console.print()

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("key", style="dim", width=24)
    table.add_column("value", style="bold white")

    groq_key = os.getenv("GROQ_API_KEY", "")
    key_status = f"[green]Configured[/green] ({groq_key[:8]}...)" if groq_key else "[red]NOT SET[/red]"

    table.add_row("Version",       "0.1.0")
    table.add_row("GROQ_API_KEY",  key_status)
    table.add_row("Model",         os.getenv(
        "METAAGENT_MODEL", "llama-3.3-70b-versatile"))
    table.add_row("Output dir",    os.getenv(
        "METAAGENT_OUTPUT_DIR", "./output"))
    table.add_row("Pipeline stages",
                  "ARCHITECT → CRITIC → SYNTHESIZER → VALIDATOR → WRITER")
    table.add_row("Max critique loops", "2")
    table.add_row("Free LLM provider", "Groq (https://console.groq.com)")

    console.print(table)
    console.print()


if __name__ == "__main__":
    app()
