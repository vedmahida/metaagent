"""
Centralized logger. Silent by default — all user-facing output
goes through terminal.py (Rich). Logger is for debug traces only.
"""
import logging
from rich.logging import RichHandler


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(message)s",
        handlers=[RichHandler(show_time=False, show_path=False)]
    )
    return logging.getLogger(name)
