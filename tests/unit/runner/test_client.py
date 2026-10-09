from types import SimpleNamespace

import pytest

from evals.runner.client import AnthropicClient, FatalModelError


class StubMessages:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.response


def make_client(messages, **kwargs) -> AnthropicClient:
    client = AnthropicClient(**kwargs)
    client._client = SimpleNamespace(messages=messages)
    return client


def response(*blocks):
    return SimpleNamespace(
        content=list(blocks),
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=7, output_tokens=3),
    )


def test_joins_text_blocks_and_skips_others():
    messages = StubMessages(
        response(
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text="one "),
            SimpleNamespace(type="text", text="two"),
        )
    )
    completion = make_client(messages).complete("sys", "user")
    assert completion.text == "one two"
    assert (completion.stop_reason, completion.input_tokens, completion.output_tokens) == ("end_turn", 7, 3)


def test_request_shape_has_no_sampling_params():
    messages = StubMessages(response(SimpleNamespace(type="text", text="x")))
    make_client(messages, model="m", max_tokens=99).complete("sys", "user")
    assert messages.kwargs == {
        "model": "m",
        "max_tokens": 99,
        "system": "sys",
        "messages": [{"role": "user", "content": "user"}],
    }


def test_effort_is_sent_only_when_set():
    messages = StubMessages(response(SimpleNamespace(type="text", text="x")))
    make_client(messages, effort="high").complete("s", "u")
    assert messages.kwargs["output_config"] == {"effort": "high"}


def test_missing_credentials_become_a_fatal_error():
    error = TypeError('"Could not resolve authentication method. Expected one of api_key..."')
    with pytest.raises(FatalModelError, match="ANTHROPIC_API_KEY"):
        make_client(StubMessages(error=error)).complete("s", "u")


def test_unrelated_type_errors_are_not_swallowed():
    with pytest.raises(TypeError, match="bug"):
        make_client(StubMessages(error=TypeError("bug"))).complete("s", "u")
