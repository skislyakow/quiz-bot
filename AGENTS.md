# AGENTS.md

Telegram-викторина (aiogram 3.30), курсовая работа. Windows; зависимости — только в `.venv`; Redis работает в WSL Ubuntu, не на Windows.

## Запуск и зависимости
- Бот: `& ".venv\Scripts\python.exe" telegram_bot.py` — только venv-интерпретатор; системные `python` (3.12) и `py` (3.14) не имеют aiogram.
- Депенденсы: `& ".venv\Scripts\python.exe" -m pip install -r requirements.txt`
- `questions.py` — только библиотека (нет `__main__`); проверка: `python -c "from questions import load_questions; print(len(load_questions()))"` → ~302 000.
- Рабочая директория важна: пути `quiz-questions/`, `.env`, `dotenv_values(".env")` — относительные. Запускать из корня репо.

## Redis (нужен до тестов бота)
- Живёт в WSL Ubuntu, из Windows доступен на `127.0.0.1:6379` (localhost-форвардинг WSL2).
- Поднять: `wsl -d Ubuntu` → `sudo service redis-server start` → `wsl redis-cli ping` (→ PONG).
- Клиент ленивый: упавший Redis не ломает старт, а лишь первый `set/get`.
- Ключ `quiz:{user_id}` хранит текущий вопрос. Смотреть: `wsl redis-cli GET quiz:<id>` / `--scan --pattern 'quiz:*'`.
- Статический тип `get()` у `redis.asyncio` — `bytes | str | None`, даже с `decode_responses=True` (это runtime-флаг). Байты декодировать до использования как ключ словаря, иначе type-checker ругается.

## Файлы вопросов (`quiz-questions/`)
- В gitignore — локальные, не в репо. Если папки нет, `QUESTIONS` будет пустым — бот молчит без краха.
- Кодировка KOI8-R (`open(..., encoding="koi8-r")`).
- Секции делятся пустой строкой (`\n\n`); ярлык `Вопрос N` начинает вопрос, `Ответ` привязывает его; `Автор`/`Источник`/`Комментарий`/`Зачет`/`Тур`/`Дата` игнорируются.
- `load_questions()` на верхнем уровне ничего не печатает — импорт безопасен.

## Соглашения `telegram_bot.py`
- `redis_client` и `QUESTIONS` — синглтоны уровня модуля; соединение не поднимать в хендлерах.
- Правило курса: `load_dotenv()` остаётся внутри `main()`; на уровне модуля читать env через `dotenv_values(".env")` (`_config`).
- aiogram 3.30 удалил фильтр `Text` → магические фильтры: `from aiogram import F`, `F.text == "..."`.
- Порядок хендлеров: `CommandStart` и конкретные `F.text == ...` раньше; catch-all `@router.message()` (проверка ответа) — последним.
- `message.from_user` типизирован `User | None` — guard перед `.id`.
- Меню — `ReplyKeyboardMarkup(is_persistent=True)`; схлопывание при вводе — UX клиента Telegram, не баг.
- Guard токена `if not token: raise ValueError(...)` перед `Bot(token=...)`.

## Git
- Стиль коммитов: короткие lowercase-английские (`add button menu`, `store current question in redis`).
- `.env` в gitignore; `.env.example` — шаблон.
- Запускать строго один процесс бота — два поллера на один токен дают флаки-апдейты.

## Проверка типов
- Файлов конфига mypy нет. Редакторский mypy/Pylance может гонять системный Python и ругаться `import-not-found: aiogram` — это шум окружения. Реальный сигнал — mypy из venv.