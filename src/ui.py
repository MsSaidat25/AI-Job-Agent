"""
Rich-based interactive CLI for the AI Job Agent.

Navigation
──────────
  Main menu → Profile setup (first run)
           → Job search
           → Market insights
           → Generate documents
           → Application tracker
           → Analytics dashboard
           → Free-form chat with the agent

Run with:
    python -m src.ui
or
    python main.py
"""
from __future__ import annotations

import sys
from typing import Optional

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

from src.agent import JobAgent
from src.models import (
    ApplicationStatus,
    ExperienceLevel,
    JobType,
    UserProfile,
    init_db,
)

console = Console()


# ── Helpers ────────────────────────────────────────────────────────────────

def _header(title: str) -> None:
    console.print(
        Panel(
            Text(title, style="bold cyan", justify="center"),
            border_style="bright_blue",
        )
    )


def _spinner(msg: str):
    return Progress(
        SpinnerColumn(),
        TextColumn(f"[cyan]{msg}[/cyan]"),
        transient=True,
        console=console,
    )


def _divider() -> None:
    console.rule(style="dim blue")


def _ask(prompt: str, default: str = "") -> str:
    return Prompt.ask(f"[bold yellow]{prompt}[/bold yellow]", default=default)


def _ask_list(prompt: str) -> list[str]:
    raw = Prompt.ask(f"[bold yellow]{prompt}[/bold yellow] (comma-separated)")
    return [s.strip() for s in raw.split(",") if s.strip()]


def _render_markdown(text: str) -> None:
    console.print(Markdown(text))


# ── Profile wizard ─────────────────────────────────────────────────────────

def profile_wizard() -> UserProfile:
    _header("Profile Setup")
    console.print(
        "[dim]Your information stays on your machine. "
        "Only anonymised skill/role data is sent to the AI.[/dim]\n"
    )

    name = _ask("Full name")
    email = _ask("Email address")
    phone = _ask("Phone number (optional)", default="")
    location = _ask("Current location (City, Country)", default="Remote")
    skills = _ask_list("Key skills")
    desired_roles = _ask_list("Desired job titles")

    exp_choices = [e.value for e in ExperienceLevel]
    console.print(f"[bold yellow]Experience level[/bold yellow]: {' / '.join(exp_choices)}")
    exp_level_str = _ask("Experience level", default="mid")
    try:
        exp_level = ExperienceLevel(exp_level_str.lower())
    except ValueError:
        exp_level = ExperienceLevel.MID

    years = IntPrompt.ask("[bold yellow]Years of experience[/bold yellow]", default=0)

    job_type_choices = [j.value for j in JobType]
    console.print(
        f"[bold yellow]Desired job type(s)[/bold yellow] "
        f"({' / '.join(job_type_choices)}):"
    )
    raw_types = _ask_list("Types (comma-separated)")
    desired_types = []
    for t in raw_types:
        try:
            desired_types.append(JobType(t.lower()))
        except ValueError:
            pass
    if not desired_types:
        desired_types = [JobType.FULL_TIME]

    sal_min_str = _ask("Minimum desired salary (USD, optional)", default="0")
    sal_max_str = _ask("Maximum desired salary (USD, optional)", default="0")
    sal_min = int(sal_min_str) if sal_min_str.isdigit() and int(sal_min_str) > 0 else None
    sal_max = int(sal_max_str) if sal_max_str.isdigit() and int(sal_max_str) > 0 else None

    languages = _ask_list("Languages spoken")
    certifications = _ask_list("Certifications (optional)")
    portfolio_url = _ask("Portfolio URL (optional)", default="")
    linkedin_url = _ask("LinkedIn URL (optional)", default="")

    # Simplified education entry
    edu = []
    if Confirm.ask("[bold yellow]Add education entry?[/bold yellow]", default=True):
        degree = _ask("Degree (e.g. B.Sc. Computer Science)")
        school = _ask("Institution")
        grad_year = _ask("Graduation year")
        edu.append({"degree": degree, "school": school, "graduation_year": grad_year})

    # Simplified work history
    work = []
    while Confirm.ask("[bold yellow]Add a work history entry?[/bold yellow]", default=True):
        title = _ask("Job title")
        company = _ask("Company")
        start = _ask("Start date (YYYY-MM)")
        end = _ask("End date (YYYY-MM or 'present')", default="present")
        highlights = _ask_list("Key achievements / responsibilities")
        work.append({
            "title": title,
            "company": company,
            "start": start,
            "end": end,
            "highlights": highlights,
        })
        if not Confirm.ask("Add another role?", default=False):
            break

    profile = UserProfile(
        name=name,
        email=email,
        phone=phone or None,
        location=location,
        skills=skills,
        experience_level=exp_level,
        years_of_experience=years,
        education=edu,
        work_history=work,
        desired_roles=desired_roles,
        desired_job_types=desired_types,
        desired_salary_min=sal_min,
        desired_salary_max=sal_max,
        languages=languages or ["English"],
        certifications=certifications,
        portfolio_url=portfolio_url or None,
        linkedin_url=linkedin_url or None,
    )

    console.print(Panel("[green]Profile saved![/green]", border_style="green"))
    return profile


# ── Job search view ────────────────────────────────────────────────────────

def job_search_view(agent: JobAgent) -> None:
    _header("Job Search")
    location_filter = _ask("Filter by location (leave blank for global)", default="")
    include_remote = Confirm.ask("Include remote jobs?", default=True)
    max_results = IntPrompt.ask("Max results to display", default=10)

    query = (
        f"Search for jobs"
        + (f" near {location_filter}" if location_filter else " globally")
        + (" including remote" if include_remote else "")
        + f". Show top {max_results} results."
    )

    with _spinner("Searching jobs and scoring matches…"):
        response = agent.chat(query)

    _divider()
    _render_markdown(response)


