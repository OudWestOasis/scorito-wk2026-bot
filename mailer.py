"""
E-mail versturen via SMTP (provider-onafhankelijk).

Gegevens komen uit Secrets/env (zie config.py):
  EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_USER, EMAIL_PASS, EMAIL_FROM, EMAIL_TO

Werkt met elke SMTP-server (Gmail, Outlook/Office365, of een mail-API met
SMTP zoals Brevo/SendGrid). Poort 465 = SSL, anders STARTTLS (bv. 587).
"""
import smtplib
from email.message import EmailMessage

import config


def send_email(subject: str, html: str, text: str) -> None:
    host = config.require("EMAIL_SMTP_HOST")
    user = config.require("EMAIL_USER")
    pwd = config.require("EMAIL_PASS")
    port = config.EMAIL_SMTP_PORT

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.EMAIL_FROM or user
    msg["To"] = config.EMAIL_TO
    msg.set_content(text)                       # platte-tekst fallback
    msg.add_alternative(html, subtype="html")   # nette HTML-versie

    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=30) as s:
            s.login(user, pwd)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.ehlo()
            s.starttls()
            s.login(user, pwd)
            s.send_message(msg)
