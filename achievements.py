
# Список всех достижений
ACHIEVEMENTS = {
    "welcome": {
        "id": "welcome",
        "name": "🤡 ДИЛДОЛОХ",
        "description": "Присоединиться к серверу — первый шаг к величию!",
        "points": 25,
        "icon": "🤡"
    },
    "chat_50": {
        "id": "chat_50",
        "name": "🐴 ДИЛДОКОНЬ",
        "description": "Написать 2 сообщения — ты уже в теме!",
        "points": 35,
        "icon": "🐴"
    },
    "voice_1h": {
        "id": "voice_1h",
        "name": "🛡️ ДИЛДОСТРАЖ",
        "description": "Провести 1 час в голосовом канале — страж порядка!",
        "points": 40,
        "icon": "🛡️"
    },
    "voice_2h": {
        "id": "voice_2h",
        "name": "🍆 БОЛЬШОЙ-ДИЛДОС",
        "description": "Провести 2 часа в голосовом — ты большой!",
        "points": 50,
        "icon": "🍆"
    },
    "voice_4h": {
        "id": "voice_4h",
        "name": "🌽 ДИЛДОХУЙ",
        "description": "Провести 4 часа в голосовом — реально мощный поток!",
        "points": 70,
        "icon": "🌽"
    },
    "voice_6h": {
        "id": "voice_6h",
        "name": "👦🏿 ЧЕРНЫЙ-ВЛАСТЕЛИН",
        "description": "Провести 6 часов в голосовом — тьма тебя боится!",
        "points": 100,
        "icon": "👦🏿"
    },
    "voice_7h": {
        "id": "voice_7h",
        "name": "👅 ДИЛДОЛИЗ",
        "description": "Провести 7 часов в голосовом — легенда!",
        "points": 120,
        "icon": "👅"
    },
    "voice_10h": {
        "id": "voice_10h",
        "name": "🍺 ДИЛДОБИЛДЕР",
        "description": "Провести 10 часов в голосовом — ТЫ ПОСТРОИЛ ЭТОТ ГОРОД!",
        "points": 150,
        "icon": "🍺"
    },
    "duel_lose": {
        "id": "duel_lose",
        "name": "😭 ЛОХ",
        "description": "Проиграть дуэль — бывает, брат!",
        "points": 5,
        "icon": "😭"
    },
    "duel_win": {
        "id": "duel_win",
        "name": "🍺 ПИВНОЙ",
        "description": "Выиграть дуэль — ты красава!",
        "points": 10,
        "icon": "🍺"
    },
    "duel_10wins": {
        "id": "duel_10wins",
        "name": "🐻 ПЬЯНЫЙ ПУХ",
        "description": "Выиграть 10 дуэлей — легенда!",
        "points": 50,
        "icon": "🐻"
    },
    "duel_10loses": {
        "id": "duel_10loses",
        "name": "🍷 ПЬЯНЫЙ ВЛАД",
        "description": "Проиграть 10 дуэлей — держись, братан!",
        "points": 30,
        "icon": "🍷"
    },
    "night_owl": {
        "id": "night_owl",
        "name": "🌙 НОЧНОЙ ДОЗОР",
        "description": "Сидеть в голосовом после 2:00 ночи!",
        "points": 40,
        "icon": "🌙"
    },
    "hero_day": {
        "id": "hero_day",
        "name": "🦸 ГЕРОЙ ДНЯ",
        "description": "Первый, кто написал сегодня!",
        "points": 30,
        "icon": "🦸"
    },
}

def check_achievements(user_id: int, player_data, current_achievements):
    """Проверяет, какие достижения можно выдать"""
    new_achievements = []
    
    # welcome
    if "welcome" not in current_achievements:
        new_achievements.append("welcome")
    
    # Сообщения
    msg_count = player_data[5]
    if msg_count >= 2 and "chat_50" not in current_achievements:
        new_achievements.append("chat_50")
    
    # Время в голосовом (в секундах)
    voice_seconds = player_data[4]
    voice_hours = voice_seconds // 3600
    
    if voice_hours >= 10 and "voice_10h" not in current_achievements:
        new_achievements.append("voice_10h")
    if voice_hours >= 7 and "voice_7h" not in current_achievements:
        new_achievements.append("voice_7h")
    if voice_hours >= 6 and "voice_6h" not in current_achievements:
        new_achievements.append("voice_6h")
    if voice_hours >= 4 and "voice_4h" not in current_achievements:
        new_achievements.append("voice_4h")
    if voice_hours >= 2 and "voice_2h" not in current_achievements:
        new_achievements.append("voice_2h")
    if voice_hours >= 1 and "voice_1h" not in current_achievements:
        new_achievements.append("voice_1h")
    
    return new_achievements