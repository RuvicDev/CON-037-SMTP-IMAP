"""Cliente de correo genérico: enviar por SMTP, buscar y leer por IMAP.

Capacidades:
- send_email():     enviar un correo (texto y/o HTML).
- search_emails():  buscar en la bandeja con filtros (no leído, remitente,
                    asunto, fecha).
- get_email():      obtener el contenido completo de un correo puntual.

Autenticación: usuario/contraseña (o contraseña de aplicación) genérico,
u OAuth2 con usuario para Gmail o Microsoft 365/Outlook — ambos
proveedores desactivaron la autenticación por contraseña para IMAP/SMTP
(Google en marzo de 2025, Microsoft el 30 de abril de 2026), así que
"cualquier proveedor" en la práctica significa: contraseña para
servidores propios, y OAuth2 obligatorio para Gmail/Microsoft. Las
credenciales SIEMPRE provienen de variables de entorno RUVIC_SMTP_IMAP_*
(ver config.SmtpImapConfig.from_env). Prohibido hardcodearlas.
"""

from __future__ import annotations

import base64
import email
import imaplib
import smtplib
import socket
import time
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime
from typing import Any

import requests

from .config import SmtpImapConfig
from .exceptions import (
    SmtpImapAuthError,
    SmtpImapDataError,
    SmtpImapNetworkError,
)
from .logging_utils import get_logger


def _decode_mime_words(raw: str | None) -> str:
    """Decodifica encabezados de correo con codificación MIME (ej. "=?UTF-8?...?=")."""
    if not raw:
        return ""
    parts = decode_header(raw)
    decoded = []
    for text, charset in parts:
        if isinstance(text, bytes):
            decoded.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(text)
    return "".join(decoded)


