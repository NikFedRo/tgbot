import os
import asyncio
from typing import Optional, Set, List, Dict
import time
import re

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from pathlib import Path
from pyrogram import Client as PyroClient, filters as pyro_filters


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-3.5-turbo-16k"
SYSTEM_PROMPT = (
    "Ты — редактор новостного экономического телеграм-канала. Пиши краткие и интересные новости для аудитории мужчин 20-35 лет."
    "1.Стиль: разговорный с элементами официального. Простой и плавный текст. Начинай с самых важных моментов (до 10 слов)."
    "2.Структура:"
    "Начало — главное."
    "Источник: «сообщают СМИ» (если нет конкретного источника)."
    "Подробности и мнения экспертов (если есть)."
    "Заверши итогом или дополнительной информацией."
    "3.Ключевые слова:"
    "Используй активные глаголы и фразы: предложили, начнут, обяжут, будут, заявили, В России, в Госдуме и т.д."
    #"Ты редактор новостного экономического Telegram-канала.\n"
    #"Аудитория — мужчины 20–35 лет.\n"
    #Поэтому пиши новости по следующим настройкам: "
    #"\n\n"
    #"Самое главное, не добавлять слова и факты, которых нет в тексте.\n"
    #"Если в тексте имеется источник или кто-то что-то сообщил или заявил, то пиши это в конец первого предложения"
    #"1) Стиль и тон: пиши новости в разговорном и немного в официально-деловом стиле. Пиши емко и кратко в зависимости от запроса. Делай упор на самые важные и интересные моменты. Используй легкие и простые фразы, чтобы текст был плавным и читался легко. Также вначале до 10 слов используй самые важные моменты из новости, чтобы при уведомлениях читатель заинтересовался новостью."
    #"2) Структура новости: вначале самое главное/захватывающее, а кто это сообщил или заявил или источник в конце предложения. Если же нет источника или человека кто это заявил/сообщил, то пиши просто «сообщают СМИ». Далее пиши про подробности и пояснения, мнения экспертов (если есть). В конце завершай небольшим итогом или другими второстепенно важными моментами. Пиши новости в основном без тире и без заголовков, но если это прям необходимо и стиль новости, который я тебе прислал позволяет, то можешь написать с ними. Также старайся, чтобы слова не повторялись, особенно если новость небольшая."
    #"3) Ключевые слова или «Новостные слова»: используй глаголы по типу - начали; предложили; подняли; будут и тому подобные глаголы. Также используй словосочетания по типу - начали массово; россиянка; В России; россияне; по его словам; В Москве; В Питере; рекордные; впервые; внезапно; считают эксперты; запретят; заблокируют; обяжут; В Госдуме; ЦБ и тому подобные словосочетания, для большего упора и вовлеченности. "
    #"\n\n"
    #"Вот идеальные примеры новостей по стилю, на которые тебе нужно ориентироваться с учетом наших запросов:"
    #"\n\n"
    #"1) В России с 2026 года начнут штрафовать за оплату криптовалютой. В Госдуме заявили, что соответствующий законопроект планируют принять уже этой осенью. Вся крипта, использованная в незаконных платежах, будет подлежать конфискации, а штрафы составят от 100 тысяч рублей для физлиц и от 700 тысяч рублей для юрлиц. Сейчас россияне нередко используют криптовалюту для оплаты видеоигр, онлайн-курсов и даже получают в ней зарплату. Всё это окажется под запретом."
    #"\n\n"
    #"2) В Россию могут начать массово завозить кубинских врачей и медсестёр, сообщил главный экономист ВЭБ Андрей Клепач. Он отметил, что до недавнего времени от 20 до 40 тыс. кубинских медиков работали в странах Латинской Америки и Африки, но многие вернулись на Кубу из-за геополитических конфликтов. Клепач считает их приглашение в Россию правильным решением."
)


