import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import logging
import random
import os  # <--- ЭТО НУЖНО ДЛЯ ТОКЕНА

from database import *
import achievements as ach

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создаем бота с нужными интентами
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Словари для отслеживания
voice_tracker = {}
duels = {}
voice_players = {}

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} запущен!")
    await init_db()
    
    try:
        synced = await bot.tree.sync()
        print(f"✅ Синхронизировано {len(synced)} команд")
    except Exception as e:
        print(f"❌ Ошибка синхронизации: {e}")
    
    track_voice_time.start()
    check_voice_achievements.start()
    check_voice_players.start()
    hourly_report.start()
    check_night_owl.start()
    check_hero_day.start()

# ============ ФОНОВЫЕ ЗАДАЧИ ============

@tasks.loop(seconds=30)
async def track_voice_time():
    """Отслеживает время в голосовых каналах"""
    for guild in bot.guilds:
        for voice_channel in guild.voice_channels:
            members_in_channel = [m for m in voice_channel.members if not m.bot]
            player_count = len(members_in_channel)
            
            for member in members_in_channel:
                user_id = member.id
                if user_id not in voice_tracker:
                    voice_tracker[user_id] = datetime.now()
                
                await add_points(user_id, 0.5)
                await update_voice_time(user_id, 30)
                
                if player_count >= 2:
                    await add_points(user_id, 0.3)
                    if user_id not in voice_players:
                        voice_players[user_id] = 0
                    voice_players[user_id] += 30

