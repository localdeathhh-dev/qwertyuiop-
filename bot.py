import os
import re
import time
import logging
import requests
import threading
import urllib.parse
import schedule

from dotenv import load_dotenv
import telebot
from telebot import types

# ==================== ЗАГРУЗКА ПЕРЕМЕННЫХ ====================
load_dotenv()

BOT_TOKEN    = os.getenv("BOT_TOKEN", "")
CHANNEL_ID   = os.getenv("CHANNEL_ID", "@your_channel")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO  = os.getenv("GITHUB_REPO", "username/lab-vpn-bot")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

# Ссылка на raw файл подписки (GitHub Pages или raw GitHub)
SUBSCRIPTION_URL = (
    f"https://raw.githubusercontent.com/{GITHUB_REPO}"
    f"/{GITHUB_BRANCH}/subscription.txt"
)

SUBSCRIPTION_FILE = "subscription.txt"

SOURCES = [
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia"
    "/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia"
    "/main/WHITE-SNI-RU-all.txt",
]

# ==================== ЛОГИРОВАНИЕ ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("labvpn.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ==================== СЛОВАРЬ ФЛАГОВ ====================
FLAG_TO_COUNTRY = {
    "🇦🇫": "Афганистан",      "🇦🇱": "Албания",
    "🇩🇿": "Алжир",           "🇦🇩": "Андорра",
    "🇦🇴": "Ангола",          "🇦🇬": "Антигуа и Барбуда",
    "🇦🇷": "Аргентина",       "🇦🇲": "Армения",
    "🇦🇺": "Австралия",       "🇦🇹": "Австрия",
    "🇦🇿": "Азербайджан",     "🇧🇸": "Багамы",
    "🇧🇭": "Бахрейн",         "🇧🇩": "Бангладеш",
    "🇧🇧": "Барбадос",        "🇧🇾": "Беларусь",
    "🇧🇪": "Бельгия",         "🇧🇿": "Белиз",
    "🇧🇯": "Бенин",           "🇧🇹": "Бутан",
    "🇧🇴": "Боливия",         "🇧🇦": "Босния и Герцеговина",
    "🇧🇼": "Ботсвана",        "🇧🇷": "Бразилия",
    "🇧🇳": "Бруней",          "🇧🇬": "Болгария",
    "🇧🇫": "Буркина-Фасо",    "🇧🇮": "Бурунди",
    "🇨🇻": "Кабо-Верде",      "🇰🇭": "Камбоджа",
    "🇨🇲": "Камерун",         "🇨🇦": "Канада",
    "🇨🇫": "ЦАР",             "🇹🇩": "Чад",
    "🇨🇱": "Чили",            "🇨🇳": "Китай",
    "🇨🇴": "Колумбия",        "🇰🇲": "Коморы",
    "🇨🇩": "ДР Конго",        "🇨🇬": "Конго",
    "🇨🇷": "Коста-Рика",      "🇭🇷": "Хорватия",
    "🇨🇺": "Куба",            "🇨🇾": "Кипр",
    "🇨🇿": "Чехия",           "🇩🇰": "Дания",
    "🇩🇯": "Джибути",         "🇩🇲": "Доминика",
    "🇩🇴": "Доминиканская Республика",
    "🇪🇨": "Эквадор",         "🇪🇬": "Египет",
    "🇸🇻": "Сальвадор",       "🇬🇶": "Экваториальная Гвинея",
    "🇪🇷": "Эритрея",         "🇪🇪": "Эстония",
    "🇸🇿": "Эсватини",        "🇪🇹": "Эфиопия",
    "🇫🇯": "Фиджи",           "🇫🇮": "Финляндия",
    "🇫🇷": "Франция",         "🇬🇦": "Габон",
    "🇬🇲": "Гамбия",          "🇬🇪": "Грузия",
    "🇩🇪": "Германия",        "🇬🇭": "Гана",
    "🇬🇷": "Греция",          "🇬🇩": "Гренада",
    "🇬🇹": "Гватемала",       "🇬🇳": "Гвинея",
    "🇬🇼": "Гвинея-Бисау",    "🇬🇾": "Гайана",
    "🇭🇹": "Гаити",           "🇭🇳": "Гондурас",
    "🇭🇺": "Венгрия",         "🇮🇸": "Исландия",
    "🇮🇳": "Индия",           "🇮🇩": "Индонезия",
    "🇮🇷": "Иран",            "🇮🇶": "Ирак",
    "🇮🇪": "Ирландия",        "🇮🇱": "Израиль",
    "🇮🇹": "Италия",          "🇯🇲": "Ямайка",
    "🇯🇵": "Япония",          "🇯🇴": "Иордания",
    "🇰🇿": "Казахстан",       "🇰🇪": "Кения",
    "🇰🇮": "Кирибати",        "🇰🇵": "Северная Корея",
    "🇰🇷": "Южная Корея",     "🇰🇼": "Кувейт",
    "🇰🇬": "Кыргызстан",      "🇱🇦": "Лаос",
    "🇱🇻": "Латвия",          "🇱🇧": "Ливан",
    "🇱🇸": "Лесото",          "🇱🇷": "Либерия",
    "🇱🇾": "Ливия",           "🇱🇮": "Лихтенштейн",
    "🇱🇹": "Литва",           "🇱🇺": "Люксембург",
    "🇲🇬": "Мадагаскар",      "🇲🇼": "Малави",
    "🇲🇾": "Малайзия",        "🇲🇻": "Мальдивы",
    "🇲🇱": "Мали",            "🇲🇹": "Мальта",
    "🇲🇭": "Маршалловы Острова",
    "🇲🇷": "Мавритания",      "🇲🇺": "Маврикий",
    "🇲🇽": "Мексика",         "🇫🇲": "Микронезия",
    "🇲🇩": "Молдова",         "🇲🇨": "Монако",
    "🇲🇳": "Монголия",        "🇲🇪": "Черногория",
    "🇲🇦": "Марокко",         "🇲🇿": "Мозамбик",
    "🇲🇲": "Мьянма",          "🇳🇦": "Намибия",
    "🇳🇷": "Науру",           "🇳🇵": "Непал",
    "🇳🇱": "Нидерланды",      "🇳🇿": "Новая Зеландия",
    "🇳🇮": "Никарагуа",       "🇳🇪": "Нигер",
    "🇳🇬": "Нигерия",         "🇲🇰": "Северная Македония",
    "🇳🇴": "Норвегия",        "🇴🇲": "Оман",
    "🇵🇰": "Пакистан",        "🇵🇼": "Палау",
    "🇵🇦": "Панама",          "🇵🇬": "Папуа Новая Гвинея",
    "🇵🇾": "Парагвай",        "🇵🇪": "Перу",
    "🇵🇭": "Филиппины",       "🇵🇱": "Польша",
    "🇵🇹": "Португалия",      "🇶🇦": "Катар",
    "🇷🇴": "Румыния",         "🇷🇺": "Россия",
    "🇷🇼": "Руанда",          "🇰🇳": "Сент-Китс и Невис",
    "🇱🇨": "Сент-Люсия",      "🇻🇨": "Сент-Винсент и Гренадины",
    "🇼🇸": "Самоа",           "🇸🇲": "Сан-Марино",
    "🇸🇹": "Сан-Томе и Принсипи",
    "🇸🇦": "Саудовская Аравия",
    "🇸🇳": "Сенегал",         "🇷🇸": "Сербия",
    "🇸🇨": "Сейшелы",         "🇸🇱": "Сьерра-Леоне",
    "🇸🇬": "Сингапур",        "🇸🇰": "Словакия",
    "🇸🇮": "Словения",        "🇸🇧": "Соломоновы Острова",
    "🇸🇴": "Сомали",          "🇿🇦": "ЮАР",
    "🇸🇸": "Южный Судан",     "🇪🇸": "Испания",
    "🇱🇰": "Шри-Ланка",       "🇸🇩": "Судан",
    "🇸🇷": "Суринам",         "🇸🇪": "Швеция",
    "🇨🇭": "Швейцария",       "🇸🇾": "Сирия",
    "🇹🇼": "Тайвань",         "🇹🇯": "Таджикистан",
    "🇹🇿": "Танзания",        "🇹🇭": "Таиланд",
    "🇹🇱": "Тимор-Лесте",     "🇹🇬": "Того",
    "🇹🇴": "Тонга",           "🇹🇹": "Тринидад и Тобаго",
    "🇹🇳": "Тунис",           "🇹🇷": "Турция",
    "🇹🇲": "Туркменистан",    "🇹🇻": "Тувалу",
    "🇺🇬": "Уганда",          "🇺🇦": "Украина",
    "🇦🇪": "ОАЭ",             "🇬🇧": "Великобритания",
    "🇺🇸": "США",             "🇺🇾": "Уругвай",
    "🇺🇿": "Узбекистан",      "🇻🇺": "Вануату",
    "🇻🇪": "Венесуэла",       "🇻🇳": "Вьетнам",
    "🇾🇪": "Йемен",           "🇿🇲": "Замбия",
    "🇿🇼": "Зимбабве",        "🇽🇰": "Косово",
    "🇵🇸": "Палестина",       "🇰🇾": "Каймановы острова",
    "🇬🇮": "Гибралтар",       "🇮🇲": "Остров Мэн",
    "🇯🇪": "Джерси",          "🇬🇬": "Гернси",
    "🇻🇬": "Британские Виргинские острова",
    "🇲🇶": "Мартиника",       "🇬🇵": "Гваделупа",
    "🇷🇪": "Реюньон",         "🇾🇹": "Майотта",
    "🇵🇫": "Французская Полинезия",
    "🇳🇨": "Новая Каледония",
    "🇬🇫": "Французская Гвиана",
    "🇧🇲": "Бермуды",         "🇦🇼": "Аруба",
    "🇨🇼": "Кюрасао",         "🇸🇭": "Остров Святой Елены",
}

