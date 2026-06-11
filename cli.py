"""Sweepstake CLI - championship-aware commands.

Usage:
    ss list                          # List available championships
    ss run <championship>            # Run full pipeline + reports
    ss run <championship> --pipeline # Run only the data pipeline
    ss run <championship> --reports  # Run only report generation
    ss run <championship> --bronze   # Run only bronze stage
    ss run <championship> --silver   # Run only silver stage
    ss run <championship> --gold     # Run only gold stage
"""

from __future__ import annotations

import argparse
import os
import sys
import webbrowser

from src.championships import list_championships, load_config
from src.core.pipeline import run_raw_to_bronze, run_silver_to_gold, run_pipeline, run_bronze_to_silver
from src.core.reports.dashboard import generate_dashboard
from src.core.reports.html import generate_html_reports
from src.core.logo_fetcher import fetch_all_logos
from src.core.printing import print_colored


def cmd_fetch_logos(args: argparse.Namespace) -> None:
    """Download and cache team logos."""
    champ_id = args.championship
    try:
        config = load_config(champ_id)
    except FileNotFoundError as e:
        print_colored(f"Error: {e}", "red")
        sys.exit(1)
    fetch_all_logos(config, force=args.force)


def cmd_list(_args: argparse.Namespace) -> None:
    """List all available championships."""
    championships = list_championships()
    if not championships:
        print_colored("No championships found.", "gray")
        return
    print_colored("Available championships:", "sand")
    for c in championships:
        cfg = load_config(c)
        print_colored(f"  {c}  ({cfg.name}, {cfg.year})", "ice")


def cmd_run(args: argparse.Namespace) -> None:
    """Run pipeline and/or reports for a championship."""
    champ_id = args.championship

    try:
        config = load_config(champ_id)
    except FileNotFoundError as e:
        print_colored(f"Error: {e}", "red")
        sys.exit(1)

    print_colored(f"\nChampionship: {config.name} ({config.year})", "sand")
    print_colored(f"ID: {config.id}\n", "gray")

    # Determine what to run
    run_pipe = args.pipeline or args.bronze or args.silver or args.gold
    run_rep = args.reports
    run_all = not (args.pipeline or args.reports or args.bronze or args.silver or args.gold)

    if run_all:
        run_pipe = True
        run_rep = True

    # Pipeline stages
    if run_pipe:
        if args.bronze:
            run_raw_to_bronze(config)
        elif args.silver:
            run_bronze_to_silver(config)
        elif args.gold:
            run_silver_to_gold(config)
        else:
            run_pipeline(config)

    # Reports
    if run_rep:
        generate_html_reports(config)
        generate_dashboard(config)

        # Open dashboard in browser
        index_path = os.path.abspath(config.index_html_path())
        print_colored(f"\nOpening dashboard: {index_path}", "green")
        webbrowser.open(f"file://{index_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sweepstake CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command")

    # ss list
    list_parser = subparsers.add_parser("list", help="List available championships")
    list_parser.set_defaults(func=cmd_list)

    # ss run
    run_parser = subparsers.add_parser("run", help="Run pipeline and/or reports")
    run_parser.add_argument(
        "championship",
        help="Championship ID (e.g. a2025_club_world_cup)",
    )
    run_parser.add_argument(
        "--pipeline", action="store_true", help="Run data pipeline only"
    )
    run_parser.add_argument(
        "--reports", action="store_true", help="Generate reports only"
    )
    run_parser.add_argument(
        "--bronze", action="store_true", help="Run bronze stage only"
    )
    run_parser.add_argument(
        "--silver", action="store_true", help="Run silver stage only"
    )
    run_parser.add_argument(
        "--gold", action="store_true", help="Run gold stage only"
    )
    run_parser.set_defaults(func=cmd_run)

    # ss fetch-logos
    logos_parser = subparsers.add_parser("fetch-logos", help="Download and cache team logos")
    logos_parser.add_argument("championship", help="Championship ID (e.g. 2026_world_cup)")
    logos_parser.add_argument("--force", action="store_true", help="Redownload even if cached")
    logos_parser.set_defaults(func=cmd_fetch_logos)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