@tasks.loop(minutes=5)
async def check_voice_achievements():
    """Проверяет достижения за голосовой канал"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM players") as cursor:
            players = await cursor.fetchall()
            
            for (user_id,) in players:
                player = await get_player(user_id)
                if player:
                    current_ach = await get_achievements(user_id)
                    new_ach = ach.check_achievements(user_id, player, current_ach)
                    
                    for ach_id in new_ach:
                        await add_achievement(user_id, ach_id)
                        bonus_points = ach.ACHIEVEMENTS[ach_id]["points"]
                        await add_points(user_id, bonus_points)
                        
                        user = await bot.fetch_user(user_id)
                        if user:
                            try:
                                if ach_id == "voice_10h":
                                    for guild in bot.guilds:
                                        for channel in guild.text_channels:
                                            if channel.permissions_for(guild.me).send_messages:
                                                embed_all = discord.Embed(
                                                    title="🚨 ВНИМАНИЕ! ВНИМАНИЕ! 🚨",
                                                    description=f"У нас появился **🍺 ДИЛДОБИЛДЕР** — {user.mention}!\n\n"
                                                                f"**НЕМЕДЛЕННО ПОДНЯТЬ ЩИТЫ!** 🛡️\n"
                                                                f"И **БАХНИТЕ ПИВКА** за его величие! 🍻",
                                                    color=discord.Color.gold()
                                                )
                                                await channel.send(embed=embed_all)
                                                break
                                        break
                                
                                embed = discord.Embed(
                                    title=f"🎉 ПОЗДРАВЛЯЮ!",
                                    description=f"Ты получил новое звание!\n\n**{ach.ACHIEVEMENTS[ach_id]['icon']} {ach.ACHIEVEMENTS[ach_id]['name']}**\n\n_{ach.ACHIEVEMENTS[ach_id]['description']}_",
                                    color=discord.Color.gold()
                                )
                                embed.add_field(
                                    name="Награда",
                                    value=f"+{bonus_points} Дилдотокенов 🪙",
                                    inline=False
                                )
                                embed.set_footer(text="Продолжай в том же духе!")
                                await user.send(embed=embed)
                            except:
                                pass

@tasks.loop(seconds=60)
async def check_voice_players():
    """Проверяет количество игроков в голосовых каналах"""
    for guild in bot.guilds:
        for voice_channel in guild.voice_channels:
            members = [m for m in voice_channel.members if not m.bot]
            if len(members) >= 2:
                for member in members:
                    await add_points(member.id, 0.5)

@tasks.loop(hours=1)
async def hourly_report():
    """Ежечасный отчет"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, username, dildo_points FROM players ORDER BY dildo_points DESC LIMIT 5"
        ) as cursor:
            top_players = await cursor.fetchall()
    
    if not top_players:
        return
    
    report = "📊 **ЕЖЕЧАСОВОЙ ОТЧЕТ ДИЛДОБОТА**\n\n"
    report += "🏆 **Топ игроков по Дилдотокенам:**\n"
    
    for i, (user_id, username, points) in enumerate(top_players, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        report += f"{medal} **{username}** — 🪙 {points} Дилдотокенов\n"
    
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(report)
                break
        break

@tasks.loop(minutes=10)
async def check_night_owl():
    """Проверка Ночного дозора (после 2:00 ночи)"""
    now = datetime.now()
    if now.hour >= 2 and now.hour <= 5:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT user_id FROM players") as cursor:
                players = await cursor.fetchall()
                for (user_id,) in players:
                    current_ach = await get_achievements(user_id)
                    if "night_owl" not in current_ach:
                        for guild in bot.guilds:
                            for voice_channel in guild.voice_channels:
                                for member in voice_channel.members:
                                    if member.id == user_id and not member.bot:
                                        await add_achievement(user_id, "night_owl")
                                        await add_points(user_id, ach.ACHIEVEMENTS["night_owl"]["points"])
                                        try:
                                            user = await bot.fetch_user(user_id)
                                            embed = discord.Embed(
                                                title="🎉 ПОЗДРАВЛЯЮ!",
                                                description=f"Ты получил новое звание!\n\n**🌙 НОЧНОЙ ДОЗОР**\n\n_Сидеть в голосовом после 2:00 ночи!_",
                                                color=discord.Color.gold()
                                            )
                                            embed.add_field(name="Награда", value="+40 Дилдотокенов 🪙", inline=False)
                                            await user.send(embed=embed)
                                        except:
                                            pass

@tasks.loop(minutes=1)
async def check_hero_day():
    """Проверка Героя дня (первый, кто написал сегодня)"""
    now = datetime.now().date()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, last_active FROM players ORDER BY last_active ASC LIMIT 1") as cursor:
            result = await cursor.fetchone()
            if result:
                user_id, last_active = result
                if last_active:
                    last_date = datetime.fromisoformat(last_active).date()
                    if last_date == now:
                        current_ach = await get_achievements(user_id)
                        if "hero_day" not in current_ach:
                            await add_achievement(user_id, "hero_day")
                            await add_points(user_id, ach.ACHIEVEMENTS["hero_day"]["points"])
                            try:
                                user = await bot.fetch_user(user_id)
                                embed = discord.Embed(
                                    title="🎉 ПОЗДРАВЛЯЮ!",
                                    description=f"Ты получил новое звание!\n\n**🦸 ГЕРОЙ ДНЯ**\n\n_Первый, кто написал сегодня!_",
                                    color=discord.Color.gold()
                                )
                                embed.add_field(name="Награда", value="+30 Дилдотокенов 🪙", inline=False)
                                await user.send(embed=embed)
                            except:
                                pass

# ============ СОБЫТИЯ ============

@bot.event
async def on_member_join(member):
    if member.bot:
        return
    
    await create_player(member.id, member.name)
    await add_achievement(member.id, "welcome")
    await add_points(member.id, ach.ACHIEVEMENTS["welcome"]["points"])
    
    try:
        embed_dm = discord.Embed(
            title="🎉 ПОЗДРАВЛЯЮ!",
            description=f"Ты получил новое звание!\n\n**🤡 ДИЛДОЛОХ**\n\n_Присоединиться к серверу — первый шаг к величию!_",
            color=discord.Color.gold()
        )
        embed_dm.add_field(name="Награда", value="+25 Дилдотокенов 🪙", inline=False)
        embed_dm.set_footer(text="Теперь ты официально ДИЛДОЛОХ!")
        await member.send(embed=embed_dm)
    except:
        pass

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    player = await get_player(message.author.id)
    if not player:
        await create_player(message.author.id, message.author.name)
    
    await increment_messages(message.author.id)
    await add_points(message.author.id, 1)
    
    player = await get_player(message.author.id)
    current_ach = await get_achievements(message.author.id)
    new_ach = ach.check_achievements(message.author.id, player, current_ach)
    
    for ach_id in new_ach:
        await add_achievement(message.author.id, ach_id)
        bonus_points = ach.ACHIEVEMENTS[ach_id]["points"]
        await add_points(message.author.id, bonus_points)
        
        if ach_id == "voice_10h":
            for guild in bot.guilds:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        embed_all = discord.Embed(
                            title="🚨 ВНИМАНИЕ! ВНИМАНИЕ! 🚨",
                            description=f"У нас появился **🍺 ДИЛДОБИЛДЕР** — {message.author.mention}!\n\n"
                                        f"**НЕМЕДЛЕННО ПОДНЯТЬ ЩИТЫ!** 🛡️\n"
                                        f"И **БАХНИТЕ ПИВКА** за его величие! 🍻",
                            color=discord.Color.gold()
                        )
                        await channel.send(embed=embed_all)
                        break
                break
        
        embed = discord.Embed(
            title="🎉 ПОЗДРАВЛЯЮ!",
            description=f"{message.author.mention} получил новое звание!\n\n**{ach.ACHIEVEMENTS[ach_id]['icon']} {ach.ACHIEVEMENTS[ach_id]['name']}**",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="Награда",
            value=f"+{bonus_points} Дилдотокенов 🪙",
            inline=False
        )
        await message.channel.send(embed=embed)
        
        try:
            embed_dm = discord.Embed(
                title="🎉 ПОЗДРАВЛЯЮ!",
                description=f"Ты получил новое звание!\n\n**{ach.ACHIEVEMENTS[ach_id]['icon']} {ach.ACHIEVEMENTS[ach_id]['name']}**\n\n_{ach.ACHIEVEMENTS[ach_id]['description']}_",
                color=discord.Color.gold()
            )
            embed_dm.add_field(
                name="Награда",
                value=f"+{bonus_points} Дилдотокенов 🪙",
                inline=False
            )
            embed_dm.set_footer(text="Ты на пути к величию!")
            await message.author.send(embed=embed_dm)
        except:
            pass
    
    await bot.process_commands(message)

# ============ СЛЭШ-КОМАНДЫ ============

@bot.tree.command(name="profile", description="Показать профиль игрока")
@app_commands.describe(member="Пользователь (опционально)")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    if member is None:
        member = interaction.user
    
    player = await get_player(member.id)
    if not player:
        await interaction.response.send_message(f"❌ У {member.mention} нет профиля!", ephemeral=True)
        return
    
    user_id, username, points, join_date, voice_time, msg_count, last_active, spouse_id, duel_wins, duel_loses, casino_spins, coin_wins, coin_loses = player
    
    all_achievements = await get_achievements(member.id)
    
    # 1. ОСНОВНЫЕ ЗВАНИЯ
    main_ranks = ["welcome", "chat_50", "voice_1h", "voice_2h", "voice_4h", "voice_6h", "voice_7h", "voice_10h"]
    main_list = [ach.ACHIEVEMENTS[a]["name"] for a in all_achievements if a in main_ranks]
    
    # 2. ТИТУЛЫ (дополнительные)
    title_ids = ["duel_lose", "duel_win", "duel_10wins", "duel_10loses", "night_owl", "hero_day"]
    titles_list = [ach.ACHIEVEMENTS[a]["name"] for a in all_achievements if a in title_ids]
    
    # Текущее основное звание (самое последнее)
    if main_list:
        current_rank = main_list[-1]
    else:
        current_rank = "Нет звания"
    
    # Титулы (список)
    titles_str = "\n".join(titles_list) if titles_list else "Нет титулов"
    
    voice_hours = voice_time // 3600
    voice_minutes = (voice_time % 3600) // 60
    
    # --- СЕМЕЙНОЕ ПОЛОЖЕНИЕ (несколько супругов) ---
    spouse_status = "Холост/Не замужем"
    spouse_list = []
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, spouse_id FROM players WHERE spouse_id IS NOT NULL") as cursor:
            all_marriages = await cursor.fetchall()
            for uid, sid in all_marriages:
                if sid == user_id and uid != user_id:
                    spouse_list.append(uid)
    
    if spouse_list:
        spouse_mentions = []
        for sid in spouse_list:
            try:
                s_user = await bot.fetch_user(sid)
                spouse_mentions.append(s_user.mention)
            except:
                spouse_mentions.append(f"<@{sid}>")
        spouse_status = f"В браке с {', '.join(spouse_mentions)}"
    
    # --- СТРОИМ ПРОФИЛЬ ---
    embed = discord.Embed(
        title=f"📊 Профиль {member.display_name}",
        color=member.color if member.color != discord.Color.default() else discord.Color.blue()
    )
    
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="🪙 Дилдотокены", value=str(points), inline=True)
    embed.add_field(name="💬 Сообщений", value=str(msg_count), inline=True)
    embed.add_field(name="🎧 В голосовых", value=f"{voice_hours}ч {voice_minutes}м", inline=True)
    
    embed.add_field(name="🏅 Звание", value=current_rank, inline=False)
    embed.add_field(name="👑 Титулы", value=titles_str, inline=False)
    embed.add_field(name="💍 Семейное положение", value=spouse_status, inline=False)
    
    embed.add_field(name="⚔️ Побед в дуэлях", value=str(duel_wins), inline=True)
    embed.add_field(name="⚔️ Поражений в дуэлях", value=str(duel_loses), inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="top", description="Топ игроков по Дилдотокенам")
