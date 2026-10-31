# Model comparison: classifier prompt `v4` (fallback off)

| model | measured | category | priority | both | holdout both | needs_human | valid JSON 1st try | API p50 / p95, s | wall p50 / p95, s | tokens in / out | $/ticket | $/10k |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Gemini 3.8 Flash | 5/30 | 100.0% | 100.0% | 100.0% | - | 100.0% | 100.0% | 48.328 / 57.258 | 119.455 / 166.548 | 1956 / 129 | 0.001951 | 19.51 |
| Gemini 3.6 Flash | 30/30 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 3.611 / 14.779 | 4.921 / 41.764 | 1964 / 169 | 0.002107 | 21.07 |
| Gemini 3.5 Flash-Lite | 30/30 | 100.0% | 100.0% | 100.0% | 100.0% | 86.7% | 100.0% | 1.419 / 1.584 | 1.422 / 1.585 | 1964 / 167 | 0.001008 | 10.08 |
| GPT-OSS-120B (Groq) | 30/30 | 100.0% | 90.0% | 90.0% | 80.0% | 93.3% | 100.0% | 1.177 / 1.454 | 17.39 / 19.519 | 2300 / 252 | 0.000496 | 4.96 |
| GPT-OSS-20B (Groq) | 30/30 | 96.7% | 80.0% | 80.0% | 70.0% | 83.3% | 100.0% | 0.911 / 1.086 | 17.338 / 18.831 | 2300 / 198 | 0.000232 | 2.32 |
| Nemotron 3 Ultra 550B (OpenRouter :free) | 30/30 | 96.7% | 96.7% | 93.3% | 100.0% | 96.7% | 100.0% | 6.61 / 15.79 | 6.611 / 15.791 | 1962 / 448 | 0.001966 | 19.66 |

Prices: public paid tier per 1M tokens (input / output), from `pricing_snapshot.json`:

- Gemini 3.8 Flash (`gemini-3.8-flash`): $0.75 / $3.75
- Gemini 3.6 Flash (`gemini-3.6-flash`): $0.75 / $3.75
- Gemini 3.5 Flash-Lite (`gemini-3.5-flash-lite`): $0.3 / $2.5
- GPT-OSS-120B (Groq) (`openai/gpt-oss-120b`): $0.15 / $0.6
- GPT-OSS-20B (Groq) (`openai/gpt-oss-20b`): $0.075 / $0.3
- Nemotron 3 Ultra 550B (OpenRouter :free) (`nvidia/nemotron-3-ultra-550b-a55b:free`): $0.5 / $2.2

API latency = HTTP time of the successful call. Wall latency also includes retries and Retry-After waits caused by free-tier limits (e.g. Groq 8000 TPM), so it reflects the free tier, not the model.

Gemini 3.8 / 3.6 Flash were measured with a 60 s request timeout (LLM_TIMEOUT_S=60) from two free-tier Google projects (20 requests/day/model each); all other models with the default 20 s. A row with measured < total covers only the tickets that got an answer, so its accuracy is not directly comparable with fully measured rows.
