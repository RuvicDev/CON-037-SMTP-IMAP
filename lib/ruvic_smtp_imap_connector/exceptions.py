"""Excepciones propias del conector SMTP/IMAP.

Separan los tipos de fallo que el usuario debe distinguir: configuración
inválida, autenticación, red, y datos (correo/carpeta inexistente, etc.).
"""


class SmtpImapConnectorError(Exception):
    """Error base del conector."""


class SmtpImapConfigError(SmtpImapConnectorError):
    """Configuración inválida: falta un campo requerido por el modo elegido."""


class SmtpImapAuthError(SmtpImapConnectorError):
    """Usuario/contraseña inválidos, o el token OAuth2 fue rechazado/revocado."""


class SmtpImapNetworkError(SmtpImapConnectorError):
    """No se pudo alcanzar el servidor de correo (DNS, timeout, conexión rechazada)."""


class SmtpImapDataError(SmtpImapConnectorError):
    """La operación es válida pero el correo/carpeta no existe, o el servidor
    rechazó la operación por una razón propia (destinatario inválido, etc.)."""
