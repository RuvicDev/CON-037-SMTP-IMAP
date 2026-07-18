"""Prueba de conexión estándar del conector smtp_imap.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_SMTP_IMAP_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Verifica el acceso IMAP usando las env vars RUVIC_SMTP_IMAP_*."""
    try:
        from ruvic_smtp_imap_connector import (
            SmtpImapAuthError,
            SmtpImapClient,
            SmtpImapDataError,
            SmtpImapNetworkError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-smtp-imap-connector no está instalada. "
            "Instala con: pip install git+https://github.com/tu-org/"
            "conector-smtp-imap.git#subdirectory=lib",
        )

    try:
        client = SmtpImapClient()  # valida config y credenciales del modo detectado
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except SmtpImapAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except SmtpImapNetworkError as exc:
        return False, f"Error de red: {exc}"
    except SmtpImapDataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    return True, f"Conexión exitosa a {client.config.imap_host} (modo: {client.config.auth_mode})"


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
