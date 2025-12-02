"""Szczypior Discord Bot - Główny plik uruchomieniowy."""

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from typing import Optional
from .sheets_manager import SheetsManager
from .gemini_client import GeminiClient

# Wczytaj zmienne środowiskowe
load_dotenv()

# Konfiguracja bota
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Menedżer Google Sheets
sheets_manager = None

# Klient Gemini AI
gemini_client = None

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


@bot.event
async def on_ready():
    """Wywoływane gdy bot jest gotowy."""
    global sheets_manager, gemini_client
    print(f"{bot.user} jest online!")
    print(f"ID bota: {bot.user.id}")
    
    # Inicjalizacja Google Sheets (opcjonalne - tylko jeśli skonfigurowane)
    try:
        sheets_manager = SheetsManager()
        sheets_manager.setup_headers()
        print("✅ Google Sheets połączony i gotowy")
    except Exception as e:
        print(f"⚠️ Google Sheets niedostępny: {e}")
        print("ℹ️ Bot będzie działał bez zapisywania danych")
    
    # Inicjalizacja Gemini AI (opcjonalne - tylko jeśli skonfigurowane)
    try:
        gemini_client = GeminiClient()
        print(f"✅ Gemini AI połączony: {gemini_client.model_name}")
    except Exception as e:
        print(f"⚠️ Gemini AI niedostępny: {e}")
        print("ℹ️ Bot będzie działał bez funkcji AI")
    
    # Synchronizacja historii czatu z Google Sheets
    if sheets_manager and gemini_client:
        print("\n🔄 Rozpoczynam synchronizację historii czatu...")
        await sync_chat_history()


async def sync_chat_history():
    """Synchronizuje historię czatu z Google Sheets - dodaje brakujące aktywności."""
    try:
        # Pobierz ID kanału do monitorowania z .env
        channel_id = os.getenv('MONITORED_CHANNEL_ID')
        if not channel_id or channel_id == 'your_channel_id_here':
            print("⚠️ Brak MONITORED_CHANNEL_ID w .env - pomijam synchronizację")
            return
        
        # Poczekaj na pełne połączenie bota
        await bot.wait_until_ready()
        
        # Spróbuj znaleźć kanał w różny sposób
        channel = bot.get_channel(int(channel_id))
        
        # Jeśli nie znaleziono, spróbuj fetch
        if not channel:
            try:
                channel = await bot.fetch_channel(int(channel_id))
            except Exception as e:
                print(f"❌ Nie można pobrać kanału: {e}")
                print(f"   Sprawdź czy bot ma dostęp do kanału ID: {channel_id}")
                print(f"   Upewnij się że bot jest na serwerze i ma uprawnienia do czytania historii")
                return
        
        print(f"📊 Skanowanie kanału: {channel.name} (ID: {channel.id})")
        
        # Pobierz Message ID już zapisane w Sheets
        existing_message_ids = sheets_manager.get_all_message_ids()
        print(f"📋 Znaleziono {len(existing_message_ids)} aktywności w arkuszu")
        
        # Skanuj historię kanału (ostatnie 100 wiadomości)
        processed = 0
        added = 0
        skipped = 0
        
        print("🔍 Pobieram historię wiadomości...")
        async for message in channel.history(limit=100):
            # Pomiń wiadomości bota
            if message.author == bot.user:
                continue
            
            # Pomiń wiadomości już przetworzone
            if str(message.id) in existing_message_ids:
                skipped += 1
                continue
            
            # Sprawdź czy wiadomość ma załącznik (obraz, nie GIF)
            has_image = False
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    if attachment.content_type != 'image/gif':
                        has_image = True
                        break
            
            if not has_image:
                continue
            
            # Sprawdź czy zawiera słowa kluczowe o aktywności (lub brak treści - same zdjęcie)
            keywords = ['bieg', 'rower', 'pływa', 'spacer', 'trening', 'km', 'kilometr']
            has_keywords = any(keyword in message.content.lower() for keyword in keywords) if message.content else False
            
            # Jeśli nie ma słów kluczowych i nie jest puste, pomiń
            if message.content and not has_keywords:
                continue
            
            # Analizuj wiadomość za pomocą Gemini
            try:
                processed += 1
                content_preview = message.content[:50] if message.content else "[samo zdjęcie]"
                print(f"🔍 Analizuję wiadomość od {message.author}: {content_preview}...")
                
                # Znajdź URL obrazu
                image_url = None
                for attachment in message.attachments:
                    if attachment.content_type and attachment.content_type.startswith('image/'):
                        if attachment.content_type != 'image/gif':
                            image_url = attachment.url
                            break
                
                if not image_url:
                    continue
                
                # Analizuj obraz za pomocą Gemini
                analysis = gemini_client.analyze_activity_from_image(
                    image_url,
                    message.content if message.content else None
                )
                
                if analysis.get('typ_aktywnosci') and analysis.get('dystans'):
                    activity_type = analysis['typ_aktywnosci']
                    distance = float(analysis['dystans'])
                    weight = float(analysis.get('obciazenie') or 0)
                    elevation = float(analysis.get('przewyzszenie') or 0)
                    comment = analysis.get('komentarz', '')
                    
                    # Oblicz punkty
                    points, error_msg = calculate_points(
                        activity_type, distance,
                        weight if weight > 0 else None,
                        elevation if elevation > 0 else None
                    )
                    
                    if not error_msg and points > 0:
                        # Zapisz do Sheets z timestampem wiadomości
                        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        saved = sheets_manager.add_activity(
                            username=str(message.author),
                            activity_type=activity_type,
                            distance=distance,
                            weight=weight if weight > 0 else None,
                            elevation=elevation if weight > 0 else None,
                            points=points,
                            comment=f"[SYNC] {comment}",
                            timestamp=timestamp,
                            message_id=str(message.id)
                        )
                        
                        if saved:
                            added += 1
                            print(f"  ✅ Dodano: {activity_type} {distance}km ({points} pkt)")
                
            except Exception as e:
                print(f"  ⚠️ Błąd analizy wiadomości: {e}")
        
        print(f"\n✅ Synchronizacja zakończona!")
        print(f"  📊 Przeanalizowano: {processed} wiadomości")
        print(f"  ➕ Dodano nowych: {added} aktywności")
        print(f"  ⏭️ Pominięto: {skipped} (już istnieją)")
        
    except Exception as e:
        print(f"❌ Błąd synchronizacji: {e}")