# ==================== УТИЛИТЫ ====================

def extract_flag(text: str) -> str:
    """Извлекает эмодзи флага из начала строки."""
    m = re.match(r'^([\U0001F1E6-\U0001F1FF]{2})', text)
    return m.group(1) if m else ""

def extract_sni(line: str) -> str:
    """Извлекает sni= из строки конфига."""
    m = re.search(r'[?&]sni=([^&\s#]+)', line)
    return m.group(1) if m else ""

def parse_name(line: str) -> str:
    """Имя сервера — всё после # в конце строки."""
    if '#' in line:
        return urllib.parse.unquote(line.split('#', 1)[-1].strip())
    return ""

def set_name(line: str, name: str) -> str:
    """Вставляет новое имя сервера в строку конфига."""
    base = line.split('#', 1)[0] if '#' in line else line
    return base + '#' + urllib.parse.quote(name, safe='')

def rename_server(original_name: str, line: str) -> str:
    """
    Формирует новое имя: 🇫🇮 Финляндия [sni.example.com]
    """
    flag    = extract_flag(original_name)
    country = FLAG_TO_COUNTRY.get(flag, "Неизвестно") if flag else "Неизвестно"
    sni     = extract_sni(line)
    prefix  = f"{flag} {country}" if flag else "🌐 Неизвестно"
    return f"{prefix} [{sni}]" if sni else prefix

