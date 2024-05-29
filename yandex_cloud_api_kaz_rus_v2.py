# import requests
# import os
# from dotenv import load_dotenv
# import logging
#
# from telegram_bot_v2kaz_rus import get_iam_token
#
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
#
# load_dotenv()
# YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
# YANDEX_OAUTH_TOKEN = os.getenv("YANDEX_OAUTH_TOKEN")
# YANDEX_IAM_TOKEN = None
# # YANDEX_IAM_TOKEN = os.getenv("YANDEX_IAM_TOKEN")
#
# def recognize_speech(audio_content):
#     if not YANDEX_IAM_TOKEN:
#         get_iam_token()
#     url = f"https://stt.api.cloud.yandex.net/speech/v1/stt:recognize?folderId={YANDEX_FOLDER_ID}&lang=ru-RU"
#     headers = {"Authorization": f"Bearer {YANDEX_IAM_TOKEN}"}
#
#     logger.info(f"Sending {len(audio_content)} bytes to Yandex STT.")
#
#     response = requests.post(url, headers=headers, data=audio_content)
#     if response.status_code == 200:
#         result = response.json().get("result")
#         logger.info(f"Recognition result: {result}")
#         return result
#     else:
#         error_message = f"Failed to recognize speech, status code: {response.status_code}"
#         logger.error(error_message)
#         raise Exception(error_message)
#
#
# def synthesize_speech(text):
#     if not YANDEX_IAM_TOKEN:
#         get_iam_token()
#     url = 'https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize'
#     headers = {'Authorization': f'Bearer {YANDEX_IAM_TOKEN}'}
#     data = {
#         'text': text,
#         'lang': 'kk-KK',
#         'voice': 'amira',
#         'folderId': YANDEX_FOLDER_ID,
#         'format': 'mp3',
#         'sampleRateHertz': 48000,
#     }
#
#     response = requests.post(url, headers=headers, data=data, stream=True)
#     logger.info(f"Status Code: {response.status_code}")
#     logger.info(f"Response Headers: {response.headers}")
#
#     if response.status_code == 200:
#         audio_content = response.content
#         logger.info(f"Received audio content length: {len(audio_content)} bytes")
#         with open("response.mp3", "wb") as file:
#             file.write(audio_content)
#         logger.info("Audio content saved as 'response.mp3'.")
#         return audio_content
#     else:
#         error_message = f"Failed to synthesize speech, status code: {response.status_code}, response text: {response.text}"
#         logger.error(error_message)
#         raise Exception(error_message)