@bot.event
async def on_message(message):
    """Wywoływane gdy bot otrzyma wiadomość."""
    # Ignoruj własne wiadomości
    if message.author == bot.user:
        return
    
    # Przetwarzaj komendy (!)
    await bot.process_commands(message)
    
    # Jeśli wiadomość nie jest komendą i Gemini jest dostępny
    if not message.content.startswith('!') and gemini_client:
        # Sprawdź czy wiadomość zawiera załączniki (obrazy)
        if not message.attachments:
            return
        
        # Sprawdź czy jest przynajmniej jedno zdjęcie (nie GIF)
        has_image = False
        for attachment in message.attachments:
            # Sprawdź czy to obraz i nie jest GIFem
            if attachment.content_type and attachment.content_type.startswith('image/'):
                if not attachment.content_type == 'image/gif':
                    has_image = True
                    break
        
        # Jeśli nie ma żadnego obrazu (tylko GIFy lub inne pliki), ignoruj
        if not has_image:
            return
        
        # Sprawdź czy wiadomość zawiera wzmiankę o aktywności (lub brak treści - same zdjęcie)
        keywords = ['bieg', 'rower', 'pływa', 'spacer', 'trening', 'km', 'kilometr']
        has_keywords = any(keyword in message.content.lower() for keyword in keywords) if message.content else False
        
        # Jeśli jest treść ale nie ma słów kluczowych, ignoruj
        if message.content and not has_keywords:
            return
        
        # Dodaj reakcję żeby pokazać że bot przetwarza
        await message.add_reaction('🤔')
        
        try:
            # Pobierz URL pierwszego obrazu (nie GIF)
            image_url = None
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    if attachment.content_type != 'image/gif':
                        image_url = attachment.url
                        break
            
            if not image_url:
                await message.remove_reaction('🤔', bot.user)
                return
            
            # Analizuj obraz za pomocą Gemini
            analysis = gemini_client.analyze_activity_from_image(
                image_url, 
                message.content if message.content else None
            )
            
            # Sprawdź czy udało się wyodrębnić aktywność
            if analysis.get('typ_aktywnosci') and analysis.get('dystans'):
                activity_type = analysis['typ_aktywnosci']
                distance = float(analysis['dystans'])
                weight = float(analysis.get('obciazenie') or 0)
                elevation = float(analysis.get('przewyzszenie') or 0)
                
                # Oblicz punkty
                points, error_msg = calculate_points(
                    activity_type, distance, 
                    weight if weight > 0 else None,
                    elevation if elevation > 0 else None
                )
                
                if not error_msg and points > 0:
                    # Usuń reakcję "myślenia"
                    await message.remove_reaction('🤔', bot.user)
                    
                    # Pobierz historię użytkownika dla kontekstu
                    user_history = []
                    if sheets_manager:
                        try:
                            user_history = sheets_manager.get_user_history(str(message.author))
                        except:
                            pass
                    
                    # Wygeneruj spersonalizowany komentarz
                    try:
                        ai_comment = gemini_client.generate_motivational_comment(
                            {
                                'typ_aktywnosci': activity_type,
                                'dystans': distance,
                                'punkty': points
                            },
                            user_history
                        )
                    except Exception as e:
                        print(f"Błąd generowania komentarza: {e}")
                        ai_comment = analysis.get('komentarz', '')
                    
                    # Zapisz do Google Sheets jeśli dostępny
                    saved = False
                    if sheets_manager:
                        try:
                            # Zapisz z Message ID i komentarzem AI
                            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                            saved = sheets_manager.add_activity(
                                username=str(message.author),
                                activity_type=activity_type,
                                distance=distance,
                                weight=weight if weight > 0 else None,
                                elevation=elevation if elevation > 0 else None,
                                points=points,
                                comment=analysis.get('komentarz', ''),
                                timestamp=timestamp,
                                message_id=str(message.id)
                            )
                        except Exception as e:
                            print(f"Błąd zapisu do Sheets: {e}")
                    
                    # Przygotuj odpowiedź
                    info = ACTIVITY_TYPES[activity_type]
                    embed = discord.Embed(
                        title=f"{info['emoji']} Automatycznie rozpoznano aktywność!",
                        color=discord.Color.green() if saved else discord.Color.orange()
                    )
                    
                    embed.add_field(name="Użytkownik", value=message.author.mention, inline=True)
                    embed.add_field(name="Typ", value=info['display_name'], inline=True)
                    embed.add_field(name=f"Dystans ({info['unit']})", value=f"{distance}", inline=True)
                    
                    # Dodatkowe dane z analizy obrazu
                    if analysis.get('czas'):
                        embed.add_field(name="⏱️ Czas", value=analysis['czas'], inline=True)
                    if analysis.get('tempo'):
                        embed.add_field(name="⚡ Tempo", value=analysis['tempo'], inline=True)
                    if analysis.get('puls_sredni'):
                        embed.add_field(name="❤️ Puls", value=f"{analysis['puls_sredni']} bpm", inline=True)
                    
                    if weight > 0:
                        embed.add_field(name="🎒 Obciążenie", value=f"{weight} kg", inline=True)
                    if elevation > 0:
                        embed.add_field(name="⛰️ Przewyższenie", value=f"{elevation} m", inline=True)
                    if analysis.get('kalorie'):
                        embed.add_field(name="🔥 Kalorie", value=f"{analysis['kalorie']} kcal", inline=True)
                    
                    embed.add_field(name="🏆 Punkty", value=f"**{points}**", inline=False)
                    
                    # Dodaj spersonalizowany komentarz AI
                    if ai_comment:
                        embed.add_field(name="💬 Komentarz", value=ai_comment, inline=False)
                    
                    if not saved:
                        embed.set_footer(text="⚠️ Dane nie zostały zapisane do Google Sheets")
                    
                    await message.reply(embed=embed)
                    await message.add_reaction('✅')
                else:
                    # Usuń reakcję "myślenia"
                    await message.remove_reaction('🤔', bot.user)
            else:
                # Usuń reakcję jeśli nie rozpoznano aktywności
                await message.remove_reaction('🤔', bot.user)
                
        except Exception as e:
            # Usuń reakcję w przypadku błędu
            try:
                await message.remove_reaction('🤔', bot.user)
                await message.add_reaction('❓')
            except:
                pass
            print(f"Błąd analizy wiadomości: {e}")