def clean_text(text: str) -> str:
    """Удаляет теги Telegram-каналов и другие служебные символы из текста"""
    # Удаляем теги каналов (@username)
    text = re.sub(r'@\w+', '', text)
    # Удаляем лишние пробелы
    text = re.sub(r'\s+', ' ', text)
    # Удаляем пробелы в начале и конце
    return text.strip()

def build_paraphrase_prompt(text: str, source: Optional[str] = None, extra_style: Optional[str] = None) -> str:
    style_line = f"\n\nДополнительные указания стиля:\n{extra_style}" if extra_style else ""
    
    return (
            #"Переформулируй новость так, чтобы она звучала естественно и грамотно, "
            #"но без добавления новых деталей.\n\n"
            #"Требования:\n"
            #"1. Сохрани весь смысл, даты, имена, суммы и факты.\n"
            #"2. Не добавляй ничего от себя, не изменяй факты.\n"
            #"3. Разрешается менять порядок предложений, если это делает текст логичнее.\n"
            #"4. Исправь повторы, тяжёлые обороты и неестественные конструкции.\n"
            f"Текст для переформулирования:\n{text}{style_line}"
        )

def _openrouter_request_sync(prompt: str, api_key: str, app_url: Optional[str]) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-Title": "NewsBot",
    }
    if app_url:
        headers["HTTP-Referer"] = app_url

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 400,
        "seed": 7
    }

    # Попробуем разные URL эндпоинты
    urls_to_try = [
        "https://openrouter.ai/api/v1/chat/completions",
        "https://openrouter.co/v1/chat/completions",
        "https://openrouter.ai/api/v1/chat/completions"
    ]

    max_retries = 4
    backoff = 2.0
    
    for url in urls_to_try:
        for attempt in range(max_retries):
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=60)
                if r.status_code == 429:
                    retry_after = r.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else backoff * (2 ** attempt)
                    time.sleep(min(wait, 30))
                    continue
                r.raise_for_status()
                data = r.json()
                content = data["choices"][0]["message"]["content"].strip()
                if not content:
                    print(f"[OpenRouter] Empty response from {url}")
                    continue
                return content
            except requests.exceptions.RequestException as e:
                print(f"[OpenRouter] URL {url} failed: {e}")
                if attempt == max_retries - 1:
                    break
                time.sleep(backoff * (2 ** attempt))
        else:
            # Если этот URL сработал, выходим из цикла
            break

    raise RuntimeError("OpenRouter недоступен после попыток с разными URL")


async def paraphrase(text: str, source: Optional[str], api_key: str, app_url: Optional[str], extra_style: Optional[str]) -> str:
    # Очищаем текст от тегов каналов и служебных символов
    cleaned_text = clean_text(text)
    prompt = build_paraphrase_prompt(cleaned_text, source, extra_style)
    result = await asyncio.to_thread(_openrouter_request_sync, prompt, api_key, app_url)
    
    # Если результат пустой, возвращаем исходный текст с пометкой
    if not result or not result.strip():
        return f"[Ошибка API] {cleaned_text}"
    
    # Добавляем информацию об источнике, если он указан
    if source:
        result = f"{result}\n\nТекст из: {source}"
    
    return result


def resolve_target_chat_id(default_chat_id: Optional[int] = None) -> Optional[int]:
    dest_user = os.getenv("DEST_USER_ID")
    if dest_user:
        try:
            return int(dest_user)
        except ValueError:
            pass
    target_chat = os.getenv("TARGET_CHAT_ID")
    if target_chat:
        try:
            return int(target_chat)
        except ValueError:
            pass
    return default_chat_id


async def can_send_to(bot, chat_id: int) -> bool:
    try:
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        return True
    except Exception as e:
        print(f"[Bot] cannot send to {chat_id}: {e}")
        return False


def ptb_media_suffix(msg) -> str:
    try:
        has_photo = bool(getattr(msg, "photo", None))
        has_video = bool(getattr(msg, "video", None) or getattr(msg, "animation", None))
        if has_photo and has_video:
            return " (есть изображение и видео)"
        if has_video:
            return " (есть видео)"
        if has_photo:
            return " (есть изображение)"
    except Exception:
        pass
    return ""


