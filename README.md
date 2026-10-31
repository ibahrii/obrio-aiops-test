# Nebula Support AI — тестове завдання OBRIO (AI Ops Specialist)

Два інструменти для команди Support продукту Nebula:

1. **Ticket classifier** (Task 1): текст тікета → категорія, пріоритет, наступний крок, `needs_human` + черга Review queue для людини.
2. **Agent assistant** (Task 2): тікет → summary, три чернетки відповіді (formal / empathetic / short), цитати з бази знань, позначка «потрібне рішення агента».
3. **API і вебхук-маршрутизація** (FastAPI): вебхук нового тікета з CRM (Zendesk / Intercom) → класифікація → P1 у Telegram, `needs_human` у Review queue, решта в CRM (симуляція CSV). Ідемпотентно за `ticket_id`.
4. **PII-маскування:** email, телефони, картки й імена замінюються на `[EMAIL]` `[PHONE]` `[CARD]` `[NAME]` до будь-якого виклику LLM.

📄 Звіт: [`REPORT.md`](REPORT.md) · еволюція промптів: [`PROMPT_LOG.md`](PROMPT_LOG.md) · шпаргалка: [`DECISIONS.md`](DECISIONS.md) · результати: [`eval/results/`](eval/results/)

> **Усі дані синтетичні.** Тікети, база знань (`data/kb/`, 18 статей) і політики (наприклад, «14 днів на повернення») вигадані для демо й не відображають реальних правил OBRIO/Nebula. Використовуються лише безкоштовні API.

## Швидкий старт (локально)

