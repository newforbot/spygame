# shpionfinal.py
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Chat
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
import random
import asyncio
import time
import logging
import os
import json

# === ЛОГИ ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === НАСТРОЙКИ ===
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5213637344"))

DATA_FILE = "/data/spybot_data.json"
LOCATIONS_FILE = "/data/locations.json"
AUTOSAVE_INTERVAL = 120  # seconds

# === ЗАГРУЗКА / СОХРАНЕНИЕ ДАННЫХ ===
saved_data = {
    "known_users": [],
    "user_lang": {},   # str(user_id) -> lang
    "stats": {},       # str(user_id) -> stats dict
    "used_location_times": {}  # str(chat_id) -> [(idx, ts), ...]
}

def load_data():
    global saved_data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
            # ensure keys
            saved_data.setdefault("known_users", [])
            saved_data.setdefault("user_lang", {})
            saved_data.setdefault("stats", {})
            saved_data.setdefault("used_location_times", {})
            logger.info("Loaded data from %s", DATA_FILE)
        except Exception as e:
            logger.exception("Failed to load data file: %s", e)

def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(saved_data, f, ensure_ascii=False, indent=2)
        logger.debug("Saved data to %s", DATA_FILE)
    except Exception as e:
        logger.exception("Failed to save data: %s", e)

# === ЗАГРУЗКА / СОХРАНЕНИЕ ЛОКАЦИЙ ===
# Если файла нет — будет использоваться дефолтный LOCATIONS (ниже), и файл будет создан.
def load_locations():
    global LOCATIONS
    if os.path.exists(LOCATIONS_FILE):
        try:
            with open(LOCATIONS_FILE, "r", encoding="utf-8") as f:
                LOCATIONS = json.load(f)
            logger.info("Loaded locations from %s", LOCATIONS_FILE)
        except Exception as e:
            logger.exception("Failed to load locations file: %s", e)