# ── Market insights view ───────────────────────────────────────────────────

def market_insights_view(agent: JobAgent) -> None:
    _header("Market Intelligence")
    region = _ask("Region (e.g. 'Berlin, Germany' or 'Southeast Asia')")
    industry = _ask("Industry (e.g. 'Technology', 'Finance')")

    with _spinner(f"Analysing {industry} market in {region}…"):
        response = agent.chat(
            f"Give me a detailed job market analysis for the {industry} industry in {region}. "
            f"Also include culturally-aware application tips for this region."
        )

    _divider()
    _render_markdown(response)


# ── Document generation view ───────────────────────────────────────────────

def document_generation_view(agent: JobAgent) -> None:
    _header("Document Generator")
    console.print(
        "[dim]First run a job search so the agent knows which jobs are available.[/dim]\n"
    )

    doc_type = Prompt.ask(
        "[bold yellow]Generate[/bold yellow]",
        choices=["resume", "cover_letter", "both"],
        default="both",
    )

    job_id = _ask("Job ID to tailor for (from search results)")
    tone = "professional"
    if "resume" in doc_type or doc_type == "both":
        tone = Prompt.ask(
            "[bold yellow]Resume tone[/bold yellow]",
            choices=["professional", "creative", "technical"],
            default="professional",
        )

    msgs = []
    if doc_type in ("resume", "both"):
        msgs.append(f"Generate a {tone} resume for job ID {job_id}.")
    if doc_type in ("cover_letter", "both"):
        msgs.append(f"Generate a cover letter for job ID {job_id}.")

    with _spinner("Generating tailored documents…"):
        response = agent.chat(" ".join(msgs))

    _divider()
    _render_markdown(response)


# ── Application tracker view ───────────────────────────────────────────────

def tracker_view(agent: JobAgent) -> None:
    _header("Application Tracker")
    action = Prompt.ask(
        "[bold yellow]Action[/bold yellow]",
        choices=["log", "update", "list"],
        default="list",
    )

    if action == "log":
        job_id = _ask("Job ID to log")
        notes = _ask("Notes (optional)", default="")
        with _spinner("Logging application…"):
            response = agent.chat(
                f"Track a new application for job ID {job_id}. Notes: {notes or 'None'}"
            )

    elif action == "update":
        app_id = _ask("Application ID to update")
        status_choices = [s.value for s in ApplicationStatus]
        console.print(f"Statuses: {', '.join(status_choices)}")
        new_status = _ask("New status")
        feedback = _ask("Employer feedback (optional)", default="")
        with _spinner("Updating application…"):
            response = agent.chat(
                f"Update application {app_id} to status '{new_status}'."
                + (f" Employer feedback: {feedback}" if feedback else "")
            )

    else:  # list
        with _spinner("Loading application history…"):
            response = agent.chat(
                "Show me my analytics and all application metrics with insights."
            )

    _divider()
    _render_markdown(response)


# ── Analytics dashboard ────────────────────────────────────────────────────

def analytics_view(agent: JobAgent) -> None:
    _header("Analytics Dashboard")
    with _spinner("Computing analytics and generating insights…"):
        response = agent.chat(
            "Give me a full analytics report: success metrics, AI insights, "
            "and analysis of any employer feedback I've received."
        )
    _divider()
    _render_markdown(response)


# ── Free-form chat view ────────────────────────────────────────────────────

def chat_view(agent: JobAgent) -> None:
    _header("Chat with your Job Agent")
    console.print("[dim]Type 'exit' to return to the main menu.[/dim]\n")
    while True:
        user_input = _ask("You")
        if user_input.lower() in ("exit", "quit", "back"):
            break
        with _spinner("Thinking…"):
            response = agent.chat(user_input)
        _divider()
        _render_markdown(response)
        _divider()


# ── Main menu ──────────────────────────────────────────────────────────────

_MENU_OPTIONS = {
    "1": ("Job Search", job_search_view),
    "2": ("Market Intelligence", market_insights_view),
    "3": ("Generate Documents", document_generation_view),
    "4": ("Application Tracker", tracker_view),
    "5": ("Analytics Dashboard", analytics_view),
    "6": ("Free-form Chat", chat_view),
    "q": ("Quit", None),
}


def main_menu(agent: JobAgent) -> None:
    while True:
        _divider()
        _header("AI Job Agent — Main Menu")

        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        table.add_column("Key", style="bold cyan", width=4)
        table.add_column("Option", style="white")
        for key, (label, _) in _MENU_OPTIONS.items():
            table.add_row(key, label)
        console.print(table)

        choice = Prompt.ask(
            "[bold yellow]Select[/bold yellow]",
            choices=list(_MENU_OPTIONS.keys()),
        )
        if choice == "q":
            console.print("[bold green]Goodbye! Good luck with your job search.[/bold green]")
            sys.exit(0)

        _, handler = _MENU_OPTIONS[choice]
        if handler:
            try:
                handler(agent)
            except KeyboardInterrupt:
                console.print("\n[dim]Returning to menu…[/dim]")


# ── Entry point ────────────────────────────────────────────────────────────

def run() -> None:
    console.clear()
    console.print(
        Panel(
            "[bold cyan]AI Job Application Agent[/bold cyan]\n"
            "[dim]Powered by Claude — your personal career co-pilot[/dim]",
            border_style="bright_blue",
            padding=(1, 4),
        )
    )

    # First run: set up profile; subsequent runs could load from DB
    profile = profile_wizard()
    agent = JobAgent(profile)

    console.print(
        f"\n[green]Welcome, {profile.name}![/green] "
        f"Agent ready for location: [bold]{profile.location}[/bold]\n"
    )
    main_menu(agent)


if __name__ == "__main__":
    run()
