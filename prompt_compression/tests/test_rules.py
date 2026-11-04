import pytest

from prompt_compression import rules


@pytest.mark.parametrize(
    "text, expected_rule",
    [
        ("mail me at jane.doe@example.com", "email"),
        ("call +1 555 013 2287 tonight", "phone"),
        ("call (555) 867-5309 after 6pm", "phone"),
        ("card 4111 1111 1111 1111 exp 08/29", "credit_card"),
        ("card 5555-5555-5555-4444", "credit_card"),
        ("SSN 123-45-6789", "us_ssn"),
        ("Passport number X1234567, issued in Ottawa", "national_id"),
        ("National ID 1985-0312-4471", "national_id"),
        ("IBAN DE89 3704 0044 0532 0130 00", "iban"),
        ("routing number is 021000021", "bank_account"),
        ("AKIAIOSFODNN7EXAMPLE", "aws_access_key"),
        ("token ghp_1A2b3C4d5E6f7G8h9I0jK1lM2nO3pQ4rS5tU", "github_token"),
        ("OPENAI_API_KEY=[OPENAI_API_KEY_PLACEHOLDER]", "openai_style_key"),
        ("sk_live_[STRIPE_KEY_PLACEHOLDER]", "stripe_key"),
        ("-----BEGIN RSA PRIVATE KEY-----\nabc\n-----END RSA PRIVATE KEY-----", "private_key"),
        ("-----BEGIN OPENSSH PRIVATE KEY-----", "private_key"),
        ("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0", "jwt"),
        ("client_secret: 8f3b2c1d-4e5f-6a7b-8c9d", "secret_assignment"),
        ("postgres://app_user:s3cr3tPass@10.0.4.12:5432/payroll", "credentials_in_url"),
        ("my password is Sunflower#77", "password"),
        ("the root password for the router, it's tiger-lily-9921", "password"),
        ("my PIN for the card is 4821", "pin"),
        ("Login for the staging box is admin / P@ssw0rd!2024", "login_pair"),
    ],
)
def test_rule_hits(text, expected_rule):
    assert expected_rule in rules.rule_hits(text)


@pytest.mark.parametrize(
    "text",
    [
        "Our team discussed general password hygiene, such as using a password manager.",
        "In NLP, a 'token' is a unit of text such as a word.",
        "I read about 3 books last month.",
        "Is 1,021 a prime number?",
        "The order ID is ORD-2024-88731 and the SKU is BLK-4410-XL.",
        "Parse the timestamp 2024-11-05T23:59:59+05:30.",
        "Set max_tokens to 512, temperature to 0.",
        "The pin is located on the left side of the board.",
        "I left the frying pan because it was dirty.",
        "Card 4111 1111 1111 1112 fails the checksum.",  # Luhn-invalid
    ],
)
def test_no_false_positive(text):
    assert rules.rule_hits(text) == []


def test_luhn():
    assert rules.luhn_valid("4111111111111111")
    assert not rules.luhn_valid("4111111111111112")
    assert not rules.luhn_valid("1234")


def test_iban_checksum():
    assert rules.iban_valid("DE89 3704 0044 0532 0130 00")
    assert not rules.iban_valid("DE00 3704 0044 0532 0130 00")


def test_redact_replaces_spans_with_placeholders():
    text = "Email jane.doe@example.com or call +1 555 013 2287; password: hunter22"
    redacted, hits = rules.redact(text)
    assert "jane.doe@example.com" not in redacted
    assert "555 013 2287" not in redacted
    assert "hunter22" not in redacted
    assert "[EMAIL]" in redacted and "[PHONE]" in redacted and "[PASSWORD]" in redacted
    # The keyword stays so the model still knows a password was there.
    assert "password:" in redacted
    assert set(hits) >= {"email", "phone", "password"}


def test_redact_leaves_clean_text_alone():
    text = "Write a haiku about autumn leaves."
    assert rules.redact(text) == (text, [])
