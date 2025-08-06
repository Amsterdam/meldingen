from meldingen.generators import PublicIdGenerator


def test_public_id_generator_no_arguments() -> None:
    generator = PublicIdGenerator()

    alphabet = generator()

    assert generator._alphabet == 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

    assert len(alphabet) == 6
