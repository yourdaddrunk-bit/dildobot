import aiosqlite
import asyncio
from datetime import datetime, timedelta

DB_PATH = "players.db"

async def init_db():
    """Создание таблиц в базе данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица игроков
        await db.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                dildo_points INTEGER DEFAULT 0,
                join_date TEXT,
                voice_time INTEGER DEFAULT 0,
                message_count INTEGER DEFAULT 0,
                last_active TEXT,
                spouse_id INTEGER DEFAULT NULL,
                duel_wins INTEGER DEFAULT 0,
                duel_loses INTEGER DEFAULT 0,
                casino_spins INTEGER DEFAULT 0,
                coin_wins INTEGER DEFAULT 0,
                coin_loses INTEGER DEFAULT 0
            )
        ''')
        
        # Таблица достижений
        await db.execute('''
            CREATE TABLE IF NOT EXISTS player_achievements (
                user_id INTEGER,
                achievement_id TEXT,
                unlocked_date TEXT,
                PRIMARY KEY (user_id, achievement_id)
            )
        ''')
        
        await db.commit()

async def get_player(user_id: int):
    """Получить данные игрока"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM players WHERE user_id = ?", (user_id,)
        ) as cursor:
            return await cursor.fetchone()

async def create_player(user_id: int, username: str):
    """Создать нового игрока"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO players (user_id, username, join_date, last_active) VALUES (?, ?, ?, ?)",
            (user_id, username, datetime.now().isoformat(), datetime.now().isoformat())
        )
        await db.commit()

async def add_points(user_id: int, points: int):
    """Добавить очки игроку"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE players SET dildo_points = dildo_points + ? WHERE user_id = ?",
            (points, user_id)
        )
        await db.commit()

async def add_achievement(user_id: int, achievement_id: str):
    """Добавить достижение игроку"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO player_achievements (user_id, achievement_id, unlocked_date) VALUES (?, ?, ?)",
            (user_id, achievement_id, datetime.now().isoformat())
        )
        await db.commit()

async def get_achievements(user_id: int):
    """Получить все достижения игрока"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT achievement_id FROM player_achievements WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            return [row[0] for row in await cursor.fetchall()]

async def update_voice_time(user_id: int, seconds: int):
    """Обновить время в голосовом канале"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE players SET voice_time = voice_time + ? WHERE user_id = ?",
            (seconds, user_id)
        )
        await db.commit()

async def increment_messages(user_id: int):
    """Увеличить счетчик сообщений"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE players SET message_count = message_count + 1, last_active = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user_id)
        )
        await db.commit()

async def set_spouse(user_id: int, spouse_id: int):
    """Установить супруга"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE players SET spouse_id = ? WHERE user_id = ?",
            (spouse_id, user_id)
        )
        await db.commit()

async def get_spouse(user_id: int):
    """Получить ID супруга"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT spouse_id FROM players WHERE user_id = ?", (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

async def update_duel_stats(user_id: int, win: bool):
    """Обновить статистику дуэлей"""
    async with aiosqlite.connect(DB_PATH) as db:
        if win:
            await db.execute(
                "UPDATE players SET duel_wins = duel_wins + 1 WHERE user_id = ?",
                (user_id,)
            )
        else:
            await db.execute(
                "UPDATE players SET duel_loses = duel_loses + 1 WHERE user_id = ?",
                (user_id,)
            )
        await db.commit()

async def update_casino_spins(user_id: int):
    """Обновить количество прокрутов рулетки"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE players SET casino_spins = casino_spins + 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()

async def update_coin_stats(user_id: int, win: bool):
    """Обновить статистику монетки"""
    async with aiosqlite.connect(DB_PATH) as db:
        if win:
            await db.execute(
                "UPDATE players SET coin_wins = coin_wins + 1 WHERE user_id = ?",
                (user_id,)
            )
        else:
            await db.execute(
                "UPDATE players SET coin_loses = coin_loses + 1 WHERE user_id = ?",
                (user_id,)
            )
        await db.commit()

async def get_duel_stats(user_id: int):
    """Получить статистику дуэлей"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT duel_wins, duel_loses FROM players WHERE user_id = ?", (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result if result else (0, 0)

async def get_casino_spins(user_id: int):
    """Получить количество прокрутов рулетки"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT casino_spins FROM players WHERE user_id = ?", (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

async def get_coin_stats(user_id: int):
    """Получить статистику монетки"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT coin_wins, coin_loses FROM players WHERE user_id = ?", (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result if result else (0, 0)