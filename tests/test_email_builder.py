from formatter.email_builder import DEGRADED_PREFIX, build_email

NL = [{"subject": "AI Weekly", "sender": "ai@news.com", "date": "Mon 20 Apr", "summary": "- point 1\n- point 2"}]
JI = [
    {"title": "SimScale raises Series B", "url": "https://simscale.com", "location": "DE", "summary": "Munich-based SimScale raised EUR 20M."},
    {"title": "French CAE startup", "url": "https://cae.fr", "location": "EU", "summary": "Paris-based CAE startup hiring."},
    {"title": "US digital twin", "url": "https://us.com", "location": "Global", "summary": "US company raised funding."},
]


def test_returns_html_string(config):
    html, subject = build_email(NL, JI, config)
    assert "<html" in html.lower()
    assert "AI Weekly" in html


def test_subject_format(config):
    _, subject = build_email(NL, JI, config)
    assert "Weekly Digest" in subject


def test_de_before_eu_before_global(config):
    html, _ = build_email(NL, JI, config)
    assert html.index("SimScale") < html.index("French CAE") < html.index("US digital twin")


def test_stats_footer_present(config):
    html, _ = build_email(NL, JI, config)
    assert "1 newsletter" in html
    assert "3 companies found" in html


def test_partial_subject_prefix_when_degraded(config):
    degraded_nl = [{**NL[0], "summary": f"{DEGRADED_PREFIX}first 200 chars..."}]
    _, subject = build_email(degraded_nl, JI, config)
    assert subject.startswith(DEGRADED_PREFIX)
