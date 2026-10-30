# Environment check — 2026-10-30

Keys (presence only): GEMINI_API_KEY — є, GROQ_API_KEY — є, OPENROUTER_API_KEY — є.
All three APIs reachable from the container (HTTP 200 on `/models`).

## Model selection (from live `/models` listings)

| Role | Provider | Model id | Notes from test calls |
|---|---|---|---|
| Gemini Flash (current) | Google AI Studio | `gemini-3.8-flash` | `gemini-flash-latest` resolves to it. Unstable during the session: one call took 298 s, others timed out at 60–90 s or returned 503 "high demand". |
| Gemini Flash (alt) | Google AI Studio | `gemini-3.6-flash` | `gemini-3.5-flash` alias is served as 3.6. 2.8–3.4 s typical, one 25.8 s outlier. |
| Gemini Flash-Lite | Google AI Studio | `gemini-3.5-flash-lite` | `gemini-flash-lite-latest` resolves to it. ~0.6 s. No thinking tokens by default. |
| Groq strong | Groq | `openai/gpt-oss-120b` | Free tier: 1000 RPD, **8000 TPM** (tight), ~0.7 s. |
| Groq fast | Groq | `openai/gpt-oss-20b` | Same free limits, ~0.6 s. |
| OpenRouter free | OpenRouter | `nvidia/nemotron-3-ultra-550b-a55b:free` | Key is free tier: **50 free-model requests/day**. `google/gemma-4-31b-it:free` → 429 (shared upstream pool); `thinkingmachines/inkling:free` → 403 (agentic harnesses only). |

`gemini-2.5-flash` / `gemini-2.5-flash-lite` → 404 "no longer available to new users".
`qwen/qwen3.8-27b` on Groq → 429 because its free-tier output-token-per-minute limit (1000) is below the default max_tokens.

## Prices

Public paid-tier prices snapshot: `eval/results/pricing_snapshot.json` (source: OpenRouter endpoints API, which lists each upstream provider's own price; fetched 2026-10-30). Secondary pricing websites gave conflicting numbers, so they were not used.
