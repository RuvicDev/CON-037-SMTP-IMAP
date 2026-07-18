"""Conector Ruvic de correo genérico (SMTP + IMAP)."""

from .client import SmtpImapClient
from .config import ENV_PREFIX, SmtpImapConfig
from .exceptions import (
    SmtpImapAuthError,
    SmtpImapConfigError,
    SmtpImapConnectorError,
    SmtpImapDataError,
    SmtpImapNetworkError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "SmtpImapAuthError",
    "SmtpImapClient",
    "SmtpImapConfig",
    "SmtpImapConfigError",
    "SmtpImapConnectorError",
    "SmtpImapDataError",
    "SmtpImapNetworkError",
    "setup_logging",
]

__version__ = "1.0.0"
