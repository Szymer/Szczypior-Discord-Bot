# bot/orchestrator.py
import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import discord

from api_menager import APIManager, APIManagerError, APIManagerHTTPError
from config_manager import config_manager
from constants import ACTIVITY_TYPES
from exceptions import (
    ConfigurationError,
    LLMAnalysisError,
    LLMTimeoutError,
)
from libs.shared.schemas.challenge import ChallengeRead
from utils import get_display_name, parse_distance

logger = logging.getLogger(__name__)


class BotOrchestrator:
    """Orkiestruje logikę biznesową bota."""

    def __init__(
        self,
        bot,
        api_manager: Optional[APIManager] = None,
        llm_clients: Optional[List[Any]] = None,
        sheets_manager: Any = None,
    ):
        self.bot = bot
        self.llm_clients: List[Any] = [c for c in (llm_clients or []) if c is not None]
        self.api_manager = api_manager
        # kept for backward-compat with sync_chat_history (not called in normal flow)
        self.sheets_manager = sheets_manager
        self.activity_keywords = config_manager.get_activity_keywords()
        # Cache: challenge_id -> activity types dict (same shape as ACTIVITY_TYPES)
        self._rules_cache: dict[int, dict[str, Any]] = {}
        # Cache: challenge_id -> effective points_rules dict
        self._points_rules_cache: dict[int, dict[str, Any]] = {}
        # Startup sync tunables: keep cache bounded to avoid memory spikes.
        self._startup_sync_user_history_limit = max(
            50,
            int(os.getenv("STARTUP_SYNC_USER_HISTORY_LIMIT", "500")),
        )
        self._startup_sync_max_user_iid_cache = max(
            50,
            int(os.getenv("STARTUP_SYNC_MAX_USER_IID_CACHE", "1000")),
        )

    @staticmethod
    def _is_temporary_llm_error(error_text: str) -> bool:
        text = (error_text or "").lower()
        return any(
            token in text
            for token in (
                "503",
                "unavailable",
                "high demand",
                "resource_exhausted",
                "rate limit",
                "quota exceeded",
                "backend error",
            )
        )

    def _llm_clients_for_failover(self) -> list[tuple[str, Any]]:
        clients: list[tuple[str, Any]] = []
        for idx, client in enumerate(self.llm_clients):
            if client is None:
                continue
            try:
                model_info = client.get_model_info() if hasattr(client, "get_model_info") else {}
                provider_name = str(model_info.get("provider") or model_info.get("model_name") or f"client_{idx}")
            except Exception:
                provider_name = f"client_{idx}"
            clients.append((provider_name, client))

        return clients

    @staticmethod
    def _prompt_provider() -> str:
        order = config_manager.get_llm_client_order()
        if order:
            return order[0]
        return config_manager.get_llm_provider()

    def _first_client_with_method(self, method_name: str) -> Optional[Any]:
        for _, client in self._llm_clients_for_failover():
            if hasattr(client, method_name):
                return client
        return None

    def _should_try_next_client_from_result(self, result: Optional[Dict[str, Any]]) -> bool:
        if not isinstance(result, dict):
            return False

        comment = str(result.get("komentarz") or "")
        if not comment:
            return False

        return self._is_temporary_llm_error(comment)

    async def _analyze_image_with_failover(
        self,
        image_url: str,
        prompt: str,
        system_prompt: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        clients = self._llm_clients_for_failover()
        last_result: Optional[Dict[str, Any]] = None

        for client_name, client in clients:
            try:
                result = client.analyze_image(
                    image_url,
                    prompt,
                    system_instruction=system_prompt,
                )
            except Exception as exc:
                logger.warning(
                    "Image analysis failed on LLM client",
                    exc_info=True,
                    extra={"client": client_name},
                )
                if self._is_temporary_llm_error(str(exc)):
                    continue
                last_result = {
                    "typ_aktywnosci": None,
                    "dystans": None,
                    "komentarz": f"Błąd analizy obrazu: {exc}",
                }
                continue

            if self._should_try_next_client_from_result(result):
                logger.warning(
                    "Temporary LLM error detected in analysis result, trying fallback client",
                    extra={"client": client_name, "comment": result.get("komentarz")},
                )
                last_result = result
                continue

            return result

        return last_result

    async def _generate_text_with_failover(
        self,
        prompt: str,
        system_prompt: Optional[str],
    ) -> Optional[str]:
        clients = self._llm_clients_for_failover()
        loop = asyncio.get_event_loop()

        for client_name, client in clients:
            try:
                response = await loop.run_in_executor(
                    None,
                    lambda c=client: c.generate_text(
                        prompt,
                        system_instruction=system_prompt,
                    ),
                )
            except Exception as exc:
                logger.warning(
                    "Text analysis failed on LLM client",
                    exc_info=True,
                    extra={"client": client_name},
                )
                if self._is_temporary_llm_error(str(exc)):
                    continue
                continue

            if response and response.strip():
                return response

        return None

    def _get_activity_types(
        self,
        channel_id: Optional[str] = None,
        challenge_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Zwraca słownik reguł aktywności dla danego challenge'u.
        Kolejność rozwiązywania:
          1. challenge_id podane wprost
          2. challenge_id z globalnej mapy channel_to_challenge (via channel_id)
          3. Fallback na stałą ACTIVITY_TYPES
        Wyniki są cachowane per challenge_id.
        """
        if challenge_id is None and channel_id:
            try:
                channel_to_challenge = self.get_channel_to_challenge_mapping()
                challenge_id = channel_to_challenge.get(channel_id)
            except Exception as e:
                logger.error("Błąd podczas pobierania mapowania kanałów", exc_info=True)
                pass

        if challenge_id is None:
            return ACTIVITY_TYPES

        if challenge_id in self._rules_cache:
            return self._rules_cache[challenge_id]

        if self.api_manager:
            try:
                rules = self.api_manager.get_activity_rules(challenge_id)
                rules_dict = {
                    r.activity_type: {
                        "emoji": r.emoji,
                        "base_points": r.base_points,
                        "unit": r.unit,
                        "min_distance": float(r.min_distance),
                        "bonuses": r.bonuses,
                        "display_name": r.display_name,
                    }
                    for r in rules
                }
                if rules_dict:
                    self._rules_cache[challenge_id] = rules_dict
                    logger.info(
                        "Loaded activity rules from API",
                        extra={"challenge_id": challenge_id, "rule_count": len(rules_dict)},
                    )
                    return rules_dict
            except Exception:
                logger.warning(
                    "Failed to fetch activity rules from API, using defaults",
                    exc_info=True,
                    extra={"challenge_id": challenge_id},
                )

        return ACTIVITY_TYPES

    @staticmethod
    def _to_float_or_default(value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_int_or_default(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _normalize_points_rules(self, raw_points_rules: Optional[dict[str, Any]]) -> dict[str, Any]:
        default_rules = config_manager.get_points_rules()
        if not isinstance(raw_points_rules, dict):
            raw_points_rules = {}

        weight_raw = raw_points_rules.get("weight_bonus")
        elevation_raw = raw_points_rules.get("elevation_bonus")

        return {
            "weight_bonus": {
                "min_weight_kg": self._to_float_or_default(
                    weight_raw.get("min_weight_kg") if isinstance(weight_raw, dict) else None,
                    float(default_rules["weight_bonus"]["min_weight_kg"]),
                ),
                "distance_points_multiplier": self._to_float_or_default(
                    weight_raw.get("distance_points_multiplier") if isinstance(weight_raw, dict) else None,
                    float(default_rules["weight_bonus"]["distance_points_multiplier"]),
                ),
            },
            "elevation_bonus": {
                "meters_step": self._to_int_or_default(
                    elevation_raw.get("meters_step") if isinstance(elevation_raw, dict) else None,
                    int(default_rules["elevation_bonus"]["meters_step"]),
                ),
                "points_per_step": self._to_int_or_default(
                    elevation_raw.get("points_per_step") if isinstance(elevation_raw, dict) else None,
                    int(default_rules["elevation_bonus"]["points_per_step"]),
                ),
            },
        }

    def _get_points_rules(self, challenge_id: Optional[int]) -> dict[str, Any]:
        if challenge_id is None:
            return self._normalize_points_rules(None)

        if challenge_id in self._points_rules_cache:
            return self._points_rules_cache[challenge_id]

        raw_points_rules: Optional[dict[str, Any]] = None
        if self.api_manager:
            try:
                challenge = self.api_manager.get_challenge(challenge_id)
                if isinstance(challenge.rules, dict):
                    raw_points_rules = challenge.rules.get("points_rules")
            except Exception:
                logger.warning(
                    "Failed to fetch challenge points_rules from API, using defaults",
                    exc_info=True,
                    extra={"challenge_id": challenge_id},
                )

        effective_rules = self._normalize_points_rules(raw_points_rules)
        self._points_rules_cache[challenge_id] = effective_rules
        return effective_rules

    def _create_unique_id(self, message: discord.Message) -> str:
        """
        Tworzy unikalny ID dla wiadomości Discord (IID).

        Args:
            message: Wiadomość Discord

        Returns:
            Unikalny ID w formacie: {timestamp_int}_{message_id}
        """
        timestamp_int = int(message.created_at.timestamp())
        return f"{timestamp_int}_{message.id}"

    def _extract_time_from_comment(self, comment: str) -> Optional[float]:
        """
        Ekstrahuje czas aktywności z komentarza (format: HH:MM:SS lub MM:SS).

        Args:
            comment: Komentarz od Gemini

        Returns:
            Czas w minutach lub None
        """
        # Szukaj różnych formatów czasu
        patterns = [
            r"(\d{1,2})\s*(?:godzin[ęya]?|hour|h|godz\.?)[,\s]+(\d{1,2})\s*(?:minut|minute|min|m)",  # "1 godzinę, 12 minut"
            r"(\d{1,2}):(\d{2}):(\d{2})",  # "1:12:56"
            r"(\d{1,2})h\s*(\d{1,2})m",  # "1h 12m"
            r"(\d{2,3}):(\d{2})",  # "72:56" (minuty:sekundy)
        ]

        for pattern in patterns:
            match = re.search(pattern, comment, re.IGNORECASE)
            if match:
                groups = match.groups()

                if len(groups) == 3:  # HH:MM:SS
                    hours = int(groups[0])
                    minutes = int(groups[1])
                    seconds = int(groups[2])
                    total_minutes = hours * 60 + minutes + seconds / 60
                    return round(total_minutes, 1)
                elif len(groups) == 2:
                    # Sprawdź czy to godziny+minuty czy minuty+sekundy
                    val1 = int(groups[0])
                    val2 = int(groups[1])

                    # Jeśli pierwszy pattern (godziny i minuty w tekście)
                    if "godzin" in pattern or "hour" in pattern:
                        total_minutes = val1 * 60 + val2
                    # Jeśli val1 > 23, to prawdopodobnie są to minuty
                    elif val1 > 23:
                        total_minutes = val1 + val2 / 60
                    # W przeciwnym razie to godziny:minuty
                    else:
                        total_minutes = val1 * 60 + val2

                    return round(total_minutes, 1)

        return None

    def _convert_time_to_cardio_distance(self, time_minutes: float) -> float:
        """
        Konwertuje czas aktywności cardio na ekwiwalentny dystans.
        Założenie: średnie tempo cardio to ~10 minut/km.

        Args:
            time_minutes: Czas w minutach

        Returns:
            Dystans w km
        """
        # Dla innych aktywności cardio (piłka, siłownia, itp.) zakładamy
        # że 10 minut aktywności = 1 km ekwiwalentu
        distance_km = time_minutes / 10.0
        return round(distance_km, 2)

    def _parse_analysis_time_to_minutes(self, raw_time: Any) -> Optional[int]:
        """Konwertuje różne formaty pola `czas` z analizy do liczby minut (int)."""
        if raw_time in (None, ""):
            return None

        if isinstance(raw_time, (int, float)):
            minutes = int(float(raw_time))
            return minutes if minutes >= 0 else None

        if not isinstance(raw_time, str):
            return None

        text = raw_time.strip().lower()
        if not text:
            return None

        # Format HH:MM:SS
        match_hms = re.fullmatch(r"(\d{1,3}):(\d{1,2}):(\d{1,2})", text)
        if match_hms:
            h, m, s = (int(part) for part in match_hms.groups())
            total_minutes = h * 60 + m + (1 if s >= 30 else 0)
            return total_minutes

        # Format MM:SS
        match_ms = re.fullmatch(r"(\d{1,4}):(\d{1,2})", text)
        if match_ms:
            m, s = (int(part) for part in match_ms.groups())
            return m + (1 if s >= 30 else 0)

        # Formaty typu "72 min", "72m", "72.5"
        match_num = re.search(r"\d+(?:[\.,]\d+)?", text)
        if match_num:
            value = float(match_num.group(0).replace(",", "."))
            minutes = int(round(value))
            return minutes if minutes >= 0 else None

        return None

    def _detect_activity_type_from_text(self, text: str) -> Optional[str]:
        """
        Wykrywa typ aktywności na podstawie keywordów w tekście.

        Args:
            text: Tekst wiadomości

        Returns:
            Typ aktywności lub None
        """
        if not text or len(text) < 5:
            return None

        text_lower = text.lower()
        for activity_type, keywords in self.activity_keywords.items():
            if any(keyword.lower() in text_lower for keyword in keywords):
                logger.debug(
                    "Detected activity keyword",
                    extra={"activity_type": activity_type, "text_excerpt": text_lower[:80]},
                )
                return activity_type

        logger.debug("No activity keywords matched", extra={"text_excerpt": text_lower[:80]})
        return None

    async def analyze_content(
        self,
        text: Optional[str] = None,
        image_url: Optional[str] = None,
        user_history: Optional[List[Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Unified method for analyzing content (text and/or image) for activity data.
        
        This method is used both for live message processing and startup sync.
        All prompts are loaded from config.json via config_manager.
        
        Args:
            text: Optional text content to analyze
            image_url: Optional image URL to analyze
            user_history: Optional list of user's previous activities for context
            
        Returns:
            Dictionary with activity data or None if no activity detected.
            Schema: {
                'typ_aktywnosci': str,
                'dystans': float,
                'obciazenie': Optional[float],
                'przewyzszenie': Optional[float],
                'czas': Optional[float],
                'tempo': Optional[str],
                'puls_sredni': Optional[int],
                'kalorie': Optional[int],
                'komentarz': Optional[str]
            }
        """
        if not text and not image_url:
            logger.warning("analyze_content called with no text and no image")
            return None
            
        # Get provider and prompts from config
        provider = self._prompt_provider()
        system_prompt = config_manager.get_system_prompt(provider)
        prompts = config_manager.get_llm_prompts(provider)
        
        # Format user history for context
        user_history_text = "Brak wcześniejszych aktywności."
        if user_history:
            def _history_value(activity: Any, key: str, default: Any = None) -> Any:
                """Supports legacy dict rows and ActivityRead objects from API client."""
                if isinstance(activity, dict):
                    return activity.get(key, default)

                key_to_attr = {
                    "Data": "created_at",
                    "Rodzaj Aktywności": "activity_type",
                    "Dystans (km)": "distance_km",
                    "PUNKTY": "total_points",
                }
                attr_name = key_to_attr.get(key)
                if not attr_name:
                    return default

                value = getattr(activity, attr_name, default)
                if key == "Data" and value and hasattr(value, "strftime"):
                    return value.strftime("%Y-%m-%d")
                return value

            history_lines = [
                f"- {_history_value(act, 'Data', 'N/A')}: {_history_value(act, 'Rodzaj Aktywności', 'N/A')} "
                f"{parse_distance(_history_value(act, 'Dystans (km)', 0))}km, {_history_value(act, 'PUNKTY', '0')} pkt"
                for act in user_history[-5:]  # Last 5 activities
            ]
            user_history_text = "\n".join(history_lines)
        
        try:
            # CASE 1: Image analysis (with optional text context)
            if image_url:
                prompt_template = prompts.get("activity_analysis")
                if not prompt_template:
                    logger.error(f"Missing 'activity_analysis' prompt for provider '{provider}'")
                    return None
                
                user_prompt = prompt_template.format(
                    text_context=text or "",
                    user_history=user_history_text
                )
                
                analysis_result = await self._analyze_image_with_failover(
                    image_url,
                    user_prompt,
                    system_prompt,
                )

                if not analysis_result:
                    logger.info("Image analysis failed on all configured LLM clients")
                    return None
                
                logger.info(
                    "AI image analysis result",
                    extra={
                        "text_context": text,
                        "analysis": analysis_result
                    }
                )
                
                # Check for low contrast and retry with better model if needed
                comment = analysis_result.get("komentarz", "")
                is_low_contrast = any(
                    phrase in comment.lower() 
                    for phrase in ["nieczytelny", "niski kontrast", "low contrast"]
                )
                has_no_data = not analysis_result.get("dystans") and not analysis_result.get("czas")
                
                if is_low_contrast and has_no_data:
                    logger.warning("Low contrast detected, retrying with better model")
                    try:
                        better_model_client = self._first_client_with_method("analyze_image_with_better_model")
                        if better_model_client:
                            analysis_result = better_model_client.analyze_image_with_better_model(
                                image_url,
                                user_prompt,
                                system_instruction=system_prompt,
                            )
                            logger.info("Retry with better model succeeded", extra={"analysis": analysis_result})
                    except Exception:
                        logger.warning("Better model retry failed, using original result", exc_info=True)
                
                # Validate result
                if not analysis_result.get("typ_aktywnosci") or not analysis_result.get("dystans"):
                    logger.info("Image analysis did not detect complete activity data")
                    return None
                    
                return analysis_result
            
            # CASE 2: Text-only analysis
            elif text:
                prompt_template = prompts.get("text_analysis")
                if not prompt_template:
                    logger.error(f"Missing 'text_analysis' prompt for provider '{provider}'")
                    return None
                
                user_prompt = prompt_template.format(text=text)
                
                response = await self._generate_text_with_failover(user_prompt, system_prompt)
                
                if not response:
                    logger.info("AI returned no response for text analysis")
                    return None
                
                # Parse JSON response
                response_clean = response.strip().replace("```json", "").replace("```", "").strip()
                result = json.loads(response_clean)
                
                # Validate result
                if not result.get("typ_aktywnosci") or result.get("typ_aktywnosci") == "null":
                    logger.info(
                        "AI did not detect activity in text",
                        extra={"reason": result.get("komentarz", "no reason")}
                    )
                    return None
                
                if not result.get("dystans") or result.get("dystans") == 0:
                    logger.info("AI did not find distance in text")
                    return None
                
                logger.info(
                    "AI text analysis result",
                    extra={
                        "text_excerpt": text[:100],
                        "analysis": result
                    }
                )
                
                return result
                
        except json.JSONDecodeError:
            logger.error(
                "Failed to parse JSON from AI response",
                exc_info=True,
                extra={"response_preview": response_clean[:200] if 'response_clean' in locals() else "N/A"}
            )
            return None
        except Exception:
            logger.error("Content analysis failed", exc_info=True)
            return None

    def _activity_already_exists(self, message: discord.Message) -> bool:
        """
        Sprawdza czy aktywność z danej wiadomości już istnieje w bazie na podstawie IID.

        Args:
            message: Wiadomość Discord

        Returns:
            True jeśli aktywność już istnieje (duplikat), False jeśli można dodać
        """
        if not self.api_manager:
            return False

        iid = self._create_unique_id(message)
        try:
            self.api_manager.get_activity(iid)
            logger.debug("Duplicate activity detected", extra={"iid": iid})
            return True
        except APIManagerHTTPError as exc:
            if exc.status_code == 404:
                return False
            logger.warning("API error checking duplicate", extra={"iid": iid, "error": str(exc)})
            return False
        except APIManagerError:
            logger.warning("Connection error checking duplicate", extra={"iid": iid}, exc_info=True)
            return False

    def _activity_exists_by_iid(self, iid: str) -> bool:
        """Sprawdza istnienie aktywności po IID bez potrzeby trzymania całej wiadomości."""
        if not self.api_manager:
            return False

        try:
            self.api_manager.get_activity(iid)
            logger.debug("Duplicate activity detected during startup sync", extra={"iid": iid})
            return True
        except APIManagerHTTPError as exc:
            if exc.status_code == 404:
                return False
            logger.warning("API error checking duplicate", extra={"iid": iid, "error": str(exc)})
            return False
        except APIManagerError:
            logger.warning("Connection error checking duplicate", extra={"iid": iid}, exc_info=True)
            return False

    @staticmethod
    def _normalize_datetime_for_discord(value: datetime) -> datetime:
        """Normalizuje datę do UTC, aby można było bezpiecznie użyć jej w Discord history()."""
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _is_sync_candidate_message(self, message: discord.Message) -> bool:
        """Lekki filtr wiadomości przed dodaniem do kolejki startup sync."""
        if message.author == self.bot.user:
            return False

        if message.content.startswith("!"):
            return False

        if message.type.value == 19:
            return False

        has_activity_keywords = (
            self._detect_activity_type_from_text(message.content) if message.content else None
        )
        has_image = self._is_message_eligible_for_analysis(message)
        return bool(has_activity_keywords or has_image)

    async def _resolve_sync_channel(self, channel_id: str) -> Optional[discord.abc.Messageable]:
        """Pobiera kanał challenge'u i sprawdza minimalne uprawnienia do odczytu historii."""
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                channel = await self.bot.fetch_channel(int(channel_id))
        except discord.errors.Forbidden:
            logger.error(
                "Bot does not have access to the challenge channel",
                extra={
                    "channel_id": channel_id,
                    "required_permissions": "View Channel, Read Message History",
                },
            )
            return None
        except discord.errors.NotFound:
            logger.error("Challenge channel not found", extra={"channel_id": channel_id})
            return None
        except Exception:
            logger.error(
                "Failed to fetch challenge channel",
                exc_info=True,
                extra={"channel_id": channel_id},
            )
            return None

        if hasattr(channel, "permissions_for") and getattr(channel, "guild", None) is not None:
            me = getattr(channel.guild, "me", None)
            if me is not None:
                permissions = channel.permissions_for(me)
                if not permissions.view_channel or not permissions.read_message_history:
                    logger.error(
                        "Bot lacks required permissions in challenge channel",
                        extra={
                            "channel": getattr(channel, "name", channel_id),
                            "view_channel": permissions.view_channel,
                            "read_message_history": permissions.read_message_history,
                        },
                    )
                    return None

        return channel

    def _build_user_challenge_iid_cache(self, discord_id: str, challenge_id: int) -> set[str]:
        """Pobiera historię użytkownika i buduje ograniczony cache IID dla danego challenge'u."""
        if not self.api_manager:
            return set()

        try:
            activities = self.api_manager.get_user_activities(
                discord_id,
                limit=self._startup_sync_user_history_limit,
            )
        except APIManagerError:
            logger.warning(
                "Could not fetch user history during startup sync",
                exc_info=True,
                extra={"discord_id": discord_id, "challenge_id": challenge_id},
            )
            return set()

        filtered = [act for act in activities if act.challenge_id == challenge_id]
        if len(filtered) > self._startup_sync_max_user_iid_cache:
            filtered.sort(key=lambda act: act.created_at, reverse=True)
            filtered = filtered[: self._startup_sync_max_user_iid_cache]
            logger.info(
                "Startup sync user IID cache capped",
                extra={
                    "discord_id": discord_id,
                    "challenge_id": challenge_id,
                    "cache_size": len(filtered),
                    "max_cache_size": self._startup_sync_max_user_iid_cache,
                },
            )

        return {act.iid for act in filtered}

    async def _sync_single_challenge(self, challenge: ChallengeRead) -> dict[str, int]:
        """Synchronizuje backlog jednego challenge'u w zakresie jego czasu trwania."""
        summary = {
            "scanned": 0,
            "queued": 0,
            "duplicates": 0,
            "processed": 0,
            "failed": 0,
            "skipped": 0,
        }

        if not challenge.discord_channel_id:
            logger.info("Skipping startup sync for challenge without channel", extra={"challenge_id": challenge.id})
            return summary

        channel = await self._resolve_sync_channel(challenge.discord_channel_id)
        if channel is None:
            summary["skipped"] += 1
            return summary

        start_at = self._normalize_datetime_for_discord(challenge.start_date) - timedelta(seconds=1)
        end_at = self._normalize_datetime_for_discord(challenge.end_date) + timedelta(seconds=1)

        user_order: list[str] = []
        messages_by_user: dict[str, list[tuple[int, str]]] = {}

        logger.info(
            "Scanning challenge channel backlog",
            extra={
                "challenge_id": challenge.id,
                "channel_id": challenge.discord_channel_id,
                "start_at": start_at.isoformat(),
                "end_at": end_at.isoformat(),
            },
        )

        async for message in channel.history(limit=None, after=start_at, before=end_at, oldest_first=True):
            summary["scanned"] += 1

            if not self._is_sync_candidate_message(message):
                continue

            iid = self._create_unique_id(message)
            author_id = str(message.author.id)
            if author_id not in messages_by_user:
                messages_by_user[author_id] = []
                user_order.append(author_id)

            messages_by_user[author_id].append((message.id, iid))
            summary["queued"] += 1

        logger.info(
            "Challenge backlog scan complete",
            extra={
                "challenge_id": challenge.id,
                "channel_id": challenge.discord_channel_id,
                "scanned": summary["scanned"],
                "queued": summary["queued"],
                "users": len(user_order),
            },
        )

        for author_id in user_order:
            user_messages = messages_by_user.get(author_id, [])
            if not user_messages:
                continue

            existing_iids = self._build_user_challenge_iid_cache(author_id, challenge.id)

            logger.info(
                "Startup sync processing user backlog",
                extra={
                    "challenge_id": challenge.id,
                    "author_id": author_id,
                    "candidate_messages": len(user_messages),
                    "cached_iids": len(existing_iids),
                },
            )

            for message_id, iid in user_messages:
                if iid in existing_iids:
                    summary["duplicates"] += 1
                    continue

                try:
                    message = await channel.fetch_message(message_id)
                except discord.errors.NotFound:
                    summary["skipped"] += 1
                    logger.warning(
                        "Queued startup sync message disappeared before fetch",
                        extra={"challenge_id": challenge.id, "message_id": message_id},
                    )
                    continue
                except discord.errors.Forbidden:
                    summary["failed"] += 1
                    logger.error(
                        "Bot lost access while fetching queued startup sync message",
                        extra={"challenge_id": challenge.id, "message_id": message_id},
                    )
                    continue
                except Exception:
                    summary["failed"] += 1
                    logger.error(
                        "Failed to fetch queued startup sync message",
                        exc_info=True,
                        extra={"challenge_id": challenge.id, "message_id": message_id},
                    )
                    continue

                try:
                    await self.handle_message(message, quiet_mode=True)
                    summary["processed"] += 1
                    existing_iids.add(iid)
                except Exception:
                    summary["failed"] += 1
                    logger.error(
                        "Failed to process queued startup sync message",
                        exc_info=True,
                        extra={"challenge_id": challenge.id, "message_id": message_id},
                    )

            # Drop per-user buffers eagerly to keep startup sync memory usage low.
            messages_by_user.pop(author_id, None)

        return summary

    async def sync_active_challenges(self, challenges: list[ChallengeRead]) -> dict[str, int]:
        """Synchronizuje backlog wszystkich aktywnych challenge'y przy starcie bota."""
        summary = {
            "challenge_count": len(challenges),
            "scanned": 0,
            "queued": 0,
            "duplicates": 0,
            "processed": 0,
            "failed": 0,
            "skipped": 0,
        }

        if not self.api_manager:
            logger.warning("Startup sync skipped: api_manager not available")
            return summary

        if not self._llm_clients_for_failover():
            logger.warning("Startup sync skipped: llm client not available")
            return summary

        if not challenges:
            logger.info("Startup sync skipped: no active challenges")
            return summary

        logger.info("Starting startup sync for active challenges", extra={"challenge_count": len(challenges)})

        for challenge in challenges:
            challenge_summary = await self._sync_single_challenge(challenge)
            for key in ("scanned", "queued", "duplicates", "processed", "failed", "skipped"):
                summary[key] += challenge_summary[key]

        logger.info("Startup sync completed", extra=summary)
        return summary

    async def handle_message(self, message: discord.Message, quiet_mode: bool = False):
        """Przetwarza wiadomość i decyduje o podjęciu akcji."""
        # Loguj ID wiadomości na początku przetwarzania
        logger.info(
            "Processing Discord message",
            extra={"message_id": message.id, "author": str(message.author), "channel": str(message.channel)}
        )
        
        # Ignoruj własne wiadomości i komendy
        if message.author == self.bot.user or message.content.startswith("!"):
            return

        # Pomiń wiadomości typu 19 (reply/odpowiedzi)
        if message.type.value == 19:
            return

        # Sprawdź czy wiadomość zawiera słowa kluczowe aktywności
        has_activity_keywords = (
            self._detect_activity_type_from_text(message.content) if message.content else None
        )

        # Sprawdź czy jest zdjęcie
        has_image = self._is_message_eligible_for_analysis(message)

        # PRIORYTET 1: Sprawdź duplikat PRZED jakąkolwiek analizą AI
        if (has_activity_keywords or has_image) and self._activity_already_exists(message):
            logger.info(
                "Skipping duplicate message",
                extra={"message_id": message.id, "author": str(message.author)}
            )
            # W live mode dodaj cichą reakcję jeśli jeszcze nie ma.
            if (not quiet_mode) and (not any(r.emoji == "✅" for r in message.reactions)):
                await message.add_reaction("✅")
            return

        # Skip if no activity indicators
        if not has_activity_keywords and not has_image:
            return

        # Log what we're processing
        logger.info(
            "Processing activity message",
            extra={
                "message_id": message.id,
                "has_keywords": bool(has_activity_keywords),
                "has_image": bool(has_image),
                "author": str(message.author)
            }
        )
        
        if not quiet_mode:
            await message.add_reaction("🤔")

        try:
            # Get user history for context from API
            user_history = []
            if self.api_manager:
                try:
                    user_history = self.api_manager.get_user_activities(
                        str(message.author.id), limit=5
                    )
                except APIManagerError:
                    logger.warning("Could not fetch user history from API", exc_info=True)

            # Get image URL if present
            image_url = self._get_image_url(message) if has_image else None
            
            # Use unified analysis method
            analysis = await self.analyze_content(
                text=message.content,
                image_url=image_url,
                user_history=user_history
            )

            if not analysis:
                if not quiet_mode:
                    await message.remove_reaction("🤔", self.bot.user)
                    await message.add_reaction("❓")
                return

            await self._process_successful_analysis(message, analysis, quiet_mode=quiet_mode)
            
        except Exception:
            logger.error(
                "Message analysis failed",
                extra={"message_id": message.id},
                exc_info=True
            )
            if not quiet_mode:
                await message.remove_reaction("🤔", self.bot.user)
                await message.add_reaction("❓")

    def _is_message_eligible_for_analysis(self, message: discord.Message) -> bool:
        """Sprawdza, czy wiadomość powinna być analizowana."""
        if not message.attachments:
            return False

        # Sprawdź czy jest obrazek (nie GIF)
        has_image = any(
            att.content_type
            and att.content_type.startswith("image/")
            and att.content_type != "image/gif"
            for att in message.attachments
        )

        # Analizuj każde zdjęcie - Gemini sam zadecyduje czy to aktywność
        return has_image

    def _get_image_url(self, message: discord.Message) -> Optional[str]:
        """Zwraca URL pierwszego obrazu z wiadomości (nie-GIF)."""
        for attachment in message.attachments:
            if (
                attachment.content_type
                and attachment.content_type.startswith("image/")
                and attachment.content_type != "image/gif"
            ):
                return attachment.url
        return None

    async def _process_successful_analysis(
        self, message: discord.Message, analysis: Dict[str, Any], quiet_mode: bool = False
    ):
        """Obsługuje logikę po pomyślnej analizie obrazu."""
        activity_type = analysis["typ_aktywnosci"]
        distance = float(analysis["dystans"])
        
        logger.info(
            "Successful activity analysis",
            extra={
                "discord_msg_id": message.id,
                "activity_type": activity_type,
                "distance": distance,
                "author": str(message.author)
            }
        )

        # Walidacja - sprawdź czy typ aktywności istnieje i czy spełnia minimalne wymagania
        activity_types = self._get_activity_types(channel_id=str(message.channel.id))
        if activity_type not in activity_types:
            if not quiet_mode:
                await message.remove_reaction("🤔", self.bot.user)
            logger.warning("Unknown activity type", extra={"activity_type": activity_type})
            return

        # Sprawdź minimalny dystans (dla walidacji przed zapisem)
        activity_info = activity_types[activity_type]
        min_distance = activity_info.get("min_distance", 0)
        if distance < min_distance:
            if not quiet_mode:
                await message.remove_reaction("🤔", self.bot.user)
            logger.info(
                "Distance below minimum",
                extra={"distance": distance, "min_distance": min_distance}
            )
            return

        if not quiet_mode:
            await message.remove_reaction("🤔", self.bot.user)

        # Zapis do API
        saved_activity = await self._save_activity_to_api(message, analysis, channel_id=str(message.channel.id))

        if not saved_activity:
            logger.error("Failed to save activity", extra={"discord_msg_id": message.id})
            if not quiet_mode:
                embed = discord.Embed(
                    title="❌ Błąd zapisu",
                    description="Nie udało się zapisać aktywności do bazy danych.",
                    color=discord.Color.red()
                )
                await message.reply(embed=embed)
            return

        points = saved_activity.total_points

        if points == 0:
            if not quiet_mode:
                embed = discord.Embed(
                    title="⚠️ Aktywność nie spełnia wymagań",
                    description="Aktywność została zapisana, ale nie uzyskała punktów (dystans poniżej minimum).",
                    color=discord.Color.orange()
                )
                await message.reply(embed=embed)
            return

        logger.info(
            "Activity saved to API with points",
            extra={"discord_msg_id": message.id, "points": points, "iid": saved_activity.iid}
        )

        if quiet_mode:
            return

        # Generowanie komentarza motywacyjnego
        ai_comment = await self._generate_motivational_comment(
            message.author, activity_type, distance, points
        )

        # Wysyłanie odpowiedzi
        embed = self._create_response_embed(message, analysis, points, ai_comment, True, iid=saved_activity.iid)
        await message.reply(embed=embed)
        await message.add_reaction("✅")

    async def _generate_motivational_comment(
        self, author: discord.User, activity_type: str, distance: float, points: int
    ) -> str:
        """Pobiera historię z API, buduje prompt i generuje komentarz motywacyjny."""
        display_name = get_display_name(author)
        user_history_api = []

        if self.api_manager:
            try:
                user_history_api = self.api_manager.get_user_activities(
                    str(author.id), limit=5
                )
            except APIManagerError:
                logger.warning(
                    "Failed to fetch user history for motivational comment",
                    exc_info=True,
                    extra={"user": display_name},
                )

        # Convert ActivityRead list to legacy dict format expected by _build_motivational_comment_prompt
        user_history = [
            {
                "Data": act.created_at.strftime("%Y-%m-%d"),
                "Rodzaj Aktywności": act.activity_type,
                "Dystans (km)": act.distance_km,
                "PUNKTY": act.total_points,
            }
            for act in user_history_api
        ]

        current_activity_summary = {
            "typ_aktywnosci": activity_type,
            "dystans": distance,
            "punkty": points,
        }

        user_prompt = self._build_motivational_comment_prompt(current_activity_summary, user_history)
        user_prompt = (
            user_prompt
            + "\n\nZwróć wyłącznie sam komentarz motywacyjny jako czysty tekst (bez JSON, bez kluczy, bez markdown)."
        )
        
        # Pobierz globalny system_prompt
        provider = self._prompt_provider()
        system_prompt = config_manager.get_system_prompt(provider)

        try:
            raw_response = await self._generate_text_with_failover(user_prompt, system_prompt)
            if not raw_response:
                return "Dobra robota!"
            return self._extract_motivational_comment(raw_response)
        except (LLMAnalysisError, LLMTimeoutError):
            logger.error("Failed to generate AI comment", exc_info=True)
            return "Dobra robota!"  # Fallback

    def _extract_motivational_comment(self, response: Any) -> str:
        """Normalizuje odpowiedź LLM i wyciąga sam komentarz motywacyjny."""
        if response is None:
            return "Dobra robota!"

        if isinstance(response, dict):
            return str(
                response.get("motivational_comment")
                or response.get("komentarz")
                or response.get("period_summary")
                or "Dobra robota!"
            ).strip()

        text = str(response).strip()
        if not text:
            return "Dobra robota!"

        cleaned = text.replace("```json", "").replace("```", "").strip()

        # Czasem model zwraca JSON zamiast czystego tekstu - wyciągnij właściwe pole.
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                extracted = (
                    parsed.get("motivational_comment")
                    or parsed.get("komentarz")
                    or parsed.get("period_summary")
                )
                if extracted:
                    return str(extracted).strip()
        except json.JSONDecodeError:
            pass

        return cleaned

    async def _save_activity_to_api(
        self, message: discord.Message, analysis: Dict[str, Any], channel_id: Optional[str] = None
    ):
        """
        Zapisuje aktywność do db-service przez API.

        Returns:
            ActivityRead jeśli sukces, None w przypadku błędu
        """
        from libs.shared.schemas.activity import ActivityCreate

        if config_manager.is_debug_mode():
            logger.warning(
                "🔍 DEBUG MODE: Skipping save to API",
                extra={"message_id": message.id, "analysis": analysis}
            )
            return None

        if not self.api_manager:
            return None

        # Sprawdź challenge_id z globalnej mapy kanał -> challenge
        challenge_id: Optional[int] = None
        if channel_id:
            try:
                channel_to_challenge = self.get_channel_to_challenge_mapping()
                challenge_id = channel_to_challenge.get(channel_id)
            except Exception as e:
                logger.error("Błąd podczas pobierania mapowania kanałów", exc_info=True)
                pass

        try:
            activity_type = analysis["typ_aktywnosci"]
            distance = float(analysis["dystans"])
            weight_kg = float(analysis.get("obciazenie") or 0) or None
            elevation_raw = analysis.get("przewyzszenie")
            elevation_m = int(float(elevation_raw)) if elevation_raw else None

            points_breakdown, error = self.calculate_points_breakdown(
                activity_type,
                distance,
                weight=weight_kg,
                elevation=elevation_m,
                challenge_id=challenge_id,
            )
            if error:
                logger.error(
                    "Could not calculate points for payload",
                    extra={
                        "message_id": message.id,
                        "activity_type": activity_type,
                        "distance": distance,
                        "error": error,
                    },
                )
                return None

            base_pts = points_breakdown["base_points"]
            weight_bonus = points_breakdown["weight_bonus_points"]
            elevation_bonus = points_breakdown["elevation_bonus_points"]
            total_points = points_breakdown["total_points"]
            
            iid = self._create_unique_id(message)
            display_name = get_display_name(message.author)
            time_minutes = self._parse_analysis_time_to_minutes(analysis.get("czas"))

            if analysis.get("czas") and time_minutes is None:
                logger.warning(
                    "Could not parse analysis time value",
                    extra={"message_id": message.id, "raw_time": analysis.get("czas")},
                )

            payload = ActivityCreate(
                discord_id=str(message.author.id),
                display_name=display_name,
                iid=iid,
                activity_type=activity_type,
                distance_km=distance,
                base_points=base_pts,
                weight_kg=weight_kg,
                elevation_m=elevation_m,
                weight_bonus_points=weight_bonus,
                elevation_bonus_points=elevation_bonus,
                mission_bonus_points=0,
                total_points=total_points,
                time_minutes=time_minutes,
                pace=analysis.get("tempo"),
                heart_rate_avg=int(analysis["puls_sredni"]) if analysis.get("puls_sredni") else None,
                calories=int(analysis["kalorie"]) if analysis.get("kalorie") else None,
                created_at=message.created_at.replace(tzinfo=None),
                message_id=str(message.id),
                message_timestamp=str(int(message.created_at.timestamp())),
                challenge_id=challenge_id,
            )

            logger.info(
                "Saving activity to API",
                extra={
                    "discord_msg_id": message.id,
                    "user": display_name,
                    "activity_type": activity_type,
                    "distance_km": distance,
                    "total_points": total_points,
                }
            )

            return self.api_manager.save_activity(payload)

        except (APIManagerHTTPError, APIManagerError):
            logger.error("Failed to save activity to API", exc_info=True)
            return None
        except Exception:
            logger.error("Unexpected error saving activity", exc_info=True)
            return None

    def _create_response_embed(
        self,
        message: discord.Message,
        analysis: Dict[str, Any],
        points: int,
        ai_comment: str,
        saved: bool,
        iid: Optional[str] = None,
    ) -> discord.Embed:
        """Tworzy embed z odpowiedzią dla użytkownika."""
        activity_type = analysis["typ_aktywnosci"]
        _fallback = {"emoji": "📝", "display_name": activity_type, "unit": "km"}
        info = self._get_activity_types(channel_id=str(message.channel.id)).get(activity_type, _fallback)
        embed = discord.Embed(
            title=f"{info['emoji']} Automatycznie rozpoznano aktywność!",
            color=discord.Color.green() if saved else discord.Color.orange(),
        )
        embed.add_field(name="Użytkownik", value=message.author.mention, inline=True)
        embed.add_field(name="Typ", value=info["display_name"], inline=True)
        embed.add_field(
            name=f"Dystans ({info['unit']})", value=f"{analysis['dystans']}", inline=True
        )

        if analysis.get("czas"):
            embed.add_field(name="⏱️ Czas", value=analysis["czas"], inline=True)
        if analysis.get("tempo"):
            embed.add_field(name="⚡ Tempo", value=analysis["tempo"], inline=True)
        if analysis.get("puls_sredni"):
            embed.add_field(name="❤️ Puls", value=f"{analysis['puls_sredni']} bpm", inline=True)
        if analysis.get("obciazenie") and float(analysis.get("obciazenie")) > 0:
            embed.add_field(name="🎒 Obciążenie", value=f"{analysis['obciazenie']} kg", inline=True)
        if analysis.get("przewyzszenie") and float(analysis.get("przewyzszenie")) > 0:
            embed.add_field(
                name="⛰️ Przewyższenie", value=f"{analysis['przewyzszenie']} m", inline=True
            )
        if analysis.get("kalorie"):
            embed.add_field(name="🔥 Kalorie", value=f"{analysis['kalorie']} kcal", inline=True)

        embed.add_field(name="🏆 Punkty", value=f"**{points}**", inline=False)

        if ai_comment:
            embed.add_field(name="💬 Komentarz", value=ai_comment, inline=False)

        footer_text = f"IID: {iid}" if iid else ""
        if not saved:
            footer_text = (footer_text + " | " if footer_text else "") + "⚠️ Dane nie zostały zapisane"
        if footer_text:
            embed.set_footer(text=footer_text)

        return embed

    def calculate_points_breakdown(
        self,
        activity_type: str,
        distance: float,
        weight: Optional[float] = None,
        elevation: Optional[float] = None,
        challenge_id: Optional[int] = None,
    ) -> tuple[dict[str, int], str]:
        """Zwraca spójny breakdown punktów i ich sumę dla aktywności."""
        activity_types = self._get_activity_types(challenge_id=challenge_id)
        if activity_type not in activity_types:
            return {}, f"Nieznany typ aktywności: {activity_type}"

        activity_info = activity_types[activity_type]
        min_distance = activity_info.get("min_distance", 0)
        if distance < min_distance:
            return {}, f"Minimalny dystans dla {activity_info['display_name']}: {min_distance} km"

        base_points_rate = activity_info["base_points"]
        base_points = int(distance * base_points_rate)
        bonuses = activity_info.get("bonuses", [])
        points_rules = self._get_points_rules(challenge_id)

        weight_bonus_points = 0
        weight_bonus_cfg = points_rules.get("weight_bonus", {})
        min_weight_kg = float(weight_bonus_cfg.get("min_weight_kg", 5))
        distance_multiplier = float(weight_bonus_cfg.get("distance_points_multiplier", 1.5))
        if (
            weight
            and weight >= min_weight_kg
            and "obciążenie" in bonuses
            and distance_multiplier > 1
        ):
            weight_bonus_points = int(base_points * (distance_multiplier - 1))

        elevation_bonus_points = 0
        elevation_bonus_cfg = points_rules.get("elevation_bonus", {})
        meters_step = int(elevation_bonus_cfg.get("meters_step", 50))
        points_per_step = int(elevation_bonus_cfg.get("points_per_step", 500))
        if elevation and elevation > 0 and "przewyższenie" in bonuses and meters_step > 0:
            elevation_bonus_points = int(elevation // meters_step) * points_per_step

        total_points = base_points + weight_bonus_points + elevation_bonus_points
        if total_points < 1:
            base_points = 1
            total_points = 1

        return {
            "base_points": base_points,
            "weight_bonus_points": weight_bonus_points,
            "elevation_bonus_points": elevation_bonus_points,
            "total_points": total_points,
        }, ""

    def calculate_points(
        self,
        activity_type: str,
        distance: float,
        weight: Optional[float] = None,
        elevation: Optional[float] = None,
        challenge_id: Optional[int] = None,
    ) -> tuple[int, str]:
        """Oblicza punkty za aktywność zgodnie z wytycznymi konkursu."""
        points_breakdown, error = self.calculate_points_breakdown(
            activity_type,
            distance,
            weight=weight,
            elevation=elevation,
            challenge_id=challenge_id,
        )
        if error:
            return 0, error
        return points_breakdown["total_points"], ""

    async def sync_chat_history(self):
        """Synchronizuje historię czatu z Google Sheets - dodaje brakujące aktywności."""
        if not self.sheets_manager or not self._llm_clients_for_failover():
            logger.warning("Sync skipped: sheets_manager or llm clients not available")
            return

        try:
            channel_id = os.getenv("MONITORED_CHANNEL_ID")
            if not channel_id or channel_id == "your_channel_id_here":
                logger.warning("Sync skipped: MONITORED_CHANNEL_ID not configured in .env")
                return

            try:
                channel = self.bot.get_channel(int(channel_id))
                if not channel:
                    channel = await self.bot.fetch_channel(int(channel_id))
            except discord.errors.Forbidden:
                logger.error(
                    "Bot does not have access to the monitored channel",
                    extra={
                        "channel_id": channel_id,
                        "required_permissions": "View Channel, Read Message History",
                    },
                )
                return
            except discord.errors.NotFound:
                logger.error("Channel not found", extra={"channel_id": channel_id})
                return
            except Exception:
                logger.error(
                    "Failed to fetch channel", exc_info=True, extra={"channel_id": channel_id}
                )
                return

            # Sprawdź uprawnienia bota w kanale
            permissions = channel.permissions_for(channel.guild.me)
            if not permissions.view_channel or not permissions.read_message_history:
                logger.error(
                    "Bot lacks required permissions in channel",
                    extra={
                        "channel": channel.name,
                        "view_channel": permissions.view_channel,
                        "read_message_history": permissions.read_message_history,
                    },
                )
                return

            logger.info("Starting chat history sync", extra={"channel": channel.name})

            # KROK 1: Pobierz datę ostatniego wpisu z Google Sheets
            from datetime import datetime, timezone, timedelta
            
            latest_sheet_date = await self.sheets_manager.get_latest_activity_date()
            
            if latest_sheet_date:
                # Dodaj timezone UTC do daty z arkusza (jeśli nie ma)
                if latest_sheet_date.tzinfo is None:
                    latest_sheet_date = latest_sheet_date.replace(tzinfo=timezone.utc)
                
                # Odejmij 1 godzinę aby złapać ewentualne wiadomości z tego samego czasu
                min_sync_date = latest_sheet_date - timedelta(hours=1)
                
                logger.info(
                    "Syncing messages newer than latest sheet entry",
                    extra={
                        "latest_sheet_date": latest_sheet_date.isoformat(),
                        "sync_from_date": min_sync_date.isoformat()
                    }
                )
            else:
                # Jeśli arkusz jest pusty, użyj domyślnej daty (1 grudnia 2025)
                min_sync_date = datetime(2025, 12, 1, 0, 0, 0, tzinfo=timezone.utc)
                logger.info(
                    "Sheet is empty, syncing from default date",
                    extra={"sync_from_date": min_sync_date.isoformat()}
                )

            # KROK 2: Zbierz wszystkie wiadomości z kanału nowsze niż min_sync_date
            all_messages = []
            logger.info("Fetching messages from channel")

            # ID wiadomości do debugowania
            DEBUG_MESSAGE_ID = 1445524947186356255

            # Użyj parametru after aby pobrać tylko wiadomości nowsze niż min_sync_date
            # Limit zwiększony do 500 bo teraz pobieramy tylko nowe wiadomości
            async for message in channel.history(limit=500, after=min_sync_date):
                # Nie musimy już sprawdzać daty - Discord już filtruje za nas

                # DEBUG: Sprawdź konkretną wiadomość
                if message.id == DEBUG_MESSAGE_ID:
                    logger.debug(
                        "Found debug message",
                        extra={
                            "message_id": DEBUG_MESSAGE_ID,
                            "author": str(message.author),
                            "is_bot": message.author == self.bot.user,
                            "has_content": bool(message.content),
                            "attachments_count": len(message.attachments),
                        },
                    )

                # Pomiń wiadomości od bota
                if message.author == self.bot.user:
                    continue

                # Pomiń wiadomości typu 19 (reply/odpowiedzi)
                if message.type.value == 19:
                    continue

                # Sprawdź czy wiadomość ma zdjęcie LUB zawiera słowa kluczowe aktywności
                has_image = self._is_message_eligible_for_analysis(message)
                has_keywords = (
                    self._detect_activity_type_from_text(message.content)
                    if message.content
                    else None
                )

                if has_image or has_keywords:
                    all_messages.append(message)

            logger.info("Messages fetched", extra={"count": len(all_messages)})

            # KROK 2: Filtruj wiadomości - tylko te, których IID NIE MA w cache
            messages_to_process = []
            for message in all_messages:
                is_duplicate = self._activity_already_exists(message)
                if not is_duplicate:
                    messages_to_process.append(message)

            logger.info(
                "Duplicate check complete",
                extra={
                    "new_messages": len(messages_to_process),
                    "duplicates_skipped": len(all_messages) - len(messages_to_process),
                },
            )

            # KROK 3: Przetwarzaj tylko unikalne wiadomości w batch'ach
            processed, added, not_recognized = 0, 0, 0

            # Odwróć kolejność aby przetwarzać od najstarszej do najnowszej
            messages_to_process.reverse()

            # Przetwarzaj w małych batch'ach dla oszczędności pamięci
            BATCH_SIZE = 20
            for batch_start in range(0, len(messages_to_process), BATCH_SIZE):
                batch = messages_to_process[batch_start:batch_start + BATCH_SIZE]
                logger.info(f"Processing batch {batch_start//BATCH_SIZE + 1}/{(len(messages_to_process)-1)//BATCH_SIZE + 1}")

                for message in batch:
                    processed += 1
                    try:
                        # Get image URL if present
                        image_url = self._get_image_url(message)
                        
                        # Use unified analysis method (no history for sync to save tokens)
                        analysis = await self.analyze_content(
                            text=message.content,
                            image_url=image_url,
                            user_history=None  # Skip history during sync to save tokens
                        )

                        if not analysis:
                            not_recognized += 1
                            logger.debug(
                                "AI did not return analysis for sync message",
                                extra={"message_id": message.id},
                            )
                            continue

                        # Sprawdź czy mamy podstawowe dane lub zastosuj fallback
                        has_basic_data = (
                            analysis and analysis.get("typ_aktywnosci") and analysis.get("dystans")
                        )

                        # Fallback dla aktywności bez dystansu (jak w handle_message)
                        if not has_basic_data and analysis and analysis.get("komentarz"):
                            comment = analysis.get("komentarz", "")
                            sport_keywords = [
                                "aktywność",
                                "trening",
                                "sport",
                                "czas trwania",
                                "tętno",
                                "bpm",
                                "soccer",
                                "football",
                                "cardio",
                                "fitness",
                                "gym",
                                "workout",
                            ]

                            if any(keyword.lower() in comment.lower() for keyword in sport_keywords):
                                time_minutes = self._extract_time_from_comment(comment)

                                if time_minutes and time_minutes > 5:
                                    distance = self._convert_time_to_cardio_distance(time_minutes)
                                    logger.debug(
                                        "Fallback sync: converted time to distance",
                                        extra={"time_minutes": time_minutes, "distance_km": distance},
                                    )

                                    analysis["typ_aktywnosci"] = "cardio"
                                    analysis["dystans"] = distance
                                    analysis["czas"] = f"{int(time_minutes)} min"
                                    has_basic_data = True

                        if has_basic_data:
                            # Zapisz aktywność (IID automatycznie dodane do cache w add_activity)
                            # Arkusz obliczy punkty
                            saved, row_number = await self._save_activity_to_sheets(message, analysis)
                            
                            if saved and row_number > 0:
                                # Pobierz punkty z arkusza
                                points = await self.sheets_manager.get_points_from_row(row_number)
                                if points and points > 0:
                                    added += 1
                                    logger.info(
                                        "Activity added from sync",
                                        extra={
                                            "discord_msg_id": message.id,
                                            "activity_type": analysis["typ_aktywnosci"],
                                            "distance": analysis["dystans"],
                                            "weight": analysis.get("obciazenie"),
                                            "elevation": analysis.get("przewyzszenie"),
                                            "points": points,
                                            "row": row_number
                                        },
                                    )
                        else:
                            # Nie rozpoznano aktywności
                            not_recognized += 1
                            logger.debug(
                                "Activity not recognized in sync message",
                                extra={
                                    "message_id": message.id,
                                    "comment": analysis.get("komentarz", "No data"),
                                },
                            )

                    except Exception:
                        logger.warning(
                            "Error analyzing message during sync",
                            exc_info=True,
                            extra={"message_id": message.id},
                        )

                # Wyczyść batch z pamięci po przetworzeniu
                batch.clear()

            logger.info(
                "Sync completed",
                extra={
                    "analyzed": processed,
                    "added": added,
                    "duplicates_skipped": len(all_messages) - len(messages_to_process),
                    "not_recognized": not_recognized,
                },
            )
            
            # Wyczyść listy wiadomości z pamięci
            all_messages.clear()
            messages_to_process.clear()
            
            # Wymuś garbage collection po dużej operacji
            import gc
            gc.collect()
            logger.debug("Garbage collection completed after sync")

        except Exception:
            logger.error("Critical sync error", exc_info=True)

    def _build_motivational_comment_prompt(
        self, current_activity: Dict[str, Any], previous_activities: List[Dict[str, Any]]
    ) -> str:
        """Buduje prompt do wygenerowania komentarza motywacyjnego."""
        logger.info(
            "🔍 DEBUG: Building motivational prompt",
            extra={
                "current_activity": current_activity,
                "previous_activities_count": len(previous_activities),
                "previous_activities_raw": previous_activities
            }
        )
        
        # Przygotuj kontekst historii
        if previous_activities:
            recent = previous_activities[-5:]
            logger.info(
                "🔍 DEBUG: Processing recent activities",
                extra={"recent_count": len(recent), "recent_data": recent}
            )
            
            history_summary = [
                f"- {act.get('Rodzaj Aktywności', 'N/A')}: {parse_distance(act.get('Dystans (km)', 0))} km, "
                f"{act.get('PUNKTY', 0)} pkt (Data: {act.get('Data', 'N/A')})"
                for act in recent
            ]
            history_text = "\n".join(history_summary)

            # Użyj parse_distance do konwersji wszystkich dystansów
            distances = [parse_distance(act.get("Dystans (km)", 0)) for act in previous_activities]
            total_distance = sum(distances)
            total_points = sum(int(act.get("PUNKTY", 0)) for act in previous_activities)
            activity_count = len(previous_activities)
            
            logger.info(
                "🔍 DEBUG: History statistics calculated",
                extra={
                    "activity_count": activity_count,
                    "total_distance": total_distance,
                    "total_points": total_points,
                    "history_text": history_text
                }
            )
        else:
            logger.info("🔍 DEBUG: No previous activities - first activity for user")
            history_text = "To pierwsza zarejestrowana aktywność!"
            total_distance, total_points, activity_count = 0, 0, 0

        # Pobierz szablon promptu z konfiguracji
        provider = self._prompt_provider()
        prompts = config_manager.get_llm_prompts(provider)

        prompt_template = prompts.get("motivational_comment")
        if not prompt_template:
            raise ConfigurationError(
                f"Missing 'motivational_comment' prompt for provider '{provider}' in config.json"
            )

        # Wypełnij szablon danymi
        final_prompt = prompt_template.format(
            activity_type=current_activity.get("typ_aktywnosci", "nieznany"),
            distance=current_activity.get("dystans", 0),
            points=current_activity.get("punkty", 0),
            activity_count=activity_count,
            total_distance=f"{total_distance:.1f}",
            total_points=total_points,
            history_text=history_text,
        )
        
        logger.info(
            "🔍 DEBUG: Final prompt built",
            extra={"prompt_preview": final_prompt[:300]}
        )
        
        return final_prompt

    def get_channel_to_challenge_mapping(self) -> Dict[str, int]:
        """
        Funkcja dynamicznie pobiera mapowanie kanałów do wyzwań.
        Zwraca słownik, gdzie kluczem jest ID kanału, a wartością ID wyzwania.
        """
        try:
            active_challenges = self.api_manager.get_active_challenges()
            return {ch.discord_channel_id: ch.id for ch in active_challenges}
        except Exception as e:
            logger.error("Nie udało się pobrać mapowania kanałów do wyzwań", exc_info=True)
            return {}
