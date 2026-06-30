"""
main.py — Entry point for Treasure Hunter AI.

Run with:
    python main.py
"""

from __future__ import annotations

import sys

from utils.logger import setup_logging

# Set up logging before importing anything that uses a logger
setup_logging()

import logging  # noqa: E402 (import after logging config)

logger = logging.getLogger(__name__)


def main() -> None:
    """Bootstrap the game and start the main loop."""
    logger.info("=" * 60)
    logger.info("  Treasure Hunter AI — starting up")
    logger.info("=" * 60)

    try:
        from core.game import Game  # noqa: PLC0415 (lazy import after logging)
        game = Game()
        game.run()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received — exiting cleanly.")
    except Exception:
        logger.exception("Fatal error during game execution.")
        sys.exit(1)


if __name__ == "__main__":
    main()
