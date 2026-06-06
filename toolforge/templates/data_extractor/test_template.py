from tool import extract


def test_extract_email():
    result = extract(
        text="Contact us at support@example.com or sales@company.org",
        pattern="",
        extract_type="email",
    )
    assert result["count"] == 2
    assert "support@example.com" in result["extracted"]


def test_extract_number():
    result = extract(
        text="The price is $42.99, originally $59.99.",
        pattern="",
        extract_type="number",
    )
    assert len(result["extracted"]) >= 2
