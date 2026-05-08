from jobs.filters import is_ai_eng_role, is_de_eu


def test_is_ai_eng_role():
    assert is_ai_eng_role("ML Engineer", "Works on structural mechanics models") is True


def test_is_ai_eng_role_excludes_marketing():
    assert is_ai_eng_role("Marketing Manager", "Brand and campaigns") is False


def test_is_de_eu():
    assert is_de_eu("DE") is True
    assert is_de_eu("AT") is True
    assert is_de_eu("CH") is True
    assert is_de_eu("US") is False
