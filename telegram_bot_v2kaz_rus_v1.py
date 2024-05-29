import asyncio
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.session import aiohttp
from aiogram.filters import CommandStart
from aiogram.dispatcher.router import Router
from aiogram.types import InlineKeyboardButton, Message, InlineKeyboardMarkup, CallbackQuery
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
    if language == 'ru':
        await callback_query.message.answer("Здравствуйте! Отправьте мне, пожалуйста, голосовое сообщение с названием одного препарата (допустимые к демонстрации препараты: Ибупрофен, Анальгин, Аспирин, Кызыл май).\nТакже посмотреть демонстрационное видео можно по этой ссылке:\nhttps://youtube.com/shorts/CLDUrzblecI?feature=share")
    elif language == 'kk':
        await callback_query.message.answer('Сәлеметсіз бе! Маған бір дәрі-дәрмектің атауы бар дауыстық хабарлама жіберіңіз (демонстрацияға рұқсат етілген дәрілік нұсқалар: ибупрофен, анальгин, аспирин, қызыл май).\nСонымен қатар демонстрациялық бейнені мына сілтемеден көре аласыз:\nhttps://youtube.com/shorts/CLDUrzblecI?feature=share')
    await callback_query.answer()


@router.message(F.voice)
async def handle_voice_message(message: types.Message):
    user_id = message.from_user.id
    user_language = user_languages.get(user_id, 'ru')

    voice_file_id = message.voice.file_id
    file_info = await bot.get_file(voice_file_id)
    file_url = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'

    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as response:
            if response.status == 200:
                file_content = await response.read()
                logger.info("File downloaded successfully.")
            else:
                logger.error(f"Failed to download file: HTTP status {response.status}")
                return

    try:
        speech_text = recognize_speech(file_content)
        response_text = await process_question(speech_text)
        logger.info(f"Response text from GPT: {response_text}")

        if response_text.lower().strip() in ['кызылмай', 'кызыл май', 'аспирин', 'анальгин', 'ибупрофен']:
            if response_text.lower().strip() == 'кызылмай' or response_text.lower().strip() == 'кызыл май':
                api_response = fetch_medicine_info('75c9de5e-0669-41b0-b07b-d6d545c6711a')
            elif response_text.lower().strip() == 'аспирин':
                api_response = fetch_medicine_info('ba5e98ee-12e0-4dac-9730-d15f67d51942')
            elif response_text.lower().strip() == 'анальгин':
                api_response = fetch_medicine_info('100311')
            elif response_text.lower().strip() == 'ибупрофен':
                api_response = fetch_medicine_info('37025703-0b63-4c4a-bdf7-2a40cd8cc236')
            else:
                api_response = {}

            if api_response:
                formatted_response = format_response(api_response)
                logger.info(f"Formatted response for synthesis: {formatted_response}")

                if user_language == 'kk':
                    formatted_response = translate_text(formatted_response, 'ru', 'kk')
                logger.info(f"Formatted response for synthesis: {formatted_response}")

                audio_response_bytes = synthesize_speech(formatted_response, user_language)

                mp3_audio_path = "response.mp3"
                with open(mp3_audio_path, "wb") as mp3_audio_file:
                    mp3_audio_file.write(audio_response_bytes)

                try:
                    await message.answer_voice(voice=types.FSInputFile(mp3_audio_path), caption=formatted_response)
                    logger.info("Voice response sent successfully.")
                except Exception as e:
                    logger.error(f"Failed to send voice response: {e}")
                    await message.answer("Failed to send the voice response.")
                finally:
                    if os.path.exists(mp3_audio_path):
                        os.remove(mp3_audio_path)
                        logger.info(f"Deleted file {mp3_audio_path}.")
            else:
                await message.answer(text='К сожалению, данное лекарство не найдено.\n Пожалуйста, отправьте еще раз голосовое сообщение с названием одного из препаратов (допустимые к демонстрации препараты: Ибупрофен, Анальгин, Аспирин, Кызыл май)')
        else:
            if user_language == 'kk':
                await message.answer(
                    text='Демонстрацияның бір бөлігі ретінде келесі қолайлы дәрі атауларының бірін қамтитын сөйлемді айтыңыз: ибупрофен, аспирин, анальгин, қызыл май.\nСонымен қатар демонстрациялық бейнені мына сілтемеден көре аласыз:\nhttps://youtube.com/shorts/CLDUrzblecI?feature=share')
            else:
                await message.answer(
                    text='В рамках демонстрации произнесите предложение, содержащее одно из следующих подходящих названий лекарств: ибупрофен, аспирин, анальгин, кызыл май.\nВы также можете посмотреть демонстрационное видео по этой ссылке:\nhttps://youtube.com/shorts/CLDUrzblecI?feature=share')

    except Exception as e:
        logger.error(f"Failed to send voice: {e}")
        if user_language == 'kk':
            await message.answer(
                text='Техникалық себептерге байланысты сұрау өңделмеді.\nАлайда демонстрациялық бейнені мына сілтемеден көре аласыз:\nhttps://youtube.com/shorts/CLDUrzblecI?feature=share')
        else:
            await message.answer(
                text='Запрос не был обработан по техническим причинам.\nОднако посмотреть демонстрационное видео можно по этой ссылке:\nhttps://youtube.com/shorts/CLDUrzblecI?feature=share')


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
