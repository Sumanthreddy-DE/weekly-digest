from discovery.sources.base import SourceBase


class YCCompaniesSource(SourceBase):
    name = "yc_companies"
    extractor = "custom-yc"

    def iter_pages(self, start_page: int):
        return iter(())
