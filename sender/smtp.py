import logging
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

log = logging.getLogger(__name__)


def send_email(html: str, subject: str, config: dict, fallback_dir: str = "logs") -> bool:
    gmail = config["gmail"]
    send_to = config["digest"]["send_to"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail["email"]
    msg["To"] = send_to
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(gmail["email"], gmail["app_password"])
            smtp.sendmail(gmail["email"], send_to, msg.as_string())
        log.info("Digest sent to %s", send_to)
        return True
    except Exception as e:
        log.error("SMTP failed: %s, saving fallback", e)
        _save_fallback(html, fallback_dir)
        return False


def _save_fallback(html: str, fallback_dir: str) -> None:
    Path(fallback_dir).mkdir(parents=True, exist_ok=True)
    path = Path(fallback_dir) / f"digest-{date.today().isoformat()}.html"
    path.write_text(html)
    log.info("Fallback saved to %s", path)
