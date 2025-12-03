# bot/orchestrator.py
import os
from typing import Optional, Dict, Any, List
import discord
from .config_manager import config_manager

class BotOrchestrator:
    """Orkiestruje logikę biznesową bota."""

    # Typy aktywności i ich punktacja bazowa (zgodnie z wytycznymi konkursu)
    ACTIVITY_TYPES = {
        "bieganie_teren": {
            "emoji": "🏃", 
            "base_points": 1000, 
            "unit": "km",
            "min_distance": 0,
            "bonuses": ["obciążenie", "przewyższenie"],
            "display_name": "Bieganie (Teren)"
        },
        "bieganie_bieznia": {
            "emoji": "🏃‍♂️", 
            "base_points": 800, 
            "unit": "km",
            "min_distance": 0,
            "bonuses": ["obciążenie"],
            "display_name": "Bieganie (Bieżnia)"
        },
        "plywanie": {
            "emoji": "🏊", 
            "base_points": 4000, 
            "unit": "km",
            "min_distance": 0,
            "bonuses": [],
            "display_name": "Pływanie"
        },
        "rower": {
            "emoji": "🚴", 
            "base_points": 300, 
            "unit": "km",
            "min_distance": 6,
            "bonuses": ["przewyższenie"],
            "display_name": "Rower/Rolki"
        },
        "spacer": {
            "emoji": "🚶", 
            "base_points": 200, 
            "unit": "km",
            "min_distance": 3,
            "bonuses": ["obciążenie", "przewyższenie"],
            "display_name": "Spacer/Trekking"
        },
        "cardio": {
            "emoji": "🔫", 
            "base_points": 800, 
            "unit": "km",
            "min_distance": 0,
            "bonuses": ["obciążenie", "przewyższenie"],
            "display_name": "Inne Cardio (wioślarz, orbitrek, ASG)"
        },
    }

    def __init__(self, bot, gemini_client, sheets_manager):
        self.bot = bot
        self.gemini_client = gemini_client
        self.sheets_manager = sheets_manager

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

            # Analiza obrazu przez Gemini
            analysis = self._analyze_image_with_gemini(image_url, message.content)

            if analysis and analysis.get('typ_aktywnosci') and analysis.get('dystans'):
                await self._process_successful_analysis(message, analysis)
            else:
                await message.remove_reaction('🤔', self.bot.user)

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

        has_image = any(
            att.content_type and att.content_type.startswith('image/') and att.content_type != 'image/gif'
            for att in message.attachments
        )
        if not has_image:
            return False

        keywords = ['bieg', 'rower', 'pływa', 'spacer', 'trening', 'km', 'kilometr']
        has_keywords = any(keyword in message.content.lower() for keyword in keywords) if message.content else False

        # Analizuj jeśli jest obraz i (brak tekstu LUB tekst zawiera słowa kluczowe)
        return not message.content or has_keywords

    def _get_image_url(self, message: discord.Message) -> Optional[str]:
        """Zwraca URL pierwszego obrazu z wiadomości (nie-GIF)."""
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/') and attachment.content_type != 'image/gif':
                return attachment.url
        return None

    def _analyze_image_with_gemini(self, image_url: str, text_context: Optional[str]) -> Dict[str, Any]:
        """Tworzy prompt i wywołuje analizę obrazu w LLM Client."""
        prompt = self._build_activity_analysis_prompt(text_context)
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
                user_history = self.sheets_manager.get_user_history(str(author))
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
        """Zapisuje aktywność do Google Sheets."""
        if not self.sheets_manager:
            return False
        try:
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            return self.sheets_manager.add_activity(
                username=str(message.author),
                activity_type=analysis['typ_aktywnosci'],
                distance=float(analysis['dystans']),
                weight=float(analysis.get('obciazenie') or 0) or None,
                elevation=float(analysis.get('przewyzszenie') or 0) or None,
                points=points,
                comment=ai_comment, # Zapisujemy komentarz AI
                timestamp=timestamp,
                message_id=str(message.id)
            )
        except Exception as e:
            print(f"Błąd zapisu do Sheets w orchestratorze: {e}")
            return False

    def _create_response_embed(self, message: discord.Message, analysis: Dict[str, Any], points: int, ai_comment: str, saved: bool) -> discord.Embed:
        """Tworzy embed z odpowiedzią dla użytkownika."""
        activity_type = analysis['typ_aktywnosci']
        info = self.ACTIVITY_TYPES[activity_type]
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
        if activity_type not in self.ACTIVITY_TYPES:
            return 0, f"Nieznany typ aktywności: {activity_type}"
        
        activity_info = self.ACTIVITY_TYPES[activity_type]
        
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
            
            existing_message_ids = self.sheets_manager.get_all_message_ids()
            print(f"📋 Znaleziono {len(existing_message_ids)} aktywności w arkuszu")
            
            processed, added, skipped = 0, 0, 0
            
            async for message in channel.history(limit=100):
                if message.author == self.bot.user or str(message.id) in existing_message_ids:
                    if str(message.id) in existing_message_ids: skipped += 1
                    continue
                
                if not self._is_message_eligible_for_analysis(message):
                    continue
                
                processed += 1
                try:
                    image_url = self._get_image_url(message)
                    if not image_url: continue

                    analysis = self._analyze_image_with_gemini(image_url, message.content)
                    
                    if analysis and analysis.get('typ_aktywnosci') and analysis.get('dystans'):
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
                
                except Exception as e:
                    print(f"  ⚠️ Błąd analizy wiadomości podczas synchronizacji: {e}")
            
            print(f"\n✅ Synchronizacja zakończona! Przeanalizowano: {processed}, Dodano: {added}, Pominięto: {skipped}")
            
        except Exception as e:
            print(f"❌ Krytyczny błąd synchronizacji: {e}")

    def _build_activity_analysis_prompt(self, text_context: Optional[str]) -> str:
        """Buduje prompt do analizy aktywności na podstawie obrazu i tekstu."""
        # Pobierz prompt z konfiguracji
        provider = config_manager.get_llm_provider()
        prompts = config_manager.get_llm_prompts(provider)
        
        base_prompt = prompts.get("activity_analysis", """Przeanalizuj to zdjęcie aktywności sportowej.

Wyciągnij następujące informacje i zwróć TYLKO obiekt JSON (bez markdown):
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
- Przeanalizuj dokładnie dane widoczne na zdjęciu (aplikacja Garmin, Strava, itp.)
- Jeśli dane nie są widoczne, zwróć null
- Dystans ZAWSZE w kilometrach
- Bądź precyzyjny - przepisuj dokładne wartości ze zdjęcia
- Zwróć TYLKO JSON, bez ```json ani innych formatowań""")

        if text_context:
            return f"""Przeanalizuj to zdjęcie aktywności sportowej wraz z kontekstem tekstowym.

Tekst użytkownika: "{text_context}"

{base_prompt}"""
        return base_prompt

    def _build_motivational_comment_prompt(self, current_activity: Dict[str, Any], previous_activities: List[Dict[str, Any]]) -> str:
        """Buduje prompt do wygenerowania komentarza motywacyjnego."""
        # Przygotuj kontekst historii
        if previous_activities:
            recent = previous_activities[-5:]
            history_summary = [
                f"- {act.get('Aktywność', 'N/A')}: {act.get('Dystans (km)', 0)} km, {act.get('Punkty', 0)} pkt (Data: {act.get('Data', 'N/A')})"
                for act in recent
            ]
            history_text = "\n".join(history_summary)
            total_distance = sum(float(act.get('Dystans (km)', 0)) for act in previous_activities)
            total_points = sum(int(act.get('Punkty', 0)) for act in previous_activities)
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