@bot.command(name="ping")
async def ping(ctx):
    """Sprawdza czy bot odpowiada."""
    await ctx.send(f"Pong! Latencja: {round(bot.latency * 1000)}ms")


@bot.command(name="hello")
async def hello(ctx):
    """Powitanie od Szczypior Bota."""
    await ctx.send(f"Cześć {ctx.author.mention}! Jestem Szczypior Bot! 🌿")


def calculate_points(activity_type: str, distance: float, weight: Optional[float] = None, 
                     elevation: Optional[float] = None) -> tuple[int, str]:
    """
    Oblicza punkty za aktywność zgodnie z wytycznymi konkursu.
    
    Args:
        activity_type: Typ aktywności
        distance: Dystans w km
        weight: Obciążenie w kg (opcjonalne)
        elevation: Przewyższenie w m (opcjonalne)
        
    Returns:
        Tuple (liczba punktów, komunikat o błędzie lub '')
    """
    if activity_type not in ACTIVITY_TYPES:
        return 0, f"Nieznany typ aktywności: {activity_type}"
    
    activity_info = ACTIVITY_TYPES[activity_type]
    
    # Sprawdź minimalny dystans
    min_distance = activity_info.get("min_distance", 0)
    if distance < min_distance:
        return 0, f"Minimalny dystans dla {activity_info['display_name']}: {min_distance} km"
    
    # Oblicz punkty bazowe
    base_points = activity_info["base_points"]
    points = int(distance * base_points)
    
    # Bonusy
    bonuses = activity_info.get("bonuses", [])
    
    if weight and weight > 0:
        if "obciążenie" in bonuses:
            # Bonus za obciążenie - zakładamy 10% bazowej wartości za każde 5kg
            bonus = int((weight / 5) * (distance * base_points * 0.1))
            points += bonus
        else:
            return 0, f"Aktywność {activity_info['display_name']} nie wspiera bonusu za obciążenie"
    
    if elevation and elevation > 0:
        if "przewyższenie" in bonuses:
            # Bonus za przewyższenie - zakładamy 5% bazowej wartości za każde 100m
            bonus = int((elevation / 100) * (distance * base_points * 0.05))
            points += bonus
        else:
            return 0, f"Aktywność {activity_info['display_name']} nie wspiera bonusu za przewyższenie"
    
    return max(points, 1), ""  # Minimum 1 punkt


