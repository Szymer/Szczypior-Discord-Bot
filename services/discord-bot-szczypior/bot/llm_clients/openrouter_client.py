import os
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)

from .base_client import BaseLLMClient


class OpenRouterClient(BaseLLMClient):
    """Klient do komunikacji z OpenRouter API."""

    _DEFAULT_MODEL = "qwen/qwen2.5-vl-72b-instruct:free"
    _DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
    _DEFAULT_FALLBACK_MODELS = [
        "meta-llama/llama-3.2-11b-vision-instruct:free",
        "nvidia/nemotron-nano-12b-v2-vl:free",
    ]

    def __init__(
        self,
        model_name: Optional[str] = None,
        generation_params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(model_name, **kwargs)

        api_key = os.getenv("OPEN_ROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError(
                "Nie znaleziono klucza OPEN_ROUTER_API_KEY ani OPENROUTER_API_KEY w zmiennych środowiskowych."
            )

        self.model_name = (self.model_name or self._DEFAULT_MODEL).strip()
        self.generation_params = generation_params or {}

        base_url = os.getenv("OPENROUTER_BASE_URL", self._DEFAULT_BASE_URL).strip()
        self._api_key = api_key
        self._base_url = base_url

        self._extra_headers: Dict[str, str] = {}
        http_referer = os.getenv("OPENROUTER_HTTP_REFERER", "").strip()
        app_title = os.getenv("OPENROUTER_APP_TITLE", "").strip()
        if http_referer:
            self._extra_headers["HTTP-Referer"] = http_referer
        if app_title:
            self._extra_headers["X-Title"] = app_title

    def _fallback_models(self) -> list[str]:
        env_raw = os.getenv("OPENROUTER_FALLBACK_MODELS", "").strip()
        if env_raw:
            return [item.strip() for item in env_raw.split(",") if item.strip()]
        return list(self._DEFAULT_FALLBACK_MODELS)

    def _extract_text_content(self, content: Any) -> Optional[str]:
        if isinstance(content, str) and content.strip():
            return content

        if isinstance(content, list):
            text_parts = [
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            merged = "".join(text_parts).strip()
            if merged:
                return merged

        return None

    def generate_text(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_instruction: Optional[str] = None,
    ) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt nie może być pusty.")

        messages = []
        if system_instruction:
            messages.append(SystemMessage(content=system_instruction))
        messages.append(HumanMessage(content=prompt))

        resolved_temperature = (
            temperature
            if temperature is not None
            else self.generation_params.get("temperature", 0.7)
        )
        resolved_max_tokens = (
            max_tokens
            if max_tokens is not None
            else self.generation_params.get("max_tokens", 2048)
        )

        model_kwargs: Dict[str, Any] = {}
        if self._extra_headers:
            model_kwargs["extra_headers"] = self._extra_headers

        candidate_models: list[str] = [self.model_name]
        for model in self._fallback_models():
            if model not in candidate_models:
                candidate_models.append(model)

        last_error: Optional[Exception] = None
        for candidate in candidate_models:
            try:
                llm = ChatOpenAI(
                    model=candidate,
                    api_key=self._api_key,
                    base_url=self._base_url,
                    temperature=float(resolved_temperature),
                    max_tokens=int(resolved_max_tokens),
                    model_kwargs=model_kwargs,
                )

                response = llm.invoke(messages)
                content = self._extract_text_content(getattr(response, "content", None))
                if content:
                    if candidate != self.model_name:
                        self.model_name = candidate
                    return content

                last_error = ValueError(
                    f"Model {candidate} zwrócił pustą treść odpowiedzi."
                )
            except (
                APIConnectionError,
                APIError,
                APITimeoutError,
                AuthenticationError,
                BadRequestError,
                ConflictError,
                InternalServerError,
                NotFoundError,
                PermissionDeniedError,
                RateLimitError,
                UnprocessableEntityError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as exc:
                last_error = exc

        if last_error:
            raise RuntimeError(
                "OpenRouter (LangChain) nie zwrócił odpowiedzi na żadnym modelu "
                f"({candidate_models}). Ostatni błąd: {last_error}"
            ) from last_error

        raise RuntimeError("OpenRouter (LangChain) nie miał dostępnych modeli do użycia.")

    def analyze_image(
        self,
        image_url: str,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError(
            "Metoda `analyze_image` nie jest jeszcze zaimplementowana dla OpenRouterClient."
        )

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "OpenRouter",
            "model_name": self.model_name,
            "base_url": self._base_url,
        }