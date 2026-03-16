from src.errors import ValidationError
from src.observability import clear_request_id, error_response, success_response


def test_success_response_shape() -> None:
    clear_request_id()
    payload = success_response({"items": []})
    assert payload["ok"] is True
    assert isinstance(payload["request_id"], str)
    assert payload["data"] == {"items": []}


def test_error_response_shape() -> None:
    clear_request_id()
    payload = error_response(ValidationError("Bad input"))
    assert payload["ok"] is False
    assert payload["error"]["code"] == "validation_error"
    assert "request_id" in payload