@bot.command(name="typy_aktywnosci")
async def list_activities(ctx):
    """Wyświetla dostępne typy aktywności."""
    embed = discord.Embed(
        title="🏃 Dostępne typy aktywności",
        description="Lista wszystkich typów aktywności zgodnie z wytycznymi konkursu:",
        color=discord.Color.green()
    )
    
    for activity, info in ACTIVITY_TYPES.items():
        bonuses_text = ", ".join(info['bonuses']) if info['bonuses'] else "brak"
        min_dist_text = f"{info['min_distance']} km" if info['min_distance'] > 0 else "BRAK"
        
        embed.add_field(
            name=f"{info['emoji']} {info['display_name']}",
            value=(
                f"**{info['base_points']} pkt/{info['unit']}**\n"
                f"Min. dystans: {min_dist_text}\n"
                f"Bonusy: {bonuses_text}"
            ),
            inline=True
        )
    
    embed.set_footer(text="Użyj: !dodaj_aktywnosc <typ> <wartość> [obciążenie] [przewyższenie]")
    await ctx.send(embed=embed)


@bot.command(name="dodaj_aktywnosc")
async def add_activity(ctx, activity_type: str, distance: float, 
                       weight: Optional[float] = None, elevation: Optional[float] = None):
    """
    Dodaje nową aktywność.
    
    Przykłady użycia:
    !dodaj_aktywnosc bieganie_teren 5.2
    !dodaj_aktywnosc bieganie_teren 10 5 (z obciążeniem 5kg)
    !dodaj_aktywnosc bieganie_teren 15 0 200 (z przewyższeniem 200m)
    !dodaj_aktywnosc rower 25 0 150
    """
    activity_type = activity_type.lower()
    
    if activity_type not in ACTIVITY_TYPES:
        available = ", ".join([f"`{k}`" for k in ACTIVITY_TYPES.keys()])
        await ctx.send(
            f"❌ Nieznany typ aktywności: `{activity_type}`\n"
            f"Dostępne typy: {available}\n"
            f"Użyj `!typy_aktywnosci` aby zobaczyć szczegóły."
        )
        return
    
    if distance <= 0:
        await ctx.send("❌ Wartość musi być większa niż 0!")
        return
    
    # Oblicz punkty
    points, error_msg = calculate_points(activity_type, distance, weight, elevation)
    
    if error_msg:
        await ctx.send(f"❌ {error_msg}")
        return
    
    # Zapisz do Google Sheets jeśli dostępny
    username = str(ctx.author)
    saved = False
    
    if sheets_manager:
        try:
            saved = sheets_manager.add_activity(
                username=username,
                activity_type=activity_type,
                distance=distance,
                weight=weight,
                elevation=elevation,
                points=points,
                comment=""
            )
        except Exception as e:
            print(f"Błąd zapisu do Sheets: {e}")
    
    # Przygotuj odpowiedź
    info = ACTIVITY_TYPES[activity_type]
    embed = discord.Embed(
        title=f"{info['emoji']} Aktywność dodana!",
        color=discord.Color.green() if saved else discord.Color.orange()
    )
    
    embed.add_field(name="Użytkownik", value=ctx.author.mention, inline=True)
    embed.add_field(name="Typ", value=info['display_name'], inline=True)
    embed.add_field(name=f"Dystans ({info['unit']})", value=f"{distance}", inline=True)
    
    if weight and weight > 0:
        embed.add_field(name="Obciążenie", value=f"{weight} kg", inline=True)
    if elevation and elevation > 0:
        embed.add_field(name="Przewyższenie", value=f"{elevation} m", inline=True)
    
    embed.add_field(name="Punkty", value=f"🏆 **{points}**", inline=False)
    
    if not saved:
        embed.set_footer(text="⚠️ Dane nie zostały zapisane do Google Sheets")
    
    await ctx.send(embed=embed)


