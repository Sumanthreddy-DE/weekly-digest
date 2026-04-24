from unittest.mock import MagicMock, patch


import main


@patch("main.send_email", return_value=True)
@patch("main.build_email", return_value=("<html/>", "Weekly Digest — 2026-04-20"))
@patch("main.summarize_job_intel", return_value=[])
@patch("main.summarize_newsletters", return_value=[])
@patch("main.fetch_job_intel", return_value=[])
@patch("main.fetch_newsletters", return_value=[])
@patch("main.save_state")
@patch("main.load_state", return_value={"last_successful_delivery": None, "items": []})
@patch("main.load_config")
def test_full_pipeline_runs_without_error(mock_cfg, mock_load, mock_save, mock_fetch_newsletters, mock_fetch_job_intel, mock_summarize_newsletters, mock_summarize_job_intel, mock_build_email, mock_send_email, config):
    mock_cfg.return_value = config
    with patch("main.acquire_lock") as mock_lock:
        mock_lock.return_value.__enter__ = MagicMock(return_value=None)
        mock_lock.return_value.__exit__ = MagicMock(return_value=False)
        main.run()
    mock_save.assert_called()


@patch("main.send_email", return_value=False)
@patch("main.build_email", return_value=("<html/>", "Weekly Digest — 2026-04-20"))
@patch("main.summarize_job_intel", return_value=[])
@patch("main.summarize_newsletters", return_value=[])
@patch("main.fetch_job_intel", return_value=[])
@patch("main.fetch_newsletters", return_value=[])
@patch("main.save_state")
@patch("main.load_state", return_value={"last_successful_delivery": None, "items": []})
@patch("main.load_config")
def test_state_not_marked_delivered_on_send_failure(mock_cfg, mock_load, mock_save, mock_fetch_newsletters, mock_fetch_job_intel, mock_summarize_newsletters, mock_summarize_job_intel, mock_build_email, mock_send_email, config):
    mock_cfg.return_value = config
    with patch("main.acquire_lock") as mock_lock:
        mock_lock.return_value.__enter__ = MagicMock(return_value=None)
        mock_lock.return_value.__exit__ = MagicMock(return_value=False)
        main.run()
    assert mock_save.call_count == 1
    saved = mock_save.call_args[0][2]
    assert saved["last_successful_delivery"] is None
