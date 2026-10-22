from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib

from zooffer.config import settings
from zooffer.core.logging import get_logger

logger = get_logger("zooffer.email")


class EmailSender:
    async def send(self, *, to: str, subject: str, body: str) -> None:
        raise NotImplementedError


class ConsoleEmailSender(EmailSender):
    async def send(self, *, to: str, subject: str, body: str) -> None:
        # Development only: no real delivery. Do not log full bodies (may contain tokens).
        logger.info("email_console", to_domain=to.split("@")[-1], subject=subject, length=len(body))


class SmtpEmailSender(EmailSender):
    async def send(self, *, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = settings.smtp_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=True,
            timeout=10,
        )


def get_email_sender() -> EmailSender:
    if settings.email_backend == "smtp":
        return SmtpEmailSender()
    return ConsoleEmailSender()
