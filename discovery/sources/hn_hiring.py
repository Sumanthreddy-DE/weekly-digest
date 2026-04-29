from discovery.sources.base import SourceBase


class HNHiringSource(SourceBase):
    name = "hn_who_is_hiring"
    extractor = "llm-ollama"

    def iter_pages(self, start_page: int):
        return iter(())
