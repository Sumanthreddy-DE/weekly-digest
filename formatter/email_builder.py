from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

DEGRADED_PREFIX = "[PARTIAL] "
_TEMPLATE_DIR = Path(__file__).parent
_TEMPLATE_FILE = "digest_template.html"


def build_email(newsletter_summaries: list, job_intel_summaries: list, config: dict) -> tuple:
    today = date.today().strftime("%Y-%m-%d")
    subject = f"Weekly Digest — {today}"

    all_summaries = [s.get("summary", "") for s in newsletter_summaries + job_intel_summaries]
    if any(s.startswith(DEGRADED_PREFIX) for s in all_summaries):
        subject = DEGRADED_PREFIX + subject

    de = [i for i in job_intel_summaries if i.get("location") == "DE"]
    eu = [i for i in job_intel_summaries if i.get("location") == "EU"]
    gl = [i for i in job_intel_summaries if i.get("location") == "Global"]

    env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)))
    html = env.get_template(_TEMPLATE_FILE).render(
        subject=subject,
        newsletters=newsletter_summaries,
        de_items=de,
        eu_items=eu,
        global_items=gl,
        newsletter_count=len(newsletter_summaries),
        intel_count=len(job_intel_summaries),
        de_count=len(de),
        eu_count=len(eu),
        global_count=len(gl),
    )
    return html, subject
