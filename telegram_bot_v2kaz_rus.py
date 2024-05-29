import asyncio
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.session import aiohttp
from aiogram.filters import CommandStart
from aiogram.dispatcher.router import Router
from aiogram.types import InlineKeyboardButton, Message, InlineKeyboardMarkup, CallbackQuery, InputFile, FSInputFile
from dotenv import load_dotenv
import os
import re
import logging

from openai_gpt import process_question

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_OAUTH_TOKEN = os.getenv("YANDEX_OAUTH_TOKEN")
# YANDEX_IAM_TOKEN = os.getenv("YANDEX_IAM_TOKEN")

bot = Bot(token=BOT_TOKEN, parse_mode='HTML')
dp = Dispatcher()
router = Router()

YANDEX_IAM_TOKEN = None


def get_iam_token():
    global YANDEX_IAM_TOKEN
    url = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
    payload = {"yandexPassportOauthToken": YANDEX_OAUTH_TOKEN}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    YANDEX_IAM_TOKEN = response.json()["iamToken"]
    logger.info(f"Received new IAM token: {YANDEX_IAM_TOKEN}")

async def refresh_iam_token():
    while True:
        await asyncio.sleep(6 * 3600)
        get_iam_token()
        logger.info("IAM token refreshed")

def fetch_medicine_info(sku):
    """Отправка запроса к API для получения данных о лекарстве."""
    url = 'https://prod-backoffice.daribar.com/api/v1/products/search?city=%D0%90%D0%BB%D0%BC%D0%B0%D1%82%D1%8B'
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9,ru;q=0.8',
        'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjdXN0b21lciI6ZmFsc2UsImV4cCI6MTcxNTcwODM0NiwibmFtZSI6IiIsInBob25lIjoiNzc3NzU4NDY5NjEiLCJyZWZyZXNoIjpmYWxzZSwicm9sZSI6ImFkbWluIiwic2Vzc2lvbl9pZCI6IjE0MGE4ZTg3LWQzZTctNGE4Yi1iODE1LTEyZjE2YjBiZGU0NiJ9.JI2N8d93qDcH5sTOOI0bAo3aRJcjK02ZsMjez_Xd3wQ',
        'content-type': 'application/json',
        'origin': 'https://daribar.kz',
        'referer': 'https://daribar.kz/'
    }
    data = f'[{{"sku":"{sku}","count_desired":1}}]'
    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()


@router.message(CommandStart())
async def process_start_command(message: Message):
    """Send a message when the command /start is issued."""
    rus_button = InlineKeyboardButton(text="Русский", callback_data="set_lang_ru")
    kaz_button = InlineKeyboardButton(text="Қазақ", callback_data="set_lang_kk")
    markup = InlineKeyboardMarkup(inline_keyboard=[[rus_button],
                     [kaz_button]])
    markup.row_width = 2

    await message.answer("Выберите язык / Тілді таңдаңыз:", reply_markup=markup)


user_languages = {}


@router.callback_query(F.data.in_(['set_lang_ru', 'set_lang_kk']))
async def set_language(callback_query: CallbackQuery):
    """Handle language selection."""
    user_id = callback_query.from_user.id
    language = callback_query.data.split('_')[-1]
    user_languages[user_id] = language
    if language == 'kk':
        mp3_audio_path = "sample2.mp3"

        await callback_query.message.answer_voice(voice=FSInputFile(mp3_audio_path), caption="Сәлеметсіз бе! Егер бүгін басыңыз ауырса, оның қашан басталғанын және қашан аяқталғанын айтып беріңізші?")
    elif language == 'ru':
        await callback_query.message.answer('Здравствуйте! Посмотреть демонстрационное видео можно по этой ссылке:\n https://youtube.com/shorts/VtFKszTH1rs?feature=share')
    await callback_query.answer()


@router.message(F.voice)
async def handle_voice_message(message: types.Message):
    mp3_audio_path = "rakhmet.mp3"

    await message.answer_voice(voice=types.FSInputFile(mp3_audio_path), caption="Өтінішіңізге рахмет, жауабыңыз жазылды")





