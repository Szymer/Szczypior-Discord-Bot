"""Thread-safe sliding-window rate limiter dla modeli LLM."""

import os
import threading
import time
from collections import deque
from typing import Dict, Optional


class ModelRateLimiter:
    """
    Sliding-window rate limiter ograniczający liczbę zapytań per model per minuta (RPM).

    Używa threading.Lock zamiast asyncio, ponieważ wywołania Gemini API
    wykonywane są synchronicznie w thread pool (run_in_executor).

    Konfiguracja przez zmienną środowiskową GOOGLE_RPM:
        GOOGLE_RPM=models/gemma-3-27b-it:30,models/gemini-3.1-flash-lite:15
    """

    def __init__(self, rpm_map: Dict[str, int]):
        """
        Args:
            rpm_map: Mapa {model_name: rpm_limit} — modele bez wpisu nie mają limitu.
        """
        self._rpm_map: Dict[str, int] = dict(rpm_map)
        self._windows: Dict[str, deque] = {m: deque() for m in rpm_map}
        self._locks: Dict[str, threading.Lock] = {m: threading.Lock() for m in rpm_map}
        self._counters: Dict[str, int] = {m: 0 for m in rpm_map}
        # Zabezpiecza dynamiczne dodawanie nowych modeli
        self._registry_lock = threading.Lock()

    @classmethod
    def from_env(cls, env_var: str = "GOOGLE_RPM") -> "ModelRateLimiter":
        """
        Tworzy instancję na podstawie zmiennej środowiskowej.

        Format: GOOGLE_RPM=models/gemma-3-27b-it:30,models/gemini-3.1-flash-lite:15
        """
        raw = os.getenv(env_var, "").strip()
        rpm_map: Dict[str, int] = {}
        if raw:
            for entry in raw.split(","):
                entry = entry.strip()
                if ":" not in entry:
                    continue
                # Użyj rpartition żeby nie rozdzielić "models/name:rpm"
                model, _, rpm_str = entry.rpartition(":")
                model = model.strip()
                try:
                    rpm = int(rpm_str.strip())
                    if model and rpm > 0:
                        rpm_map[model] = rpm
                except ValueError:
                    pass
        return cls(rpm_map)

    def _ensure_model(self, model_name: str) -> None:
        """Dynamicznie rejestruje model, jeśli nie był znany przy inicjalizacji."""
        if model_name not in self._locks:
            with self._registry_lock:
                if model_name not in self._locks:
                    self._windows[model_name] = deque()
                    self._locks[model_name] = threading.Lock()
                    self._counters[model_name] = 0

    def get_rpm_limit(self, model_name: str) -> Optional[int]:
        """Zwraca zdefiniowany limit RPM dla modelu (None = brak limitu)."""
        return self._rpm_map.get(model_name)

    def get_stats(self) -> Dict[str, Dict]:
        """Zwraca statystyki: limit, zapytania w ostatniej minucie, łączna liczba."""
        stats: Dict[str, Dict] = {}
        for model in list(self._rpm_map.keys()):
            lock = self._locks[model]
            with lock:
                now = time.monotonic()
                window = self._windows[model]
                while window and window[0] <= now - 60.0:
                    window.popleft()
                stats[model] = {
                    "rpm_limit": self._rpm_map[model],
                    "requests_last_minute": len(window),
                    "total_requests": self._counters[model],
                }
        return stats

    def try_acquire(self, model_name: str) -> bool:
        """
        Próbuje zająć slot RPM dla modelu.

        Zwraca True jeśli slot był wolny (request zarejestrowany).
        Zwraca False jeśli limit wyczerpany — bez blokowania wątku.
        Modele bez zdefiniowanego limitu zawsze zwracają True.
        """
        self._ensure_model(model_name)
        rpm = self._rpm_map.get(model_name)

        with self._locks[model_name]:
            now = time.monotonic()
            window = self._windows[model_name]

            # Wyrzuć wpisy starsze niż 60 s
            while window and window[0] <= now - 60.0:
                window.popleft()

            if rpm and len(window) >= rpm:
                return False

            window.append(now)
            self._counters[model_name] += 1
            return True
