# bot/config_manager.py
import json
import os
from typing import Any, Dict, Optional


class ConfigManager:
    """
    Zarządza konfiguracją aplikacji, wczytując ją z pliku JSON
    i pozwalając na nadpisywanie wartości przez zmienne środowiskowe.
    Wzorzec Singleton zapewniający jedną instancję w całej aplikacji.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_path: str = 'config.json'):
        if not hasattr(self, '_initialized'):
            self._initialized = False

        if self._initialized:
            return
        
        self.config_path = config_path
        self.config = self._load_config()
        self._activity_keywords: Optional[Dict[str, list[str]]] = None
        self._initialized = True
        print("✅ ConfigManager zainicjalizowany.")

    def _load_config(self) -> Dict[str, Any]:
        """Wczytuje plik konfiguracyjny JSON."""
        try:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            abs_config_path = os.path.join(project_root, self.config_path)
            
            with open(abs_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Waliduj konfiguracj\u0119
            self._validate_config(config)
            return config
            
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Plik konfiguracyjny '{abs_config_path}' nie zosta\u0142 znaleziony.") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Plik konfiguracyjny '{abs_config_path}' jest niepoprawnym plikiem JSON.") from exc
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Waliduje struktur\u0119 konfiguracji."""
        required_keys = ['activity_keywords', 'llm_providers']
        
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Brak wymaganego klucza '{key}' w config.json")
        
        # Sprawd\u017a czy s\u0105 skonfigurowane przynajmniej jedne LLM providers
        if not config['llm_providers']:
            raise ValueError("Brak konfiguracji LLM providers w config.json")
        
        # Sprawd\u017a czy domy\u015blny provider istnieje
        default_provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        if default_provider not in config['llm_providers']:
            raise ValueError(
                f"Domy\u015blny provider '{default_provider}' nie jest skonfigurowany w config.json. "
                f"Dost\u0119pni providerzy: {list(config['llm_providers'].keys())}"
            )

    def get_llm_provider(self) -> str:
        """Pobiera nazwę dostawcy LLM ze zmiennych środowiskowych lub zwraca domyślną."""
        return os.getenv("LLM_PROVIDER", "gemini").lower()

    def get_llm_config(self, provider: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Pobiera pełną konfigurację dla danego dostawcy LLM.
        Jeśli provider nie jest podany, używa domyślnego.
        """
        if provider is None:
            provider = self.get_llm_provider()
        return self.config.get("llm_providers", {}).get(provider)

    def get_llm_generation_params(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Pobiera parametry generowania dla danego dostawcy,
        uwzględniając nadpisania ze zmiennych środowiskowych.
        """
        if provider is None:
            provider = self.get_llm_provider()
            
        provider_config = self.get_llm_config(provider)
        if not provider_config:
            return {}

        params = provider_config.get("generation_params", {})
        
        # Nadpisywanie ze zmiennych środowiskowych
        params['temperature'] = float(os.getenv('LLM_TEMPERATURE', params.get('temperature', 0.7)))
        params['max_tokens'] = int(os.getenv('LLM_MAX_TOKENS', params.get('max_tokens', 2048)))
        
        return params

    def get_prompt(self, prompt_name: str, prompt_type: str = "system_prompt", provider: Optional[str] = None) -> Optional[str]:
        """
        Pobiera konkretny szablon promptu dla danego dostawcy.
        
        Args:
            prompt_name: Nazwa promptu (np. 'activity_analysis').
            prompt_type: Typ promptu (np. 'system_prompt').
            provider: Nazwa dostawcy (np. 'gemini'). Jeśli None, używa domyślnego.
            
        Returns:
            Szablon promptu jako string lub None.
        """
        if provider is None:
            provider = self.get_llm_provider()
            
        provider_config = self.get_llm_config(provider)
        if not provider_config:
            return None
            
        return provider_config.get("prompts", {}).get(prompt_name, {}).get(prompt_type)
    
    def get_llm_prompts(self, provider: Optional[str] = None) -> Dict[str, str]:
        """
        Zwraca wszystkie prompty systemowe dla danego dostawcy LLM.
        
        Args:
            provider: Nazwa dostawcy (np. 'gemini'). Jeśli None, używa domyślnego.
            
        Returns:
            Słownik z promptami (np. {'activity_analysis': '...', 'motivational_comment': '...'}).
        """
        if provider is None:
            provider = self.get_llm_provider()
            
        provider_config = self.get_llm_config(provider)
        if not provider_config:
            return {}
        
        prompts_config = provider_config.get("prompts", {})
        
        # Wyciągnij system_prompt z każdego promptu
        simplified_prompts = {}
        for prompt_name, prompt_data in prompts_config.items():
            if isinstance(prompt_data, dict) and "system_prompt" in prompt_data:
                simplified_prompts[prompt_name] = prompt_data["system_prompt"]
            elif isinstance(prompt_data, str):
                simplified_prompts[prompt_name] = prompt_data
        
        return simplified_prompts

    def get_activity_keywords(self) -> Dict[str, list[str]]:
        """Zwraca słownik słów kluczowych przypisanych do typów aktywności."""
        if self._activity_keywords is None:
            raw_keywords = self.config.get("activity_keywords", {})
            # Upewnij się, że wartości są listami stringów
            self._activity_keywords = {
                activity: [str(keyword) for keyword in keywords]
                for activity, keywords in raw_keywords.items()
                if isinstance(keywords, list)
            }
        return self._activity_keywords

# Utworzenie globalnej instancji, aby była łatwo dostępna w całej aplikacji
config_manager = ConfigManager()
