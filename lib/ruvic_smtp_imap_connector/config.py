"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_SMTP_IMAP_.

Soporta tres modos, detectados automáticamente por las variables presentes:
- "password": usuario/contraseña (o contraseña de aplicación) genérico,
  para servidores de correo propios o proveedores que aún lo permiten.
  Requiere PASSWORD.
- "oauth2_gmail": OAuth2 con usuario para Gmail/Google Workspace (Google
  desactivó la autenticación por contraseña para IMAP/SMTP en marzo de
  2025). Requiere GMAIL_REFRESH_TOKEN.
- "oauth2_microsoft": OAuth2 con usuario para Outlook/Microsoft 365
  (Microsoft desactivó la autenticación básica por SMTP el 30 de abril
  de 2026). Requiere MS_REFRESH_TOKEN.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_PREFIX = "RUVIC_SMTP_IMAP_"

_GMAIL_SMTP_HOST, _GMAIL_SMTP_PORT = "smtp.gmail.com", 587
_GMAIL_IMAP_HOST, _GMAIL_IMAP_PORT = "imap.gmail.com", 993
_GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"

_MS_SMTP_HOST, _MS_SMTP_PORT = "smtp.office365.com", 587
_MS_IMAP_HOST, _MS_IMAP_PORT = "outlook.office365.com", 993
_MS_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"


@dataclass(frozen=True)
class SmtpImapConfig:
    """Parámetros de conexión a un servidor de correo por SMTP/IMAP."""

    auth_mode: str  # "password" | "oauth2_gmail" | "oauth2_microsoft"
    email_address: str
    smtp_host: str
    smtp_port: int
    imap_host: str
    imap_port: int
    password: str = ""
    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""
    oauth_token_url: str = ""
    timeout: int = 20

    @classmethod
    def from_env(cls) -> "SmtpImapConfig":
        """Construye la configuración desde las variables RUVIC_SMTP_IMAP_*.

        Detecta el modo automáticamente: GMAIL_REFRESH_TOKEN presente ->
        OAuth2 Gmail; si no, MS_REFRESH_TOKEN presente -> OAuth2 Microsoft;
        si no, PASSWORD presente -> genérico.

        Raises:
            ValueError: si falta EMAIL_ADDRESS, o las credenciales del
                modo detectado.
        """
        email_address = os.environ.get(f"{ENV_PREFIX}EMAIL_ADDRESS", "").strip()
        if not email_address:
            raise ValueError(
                f"Falta la variable de entorno del conector smtp_imap: "
                f"{ENV_PREFIX}EMAIL_ADDRESS. Configura el conector en Settings → Conectores."
            )

        timeout = int(os.environ.get(f"{ENV_PREFIX}REQUEST_TIMEOUT", "20"))

        gmail_refresh = os.environ.get(f"{ENV_PREFIX}GMAIL_REFRESH_TOKEN", "").strip()
        ms_refresh = os.environ.get(f"{ENV_PREFIX}MS_REFRESH_TOKEN", "").strip()
        password = os.environ.get(f"{ENV_PREFIX}PASSWORD", "").strip()

        if gmail_refresh:
            client_id = os.environ.get(f"{ENV_PREFIX}GMAIL_CLIENT_ID", "")
            client_secret = os.environ.get(f"{ENV_PREFIX}GMAIL_CLIENT_SECRET", "")
            if not client_id or not client_secret:
                raise ValueError(
                    f"El modo OAuth2 Gmail requiere {ENV_PREFIX}GMAIL_CLIENT_ID y "
                    f"{ENV_PREFIX}GMAIL_CLIENT_SECRET además de {ENV_PREFIX}GMAIL_REFRESH_TOKEN."
                )
            return cls(
                auth_mode="oauth2_gmail",
                email_address=email_address,
                smtp_host=_GMAIL_SMTP_HOST, smtp_port=_GMAIL_SMTP_PORT,
                imap_host=_GMAIL_IMAP_HOST, imap_port=_GMAIL_IMAP_PORT,
                client_id=client_id, client_secret=client_secret,
                refresh_token=gmail_refresh, oauth_token_url=_GMAIL_TOKEN_URL,
                timeout=timeout,
            )

        if ms_refresh:
            client_id = os.environ.get(f"{ENV_PREFIX}MS_CLIENT_ID", "")
            client_secret = os.environ.get(f"{ENV_PREFIX}MS_CLIENT_SECRET", "")
            if not client_id or not client_secret:
                raise ValueError(
                    f"El modo OAuth2 Microsoft requiere {ENV_PREFIX}MS_CLIENT_ID y "
                    f"{ENV_PREFIX}MS_CLIENT_SECRET además de {ENV_PREFIX}MS_REFRESH_TOKEN."
                )
            return cls(
                auth_mode="oauth2_microsoft",
                email_address=email_address,
                smtp_host=_MS_SMTP_HOST, smtp_port=_MS_SMTP_PORT,
                imap_host=_MS_IMAP_HOST, imap_port=_MS_IMAP_PORT,
                client_id=client_id, client_secret=client_secret,
                refresh_token=ms_refresh, oauth_token_url=_MS_TOKEN_URL,
                timeout=timeout,
            )

        if password:
            smtp_host = os.environ.get(f"{ENV_PREFIX}SMTP_HOST", "").strip()
            imap_host = os.environ.get(f"{ENV_PREFIX}IMAP_HOST", "").strip()
            if not smtp_host or not imap_host:
                raise ValueError(
                    f"El modo de contraseña requiere {ENV_PREFIX}SMTP_HOST y {ENV_PREFIX}IMAP_HOST."
                )
            return cls(
                auth_mode="password",
                email_address=email_address,
                smtp_host=smtp_host,
                smtp_port=int(os.environ.get(f"{ENV_PREFIX}SMTP_PORT", "587")),
                imap_host=imap_host,
                imap_port=int(os.environ.get(f"{ENV_PREFIX}IMAP_PORT", "993")),
                password=password,
                timeout=timeout,
            )

        raise ValueError(
            f"Falta una credencial válida del conector smtp_imap: define "
            f"{ENV_PREFIX}PASSWORD (genérico), {ENV_PREFIX}GMAIL_REFRESH_TOKEN "
            f"(OAuth2 Gmail), o {ENV_PREFIX}MS_REFRESH_TOKEN (OAuth2 Microsoft)."
        )
