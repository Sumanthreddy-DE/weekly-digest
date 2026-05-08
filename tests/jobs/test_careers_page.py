from jobs.sources.careers_page import CareersPageSource


HTML = """
<html><body>
  <a href="/jobs/ml-engineer">Machine Learning Engineer</a>
  <a href="/jobs/backend-dev">Backend Developer</a>
  <a href="/jobs/simulation-engineer">Simulation Engineer</a>
</body></html>
"""


def _config():
    return {"jobs": {}}


def test_parse_jobs_page_extracts_relevant_roles():
    source = CareersPageSource(_config(), [{"name": "SimForge", "homepage": "https://simforge.example", "country": "DE", "city": "Berlin"}])
    jobs = source.parse_jobs_page(
        HTML,
        {"name": "SimForge", "homepage": "https://simforge.example", "country": "DE", "city": "Berlin"},
        "https://simforge.example/careers",
    )
    assert len(jobs) == 2
    assert jobs[0].company_name == "SimForge"
    assert jobs[0].country == "DE"


def test_looks_like_job():
    assert CareersPageSource._looks_like_job("Machine Learning Engineer") is True
    assert CareersPageSource._looks_like_job("Simulation Engineer") is True
    assert CareersPageSource._looks_like_job("Office Manager") is False
