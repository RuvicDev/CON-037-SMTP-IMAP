---
name: smtp-imap
description: "Usa la librería ruvic_smtp_imap_connector para enviar y leer correo con cualquier proveedor - enviar un correo por SMTP (send_email), buscar correos en la bandeja con filtros por IMAP (search_emails), y obtener el contenido completo de un correo puntual (get_email). Úsala cuando el usuario pida enviar un correo, revisar la bandeja de entrada, buscar correos de alguien específico, o leer el contenido de un mensaje. Funciona con Gmail, Microsoft 365/Outlook (vía OAuth2), o cualquier servidor de correo propio (vía usuario/contraseña)."
triggers:
- correo
- email
- smtp
- imap
- gmail
- outlook
- bandeja de entrada
- enviar correo
---

# Conector SMTP/IMAP (ruvic_smtp_imap_connector)

Librería Python de correo genérico: envía por SMTP y lee/busca por IMAP, para cualquier proveedor. Está **preinstalada en el runtime** cuando el conector está configurado (si no, instálala con `pip install git+https://github.com/tu-org/conector-smtp-imap.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de variables de entorno, disponibles cuando el conector `smtp_imap` está configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_SMTP_IMAP_EMAIL_ADDRESS` | Siempre requerida |
| `RUVIC_SMTP_IMAP_PASSWORD` / `..._SMTP_HOST` / `..._IMAP_HOST` | Si el modo es contraseña genérica |
| `RUVIC_SMTP_IMAP_GMAIL_REFRESH_TOKEN` (+ `..._GMAIL_CLIENT_ID`/`_SECRET`) | Si el modo es OAuth2 Gmail |
| `RUVIC_SMTP_IMAP_MS_REFRESH_TOKEN` (+ `..._MS_CLIENT_ID`/`_SECRET`) | Si el modo es OAuth2 Microsoft |

El código generado **NUNCA** usa nombres de variable con segmento de alias (`_DEFAULT_`, `_TEST_`, `_PRODUCCION_`, etc.) — siempre `RUVIC_SMTP_IMAP_{CAMPO}` tal cual, sin importar cuántas instancias de este conector haya configuradas. Esto aplica salvo que dichos nombres aparezcan explícitamente en una sección autogenerada al final de este skill.

Si estas variables NO existen, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en **Settings → Conectores**.

## ⚠️ Gmail y Outlook YA NO aceptan usuario/contraseña

Google desactivó la autenticación por contraseña para IMAP/SMTP en marzo de 2025, y Microsoft hizo lo mismo el 30 de abril de 2026. Si el usuario pide conectar Gmail u Outlook, **debe usarse el modo OAuth2 correspondiente** — el modo de contraseña simplemente no va a funcionar con esos dos proveedores, sin importar qué contraseña se use (ni siquiera una "contraseña de aplicación" sirve ya). El código generado nunca necesita saber cuál modo está activo — la interfaz es idéntica.

## Conexión (siempre igual)

```python
from ruvic_smtp_imap_connector import SmtpImapClient

client = SmtpImapClient()  # lee RUVIC_SMTP_IMAP_* del entorno automáticamente
```

## Capacidad 1 — Enviar un correo

```python
client.send_email(
    to="cliente@ejemplo.com",
    subject="Factura de julio",
    body_text="Adjunto la factura del mes de julio.",
)

# Con HTML y varios destinatarios:
client.send_email(
    to=["cliente@ejemplo.com", "contabilidad@ejemplo.com"],
    subject="Reporte mensual",
    body_text="Ve el reporte en el archivo adjunto.",
    body_html="<p>Ve el reporte en el archivo adjunto.</p>",
    cc="gerencia@miempresa.com",
)
```

## Capacidad 2 — Buscar correos en la bandeja con filtros

```python
# Correos no leídos de un remitente específico
resultados = client.search_emails(unread_only=True, from_address="facturas@proveedor.com")
for r in resultados:
    print(f"{r['subject']} - {r['from']} - {'no leído' if r['is_unread'] else 'leído'}")

# Buscar por texto en el asunto
resultados = client.search_emails(subject_contains="factura", limit=10)
```

## Capacidad 3 — Obtener el contenido completo de un correo

Usa el `uid` que te dio `search_emails`:

```python
correo = client.get_email(resultados[0]["uid"])
print(correo["body_text"] or correo["body_html"])
```

## Manejo de errores

```python
from ruvic_smtp_imap_connector import SmtpImapAuthError, SmtpImapNetworkError, SmtpImapDataError

try:
    client.send_email("destino@ejemplo.com", "Asunto", "Cuerpo")
except SmtpImapAuthError:
    print("Credenciales inválidas o token OAuth2 revocado — revisa la configuración del conector")
except SmtpImapNetworkError:
    print("No se pudo conectar al servidor de correo — revisa la red")
except SmtpImapDataError as e:
    print(f"Error de datos: {e}")  # ej. destinatario inválido, correo no encontrado
```

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_SMTP_IMAP_*` (el constructor de `SmtpImapClient` ya lo hace).
2. Nunca imprimas `RUVIC_SMTP_IMAP_PASSWORD` ni los `..._CLIENT_SECRET`/`..._REFRESH_TOKEN` en logs ni en la salida.
3. Antes de enviar un correo a varios destinatarios, confirma la lista con el usuario — no asumas destinatarios que no mencionó explícitamente.
4. `search_emails` sin filtros trae **todos** los correos de la carpeta — usa filtros (`unread_only`, `from_address`, `subject_contains`, `limit`) salvo que el usuario pida explícitamente "todos".
5. El campo `uid` de un correo es válido solo dentro de la misma carpeta (`folder`) — si buscas en una carpeta y luego llamas `get_email`, usa la misma carpeta en ambas llamadas.
6. No proceses adjuntos — este conector solo maneja texto/HTML del cuerpo del correo, no archivos adjuntos.
