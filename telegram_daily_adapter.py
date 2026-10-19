"""Opt-in Telegram daily report adapter. Paper trading only."""

import os

import bot
from daily_sender import DailySender


def send_daily_report(database_path, day, *, allow_network=False):
    """Send only with two explicit opt-ins.

    No scheduler is installed by this module.
    """

    enabled = (
        os.getenv("DAILY_REPORT_TELEGRAM_ENABLED", "false").lower()
        == "true"
    )

    if not enabled or not allow_network:
        return "disabled"

    sender = DailySender(database_path)

    try:
        if sender.status(day) is not None:
            return sender.status(day)

        def notify(message):
            # Existing project's Telegram sender.
            # Exceptions must propagate to preserve pending state.
            result = bot.notify(message, telegram=True)

            if result is False:
                raise RuntimeError("Telegram delivery not confirmed")

        delivered = sender.send(day, notify)

        if delivered:
            return "sent"

        return sender.status(day) or "not_sent"

    finally:
        sender.close()
