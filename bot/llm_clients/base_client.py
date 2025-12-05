# bot/llm_clients/base_client.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseLLMClient(ABC):
    """
    Abstrakcyjna klasa bazowa dla wszystkich klientów modeli językowych.
    Definiuje wspólny interfejs, który musi być zaimplementowany przez każdego klienta.
    """

    @abstractmethod
    def __init__(self, model_name: Optional[str] = None, **kwargs):
        """
        Inicjalizuje klienta.

        Args:
            model_name: Nazwa modelu do użycia.
            **kwargs: Dodatkowe argumenty specyficzne dla klienta.
        """
        self.model_name = model_name

    @abstractmethod
    def generate_text(
        self, prompt: str, temperature: float = 0.7, max_tokens: Optional[int] = None
    ) -> str:
        """
        Generuje tekst na podstawie promptu.

        Args:
            prompt: Prompt dla modelu.
            temperature: Temperatura generowania.
            max_tokens: Maksymalna liczba tokenów.

        Returns:
            Wygenerowany tekst.
        """
        pass

    @abstractmethod
    def analyze_image(self, image_url: str, prompt: str) -> Dict[str, Any]:
        """
        Analizuje obraz na podstawie dostarczonego promptu.

        Args:
            image_url: URL obrazu do analizy.
            prompt: Prompt zawierający instrukcje dla modelu.

        Returns:
            Słownik z przeanalizowanymi danymi.
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Zwraca informacje o używanym modelu.

        Returns:
            Słownik z informacjami o modelu.
        """
        pass
