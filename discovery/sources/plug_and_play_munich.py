from discovery.sources.base import SourceBase


class PlugAndPlayMunichSource(SourceBase):
    name = "plug_and_play_munich"
    geo_tier = "DE"
    extractor = "custom-plug-and-play"

    def iter_pages(self, start_page: int):
        return iter(())