@bot.command(name="moja_historia")
async def my_history(ctx, limit: int = 5):
    """
    Wyświetla ostatnie aktywności użytkownika.
    
    Przykład: !moja_historia 10
    """
    if not sheets_manager:
        await ctx.send("❌ Google Sheets nie jest skonfigurowany. Użyj `!pomoc` aby dowiedzieć się jak go skonfigurować.")
        return
    
    username = str(ctx.author)
    history = sheets_manager.get_user_history(username)
    
    if not history:
        await ctx.send(f"{ctx.author.mention}, nie masz jeszcze żadnych zapisanych aktywności! Użyj `!dodaj_aktywnosc`")
        return
    
    # Ogranicz do ostatnich N wpisów
    history = history[-limit:][::-1]  # Odwróć aby najnowsze były na górze
    
    embed = discord.Embed(
        title=f"📊 Historia aktywności - {ctx.author.display_name}",
        color=discord.Color.blue()
    )
    
    for record in history:
        activity = record.get('Aktywność', 'N/A')
        distance = record.get('Dystans (km)', 0)
        points = record.get('Punkty', 0)
        date = record.get('Data', 'N/A')
        
        emoji = ACTIVITY_TYPES.get(activity.lower(), {}).get('emoji', '📝')
        embed.add_field(
            name=f"{emoji} {activity} - {date}",
            value=f"Wartość: {distance} | Punkty: {points} 🏆",
            inline=False
        )
    
    await ctx.send(embed=embed)


