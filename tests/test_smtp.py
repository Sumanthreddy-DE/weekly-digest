from unittest.mock import MagicMock, patch

from sender.smtp import send_email

HTML = "<html><body><p>Test digest content</p></body></html>"
SUBJECT = "Weekly Digest — 2026-04-20"


@patch("sender.smtp.smtplib.SMTP_SSL")
def test_send_email_returns_true_on_success(mock_cls, config):
    mock_smtp = MagicMock()
    mock_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
    mock_cls.return_value.__exit__ = MagicMock(return_value=False)
    assert send_email(HTML, SUBJECT, config) is True
    mock_smtp.sendmail.assert_called_once()


@patch("sender.smtp.smtplib.SMTP_SSL")
def test_send_email_uses_correct_credentials(mock_cls, config):
    mock_smtp = MagicMock()
    mock_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
    mock_cls.return_value.__exit__ = MagicMock(return_value=False)
    send_email(HTML, SUBJECT, config)
    mock_smtp.login.assert_called_once_with(config["gmail"]["email"], config["gmail"]["app_password"])


@patch("sender.smtp.smtplib.SMTP_SSL")
def test_send_email_returns_false_and_saves_fallback(mock_cls, config, tmp_path):
    mock_cls.side_effect = Exception("SMTP refused")
    result = send_email(HTML, SUBJECT, config, fallback_dir=str(tmp_path))
    assert result is False
    saved = list(tmp_path.glob("*.html"))
    assert len(saved) == 1
    assert "Test digest content" in saved[0].read_text()
