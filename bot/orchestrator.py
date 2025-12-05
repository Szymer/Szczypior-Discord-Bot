# bot/orchestrator.py
import logging
import os
import json
import asyncio
import re
from typing import Optional, Dict, Any, List
import discord
from .config_manager import config_manager
from .constants import ACTIVITY_TYPES
from .utils import get_display_name, parse_distance
from .exceptions import (
    ConfigurationError,
    LLMAnalysisError,
    LLMTimeoutError,
    ActivityValidationError,
    DuplicateActivityError
)

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
            r'(\d{1,2})\s*(?:godzin[ęya]?|hour|h|godz\.?)[,\s]+(\d{1,2})\s*(?:minut|minute|min|m)',  # "1 godzinę, 12 minut"
            r'(\d{1,2}):(\d{2}):(\d{2})',  # "1:12:56"
            r'(\d{1,2})h\s*(\d{1,2})m',  # "1h 12m"
            r'(\d{2,3}):(\d{2})'  # "72:56" (minuty:sekundy)
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
                    if 'godzin' in pattern or 'hour' in pattern:
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
        
        if not text or len(text) < 5:
            return None

        text_lower = text.lower()
        for activity_type, keywords in self.activity_keywords.items():
            if any(keyword.lower() in text_lower for keyword in keywords):
                logger.debug("Detected activity keyword", extra={"activity_type": activity_type, "text_excerpt": text_lower[:80]})
                return activity_type

        logger.debug("No activity keywords matched", extra={"text_excerpt": text_lower[:80]})
        return None
    
    async def _analyze_text_with_ai(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Analizuje tekst wiadomości używając AI.
        
        Args:
            text: Tekst wiadomości
            
        Returns:
            Słownik z danymi aktywności lub None
        """
        try:
            # Przygotuj prompt dla AI
            prompt = f"""Przeanalizuj poniższą wiadomość tekstową i wyciągnij dane o aktywności sportowej.

WIADOMOŚĆ UŻYTKOWNIKA:
{text}

INSTRUKCJE:
1. Szukaj dystansu w formatach: "1250m", "5km", "10.5 km", "2.3 kilometers", "1500 metrów"
2. Konwertuj wszystkie dystanse na kilometry (m → km, mile → km)
3. Szukaj czasu w formatach: "43:12", "1:23:45", "45 min", "1h 20min"
4. Rozpoznaj typ aktywności: pływanie, bieganie, rower, spacer, cardio, etc.

MAPOWANIE TYPÓW (zwróć dokładnie taką wartość):
- Pływanie/Swimming/Basen → plywanie
- Bieganie/Running/Bieg → bieganie_teren
- Bieżnia/Treadmill → bieganie_bieznia
- Rower/Cycling/Bike → rower
- Spacer/Walking/Hiking → spacer
- Siłownia/Gym/Fitness/Soccer/Cardio → cardio

Zwróć TYLKO obiekt JSON (bez markdown, bez ```json):
{{
    "typ_aktywnosci": "dokładna wartość z mapowania powyżej",
    "dystans": liczba_w_km (float),
    "czas": "format MM:SS lub HH:MM:SS",
    "komentarz": "krótki opis co rozpoznałeś"
}}

Jeśli nie wykryjesz aktywności, zwróć:
{{
    "typ_aktywnosci": null,
    "dystans": null,
    "komentarz": "Nie wykryto danych o aktywności"
}}"""

            # Wywołaj AI używając generate_text (synchroniczne wywołanie)
            # UWAGA: używamy self.gemini_client, nie self.llm_client
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                self.gemini_client.generate_text, 
                prompt
            )
            
            if not response:
                print("⚠️ AI nie zwróciło odpowiedzi")
                return None
            
            # Wyczyść odpowiedź z markdown
            response_clean = response.strip().replace("```json", "").replace("```", "").strip()
            
            # Parsuj odpowiedź JSON
            result = json.loads(response_clean)
            
            # Walidacja - sprawdź czy wykryto aktywność
            if not result.get('typ_aktywnosci') or result.get('typ_aktywnosci') == 'null':
                logger.info("AI did not detect activity in text", extra={"reason": result.get('komentarz', 'no reason')})
                return None
            
            # Walidacja - musi być dystans
            if not result.get('dystans') or result.get('dystans') == 0:
                logger.info("AI did not find distance in text")
                return None
            
            logger.info("AI recognized activity", extra={"type": result['typ_aktywnosci'], "distance": result['dystans']})
            return result
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON from AI response", exc_info=True, extra={"response_preview": response_clean[:200]})
            return None
        except (AttributeError, KeyError) as e:
            logger.error("Invalid response structure from AI", exc_info=True)
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
        # Ignoruj własne wiadomości i komendy
        if message.author == self.bot.user or message.content.startswith('!'):
            return

        # Sprawdź czy wiadomość zawiera słowa kluczowe aktywności
        has_activity_keywords = self._detect_activity_type_from_text(message.content) if message.content else None
        
        # Sprawdź czy jest zdjęcie
        has_image = self._is_message_eligible_for_analysis(message)
        
        # PRIORYTET 1: Sprawdź duplikat PRZED jakąkolwiek analizą AI
        if (has_activity_keywords or has_image) and self._activity_already_exists(message):
            print(f"⏭️ Pomijam wiadomość {message.id} - już przetworzona")
            # Dodaj cichą reakcję jeśli jeszcze nie ma
            if not any(r.emoji == '✅' for r in message.reactions):
                await message.add_reaction('✅')
            return
        
        # PRIORYTET 2: Analiza obrazu (ZAWSZE Z TEKSTEM jeśli dostępny)
        if has_image:
            logger.info("Processing image message", extra={
                "has_text": bool(message.content),
                "author": str(message.author)
            })
            await message.add_reaction('🤔')

            try:
                image_url = self._get_image_url(message)
                if not image_url:
                    await message.remove_reaction('🤔', self.bot.user)
                    return

                # Pobierz historię użytkownika dla kontekstu
                user_history_text = ""
                if self.sheets_manager:
                    display_name = get_display_name(message.author)
                    user_activities = self.sheets_manager.get_user_history(display_name)
                    if user_activities:
                        recent = user_activities[-5:]  # Ostatnie 5 aktywności
                        history_lines = [
                            f"- {act.get('Data', 'N/A')}: {act.get('Rodzaj Aktywności', 'N/A')} "
                            f"{parse_distance(act.get('Dystans (km)', 0))}km, {act.get('PUNKTY', '0')} pkt"
                            for act in recent
                        ]
                        user_history_text = "\n".join(history_lines)

                # Analiza obrazu przez Gemini (ZAWSZE przekazuj tekst jeśli istnieje)
                analysis = self._analyze_image_with_gemini(image_url, message.content, user_history_text)

                # Sprawdź czy mamy podstawowe dane (typ i dystans)
                has_basic_data = analysis and analysis.get('typ_aktywnosci') and analysis.get('dystans')
                
                if not has_basic_data:
                    logger.warning("Image does not contain complete activity data")
                    await message.remove_reaction('🤔', self.bot.user)
                    await message.add_reaction('❓')
                    return

                await self._process_successful_analysis(message, analysis)
                return
            except LLMAnalysisError as e:
                logger.error("Image analysis failed", exc_info=True)
                await message.remove_reaction('🤔', self.bot.user)
                await message.add_reaction('❓')
                return
        
        # PRIORYTET 3: Analiza TYLKO tekstu (fallback gdy nie ma obrazu)
        if not has_activity_keywords:
            return
        
        logger.info("Detected activity keywords in text", extra={
            "activity_type": has_activity_keywords,
            "author": str(message.author)
        })
        await message.add_reaction('🤔')
        
        try:
            # Analizuj tekst używając AI
            analysis_result = await self._analyze_text_with_ai(message.content)
            
            if not analysis_result:
                await message.remove_reaction('🤔', self.bot.user)
                await message.add_reaction('❓')
                return
            
            await self._process_successful_analysis(message, analysis_result)
            return
        except LLMAnalysisError as e:
            logger.error("Text analysis failed", exc_info=True)
            await message.remove_reaction('🤔', self.bot.user)
            await message.add_reaction('❓')
            return

    def _is_message_eligible_for_analysis(self, message: discord.Message) -> bool:
        """Sprawdza, czy wiadomość powinna być analizowana."""
        if not message.attachments:
            return False

        # Sprawdź czy jest obrazek (nie GIF)
        has_image = any(
            att.content_type and att.content_type.startswith('image/') and att.content_type != 'image/gif'
            for att in message.attachments
        )
        
        # Analizuj każde zdjęcie - Gemini sam zadecyduje czy to aktywność
        return has_image

    def _get_image_url(self, message: discord.Message) -> Optional[str]:
        """Zwraca URL pierwszego obrazu z wiadomości (nie-GIF)."""
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/') and attachment.content_type != 'image/gif':
                return attachment.url
        return None

    def _analyze_image_with_gemini(self, image_url: str, text_context: Optional[str], user_history: Optional[str] = None) -> Dict[str, Any]:
        """Tworzy prompt i wywołuje analizę obrazu w LLM Client."""
        prompt = self._build_activity_analysis_prompt(text_context, user_history)
        return self.gemini_client.analyze_image(image_url, prompt)

    async def _process_successful_analysis(self, message: discord.Message, analysis: Dict[str, Any]):
        """Obsługuje logikę po pomyślnej analizie obrazu."""
        activity_type = analysis['typ_aktywnosci']
        distance = float(analysis['dystans'])
        weight = float(analysis.get('obciazenie') or 0)
        elevation = float(analysis.get('przewyzszenie') or 0)

        points, error_msg = self.calculate_points(
            activity_type, distance,
            weight if weight > 0 else None,
            elevation if elevation > 0 else None
        )

        if error_msg or points <= 0:
            await message.remove_reaction('🤔', self.bot.user)
            return

        await message.remove_reaction('🤔', self.bot.user)

        # Generowanie komentarza
        ai_comment = self._generate_motivational_comment(message.author, activity_type, distance, points)

        # Zapis do arkusza
        saved = self._save_activity_to_sheets(message, analysis, points, ai_comment)

        # Wysyłanie odpowiedzi
        embed = self._create_response_embed(message, analysis, points, ai_comment, saved)
        await message.reply(embed=embed)
        await message.add_reaction('✅')

    def _generate_motivational_comment(self, author: discord.User, activity_type: str, distance: float, points: int) -> str:
        """Pobiera historię, buduje prompt i generuje komentarz motywacyjny."""
        user_history = []
        if self.sheets_manager:
            try:
                display_name = author.global_name if author.global_name else str(author)
                user_history = self.sheets_manager.get_user_history(display_name)
            except Exception as e:
                logger.warning("Failed to fetch user history for motivational comment", exc_info=True, extra={"user": str(author)})

        current_activity_summary = {
            'typ_aktywnosci': activity_type,
            'dystans': distance,
            'punkty': points
        }
        
        prompt = self._build_motivational_comment_prompt(current_activity_summary, user_history)
        
        try:
            return self.gemini_client.generate_text(prompt, temperature=0.8, max_tokens=200)
        except (LLMAnalysisError, LLMTimeoutError) as e:
            logger.error("Failed to generate AI comment", exc_info=True)
            return "Dobra robota!"  # Fallback

    def _save_activity_to_sheets(self, message: discord.Message, analysis: Dict[str, Any], points: int, ai_comment: str) -> bool:
        """
        Zapisuje aktywność do Google Sheets.
        
        Args:
            message: Wiadomość Discord
            analysis: Analiza aktywności
            points: Punkty za aktywność (nie używane - punkty obliczane przez arkusz)
            ai_comment: Komentarz AI (nie zapisywany do arkusza)
        """
        if not self.sheets_manager:
            return False
        try:
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            
            # Określ czy jest obciążenie > 5kg
            weight_value = float(analysis.get('obciazenie') or 0)
            has_weight = weight_value > 5
            
            # Użyj get_display_name z utils
            display_name = get_display_name(message.author)
            
            return self.sheets_manager.add_activity(
                username=display_name,
                activity_type=analysis['typ_aktywnosci'],
                distance=float(analysis['dystans']),
                has_weight=has_weight,
                timestamp=timestamp,
                message_id=str(message.id),
                message_timestamp=str(int(message.created_at.timestamp()))
            )
        except Exception as e:
            logger.error("Failed to save activity to Sheets", exc_info=True, extra={"user": display_name})
            return False

    def _create_response_embed(self, message: discord.Message, analysis: Dict[str, Any], points: int, ai_comment: str, saved: bool) -> discord.Embed:
        """Tworzy embed z odpowiedzią dla użytkownika."""
        activity_type = analysis['typ_aktywnosci']
        info = ACTIVITY_TYPES[activity_type]
        embed = discord.Embed(
            title=f"{info['emoji']} Automatycznie rozpoznano aktywność!",
            color=discord.Color.green() if saved else discord.Color.orange()
        )
        embed.add_field(name="Użytkownik", value=message.author.mention, inline=True)
        embed.add_field(name="Typ", value=info['display_name'], inline=True)
        embed.add_field(name=f"Dystans ({info['unit']})", value=f"{analysis['dystans']}", inline=True)

        if analysis.get('czas'):
            embed.add_field(name="⏱️ Czas", value=analysis['czas'], inline=True)
        if analysis.get('tempo'):
            embed.add_field(name="⚡ Tempo", value=analysis['tempo'], inline=True)
        if analysis.get('puls_sredni'):
            embed.add_field(name="❤️ Puls", value=f"{analysis['puls_sredni']} bpm", inline=True)
        if analysis.get('obciazenie') and float(analysis.get('obciazenie')) > 0:
            embed.add_field(name="🎒 Obciążenie", value=f"{analysis['obciazenie']} kg", inline=True)
        if analysis.get('przewyzszenie') and float(analysis.get('przewyzszenie')) > 0:
            embed.add_field(name="⛰️ Przewyższenie", value=f"{analysis['przewyzszenie']} m", inline=True)
        if analysis.get('kalorie'):
            embed.add_field(name="🔥 Kalorie", value=f"{analysis['kalorie']} kcal", inline=True)
        
        embed.add_field(name="🏆 Punkty", value=f"**{points}**", inline=False)
        
        if ai_comment:
            embed.add_field(name="💬 Komentarz", value=ai_comment, inline=False)
        
        if not saved:
            embed.set_footer(text="⚠️ Dane nie zostały zapisane do Google Sheets")
            
        return embed

    def calculate_points(self, activity_type: str, distance: float, weight: Optional[float] = None, 
                         elevation: Optional[float] = None) -> tuple[int, str]:
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
            channel_id = os.getenv('MONITORED_CHANNEL_ID')
            if not channel_id or channel_id == 'your_channel_id_here':
                logger.warning("Sync skipped: MONITORED_CHANNEL_ID not configured in .env")
                return
            
            try:
                channel = self.bot.get_channel(int(channel_id))
                if not channel:
                    channel = await self.bot.fetch_channel(int(channel_id))
            except discord.errors.Forbidden:
                logger.error("Bot does not have access to the monitored channel", extra={
                    "channel_id": channel_id,
                    "required_permissions": "View Channel, Read Message History"
                })
                return
            except discord.errors.NotFound:
                logger.error("Channel not found", extra={"channel_id": channel_id})
                return
            except Exception as e:
                logger.error("Failed to fetch channel", exc_info=True, extra={"channel_id": channel_id})
                return
            
            # Sprawdź uprawnienia bota w kanale
            permissions = channel.permissions_for(channel.guild.me)
            if not permissions.view_channel or not permissions.read_message_history:
                logger.error("Bot lacks required permissions in channel", extra={
                    "channel": channel.name,
                    "view_channel": permissions.view_channel,
                    "read_message_history": permissions.read_message_history
                })
                return
            
            logger.info("Starting chat history sync", extra={"channel": channel.name})
            
            # KROK 1: Zbierz wszystkie wiadomości z kanału
            all_messages = []
            logger.info("Fetching messages from channel")
            
            # ID wiadomości do debugowania
            DEBUG_MESSAGE_ID = 1445524947186356255
            
            async for message in channel.history(limit=100):
                # DEBUG: Sprawdź konkretną wiadomość
                if message.id == DEBUG_MESSAGE_ID:
                    logger.debug("Found debug message", extra={
                        "message_id": DEBUG_MESSAGE_ID,
                        "author": str(message.author),
                        "is_bot": message.author == self.bot.user,
                        "has_content": bool(message.content),
                        "attachments_count": len(message.attachments)
                    })
                
                # Pomiń wiadomości od bota
                if message.author == self.bot.user:
                    continue
                
                # Sprawdź czy wiadomość ma zdjęcie LUB zawiera słowa kluczowe aktywności
                has_image = self._is_message_eligible_for_analysis(message)
                has_keywords = self._detect_activity_type_from_text(message.content) if message.content else None
                
                if has_image or has_keywords:
                    all_messages.append(message)
            
            logger.info("Messages fetched", extra={"count": len(all_messages)})
            
            # KROK 2: Filtruj wiadomości - tylko te, których IID NIE MA w cache
            messages_to_process = []
            for message in all_messages:
                is_duplicate = self._activity_already_exists(message)
                if not is_duplicate:
                    messages_to_process.append(message)
            
            logger.info("Duplicate check complete", extra={
                "new_messages": len(messages_to_process),
                "duplicates_skipped": len(all_messages) - len(messages_to_process)
            })
            
            # KROK 3: Przetwarzaj tylko unikalne wiadomości
            processed, added, not_recognized = 0, 0, 0
            
            for message in messages_to_process:
                processed += 1
                try:
                    # Sprawdź czy ma zdjęcie i/lub tekst
                    image_url = self._get_image_url(message)
                    has_keywords = self._detect_activity_type_from_text(message.content) if message.content else None
                    
                    analysis = None
                    
                    # PRIORYTET: Jeśli ma zdjęcie, ZAWSZE analizuj zdjęcie (wraz z tekstem jeśli istnieje)
                    if image_url:
                        logger.debug("Analyzing image from sync", extra={
                            "message_id": message.id,
                            "has_text": bool(message.content)
                        })
                        # Dla synchronizacji nie przekazujemy historii (oszczędność tokenów)
                        analysis = self._analyze_image_with_gemini(image_url, message.content, None)
                    # Jeśli NIE MA zdjęcia ALE ma keywords, analizuj jako tekst
                    elif has_keywords:
                        logger.debug("Analyzing text from sync", extra={
                            "message_id": message.id,
                            "activity_type": has_keywords
                        })
                        analysis = await self._analyze_text_with_ai(message.content)
                    else:
                        # Ani zdjęcia, ani keywords - nie powinno się zdarzyć (filtrowane w KROK 1)
                        continue
                    
                    if not analysis:
                        not_recognized += 1
                        logger.debug("AI did not return analysis for sync message", extra={"message_id": message.id})
                        continue
                    
                    # Sprawdź czy mamy podstawowe dane lub zastosuj fallback
                    has_basic_data = analysis and analysis.get('typ_aktywnosci') and analysis.get('dystans')
                    
                    # Fallback dla aktywności bez dystansu (jak w handle_message)
                    if not has_basic_data and analysis and analysis.get('komentarz'):
                        comment = analysis.get('komentarz', '')
                        sport_keywords = ['aktywność', 'trening', 'sport', 'czas trwania', 'tętno', 'bpm',
                                        'soccer', 'football', 'cardio', 'fitness', 'gym', 'workout']
                        
                        if any(keyword.lower() in comment.lower() for keyword in sport_keywords):
                            time_minutes = self._extract_time_from_comment(comment)
                            
                            if time_minutes and time_minutes > 5:
                                distance = self._convert_time_to_cardio_distance(time_minutes)
                                logger.debug("Fallback sync: converted time to distance", extra={
                                    "time_minutes": time_minutes,
                                    "distance_km": distance
                                })
                                
                                analysis['typ_aktywnosci'] = 'cardio'
                                analysis['dystans'] = distance
                                analysis['czas'] = f"{int(time_minutes)} min"
                                has_basic_data = True
                    
                    if has_basic_data:
                        # Zapisz aktywność (IID automatycznie dodane do cache w add_activity)
                        points, error_msg = self.calculate_points(
                            analysis['typ_aktywnosci'], float(analysis['dystans']),
                            float(analysis.get('obciazenie') or 0) or None,
                            float(analysis.get('przewyzszenie') or 0) or None
                        )
                        
                        if not error_msg and points > 0:
                            saved = self._save_activity_to_sheets(message, analysis, points, f"[SYNC] {analysis.get('komentarz', '')}")
                            if saved:
                                added += 1
                                logger.info("Activity added from sync", extra={
                                    "activity_type": analysis['typ_aktywnosci'],
                                    "distance": analysis['dystans'],
                                    "points": points
                                })
                    else:
                        # Nie rozpoznano aktywności
                        not_recognized += 1
                        logger.debug("Activity not recognized in sync message", extra={
                            "message_id": message.id,
                            "comment": analysis.get('komentarz', 'No data')
                        })
                
                except Exception as e:
                    logger.warning("Error analyzing message during sync", exc_info=True, extra={"message_id": message.id})
            
            logger.info("Sync completed", extra={
                "analyzed": processed,
                "added": added,
                "duplicates_skipped": len(all_messages) - len(messages_to_process),
                "not_recognized": not_recognized
            })
            
        except Exception as e:
            logger.error("Critical sync error", exc_info=True)

    def _build_activity_analysis_prompt(self, text_context: Optional[str], user_history: Optional[str] = None) -> str:
        """Buduje prompt do analizy aktywności na podstawie obrazu, tekstu i historii użytkownika."""
        # Pobierz prompt z konfiguracji
        provider = config_manager.get_llm_provider()
        prompts = config_manager.get_llm_prompts(provider)
        
        base_prompt = prompts.get("activity_analysis")
        if not base_prompt:
            raise ConfigurationError(
                f"Missing 'activity_analysis' prompt for provider '{provider}' in config.json"
            )

        if text_context:
            user_prompt = prompts.get("user_prompt_with_context", "{system_prompt}")
            return user_prompt.format(
                text_context=text_context or "",
                user_history=user_history or "Brak wcześniejszych aktywności.",
                system_prompt=base_prompt
            )
        return base_prompt

    def _build_motivational_comment_prompt(self, current_activity: Dict[str, Any], previous_activities: List[Dict[str, Any]]) -> str:
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
            distances = [parse_distance(act.get('Dystans (km)', 0)) for act in previous_activities]
            total_distance = sum(distances)
            total_points = sum(int(act.get('PUNKTY', 0)) for act in previous_activities)
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
            activity_type=current_activity.get('typ_aktywnosci', 'nieznany'),
            distance=current_activity.get('dystans', 0),
            points=current_activity.get('punkty', 0),
            activity_count=activity_count,
            total_distance=f"{total_distance:.1f}",
            total_points=total_points,
            history_text=history_text
        )
