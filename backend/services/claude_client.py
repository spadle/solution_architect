import logging
from typing import Any

from anthropic import AsyncAnthropic

from backend.config import settings

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Wrapper around the Anthropic SDK for Claude API calls."""

    def __init__(self):
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model

    async def create_message(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int = 4096,
    ) -> Any:
        """Send a message to Claude with tool definitions."""
        response = await self._client.messages.create(
            model=self.model,
            system=system,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
        )
        logger.info(
            f"Claude response: {response.stop_reason}, "
            f"usage: {response.usage.input_tokens}in/{response.usage.output_tokens}out"
        )
        return response


claude_client = ClaudeClient()
