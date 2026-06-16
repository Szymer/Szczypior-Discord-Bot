# bot/llm_clients/__init__.py

from config_manager import config_manager
from .anthropic_client import AnthropicClient
from .base_client import BaseLLMClient
from .gemini_client import GeminiClient
from .openai_client import OpenAIClient
from .openrouter_client import OpenRouterClient

# Mapowanie nazw dostawców na klasy klientów
CLIENT_MAP = {
    "gemini": GeminiClient,
    "anthropic": AnthropicClient,
    "openai": OpenAIClient,
    "openrouter": OpenRouterClient,
}


def get_llm_client_for_provider(provider: str, **kwargs) -> BaseLLMClient:
    """Tworzy klienta dla konkretnego providera."""
    normalized_provider = (provider or "").lower().strip()
    llm_config = config_manager.get_llm_config(normalized_provider)
    if not llm_config:
        raise ValueError(
            f"Brak konfiguracji dla dostawcy LLM: '{normalized_provider}' w config.json."
        )

    client_class = CLIENT_MAP.get(normalized_provider)
    if not client_class:
        raise ValueError(
            f"Nieobsługiwany dostawca LLM: '{normalized_provider}'. Dostępni dostawcy: {list(CLIENT_MAP.keys())}"
        )

    constructor_args = {
        "model_name": llm_config.get("default_model"),
        "generation_params": config_manager.get_llm_generation_params(normalized_provider),
    }
    constructor_args.update(kwargs)
    return client_class(**constructor_args)


def get_llm_clients(provider_order: list[str]) -> list[BaseLLMClient]:
    """Tworzy listę klientów LLM w podanej kolejności fallbacku."""
    clients: list[BaseLLMClient] = []
    for provider in provider_order:
        clients.append(get_llm_client_for_provider(provider))
    return clients


def get_llm_client(**kwargs) -> BaseLLMClient:
    """
    Fabryka do tworzenia instancji klienta LLM.
    Konfiguracja jest pobierana z ConfigManager.
    Można ją nadpisać, przekazując argumenty do fabryki.

    Args:
        **kwargs: Argumenty do nadpisania konfiguracji (np. model_name).

    Returns:
        Instancja odpowiedniego klienta LLM.
    """
    provider = config_manager.get_llm_provider()
    return get_llm_client_for_provider(provider, **kwargs)
