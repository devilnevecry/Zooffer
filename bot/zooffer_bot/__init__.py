"""Zooffer Telegram bot.

The bot is a thin client of the shared ``zooffer`` backend services. Import the
factory functions instead of constructing global bots in tests.
"""

from __future__ import annotations

from .config import BotConfig, load_config

__all__ = ["BotConfig", "load_config"]
