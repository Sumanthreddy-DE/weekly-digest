from unittest.mock import MagicMock, patch

from collector.newsletters import fetch_newsletters

SAMPLE_RAW_EMAIL = (
    b"From: sender@example.com\r\n"
    b"Subject: Test Newsletter\r\n"
    b"Date: Mon, 20 Apr 2026 10:00:00 +0000\r\n"
    b"Message-ID: <test-msg-1@example>\r\n\r\n"
    b"<html><body><p>Hello <b>world</b>.</p></body></html>"
)


def _make_imap(raw_email):
    imap = MagicMock()
    imap.search.return_value = ("OK", [b"1"])
    imap.fetch.return_value = ("OK", [(b"1 (RFC822 {1234}", raw_email)])
    imap.select.return_value = ("OK", [])
    imap.login.return_value = ("OK", [])
    return imap


@patch("collector.newsletters.imaplib.IMAP4_SSL")
def test_fetch_newsletters_returns_list(mock_cls, config):
    mock_imap = _make_imap(SAMPLE_RAW_EMAIL)
    mock_cls.return_value.__enter__ = MagicMock(return_value=mock_imap)
    mock_cls.return_value.__exit__ = MagicMock(return_value=False)
    state = {"last_successful_delivery": None, "items": []}
    result = fetch_newsletters(config, state)
    assert isinstance(result, list)


@patch("collector.newsletters.imaplib.IMAP4_SSL")
def test_fetch_newsletters_strips_html(mock_cls, config):
    mock_imap = _make_imap(SAMPLE_RAW_EMAIL)
    mock_cls.return_value.__enter__ = MagicMock(return_value=mock_imap)
    mock_cls.return_value.__exit__ = MagicMock(return_value=False)
    state = {"last_successful_delivery": None, "items": []}
    result = fetch_newsletters(config, state)
    if result:
        assert "<html>" not in result[0]["body"]
        assert "Hello" in result[0]["body"]


@patch("collector.newsletters.imaplib.IMAP4_SSL")
def test_fetch_newsletters_deduplicates_against_state(mock_cls, config):
    mock_imap = _make_imap(SAMPLE_RAW_EMAIL)
    mock_cls.return_value.__enter__ = MagicMock(return_value=mock_imap)
    mock_cls.return_value.__exit__ = MagicMock(return_value=False)
    state = {
        "last_successful_delivery": None,
        "items": [{"id": "<test-msg-1@example>", "type": "newsletter", "state": "delivered", "discovered_at": "2026-04-13T07:00:00Z", "delivered_at": "2026-04-13T08:00:00Z"}],
    }
    result = fetch_newsletters(config, state)
    assert all(r["id"] != "<test-msg-1@example>" for r in result)