async def top(interaction: discord.Interaction):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, username, dildo_points FROM players ORDER BY dildo_points DESC LIMIT 10"
        ) as cursor:
            top_players = await cursor.fetchall()
    
    if not top_players:
        await interaction.response.send_message("❌ Нет игроков в базе!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🏆 Топ игроков",
        color=discord.Color.gold()
    )
    
    for i, (user_id, username, points) in enumerate(top_players, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        embed.add_field(
            name=f"{medal} {username}",
            value=f"🪙 {points} Дилдотокенов",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="звания", description="Показать все звания")
async def show_achievements(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📜 Список званий",
        description="Получай звания за активность на сервере! Время суммируется!",
        color=discord.Color.purple()
    )
    
    for ach_id, ach_data in ach.ACHIEVEMENTS.items():
        embed.add_field(
            name=f"{ach_data['icon']} {ach_data['name']}",
            value=f"{ach_data['description']}\n🪙 +{ach_data['points']} Дилдотокенов",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

# ============ ДУЭЛИ ============

@bot.tree.command(name="вызов", description="Бросить вызов участнику")
@app_commands.describe(opponent="Кого вызываешь на дуэль")
async def challenge(interaction: discord.Interaction, opponent: discord.Member):
    challenger = interaction.user
    
    if opponent.id == challenger.id:
        await interaction.response.send_message("🤡 Сам с собой мериться будешь? Позови кого-то!", ephemeral=True)
        return
    
    if opponent.bot:
        await interaction.response.send_message("🤖 Бот не будет с тобой мериться, у него нет члена!", ephemeral=True)
        return
    
    if challenger.id in duels:
        await interaction.response.send_message("⏳ У тебя уже есть активный вызов! Дождись ответа.", ephemeral=True)
        return
    
    duels[challenger.id] = {
        "opponent": opponent.id,
        "timestamp": datetime.now()
    }
    
    embed = discord.Embed(
        title="⚔️ ВЫЗОВ НА ДУЭЛЬ!",
        description=f"{challenger.mention} вызывает {opponent.mention} на **битву членами**! 🍆",
        color=discord.Color.orange()
    )
    embed.add_field(
        name="Как принять?",
        value=f"{opponent.mention}, напиши `/принять {challenger.mention}`",
        inline=False
    )
    embed.set_footer(text="У тебя 60 секунд, чтобы ответить!")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="принять", description="Принять вызов на дуэль")
@app_commands.describe(challenger="Кто тебя вызвал")
async def accept(interaction: discord.Interaction, challenger: discord.Member):
    opponent = interaction.user
    
    if challenger.id not in duels:
        await interaction.response.send_message("❌ Нет активного вызова от этого участника!", ephemeral=True)
        return
    
    duel_data = duels[challenger.id]
    
    if duel_data["opponent"] != opponent.id:
        await interaction.response.send_message("❌ Этот вызов не для тебя!", ephemeral=True)
        return
    
    time_diff = (datetime.now() - duel_data["timestamp"]).total_seconds()
    if time_diff > 60:
        del duels[challenger.id]
        await interaction.response.send_message("⏰ Время вызова истекло!", ephemeral=True)
        return
    
    del duels[challenger.id]
    
    if not await get_player(challenger.id) or not await get_player(opponent.id):
        await interaction.response.send_message("❌ У одного из участников нет профиля!", ephemeral=True)
        return
    
    challenger_size = random.randint(1, 99)
    opponent_size = random.randint(1, 99)
    
    size_messages = ["🍆", "🥒", "🌽", "🌭", "🍌", "🌶️", "🧅", "🥕"]
    
    embed = discord.Embed(
        title="🍆 БИТВА ЧЛЕНОВ!",
        description=f"{challenger.mention} VS {opponent.mention}",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name=f"{challenger.display_name}",
        value=f"{random.choice(size_messages)} **{challenger_size} см**",
        inline=True
    )
    embed.add_field(
        name=f"{opponent.display_name}",
        value=f"{random.choice(size_messages)} **{opponent_size} см**",
        inline=True
    )
    
    if challenger_size > opponent_size:
        winner = challenger
        loser = opponent
        win_message = f"🏆 **{challenger.mention} ПОБЕДИЛ!**\nТвоя волына больше! 🍆💪"
        await add_points(winner.id, 5)
        await add_points(loser.id, -5)
        await update_duel_stats(winner.id, True)
        await update_duel_stats(loser.id, False)
        
        wins, loses = await get_duel_stats(winner.id)
        current_ach = await get_achievements(winner.id)
        
        if wins >= 10 and "duel_10wins" not in current_ach:
            await add_achievement(winner.id, "duel_10wins")
            await add_points(winner.id, ach.ACHIEVEMENTS["duel_10wins"]["points"])
        
        if "duel_win" not in current_ach:
            await add_achievement(winner.id, "duel_win")
            await add_points(winner.id, ach.ACHIEVEMENTS["duel_win"]["points"])
        
        loses_count, _ = await get_duel_stats(loser.id)
        current_ach_loser = await get_achievements(loser.id)
        
        if loses_count >= 10 and "duel_10loses" not in current_ach_loser:
            await add_achievement(loser.id, "duel_10loses")
            await add_points(loser.id, ach.ACHIEVEMENTS["duel_10loses"]["points"])
        
        if "duel_lose" not in current_ach_loser:
            await add_achievement(loser.id, "duel_lose")
            await add_points(loser.id, ach.ACHIEVEMENTS["duel_lose"]["points"])
            
    elif opponent_size > challenger_size:
        winner = opponent
        loser = challenger
        win_message = f"🏆 **{opponent.mention} ПОБЕДИЛ!**\nТвоя волына больше! 🍆💪"
        await add_points(winner.id, 5)
        await add_points(loser.id, -5)
        await update_duel_stats(winner.id, True)
        await update_duel_stats(loser.id, False)
        
        wins, loses = await get_duel_stats(winner.id)
        current_ach = await get_achievements(winner.id)
        
        if wins >= 10 and "duel_10wins" not in current_ach:
            await add_achievement(winner.id, "duel_10wins")
            await add_points(winner.id, ach.ACHIEVEMENTS["duel_10wins"]["points"])
        
        if "duel_win" not in current_ach:
            await add_achievement(winner.id, "duel_win")
            await add_points(winner.id, ach.ACHIEVEMENTS["duel_win"]["points"])
        
        loses_count, _ = await get_duel_stats(loser.id)
        current_ach_loser = await get_achievements(loser.id)
        
        if loses_count >= 10 and "duel_10loses" not in current_ach_loser:
            await add_achievement(loser.id, "duel_10loses")
            await add_points(loser.id, ach.ACHIEVEMENTS["duel_10loses"]["points"])
        
        if "duel_lose" not in current_ach_loser:
            await add_achievement(loser.id, "duel_lose")
            await add_points(loser.id, ach.ACHIEVEMENTS["duel_lose"]["points"])
    else:
        win_message = f"🤝 **НИЧЬЯ!**\nВаши волыны равны! {random.choice(size_messages)}"
        await add_points(challenger.id, 2)
        await add_points(opponent.id, 2)
    
    embed.add_field(
        name="💰 ИТОГ:",
        value=win_message,
        inline=False
    )
    
    challenger_points = await get_points(challenger.id)
    opponent_points = await get_points(opponent.id)
    
    embed.add_field(
        name="📊 Баланс после битвы:",
        value=f"{challenger.mention}: 🪙 {challenger_points}\n{opponent.mention}: 🪙 {opponent_points}",
        inline=False
    )
    
    embed.set_footer(text="Дилдобот — судья этой битвы!")
    
    await interaction.response.send_message(embed=embed)

# ============ НОВЫЕ КОМАНДЫ ============

@bot.tree.command(name="дать_леща", description="Дать леща участнику")
@app_commands.describe(member="Кому даём леща")
async def give_leash(interaction: discord.Interaction, member: discord.Member):
    user = interaction.user
    
    if member.id == user.id:
        await interaction.response.send_message("🤡 Сам себе леща дать хочешь? Ты мазохист?", ephemeral=True)
        return
    
    if member.bot:
        await interaction.response.send_message("🤖 Боту леща? Он железный, не почувствует!", ephemeral=True)
        return
    
    player = await get_player(user.id)
    if not player:
        await interaction.response.send_message("❌ У тебя нет профиля! Напиши что-нибудь в чат.", ephemeral=True)
        return
    
    cost = 15
    points = await get_points(user.id)
    
    if points < cost:
        await interaction.response.send_message(f"❌ У тебя всего {points} Дилдотокенов! Нужно {cost} для леща 💢", ephemeral=True)
        return
    
    await add_points(user.id, -cost)
    await add_points(member.id, -5)
    
    reactions = [
        f"💢 **ЛЕЩ!** {user.mention} дал леща {member.mention}! Тот аж подпрыгнул! 🐟",
        f"😱 {user.mention} врезал {member.mention} так, что искры из глаз посыпались!",
        f"🤕 {member.mention} получил леща от {user.mention} и теперь задумался о жизни...",
        f"💥 **БАМ!** {user.mention} отвесил {member.mention} звонкого леща!",
    ]
    
    embed = discord.Embed(
        title="💢 ЛЕЩ!",
        description=random.choice(reactions),
        color=discord.Color.red()
    )
    embed.add_field(
        name="💰 Финансовый итог:",
        value=f"{user.mention} потратил **{cost}** Дилдотокенов\n{member.mention} потерял **5** Дилдотокенов 💸",
        inline=False
    )
    embed.set_footer(text="Дилдобот не одобряет насилие, но это было смешно")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="потрогать_член", description="Потрогать член участника")
