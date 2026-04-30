from jobs.sources.stepstone import StepStoneSource


HTML = """
<html><body>
  <article>
    <a href="/job/ml-engineer">Machine Learning Engineer</a>
    <div class="location">Berlin, Germany</div>
  </article>
  <article>
    <a href="/job/sales-manager">Sales Manager</a>
    <div class="location">Hamburg, Germany</div>
  </article>
</body></html>
"""


def test_parse_jobs_page_filters_relevant_roles():
    source = StepStoneSource({})
    jobs = source.parse_jobs_page(HTML, "https://stepstone.example")
    assert len(jobs) == 1
    assert jobs[0].role_title == "Machine Learning Engineer"
    assert jobs[0].country == "DE"
