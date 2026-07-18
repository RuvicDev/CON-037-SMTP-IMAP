# conector-smtp-imap

Conector Ruvic de correo genérico: **enviar por SMTP** y **buscar/leer por IMAP**, para cualquier proveedor.

## Capacidades

`send_email`, `search_emails` (con filtros: no leído, remitente, asunto, fecha), `get_email` (contenido completo de un correo puntual).

## ⚠️ Gmail y Outlook ya no aceptan usuario/contraseña

- **Google** desactivó la autenticación por contraseña para IMAP/SMTP en **marzo de 2025**.
- **Microsoft** desactivó la autenticación básica para SMTP en Exchange Online/Outlook.com el **30 de abril de 2026**.

Esto significa que **"cualquier proveedor" en la práctica es dos categorías**: servidores de correo propios/otros proveedores que todavía permiten contraseña (modo `password`), y Gmail/Microsoft que **requieren OAuth2 obligatoriamente** (modos `oauth2_gmail`/`oauth2_microsoft`). No hay forma de usar contraseña con Gmail u Outlook hoy, ni siquiera con "contraseñas de aplicación".

## Instalación

Requiere **Python ≥ 3.10**.

```bash
pip install git+https://github.com/tu-org/conector-smtp-imap.git#subdirectory=lib
```

Para desarrollo local (editable, en un venv limpio):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib
```

## Variables de entorno

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_SMTP_IMAP_EMAIL_ADDRESS` | Sí | Siempre requerida |
| `RUVIC_SMTP_IMAP_PASSWORD` / `..._SMTP_HOST` / `..._SMTP_PORT` / `..._IMAP_HOST` / `..._IMAP_PORT` | Si modo contraseña | Servidor propio u otro proveedor |
| `RUVIC_SMTP_IMAP_GMAIL_REFRESH_TOKEN` / `..._GMAIL_CLIENT_ID` / `..._GMAIL_CLIENT_SECRET` | Si modo OAuth2 Gmail | — |
| `RUVIC_SMTP_IMAP_MS_REFRESH_TOKEN` / `..._MS_CLIENT_ID` / `..._MS_CLIENT_SECRET` | Si modo OAuth2 Microsoft | — |
| `RUVIC_SMTP_IMAP_REQUEST_TIMEOUT` | No | Segundos, default `20` |

El modo se detecta automáticamente según qué variables estén presentes.

## Permisos / prerrequisitos

### Modo contraseña (servidor propio u otro proveedor)
- Cuenta de correo dedicada a esta integración, con SMTP y IMAP habilitados en el servidor.
- Si el proveedor lo requiere, genera una **contraseña de aplicación** en vez de usar la contraseña principal de la cuenta.

### Modo OAuth2 Gmail
- Un proyecto en **Google Cloud Console** con la API de Gmail habilitada.
- Un **OAuth Client ID** (tipo "Web application") con la Redirect URI de la plataforma registrada.
- Scope solicitado: `https://mail.google.com/` (acceso completo de correo, necesario para SMTP+IMAP vía XOAUTH2).

### Modo OAuth2 Microsoft
- Una app registrada en **Microsoft Entra ID** (antes Azure AD).
- Scopes: `https://outlook.office365.com/SMTP.Send`, `https://outlook.office365.com/IMAP.AccessAsUser.All`, `offline_access` (para el refresh token).
- El tenant/cuenta debe tener **SMTP AUTH habilitado** — Microsoft lo desactiva por defecto en cuentas nuevas; puede requerir que un administrador lo active explícitamente para el buzón.

## Cómo correr las pruebas locales

```bash
export RUVIC_SMTP_IMAP_EMAIL_ADDRESS=pruebas@tudominio.com
export RUVIC_SMTP_IMAP_PASSWORD=xxxxxxxx
export RUVIC_SMTP_IMAP_SMTP_HOST=smtp.tudominio.com
export RUVIC_SMTP_IMAP_IMAP_HOST=imap.tudominio.com

python test_connection.py
python validate_local.py
```

Prueba también el caso de error:

```bash
RUVIC_SMTP_IMAP_PASSWORD=incorrecta python test_connection.py
# FALLO: Autenticación fallida: ...
```

## Limitaciones conocidas

- No maneja adjuntos (ni para enviar ni para leer) — solo el cuerpo en texto/HTML.
- No implementa mover, archivar, ni eliminar correos.
- `search_emails` usa la sintaxis de búsqueda estándar de IMAP — filtros combinados usan lógica "Y" (AND), no hay soporte para "O" (OR) entre filtros.
- El límite de resultados (`limit`) se aplica sobre los correos más recientes que cumplen el filtro, no es una paginación real.

## Notas de integración

- El paquete pip es `ruvic-smtp-imap-connector`; el import name es `ruvic_smtp_imap_connector`.
- Dependencia externa: `requests` (solo para el refresh de tokens OAuth2). SMTP/IMAP usan `smtplib`/`imaplib` de la librería estándar de Python.
- Ver `SKILL.md` para los ejemplos de uso que consume el agente.
