import logging
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class LLMMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def to_openai(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}

    def to_anthropic(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(
        self,
        messages: List[LLMMessage],
        max_tokens: int = 1000,
        temperature: float = 0.3,
        **kwargs,
    ) -> str:
        """Generate a response from the LLM"""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get LLM provider name"""
        pass


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai

            self._client = openai.AsyncOpenAI(api_key=self.api_key)

        return self._client

    async def generate_response(
        self,
        messages: List[LLMMessage],
        max_tokens: int = 1000,
        temperature: float = 0.3,
        **kwargs,
    ) -> str:
        client = self._get_client()

        openai_messages = [msg.to_openai() for msg in messages]

        response = await client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

        content = response.choices[0].message.content

        return content

    def get_provider_name(self) -> str:
        return f"openai-{self.model}"


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)

        return self._client

    async def generate_response(
        self,
        messages: List[LLMMessage],
        max_tokens: int = 1000,
        temperature: float = 0.3,
        **kwargs,
    ) -> str:
        client = self._get_client()

        system_message = None
        conversation_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                conversation_messages.append(msg.to_anthropic())

        response = await client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_message,
            messages=conversation_messages,
            **kwargs,
        )

        content = response.content[0].text

        return content

    def get_provider_name(self) -> str:
        return f"anthropic-{self.model}"


class MockLLMProvider(LLMProvider):
    def __init__(self):
        self.responses = [
            "Based on the error description, this appears to be a database connection timeout issue. I recommend checking: 1) Database server status 2) Connection pool configuration 3) Network connectivity between services.",
            "This looks like a memory-related issue. The symptoms suggest a potential memory leak. Consider: 1) Analyzing heap dumps 2) Reviewing recent code changes 3) Monitoring memory usage patterns.",
            "The performance degradation suggests a bottleneck in the system. To diagnose: 1) Check database query performance 2) Review system resource utilization 3) Analyze request patterns.",
            "This appears to be an authentication/authorization issue. Steps to resolve: 1) Verify user permissions 2) Check authentication service logs 3) Review access control configuration.",
        ]
        self.response_index = 0

    async def generate_response(
        self,
        messages: List[LLMMessage],
        max_tokens: int = 1000,
        temperature: float = 0.3,
        **kwargs,
    ) -> str:

        content = self.responses[self.response_index % len(self.responses)]
        self.response_index += 1

        return content

    def get_provider_name(self) -> str:
        return "mock-llm"


class LLMService:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def generate_response(
        self,
        messages: List[LLMMessage],
        max_tokens: int = 1000,
        temperature: float = 0.3,
        **kwargs,
    ) -> str:
        start_time = time.time()

        response = await self.provider.generate_response(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

        response_time = time.time() - start_time
        logger.info(
            f"LLM response generated in {response_time:.2f}s using {self.provider.get_provider_name()}"
        )

        return response


llm_service: Optional[LLMService] = None


def initialize_llm_service(provider: LLMProvider):
    global llm_service
    if not llm_service:
        llm_service = LLMService(provider)


def get_llm_service() -> LLMService:
    if llm_service is None:
        raise RuntimeError("LLM service not initialized.")
    return llm_service