```bash
python -m venv .venv && source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

```bash
cp .env.example .env   # впишіть GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY
```

```bash
set -a && source .env && set +a && streamlit run app.py
```

Без ключів працює вкладка **Evaluation** (читає збережені результати з `eval/results/`) і частина кнопок-прикладів, чиї відповіді вже лежать у кеші `.cache/llm/` (це реальні відповіді з прогонів). Для решти прикладів і для власних тікетів потрібні ключі.

## API і вебхуки

```bash
set -a && source .env && set +a && uvicorn src.api:app --port 8000
```

Інтерактивна документація: http://localhost:8000/docs.

| ендпоінт | тіло |
|---|---|
| `POST /webhook/ticket` | вебхук Zendesk `{"ticket": {"id", "subject", "description", "requester": {"name", "email"}}}`, Intercom `{"type": "notification_event", "data": {"item": {"id", "source": {"body", "author"}}}}` або `{"ticket_id", "text"}` |
| `POST /classify` | `{"text": "...", "requester_name": "необов'язково"}` → класифікація + `masked_text` (що реально пішло в модель) |
| `POST /assist` | `{"text": "..."}` → summary, три чернетки, цитати |
| `GET /health` | стан сервісу |

Приклад вебхука у форматі Zendesk:

```bash
curl -s localhost:8000/webhook/ticket -H 'Content-Type: application/json' -d '{"ticket": {"id": 1001, "subject": "Charged twice", "description": "Two charges of $29.99 on card 4111 1111 1111 1111. Regards, Oliver Bennett", "requester": {"name": "Oliver Bennett", "email": "oliver@example.com"}}}'
```

Повторіть ту саму команду: відповідь буде `"duplicate": true`, без повторного виклику LLM і без другого сповіщення.

**Маршрутизація:** P1 → Telegram (або рядок у `logs/notifications.log`, якщо змінних немає) · `needs_human` → `data/runtime/review_queue.jsonl` (кнопка «Load tickets queued by the webhook API» у Streamlit) · решта → `data/runtime/crm_tickets.csv`. Стан ідемпотентності — `data/runtime/router.sqlite`. Каталог `data/runtime/` не комітиться, шлях змінюється через `ROUTER_STATE_DIR`.

Необов'язкові змінні оточення (є в `.env.example`):
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — сповіщення про P1;
- `WEBHOOK_SECRET` — перевірка HMAC-підпису вебхука (Zendesk `X-Zendesk-Webhook-Signature`, Intercom `X-Hub-Signature` або `X-Signature`).

End-to-end демо: 5 тікетів по HTTP + повторна доставка, з реальними викликами LLM. Результат — [`eval/results/webhook_demo.md`](eval/results/webhook_demo.md):

```bash
python eval/webhook_demo.py
```

## Деплой на Streamlit Community Cloud

1. Запушити репозиторій на GitHub.
2. На [share.streamlit.io](https://share.streamlit.io) → **Create app** → вибрати репозиторій, гілку, файл `app.py`.
3. **Advanced settings → Secrets** — вставити (формат як у `.streamlit/secrets.toml.example`):
   ```toml
   GEMINI_API_KEY = "..."
   GROQ_API_KEY = "..."
   OPENROUTER_API_KEY = "..."
   ```
4. Deploy. Ключі читаються з env або `st.secrets` (`src/config.py:get_api_key`) і ніколи не логуються.

## Відтворення результатів

Усі відповіді моделей кешуються на диск (ключ = hash тексту + модель + версія промпту + версія KB), тому повторний прогін нічого не коштує й не витрачає ліміти.

```bash
python eval/run_eval.py --model gemini-flash-lite --prompt v4                 # Task 1, 30 тікетів
```

```bash
python eval/run_eval.py --model gemini-flash-lite --prompt v4 --dataset holdout
```

```bash
python eval/compare_models.py --run groq-gpt-oss-120b --holdout               # порівняння моделей
```

```bash
python eval/run_assistant_eval.py --model gemini-flash-lite --prompt v2       # Task 2
```

```bash
python eval/cost_report.py && python eval/simulate_failures.py && python -m pytest -q
```

```bash
bash eval/run_all.sh   # усе разом лише з кешу (без API-викликів)
```

## Структура

```
app.py                  Streamlit: Classifier (+ Review queue) · Agent Assistant · Evaluation
src/config.py           моделі (ID взяті з /models API), ціни, ліміти, версії промптів, поріг confidence
src/schemas.py          pydantic-схеми виходу
src/llm.py              клієнти Gemini / Groq / OpenRouter, retry, timeout, 429, fallback, кеш, токени
src/cache.py            дисковий кеш (sha256-ключ, TTL, версіонування)
src/classifier.py       Task 1
src/guards.py           HITL-правила, маршрутизація, injection/crisis-детект, перевірка цитат, довжина, мова
src/retrieval.py        BM25 + буст за категорією + розширення запиту
src/assistant.py        Task 2
src/pii.py              маскування PII перед викликами LLM
src/router.py           парсинг вебхуків, ідемпотентність, P1 → Telegram, needs_human → черга, решта → CSV
src/api.py              FastAPI: /webhook/ticket, /classify, /assist
src/cost.py             вартість
prompts/                classifier_v1..v4.md, assistant_v1..v2.md
data/                   tickets_eval.jsonl (30), tickets_holdout.jsonl (10), assistant_eval.jsonl (10), kb/*.md (18)
eval/                   run_eval.py, compare_models.py, run_assistant_eval.py, cost_report.py,
                        simulate_failures.py, fetch_prices.py, webhook_demo.py, results/
tests/                  pytest: сценарії збоїв, guards, PII, API
```

## Моделі

| роль | модель | провайдер |
|---|---|---|
| основна (Task 1 і 2) | `gemini-3.5-flash-lite` | Google AI Studio (free tier) |
| fallback 1 | `openai/gpt-oss-120b` | Groq (free tier) |
| fallback 2 / порівняння | `gemini-3.8-flash`, `gemini-3.6-flash`, `openai/gpt-oss-20b`, `nvidia/nemotron-3-ultra-550b-a55b:free` | Google / Groq / OpenRouter |

Код відмовляється викликати на OpenRouter будь-яку модель без суфікса `:free` (`src/llm.py`).