@router.message()
async def handle_any_message(message: Message):
    user_id = message.from_user.id
    user_language = user_languages.get(user_id, 'ru')
    if user_language == 'kk':
        await message.answer(text="Маған бір дәрі-дәрмектің атауы бар дауыстық хабарлама жіберіңіз (демонстрацияға рұқсат етілген дәрілік нұсқалар: ибупрофен, анальгин, аспирин, қызыл май).\nСонымен қатар демонстрациялық бейнені мына сілтемеден көре аласыз:\nhttps://youtube.com/shorts/CLDUrzblecI?feature=share")
    else:
        await message.answer(
            text="Отправьте мне, пожалуйста, голосовое сообщение с названием одного препарата (допустимые к демонстрации препараты: Ибупрофен, Анальгин, Аспирин, Кызыл май).\nТакже посмотреть демонстрационное видео можно по этой ссылке:\nhttps://youtube.com/shorts/CLDUrzblecI?feature=share")


def format_response(data):
    results = []
    for item in data['result'][:3]:
        pharmacy_info = f"Препарат {item['products'][0]['name']}\nАдрес:\nгород {item['source']['city']},\n{item['source']['address']}\nCтоимость препарата {item['products'][0]['base_price']} тенге\n"
        results.append(pharmacy_info)
    return "\n".join(results)


def remove_annotations(text: str) -> str:
    pattern = r'(\[\[.*?\]\])|(\【[^】]*\】)'
    cleaned_text = re.sub(pattern, '', text)
    return cleaned_text


def translate_text(text, source_lang='ru', target_lang='kk'):
    url = "https://translate.api.cloud.yandex.net/translate/v2/translate"
    headers = {
        'Authorization': f'Bearer {YANDEX_IAM_TOKEN}',
        'Content-Type': 'application/json'
    }
    payload = {
        'folder_id': YANDEX_FOLDER_ID,
        'texts': [text],
        'targetLanguageCode': target_lang,
        'sourceLanguageCode': source_lang
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        translations = response.json().get('translations', [])
        if translations:
            return translations[0]['text']
        else:
            return "Перевод не найден."
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err}")
        return "Перевод не удался."
    except Exception as err:
        logging.error(f"An error occurred: {err}")
        return "Перевод не удался."


def recognize_speech(audio_content):
    global YANDEX_IAM_TOKEN
    url = f"https://stt.api.cloud.yandex.net/speech/v1/stt:recognize?folderId={YANDEX_FOLDER_ID}&lang=ru-RU"
    headers = {"Authorization": f"Bearer {YANDEX_IAM_TOKEN}"}

    logger.info(f"Sending {len(audio_content)} bytes to Yandex STT.")
    response = requests.post(url, headers=headers, data=audio_content)
    response.raise_for_status()

    if response.status_code == 200:
        result = response.json().get("result")
        logger.info(f"Recognition result: {result}")
        return result
    else:
        error_message = f"Failed to recognize speech, status code: {response.status_code}"
        logger.error(error_message)
        raise Exception(error_message)


def synthesize_speech(text, lang_code):
    voice_settings = {
        'ru': {'lang': 'ru-RU', 'voice': 'oksana'},
        'kk': {'lang': 'kk-KK', 'voice': 'amira'}
    }
    settings = voice_settings.get(lang_code, voice_settings['ru'])

    url = 'https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize'
    headers = {'Authorization': f'Bearer {YANDEX_IAM_TOKEN}'}
    data = {
        'text': text,
        'lang': settings['lang'],
        'voice': settings['voice'],
        'folderId': YANDEX_FOLDER_ID,
        'format': 'mp3',
        'sampleRateHertz': 48000,
    }

    response = requests.post(url, headers=headers, data=data, stream=True)
    logger.info(f"Status Code: {response.status_code}")
    logger.info(f"Response Headers: {response.headers}")

    if response.status_code == 200:
        audio_content = response.content
        logger.info(f"Received audio content length: {len(audio_content)} bytes")
        with open("response.mp3", "wb") as file:
            file.write(audio_content)
        logger.info("Audio content saved as 'response.mp3'.")
        return audio_content
    else:
        error_message = f"Failed to synthesize speech, status code: {response.status_code}, response text: {response.text}"
        logger.error(error_message)
        raise Exception(error_message)


dp.include_router(router)


async def main():
    get_iam_token()
    task = asyncio.create_task(refresh_iam_token())
    _ = task
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
