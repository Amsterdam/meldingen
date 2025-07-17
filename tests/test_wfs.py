import pytest

from meldingen.wfs import UrlProcessor


@pytest.mark.anyio
def test_get_url_from_parameters() -> None:
    processor = UrlProcessor()

    url = processor("https://example.com", "typename", filter="filtering")

    assert (
        url
        == "https://example.com?TYPENAMES=typename&SRSNAME=urn%3Aogc%3Adef%3Acrs%3AEPSG%3A%3A4326&OUTPUTFORMAT=application%2Fjson&SERVICE=WFS&REQUEST=GetFeature&VERSION=2.0.0&COUNT=1000&FILTER=filtering"
    )
