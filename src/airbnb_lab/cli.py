"""Command line entry point; paths are relative to --root."""
import argparse
import logging
from pathlib import Path
from .ingest import ingest, load_config


def main():
    parser = argparse.ArgumentParser(description="Inside Airbnb portfolio pipeline")
    parser.add_argument("command", choices=["ingest", "run"])
    parser.add_argument("--config", default="configs/albany.json")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--offline", action="store_true", help="Use checksum-verified raw files only")
    parser.add_argument("--force", action="store_true", help="Rebuild outputs even if unchanged")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = args.root / config_path
    config = load_config(config_path)
    if args.command == "ingest":
        ingest(config, args.root, args.offline)
    else:
        from .pipeline import run
        run(config, args.root, args.offline, args.force)


if __name__ == "__main__":
    main()
