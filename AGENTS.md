# AGENTS.md

Telegram- и VK-викторины (aiogram 3.30 + vkbottle), курсовая работа. Windows; зависимости — только в `.venv`; Redis работает в WSL Ubuntu, не на Windows.

## Запуск и зависимости
- TG-бот: `& ".venv\Scripts\python.exe" telegram_bot.py` — только venv-интерпретатор; системные `python` (3.12) и `py` (3.14) не имеют aiogram.
- VK-бот: `& ".venv\Scripts\python.exe" vk_bot.py` — отдельный процесс; системные `python`/`py` не имеют vkbottle.
- Депенденсы: `& ".venv\Scripts\python.exe" -m pip install -r requirements.txt`
- Проверка базы вопросов: `python -c "from questions import load_questions; print(len(load_questions()))"` → ~302 000.
- Рабочая директория важна: пути `quiz-questions/`, `.questions_cache.pkl`, `.env` — относительные. Запускать из корня репо.

## Redis (нужен до тестов бота)
- Живёт в WSL Ubuntu, из Windows доступен на `127.0.0.1:6379` (localhost-форвардинг WSL2).
- Поднять: `wsl -d Ubuntu` → `sudo service redis-server start` → `wsl redis-cli ping` (→ PONG).
- Клиент ленивый: упавший Redis не ломает старт, а лишь первый `set/get`.
- TG хранит состояние в FSM (aiogram RedisStorage, ключи `fsm:*`); текущий вопрос лежит в FSM-данных, не в `quiz:{user_id}`. VK хранит текущий вопрос в `vk_quiz:{user_id}` с TTL 1 час (`QUESTION_TTL`). Смотреть: `wsl redis-cli --scan --pattern '*quiz:*'` / `GET vk_quiz:<id>`.
- Статический тип `get()` у `redis.asyncio` — `bytes | str | None`, даже с `decode_responses=True` (это runtime-флаг). Байты декодировать до использования как ключ словаря, иначе type-checker ругается. В `vk_bot.py` декодирование вынесено в `get_active_question()`.

## Клиент Redis (`db.py`)
- Единственный источник создания клиента: `create_redis_client(decode_responses=False) -> redis.asyncio.Redis`.
- Параметры (`REDIS_HOST`/`REDIS_PORT`/`REDIS_PASSWORD`) читаются из `.env` один раз на уровне модуля через `dotenv_values(".env")` (`_config`).
- `decode_responses=True` использует только VK-бот; TG-клиент — дефолт.
- `redis_client` в обоих бота — синглтон уровня модуля; соединение не поднимать в хендлерах.

## Пользовательские тексты (`messages.py`)
- Все user-facing строки — константы здесь: `NO_ACTIVE_QUESTION`, `UNKNOWN_QUESTION`, `GREETING_NO_QUESTION`, `SCORE_ZERO`, функция `correct_answer_message(answer)`.
- Тексты не дублировать в `telegram_bot.py`/`vk_bot.py`; править только в `messages.py`.
- Строки ответов «Правильно!»/«Неправильно...» живут в `answer_utils.evaluate_answer` — они тоже user-facing, но связаны с логикой сравнения.

## Файлы вопросов (`quiz-questions/`)
- В gitignore — локальные, не в репо. Если папки нет, `QUESTIONS` будет пустым — бот молчит без краха.
- Кодировка KOI8-R (`open(..., encoding="koi8-r")`).
- Секции делятся пустой строкой (`\n\n`); ярлык `Вопрос N` начинает вопрос, `Ответ` привязывает его; `Автор`/`Источник`/`Комментарий`/`Зачет`/`Тур`/`Дата` игнорируются.
- `load_questions()` на верхнем уровне ничего не печатает — импорт безопасен.

## `questions.py` (библиотека, нет `__main__`)
- `load_questions()` парсит `quiz-questions/*.txt` в `dict[str, str]` (вопрос → ответ) и пишет pickle-кэш `.questions_cache.pkl` (в gitignore).
- Кэш валиден по сигнатуре `имя:размер:mtime_ns` всех `*.txt`; изменился любой файл → перепарс. Битый кэш → перепарс. Атомарная запись через `.tmp` + `os.replace` (безопасно при двух процессах).
- Первый запуск ~10-11 с (парс), последующие — доли секунды (load из pickle).
- `random_question()` возвращает случайный вопрос из кэшированного списка ключей — НЕ вызывать `random.choice(list(QUESTIONS))` (это O(n) на 302k ключей, ~18 мс вместо ~0.001 мс).

