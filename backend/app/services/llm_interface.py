from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
import time
import json

logger = logging.getLogger(__name__)


class LLMMessage:
    """Standard message format for LLM interactions"""

    def __init__(self, role: str, content: str):
        self.role = role  # "system", "user", "assistant"
        self.content = content

    def to_openai(self) -> Dict[str, str]:
        """Convert to OpenAI format"""
        return {"role": self.role, "content": self.content}

    def to_anthropic(self) -> Dict[str, str]:
        """Convert to Anthropic format"""
        return {"role": self.role, "content": self.content}


class LLMResponse:
    """Standard response format from LLM"""

    def __init__(self, content: str, usage: Optional[Dict[str, int]] = None, model: str = None):
        self.content = content
        self.usage = usage or {}
        self.model = model
        self.timestamp = time.time()


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[LLMMessage],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate chat completion"""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name"""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI ChatGPT provider"""

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        """Lazy load OpenAI client"""
        if self._client is None:
            try:
                import openai
                self._client = openai.AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        return self._client

    async def chat_completion(
        self,
        messages: List[LLMMessage],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate chat completion using OpenAI"""

        client = self._get_client()

        # Convert messages to OpenAI format
        openai_messages = [msg.to_openai() for msg in messages]

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }

            return LLMResponse(
                content=content,
                usage=usage,
                model=self.model
            )

        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise

    def get_provider_name(self) -> str:
        return f"openai-{self.model}"


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider"""

    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        """Lazy load Anthropic client"""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        return self._client

    async def chat_completion(
        self,
        messages: List[LLMMessage],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate chat completion using Anthropic Claude"""

        client = self._get_client()

        # Separate system message from conversation
        system_message = None
        conversation_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                conversation_messages.append(msg.to_anthropic())

        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_message,
                messages=conversation_messages,
                **kwargs
            )

            content = response.content[0].text
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }

            return LLMResponse(
                content=content,
                usage=usage,
                model=self.model
            )

        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise

    def get_provider_name(self) -> str:
        return f"anthropic-{self.model}"


class MockLLMProvider(LLMProvider):
    """Mock provider for testing without API costs"""

    def __init__(self):
        self.responses = [
            "Based on the error description, this appears to be a database connection timeout issue. I recommend checking: 1) Database server status 2) Connection pool configuration 3) Network connectivity between services.",
            "This looks like a memory-related issue. The symptoms suggest a potential memory leak. Consider: 1) Analyzing heap dumps 2) Reviewing recent code changes 3) Monitoring memory usage patterns.",
            "The performance degradation suggests a bottleneck in the system. To diagnose: 1) Check database query performance 2) Review system resource utilization 3) Analyze request patterns.",
            "This appears to be an authentication/authorization issue. Steps to resolve: 1) Verify user permissions 2) Check authentication service logs 3) Review access control configuration."
        ]
        self.response_index = 0

    async def chat_completion(
        self,
        messages: List[LLMMessage],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate mock response"""

        # Simulate API delay
        import asyncio
        await asyncio.sleep(0.5)

        # Get next mock response
        content = self.responses[self.response_index % len(self.responses)]
        self.response_index += 1

        # Simulate usage stats
        usage = {
            "prompt_tokens": sum(len(msg.content.split()) for msg in messages),
            "completion_tokens": len(content.split()),
            "total_tokens": sum(len(msg.content.split()) for msg in messages) + len(content.split())
        }

        return LLMResponse(
            content=content,
            usage=usage,
            model="mock-llm"
        )

    def get_provider_name(self) -> str:
        return "mock-llm"


class LLMService:
    """Main service for LLM interactions with pluggable providers"""

    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.usage_stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost_estimate": 0.0
        }

    def switch_provider(self, new_provider: LLMProvider):
        """Switch to a different LLM provider"""
        logger.info(f"Switching LLM provider from {self.provider.get_provider_name()} to {new_provider.get_provider_name()}")
        self.provider = new_provider

    async def generate_response(
        self,
        messages: List[LLMMessage],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate response using current provider"""

        start_time = time.time()

        try:
            response = await self.provider.chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            # Update usage stats
            self.usage_stats["total_requests"] += 1
            self.usage_stats["total_tokens"] += response.usage.get("total_tokens", 0)

            # Rough cost estimate (OpenAI GPT-3.5-turbo pricing)
            cost_per_token = 0.000002  # $0.002 per 1K tokens
            self.usage_stats["total_cost_estimate"] += response.usage.get("total_tokens", 0) * cost_per_token

            response_time = time.time() - start_time
            logger.info(f"LLM response generated in {response_time:.2f}s using {self.provider.get_provider_name()}")

            return response

        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            raise

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            **self.usage_stats,
            "provider": self.provider.get_provider_name()
        }


# Global LLM service instance - will be configured in main app
llm_service: Optional[LLMService] = None


def initialize_llm_service(provider: LLMProvider):
    """Initialize the global LLM service"""
    global llm_service
    llm_service = LLMService(provider)


def get_llm_service() -> LLMService:
    """Get the global LLM service instance"""
    if llm_service is None:
        raise RuntimeError("LLM service not initialized. Call initialize_llm_service() first.")
    return llm_service