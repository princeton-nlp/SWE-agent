"""Main command line interface for SWE-agent.
Specify one of the subcommands.
"""

import argparse
import sys


def get_cli():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "command",
        choices=["run", "run-batch", "run-replay", "traj-to-demo", "run-api", "merge-preds", "inspector"],
        nargs="?",
    )
    parser.add_argument("-h", "--help", action="store_true", help="Show this help message and exit")
    return parser


def main(args: list[str] | None = None):
    if args is None:
        args = sys.argv[1:]
    cli = get_cli()
    parsed_args, remaining_args = cli.parse_known_args(args)  # type: ignore
    command = parsed_args.command
    show_help = parsed_args.help
    if show_help:
        if not command:
            # Show main help
            cli.print_help()
            sys.exit(0)
        else:
            # Add to remaining_args
            remaining_args.append("--help")
    elif not command:
        cli.print_help()
        sys.exit(2)
    # Defer imports to avoid unnecessary long loading times
    if command == "run":
        from sweagent.run.run_single import run_from_cli as run_single_main

        run_single_main(remaining_args)
    elif command == "run-batch":
        from sweagent.run.run_batch import run_from_cli as run_batch_main

        run_batch_main(remaining_args)
    elif command == "run-replay":
        from sweagent.run.run_replay import run_from_cli as run_replay_main

        run_replay_main(remaining_args)
    elif command == "traj-to-demo":
        from sweagent.run.run_traj_to_demo import run_from_cli as convert_traj_to_demo_main

        convert_traj_to_demo_main(remaining_args)
    elif command == "run-api":
        from sweagent.api.server import run_from_cli as run_api_main

        run_api_main(remaining_args)
    elif command == "merge-preds":
        from sweagent.run.merge_predictions import run_from_cli as merge_predictions_main

        merge_predictions_main(remaining_args)
    elif command == "inspector":
        from sweagent.inspector.server import run_from_cli as inspector_main

        inspector_main(remaining_args)
    else:
        msg = f"Unknown command: {command}"
        raise ValueError(msg)


if __name__ == "__main__":
    main()