@bot.command(name="moje_punkty")
async def my_points(ctx):
    """Wyświetla sumę punktów użytkownika."""
    if not sheets_manager:
        await ctx.send("❌ Google Sheets nie jest skonfigurowany.")
        return
    
    username = str(ctx.author)
    total_points = sheets_manager.get_user_total_points(username)
    history = sheets_manager.get_user_history(username)
    
    embed = discord.Embed(
        title=f"🏆 Twoje punkty",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="Użytkownik", value=ctx.author.mention, inline=True)
    embed.add_field(name="Całkowite punkty", value=f"**{total_points}** 🏆", inline=True)
    embed.add_field(name="Liczba aktywności", value=f"{len(history)}", inline=True)
    
    await ctx.send(embed=embed)


@bot.command(name="pomoc")
async def help_command(ctx):
    """Wyświetla listę dostępnych komend."""
    embed = discord.Embed(
        title="🌿 Szczypior Bot - Pomoc",
        description="Lista dostępnych komend:",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="📝 Podstawowe",
        value=(
            "`!ping` - Sprawdza latencję bota\n"
            "`!hello` - Powitanie\n"
            "`!pomoc` - Ta wiadomość"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🏃 Aktywności",
        value=(
            "`!typy_aktywnosci` - Lista dostępnych aktywności\n"
            "`!dodaj_aktywnosc <typ> <wartość> [obciążenie] [przewyższenie]` - Dodaj aktywność\n"
            "`!moja_historia [limit]` - Twoje ostatnie aktywności\n"
            "`!moje_punkty` - Sprawdź swoje punkty"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📊 Rankingi i statystyki",
        value=(
            "`!ranking [limit]` - Ranking użytkowników według punktów\n"
            "`!stats` - Statystyki całego serwera\n"
            "`!stats_aktywnosci` - Najpopularniejsze aktywności"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📊 Przykłady",
        value=(
            "`!dodaj_aktywnosc bieganie_teren 5.2`\n"
            "`!dodaj_aktywnosc bieganie_teren 10 5` (z 5kg obciążeniem)\n"
            "`!dodaj_aktywnosc bieganie_teren 15 0 200` (z 200m przewyższeniem)\n"
            "`!dodaj_aktywnosc rower 25` (rower 25km)\n"
            "`!moja_historia 10` (ostatnie 10 aktywności)"
        ),
        inline=False
    )
    
    embed.set_footer(text="Bot stworzony dla miłośników aktywności fizycznej! 🌿")
    await ctx.send(embed=embed)


@bot.command(name="ranking")
async def ranking(ctx, limit: int = 10):
    """
    Wyświetla ranking użytkowników według punktów.
    
    Przykład: !ranking 5
    """
    if not sheets_manager:
        await ctx.send("❌ Google Sheets nie jest skonfigurowany.")
        return
    
    try:
        # Pobierz wszystkie rekordy
        all_records = sheets_manager.worksheet.get_all_records()
        
        if not all_records:
            await ctx.send("📊 Brak danych do wyświetlenia rankingu.")
            return
        
        # Oblicz punkty dla każdego użytkownika
        user_points = {}
        for record in all_records:
            username = record.get('User', '')
            points = record.get('Punkty', 0)
            if username:
                user_points[username] = user_points.get(username, 0) + points
        
        # Sortuj według punktów malejąco
        sorted_users = sorted(user_points.items(), key=lambda x: x[1], reverse=True)
        sorted_users = sorted_users[:limit]
        
        embed = discord.Embed(
            title="🏆 Ranking użytkowników",
            description=f"Top {min(limit, len(sorted_users))} użytkowników według punktów:",
            color=discord.Color.gold()
        )
        
        medals = ["🥇", "🥈", "🥉"]
        for i, (username, points) in enumerate(sorted_users):
            medal = medals[i] if i < 3 else f"{i+1}."
            embed.add_field(
                name=f"{medal} {username}",
                value=f"**{points}** punktów 🏆",
                inline=False
            )
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Błąd podczas generowania rankingu: {e}")


@bot.command(name="stats")
async def server_stats(ctx):
    """Wyświetla ogólne statystyki serwera."""
    if not sheets_manager:
        await ctx.send("❌ Google Sheets nie jest skonfigurowany.")
        return
    
    try:
        all_records = sheets_manager.worksheet.get_all_records()
        
        if not all_records:
            await ctx.send("📊 Brak danych do wyświetlenia statystyk.")
            return
        
        # Oblicz statystyki
        total_activities = len(all_records)
        unique_users = len(set(r.get('User', '') for r in all_records if r.get('User')))
        total_points = sum(r.get('Punkty', 0) for r in all_records)
        total_distance = sum(r.get('Dystans (km)', 0) for r in all_records)
        
        # Najpopularniejsza aktywność
        activities = [r.get('Aktywność', '') for r in all_records if r.get('Aktywność')]
        if activities:
            from collections import Counter
            most_common = Counter(activities).most_common(1)[0]
            popular_activity = most_common[0]
            popular_count = most_common[1]
        else:
            popular_activity = "N/A"
            popular_count = 0
        
        embed = discord.Embed(
            title="📊 Statystyki serwera",
            description="Ogólne statystyki wszystkich użytkowników:",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="👥 Aktywni użytkownicy", value=f"**{unique_users}**", inline=True)
        embed.add_field(name="📝 Liczba aktywności", value=f"**{total_activities}**", inline=True)
        embed.add_field(name="🏆 Suma punktów", value=f"**{total_points}**", inline=True)
        embed.add_field(name="📏 Suma dystansu", value=f"**{total_distance:.1f}** km", inline=True)
        embed.add_field(
            name="⭐ Najpopularniejsza aktywność",
            value=f"**{popular_activity}** ({popular_count}x)",
            inline=True
        )
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Błąd podczas generowania statystyk: {e}")


@bot.command(name="stats_aktywnosci")
async def activity_stats(ctx):
    """Wyświetla statystyki według typu aktywności."""
    if not sheets_manager:
        await ctx.send("❌ Google Sheets nie jest skonfigurowany.")
        return
    
    try:
        all_records = sheets_manager.worksheet.get_all_records()
        
        if not all_records:
            await ctx.send("📊 Brak danych do wyświetlenia statystyk.")
            return
        
        # Grupuj według typu aktywności
        activity_stats = {}
        for record in all_records:
            activity = record.get('Aktywność', '').lower()
            if activity and activity in ACTIVITY_TYPES:
                if activity not in activity_stats:
                    activity_stats[activity] = {
                        'count': 0,
                        'total_distance': 0,
                        'total_points': 0
                    }
                activity_stats[activity]['count'] += 1
                activity_stats[activity]['total_distance'] += record.get('Dystans (km)', 0)
                activity_stats[activity]['total_points'] += record.get('Punkty', 0)
        
        # Sortuj według liczby aktywności
        sorted_activities = sorted(
            activity_stats.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        
        embed = discord.Embed(
            title="📊 Statystyki aktywności",
            description="Podsumowanie wszystkich typów aktywności:",
            color=discord.Color.purple()
        )
        
        for activity, stats in sorted_activities:
            info = ACTIVITY_TYPES.get(activity, {})
            emoji = info.get('emoji', '📝')
            embed.add_field(
                name=f"{emoji} {activity.capitalize()}",
                value=(
                    f"Liczba: **{stats['count']}**\n"
                    f"Suma: **{stats['total_distance']:.1f}** {info.get('unit', 'km')}\n"
                    f"Punkty: **{stats['total_points']}** 🏆"
                ),
                inline=True
            )
        
        if not sorted_activities:
            embed.description = "Brak zapisanych aktywności."
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Błąd podczas generowania statystyk aktywności: {e}")


def main():
    """Główna funkcja uruchamiająca bota."""
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("Brak tokena Discord! Ustaw DISCORD_TOKEN w pliku .env")
    bot.run(token)


if __name__ == "__main__":
    main()
