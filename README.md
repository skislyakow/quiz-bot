# Quiz Bot

[![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram-Bot%20API-26A5E4?logo=telegram&logoColor=white)](https://core.telegram.org/bots/api)
[![VK API](https://img.shields.io/badge/VK-API-0077FF?logo=vk&logoColor=white)](https://vk.com/dev)
[![aiogram](https://img.shields.io/badge/aiogram-3.30-2C2D33?logo=telegram&logoColor=white)](https://aiogram.dev)
[![vkbottle](https://img.shields.io/badge/vkbottle-4.10-0077FF?logo=vk&logoColor=white)](https://vkbottle.readthedocs.io)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

Викторина в Telegram и ВКонтакте на базе базы из ~302 000 вопросов. Курсовая работа.

## Демо

<!-- Положи запись диалога с ботом в assets/demo.gif (5-10 сек) -->
![Демо диалога с ботом](assets/demo.gif)

## Попробовать

Боты поднимаются локально (см. «Быстрый старт»). Публичных экземпляров нет.

## Что умеет бот

Бот задаёт случайные вопросы викторины и проверяет ответы в Telegram и ВКонтакте:

- присылает случайный вопрос по кнопке «Новый вопрос»;
- показывает правильный ответ по кнопке «Сдаться» и сразу даёт новый вопрос;
- показывает счёт по кнопке «Мой счёт»;
- понимает разные формулировки: ответ нормализуется (лемматизация через pymorphy3, обрезка по точке/скобке, игнор пунктуации), допускается вхождение ответа как подстроки (от 3 символов);
- хранит активный вопрос в состоянии (FSM у Telegram, Redis у ВКонтакте).

Если активного вопроса нет, бот просит нажать «Новый вопрос».

## Как реализовано

Telegram- и VK-боты — **два независимых процесса** (`telegram_bot.py` и `vk_bot.py`) на разных токенах. Общая логика вынесена в модули:

- `questions.py` — парсинг базы вопросов и `random_question()` (случайный вопрос из закэшированного списка ключей, без O(n) на 302k элементов);
- `answer_utils.py` — `evaluate_answer()` (единственный источник сравнения ответов) и `normalize_answer()`;
- `db.py` — создание Redis-клиента (`create_redis_client`);
- `messages.py` — все пользовательские строки.

Состояние:
- **Telegram** — FSM (aiogram `RedisStorage`, ключи `fsm:*`);
- **ВКонтакте** — Redis-ключ `vk_quiz:{user_id}` с TTL 1 час (`QUESTION_TTL`).

### Используемые инструменты

| Инструмент | Зачем |
|------------|-------|
| **aiogram** | Telegram Bot API (3.30) |
| **vkbottle** | Long Poll API ВКонтакте (4.10) |
| **redis** | Хранение FSM-состояния TG и активного вопроса VK |
| **pymorphy3** | Лемматизация ответов при сравнении |
| **python-dotenv** | Загрузка переменных окружения из `.env` |

## Быстрый старт

1. Скопировать `.env.example` в `.env` и заполнить токены:

   ```
   TELEGRAM_BOT_TOKEN=токен_от_@BotFather
   VK_GROUP_TOKEN=токен_группы_ВК
   REDIS_HOST=127.0.0.1
   REDIS_PORT=6379
   REDIS_PASSWORD=
   ```

   `.env` добавлен в `.gitignore` и не попадёт в репозиторий.

2. Создать виртуальное окружение и поставить зависимости:

   ```bash
   python -m venv .venv
   .venv\Scripts\Activate.ps1          # Windows (PowerShell)
   # source .venv/bin/activate          # Linux/macOS
   pip install -r requirements.txt
   ```

3. (Опционально) Положить файлы базы вопросов в папку `quiz-questions/` (кодировка KOI8-R, `*.txt`). Без неё бот запустится, но будет молчать — `QUESTIONS` будет пустым. Первый запуск парсит базу и пишет кэш `.questions_cache.pkl` (~10–11 с); дальше — доли секунды.

## Запуск

### Redis (нужен до старта ботов)

Redis поднят в WSL Ubuntu и доступен из Windows на `127.0.0.1:6379`:

```bash
wsl -d Ubuntu
sudo service redis-server start
wsl redis-cli ping        # -> PONG
```

Клиент ленивый: упавший Redis не ломает старт бота, а лишь первый `set`/`get`.

### Telegram бот

> Запускать строго из корня репозитория (пути `.env`, `quiz-questions/`, кэш — относительные).

```bash
.venv\Scripts\python.exe telegram_bot.py
```

### VK бот

Отдельный процесс. Для работы нужно:
- включить Long Poll у группы (событие `message_new`);
- выдать боту права «Возможности ботов» (иначе отправка клавиатуры даст `VKAPIError_912`);
- один токен = один поллер (не запускайте два поллера на один токен — будут флакающие апдейты).

```bash
.venv\Scripts\python.exe vk_bot.py
```

## Переменные окружения

| Переменная | Назначение |
|------------|------------|
| `TELEGRAM_BOT_TOKEN` | Токен Telegram-бота от @BotFather |
| `VK_GROUP_TOKEN` | Токен группы ВКонтакте |
| `REDIS_HOST` | Хост Redis (по умолчанию `127.0.0.1`) |
| `REDIS_PORT` | Порт Redis (по умолчанию `6379`) |
| `REDIS_PASSWORD` | Пароль Redis (пусто, если нет) |

## Полезные команды

```bash
# Проверить базу вопросов
python -c "from questions import load_questions; print(len(load_questions()))"   # -> ~302000

# Посмотреть активный вопрос VK в Redis
wsl redis-cli --scan --pattern '*quiz:*'
wsl redis-cli GET vk_quiz:<user_id>
```

## Файлы проекта

| Файл | Назначение |
|------|------------|
| `telegram_bot.py` | Telegram бот (aiogram, FSM) |
| `vk_bot.py` | VK бот (vkbottle longpoll) |
| `questions.py` | Парсинг базы вопросов и `random_question()` |
| `answer_utils.py` | `normalize_answer()` и `evaluate_answer()` |
| `db.py` | Создание Redis-клиента |
| `messages.py` | Пользовательские строки |
| `quiz-questions/` | База вопросов (KOI8-R, `*.txt`) — в `.gitignore` |
| `.questions_cache.pkl` | Кэш базы вопросов — в `.gitignore` |
| `.env.example` | Шаблон переменных окружения |
| `requirements.txt` | Зависимости (закреплены версии) |

## Лицензия

[MIT](LICENSE)