# ==================== ОБНОВЛЕНИЕ СЕРВЕРОВ ====================

VALID_PREFIXES = (
    'vless://', 'vmess://', 'trojan://',
    'ss://', 'ssr://', 'hysteria://',
    'hysteria2://', 'tuic://'
)

def fetch_raw_configs() -> list:
    """Скачивает сырые конфиги с GitHub."""
    result = []
    for url in SOURCES:
        try:
            log.info(f"Скачиваю: {url}")
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            lines = [l.strip() for l in r.text.splitlines() if l.strip()]
            result.extend(lines)
            log.info(f"  → получено {len(lines)} строк")
        except Exception as e:
            log.error(f"Ошибка загрузки {url}: {e}")
    return result

def process_configs(raw: list) -> list:
    """Фильтрует и переименовывает конфиги."""
    out = []
    for line in raw:
        if not line or line.startswith('#'):
            continue
        if not any(line.lower().startswith(p) for p in VALID_PREFIXES):
            continue
        original = parse_name(line)
        new_name = rename_server(original, line)
        out.append(set_name(line, new_name))
    log.info(f"Обработано валидных конфигов: {len(out)}")
    return out

def save_local(configs: list):
    """Сохраняет subscription.txt локально."""
    with open(SUBSCRIPTION_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(configs))
    log.info(f"Сохранено локально: {len(configs)} серверов")