@app_commands.describe(member="Чей член трогаем")
async def touch_dick(interaction: discord.Interaction, member: discord.Member):
    user = interaction.user
    
    if member.id == user.id:
        await interaction.response.send_message("🤡 Сам себя трогаешь? Это в другой комнате делают!", ephemeral=True)
        return
    
    if member.bot:
        await interaction.response.send_message("🤖 У бота нет члена! Только провода!", ephemeral=True)
        return
    
    player = await get_player(user.id)
    if not player:
        await interaction.response.send_message("❌ У тебя нет профиля! Напиши что-нибудь в чат.", ephemeral=True)
        return
    
    cost = 10
    points = await get_points(user.id)
    
    if points < cost:
        await interaction.response.send_message(f"❌ У тебя всего {points} Дилдотокенов! Нужно {cost} чтобы потрогать член 🍆", ephemeral=True)
        return
    
    await add_points(user.id, -cost)
    
    reactions = [
        f"🍆 {user.mention} потрогал член {member.mention}! Все в шоке! 😱",
        f"🤭 {user.mention} решил пощупать {member.mention}! Смело!",
        f"😳 {user.mention} трогает член {member.mention}! Камера смотрит!",
        f"🍆💀 {user.mention} залез рукой в штаны {member.mention}! Фу!",
    ]
    
    embed = discord.Embed(
        title="🍆 ПОТРОГАЛ ЧЛЕН!",
        description=random.choice(reactions),
        color=discord.Color.purple()
    )
    embed.add_field(
        name="💰 Финансовый итог:",
        value=f"{user.mention} потратил **{cost}** Дилдотокенов",
        inline=False
    )
    embed.set_footer(text="Дилдобот — свидетель этой истории")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="свадьба", description="Сыграть свадьбу с участником")
