# bot/orchestrator.py
import os
from typing import Optional, Dict, Any, List
import discord
from .config_manager import config_manager
from .constants import ACTIVITY_TYPES
from .utils import get_display_name, parse_distance

class BotOrchestrator:
    """Orkiestruje logikę biznesową bota."""

    def __init__(self, bot, gemini_client, sheets_manager):
        self.bot = bot
        self.gemini_client = gemini_client
        self.sheets_manager = sheets_manager

    def _create_unique_id(self, message: discord.Message) -> str:
        """
        Tworzy unikalny ID dla wiadomości Discord.
        
        Args:
            message: Wiadomość Discord
            
        Returns:
            Unikalny ID w formacie: {timestamp}_{message_id}
        """
        return f"{message.created_at.timestamp()}_{message.id}"
    
    def _activity_already_exists(self, message: discord.Message, analysis: Dict[str, Any] = None) -> bool:
        """
        Sprawdza czy aktywność z danej wiadomości już istnieje w arkuszu.
        
        Args:
            message: Wiadomość Discord
            analysis: Analiza aktywności (jeśli dostępna)
            
        Returns:
            True jeśli aktywność już istnieje, False w przeciwnym razie
        """
        if not self.sheets_manager:
            return False
        
        # Używamy IID (message_timestamp_message_id) do sprawdzania duplikatów
        message_id = str(message.id)
        message_timestamp = str(int(message.created_at.timestamp()))
        
        return self.sheets_manager.activity_exists(message_id, message_timestamp)

    async def handle_message(self, message: discord.Message):
        """Przetwarza wiadomość i decyduje o podjęciu akcji."""
        # Ignoruj własne wiadomości i komendy
        if message.author == self.bot.user or message.content.startswith('!'):
            return

        # Sprawdź czy wiadomość kwalifikuje się do analizy
        if not self._is_message_eligible_for_analysis(message):
            return

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

            # Analiza obrazu przez Gemini
            analysis = self._analyze_image_with_gemini(image_url, message.content, user_history_text)

            if analysis and analysis.get('typ_aktywnosci') and analysis.get('dystans'):
                # Sprawdź czy aktywność już została dodana (duplikat)
                if self._activity_already_exists(message, analysis):
                    print(f"⚠️ Aktywność z wiadomości {message.id} już istnieje w arkuszu - pomijam")
                    await message.remove_reaction('🤔', self.bot.user)
                    await message.add_reaction('✅')  # Już dodane
                    return
                
                await self._process_successful_analysis(message, analysis)
            else:
                # Zdjęcie nie zawiera danych o aktywności
                await message.remove_reaction('🤔', self.bot.user)
                await message.add_reaction('❓')
                
                # Opcjonalnie wyślij krótką wiadomość
                await message.reply(
                    "❓ Nie mogłem rozpoznać danych o aktywności na tym zdjęciu. "
                    "Upewnij się, że zdjęcie zawiera wyraźne informacje o dystansie i typie aktywności.",
                    delete_after=30  # Usuń po 30 sekundach
                )
                print(f"⚠️ Brak danych o aktywności w analizie zdjęcia od {message.author}")

        except Exception as e:
            print(f"Błąd analizy wiadomości w orchestratorze: {e}")
            try:
                await message.remove_reaction('🤔', self.bot.user)
                await message.add_reaction('❓')
            except discord.errors.NotFound:
                pass # Wiadomość mogła zostać usunięta

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
                print(f"Nie udało się pobrać historii użytkownika {author}: {e}")

        current_activity_summary = {
            'typ_aktywnosci': activity_type,
            'dystans': distance,
            'punkty': points
        }
        
        prompt = self._build_motivational_comment_prompt(current_activity_summary, user_history)
        
        try:
            return self.gemini_client.generate_text(prompt, temperature=0.8, max_tokens=200)
        except Exception as e:
            print(f"Błąd generowania komentarza AI: {e}")
            return "Dobra robota!" # Fallback

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
            print(f"Błąd zapisu do Sheets w orchestratorze: {e}")
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
            print("⚠️ Brak menedżera arkuszy lub klienta Gemini - pomijam synchronizację.")
            return

        try:
            channel_id = os.getenv('MONITORED_CHANNEL_ID')
            if not channel_id or channel_id == 'your_channel_id_here':
                print("⚠️ Brak MONITORED_CHANNEL_ID w .env - pomijam synchronizację")
                return
            
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                channel = await self.bot.fetch_channel(int(channel_id))
            
            print(f"🔄 Rozpoczynam synchronizację historii czatu dla kanału: {channel.name}")
            
            processed, added, skipped, not_recognized = 0, 0, 0, 0
            
            async for message in channel.history(limit=100):
                # Pomiń wiadomości od bota
                if message.author == self.bot.user:
                    continue
                
                if not self._is_message_eligible_for_analysis(message):
                    continue
                
                processed += 1
                try:
                    image_url = self._get_image_url(message)
                    if not image_url: continue

                    # Dla synchronizacji nie przekazujemy historii (oszczędność tokenów)
                    analysis = self._analyze_image_with_gemini(image_url, message.content, None)
                    
                    if analysis and analysis.get('typ_aktywnosci') and analysis.get('dystans'):
                        # Sprawdź czy aktywność już istnieje w arkuszu
                        if self._activity_already_exists(message, analysis):
                            skipped += 1
                            continue
                        
                        points, error_msg = self.calculate_points(
                            analysis['typ_aktywnosci'], float(analysis['dystans']),
                            float(analysis.get('obciazenie') or 0) or None,
                            float(analysis.get('przewyzszenie') or 0) or None
                        )
                        
                        if not error_msg and points > 0:
                            saved = self._save_activity_to_sheets(message, analysis, points, f"[SYNC] {analysis.get('komentarz', '')}")
                            if saved:
                                added += 1
                                print(f"  ✅ Dodano z synchronizacji: {analysis['typ_aktywnosci']} {analysis['dystans']}km ({points} pkt)")
                    else:
                        # Nie rozpoznano aktywności
                        not_recognized += 1
                        print(f"  ⚠️ Nie rozpoznano aktywności w wiadomości {message.id}: {analysis.get('komentarz', 'Brak danych')}")
                
                except Exception as e:
                    print(f"  ⚠️ Błąd analizy wiadomości podczas synchronizacji: {e}")
            
            print(f"\n✅ Synchronizacja zakończona!")
            print(f"   📊 Przeanalizowano: {processed}")
            print(f"   ➕ Dodano: {added}")
            print(f"   ⏭️ Pominięto (już istnieją): {skipped}")
            print(f"   ❓ Nie rozpoznano: {not_recognized}")
            
        except Exception as e:
            print(f"❌ Krytyczny błąd synchronizacji: {e}")

    def _build_activity_analysis_prompt(self, text_context: Optional[str], user_history: Optional[str] = None) -> str:
        """Buduje prompt do analizy aktywności na podstawie obrazu, tekstu i historii użytkownika."""
        # Pobierz prompt z konfiguracji
        provider = config_manager.get_llm_provider()
        prompts = config_manager.get_llm_prompts(provider)
        
        base_prompt = prompts.get("activity_analysis", """Przeanalizuj to zdjęcie i sprawdź czy zawiera dane o aktywności sportowej.

Jeśli zdjęcie NIE ZAWIERA danych o aktywności sportowej (aplikacja fitness, zrzut ekranu treningowy itp.), zwróć:
{
  "typ_aktywnosci": null,
  "dystans": null,
  "komentarz": "Nie wykryto danych o aktywności sportowej na zdjęciu"
}

Jeśli zdjęcie ZAWIERA dane o aktywności, wyciągnij następujące informacje i zwróć TYLKO obiekt JSON (bez markdown):
{
  "typ_aktywnosci": "jeden z [bieganie_teren, bieganie_bieznia, plywanie, rower, spacer, cardio]",
  "dystans": float,
  "czas": "string lub null",
  "tempo": "string lub null",
  "obciazenie": float lub null,
  "przewyzszenie": float lub null,
  "kalorie": int lub null,
  "puls_sredni": int lub null,
  "komentarz": "string"
}

WAŻNE:
- Przeanalizuj dokładnie dane widoczne na zdjęciu (aplikacja Garmin, Strava, Endomondo itp.)
- Jeśli konkretne dane nie są widoczne, zwróć null dla tego pola
- Dystans ZAWSZE w kilometrach
- Bądź precyzyjny - przepisuj dokładne wartości ze zdjęcia
- Zwróć TYLKO JSON, bez ```json ani innych formatowań""")

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
        
        prompt_template = prompts.get("motivational_comment", """Napisz krótki (2-4 zdania), motywujący komentarz dla użytkownika.

AKTUALNA AKTYWNOŚĆ:
- Typ: {activity_type}
- Dystans: {distance} km
- Punkty: {points}

HISTORIA UŻYTKOWNIKA:
- Łącznie aktywności: {activity_count}
- Łączny dystans: {total_distance} km
- Łączne punkty: {total_points}

Ostatnie aktywności:
{history_text}

WYTYCZNE:
- Bądź entuzjastyczny i wspierający.
- Odnieś się do postępów (jeśli widoczne).
- Zachęć do kontynuacji.
- Użyj naturalnego, przyjacielskiego języka.
- Jeśli to pierwsza aktywność, powitaj i zmotywuj.
- Jeśli użytkownik poprawia wyniki, podkreśl to.
- Dodaj 2-3 emoji dla lepszego efektu.""")
        
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