def pyro_media_suffix(message) -> str:
    try:
        has_photo = bool(getattr(message, "photo", None))
        has_video = bool(getattr(message, "video", None) or getattr(message, "animation", None))
        if has_photo and has_video:
            return " (есть изображение и видео)"
        if has_video:
            return " (есть видео)"
        if has_photo:
            return " (есть изображение)"
    except Exception:
        pass
    return ""


def get_style_for_chat(app: Application, chat_id: int) -> Optional[str]:
    styles: Dict[int, str] = app.bot_data.get("style_by_chat", {})
    return styles.get(chat_id)


def set_style_for_chat(app: Application, chat_id: int, text: Optional[str]) -> None:
    styles: Dict[int, str] = app.bot_data.setdefault("style_by_chat", {})
    if text:
        styles[chat_id] = text.strip()
    else:
        styles.pop(chat_id, None)


def set_last_input_for_chat(app: Application, chat_id: int, text: str, source: Optional[str]) -> None:
    app.bot_data.setdefault("last_input_by_chat", {})[chat_id] = {"text": text, "source": source}


def get_last_input_for_chat(app: Application, chat_id: int) -> Optional[Dict[str, Optional[str]]]:
    store: Dict[int, Dict[str, Optional[str]]] = app.bot_data.get("last_input_by_chat", {})
    return store.get(chat_id)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = (
        "Привет! Пришли текст новости или ответь командой /paraphrase на сообщение, "
        "и я переформулирую его. Также можно настроить стиль: /style <указания>.\n"
        "Для правки последнего результата используйте: /revise <как изменить>."
    )
    await update.effective_chat.send_message(msg)


