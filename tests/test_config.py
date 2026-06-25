from app.config import get_settings


def test_get_settings_reads_from_environment(monkeypatch):
    monkeypatch.setenv("VAPI_API_KEY", "test-vapi-key")
    monkeypatch.setenv("VAPI_PHONE_NUMBER_ID", "test-phone-id")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    settings = get_settings()

    assert settings.vapi_api_key == "test-vapi-key"
    assert settings.vapi_phone_number_id == "test-phone-id"
    assert settings.openai_api_key == "test-openai-key"
