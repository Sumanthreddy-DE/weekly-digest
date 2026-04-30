from jobs.sources.otta import OttaSource


HTML = """
<html><body>
  <article>
    <div class="company-name">TwinWorks</div>
    <a href="/jobs/ml-platform-engineer">ML Platform Engineer</a>
    <div class="location">Berlin, Germany</div>
  </article>
  <article>
    <div class="company-name">FunCo</div>
    <a href="/jobs/marketing-manager">Marketing Manager</a>
    <div class="location">Remote</div>
  </article>
</body></html>
"""


def test_parse_jobs_page_filters_relevant_roles():
    source = OttaSource({})
    jobs = source.parse_jobs_page(HTML, "https://otta.example")
    assert len(jobs) == 1
    assert jobs[0].company_name == "TwinWorks"
    assert jobs[0].country == "DE"
