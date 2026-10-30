# Model comparison — classifier prompt `v4` (fallback off)

| model | category | priority | both | holdout both | needs_human | valid JSON 1st try | API p50 / p95, s | wall p50 / p95, s | tokens in / out | $/ticket | $/10k |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Gemini 3.5 Flash-Lite | 96.7% | 100.0% | 96.7% | 100.0% | 90.0% | 100.0% | 1.419 / 1.584 | 1.422 / 1.585 | 1964 / 167 | 0.001008 | 10.08 |
| Nemotron 3 Ultra 550B (OpenRouter :free) | 93.3% | 96.7% | 90.0% | 100.0% | 93.3% | 100.0% | 6.61 / 15.79 | 6.611 / 15.791 | 1962 / 448 | 0.001966 | 19.66 |

Prices: public paid tier per 1M tokens (input / output), from `pricing_snapshot.json`:

- Gemini 3.5 Flash-Lite (`gemini-3.5-flash-lite`): $0.3 / $2.5
- Nemotron 3 Ultra 550B (OpenRouter :free) (`nvidia/nemotron-3-ultra-550b-a55b:free`): $0.5 / $2.2

API latency = HTTP time of the successful call. Wall latency also includes retries and Retry-After waits caused by free-tier limits (e.g. Groq 8000 TPM), so it reflects the free tier, not the model.
