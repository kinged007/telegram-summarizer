import os
import tempfile
from src.templates import resolve_chat_id, resolve_prompt_template


def test_resolve_chat_id_numeric():
    assert resolve_chat_id("-1001234567890", {}) == "-1001234567890"


def test_resolve_chat_id_with_topic():
    assert resolve_chat_id("-1001234567890_123", {}) == "-1001234567890_123"


def test_resolve_chat_id_named():
    templates = {"John": "-1001234567890"}
    assert resolve_chat_id("John", templates) == "-1001234567890"


def test_resolve_chat_id_unknown():
    assert resolve_chat_id("Unknown", {}) is None


def test_resolve_chat_id_at_username():
    # usernames like @telegram are stored as values, numeric check should not match
    # so resolve via template name
    templates = {"TelegramSupport": "@telegram"}
    assert resolve_chat_id("TelegramSupport", templates) == "@telegram"


def test_resolve_prompt_template_found():
    prompts = {"Technical": "summarize technical stuff"}
    assert resolve_prompt_template("Technical", prompts) == "summarize technical stuff"


def test_resolve_prompt_template_missing():
    assert resolve_prompt_template("Missing", {}) is None
