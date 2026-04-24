import email
import imaplib
import logging
from datetime import datetime, timezone, timedelta
from email.header import decode_header as _decode_header_raw

from bs4 import BeautifulSoup

log = logging.getLogger(__name__)


def _decode_header(value: str) -> str:
    parts = _decode_header_raw(value)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def _strip_html(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)


def _get_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            text = payload.decode("utf-8", errors="replace")
            if ct == "text/plain":
                return text
            if ct == "text/html":
                return _strip_html(text)
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            raw = payload.decode("utf-8", errors="replace")
            return _strip_html(raw) if "<html" in raw.lower() else raw
    return ""


def _since_date(state: dict, default_days: int) -> str:
    last = state.get("last_successful_delivery")
    if last:
        dt = datetime.fromisoformat(last.replace("Z", "+00:00")) - timedelta(days=1)
    else:
        dt = datetime.now(timezone.utc) - timedelta(days=default_days)
    return dt.strftime("%d-%b-%Y")


def fetch_newsletters(config: dict, state: dict) -> list:
    gmail = config["gmail"]
    senders = config["newsletters"]["senders"]
    existing_ids = {i["id"] for i in state.get("items", [])}
    since = _since_date(state, config["state"]["default_lookback_days"])
    results = []

    with imaplib.IMAP4_SSL(gmail["imap_server"]) as imap:
        imap.login(gmail["email"], gmail["app_password"])
        imap.select("INBOX")
        for sender in senders:
            _, data = imap.search(None, f'(FROM "{sender}" SINCE "{since}")')
            if not data or not data[0]:
                continue
            for num in data[0].split():
                _, raw_data = imap.fetch(num, "(RFC822)")
                if not raw_data or not raw_data[0]:
                    continue
                raw = raw_data[0][1] if isinstance(raw_data[0], tuple) else raw_data[0]
                msg = email.message_from_bytes(raw)
                msg_id = msg.get("Message-ID", "").strip()
                if not msg_id or msg_id in existing_ids:
                    continue
                results.append({
                    "id": msg_id,
                    "type": "newsletter",
                    "sender": sender,
                    "subject": _decode_header(msg.get("Subject", "")),
                    "date": msg.get("Date", ""),
                    "body": _get_body(msg),
                })
    log.info("Fetched %d new newsletters", len(results))
    return results
