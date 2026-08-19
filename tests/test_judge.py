"""Tests for the LLM judge, incl. Gemini (google-generative-ai) routing (#247)."""

from __future__ import annotations

import pytest

from clawbench.runner import judge, judge_llm


def test_gemini_openai_cfg_normalizes_native_root() -> None:
    # native Google root → OpenAI-compat path appended
    cfg = judge._gemini_openai_cfg(
        {"base_url": "https://generativelanguage.googleapis.com/", "api_key": "k"}
    )
    assert cfg["base_url"] == "https://generativelanguage.googleapis.com/v1beta/openai"
    # already an /openai path → left as-is
    cfg2 = judge._gemini_openai_cfg(
        {
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            "api_key": "k",
        }
    )
    assert cfg2["base_url"].endswith("/v1beta/openai")


def test_gemini_judge_routes_through_openai_compat(monkeypatch) -> None:
    seen = {}

    def fake_post(url, headers, payload):
        seen["url"] = url
        return {
            "choices": [{"message": {"content": '{"match": true, "reason": "ok"}'}}]
        }

    monkeypatch.setattr(judge, "_post_json", fake_post)
    cfg = {
        "base_url": "https://generativelanguage.googleapis.com",  # native root
        "api_key": "k",
        "api_type": "google-generative-ai",
    }
    r = judge.judge_request(cfg, "gemini-3.5-flash", "do it", {"request": {"url": "x"}})
    assert r["match"] is True
    # hit the OpenAI-compat chat endpoint, not the native root
    assert seen["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    )


def test_unsupported_api_type_reports_error(monkeypatch) -> None:
    r = judge.judge_request(
        {"base_url": "http://x", "api_key": "k", "api_type": "bogus-type"},
        "m",
        "do it",
        {"request": {"url": "x"}},
    )
    assert r["match"] is None and r["error"] == "unsupported_api_type"


# --- verdict parsing (see #295) -------------------------------------------
#
# The `match` field decides whether a run counts as a pass, so it has to be
# read exactly. Models answer with real booleans, with the *strings* "true"
# and "false", and sometimes with no verdict at all — `bool("false")` is True,
# so a stringly-typed mismatch used to be scored as a pass.


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # real booleans
        ('{"match": true, "reason": "ok"}', True),
        ('{"match": false, "reason": "wrong item"}', False),
        # stringly-typed verdicts — the regression this pins
        ('{"match": "false", "reason": "wrong item"}', False),
        ('{"match": "true"}', True),
        ('{"match": "FALSE"}', False),
        ('{"match": "False"}', False),
        # no usable verdict → inconclusive, never an implicit pass/fail
        ('{"reason": "forgot the verdict"}', None),
        ('{"match": null}', None),
        ('{"match": "maybe"}', None),
        # fenced JSON still parses
        ('```json\n{"match": false, "reason": "r"}\n```', False),
    ],
)
def test_parse_verdict_is_tri_state(raw: str, expected: bool | None) -> None:
    assert judge._parse_verdict(raw)[0] is expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"match": "false", "reason": "wrong item"}', False),
        ('{"match": false}', False),
        ('{"match": true}', True),
        # a reply with no verdict key must not default to a pass: this module
        # produces the published Reward-lenient column
        ('{"reason": "forgot the verdict"}', None),
        ("not json at all", None),
    ],
)
def test_lenient_judge_parse_verdict_is_tri_state(
    raw: str, expected: bool | None
) -> None:
    assert judge_llm._parse_verdict(raw)[0] is expected


def test_coerce_match_rejects_non_verdict_types() -> None:
    for value in (1, 0, [], {}, None, "  "):
        assert judge._coerce_match(value) is None
