from meldingen.generators import PublicIdGenerator


def test_public_id_generator() -> None:
    generator = PublicIdGenerator("a")

    alphabet = generator()

    assert generator._alphabet == "a"

    assert len(alphabet) == 6
    assert alphabet == "aaaaaa"


def test_public_id_generator_no_arguments() -> None:
    generator = PublicIdGenerator()

    alphabet = generator()

    assert generator._alphabet == "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    assert len(alphabet) == 6