def push_github(configs: list):
    """Пушит subscription.txt на GitHub через API."""
    if not GITHUB_TOKEN:
        log.warning("GITHUB_TOKEN не задан — только локальное сохранение")
        save_local(configs)
        return

    import base64
    api = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{SUBSCRIPTION_FILE}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    content_b64 = base64.b64encode(
        "\n".join(configs).encode('utf-8')
    ).decode('utf-8')

    # Получаем SHA существующего файла
    sha = None
    try:
        r = requests.get(api, headers=headers, timeout=15)
        if r.status_code == 200:
            sha = r.json().get('sha')
    except Exception as e:
        log.warning(f"Не удалось получить SHA: {e}")

    payload = {
        "message": "🔄 Авто-обновление серверов LAB-VPN",
        "content": content_b64,
        "branch": GITHUB_BRANCH
    }
    if sha:
        payload["sha"] = sha

    try:
        r = requests.put(api, headers=headers, json=payload, timeout=30)
        if r.status_code in (200, 201):
            log.info("✅ subscription.txt обновлён на GitHub")
        else:
            log.error(f"GitHub API ошибка {r.status_code}: {r.text[:300]}")
    except Exception as e:
        log.error(f"Ошибка push на GitHub: {e}")

    save_local(configs)

def update_servers():
    """Полный цикл обновления серверов."""
    log.info("━━━ Начало обновления серверов ━━━")
    raw = fetch_raw_configs()
    if not raw:
        log.error("Не получено ни одной строки!")
        return
    processed = process_configs(raw)
    if not processed:
        log.error("Нет валидных конфигов после обработки!")
        return
    push_github(processed)
    log.info(f"━━━ Обновление завершено: {len(processed)} серверов ━━━")

# ==================== HAPP CRYPT5 ====================

