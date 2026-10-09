"""Model access. The runner only depends on the ModelClient protocol, so tests use a fake."""

from dataclasses import dataclass
from typing import Protocol

import anthropic

DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_MAX_TOKENS = 16000


class ModelError(Exception):
    """A single call failed. The run is recorded as failed and the eval continues."""


class FatalModelError(ModelError):
    """Retrying will not help (bad credentials, unknown model). The eval aborts."""


@dataclass(frozen=True)
class Completion:
    text: str
    stop_reason: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0


class ModelClient(Protocol):
    def complete(self, system: str, user: str) -> Completion: ...


class AnthropicClient:
    """Calls the Messages API once per run. Sampling parameters are left at model defaults."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        effort: str | None = None,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.effort = effort
        self._client = anthropic.Anthropic()

    def complete(self, system: str, user: str) -> Completion:
        params = {}
        if self.effort:
            params["output_config"] = {"effort": self.effort}
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                **params,
            )
        except (
            anthropic.AuthenticationError,
            anthropic.PermissionDeniedError,
            anthropic.BadRequestError,
            anthropic.NotFoundError,
        ) as e:
            raise FatalModelError(f"{type(e).__name__}: {e.message}") from e
        except anthropic.APIError as e:
            raise ModelError(f"{type(e).__name__}: {e.message}") from e
        except TypeError as e:
            # The SDK raises a bare TypeError when no credentials are configured.
            if "authentication method" not in str(e):
                raise
            raise FatalModelError(
                "no Anthropic credentials found: set ANTHROPIC_API_KEY (see .env.example)"
            ) from e

        return Completion(
            text="".join(b.text for b in response.content if b.type == "text"),
            stop_reason=response.stop_reason,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
