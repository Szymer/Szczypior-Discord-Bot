# bot/llm_clients/__init__.py
import os
from typing import Type, Optional
from ..config_manager import config_manager
from .base_client import BaseLLMClient
from .gemini_client import GeminiClient
from .anthropic_client import AnthropicClient
from .openai_client import OpenAIClient

# Mapowanie nazw dostawców na klasy klientów
CLIENT_MAP = {
    "gemini": GeminiClient,
    "anthropic": AnthropicClient,
    "openai": OpenAIClient,
}

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
    llm_config = config_manager.get_llm_config(provider)

    if not llm_config:
        raise ValueError(f"Brak konfiguracji dla dostawcy LLM: '{provider}' w config.json.")

    client_class = CLIENT_MAP.get(provider)
    
    if not client_class:
        raise ValueError(f"Nieobsługiwany dostawca LLM: '{provider}'. Dostępni dostawcy: {list(CLIENT_MAP.keys())}")

    # Przygotuj argumenty dla konstruktora klienta
    constructor_args = {}
    
    # 1. Użyj modelu z config.json jako domyślnego
    constructor_args['model_name'] = llm_config.get('default_model')
    
    # 2. Pobierz parametry generowania
    constructor_args['generation_params'] = config_manager.get_llm_generation_params(provider)

    # 3. Nadpisz argumenty tymi przekazanymi do fabryki (np. model_name z polecenia)
    constructor_args.update(kwargs)
        
    return client_class(**constructor_args)
