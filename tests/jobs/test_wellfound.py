from jobs.sources.wellfound import WellfoundSource


HTML = """
<html><body>
  <article>
    <div class="startup-name">SimForge</div>
    <a href="/jobs/ai-simulation-engineer">AI Simulation Engineer</a>
    <div class="location">Berlin, Germany</div>
  </article>
  <article>
    <div class="startup-name">RetailApp</div>
    <a href="/jobs/account-exec">Account Executive</a>
    <div class="location">Paris, France</div>
  </article>
</body></html>
"""


def test_parse_jobs_page_filters_relevant_roles():
    source = WellfoundSource({})
    jobs = source.parse_jobs_page(HTML, "https://wellfound.example")
    assert len(jobs) == 1
    assert jobs[0].company_name == "SimForge"
    assert jobs[0].country == "DE"
