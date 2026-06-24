import json
import time
import logging
from typing import Optional

from openai import OpenAI, RateLimitError

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self.client = None
        self.provider = (settings.llm_provider or "openai").lower()
        self.model = settings.llm_model or settings.openai_model
        self._init_client()

    def _init_client(self):
        api_key = settings.llm_api_key or settings.openai_api_key
        base_url = settings.llm_base_url or settings.openai_base_url
        
        if not api_key:
            return

        if self.provider == "anthropic":
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=api_key)
            except ImportError:
                logger.error("Anthropic SDK not installed. Run 'pip install anthropic'. Falling back to OpenAI compatible API.")
                self.provider = "openai"
                
        elif self.provider == "google":
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.client = genai
            except ImportError:
                logger.error("google-generativeai SDK not installed. Run 'pip install google-generativeai'. Falling back to OpenAI compatible API.")
                self.provider = "openai"

        # Default fallback to OpenAI-compatible
        if self.provider not in ("anthropic", "google"):
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            self.client = OpenAI(**kwargs)

    @property
    def available(self) -> bool:
        return self.client is not None

    def chat(self, messages: list[dict], response_format: Optional[dict] = None, max_tokens: int = 512) -> Optional[str]:
        if not self.available:
            return None

        # --- Anthropic Chat ---
        if self.provider == "anthropic":
            try:
                system_prompt = ""
                user_messages = []
                for m in messages:
                    if m["role"] == "system":
                        system_prompt += m["content"] + "\n"
                    else:
                        user_messages.append({"role": m["role"], "content": m["content"]})
                
                kwargs = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": user_messages,
                }
                if system_prompt:
                    kwargs["system"] = system_prompt
                
                response = self.client.messages.create(**kwargs)
                content = response.content[0].text
                return self._clean_response(content) if content else None
            except Exception as e:
                logger.error(f"Anthropic API call failed: {e}")
                return None

        # --- Google Generative AI (Gemini) Chat ---
        elif self.provider == "google":
            try:
                prompt = ""
                for m in messages:
                    role_label = "User" if m["role"] == "user" else "Model" if m["role"] == "assistant" else "System Instruction"
                    prompt += f"{role_label}: {m['content']}\n"
                prompt += "Model Response:"
                
                generation_config = {}
                if response_format and response_format.get("type") == "json_object":
                    generation_config["response_mime_type"] = "application/json"
                    
                model_inst = self.client.GenerativeModel(self.model)
                response = model_inst.generate_content(prompt, generation_config=generation_config)
                content = response.text
                return self._clean_response(content) if content else None
            except Exception as e:
                logger.error(f"Google Generative AI call failed: {e}")
                return None

        # --- OpenAI (or compatible NIM/Groq/Ollama) Chat ---
        else:
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
                except Exception as e:
                    logger.error(f"OpenAI API call failed: {e}")
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