@app_commands.describe(partner="С кем играем свадьбу")
async def wedding(interaction: discord.Interaction, partner: discord.Member):
    user = interaction.user
    
    if partner.id == user.id:
        await interaction.response.send_message("🤡 Жениться на себе? Ты что, нарцисс?", ephemeral=True)
        return
    
    if partner.bot:
        await interaction.response.send_message("🤖 Бот не может жениться! Он бездушный!", ephemeral=True)
        return
    
    if not await get_player(user.id) or not await get_player(partner.id):
        await interaction.response.send_message("❌ У одного из участников нет профиля!", ephemeral=True)
        return
    
    cost = 100
    user_points = await get_points(user.id)
    partner_points = await get_points(partner.id)
    
    if user_points < cost or partner_points < cost:
        await interaction.response.send_message(f"❌ Нужно по {cost} Дилдотокенов у каждого! У тебя {user_points}, у партнёра {partner_points}", ephemeral=True)
        return
    
    await add_points(user.id, -cost)
    await add_points(partner.id, -cost)
    
    await set_spouse(user.id, partner.id)
    await set_spouse(partner.id, user.id)
    
    embed = discord.Embed(
        title="💍 СВАДЬБА!",
        description=f"🎉 {user.mention} и {partner.mention} сыграли свадьбу! Теперь они муж и жена! 💍",
        color=discord.Color.pink()
    )
    embed.add_field(
        name="💰 Стоимость:",
        value=f"Каждый потратил по {cost} Дилдотокенов 🪙",
        inline=False
    )
    embed.set_footer(text="Дилдобот — главный жрец этой свадьбы!")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="пить", description="Угостить участника пивом за Дилдотокены")
