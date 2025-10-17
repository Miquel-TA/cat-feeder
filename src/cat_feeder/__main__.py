from __future__ import annotations

import argparse
import logging
from pathlib import Path

import uvicorn

from .server import create_app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cat Feeder overlay server")
    parser.add_argument(
        "--settings",
        type=Path,
        default=None,
        help="Path to settings JSON file (defaults to config/settings.json)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=8000, help="TCP port to bind")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    args = parse_args()
    app = create_app(args.settings)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

