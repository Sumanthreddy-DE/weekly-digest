from discovery.sources.base import SourceBase


class BerlinAIMapSource(SourceBase):
    name = "berlin_ai_map"
    geo_tier = "DE"
    extractor = "custom-berlin-ai"

    def iter_pages(self, start_page: int):
        return iter(())
