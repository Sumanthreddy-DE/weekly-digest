import logging

from apify_client import ApifyClient

log = logging.getLogger(__name__)


class ApifyFetchError(Exception):
    pass


def _build_queries(config: dict) -> list:
    return [
        f"{sector} {signal}"
        for sector in config["keywords"]["sectors"]
        for signal in config["keywords"]["signals"]
    ]


def fetch_via_apify(config: dict) -> list:
    apify_cfg = config["apify"]
    queries = _build_queries(config)
    try:
        client = ApifyClient(apify_cfg["api_token"])
        run = client.actor(apify_cfg["actor_id"]).call(
            run_input={"search_queries": queries},
            timeout_secs=apify_cfg["timeout_secs"],
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        log.info("Apify: fetched %d items", len(items))
        return items
    except Exception as e:
        raise ApifyFetchError(f"Apify fetch failed: {e}") from e
