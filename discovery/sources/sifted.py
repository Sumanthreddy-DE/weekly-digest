from discovery.sources.base import SourceBase


class SiftedSource(SourceBase):
    name = "sifted"
    geo_tier = "EU"
    extractor = "llm-ollama"

    def iter_pages(self, start_page: int):
        return iter(())
