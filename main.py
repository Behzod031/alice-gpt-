import asyncio
import json
import traceback
from fastapi import FastAPI, Request
import openai
import os
from dotenv import load_dotenv
import uvicorn
import openai_async
# Загрузка переменных из файла .env
load_dotenv()

app = FastAPI()
# История чата
chat_history = []

# Устанавливаем API-ключ OpenAI
openai.api_key = ""

# Слова для активации Алисы и GPT
ALICE_WORDS = ['Алиса', 'алиса']
GPT_WORDS = ['GPT', 'gpt', 'Charos', 'charos']

@app.post("/post")
async def post(request: Request):
    """Обработка запроса от Яндекс Алисы"""
    try:
        request_data = await request.json()
        response = {
            'session': request_data.get('session', {}),
            'version': request_data.get('version', '1.0'),
            'response': {
                'end_session': False
            }
        }
        await handle_dialog(response, request_data)
        return response
    except Exception as e:
        print('Ошибка обработки запроса:', e)
        return {
            'response': {
                'text': 'Произошла ошибка на сервере. Попробуйте снова позже.'
            },
            'version': '1.0',
            'session': {}
        }

async def handle_dialog(res, req):
    """Определяем, с кем говорить: с Алисой или с GPT"""
    user_message = req['request']['original_utterance'].strip()

    # Определяем, кого вызвал пользователь
    if any(user_message.lower().lstrip().startswith(word) for word in ALICE_WORDS):
        request_text = user_message[len('Алиса'):].strip()
        res['response']['text'] = f"Это стандартный ответ от Алисы на запрос: {request_text}"
    elif any(user_message.lower().lstrip().startswith(word) for word in GPT_WORDS):
        parts = user_message.split(maxsplit=1)
        request_text = parts[1] if len(parts) > 1 else ''
        if request_text:
            chat_history.append({"role": "user", "content": request_text})
            reply = chat_with_gpt(request_text)
            res['response']['text'] = reply
        else:
            res['response']['text'] = 'Вы не задали вопрос для GPT.'
    else:
        res['response']['text'] = 'Привет! Скажите "Алиса" или "Charos" в начале, чтобы задать вопрос.'

async def ask_gpt(request):
    """Запрос к ChatGPT для обработки текста"""
    try:
        response = await openai_async.chat_complete(openai.api_key, timeout=25,
                                                    payload={
                                                        'model': 'gpt-4o',
                                                        "messages": [{'role': 'user',
                                                                      "content":request
                                                                      }],
                                                    })
        print(response.json())
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print('Ошибка GPT:', e)
        return 'Не удалось получить ответ от GPT'


def save_chat_history(file_path='chat_history.json'):
    """
    Сохраняет историю чата в JSON файл.

    Аргументы:
    file_path (str): путь к файлу для сохранения
    """
    try:
        with open(file_path, 'a', encoding='utf-8') as file:
            data = json.dumps(chat_history)
            file.write(data)
        print(f"История чата успешно сохранена в {file_path}")
    except Exception as e:
        print(f"Ошибка при сохранении истории: {e}")


def load_chat_history(file_path='chat_history.json'):
    """
    Загружает историю чата из JSON файла.

    Аргументы:
    file_path (str): путь к файлу для загрузки
    """
    global chat_history
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            chat_history = json.load(file)
        print(f"История чата успешно загружена из {file_path}")
    except FileNotFoundError:
        print(f"Файл {file_path} не найден. Начало новой истории чата.")
        chat_history = []
    except Exception as e:
        print(f"Ошибка при загрузке истории: {e}")


def chat_with_gpt(user_message):
    """
    Отправляет сообщение пользователя и сохраняет ответ в истории.

    Аргументы:
    user_message (str): сообщение пользователя

    Возврат:
    str: ответ от ChatGPT
    """
    # Добавляем сообщение пользователя в историю
    chat_history.append({"role": "user", "content": user_message})

    try:
        # Отправляем запрос к OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=chat_history
        )
        print (response)
        # Получаем текст ответа от API
        assistant_message = response.choices[0].message.content
        # Добавляем ответ ассистента в историю
        chat_history.append({"role": "assistant", "content": assistant_message})

        return assistant_message
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return "Ошибка при запросе к API."












# Загрузка истории чата при запуске
load_chat_history()

uvicorn.run(app=app, host='0.0.0.0', port=4040)
