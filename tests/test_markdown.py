from meldingen.markdown import MarkdownToPlainTextConverter


def test_strips_bold_markup() -> None:
    convert = MarkdownToPlainTextConverter()

    assert convert("**bold**") == "bold"


def test_strips_heading_and_link_markup() -> None:
    convert = MarkdownToPlainTextConverter()

    assert convert("# Title\n\nSee [the docs](https://example.com/very/long/url)") == "Title\nSee the docs"


def test_plain_text_is_shorter_than_markdown_source() -> None:
    convert = MarkdownToPlainTextConverter()
    text = "**" + ("a" * 2999) + "**"

    plain = convert(text)

    assert plain == "a" * 2999
    assert len(plain) < len(text)