def encrypt_happ(url: str) -> str:
    """
    Шифрует ссылку через Happ Crypt5.
    Возвращает зашифрованную ссылку или оригинал при ошибке.
    """
    try:
        r = requests.post(
            "https://crypto.happ.su/api-v2.php",
            json={"url": url},
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            log.info(f"Happ API ответ: {data}")
            # Пробуем все возможные ключи ответа
            encrypted = (
                data.get("encrypted_url")
                or data.get("url")
                or data.get("result")
                or data.get("data")
                or data.get("link")
            )
            if encrypted:
                return str(encrypted)
            log.warning(f"Happ API: неизвестный формат ответа: {data}")
        else:
            log.error(f"Happ API HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log.error(f"Happ encrypt ошибка: {e}")
    return url  # fallback — возвращаем оригинал

def get_sub_link() -> str:
    """Возвращает зашифрованную ссылку на подписку."""
    return encrypt_happ(SUBSCRIPTION_URL)

# ==================== TELEGRAM БОТ ====================

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# Кэш зашифрованной ссылки чтобы не дёргать API каждый раз
_cached_link: dict = {"url": "", "ts": 0}
CACHE_TTL = 3600  # секунд

def get_cached_link() -> str:
    now = time.time()
    if not _cached_link["url"] or now - _cached_link["ts"] > CACHE_TTL:
        _cached_link["url"] = get_sub_link()
        _cached_link["ts"] = now
        log.info("Кэш ссылки обновлён")
    return _cached_link["url"]

def invalidate_cache():
    _cached_link["url"] = ""
    _cached_link["ts"] = 0

# ---- Проверка подписки ----

def is_subscribed(user_id: int) -> bool:
    """Проверяет подписку на канал(ы)."""
    channels = (
        CHANNEL_ID.split(',')
        if isinstance(CHANNEL_ID, str) and ',' in CHANNEL_ID
        else [CHANNEL_ID]
    )
    for ch in channels:
        ch = ch.strip()
        try:
            m = bot.get_chat_member(ch, user_id)
            if m.status in ('left', 'kicked', 'banned'):
                return False
        except Exception as e:
            log.error(f"Ошибка проверки {ch} для {user_id}: {e}")
            return False
    return True

# ---- Клавиатуры ----

def kb_subscribe() -> types.InlineKeyboardMarkup:
    channels = (
        CHANNEL_ID.split(',')
        if isinstance(CHANNEL_ID, str) and ',' in CHANNEL_ID
        else [CHANNEL_ID]
    )
    kb = types.InlineKeyboardMarkup(row_width=1)
    for ch in channels:
        ch = ch.strip().lstrip('@')
        kb.add(types.InlineKeyboardButton(
            text=f"📢 Подписаться на @{ch}",
            url=f"https://t.me/{ch}"
        ))
    kb.add(types.InlineKeyboardButton(
        text="✅ Я подписался — проверить",
        callback_data="check_sub"
    ))
    return kb

def kb_main() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton(
            "🔗 Получить VPN подписку",
            callback_data="get_vpn"
        ),
        types.InlineKeyboardButton(
            "📖 Как подключиться?",
            callback_data="how_to"
        ),
    )
    return kb

def kb_back() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_main"))
    return kb

# ---- Тексты ----

WELCOME = (
    "🧪 <b>LAB-VPN</b>\n"
    "<i>Бесплатно. Навсегда.</i>\n\n"
    "Привет, <b>{name}</b>! 👋\n\n"
    "Чтобы получить VPN подписку —\n"
    "подпишись на наш канал 👇"
)

WELCOME_OK = (
    "🧪 <b>LAB-VPN</b> — <i>Бесплатно. Навсегда.</i>\n\n"
    "Привет, <b>{name}</b>! 👋\n\n"
    "✅ Подписка подтверждена!\n"
    "Выбери действие 👇"
)

MAIN_MENU = (
    "🧪 <b>LAB-VPN</b> — <i>Бесплатно. Навсегда.</i>\n\n"
    "Выбери действие 👇"
)

# ---- Handlers ----

@bot.message_handler(commands=['start'])
def cmd_start(msg):
    name = msg.from_user.first_name
    log.info(f"/start от {msg.from_user.id} (@{msg.from_user.username})")
    if is_subscribed(msg.from_user.id):
        bot.send_message(
            msg.chat.id,
            WELCOME_OK.format(name=name),
            reply_markup=kb_main()
        )
    else:
        bot.send_message(
            msg.chat.id,
            WELCOME.format(name=name),
            reply_markup=kb_subscribe()
        )

@bot.message_handler(commands=['help'])
def cmd_help(msg):
    bot.send_message(
        msg.chat.id,
        (
            "🧪 <b>LAB-VPN — помощь</b>\n\n"
            "/start — главное меню\n"
            "/help — эта справка\n\n"
            "По вопросам: обратись к администратору канала"
        )
    )

# Callback: проверка подписки
@bot.callback_query_handler(func=lambda c: c.data == 'check_sub')
def cb_check_sub(call):
    if is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Подписка подтверждена!")
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=WELCOME_OK.format(name=call.from_user.first_name),
            reply_markup=kb_main()
        )
    else:
        bot.answer_callback_query(
            call.id,
            "❌ Ты ещё не подписан! Подпишись и нажми снова.",
            show_alert=True
        )

