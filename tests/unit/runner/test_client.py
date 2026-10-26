from types import SimpleNamespace

import anthropic
import pytest

from evals.runner.client import AnthropicClient, FatalModelError, ModelError


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


def response(*blocks, **usage):
    return SimpleNamespace(
        content=list(blocks),
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=7, output_tokens=3, **usage),
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
        "system": [{"type": "text", "text": "sys", "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": "user"}],
    }


def test_the_system_prompt_is_marked_for_caching_by_default():
    messages = StubMessages(response(SimpleNamespace(type="text", text="x")))
    make_client(messages).complete("sys", "user")
    assert messages.kwargs["system"] == [{"type": "text", "text": "sys", "cache_control": {"type": "ephemeral"}}]


def test_caching_can_be_turned_off_and_the_system_prompt_is_then_plain_text():
    messages = StubMessages(response(SimpleNamespace(type="text", text="x")))
    make_client(messages, cache=False).complete("sys", "user")
    assert messages.kwargs["system"] == "sys"


def test_cache_tokens_are_reported_next_to_the_normal_counts():
    usage = {"cache_creation_input_tokens": 50, "cache_read_input_tokens": 900}
    messages = StubMessages(response(SimpleNamespace(type="text", text="x"), **usage))
    completion = make_client(messages).complete("s", "u")
    assert (completion.input_tokens, completion.cache_write_tokens, completion.cache_read_tokens) == (7, 50, 900)


@pytest.mark.parametrize("usage", [{}, {"cache_creation_input_tokens": None, "cache_read_input_tokens": None}])
def test_missing_cache_counts_are_zero(usage):
    messages = StubMessages(response(SimpleNamespace(type="text", text="x"), **usage))
    completion = make_client(messages).complete("s", "u")
    assert (completion.cache_write_tokens, completion.cache_read_tokens) == (0, 0)


def test_more_retries_can_be_asked_for_and_the_sdk_default_is_kept_otherwise():
    default = AnthropicClient()._client.max_retries
    assert AnthropicClient(max_retries=8)._client.max_retries == 8
    assert default < 8


def test_effort_is_sent_only_when_set():
    messages = StubMessages(response(SimpleNamespace(type="text", text="x")))
    make_client(messages, effort="high").complete("s", "u")
    assert messages.kwargs["output_config"] == {"effort": "high"}


def test_a_rate_limit_that_survives_the_retries_is_a_failed_run_that_names_the_error():
    http_response = SimpleNamespace(request=None, status_code=429, headers={})
    error = anthropic.RateLimitError("slow down", response=http_response, body=None)
    with pytest.raises(ModelError, match="RateLimitError: slow down") as caught:
        make_client(StubMessages(error=error)).complete("s", "u")
    assert not isinstance(caught.value, FatalModelError)


def test_missing_credentials_become_a_fatal_error():
    error = TypeError('"Could not resolve authentication method. Expected one of api_key..."')
    with pytest.raises(FatalModelError, match="ANTHROPIC_API_KEY"):
        make_client(StubMessages(error=error)).complete("s", "u")


def test_unrelated_type_errors_are_not_swallowed():
    with pytest.raises(TypeError, match="bug"):
        make_client(StubMessages(error=TypeError("bug"))).complete("s", "u")
