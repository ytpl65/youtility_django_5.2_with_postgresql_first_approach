import pytest
from apps.service.utils import  get_or_create_dir
from apps.service.validators import clean_string, validate_email, clean_array_string, validate_cron



def test_get_or_create_dir(tmp_path):
    path = tmp_path / "sub"
    created = get_or_create_dir(path)
    assert created is True
    assert path.exists()
    # calling again should return False
    created_again = get_or_create_dir(path)
    assert created_again is False


@pytest.mark.parametrize("raw,expected", [("Hello  World", "Hello World"), ("code", "CODE")])
def test_clean_string(raw, expected):
    if raw == "code":
        assert clean_string(raw, code=True) == expected
    else:
        assert clean_string(raw) == expected


def test_validate_email():
    assert validate_email("test@example.com") is True
    assert validate_email("bad_email") is False


def test_clean_array_string():
    assert clean_array_string("a,b,c") == ["a", "b", "c"]
    assert clean_array_string(None) == []


def test_validate_cron():
    assert validate_cron("0 0 * * *") is True
    assert validate_cron("*") is False