# Callback: получить VPN
@bot.callback_query_handler(func=lambda c: c.data == 'get_vpn')
def cb_get_vpn(call):
    if not is_subscribed(call.from_user.id):
        bot.answer_callback_query(
            call.id, "❌ Сначала подпишись на канал!", show_alert=True
        )
        return

    bot.answer_callback_query(call.id, "⏳ Получаю ссылку...")
    link = get_cached_link()

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=(
            "🧪 <b>LAB-VPN</b> — твоя подписка готова!\n\n"
            "🔗 <b>Ссылка на подписку:</b>\n"
            f"<code>{link}</code>\n\n"
            "📱 <b>Как добавить в HAPP:</b>\n"
            "1. Открой приложение <b>HAPP</b>\n"
            "2. Нажми <b>+</b> → <b>Добавить подписку</b>\n"
            "3. Вставь ссылку выше\n"
            "4. Нажми <b>Сохранить</b> ✅\n\n"
            "<i>🔄 Сервера обновляются каждый час автоматически.\n"
            "Просто обнови подписку в приложении.</i>"
        ),
        reply_markup=kb_back()
    )

# Callback: инструкция
@bot.callback_query_handler(func=lambda c: c.data == 'how_to')
def cb_how_to(call):
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=(
            "📖 <b>Как подключиться к LAB-VPN?</b>\n\n"
            "<b>Шаг 1.</b> Скачай приложение <b>HAPP</b>\n"
            "• <a href='https://apps.apple.com/app/happ-proxy-utility"
            "/id6476879696'>App Store (iPhone)</a>\n"
            "• <a href='https://play.google.com/store/apps/details"
            "?id=su.happ.proxy'>Google Play (Android)</a>\n\n"
            "<b>Шаг 2.</b> В боте нажми\n"
            "<b>«🔗 Получить VPN подписку»</b>\n\n"
            "<b>Шаг 3.</b> Скопируй ссылку и в HAPP:\n"
            "→ <b>+</b> → <b>Добавить подписку</b> → Вставить\n\n"
            "<b>Шаг 4.</b> Выбери сервер → Подключись 🚀\n\n"
            "<i>Сервера обновляются каждый час.\n"
            "Нажми «Обновить» в HAPP чтобы получить новые.</i>"
        ),
        reply_markup=kb_back(),
        disable_web_page_preview=True
    )

# Callback: назад
@bot.callback_query_handler(func=lambda c: c.data == 'back_main')
def cb_back(call):
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=MAIN_MENU,
        reply_markup=kb_main()
    )

# ==================== ПЛАНИРОВЩИК ====================

def run_scheduler():
    """Запускает планировщик обновления в фоновом потоке."""
    schedule.every(1).hours.do(_scheduled_update)
    log.info("⏰ Планировщик запущен (каждый час)")
    while True:
        schedule.run_pending()
        time.sleep(30)

def _scheduled_update():
    update_servers()
    invalidate_cache()  # Сбрасываем кэш после обновления

# ==================== ТОЧКА ВХОДА ====================

if __name__ == '__main__':
    log.info("🧪 LAB-VPN запускается...")

    # Первичная загрузка серверов
    log.info("📥 Первичная загрузка серверов...")
    threading.Thread(target=update_servers, daemon=True).start()

    # Планировщик в фоне
    threading.Thread(target=run_scheduler, daemon=True).start()

    # Бот
    log.info("🤖 Бот запущен!")
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            log.error(f"Ошибка polling: {e} — перезапуск через 10 сек")
            time.sleep(10)
