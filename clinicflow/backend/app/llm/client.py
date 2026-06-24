import json
import time
from typing import Optional

from openai import OpenAI, RateLimitError

from app.core.config import settings


class LLMClient:
    def __init__(self):
        self.client = None
        self.model = settings.openai_model
        self._init_client()

    def _init_client(self):
        if settings.openai_api_key:
            kwargs = {"api_key": settings.openai_api_key}
            if settings.openai_base_url:
                kwargs["base_url"] = settings.openai_base_url
            self.client = OpenAI(**kwargs)

    @property
    def available(self) -> bool:
        return self.client is not None

    def chat(self, messages: list[dict], response_format: Optional[dict] = None, max_tokens: int = 512) -> Optional[str]:
        if not self.available:
            return None
        for attempt in range(3):
            try:
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                }
                if response_format:
                    kwargs["response_format"] = response_format
                response = self.client.chat.completions.create(**kwargs, timeout=15)
                content = response.choices[0].message.content
                return self._clean_response(content) if content else None
            except RateLimitError:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                return None
            except Exception:
                return None
            return None

    def _clean_response(self, content: str) -> str:
        content = content.strip()
        for prefix in ("Reply:", "Assistant:", "Response:", "AI:"):
            if content.lower().startswith(prefix.lower()):
                content = content[len(prefix):].strip()
        return content

    def extract_json(self, messages: list[dict]) -> Optional[dict]:
        content = self.chat(messages, response_format={"type": "json_object"}, max_tokens=512)
        if not content:
            return None
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
            return None
        except (json.JSONDecodeError, ValueError):
            return None


llm_client = LLMClient()
