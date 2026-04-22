from src.errors import ValidationError
from src.validation import (
    normalize_yyyymmdd,
    validate_database_token,
    validate_optional_int,
    validate_optional_int_from_any,
    validate_optional_text,
    validate_required_text,
    validate_uuid_like,
    validate_yyyymmdd,
)


def test_validate_required_text_trims_value() -> None:
    assert validate_required_text("database_token", " abc ") == "abc"


def test_validate_required_text_raises_for_empty() -> None:
    try:
        validate_required_text("database_token", "  ")
    except ValidationError as exc:
        assert exc.code == "validation_error"
        assert "required" in exc.message
    else:
        raise AssertionError("Expected ValidationError")


def test_validate_optional_text_none_when_blank() -> None:
    assert validate_optional_text("parent_folder_id", "   ") is None


def test_validate_yyyymmdd_accepts_eight_digits() -> None:
    assert validate_yyyymmdd("start_date", "20260316") == "20260316"


def test_validate_yyyymmdd_rejects_other_formats() -> None:
    try:
        validate_yyyymmdd("start_date", "2026-03-16")
    except ValidationError as exc:
        assert exc.code == "validation_error"
        assert "yyyymmdd" in exc.message
    else:
        raise AssertionError("Expected ValidationError")


def test_validate_optional_int_accepts_none_and_bounds() -> None:
    assert validate_optional_int("page_index", None, min_value=0) is None
    assert validate_optional_int("page_index", 0, min_value=0) == 0


def test_validate_optional_int_rejects_invalid() -> None:
    try:
        validate_optional_int("page_index", -1, min_value=0)
    except ValidationError as exc:
        assert exc.code == "validation_error"
        assert ">= 0" in exc.message
    else:
        raise AssertionError("Expected ValidationError")


def test_validate_optional_int_from_any_coerces_string() -> None:
    assert validate_optional_int_from_any("page_size", "25", min_value=1, max_value=100) == 25


def test_normalize_yyyymmdd_accepts_iso_format() -> None:
    assert normalize_yyyymmdd("start_date", "2026-03-16") == "20260316"


def test_validate_uuid_like() -> None:
    assert validate_uuid_like("project_id", "123e4567-e89b-12d3-a456-426614174000")


def test_validate_database_token_accepts_uuid() -> None:
    assert (
        validate_database_token(
            "database_token", "123e4567-e89b-12d3-a456-426614174000"
        )
        == "123e4567-e89b-12d3-a456-426614174000"
    )


def test_validate_database_token_accepts_opaque_accubid_token() -> None:
    opaque = (
        "bvu2wLp1sfCMYa_DTlqhB9vhn0zEMBIVJgz3h3JVXXcDGAvK5Ufp-cs9TnsUhGgs"
        "AjfchdHCjYGzfsOcfHlLmw"
    )
    assert validate_database_token("database_token", opaque) == opaque
