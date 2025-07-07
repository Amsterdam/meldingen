import pytest

from meldingen.wfs import ProxyWfsProvider


@pytest.mark.anyio
def test_get_url_from_parameters() -> None:
    provider = ProxyWfsProvider("https://example.com")

    url = provider.get_url("typename")

    assert (
        url
        == "https://example.com?TYPENAMES=typename&SRSNAME=urn%3Aogc%3Adef%3Acrs%3AEPSG%3A%3A4326&OUTPUTFORMAT=application%2Fjson&SERVICE=WFS&REQUEST=GetFeature&VERSION=2.0.0&COUNT=1000"
    )
