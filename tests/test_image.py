from meldingen.image import IMGProxySignatureGenerator


def test_imgproxy_signature_generator() -> None:
    """Based on the example @ https://docs.imgproxy.net/usage/signing_url"""
    generate_signature = IMGProxySignatureGenerator("736563726574", "68656C6C6F")

    signature = generate_signature(
        "/rs:fill:300:400:0/g:sm/aHR0cDovL2V4YW1w/bGUuY29tL2ltYWdl/cy9jdXJpb3NpdHku/anBn.png"
    )

    assert signature == "oKfUtW34Dvo2BGQehJFR4Nr0_rIjOtdtzJ3QFsUcXH8"
