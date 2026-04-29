from discovery.sources.base import SourceBase


class AIMadeInGermanySource(SourceBase):
    name = "ai_made_in_germany"
    geo_tier = "DE"
    extractor = "custom-ai-made-de"

    def iter_pages(self, start_page: int):
        return iter(())
