from unittest.mock import Mock

from meldingen.image import IMGProxyImageOptimizerUrlGenerator, IMGProxySignatureGenerator


def test_imgproxy_signature_generator() -> None:
    """Based on the example @ https://docs.imgproxy.net/usage/signing_url"""
    generate_signature = IMGProxySignatureGenerator("736563726574", "68656C6C6F")

    signature = generate_signature(
        "/rs:fill:300:400:0/g:sm/aHR0cDovL2V4YW1w/bGUuY29tL2ltYWdl/cy9jdXJpb3NpdHku/anBn.png"
    )

    assert signature == "oKfUtW34Dvo2BGQehJFR4Nr0_rIjOtdtzJ3QFsUcXH8"


def test_imgproxy_image_optimizer_url_generator() -> None:
    signature_generator = Mock(IMGProxySignatureGenerator)
    signature_generator.return_value = "oKfUtW34Dvo2BGQehJFR4Nr0_rIjOtdtzJ3QFsUcXH8"

    generate_url = IMGProxyImageOptimizerUrlGenerator(signature_generator, "http://imgproxy")

    url = generate_url("https://images/path/to/image.jpg")

    assert url == "http://imgproxy/oKfUtW34Dvo2BGQehJFR4Nr0_rIjOtdtzJ3QFsUcXH8/f:webp/https://images/path/to/image.jpg"
