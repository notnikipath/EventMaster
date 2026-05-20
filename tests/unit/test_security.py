from shared.eventmaster_common import decrypt_text, encrypt_text, sign_token, verify_token


def test_encrypt_roundtrip() -> None:
    value = "eventmaster confidential payload"
    encrypted = encrypt_text(value, "demo-key")
    assert encrypted != value
    assert decrypt_text(encrypted, "demo-key") == value


def test_token_roundtrip() -> None:
    token = sign_token({"sub": "user-1", "role": "attendee"}, "jwt-secret", exp_minutes=5)
    payload = verify_token(token, "jwt-secret")
    assert payload is not None
    assert payload["sub"] == "user-1"
