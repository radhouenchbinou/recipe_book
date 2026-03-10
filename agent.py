#!/usr/bin/env python3
"""Trading Bot Project Management Claude Agent."""

import argparse
import json
import os
import sys

import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from config import ACTIONS, HISTORY_FILE, MAX_HISTORY_TURNS, MODEL
from prompts import ACTION_PROMPTS, SYSTEM_PROMPT

console = Console()
client = anthropic.Anthropic()


# ---------------------------------------------------------------------------
# History helpers
# ---------------------------------------------------------------------------

def load_history() -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        console.print(f"[yellow]Warning: could not load history ({exc}). Starting fresh.[/yellow]")
        return []


def save_history(messages: list) -> None:
    # Keep only the last MAX_HISTORY_TURNS pairs (each pair = 2 messages)
    trimmed = messages[-(MAX_HISTORY_TURNS * 2):]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(trimmed, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        console.print(f"[yellow]Warning: could not save history ({exc}).[/yellow]")


# ---------------------------------------------------------------------------
# Claude interaction
# ---------------------------------------------------------------------------

def chat(user_message: str, history: list) -> str:
    history.append({"role": "user", "content": user_message})
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=8096,
            system=SYSTEM_PROMPT,
            messages=history,
        )
        assistant_text = response.content[0].text
    except anthropic.APIError as exc:
        console.print(f"[red]API error: {exc}[/red]")
        history.pop()  # remove the user message we just appended
        sys.exit(1)

    history.append({"role": "assistant", "content": assistant_text})
    save_history(history)
    return assistant_text


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def format_response(text: str) -> None:
    is_markdown = any(
        token in text
        for token in ("##", "**", "```", "| ---", "- ", "1. ", "# ")
    )
    if is_markdown:
        console.print(Panel(Markdown(text), title="[bold cyan]Agent[/bold cyan]", border_style="cyan"))
    else:
        console.print(Panel(text, title="[bold cyan]Agent[/bold cyan]", border_style="cyan"))


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def interactive_loop(history: list) -> None:
    console.print(
        Panel(
            "[bold green]Trading Bot Project Management Agent[/bold green]\n"
            "Type your question or command. Type [bold]exit[/bold] or press Ctrl-C to quit.",
            border_style="green",
        )
    )
    while True:
        try:
            user_input = console.input("[bold yellow]You:[/bold yellow] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Session ended.[/dim]")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "q"}:
            console.print("[dim]Goodbye.[/dim]")
            break

        response = chat(user_input, history)
        format_response(response)


def single_query(query: str, history: list) -> None:
    response = chat(query, history)
    format_response(response)


def run_action(action: str, history: list, sprint: int = None, week: int = None) -> None:
    if action not in ACTION_PROMPTS:
        console.print(f"[red]Unknown action '{action}'. Run with --list-actions to see available actions.[/red]")
        sys.exit(1)

    prompt_template = ACTION_PROMPTS[action]
    try:
        prompt = prompt_template.format(sprint=sprint, week=week)
    except KeyError:
        prompt = prompt_template

    console.print(f"[dim]Running action: [bold]{action}[/bold][/dim]\n")
    response = chat(prompt, history)
    format_response(response)


def list_actions() -> None:
    console.print(Panel(
        "\n".join(f"[bold cyan]{name}[/bold cyan]\n  {desc}\n" for name, desc in ACTIONS.items()),
        title="[bold]Available Actions[/bold]",
        border_style="blue",
    ))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trading Bot Project Management Claude Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python agent.py                            # interactive session\n"
            "  python agent.py -q 'What is critical path?'  # single query\n"
            "  python agent.py --action plan_phase1       # predefined action\n"
            "  python agent.py --action sprint_tasks --sprint 2\n"
            "  python agent.py --action status_report --week 3\n"
            "  python agent.py --list-actions             # show all actions\n"
            "  python agent.py --clear-history            # wipe saved history\n"
        ),
    )
    parser.add_argument("-q", "--query", help="Single query (non-interactive)")
    parser.add_argument("--action", help="Run a predefined action prompt")
    parser.add_argument("--sprint", type=int, help="Sprint number (used with --action sprint_tasks)")
    parser.add_argument("--week", type=int, help="Week number (used with --action status_report)")
    parser.add_argument("--list-actions", action="store_true", help="List available actions and exit")
    parser.add_argument("--clear-history", action="store_true", help="Clear saved conversation history and exit")
    args = parser.parse_args()

    if args.list_actions:
        list_actions()
        return

    if args.clear_history:
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
            console.print("[green]Conversation history cleared.[/green]")
        else:
            console.print("[dim]No history file found.[/dim]")
        return

    history = load_history()

    if args.action:
        run_action(args.action, history, sprint=args.sprint, week=args.week)
    elif args.query:
        single_query(args.query, history)
    else:
        interactive_loop(history)


if __name__ == "__main__":
    main()
