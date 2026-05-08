from discovery.sources.base import SourceBase


class GoogleNewsSource(SourceBase):
    def __init__(self, config: dict, geo: str):
        super().__init__(config)
        self.geo = geo
        self.name = "google_news_de" if geo == "DE" else "google_news_en"
        self.extractor = "google-news-de" if geo == "DE" else "google-news-en"

    def iter_pages(self, start_page: int):
        return iter(())
