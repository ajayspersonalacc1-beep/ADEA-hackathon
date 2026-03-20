"""Run the ADEA natural language CLI interface."""

from __future__ import annotations

import argparse

from adea.interface.cli_agent import run_cli_agent


def main() -> None:
    """Run the ADEA CLI or demo mode."""

    parser = argparse.ArgumentParser(description="Run the ADEA CLI.")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run the canned ADEA demo scenario.",
    )
    args = parser.parse_args()
    run_cli_agent(demo=args.demo)


if __name__ == "__main__":
    main()