class SmtpImapClient:
    """Cliente de correo autenticado con contraseña u OAuth2 (Gmail/Microsoft).

    Args:
        config: configuración de conexión. Si se omite, se lee de las
            variables de entorno RUVIC_SMTP_IMAP_* (comportamiento estándar
            en el runtime de la plataforma).

    Ejemplo:
        >>> client = SmtpImapClient()  # lee RUVIC_SMTP_IMAP_* del entorno
        >>> client.send_email("destino@ejemplo.com", "Asunto", "Cuerpo del mensaje")
    """

    def __init__(self, config: SmtpImapConfig | None = None) -> None:
        self.config = config or SmtpImapConfig.from_env()
        self._logger = get_logger()
        self._oauth_access_token: str | None = None
        self._oauth_token_expires_at: float = 0.0

    # ------------------------------------------------------------------ #
    # OAuth2: obtención/renovación de access token vía refresh_token
    # ------------------------------------------------------------------ #

    def _get_oauth_access_token(self) -> str:
        if self._oauth_access_token and time.time() < self._oauth_token_expires_at - 30:
            return self._oauth_access_token

        try:
            resp = requests.post(
                self.config.oauth_token_url,
                data={
                    "grant_type": "refresh_token",
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "refresh_token": self.config.refresh_token,
                },
                timeout=self.config.timeout,
            )
        except requests.exceptions.Timeout as exc:
            raise SmtpImapNetworkError("Tiempo de espera agotado renovando el token OAuth2.") from exc
        except requests.exceptions.ConnectionError as exc:
            raise SmtpImapNetworkError(
                f"No se pudo conectar a {self.config.oauth_token_url} para renovar el token."
            ) from exc

        if resp.status_code != 200:
            raise SmtpImapAuthError(
                f"No se pudo renovar el token OAuth2 (HTTP {resp.status_code}): {resp.text[:300]}. "
                "Puede que la autorización haya sido revocada — re-autoriza el conector en Settings → Conectores."
            )

        payload = resp.json()
        self._oauth_access_token = payload["access_token"]
        self._oauth_token_expires_at = time.time() + int(payload.get("expires_in", 3600))
        return self._oauth_access_token

    def _xoauth2_string(self) -> str:
        token = self._get_oauth_access_token()
        auth_string = f"user={self.config.email_address}\x01auth=Bearer {token}\x01\x01"
        return auth_string

    # ------------------------------------------------------------------ #
    # Conexiones SMTP / IMAP
    # ------------------------------------------------------------------ #

    def _open_smtp(self) -> smtplib.SMTP:
        try:
            smtp = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=self.config.timeout)
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            if self.config.auth_mode == "password":
                smtp.login(self.config.email_address, self.config.password)
            else:
                auth_string = self._xoauth2_string()
                smtp.docmd("AUTH", "XOAUTH2 " + base64.b64encode(auth_string.encode()).decode())
        except smtplib.SMTPAuthenticationError as exc:
            raise SmtpImapAuthError(f"Autenticación SMTP fallida: {exc}") from exc
        except (socket.timeout, TimeoutError) as exc:
            raise SmtpImapNetworkError(
                f"Tiempo de espera agotado ({self.config.timeout}s) conectando a "
                f"{self.config.smtp_host}:{self.config.smtp_port}."
            ) from exc
        except (socket.gaierror, ConnectionRefusedError, OSError) as exc:
            raise SmtpImapNetworkError(
                f"No se pudo conectar a {self.config.smtp_host}:{self.config.smtp_port}: {exc}"
            ) from exc
        return smtp

    def _open_imap(self) -> imaplib.IMAP4_SSL:
        try:
            imap = imaplib.IMAP4_SSL(self.config.imap_host, self.config.imap_port, timeout=self.config.timeout)
            if self.config.auth_mode == "password":
                imap.login(self.config.email_address, self.config.password)
            else:
                auth_string = self._xoauth2_string()
                imap.authenticate("XOAUTH2", lambda _: auth_string.encode())
        except imaplib.IMAP4.error as exc:
            raise SmtpImapAuthError(f"Autenticación IMAP fallida: {exc}") from exc
        except (socket.timeout, TimeoutError) as exc:
            raise SmtpImapNetworkError(
                f"Tiempo de espera agotado ({self.config.timeout}s) conectando a "
                f"{self.config.imap_host}:{self.config.imap_port}."
            ) from exc
        except (socket.gaierror, ConnectionRefusedError, OSError) as exc:
            raise SmtpImapNetworkError(
                f"No se pudo conectar a {self.config.imap_host}:{self.config.imap_port}: {exc}"
            ) from exc
        return imap

    # ------------------------------------------------------------------ #
    # Ping / prueba de conexión
    # ------------------------------------------------------------------ #

    def ping(self) -> bool:
        """Verifica las credenciales conectando por IMAP y seleccionando la bandeja."""
        imap = self._open_imap()
        try:
            status, _ = imap.select("INBOX", readonly=True)
            if status != "OK":
                raise SmtpImapDataError("No se pudo seleccionar la carpeta INBOX.")
        finally:
            imap.logout()
        self._logger.info("Ping exitoso a %s (%s)", self.config.imap_host, self.config.auth_mode)
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: enviar un correo
    # ------------------------------------------------------------------ #

    def send_email(
        self,
        to: str | list[str],
        subject: str,
        body_text: str,
        body_html: str | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
    ) -> dict[str, Any]:
        """Envía un correo por SMTP.

        Args:
            to: destinatario(s), un string o lista de strings.
            subject: asunto del correo.
            body_text: cuerpo en texto plano.
            body_html: cuerpo en HTML (opcional; si se da, el correo queda
                como multipart text/html con `body_text` de respaldo).
            cc: destinatarios en copia (opcional).
            bcc: destinatarios en copia oculta (opcional).

        Returns:
            Dict con "sent": True y "to" (lista de destinatarios finales).

        Ejemplo:
            >>> client.send_email("cliente@ejemplo.com", "Factura de julio", "Adjunto la factura...")
            {'sent': True, 'to': ['cliente@ejemplo.com']}
        """
        to_list = [to] if isinstance(to, str) else list(to)
        cc_list = [cc] if isinstance(cc, str) else list(cc or [])
        bcc_list = [bcc] if isinstance(bcc, str) else list(bcc or [])

        if not to_list:
            raise SmtpImapDataError("El correo necesita al menos un destinatario ('to').")

        msg = MIMEMultipart("alternative") if body_html else MIMEText(body_text, "plain", "utf-8")
        if body_html:
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        msg["Subject"] = subject
        msg["From"] = self.config.email_address
        msg["To"] = ", ".join(to_list)
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)

        all_recipients = to_list + cc_list + bcc_list

        smtp = self._open_smtp()
        try:
            smtp.sendmail(self.config.email_address, all_recipients, msg.as_string())
        except smtplib.SMTPRecipientsRefused as exc:
            raise SmtpImapDataError(f"El servidor rechazó a uno o más destinatarios: {exc}") from exc
        except smtplib.SMTPException as exc:
            raise SmtpImapDataError(f"No se pudo enviar el correo: {exc}") from exc
        finally:
            smtp.quit()

        self._logger.info("Correo enviado a %s (asunto: %r)", all_recipients, subject)
        return {"sent": True, "to": to_list}

    # ------------------------------------------------------------------ #
    # Capacidad 2: buscar correos en la bandeja con filtros
    # ------------------------------------------------------------------ #

    def search_emails(
        self,
        folder: str = "INBOX",
        unread_only: bool = False,
        from_address: str | None = None,
        subject_contains: str | None = None,
        since_date: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Busca correos en una carpeta, con filtros combinables.

        Args:
            folder: carpeta a buscar (default "INBOX").
            unread_only: si es True, solo trae correos no leídos.
            from_address: filtra por remitente (coincidencia parcial).
            subject_contains: filtra por texto en el asunto.
            since_date: fecha mínima en formato "DD-Mon-YYYY" (ej. "01-Jan-2026").
            limit: máximo de resultados (default 20, los más recientes primero).

        Returns:
            Lista de dicts con "uid", "subject", "from", "date", "is_unread".

        Ejemplo:
            >>> client.search_emails(unread_only=True, from_address="facturas@proveedor.com")
            [{'uid': '123', 'subject': 'Factura #456', 'from': 'facturas@proveedor.com', ...}]
        """
        imap = self._open_imap()
        try:
            status, _ = imap.select(folder, readonly=True)
            if status != "OK":
                raise SmtpImapDataError(f"No se pudo abrir la carpeta {folder!r}.")

            criteria = []
            if unread_only:
                criteria.append("UNSEEN")
            if from_address:
                criteria.append(f'FROM "{from_address}"')
            if subject_contains:
                criteria.append(f'SUBJECT "{subject_contains}"')
            if since_date:
                criteria.append(f"SINCE {since_date}")
            search_query = " ".join(criteria) if criteria else "ALL"

            status, data = imap.search(None, search_query)
            if status != "OK":
                raise SmtpImapDataError(f"Búsqueda IMAP inválida: {search_query!r}")

            uids = data[0].split()
            uids = uids[-limit:] if limit else uids
            uids.reverse()  # más recientes primero

            results = []
            for uid in uids:
                status, msg_data = imap.fetch(uid, "(FLAGS BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue
                flags_raw = msg_data[0][0].decode(errors="replace") if isinstance(msg_data[0], tuple) else ""
                header_bytes = msg_data[0][1] if isinstance(msg_data[0], tuple) else b""
                parsed = email.message_from_bytes(header_bytes)
                results.append({
                    "uid": uid.decode(),
                    "subject": _decode_mime_words(parsed.get("Subject")),
                    "from": _decode_mime_words(parsed.get("From")),
                    "date": parsed.get("Date"),
                    "is_unread": "\\Seen" not in flags_raw,
                })
        finally:
            imap.logout()

        self._logger.info("search_emails %s: %d resultado(s)", folder, len(results))
        return results

    # ------------------------------------------------------------------ #
    # Capacidad 3: obtener el contenido completo de un correo
    # ------------------------------------------------------------------ #

    def get_email(self, uid: str, folder: str = "INBOX") -> dict[str, Any]:
        """Obtiene el contenido completo de un correo puntual.

        Args:
            uid: identificador del correo (obtenido de `search_emails`).
            folder: carpeta donde está el correo (default "INBOX").

        Returns:
            Dict con "uid", "subject", "from", "to", "date", "body_text",
            "body_html" (None si no tiene versión HTML).

        Ejemplo:
            >>> client.get_email("123")
            {'uid': '123', 'subject': '...', 'from': '...', 'body_text': '...', ...}
        """
        imap = self._open_imap()
        try:
            status, _ = imap.select(folder, readonly=True)
            if status != "OK":
                raise SmtpImapDataError(f"No se pudo abrir la carpeta {folder!r}.")

            status, msg_data = imap.fetch(uid.encode() if isinstance(uid, str) else uid, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                raise SmtpImapDataError(f"Correo no encontrado: uid={uid!r} en {folder!r}")

            raw_bytes = msg_data[0][1]
            parsed = email.message_from_bytes(raw_bytes)

            body_text, body_html = None, None
            if parsed.is_multipart():
                for part in parsed.walk():
                    content_type = part.get_content_type()
                    disposition = str(part.get("Content-Disposition", ""))
                    if "attachment" in disposition:
                        continue
                    if content_type == "text/plain" and body_text is None:
                        body_text = part.get_payload(decode=True).decode(
                            part.get_content_charset() or "utf-8", errors="replace"
                        )
                    elif content_type == "text/html" and body_html is None:
                        body_html = part.get_payload(decode=True).decode(
                            part.get_content_charset() or "utf-8", errors="replace"
                        )
            else:
                payload = parsed.get_payload(decode=True)
                text = payload.decode(parsed.get_content_charset() or "utf-8", errors="replace")
                if parsed.get_content_type() == "text/html":
                    body_html = text
                else:
                    body_text = text

            result = {
                "uid": uid if isinstance(uid, str) else uid.decode(),
                "subject": _decode_mime_words(parsed.get("Subject")),
                "from": _decode_mime_words(parsed.get("From")),
                "to": _decode_mime_words(parsed.get("To")),
                "date": parsed.get("Date"),
                "body_text": body_text,
                "body_html": body_html,
            }
        finally:
            imap.logout()

        self._logger.info("get_email %s: OK", uid)
        return result
