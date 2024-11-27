import argparse
import json
from pathlib import Path

from sweagent.utils.log import get_logger

"""Merge multiple predictions into a single file."""


logger = get_logger("merge", emoji="➕")


def merge_predictions(directory: Path, output: Path | None = None) -> None:
    """Merge predictions found in `directory` into a single JSON file.

    Args:
        directory: Directory containing predictions.
        output: Output file. If not provided, the merged predictions will be
            written to `directory/preds.json`.
    """
    preds = list(directory.glob("*.pred"))
    logger.info("Found %d predictions", len(preds))
    if not preds:
        logger.warning("No predictions found in %s", directory)
        return
    if output is None:
        output = directory / "preds.json"
    data = {}
    for pred in preds:
        _data = json.loads(pred.read_text())
        instance_id = _data["instance_id"]
        data[instance_id] = _data
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data))
    logger.info("Wrote merged predictions to %s", output)


def get_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Directory containing predictions")
    parser.add_argument("--output", type=Path, help="Output file")
    return parser


def run_from_cli(args: list[str] | None = None) -> None:
    cli_parser = get_cli_parser()
    cli_args = cli_parser.parse_args(args)
    merge_predictions(cli_args.directory, cli_args.output)


if __name__ == "__main__":
    run_from_cli()
