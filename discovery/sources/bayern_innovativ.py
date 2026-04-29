from discovery.sources.base import SourceBase


class BayernInnovativSource(SourceBase):
    name = "bayern_innovativ"
    geo_tier = "DE"
    extractor = "custom-bayern"

    def iter_pages(self, start_page: int):
        return iter(())
