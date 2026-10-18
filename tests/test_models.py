import pytest

from car_rental.models import FAST_PREFERENCES, MAIN_PREFERENCES, choose, model_options


def test_picks_first_preferred_model_the_account_has():
    available = {"openai/gpt-oss-20b", "some/other-model"}
    assert choose(None, MAIN_PREFERENCES, available) == "openai/gpt-oss-20b"
    assert choose(None, FAST_PREFERENCES, available) == "openai/gpt-oss-20b"


def test_override_wins():
    assert choose("my/model", MAIN_PREFERENCES, {"openai/gpt-oss-120b"}) == "my/model"


def test_without_model_list_trusts_preferences():
    assert choose(None, MAIN_PREFERENCES, None) == MAIN_PREFERENCES[0]


def test_clear_error_when_nothing_matches():
    with pytest.raises(RuntimeError, match="GROQ_MAIN_MODEL"):
        choose(None, MAIN_PREFERENCES, {"retired/model"})


def test_reasoning_models_answer_without_visible_reasoning():
    assert model_options("openai/gpt-oss-120b") == {"reasoning_effort": "low"}
    assert model_options("qwen/qwen3.8-27b") == {"reasoning_format": "hidden"}
    assert model_options("other") == {}
