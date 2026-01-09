"""
Tests for Robust JSON Utils in core/utils.py
"""
import pytest
from core.utils import extract_json, apply_prompt_template

def test_extract_json_valid():
    text = '{"key": "value"}'
    result = extract_json(text)
    assert len(result) == 1
    assert result[0]["key"] == "value"

def test_extract_json_malformed():
    # Missing closing brace
    text = '{"key": "value"'
    result = extract_json(text)
    # json_repair usually handles this
    assert len(result) >= 1
    assert result[0]["key"] == "value"

def test_extract_json_nested_in_text():
    text = 'Here is the data: {"id": 1} and more text.'
    result = extract_json(text)
    assert len(result) == 1
    assert result[0]["id"] == 1

def test_extract_json_multiple():
    text = 'First: {"a": 1} Second: {"b": 2}'
    result = extract_json(text)
    assert len(result) == 2
    assert result[0]["a"] == 1
    assert result[1]["b"] == 2

def test_apply_prompt_template_str():
    tmpl = "Hello {{name}}!"
    res = apply_prompt_template(tmpl, "World")
    assert res == "Hello World!"

def test_apply_prompt_template_dict():
    tmpl = "Hello {{first}} {{last}}!"
    res = apply_prompt_template(tmpl, {"first": "John", "last": "Doe"})
    assert res == "Hello John Doe!"
