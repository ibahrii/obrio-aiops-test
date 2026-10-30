# Cost report (real tokens × public paid-tier prices)

| model | both acc | Task 1 $/ticket | Task 1 $/10k | Task 2 call $/ticket | Task 1+2 $/10k | Task 1 with prompt cache $/10k |
|---|---|---|---|---|---|---|
| Gemini 3.6 Flash | 100.0% | 0.002199 | 21.99 | 0.002903 (оцінка) | 51.02 (оцінка) | 9.03 |
| Gemini 3.5 Flash-Lite | 96.7% | 0.001008 | 10.08 | 0.001504 | 25.12 | 4.89 |
| GPT-OSS-120B (Groq) | 86.7% | 0.000496 | 4.96 | 0.000593 (оцінка) | 10.89 (оцінка) | 3.52 |
| GPT-OSS-20B (Groq) | 76.7% | 0.000232 | 2.32 | 0.000252 (оцінка) | 4.84 (оцінка) | 1.60 |
| Nemotron 3 Ultra 550B (OpenRouter :free) | 90.0% | 0.001966 | 19.66 | 0.003291 (оцінка) | 52.56 (оцінка) | 11.98 |

**Cascade** (Flash-Lite → GPT-OSS-120B when confidence < 0.9): escalated 1/30 tickets, both accuracy 96.7%, $0.001024/ticket, $10.24/10k.
**Batch API** (50% off) for Task 2 drafts of P3/P4 tickets (33% of tickets): saves ≈ $2.51 per 10k.
Prompt cache column: static system prompt (1919 tokens) billed at the cached-input price; storage fees and minimum cacheable size not included (оцінка).
Task 2 tokens measured on Flash-Lite only (in 1205.1, out 457.0); other models are estimates.