## Соглашения `telegram_bot.py`
- `redis_client` — синглтон уровня модуля; соединение не поднимать в хендлерах. `QUESTIONS` загружается в `main()` через `load_questions(args.questions_dir)` (флаг `--questions-dir`), не модульный синглтон.
- Правило курса: `load_dotenv()` остаётся внутри `main()`; на уровне модуля env не читать — этим занимается `db.py`.
- aiogram 3.30 удалил фильтр `Text` → магические фильтры: `from aiogram import F`, `F.text == "..."`.
- Порядок хендлеров: `CommandStart` и конкретные `F.text == ...` раньше; catch-all `@router.message()` (проверка ответа) — последним.
- `message.from_user` типизирован `User | None` — guard перед `.id`.
- Меню — `ReplyKeyboardMarkup(is_persistent=True)`; схлопывание при вводе — UX клиента Telegram, не баг.
- Guard токена `if not token: raise ValueError(...)` перед `Bot(token=...)`.

## Общая логика ответов (`answer_utils.py`)
- `evaluate_answer(user_text, correct_text) -> tuple[bool, str]` — единственный источник сравнения ответов. Возвращает `(is_correct, текст_для_пользователя)`. Используется и в `telegram_bot.py`, и в `vk_bot.py`; логику нормализации/лемматизации нигде не дублировать.
- `normalize_answer(text)` — lstrip, обрезка по `.`/`(`, лемматизация pymorphy3. Импорт pymorphy3 прикрыт `# type: ignore[import-untyped]`.

## Соглашения `vk_bot.py` (vkbottle)
- Отдельный процесс-близнец `telegram_bot.py`: та же логика, другая библиотека. FSM у VK нет — состояние в Redis-ключе `vk_quiz:{user_id}`.
- Чтение активного вопроса — только через `get_active_question(peer_id) -> str | None` (декод-гвард `raw.decode() if isinstance(raw, bytes) else raw` внутри). В хендлерах после `if question is None: return` использовать `QUESTIONS[question]` (не `QUESTIONS.get`, иначе тип `str | None`).
- Ключи `vk_quiz:{user_id}` ставить с `ex=QUESTION_TTL` (3600 с) — без TTL копятся в Redis вечно.
- vkbottle API: `Bot(token)`; хендлеры `@bot.on.message(text="...")` (конкретные) и `@bot.on.message()` (catch-all, последним); `Keyboard(inline=False).add(Text(...)).row()` из `vkbottle.tools`; `await bot.run_polling()` — корутина; `message.answer(text, keyboard=kb)`.
- Клавиатура `kb` — на всех ответах (включая «Активного вопроса нет...» и приветствие `GREETING_NO_QUESTION`), кнопки в 3 ряда через `.row()`.
- Не называть переменную в хендлере именем соседнего хендлера (shadowing): в «Сдаться» вопрос — `next_question`, не `new_question`.
- Правильный ответ — `await redis_client.delete(vk_key(message.peer_id))` (зеркало `set_state(waiting_for_question)` у TG); «Сдаться» — показ ответа + сразу новый вопрос.
- `load_dotenv()` внутри `main()`; токен `VK_GROUP_TOKEN` из `.env` с guard `if not token: raise ValueError(...)`.

## VK-группа (нюансы, встреченные вживую)
- Long Poll у группы должен отдавать событие `message_new` (`groups.getLongPollSettings` → `events.message_new`), иначе бот подключён, но молчит. Включить через API `groups.setLongPollSettings(group_id, message_new=1, ...)` или в UI группы.
- Отправка клавиатуры требует опции «Возможности ботов» в настройках группы, иначе `VKAPIError_912`.
- Один токен = один поллер; VK-группа отдаёт апдейты только одному Long Poll-соединению.

## Git
- Стиль коммитов: короткие lowercase-английские (`add button menu`, `store current question in redis`).
- `.env` в gitignore; `.env.example` — шаблон.
- В gitignore: `*.log`, `.vkbottle/`, `.questions_cache.pkl` (+ `.tmp`).
- TG и VK — два независимых процесса (`telegram_bot.py` и `vk_bot.py`) на разных токенах. Внутри одного токена — строго один поллер; два поллера на один токен дают флаки-апдейты.

## Проверка типов
- Файлов конфига mypy нет. Редакторский mypy/Pylance может гонять системный Python и ругаться `import-not-found: aiogram` — это шум окружения. Реальный сигнал — mypy из venv.
- Pylance и mypy расходятся на `redis.asyncio`: Pylance видит `get()` как `bytes | str | None` и ругается на `QUESTIONS[question]`/`evaluate_answer(correct_text: str)`; mypy (авторитетный сигнал) проходит после декод-гварда (сейчас он в `get_active_question()`). Ориентируйтесь на mypy из venv.
- flake8: коды в `# noqa` чувствительны к регистру — пишите `# noqa: W503` (заглавными), `w503` не сработает.