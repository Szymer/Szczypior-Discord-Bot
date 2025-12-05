"""
Skrypt pokazujący wszystkie informacje o użytkownikach Discord w formacie JSON.
Wyświetla: username, global_name, display_name, nick (alias na serwerze), role, itp.
"""
import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Konfiguracja bota
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'✅ Bot zalogowany jako {bot.user}')
    print(f'📊 Zbieranie informacji o użytkownikach...\n')
    
    all_users_info = []
    
    # Iteruj po wszystkich serwerach (guildach)
    for guild in bot.guilds:
        print(f"\n🏰 Serwer: {guild.name} (ID: {guild.id})")
        print(f"👥 Liczba członków: {guild.member_count}\n")
        
        guild_info = {
            "guild_name": guild.name,
            "guild_id": str(guild.id),
            "member_count": guild.member_count,
            "members": []
        }
        
        # Iteruj po wszystkich członkach serwera
        for member in guild.members:
            # Pomiń botów dla czytelności
            if member.bot:
                continue
            
            # Zbierz wszystkie dostępne informacje
            member_info = {
                # Podstawowe informacje
                "user_id": str(member.id),
                "username": member.name,  # Nazwa użytkownika (username)
                "discriminator": member.discriminator,  # #0000 (stare, teraz zazwyczaj "0")
                "global_name": member.global_name,  # Wyświetlana nazwa globalna
                "display_name": member.display_name,  # Nazwa wyświetlana na serwerze
                
                # ALIASY NA SERWERZE
                "nick": member.nick,  # Nickname/alias nadany na tym serwerze
                "server_display_name": member.display_name,  # To co widać na serwerze
                
                # Dodatkowe informacje
                "is_bot": member.bot,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                "created_at": member.created_at.isoformat(),
                
                # Role na serwerze
                "roles": [
                    {
                        "name": role.name,
                        "id": str(role.id),
                        "color": str(role.color)
                    } 
                    for role in member.roles if role.name != "@everyone"
                ],
                
                # Awatar
                "avatar_url": str(member.avatar.url) if member.avatar else None,
                "guild_avatar_url": str(member.guild_avatar.url) if member.guild_avatar else None,
            }
            
            guild_info["members"].append(member_info)
            
            # Wyświetl informacje w konsoli
            print(f"👤 {member_info['display_name']}")
            print(f"   Username: {member_info['username']}")
            print(f"   Global Name: {member_info['global_name']}")
            print(f"   Nick (alias): {member_info['nick']}")
            print(f"   Display Name: {member_info['display_name']}")
            if member_info['roles']:
                print(f"   Role: {', '.join([r['name'] for r in member_info['roles']])}")
            print()
        
        all_users_info.append(guild_info)
    
    # Zapisz do pliku JSON
    output_file = "discord_users_info.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_users_info, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Dane zapisane do pliku: {output_file}")
    print(f"\n📋 STRUKTURA DANYCH:")
    print("""
    - username: Nazwa użytkownika Discord (np. 'jan_kowalski')
    - global_name: Globalna nazwa wyświetlana (np. 'Jan Kowalski')
    - display_name: Nazwa wyświetlana NA TYM SERWERZE (uwzględnia nick)
    - nick: ALIAS/NICKNAME nadany przez admina na serwerze (może być null)
    - server_display_name: To samo co display_name
    
    WAŻNE:
    - Jeśli użytkownik ma nick (alias), to display_name = nick
    - Jeśli nie ma nicku, to display_name = global_name lub username
    - Nick to pole, które możesz ustawić prawym klikiem -> Zmień nick
    """)
    
    # Zatrzymaj bota
    await bot.close()

# Uruchom bota
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ Brak DISCORD_TOKEN w pliku .env")
    else:
        bot.run(token)
