"""tests/test_config.py - config.py 유닛 테스트"""

import os
from datetime import datetime
from unittest.mock import patch

import pytest

from config import Config, _mask, load_config


def _make_config(**overrides) -> Config:
    """테스트용 Config 기본값 생성."""
    defaults = dict(
        interpark_id="testuser",
        interpark_pw="testpass",
        goods_id="12345678",
        sale_start_time=datetime(2026, 4, 1, 10, 0, 0),
        preferred_sections=["112", "113"],
        max_tickets=3,
        card_number="0000-1111-2222-3333",
        card_expiry="1228",
        card_cvv="123",
        card_password_2digits="12",
        telegram_bot_token="bot_token",
        telegram_chat_id="123456",
        polling_interval=0.5,
        pre_sale_activate_seconds=30,
        headless=False,
        screenshot_on_error=True,
    )
    defaults.update(overrides)
    return Config(**defaults)


def _base_env() -> dict:
    """load_config() 호출에 필요한 최소 환경변수."""
    return {
        "INTERPARK_ID": "testuser",
        "INTERPARK_PW": "testpass",
        "GOODS_ID": "12345678",
        "SALE_START_TIME": "2026-04-01T10:00:00+09:00",
        "PREFERRED_SECTIONS": "112,113",
        "CARD_NUMBER": "0000-1111-2222-3333",
        "CARD_EXPIRY": "1228",
        "CARD_CVV": "123",
        "CARD_PASSWORD_2DIGITS": "12",
        "TELEGRAM_BOT_TOKEN": "bot_token",
        "TELEGRAM_CHAT_ID": "123456",
    }


class TestMask:
    def test_value_shorter_than_visible_returns_asterisks(self):
        assert _mask("abc", visible=4) == "****"

    def test_value_equal_to_visible_returns_asterisks(self):
        assert _mask("1234", visible=4) == "****"

    def test_masks_characters_beyond_visible(self):
        assert _mask("12345678", visible=4) == "1234****"

    def test_default_visible_is_four(self):
        result = _mask("ABCDEFGH")
        assert result == "ABCD****"


class TestConfigValidation:
    def test_max_tickets_zero_raises(self):
        with pytest.raises(ValueError, match="MAX_TICKETS"):
            _make_config(max_tickets=0)

    def test_max_tickets_five_raises(self):
        with pytest.raises(ValueError, match="MAX_TICKETS"):
            _make_config(max_tickets=5)

    def test_max_tickets_boundary_one_ok(self):
        cfg = _make_config(max_tickets=1)
        assert cfg.max_tickets == 1

    def test_max_tickets_boundary_four_ok(self):
        cfg = _make_config(max_tickets=4)
        assert cfg.max_tickets == 4

    def test_polling_interval_below_minimum_raises(self):
        with pytest.raises(ValueError, match="POLLING_INTERVAL"):
            _make_config(polling_interval=0.09)

    def test_polling_interval_at_minimum_ok(self):
        cfg = _make_config(polling_interval=0.1)
        assert cfg.polling_interval == 0.1

    def test_valid_config_creates_successfully(self):
        cfg = _make_config()
        assert cfg.goods_id == "12345678"
        assert cfg.preferred_sections == ["112", "113"]


class TestLoadConfig:
    def test_missing_interpark_id_raises(self):
        env = _base_env()
        del env["INTERPARK_ID"]
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="INTERPARK_ID"):
                load_config()

    def test_missing_goods_id_raises(self):
        env = _base_env()
        del env["GOODS_ID"]
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="GOODS_ID"):
                load_config()

    def test_invalid_sale_start_time_raises(self):
        env = {**_base_env(), "SALE_START_TIME": "2026/04/01 10:00"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="SALE_START_TIME"):
                load_config()

    def test_preferred_sections_parsed_as_list(self):
        with patch.dict(os.environ, _base_env(), clear=True):
            cfg = load_config()
        assert cfg.preferred_sections == ["112", "113"]

    def test_preferred_sections_strips_whitespace(self):
        env = {**_base_env(), "PREFERRED_SECTIONS": "112 , 113 , 318"}
        with patch.dict(os.environ, env, clear=True):
            cfg = load_config()
        assert cfg.preferred_sections == ["112", "113", "318"]

    def test_default_max_tickets_is_three(self):
        with patch.dict(os.environ, _base_env(), clear=True):
            cfg = load_config()
        assert cfg.max_tickets == 3

    def test_headless_false_by_default(self):
        with patch.dict(os.environ, _base_env(), clear=True):
            cfg = load_config()
        assert cfg.headless is False

    def test_headless_true_when_set(self):
        env = {**_base_env(), "HEADLESS": "true"}
        with patch.dict(os.environ, env, clear=True):
            cfg = load_config()
        assert cfg.headless is True


class TestConfigSummary:
    def test_summary_does_not_contain_raw_card_number(self):
        cfg = _make_config(card_number="9876-5432-1012-3456")
        summary = cfg.summary()
        assert "9876-5432-1012-3456" not in summary

    def test_summary_contains_masked_card_prefix(self):
        cfg = _make_config(card_number="9876-5432-1012-3456")
        summary = cfg.summary()
        assert "9876" in summary

    def test_summary_contains_goods_id(self):
        cfg = _make_config(goods_id="99998888")
        summary = cfg.summary()
        assert "99998888" in summary
