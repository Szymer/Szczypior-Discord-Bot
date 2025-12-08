# bot/orchestrator.py
import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import discord

from .config_manager import config_manager
from .constants import ACTIVITY_TYPES
from .exceptions import (
    ActivityValidationError,
    ConfigurationError,
    DuplicateActivityError,
    LLMAnalysisError,
    LLMTimeoutError,
)
from .utils import get_display_name, parse_distance

logger = logging.getLogger(__name__)


class BotOrchestrator:
    """Orkiestruje logikę biznesową bota."""

    def __init__(self, bot, gemini_client, sheets_manager):
        self.bot = bot
        self.gemini_client = gemini_client
        self.sheets_manager = sheets_manager
        self.activity_keywords = config_manager.get_activity_keywords()

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

        # Special rule: if message contains 'ASG', classify as 'inne cardio'
        # Handles typical variants and ignores case/spaces
        if "asg" in text_lower:
            logger.debug(
                "ASG keyword detected; forcing activity to inne cardio",
                extra={"text_excerpt": text_lower[:80]},
            )
            return "inne cardio"
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
        user_history: Optional[List[Dict[str, Any]]] = None
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
        provider = config_manager.get_llm_provider()
        system_prompt = config_manager.get_system_prompt(provider)
        prompts = config_manager.get_llm_prompts(provider)
        
        # Format user history for context (text and structured JSON)
        user_history_text = "Brak wcześniejszych aktywności."
        user_history_json_str = json.dumps({"user_history": []}, ensure_ascii=False)
        if user_history:
            # Build last 5 entries as readable text
            history_lines = [
                f"- {act.get('Data', 'N/A')}: {act.get('Rodzaj Aktywności', 'N/A')} "
                f"{parse_distance(act.get('Dystans (km)', 0))}km, {act.get('PUNKTY', '0')} pkt"
                for act in user_history[-5:]
            ]
            user_history_text = "\n".join(history_lines)

            # Build structured JSON for model consumption
            def _to_float(v):
                try:
                    return float(str(v).replace(',', '.')) if v not in (None, "") else None
                except Exception:
                    return None

            history_struct = []
            for act in user_history[-5:]:
                history_struct.append({
                    "date": act.get("Data"),
                    "type": act.get("Rodzaj Aktywności"),
                    "distance_km": _to_float(act.get("Dystans (km)", None)),
                    "time": act.get("Czas"),
                    "pace": act.get("Tempo"),
                    "avg_hr": act.get("Puls Średni"),
                    "elevation_gain_m": _to_float(act.get("Przewyższenie (m)", None)),
                    "load": _to_float(act.get("Obciążenie", None)),
                    "points": act.get("PUNKTY")
                })

            user_history_json_str = json.dumps({"user_history": history_struct}, ensure_ascii=False)
        
        try:
            # CASE 1: Image analysis (with optional text context)
            if image_url:
                prompt_template = prompts.get("activity_analysis")
                if not prompt_template:
                    logger.error(f"Missing 'activity_analysis' prompt for provider '{provider}'")
                    return None
                
                # Provide both text summary and structured JSON for better reliability
                user_prompt = prompt_template.format(
                    text_context=text or "",
                    user_history=user_history_text,
                    user_history_json=user_history_json_str
                )
                
                analysis_result = self.gemini_client.analyze_image(
                    image_url,
                    user_prompt,
                    system_instruction=system_prompt
                )
                
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
                        analysis_result = self.gemini_client.analyze_image_with_better_model(
                            image_url,
                            user_prompt,
                            system_instruction=system_prompt,
                            model_name="models/gemini-2.0-flash-exp"
                        )
                        logger.info("Retry with better model succeeded", extra={"analysis": analysis_result})
                    except Exception as e:
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
                
                # Include user history JSON to help contextual text analysis
                user_prompt = prompt_template.format(
                    text=text,
                    user_history_json=user_history_json_str,
                    user_history=user_history_text
                )
                
                # Execute in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.gemini_client.generate_text(user_prompt, system_instruction=system_prompt)
                )
                
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
                
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse JSON from AI response",
                exc_info=True,
                extra={"response_preview": response_clean[:200] if 'response_clean' in locals() else "N/A"}
            )
            return None
        except Exception as e:
            logger.error("Content analysis failed", exc_info=True)
            return None

    def _activity_already_exists(self, message: discord.Message) -> bool:
        """
        Sprawdza czy aktywność z danej wiadomości już istnieje w arkuszu na podstawie IID.

        Args:
            message: Wiadomość Discord

        Returns:
            True jeśli aktywność już istnieje (duplikat), False jeśli można dodać
        """
        if not self.sheets_manager:
            return False

        # Tworzymy IID konsekwentnie: {timestamp_int}_{message_id}
        message_id = str(message.id)
        message_timestamp = str(int(message.created_at.timestamp()))
        iid = f"{message_timestamp}_{message_id}"

        exists = self.sheets_manager.activity_exists(message_id, message_timestamp)

        if exists:
            logger.debug("Duplicate activity detected", extra={"iid": iid})

        return exists

    async def handle_message(self, message: discord.Message):
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
            # Dodaj cichą reakcję jeśli jeszcze nie ma
            if not any(r.emoji == "✅" for r in message.reactions):
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
        
        await message.add_reaction("🤔")

        try:
            # Get user history for context
            user_history = []
            if self.sheets_manager:
                display_name = get_display_name(message.author)
                user_history = self.sheets_manager.get_user_history(display_name)
            
            # Get image URL if present
            image_url = self._get_image_url(message) if has_image else None
            
            # Use unified analysis method
            analysis = await self.analyze_content(
                text=message.content,
                image_url=image_url,
                user_history=user_history
            )

            if not analysis:
                await message.remove_reaction("🤔", self.bot.user)
                await message.add_reaction("❓")
                return

            await self._process_successful_analysis(message, analysis)
            
        except Exception as e:
            logger.error(
                "Message analysis failed",
                extra={"message_id": message.id},
                exc_info=True
            )
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
        self, message: discord.Message, analysis: Dict[str, Any]
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
        if activity_type not in ACTIVITY_TYPES:
            await message.remove_reaction("🤔", self.bot.user)
            logger.warning("Unknown activity type", extra={"activity_type": activity_type})
            return

        # Sprawdź minimalny dystans (dla walidacji przed zapisem)
        activity_info = ACTIVITY_TYPES[activity_type]
        min_distance = activity_info.get("min_distance", 0)
        if distance < min_distance:
            await message.remove_reaction("🤔", self.bot.user)
            logger.info(
                "Distance below minimum",
                extra={"distance": distance, "min_distance": min_distance}
            )
            return

        await message.remove_reaction("🤔", self.bot.user)

        # Zapis do arkusza - arkusz obliczy punkty
        saved, row_number = self._save_activity_to_sheets(message, analysis)
        
        if not saved or row_number == 0:
            logger.error("Failed to save activity", extra={"discord_msg_id": message.id})
            # Wysłanie komunikatu o błędzie
            embed = discord.Embed(
                title="❌ Błąd zapisu",
                description="Nie udało się zapisać aktywności do arkusza.",
                color=discord.Color.red()
            )
            await message.reply(embed=embed)
            return
        
        # Pobierz punkty z arkusza (obliczone przez formułę)
        points = self.sheets_manager.get_points_from_row(row_number)
        
        if points is None or points == 0:
            logger.warning(
                "No points calculated by sheet",
                extra={"discord_msg_id": message.id, "row": row_number}
            )
            # Jeśli arkusz zwrócił 0 punktów, nie pokazuj aktywności
            embed = discord.Embed(
                title="⚠️ Aktywność nie spełnia wymagań",
                description="Aktywność została zapisana, ale nie uzyskano punktów (prawdopodobnie dystans poniżej minimum).",
                color=discord.Color.orange()
            )
            await message.reply(embed=embed)
            return

        logger.info(
            "Activity saved to Sheets with points",
            extra={"discord_msg_id": message.id, "points": points, "row": row_number}
        )

        # Generowanie komentarza (z punktami z arkusza)
        ai_comment = self._generate_motivational_comment(
            message.author, activity_type, distance, points
        )

        # Wysyłanie odpowiedzi
        embed = self._create_response_embed(message, analysis, points, ai_comment, True)
        await message.reply(embed=embed)
        await message.add_reaction("✅")

    def _generate_motivational_comment(
        self, author: discord.User, activity_type: str, distance: float, points: int
    ) -> str:
        """Pobiera historię, buduje prompt i generuje komentarz motywacyjny."""
        user_history = []
        if self.sheets_manager:
            try:
                display_name = author.global_name if author.global_name else str(author)
                user_history = self.sheets_manager.get_user_history(display_name)
            except Exception as e:
                logger.warning(
                    "Failed to fetch user history for motivational comment",
                    exc_info=True,
                    extra={"user": str(author)},
                )

        current_activity_summary = {
            "typ_aktywnosci": activity_type,
            "dystans": distance,
            "punkty": points,
        }

        user_prompt = self._build_motivational_comment_prompt(current_activity_summary, user_history)
        
        # Pobierz globalny system_prompt
        provider = config_manager.get_llm_provider()
        system_prompt = config_manager.get_system_prompt(provider)

        try:
            return self.gemini_client.generate_text(
                user_prompt, 
                temperature=0.8, 
                max_tokens=200,
                system_instruction=system_prompt
            )
        except (LLMAnalysisError, LLMTimeoutError) as e:
            logger.error("Failed to generate AI comment", exc_info=True)
            return "Dobra robota!"  # Fallback

    def _save_activity_to_sheets(
        self, message: discord.Message, analysis: Dict[str, Any]
    ) -> tuple[bool, int]:
        """
        Zapisuje aktywność do Google Sheets.

        Args:
            message: Wiadomość Discord
            analysis: Analiza aktywności

        Returns:
            Tuple (success: bool, row_number: int) - True i numer wiersza jeśli sukces, (False, 0) w przeciwnym razie
        """
        if not self.sheets_manager:
            return (False, 0)
        try:
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")

            # Określ czy jest obciążenie > 5kg
            weight_value = float(analysis.get("obciazenie") or 0)
            has_weight = weight_value > 5

            # Użyj get_display_name z utils
            display_name = get_display_name(message.author)

            # Loguj wszystkie dane przed zapisem
            logger.info(
                "Saving activity data",
                extra={
                    "discord_msg_id": message.id,
                    "user": display_name,
                    "activity_type": analysis["typ_aktywnosci"],
                    "distance_km": float(analysis["dystans"]),
                    "weight_kg": weight_value,
                    "has_weight": has_weight,
                    "elevation_m": float(analysis.get("przewyzszenie") or 0),
                    "time": analysis.get("czas"),
                    "pace": analysis.get("tempo"),
                    "calories": analysis.get("kalorie"),
                    "heart_rate": analysis.get("puls_sredni"),
                    "timestamp": timestamp
                }
            )

            return self.sheets_manager.add_activity(
                username=display_name,
                activity_type=analysis["typ_aktywnosci"],
                distance=float(analysis["dystans"]),
                has_weight=has_weight,
                elevation=float(analysis.get("przewyzszenie") or 0) if analysis.get("przewyzszenie") else None,
                timestamp=timestamp,
                message_id=str(message.id),
                message_timestamp=str(int(message.created_at.timestamp())),
            )
        except Exception as e:
            logger.error(
                "Failed to save activity to Sheets", exc_info=True, extra={"user": display_name}
            )
            return (False, 0)

    def _create_response_embed(
        self,
        message: discord.Message,
        analysis: Dict[str, Any],
        points: int,
        ai_comment: str,
        saved: bool,
    ) -> discord.Embed:
        """Tworzy embed z odpowiedzią dla użytkownika."""
        activity_type = analysis["typ_aktywnosci"]
        info = ACTIVITY_TYPES[activity_type]
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

        if not saved:
            embed.set_footer(text="⚠️ Dane nie zostały zapisane do Google Sheets")

        return embed

    def calculate_points(
        self,
        activity_type: str,
        distance: float,
        weight: Optional[float] = None,
        elevation: Optional[float] = None,
    ) -> tuple[int, str]:
        """Oblicza punkty za aktywność zgodnie z wytycznymi konkursu."""
        if activity_type not in ACTIVITY_TYPES:
            return 0, f"Nieznany typ aktywności: {activity_type}"

        activity_info = ACTIVITY_TYPES[activity_type]

        min_distance = activity_info.get("min_distance", 0)
        if distance < min_distance:
            return 0, f"Minimalny dystans dla {activity_info['display_name']}: {min_distance} km"

        base_points = activity_info["base_points"]
        points = int(distance * base_points)

        bonuses = activity_info.get("bonuses", [])

        if weight and weight > 0 and "obciążenie" in bonuses:
            bonus = int((weight / 5) * (distance * base_points * 0.1))
            points += bonus

        if elevation and elevation > 0 and "przewyższenie" in bonuses:
            bonus = int((elevation / 100) * (distance * base_points * 0.05))
            points += bonus

        return max(points, 1), ""

    async def sync_chat_history(self):
        """Synchronizuje historię czatu z Google Sheets - dodaje brakujące aktywności."""
        if not self.sheets_manager or not self.gemini_client:
            logger.warning("Sync skipped: sheets_manager or gemini_client not available")
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
            except Exception as e:
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

            # KROK 1: Zbierz wszystkie wiadomości z kanału
            all_messages = []
            logger.info("Fetching messages from channel")

            # Minimalna data wiadomości do synchronizacji (1 grudnia 2025)
            from datetime import datetime, timezone
            min_sync_date = datetime(2025, 12, 1, 0, 0, 0, tzinfo=timezone.utc)

            # ID wiadomości do debugowania
            DEBUG_MESSAGE_ID = 1445524947186356255

            async for message in channel.history(limit=500):
                # Sprawdź datę wiadomości - pomiń starsze niż 1 grudnia 2025
                if message.created_at < min_sync_date:
                    logger.debug(
                        "Skipping message older than Dec 1, 2025",
                        extra={"message_id": message.id, "created_at": message.created_at}
                    )
                    continue

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

            # KROK 3: Przetwarzaj tylko unikalne wiadomości
            processed, added, not_recognized = 0, 0, 0

            # Odwróć kolejność aby przetwarzać od najstarszej do najnowszej
            messages_to_process.reverse()

            for message in messages_to_process:
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
                        saved, row_number = self._save_activity_to_sheets(message, analysis)
                        
                        if saved and row_number > 0:
                            # Pobierz punkty z arkusza
                            points = self.sheets_manager.get_points_from_row(row_number)
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

                except Exception as e:
                    logger.warning(
                        "Error analyzing message during sync",
                        exc_info=True,
                        extra={"message_id": message.id},
                    )

            logger.info(
                "Sync completed",
                extra={
                    "analyzed": processed,
                    "added": added,
                    "duplicates_skipped": len(all_messages) - len(messages_to_process),
                    "not_recognized": not_recognized,
                },
            )

        except Exception as e:
            logger.error("Critical sync error", exc_info=True)

    def _build_motivational_comment_prompt(
        self, current_activity: Dict[str, Any], previous_activities: List[Dict[str, Any]]
    ) -> str:
        """Buduje prompt do wygenerowania komentarza motywacyjnego."""
        # Przygotuj kontekst historii
        if previous_activities:
            recent = previous_activities[-5:]
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
        else:
            history_text = "To pierwsza zarejestrowana aktywność!"
            total_distance, total_points, activity_count = 0, 0, 0

        # Pobierz szablon promptu z konfiguracji
        provider = config_manager.get_llm_provider()
        prompts = config_manager.get_llm_prompts(provider)

        prompt_template = prompts.get("motivational_comment")
        if not prompt_template:
            raise ConfigurationError(
                f"Missing 'motivational_comment' prompt for provider '{provider}' in config.json"
            )

        # Wypełnij szablon danymi
        return prompt_template.format(
            activity_type=current_activity.get("typ_aktywnosci", "nieznany"),
            distance=current_activity.get("dystans", 0),
            points=current_activity.get("punkty", 0),
            activity_count=activity_count,
            total_distance=f"{total_distance:.1f}",
            total_points=total_points,
            history_text=history_text,
        )