@app_commands.describe(member="Кого угощаем")
async def drink(interaction: discord.Interaction, member: discord.Member):
    user = interaction.user
    
    if member.id == user.id:
        await interaction.response.send_message("🤡 Нельзя угощать самого себя! Ты что, алкаш?", ephemeral=True)
        return
    
    player = await get_player(user.id)
    if not player:
        await interaction.response.send_message("❌ У тебя нет профиля!", ephemeral=True)
        return
    
    points = await get_points(user.id)
    COST = 10
    
    if points < COST:
        await interaction.response.send_message(f"❌ У тебя всего {points} Дилдотокенов! Нужно {COST} 🍺", ephemeral=True)
        return
    
    await add_points(user.id, -COST)
    await add_points(member.id, 5)
    
    embed = discord.Embed(
        title="🍺 Угощение!",
        description=f"{user.mention} угостил {member.mention} пивом за **{COST}** Дилдотокенов! 🍻",
        color=discord.Color.green()
    )
    embed.add_field(
        name=f"У {member.display_name} теперь +5 Дилдотокенов!",
        value=f"У {user.display_name} осталось {await get_points(user.id)} Дилдотокенов",
        inline=False
    )
    embed.set_footer(text="Круто быть богатым!")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="бахнуть", description="Бахнуть участника членом по лбу за Дилдотокены")
