# Nebula Support AI — тестове завдання OBRIO (AI Ops Specialist)

Два інструменти для команди Support продукту Nebula:

1. **Ticket classifier** (Task 1): текст тікета → категорія, пріоритет, наступний крок, `needs_human` + черга Review queue для людини.
2. **Agent assistant** (Task 2): тікет → summary, три чернетки відповіді (formal / empathetic / short), цитати з бази знань, позначка «потрібне рішення агента».

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

Застосунок працює й без ключів для вкладки **Evaluation** (читає збережені результати з `eval/results/`) і для кнопок-прикладів (відповіді моделей закешовані в `.cache/llm/`, це реальні відповіді з прогонів).

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
src/cost.py             вартість
prompts/                classifier_v1..v4.md, assistant_v1..v2.md
data/                   tickets_eval.jsonl (30), tickets_holdout.jsonl (10), assistant_eval.jsonl (10), kb/*.md (18)
eval/                   run_eval.py, compare_models.py, run_assistant_eval.py, cost_report.py,
                        simulate_failures.py, fetch_prices.py, results/
tests/                  pytest: сценарії збоїв + guards
```

## Моделі

| роль | модель | провайдер |
|---|---|---|
| основна (Task 1 і 2) | `gemini-3.5-flash-lite` | Google AI Studio (free tier) |
| fallback 1 | `openai/gpt-oss-120b` | Groq (free tier) |
| fallback 2 / порівняння | `gemini-3.8-flash`, `gemini-3.6-flash`, `openai/gpt-oss-20b`, `nvidia/nemotron-3-ultra-550b-a55b:free` | Google / Groq / OpenRouter |

Код відмовляється викликати на OpenRouter будь-яку модель без суфікса `:free` (`src/llm.py`).
