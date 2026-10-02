from scripts.import_google_fonts import quoted_values


def test_protobuf_escaped_apostrophe_is_not_discarded() -> None:
    assert quoted_values(r'''name: "Noto Sans N\'Ko"''', "name", top_level=True) == [
        "Noto Sans N'Ko"
    ]


def test_unicode_and_backslash_metadata() -> None:
    assert quoted_values('name: "思源黑体"', "name", top_level=True) == ["思源黑体"]
    assert quoted_values('fonts {\n  full_name: "Noto Sans SC Thin"\n}', "full_name") == [
        "Noto Sans SC Thin"
    ]