@app_commands.describe(member="Кого бахаем")
async def bang(interaction: discord.Interaction, member: discord.Member):
    user = interaction.user
    
    if member.id == user.id:
        await interaction.response.send_message("🤡 Сам себя не бахнешь! Ты че, резиновый?", ephemeral=True)
        return
    
    player = await get_player(user.id)
    if not player:
        await interaction.response.send_message("❌ У тебя нет профиля!", ephemeral=True)
        return
    
    points = await get_points(user.id)
    COST = 25
    
    if points < COST:
        await interaction.response.send_message(f"❌ У тебя всего {points} Дилдотокенов! Нужно {COST} 💥", ephemeral=True)
        return
    
    await add_points(user.id, -COST)
    await add_points(member.id, -5)
    
    reactions = [
        f"💥 **БАХ!** {user.mention} огрел {member.mention} членом по лбу! Раздался звон! 🔔",
        f"💢 **БДЫЩ!** {member.mention} получил люлей от {user.mention}! Теперь будет знать!",
        f"😵 **КРЯК!** {user.mention} вмазал {member.mention} так, что искры посыпались!",
        f"🤕 {user.mention} решил проверить череп {member.mention} на прочность. Череп выдержал!",
        f"🔥 **АРГХ!** {member.mention} получил по лбу и задумался о жизни..."
    ]
    
    embed = discord.Embed(
        title="💥 БАХ!",
        description=random.choice(reactions),
        color=discord.Color.red()
    )
    embed.add_field(
        name="💰 Финансовый итог:",
        value=f"{user.mention} потратил **{COST}** Дилдотокенов\n{member.mention} потерял **5** Дилдотокенов 💸",
        inline=False
    )
    embed.set_footer(text="Дилдобот не несет ответственности за травмы")
    
    await interaction.response.send_message(embed=embed)

# ============ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============

async def get_points(user_id: int):
    player = await get_player(user_id)
    if player:
        return player[2]
    return 0

async def get_user_info(user_id: int):
    player = await get_player(user_id)
    if player:
        return player
    return None

# ============ ЗАПУСК ============
if __name__ == "__main__":
    bot.run(os.environ['BOT_TOKEN'])