async def cmd_me(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id if update.effective_user else None
    await update.effective_chat.send_message(f"Ваш user_id: {uid}")


async def cmd_style(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text = " ".join(context.args).strip() if context.args else None
    if text:
        set_style_for_chat(context.application, chat_id, text)
        await update.effective_chat.send_message("Стиль обновлён.")
    else:
        cur = get_style_for_chat(context.application, chat_id)
        await update.effective_chat.send_message(cur or "Стиль не задан. Установите: /style <текст>")


async def cmd_revise(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    instr = " ".join(context.args).strip() if context.args else None
    if not instr:
        await update.effective_chat.send_message("Укажите указания: /revise <как изменить>")
        return
    last = get_last_input_for_chat(context.application, chat_id)
    if not last:
        await update.effective_chat.send_message("Нет сохранённого текста. Сначала получите пересказ или пришлите текст.")
        return
    api_key = os.getenv("OPENROUTER_API_KEY")
    app_url = os.getenv("APP_URL")
    if not api_key:
        await update.effective_chat.send_message("OPENROUTER_API_KEY не задан.")
        return
    base_style = get_style_for_chat(context.application, chat_id)
    extra = (base_style + "\n\n" if base_style else "") + f"Правки редактора: {instr}"
    try:
        result = await paraphrase(last["text"] or "", last.get("source"), api_key, app_url, extra)
        if not result or not result.strip():
            await update.effective_chat.send_message("Получен пустой ответ от API. Попробуйте другую модель или проверьте настройки.")
            return
    except Exception as e:
        await update.effective_chat.send_message(f"Ошибка правки: {e}")
        return
    await update.effective_chat.send_message(result)


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = resolve_target_chat_id()
    if chat_id is None:
        await update.effective_chat.send_message("Целевой чат не задан (DEST_USER_ID/TARGET_CHAT_ID).")
        return
    ok = await can_send_to(context.bot, chat_id)
    await update.effective_chat.send_message("ОК: могу писать." if ok else "НЕТ: не могу писать. Проверьте, что вы нажали /start боту или права в канале.")


async def cmd_paraphrase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api_key = os.getenv("OPENROUTER_API_KEY")
    app_url = os.getenv("APP_URL")
    if not api_key:
        await update.effective_chat.send_message("OPENROUTER_API_KEY не задан.")
        return

    text: Optional[str] = None
    source: Optional[str] = None

    if update.message and update.message.reply_to_message:
        text = update.message.reply_to_message.text or update.message.reply_to_message.caption
    if not text:
        text = " ".join(context.args).strip() if context.args else None

    if not text:
        await update.effective_chat.send_message(
            "Использование: ответьте командой /paraphrase на сообщение или передайте текст аргументом."
            "\n\n"
             "Переформулируй новость так, чтобы она звучала естественно и грамотно, "
            "но без добавления новых деталей.\n\n"
            "Требования:\n"
            "1. Сохрани весь смысл, даты, имена, суммы и факты.\n"
            "2. Не добавляй ничего от себя, не изменяй факты.\n"
            "3. Разрешается менять порядок предложений, если это делает текст логичнее.\n"
            "4. Исправь повторы, тяжёлые обороты и неестественные конструкции.\n"
            "5. Используй нейтральный деловой стиль — короткие, чёткие предложения.\n"          
        )
        return

    try:
        extra_style = get_style_for_chat(context.application, update.effective_chat.id)
        result = await paraphrase(text, source, api_key, app_url, extra_style)
        if not result or not result.strip():
            await update.effective_chat.send_message("Получен пустой ответ от API. Попробуйте другую модель или проверьте настройки.")
            return
    except Exception as e:
        await update.effective_chat.send_message(f"Ошибка переформулирования: {e}")
        return

    await update.effective_chat.send_message(result)
    set_last_input_for_chat(context.application, update.effective_chat.id, text, source)


async def on_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api_key = os.getenv("OPENROUTER_API_KEY")
    app_url = os.getenv("APP_URL")
    if not api_key:
        return

    msg = update.effective_message
    post_text = None
    if msg:
        post_text = getattr(msg, "text", None) or getattr(msg, "caption", None)
    if not post_text:
        return

    source = msg.chat.title if getattr(msg, "chat", None) else None
    try:
        extra_style = get_style_for_chat(context.application, resolve_target_chat_id(default_chat_id=msg.chat_id) or msg.chat_id)
        result = await paraphrase(post_text, source, api_key, app_url, extra_style)
        if not result or not result.strip():
            print(f"[Channel] Empty response from API for chat {msg.chat_id}")
            return
    except Exception:
        return

    suffix = ptb_media_suffix(msg)
    if suffix:
        result = f"{result}{suffix}"

    chat_id = resolve_target_chat_id(default_chat_id=msg.chat_id)
    if chat_id is None:
        return
    if not await can_send_to(context.bot, chat_id):
        return
    await context.bot.send_message(chat_id=chat_id, text=result)
    set_last_input_for_chat(context.application, chat_id, post_text, source)


async def start_pyrogram_monitor(application: Application) -> None:
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    watch_raw = os.getenv("WATCH_CHANNELS", "").strip()
    if not api_id or not api_hash or not watch_raw:
        print("[Pyrogram] skip monitor: missing TELEGRAM_API_ID/API_HASH/WATCH_CHANNELS")
        return

    try:
        api_id_int = int(api_id)
    except ValueError:
        print("[Pyrogram] invalid TELEGRAM_API_ID")
        return

    def normalize(u: str) -> str:
        u = u.strip()
        if not u:
            return u
        u = u.replace("https://t.me/", "").replace("http://t.me/", "")
        if u.startswith("@"):
            u = u[1:]
        return u

    usernames = [normalize(x) for x in watch_raw.split(",") if normalize(x)]
    if not usernames:
        print("[Pyrogram] no valid WATCH_CHANNELS")
        return

    session = os.getenv("PYROGRAM_SESSION", "pyrogram")
    pyro = PyroClient(name=session, api_id=api_id_int, api_hash=api_hash)

    await pyro.start()
    print("[Pyrogram] started session", session)

    watched_ids: Set[int] = set()
    for u in usernames:
        try:
            try:
                await pyro.join_chat(u)
                print(f"[Pyrogram] joined @{u}")
            except Exception as e_join:
                print(f"[Pyrogram] join @{u} skip/err: {e_join}")
            chat = await pyro.get_chat(u)
            watched_ids.add(chat.id)
            print(f"[Pyrogram] watching @{u} -> id {chat.id}")
        except Exception as e:
            print(f"[Pyrogram] failed to resolve @{u}: {e}")

    if not watched_ids:
        print("[Pyrogram] no channels resolved, monitor disabled")
        await pyro.stop()
        return

    id_list: List[int] = list(watched_ids)

    @pyro.on_message(pyro_filters.channel)
    async def on_new_message(client, message):
        try:
            chat_id = getattr(message.chat, 'id', None)
            if chat_id not in watched_ids:
                return
            text = getattr(message, "text", None) or getattr(message, "caption", None)
            has_suffix = pyro_media_suffix(message)
            print(f"[Pyrogram] on_message chat={chat_id} has_text={bool(text)}")
            if not text:
                return
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                return
            app_url = os.getenv("APP_URL")
            source = message.chat.title if getattr(message, "chat", None) else None
            try:
                extra_style = get_style_for_chat(application, resolve_target_chat_id() or chat_id)
                result = await paraphrase(text, source, api_key, app_url, extra_style)
            except Exception as inner_e:
                print(f"[Pyrogram] paraphrase error: {inner_e}")
                return
            if has_suffix:
                result = f"{result}{has_suffix}"
            out_chat_id = resolve_target_chat_id()
            if out_chat_id and await can_send_to(application.bot, out_chat_id):
                try:
                    await application.bot.send_message(chat_id=int(out_chat_id), text=result)
                    set_last_input_for_chat(application, out_chat_id, text, source)
                except Exception as send_e:
                    print(f"[Pyrogram] send error: {send_e}")
        except (ValueError, KeyError) as peer_e:
            print(f"[Pyrogram] Peer error (channel may be deleted): {peer_e}")
            # Удаляем канал из списка отслеживаемых
            if hasattr(message, 'chat') and hasattr(message.chat, 'id'):
                watched_ids.discard(message.chat.id)
        except Exception as outer_e:
            print(f"[Pyrogram] handler error: {outer_e}")

    @pyro.on_edited_message(pyro_filters.channel)
    async def on_edited_message(client, message):
        try:
            chat_id = getattr(message.chat, 'id', None)
            if chat_id not in watched_ids:
                return
            text = getattr(message, "text", None) or getattr(message, "caption", None)
            has_suffix = pyro_media_suffix(message)
            print(f"[Pyrogram] on_edited chat={chat_id} has_text={bool(text)}")
            if not text:
                return
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                return
            app_url = os.getenv("APP_URL")
            source = message.chat.title if getattr(message, "chat", None) else None
            try:
                extra_style = get_style_for_chat(application, resolve_target_chat_id() or chat_id)
                result = await paraphrase(text, source, api_key, app_url, extra_style)
            except Exception as inner_e:
                print(f"[Pyrogram] paraphrase error: {inner_e}")
                return
            if has_suffix:
                result = f"{result}{has_suffix}"
            out_chat_id = resolve_target_chat_id()
            if out_chat_id and await can_send_to(application.bot, out_chat_id):
                try:
                    await application.bot.send_message(chat_id=int(out_chat_id), text=result)
                    set_last_input_for_chat(application, out_chat_id, text, source)
                except Exception as send_e:
                    print(f"[Pyrogram] send error: {send_e}")
        except (ValueError, KeyError) as peer_e:
            print(f"[Pyrogram] Edited message peer error (channel may be deleted): {peer_e}")
            # Удаляем канал из списка отслеживаемых
            if hasattr(message, 'chat') and hasattr(message.chat, 'id'):
                watched_ids.discard(message.chat.id)
        except Exception as outer_e:
            print(f"[Pyrogram] edited handler error: {outer_e}")

    application.bot_data["pyrogram_client"] = pyro
    application.bot_data["pyrogram_watch_ids"] = watched_ids
    print("[Pyrogram] monitor ready; handlers registered for ids:", id_list)

    async def poll_fallback():
        last_id_by_chat: Dict[int, int] = {}
        while True:
            try:
                for cid in list(watched_ids):
                    try:
                        # Проверяем, доступен ли канал
                        try:
                            await pyro.get_chat(cid)
                        except (ValueError, KeyError) as e:
                            print(f"[Fallback] Channel {cid} no longer accessible: {e}")
                            watched_ids.discard(cid)  # Удаляем из списка отслеживаемых
                            continue
                        
                        async for msg in pyro.get_chat_history(cid, limit=1):
                            mid = msg.id
                            if last_id_by_chat.get(cid) == mid:
                                continue
                            last_id_by_chat[cid] = mid
                            text = getattr(msg, "text", None) or getattr(msg, "caption", None)
                            if not text:
                                continue
                            suffix = pyro_media_suffix(msg)
                            print(f"[Pyrogram/Fallback] fetched chat={cid} mid={mid}")
                            api_key = os.getenv("OPENROUTER_API_KEY")
                            if not api_key:
                                continue
                            app_url = os.getenv("APP_URL")
                            source = msg.chat.title if getattr(msg, "chat", None) else None
                            try:
                                extra_style = get_style_for_chat(application, resolve_target_chat_id() or cid)
                                result = await paraphrase(text, source, api_key, app_url, extra_style)
                            except Exception as inner_e:
                                print(f"[Fallback] paraphrase error: {inner_e}")
                                continue
                            if suffix:
                                result = f"{result}{suffix}"
                            out_chat_id = resolve_target_chat_id()
                            if out_chat_id and await can_send_to(application.bot, out_chat_id):
                                try:
                                    await application.bot.send_message(chat_id=int(out_chat_id), text=result)
                                    set_last_input_for_chat(application, out_chat_id, text, source)
                                except Exception as send_e:
                                    print(f"[Fallback] send error: {send_e}")
                    except (ValueError, KeyError) as peer_e:
                        print(f"[Fallback] Channel {cid} no longer accessible: {peer_e}")
                        watched_ids.discard(cid)
                    except Exception as one_e:
                        print(f"[Fallback] history error for {cid}: {one_e}")
            except Exception as loop_e:
                print(f"[Fallback] loop error: {loop_e}")
            await asyncio.sleep(30)

    application.bot_data["pyrogram_fallback_task"] = asyncio.create_task(poll_fallback())


async def after_init(application: Application) -> None:
    await start_pyrogram_monitor(application)
    try:
        dest = resolve_target_chat_id()
        if dest:
            ok = await can_send_to(application.bot, dest)
            print(f"[Bot] send-permission to {dest}: {'OK' if ok else 'NO'}")
        else:
            print("[Bot] no DEST_USER_ID/TARGET_CHAT_ID set for send-permission check")
    except Exception as e:
        print(f"[Bot] send-permission check error: {e}")


async def ignore_status_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Игнорирует обновления статуса (например, новые участники, удаления сообщений и т.д.)"""
    pass


def main() -> None:
    script_dir_env = Path(__file__).with_name('.env')
    load_dotenv(dotenv_path=script_dir_env)
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан в окружении")

    application = Application.builder().token(token).post_init(after_init).build()

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("me", cmd_me))
    application.add_handler(CommandHandler("style", cmd_style))
    application.add_handler(CommandHandler("revise", cmd_revise))
    application.add_handler(CommandHandler("check", cmd_check))
    application.add_handler(CommandHandler("paraphrase", cmd_paraphrase))
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL & filters.ALL, on_channel_post))
    application.add_handler(MessageHandler(filters.StatusUpdate.ALL, ignore_status_update))

    try:
        application.run_polling(allowed_updates=["message", "channel_post", "edited_channel_post"])
    except Exception as e:
        print(f"[Bot] Fatal error: {e}")
        print("[Bot] Restarting in 10 seconds...")
        time.sleep(10)
        main() 


if __name__ == "__main__":
    main()