def save_locations():
    try:
        with open(LOCATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(LOCATIONS, f, ensure_ascii=False, indent=2)
        logger.debug("Saved locations to %s", LOCATIONS_FILE)
    except Exception as e:
        logger.exception("Failed to save locations: %s", e)

# === IN-MEMORY VIEWS ===
known_users = set(saved_data.get("known_users", []))
# user_lang in-memory uses int keys for convenience
user_lang = {}
for k, v in saved_data.get("user_lang", {}).items():
    try:
        user_lang[int(k)] = v
    except Exception:
        pass
stats = dict(saved_data.get("stats", {}))

# === ДЕФОЛТНЫЕ ЛОКАЦИИ (если locations.json не существует) ===
LOCATIONS = {
    "ru": [
        "Школа", "Ресторан", "Аэропорт", "Пляж", "Кинотеатр", "Больница", "Парк", "Самолет",
        "Музей", "Банк", "Полицейский участок", "Футбольный стадион", "Тюрьма", "Ферма", "Парк развлечений",
        "Церковь", "Супермаркет", "Зоопарк", "Подводная лодка", "Казино", "Театр", "Военная база",
        "Кафе", "Отель", "Свадьба", "Офис", "Кемпинг", "Корабль", "Автобус", "Рынок", "Метро",
        "Поезд", "Прачечная", "Космическая станция", "Космический корабль", "Замок", "Башня волшебника",
        "Пиратский корабль", "Подземелье", "Кузница", "Пекарня", "Университет", "Бар", "Стадион",
        "Площадь города", "Библиотека", "Музей науки", "Бассейн", "Космопорт", "Склад", "Станция метро",
        "Салон красоты", "Кладбище", "Заброшенный дом", "Пустыня", "Арена гладиаторов", "Остров",
        "Вулкан", "Лес", "Пещера", "Магическая академия", "Таверна", "Банк крови", "Телестудия",
        "Фабрика", "Почта", "Парикмахерская", "Цирк", "Кондитерская", "Магазин одежды", "Аптека",
        "Станция техобслуживания", "Суд", "Станция спасателей", "Фитнес клуб", "Спа-салон", "Торговый центр",
        "Рынок специй", "Вокзал", "Маяк", "Ресторан на крыше", "Больничная палата", "Кухня ресторана",
        "Порт", "Гараж", "Тюрьма строгого режима", "Пустой стадион ночью", "Парк аттракционов",
        "Город-призрак", "Тропический остров", "Площадь перед дворцом", "Снежная гора", "Звёздная обсерватория",
        "Секретная лаборатория", "Тронный зал", "Пирамиды", "Космическая колония", "Средневековая деревня",
        "Город будущего", "Туманное болото", "Подводный город", "Дом с привидениями", "Арт-галерея"
    ],
    "en": [
        "School", "Restaurant", "Airport", "Beach", "Cinema", "Hospital", "Park", "Airplane",
        "Museum", "Bank", "Police Station", "Football Stadium", "Prison", "Farm", "Amusement Park",
        "Church", "Supermarket", "Zoo", "Submarine", "Casino", "Theatre", "Military Base",
        "Cafe", "Hotel", "Wedding", "Office", "Camping Site", "Ship", "Bus", "Market", "Subway",
        "Train", "Laundry", "Space Station", "Spaceship", "Castle", "Wizard Tower",
        "Pirate Ship", "Dungeon", "Forge", "Bakery", "University", "Bar", "Stadium",
        "Town Square", "Library", "Science Museum", "Swimming Pool", "Spaceport", "Warehouse", "Metro Station",
        "Beauty Salon", "Cemetery", "Abandoned House", "Desert", "Gladiator Arena", "Island",
        "Volcano", "Forest", "Cave", "Magic Academy", "Tavern", "Blood Bank", "TV Studio",
        "Factory", "Post Office", "Barbershop", "Circus", "Sweet Shop", "Clothing Store", "Pharmacy",
        "Service Station", "Court", "Rescue Station", "Fitness Club", "Spa", "Shopping Mall",
        "Spice Market", "Train Station", "Lighthouse", "Rooftop Restaurant", "Hospital Room", "Restaurant Kitchen",
        "Harbor", "Garage", "High Security Prison", "Empty Stadium at Night", "Theme Park",
        "Ghost Town", "Tropical Island", "Palace Square", "Snowy Mountain", "Observatory",
        "Secret Laboratory", "Throne Room", "Pyramids", "Space Colony", "Medieval Village",
        "City of the Future", "Foggy Swamp", "Underwater City", "Haunted House", "Art Gallery"
    ],
    "uz": [
        "Maktab", "Restoran", "Aeroport", "Sohil", "Kinoteatr", "Kasalxona", "Bog‘", "Samolyot",
        "Muzey", "Bank", "Politsiya bo‘limi", "Futbol stadioni", "Qamoqxona", "Ferma", "Attraksionlar bog‘i",
        "Cherkov", "Supermarket", "Hayvonot bog‘i", "Suv osti kemasi", "Kazino", "Teatr", "Harbiy baza",
        "Kafe", "Mehmonxona", "To‘y marosimi", "Ofis", "Oromgoh", "Kema", "Avtobus", "Bozor", "Metro",
        "Poyezd", "Kir yuvish joyi", "Kosmik stansiya", "Kosmik kema", "Qal’a", "Sehrgar minorasi",
        "Qaroqchilar kemasi", "Zindon", "Temirchi ustaxonasi", "Nonvoyxona", "Universitet", "Bar", "Stadion",
        "Shahar maydoni", "Kutubxona", "Fanlar muzeyi", "Suzish havzasi", "Kosmodrom", "Omborxona", "Metro bekati",
        "Go‘zallik saloni", "Mozor", "Tashlab ketilgan uy", "Cho‘l", "Gladiatorlar arenasi", "Orol",
        "Vulkan", "O‘rmon", "G‘or", "Sehrli akademiya", "Taverna", "Qon banki", "Televideniye studiyasi",
        "Zavod", "Pochta", "Sartaroshxona", "Sirk", "Shirinliklar do‘koni", "Kiyim-kechak do‘koni", "Dorixona",
        "Avtoxizmat stansiyasi", "Sud", "Qutqaruv markazi", "Fitnes klubi", "Spa saloni", "Savdo markazi",
        "Ziravorlar bozori", "Vokzal", "Mayoq", "Tomdagi restoran", "Kasallik xonasi", "Restoran oshxonasi",
        "Bandar", "Garaj", "Qattiq rejimli qamoqxona", "Tunda bo‘sh stadion", "Attraksionlar parki",
        "Jinlar shahri", "Tropik orol", "Saroy maydoni", "Qorli tog‘", "Kuzatuv minorasi",
        "Maxfiy laboratoriya", "Taxt zali", "Piramidalar", "Kosmik koloniya", "O‘rta asr qishlog‘i",
        "Kelajak shahri", "Tumanli botqoq", "Suv osti shahri", "Arvohlar uyi", "San’at galereyasi"
    ]
}

# Попробуем загрузить locations.json (если есть)
load_locations()

# === ТЕКСТЫ НА ЯЗЫКАХ (добавлены help/profile как раньше) ===
LANG_TEXTS = {
    "ru": {
        "welcome": "Привет! 👋 Я бот игры «Шпион»./help",
        "newgame": "🎮 Новая игра создана! Нажмите кнопку, чтобы присоединиться.",
        "join": "{} присоединился(лась) к игре!",
        "already_joined": "Вы уже в игре.",
        "not_created": "Игра не создана. Введите /newgame",
        "startgame": "Игра началась! 🎯 Проверьте свои личные сообщения.",
        "spy_msg": "🕵️ Вы — шпион! Попробуйте угадать локацию.",
        "player_msg": "📍 Локация: {}",
        "too_few": "Нужно минимум 3 игрока, чтобы начать игру.",
        "endgame": "Игра завершена! Спасибо за игру 👏",
        "vote_started": "🗳️ Голосование началось! У вас {} секунд, чтобы проголосовать.",
        "vote_already": "Голосование уже идет.",
        "vote_no_game": "Нет активной игры в этом чате.",
        "vote_once": "Вы уже проголосовали — изменить голос нельзя.",
        "vote_thanks": "{} проголосовал(а) за {}",
        "vote_tied": "Ничья — голосование завершено, но результата нет. Повторите /vote для нового голосования.",
        "vote_result_players_win": "Игроки угадали шпиона! Люди выигрывают 🎉",
        "vote_result_spy_wins": "Шпион остался нераскрытым — побеждает шпион 🕵️‍♂️",
        "vote_no_votes": "Никто не проголосовал. Голосование прошло бессмысленно.",
        "vote_only_one": "Недостаточно голосов (1 или менее). Голосование отменено.",
        "help": (
            "/newgame — создать новую игру\n"
            "/startgame — начать игру (необходимо ≥3 игроков)\n"
            "/vote [сек] — начать голосование (по умолчанию 60)\n"
            "/endgame confirm — завершить текущую игру (подтверждение)\n"
            "/profile — ваша статистика\n"
            "/top — топ игроков по победам\n"
            "/rules — правила\n"
            "/people — количество пользователей бота\n"
            "/locations - все локации\n"
            "/guess - попробовать угадать локацию\n"
        ),
        "profile": "Профиль {}:\nИгры: {}\nПобеды: {}\nПоражения: {}\nСыграно как шпион: {}",
        "no_stats": "Статистика отсутствует.",
        "addlocation_ok": "Новая локация добавлена: {} / {} / {}",
        "addlocation_denied": "Только админ может добавлять локации. Доступ запрещён.",
        "addlocation_usage": "Использование: /addlocation <англ_название> <узб_название> <рус_название> (многословные — с _ вместо пробелов).",
        "already_created": "В этом чате уже есть созданная игра. Используйте её или завершите /endgame confirm.",
        "game_already_started": "Игра уже началась.",
        "not_in_game": "❌ Вы не участвуете в этой игре.",
        "no_self_vote": "❌ Нельзя голосовать за себя!",
        "guess_group_only": "❌ Команду /guess можно использовать только в группе, где идёт игра.",
        "guess_no_game": "❌ Сейчас нет активной игры.",
        "guess_only_spy": "🚫 Только шпион может делать попытку угадать.",
        "guess_usage": "Использование: /guess <локация>",
        "guess_wrong": "❌ Неверно, попробуйте снова.",
        "status_players": "👥 Игроки: {}\n🕹️ Игра запущена: {}"

    },
    "en": {
        "welcome": "Hi! 👋 I’m the Spy game bot./help",
        "newgame": "🎮 New game created! Click the button to join.",
        "join": "{} joined the game!",
        "already_joined": "You already joined.",
        "not_created": "No active game. Type /newgame",
        "startgame": "The game has started! 🎯 Check your private messages.",
        "spy_msg": "🕵️ You are the spy! Try to guess the location.",
        "player_msg": "📍 Location: {}",
        "too_few": "At least 3 players required to start.",
        "endgame": "Game over! Thanks for playing 👏",
        "vote_started": "🗳️ Vote started! You have {} seconds to vote.",
        "vote_already": "A vote is already in progress.",
        "vote_no_game": "No active game in this chat.",
        "vote_once": "You already voted — you cannot change your vote.",
        "vote_thanks": "{} voted for {}",
        "vote_tied": "Tie — vote closed with no outcome. Call /vote again to retry.",
        "vote_result_players_win": "Players found the spy! Players win 🎉",
        "vote_result_spy_wins": "Spy was not found — spy wins 🕵️‍♂️",
        "vote_no_votes": "Nobody voted. Vote had no effect.",
        "vote_only_one": "Not enough decisive votes. Vote cancelled.",
        "help": (
            "/newgame — create a new game\n"
            "/startgame — start the game (requires ≥3 players)\n"
            "/vote [seconds] — start voting (default 60)\n"
            "/endgame confirm — finish current game (confirmation)\n"
            "/profile — your stats\n"
            "/top — top players by wins\n"
            "/rules — rules\n"
            "/people — number of bot users\n"
            "/locations - all locations\n"
            "/guess - try to guess the location\n"
        ),
        "profile": "Profile {}:\nGames: {}\nWins: {}\nLosses: {}\nPlayed as spy: {}",
        "no_stats": "No statistics yet.",
        "addlocation_ok": "Location added: {} / {} / {}",
        "addlocation_denied": "Only admin can add locations. Access denied.",
        "addlocation_usage": "Usage: /addlocation <eng_name> <uzb_name> <rus_name> (use _ instead of spaces for multiword).",
        "already_created": "There is already a created game in this chat. Use it or finish with /endgame confirm.",
        "game_already_started": "Game already started.",
        "not_in_game": "❌ You are not part of this game.",
        "no_self_vote": "❌ You cannot vote for yourself!",
        "guess_group_only": "❌ /guess command can only be used in a group where the game is running.",
        "guess_no_game": "❌ There is no active game right now.",
        "guess_only_spy": "🚫 Only the spy can make a guess.",
        "guess_usage": "Usage: /guess <location>",
        "guess_wrong": "❌ Wrong guess, try again!",
        "status_players": "👥 Players: {}\n🕹️ Game started: {}"

    },
    "uz": {
        "welcome": "Salom! 👋 Men 'Josus' o‘yini botiman./help",
        "newgame": "🎮 Yangi o‘yin boshlandi! Qo‘shilish uchun tugmani bosing.",
        "join": "{} o‘yinga qo‘shildi!",
        "already_joined": "Siz allaqachon o‘yindasiz.",
        "not_created": "O‘yin hali yaratilmagan. /newgame yozing.",
        "startgame": "O‘yin boshlandi! 🎯 Shaxsiy xabarlaringizni tekshiring.",
        "spy_msg": "🕵️ Siz josussiz! Joyni topishga harakat qiling.",
        "player_msg": "📍 Joy: {}",
        "too_few": "O‘yin uchun kamida 3 o‘yinchi kerak.",
        "endgame": "O‘yin tugadi! Rahmat 👏",
        "vote_started": "🗳️ Ovoz berish boshlandi! Ovozni berish uchun {} soniya bor.",
        "vote_already": "Ovoz berish allaqачон davom etmoqda.",
        "vote_no_game": "Bu chatda aktiv o‘yin yo‘q.",
        "vote_once": "Siz allaqachon ovoz berdingiz — o‘zgartirib bo‘lmaydi.",
        "vote_thanks": "{} {} ga ovoz berdi",
        "vote_tied": "Durang — ovoz berish natijasiz tugadi. Yana /vote buyrug‘ini bering.",
        "vote_result_players_win": "O‘yinchilar josusni topishdi! O‘yinchilar g‘olib 🎉",
        "vote_result_spy_wins": "Josus aniqlanmadi — josus g‘olib 🕵️‍♂️",
        "vote_no_votes": "Hech kim ovoz bermadi. Ovoz berish bekor qilindi.",
        "vote_only_one": "Yetarli qaror qabul qilinmadi. Ovoz berish bekor qilindi.",
        "help": (
            "/newgame — yangi o‘yin yaratish\n"
            "/startgame — o‘yin boshlash (kamida 3 o‘yinchi kerak)\n"
            "/vote [soniya] — ovoz berishni boshlash (standart 60)\n"
            "/endgame confirm — o‘yinni tugatish (tasdiq)\n"
            "/profile — sizning statistika\n"
            "/top — g‘alabalarga ko‘ra top\n"
            "/rules — qoidalar\n"
            "/people — bot foydalanuvchilari soni\n"
            "/locations - barcha joylar\n"
            "/guess - joyni topishga harakat qilish\n"
        ),
        "profile": "{} profili:\nO‘yinlar: {}\nG‘alabalar: {}\nMagg‘lubiyatlar: {}\nJosus sifatida o‘ynagan: {}",
        "no_stats": "Statistika yo‘q.",
        "addlocation_ok": "Yangi joy qo‘shildi: {} / {} / {}",
        "addlocation_denied": "Joy qo‘shish faqat adminga ruxsat berilgan.",
        "addlocation_usage": "Foydalanish: /addlocation <angl_nomi> <uzb_nomi> <rus_nomi> (so'zlar uchun _ ishlatilsin).",
        "already_created": "Bu chatda allaqachon o‘yin yaratilgan. Uni ishlating yoki /endgame confirm yozib tugating.",
        "game_already_started": "O‘yin allaqachon boshlangan.",
        "not_in_game": "❌ Siz bu o‘yinda ishtirok etmayapsiz.",
        "no_self_vote": "❌ O‘zingizga ovoz berolmaysiz!",
        "guess_group_only": "❌ /guess buyrug‘i faqat guruhda ishlaydi, o‘yin davom etayotganda.",
        "guess_no_game": "❌ Hozir faol o‘yin yo‘q.",
        "guess_only_spy": "🚫 Faqat josus taxmin qilishi mumkin.",
        "guess_usage": "Foydalanish: /guess <joy>",
        "guess_wrong": "❌ Noto‘g‘ri, yana urinib ko‘ring.",
        "status_players": "👥 O‘yinchilar: {}\n🕹️ O‘yin boshlandi: {}"

    }
}

# === ПРАВИЛА === (как раньше)
RULES_TEXT = {
    "ru": (
        "🎯 Правила игры «Шпион»:\n\n"
        "1️⃣ Все игроки получают одинаковую локацию, кроме шпиона.\n"
        "2️⃣ Шпион не знает локацию и должен угадать её по вопросам.\n"
        "3️⃣ Игроки по очереди задают друг другу вопросы о месте.\n"
        "4️⃣ Цель обычных игроков — вычислить шпиона.\n"
        "5️⃣ Цель шпиона — не раскрыться и угадать локацию.\n"
        "6️⃣ Когда обсуждение закончено, начинается голосование.\n"
        "7️⃣ Игроки не могут голосовать за себя.\n"
        "8️⃣ Если большинство голосует против шпиона — побеждают игроки!"
    ),
    "en": (
        "🎯 Rules of the Spy Game:\n\n"
        "1️⃣ All players get the same location except the spy.\n"
        "2️⃣ The spy doesn’t know the location and must guess it.\n"
        "3️⃣ Players take turns asking each other questions about the place.\n"
        "4️⃣ Non-spy players must find out who the spy is.\n"
        "5️⃣ The spy must avoid being detected and guess the location.\n"
        "6️⃣ When discussion ends, voting begins.\n"
        "7️⃣ Players can’t vote for themselves.\n"
        "8️⃣ If the majority vote against the spy — players win!"
    ),
    "uz": (
        "🎯 'Josus' o‘yini qoidalari:\n\n"
        "1️⃣ Barcha o‘yinchilar bir xil joyni biladi, faqat josus bilmaydi.\n"
        "2️⃣ Josus joyni bilmaydi va uni taxmin qilishi kerak.\n"
        "3️⃣ O‘yinchilar navbat bilan joy haqida savollar beradi.\n"
        "4️⃣ Oddiy o‘yinchilar josusni topishlari kerak.\n"
        "5️⃣ Josus esa fosh bo‘lmasligi va joyni topishi kerak.\n"
        "6️⃣ Muhokama tugagach, ovoz berish boshlanadi.\n"
        "7️⃣ O‘yinchilar o‘zlariga ovoz bera olmaydi.\n"
        "8️⃣ Agar ko‘pchilik josusni topa olsa — o‘yinchilar g‘alaba qozonadi!"
    ),
}

async def rules_command(update, context):
    lang = user_lang.get(update.effective_user.id, saved_data.get("user_lang", {}).get(str(update.effective_user.id), "en"))
    text = RULES_TEXT.get(lang, RULES_TEXT["en"])
    await update.message.reply_text(text)

# === ХРАНИЛИЩЕ ИГР И ДРУГИХ СТАТЕЙ (in-memory; games not persisted intentionally) ===
games = {}  # chat_id -> {players: [{"id","name"}], started:bool, creator_id, spy_id, location_index, started_at}
vote_sessions = {}  # chat_id -> {active:bool, votes: {voter_id: target_id}, counts: {target_id: int}, task: asyncio.Task, started_at: ts, timeout: seconds}

# === УТИЛИТЫ ===
def now_ts():
    return int(time.time())

def ensure_chat_used_locations(chat_id):
    used = saved_data.setdefault("used_location_times", {})
    used.setdefault(str(chat_id), [])
    return used[str(chat_id)]

def cleanup_used_locations_for_chat(chat_id):
    cutoff = now_ts() - 3600
    used_list = ensure_chat_used_locations(chat_id)
    changed = False
    while used_list and used_list[0][1] < cutoff:
        used_list.pop(0)
        changed = True
    if changed:
        saved_data["used_location_times"][str(chat_id)] = used_list
        save_data()

def choose_location_index(chat_id):
    used_list = ensure_chat_used_locations(chat_id)
    cleanup_used_locations_for_chat(chat_id)
    total = len(next(iter(LOCATIONS.values())))
    used_idxs = {idx for (idx, ts) in used_list}
    available = [i for i in range(total) if i not in used_idxs]
    if not available:
        idx = random.randrange(total)
    else:
        idx = random.choice(available)
    used_list.append((idx, now_ts()))
    used_list.sort(key=lambda x: x[1])
    saved_data["used_location_times"][str(chat_id)] = used_list
    save_data()
    return idx

def ensure_user_stats(user_id):
    sid = str(user_id)
    if sid not in saved_data["stats"]:
        saved_data["stats"][sid] = {"games": 0, "wins": 0, "losses": 0, "spy_count": 0}
        save_data()
    return saved_data["stats"][sid]

def mark_stats_game_end(game_chat_id, spy_id, spy_won):
    game = games.get(game_chat_id)
    if not game:
        return
    for p in game["players"]:
        st = ensure_user_stats(p["id"])
        st["games"] = st.get("games", 0) + 1
        if p["id"] == spy_id:
            st["spy_count"] = st.get("spy_count", 0) + 1
            if spy_won:
                st["wins"] = st.get("wins", 0) + 1
            else:
                st["losses"] = st.get("losses", 0) + 1
        else:
            if spy_won:
                st["losses"] = st.get("losses", 0) + 1
            else:
                st["wins"] = st.get("wins", 0) + 1
    save_data()

def register_user_seen(user_id, lang=None):
    # add to known_users and saved_data maps (use str keys in saved_data)
    if user_id not in known_users:
        known_users.add(user_id)
        saved_data["known_users"] = list(known_users)
    if lang:
        saved_data.setdefault("user_lang", {})[str(user_id)] = lang
    # update in-memory map
    if lang:
        user_lang[user_id] = lang
    else:
        # try load existing lang
        lang_saved = saved_data.get("user_lang", {}).get(str(user_id))
        if lang_saved:
            user_lang[user_id] = lang_saved
    save_data()

# === ОБРАБОТЧИКИ ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type != Chat.PRIVATE:
        await update.message.reply_text("👋 Нажмите /start в личных сообщениях бота, чтобы выбрать язык и получить инструкции.")
        return

    register_user_seen(user.id, user_lang.get(user.id, "en"))

    keyboard = [
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇺🇿 O‘zbek", callback_data="lang_uz")]
    ]
    await update.message.reply_text(
        "👋 Choose language / Выберите язык / Tilni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_")[1]
    saved_data.setdefault("user_lang", {})[str(query.from_user.id)] = lang
    save_data()
    user_lang[query.from_user.id] = lang
    known_users.add(query.from_user.id)
    saved_data["known_users"] = list(known_users)
    save_data()
    txt = LANG_TEXTS.get(lang, LANG_TEXTS["en"])["welcome"]
    await query.message.reply_text(txt)

async def new_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = chat.id
    creator_id = update.effective_user.id
    creator_lang = saved_data.get("user_lang", {}).get(str(creator_id), user_lang.get(creator_id, "en"))

    existing = games.get(chat_id)
    if existing and not existing.get("started"):
        await update.message.reply_text(LANG_TEXTS[creator_lang]["already_created"])
        return

    games[chat_id] = {
        "players": [],
        "started": False,
        "creator_id": creator_id,
        "spy_id": None,
        "location_index": None,
        "started_at": None
    }

    keyboard = [
        [InlineKeyboardButton("🧩 Join / Qo‘shilish / Присоединиться", callback_data=f"join_{chat_id}")]
    ]
    await update.message.reply_text(
        LANG_TEXTS[creator_lang]["newgame"],
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    try:
        chat_id = int(data.split("_")[1])
    except:
        await query.message.reply_text("Bad join data.")
        return

    user = query.from_user
    lang = saved_data.get("user_lang", {}).get(str(user.id), user_lang.get(user.id, "en"))

    if chat_id not in games:
        await query.answer(LANG_TEXTS[lang]["not_created"], show_alert=True)
        return

    game = games[chat_id]
    if game["started"]:
        await query.answer("Game already started!", show_alert=True)
        return

    if user.id not in [p["id"] for p in game["players"]]:
        game["players"].append({"id": user.id, "name": user.full_name})
        register_user_seen(user.id, lang)
        await query.message.reply_text(LANG_TEXTS[lang]["join"].format(user.full_name))
    else:
        await query.answer(LANG_TEXTS[lang]["already_joined"], show_alert=True)

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game = games.get(chat_id)
    if not game:
        lang = saved_data.get("user_lang", {}).get(str(update.effective_user.id), user_lang.get(update.effective_user.id, "en"))
        await update.message.reply_text(LANG_TEXTS[lang]["not_created"])
        return

    creator_lang = saved_data.get("user_lang", {}).get(str(game["creator_id"]), user_lang.get(game["creator_id"], "en"))
    if len(game["players"]) < 3:
        await update.message.reply_text(LANG_TEXTS[creator_lang]["too_few"])
        return

# Если игра уже запущена — начинаем новый раунд
    if game["started"]:
        await update.message.reply_text("🔁 Начинается новый раунд!")
        # Просто перезапускаем: выбираем новую локацию и нового шпиона
        location_index = choose_location_index(chat_id)
        game["location_index"] = location_index

        spy = random.choice(game["players"])
        game["spy_id"] = spy["id"]
        game["started_at"] = now_ts()

        failed_pm = []
        for player in game["players"]:
            player_lang = saved_data.get("user_lang", {}).get(str(player["id"]), user_lang.get(player["id"], "en"))
            try:
                if player["id"] == game["spy_id"]:
                    await context.bot.send_message(player["id"], LANG_TEXTS[player_lang]["spy_msg"])
                else:
                    loc = LOCATIONS.get(player_lang, LOCATIONS["en"])[location_index]
                    await context.bot.send_message(player["id"], LANG_TEXTS[player_lang]["player_msg"].format(loc))
            except Exception as e:
                logger.warning("Can't send PM to %s: %s", player["id"], e)
                failed_pm.append(player["name"])

        if failed_pm:
            names = ", ".join(failed_pm[:5])
            more = f" и ещё {len(failed_pm)-5}" if len(failed_pm) > 5 else ""
            hint = {
                "ru": "Некоторым игрокам не удалось доставить личное сообщение. Попросите их написать боту в ЛС (нажать /start).",
                "en": "Some players couldn't receive a private message. Ask them to message the bot in private (press /start).",
                "uz": "Ba'zi o'yinchilarga shaxsiy xabar yetib bormadi. Ulardan botga shaxsiy xabar yozishini so'rang (/start)."
            }
            await context.bot.send_message(chat_id, f"⚠️ {names}{more}. {hint.get(creator_lang,'Please DM the bot.')}")
        return

    game["started"] = True
    game["started_at"] = now_ts()

    location_index = choose_location_index(chat_id)
    game["location_index"] = location_index

    spy = random.choice(game["players"])
    game["spy_id"] = spy["id"]

    failed_pm = []
    for player in game["players"]:
        player_lang = saved_data.get("user_lang", {}).get(str(player["id"]), user_lang.get(player["id"], "en"))
        try:
            if player["id"] == game["spy_id"]:
                await context.bot.send_message(player["id"], LANG_TEXTS[player_lang]["spy_msg"])
            else:
                loc = LOCATIONS.get(player_lang, LOCATIONS["en"])[location_index]
                await context.bot.send_message(player["id"], LANG_TEXTS[player_lang]["player_msg"].format(loc))
        except Exception as e:
            logger.warning("Can't send PM to %s: %s", player["id"], e)
            failed_pm.append(player["name"])

    await update.message.reply_text(LANG_TEXTS[creator_lang]["startgame"])

    if failed_pm:
        names = ", ".join(failed_pm[:5])
        more = f" и ещё {len(failed_pm)-5}" if len(failed_pm) > 5 else ""
        hint = {
            "ru": "Некоторым игрокам не удалось доставить личное сообщение. Попросите их написать боту в ЛС (нажать /start).",
            "en": "Some players couldn't receive a private message. Ask them to message the bot in private (press /start).",
            "uz": "Ba'zi o'yinchilarga shaxsiy xabar yetib bormadi. Ulardan botga shaxsiy xabar yozishini so'rang (/start)."
        }
        await context.bot.send_message(chat_id, f"⚠️ {names}{more}. {hint.get(creator_lang,'Please DM the bot.')}")

async def end_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args or []
    if not args or args[0].lower() != "confirm":
        lang = saved_data.get("user_lang", {}).get(str(update.effective_user.id), user_lang.get(update.effective_user.id, "en"))
        await update.message.reply_text(f"To confirm ending the game run: /endgame confirm\n{LANG_TEXTS[lang].get('help','')}")
        return

    game = games.pop(chat_id, None)
    lang = saved_data.get("user_lang", {}).get(str(update.effective_user.id), user_lang.get(update.effective_user.id, "en"))

    session = vote_sessions.get(chat_id)
    if session and session.get("task"):
        task = session["task"]
        try:
            if not task.done():
                task.cancel()
        except Exception:
            pass
    vote_sessions.pop(chat_id, None)

    if not game:
        await update.message.reply_text(LANG_TEXTS[lang]["not_created"])
        return

    await update.message.reply_text(LANG_TEXTS[lang]["endgame"])



# === ГОЛОСОВАНИЕ ===

async def vote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game = games.get(chat_id)
    caller_lang = saved_data.get("user_lang", {}).get(str(update.effective_user.id), user_lang.get(update.effective_user.id, "en"))

    if not game or not game["started"]:
        await update.message.reply_text(LANG_TEXTS[caller_lang]["vote_no_game"])
        return

    session = vote_sessions.get(chat_id)
    if session and session.get("active"):
        await update.message.reply_text(LANG_TEXTS[caller_lang]["vote_already"])
        return

    timeout = 60
    try:
        if context.args:
            timeout_arg = int(context.args[0])
            if 10 <= timeout_arg <= 300:
                timeout = timeout_arg
    except Exception:
        timeout = 60

    players = game["players"]
    if not players:
        await update.message.reply_text(LANG_TEXTS[caller_lang]["vote_no_game"])
        return

    keyboard = []
    row = []
    for p in players:
        btn = InlineKeyboardButton(p["name"], callback_data=f"vote_{chat_id}_{p['id']}")
        row.append(btn)
        if len(row) >= 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    msg = await update.message.reply_text(
        LANG_TEXTS[caller_lang]["vote_started"].format(timeout),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    vote_sessions[chat_id] = {
        "active": True,
        "votes": {},
        "counts": {},
        "message_id": msg.message_id,
        "task": None,
        "started_at": now_ts(),
        "timeout": timeout
    }

    async def finalize_vote_after_delay(chat_id_local: int, delay: int):
        try:
            await asyncio.sleep(delay)
            await finalize_vote(chat_id_local, context)
        except asyncio.CancelledError:
            logger.info("Vote finalize task cancelled for chat %s", chat_id_local)

    task = asyncio.create_task(finalize_vote_after_delay(chat_id, timeout))
    vote_sessions[chat_id]["task"] = task

async def vote_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split("_")
    if len(parts) != 3:
        await query.message.reply_text("Bad vote data.")
        return

    try:
        chat_id = int(parts[1])
        target_id = int(parts[2])
    except:
        await query.message.reply_text("Bad vote data.")
        return

    voter = query.from_user
    voter_lang = saved_data.get("user_lang", {}).get(str(voter.id), user_lang.get(voter.id, "en"))
    session = vote_sessions.get(chat_id)
    game = games.get(chat_id)

    if not session or not session.get("active") or not game:
        await query.message.reply_text(LANG_TEXTS[voter_lang]["vote_no_game"])
        return

    if voter.id not in [p["id"] for p in game["players"]]:
        await query.answer(LANG_TEXTS[voter_lang]["not_in_game"], show_alert=True)
        return

    if voter.id == target_id:
        await query.answer(LANG_TEXTS[voter_lang]["no_self_vote"], show_alert=True)
        return

    if voter.id in session["votes"]:
        await query.answer(LANG_TEXTS[voter_lang]["vote_once"], show_alert=True)
        return

    session["votes"][voter.id] = target_id
    session["counts"][target_id] = session["counts"].get(target_id, 0) + 1

    target_name = next((p["name"] for p in game["players"] if p["id"] == target_id), str(target_id))
    try:
        await context.bot.send_message(chat_id, LANG_TEXTS[voter_lang]["vote_thanks"].format(voter.full_name, target_name))
    except Exception:
        logger.exception("Failed to publish vote info")

# === РАССЫЛКА ИТОГОВ ИГРЫ ===

async def announce_game_result(context: ContextTypes.DEFAULT_TYPE, chat_id: int, game: dict, spy_won: bool):
    """Отправляет итоги игры в группу и личные сообщения всем игрокам."""
    spy_id = game.get("spy_id")
    spy_user = next((p for p in game["players"] if p["id"] == spy_id), None)
    all_players = game["players"]

    # Список победителей
    if spy_won:
        winners = [spy_user] if spy_user else []
        losers = [p for p in all_players if p["id"] != spy_id]
        group_title = "🕵️ Победа шпиона!"
        result_text = f"🎉 {spy_user['name']} разгадал локацию и выиграл раунд!"
    else:
        winners = [p for p in all_players if p["id"] != spy_id]
        losers = [spy_user] if spy_user else []
        group_title = "🎯 Победа игроков!"
        result_text = "🎉 Игроки нашли шпиона и победили!"

    # — Отправляем в группу красиво оформленный итог
    winners_names = ", ".join([w['name'] for w in winners]) if winners else "—"
    losers_names = ", ".join([l['name'] for l in losers]) if losers else "—"

    text_group = (
        f"{group_title}\n\n"
        f"🏆 Победители: {winners_names}\n"
        f"💔 Проигравшие: {losers_names}\n\n"
        f"{result_text}"
    )

    await context.bot.send_message(chat_id, text_group)

    # — Личные сообщения
    for player in all_players:
        player_lang = saved_data.get("user_lang", {}).get(str(player["id"]), user_lang.get(player["id"], "en"))
        try:
            if player in winners:
                msg = {
                    "ru": "🎉 Поздравляем! Вы выиграли этот раунд!",
                    "en": "🎉 Congratulations! You won this round!",
                    "uz": "🎉 Tabriklaymiz! Siz bu raundda g‘alaba qozondingiz!"
                }.get(player_lang, "🎉 You won!")
            else:
                msg = {
                    "ru": "😔 К сожалению, вы проиграли в этом раунде.",
                    "en": "😔 Unfortunately, you lost this round.",
                    "uz": "😔 Afsuski, siz bu safar yutqazdingiz."
                }.get(player_lang, "😔 You lost this time.")
            await context.bot.send_message(player["id"], msg)
        except Exception as e:
            logger.warning(f"Не удалось отправить сообщение игроку {player['id']}: {e}")


async def finalize_vote(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    session = vote_sessions.get(chat_id)
    game = games.get(chat_id)
    if not session or not game:
        vote_sessions.pop(chat_id, None)
        return

    session["active"] = False

    counts = session["counts"]
    if not counts:
        creator_lang = saved_data.get("user_lang", {}).get(str(game["creator_id"]), user_lang.get(game["creator_id"], "en"))
        await context.bot.send_message(chat_id, LANG_TEXTS[creator_lang]["vote_no_votes"])
        vote_sessions.pop(chat_id, None)
        return

    max_votes = max(counts.values())
    winners = [int(tid) for tid, c in counts.items() if c == max_votes]

    creator_lang = saved_data.get("user_lang", {}).get(str(game["creator_id"]), user_lang.get(game["creator_id"], "en"))

    if len(winners) != 1:
        await context.bot.send_message(chat_id, LANG_TEXTS[creator_lang]["vote_tied"])
        vote_sessions.pop(chat_id, None)
        return

    chosen_id = winners[0]

    spy_won = False
    if chosen_id == game["spy_id"]:
        await context.bot.send_message(chat_id, LANG_TEXTS[creator_lang]["vote_result_players_win"])
        spy_won = False
        await announce_game_result(context, chat_id, game, spy_won=False)

    else:
        await context.bot.send_message(chat_id, LANG_TEXTS[creator_lang]["vote_result_spy_wins"])
        spy_won = True
        await announce_game_result(context, chat_id, game, spy_won=True)

    try:
        mark_stats_game_end(chat_id, game["spy_id"], spy_won)
    except Exception:
        logger.exception("Error updating stats")

    games.pop(chat_id, None)
    vote_sessions.pop(chat_id, None)

# === УГАДЫВАНИЕ ЛОКАЦИИ ШПИОНОМ ===

async def guess_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    # Разрешаем только в группе
    if chat.type not in ("group", "supergroup"):
        lang = saved_data.get("user_lang", {}).get(str(user.id), user_lang.get(user.id, "en"))
        await update.message.reply_text(LANG_TEXTS[lang]["guess_group_only"])
        return

    game = games.get(chat.id)
    if not game or not game.get("started"):
        lang = saved_data.get("user_lang", {}).get(str(user.id), user_lang.get(user.id, "en"))
        await update.message.reply_text(LANG_TEXTS[lang]["guess_no_game"])
        return

    if user.id != game.get("spy_id"):
        lang = saved_data.get("user_lang", {}).get(str(user.id), user_lang.get(user.id, "en"))
        await update.message.reply_text(LANG_TEXTS[lang]["guess_only_spy"])
        return

    guess_text = " ".join(context.args).strip()
    if not guess_text:
        lang = saved_data.get("user_lang", {}).get(str(user.id), user_lang.get(user.id, "en"))
        await update.message.reply_text(LANG_TEXTS[lang]["guess_usage"])
        return

    # --- Функция нормализации текста ---
    def norm(s):
        return s.strip().lower().replace("_", " ").replace("ё", "е")

    # Берём индекс текущей локации
    loc_index = game.get("location_index")
    if loc_index is None:
        await update.message.reply_text("⚠️ Ошибка: локация не найдена.")
        return

    # Все варианты локации (en, ru, uz)
    en_name = LOCATIONS["en"][loc_index]
    ru_name = LOCATIONS["ru"][loc_index]
    uz_name = LOCATIONS["uz"][loc_index]
    lang_variants = [en_name, ru_name, uz_name]

    # Проверяем совпадение
    if norm(guess_text) in map(norm, lang_variants):
        # Шпион угадал!
        mark_stats_game_end(chat.id, game["spy_id"], spy_won=True)
        await announce_game_result(context, chat.id, game, spy_won=True)
        games.pop(chat.id, None)
        return
    else:
        lang = saved_data.get("user_lang", {}).get(str(user.id), user_lang.get(user.id, "en"))
        await update.message.reply_text(LANG_TEXTS[lang]["guess_wrong"])


# === АДМИН: рассылка и добавление локаций ===

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Access denied.")
        return

    if not context.args:
        await update.message.reply_text("Использование: /broadcast <текст>")
        return

    text = " ".join(context.args)
    sent, failed = 0, 0
    for user_id in list(known_users):
        try:
            await context.bot.send_message(int(user_id), text)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1
            logger.warning(f"Не удалось отправить пользователю {user_id}: {e}")

    await update.message.reply_text(f"✅ Отправлено {sent}, не доставлено {failed}.")

async def addlocation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only: /addlocation <eng> <uz> <rus>
       Use underscores _ instead of spaces for multi-word names."""
    if update.effective_user.id != ADMIN_ID:
        # reply in caller's language if possible
        caller_lang = saved_data.get("user_lang", {}).get(str(update.effective_user.id), user_lang.get(update.effective_user.id, "en"))
        await update.message.reply_text(LANG_TEXTS[caller_lang]["addlocation_denied"])
        return

    args = context.args or []
    caller_lang = saved_data.get("user_lang", {}).get(str(update.effective_user.id), user_lang.get(update.effective_user.id, "en"))
    if len(args) < 3:
        await update.message.reply_text(LANG_TEXTS[caller_lang]["addlocation_usage"])
        return

    # take first three args only (extra words ignored)
    eng = args[0].replace("_", " ")
    uzb = args[1].replace("_", " ")
    rus = args[2].replace("_", " ")

    # Append to LOCATIONS lists
    try:
        LOCATIONS.setdefault("en", []).append(eng)
        LOCATIONS.setdefault("uz", []).append(uzb)
        LOCATIONS.setdefault("ru", []).append(rus)
        save_locations()
        # Inform admin
        await update.message.reply_text(LANG_TEXTS[caller_lang]["addlocation_ok"].format(eng, uzb, rus))
        logger.info("Admin added new location: %s / %s / %s", eng, uzb, rus)
    except Exception:
        logger.exception("Failed to add location")
        await update.message.reply_text("Failed to add location due to server error.")

async def people(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = saved_data.get("user_lang", {}).get(str(user_id), user_lang.get(user_id, "en"))
    count = len(known_users)
    if lang == "ru":
        text = f"{count} пользователей"
    elif lang == "uz":
        text = f"{count} ta foydalanuvchi"
    else:
        text = f"{count} number of users"
    await update.message.reply_text(text)

# === СПИСОК ЛОКАЦИЙ (СОРТИРОВАННЫЙ) ===

# === СПИСОК ЛОКАЦИЙ (СОРТИРОВАННЫЙ + КОЛИЧЕСТВО) ===

async def locations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает актуальный список локаций на трёх языках, отсортированных по алфавиту (EN), с подсчётом количества."""
    user_id = update.effective_user.id
    lang = saved_data.get("user_lang", {}).get(str(user_id), user_lang.get(user_id, "en"))

    if not LOCATIONS or not LOCATIONS.get("en"):
        await update.message.reply_text("⚠️ Список локаций пуст.")
        return

    # Собираем локации и сортируем по английскому названию
    count = min(len(LOCATIONS["en"]), len(LOCATIONS["uz"]), len(LOCATIONS["ru"]))
    locations_combined = []
    for i in range(count):
        en = LOCATIONS["en"][i]
        uz = LOCATIONS["uz"][i]
        ru = LOCATIONS["ru"][i]
        locations_combined.append((en, uz, ru))

    # сортировка по английскому названию
    locations_combined.sort(key=lambda x: x[0].lower())

    # собираем красивый вывод
    lines = []
    for idx, (en, uz, ru) in enumerate(locations_combined, start=1):
        lines.append(f"{idx}. 🇬🇧 *{en}*\n   🇺🇿 {uz}\n   🇷🇺 {ru}")

    header = {
        "ru": "📍 *Актуальный список локаций (по алфавиту):*",
        "en": "📍 *Current location list (alphabetically):*",
        "uz": "📍 *Joylar ro‘yxati (alfavit tartibida):*"
    }.get(lang, "📍 *Locations (alphabetical):*")

    footer = {
        "ru": f"\n\n📊 Всего локаций: *{count}*",
        "en": f"\n\n📊 Total locations: *{count}*",
        "uz": f"\n\n📊 Jami joylar soni: *{count}*"
    }.get(lang, f"\n\n📊 Total: *{count}*")

    text = header + "\n\n" + "\n\n".join(lines) + footer

    # делим, если слишком длинный
    if len(text) > 4000:
        parts = [text[i:i + 3800] for i in range(0, len(text), 3800)]
        for part in parts:
            await update.message.reply_text(part, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game = games.get(chat_id)
    lang = saved_data.get("user_lang", {}).get(str(update.effective_user.id), user_lang.get(update.effective_user.id, "en"))
    if not game:
        await update.message.reply_text(LANG_TEXTS[lang]["not_created"])
        return
    players = ", ".join([p["name"] for p in game["players"]])
    await update.message.reply_text(LANG_TEXTS[lang]["status_players"].format(players, game["started"]))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = saved_data.get("user_lang", {}).get(str(update.effective_user.id), user_lang.get(update.effective_user.id, "en"))
    await update.message.reply_text(LANG_TEXTS[lang]["help"])

# === ПРОФИЛЬ / ТОП ===

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = saved_data.get("user_lang", {}).get(str(user.id), user_lang.get(user.id, "en"))
    st = saved_data.get("stats", {}).get(str(user.id))
    if not st:
        await update.message.reply_text(LANG_TEXTS[lang]["no_stats"])
        return
    text = LANG_TEXTS[lang]["profile"].format(user.full_name, st.get("games",0), st.get("wins",0), st.get("losses",0), st.get("spy_count",0))
    await update.message.reply_text(text)

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = saved_data.get("user_lang", {}).get(str(update.effective_user.id), user_lang.get(update.effective_user.id, "en"))
    all_stats = saved_data.get("stats", {})
    if not all_stats:
        await update.message.reply_text(LANG_TEXTS[lang]["no_stats"])
        return

    sorted_users = sorted(all_stats.items(), key=lambda kv: kv[1].get("wins", 0), reverse=True)[:10]
    lines = []

    for uid, s in sorted_users:
        user_name = s.get("name")
        if not user_name:
            # Пробуем получить имя из Telegram
            try:
                user = await context.bot.get_chat(uid)
                if user.username:
                    user_name = f"@{user.username}"
                else:
                    user_name = user.full_name
            except Exception:
                user_name = str(uid)
            # Можно при желании сохранить имя, чтобы потом не запрашивать каждый раз
            s["name"] = user_name

        lines.append(f"{user_name}: {s.get('wins', 0)} wins / {s.get('games', 0)} games")

    await update.message.reply_text("\n".join(lines))

def attach_name_to_stats(user):
    sid = str(user.id)
    if sid not in saved_data["stats"]:
        saved_data["stats"][sid] = {"games":0,"wins":0,"losses":0,"spy_count":0}
    saved_data["stats"][sid]["name"] = user.full_name
    save_data()

# === BACKGROUND JOBS ===

async def periodic_cleanup(context: ContextTypes.DEFAULT_TYPE):
    now = now_ts()
    removed = 0
    for chat_id, game in list(games.items()):
        started_at = game.get("started_at")
        if started_at and now - started_at > 1800:
            session = vote_sessions.get(chat_id)
            if session and session.get("task"):
                try:
                    if not session["task"].done():
                        session["task"].cancel()
                except Exception:
                    pass
                vote_sessions.pop(chat_id, None)
            games.pop(chat_id, None)
            removed += 1
    if removed:
        logger.info("Periodic cleanup removed %s stale games", removed)

async def periodic_autosave(context: ContextTypes.DEFAULT_TYPE):
    # Save both saved_data and locations periodically
    save_data()
    save_locations()
    logger.debug("Periodic autosave executed")

# === ГЛАВНАЯ ФУНКЦИЯ ===
def main():
    load_data()
    load_locations()

    # sync in-memory views after load
    global known_users, user_lang, stats
    known_users = set(saved_data.get("known_users", []))
    # rebuild in-memory user_lang
    user_lang.clear()
    for k, v in saved_data.get("user_lang", {}).items():
        try:
            user_lang[int(k)] = v
        except Exception:
            pass
    stats.update(saved_data.get("stats", {}))

    app = Application.builder().token(TOKEN).build()

    # handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(choose_language, pattern="^lang_"))
    app.add_handler(CommandHandler("newgame", new_game))
    app.add_handler(CallbackQueryHandler(join_callback, pattern="^join_"))
    app.add_handler(CommandHandler("startgame", start_game))
    app.add_handler(CommandHandler("endgame", end_game))
    app.add_handler(CommandHandler("vote", vote_command))
    app.add_handler(CallbackQueryHandler(vote_button_callback, pattern="^vote_"))
    app.add_handler(CommandHandler("rules", rules_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("people", people))
    app.add_handler(CommandHandler("locations", locations_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("guess", guess_command))

    # admin add location
    app.add_handler(CommandHandler("addlocation", addlocation_command))

    # background jobs: cleanup and autosave
    app.job_queue.run_repeating(periodic_cleanup, interval=600, first=30)
    app.job_queue.run_repeating(periodic_autosave, interval=AUTOSAVE_INTERVAL, first=AUTOSAVE_INTERVAL)

    print("✅ Spy Bot запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
