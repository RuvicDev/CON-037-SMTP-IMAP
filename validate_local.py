"""Validación local del conector smtp_imap: ejercita las 3 capacidades.

Requiere las env vars RUVIC_SMTP_IMAP_* exportadas contra una cuenta de
correo de prueba (no uses una cuenta productiva). Funciona con cualquier
modo configurado (contraseña, OAuth2 Gmail, OAuth2 Microsoft).
"""

from ruvic_smtp_imap_connector import SmtpImapClient, setup_logging

setup_logging("INFO")
client = SmtpImapClient()

print("== 1. Enviar un correo de prueba (a la misma cuenta, para poder leerlo despues) ==")
resultado = client.send_email(
    to=client.config.email_address,
    subject="[Ruvic] Correo de prueba (validate_local.py)",
    body_text="Este correo fue enviado automáticamente para validar el conector.",
)
print(f"  {resultado}")

print("== 2. Buscar el correo recien enviado (puede tardar unos segundos en aparecer) ==")
import time
time.sleep(5)
resultados = client.search_emails(subject_contains="Ruvic", limit=5)
print(f"  {len(resultados)} resultado(s)")
for r in resultados:
    print(f"    {r}")

if resultados:
    print("== 3. Leer el contenido completo del primer resultado ==")
    correo = client.get_email(resultados[0]["uid"])
    print(f"  Asunto: {correo['subject']}")
    print(f"  De: {correo['from']}")
    print(f"  Cuerpo: {correo['body_text']}")
else:
    print("== 3. No se encontraron resultados para leer (el servidor puede tardar en indexar) ==")

print("\nValidación completa. Revisa manualmente tu bandeja y borra el correo de prueba si quieres.")
