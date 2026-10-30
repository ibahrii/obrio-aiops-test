# Failure simulation (fake transport, no real API calls)

| scenario | calls made | backoff sleeps, s | answered by | fallback | result | logged failures | pass |
|---|---|---|---|---|---|---|---|
| invalid JSON once -> repair prompt succeeds | gemini-flash-lite → gemini-flash-lite | — | gemini-flash-lite | False | billing_subscription/P3/human=False | invalid_json | ✅ |
| schema violation twice -> fallback to Groq | gemini-flash-lite → gemini-flash-lite → groq-gpt-oss-120b | — | groq-gpt-oss-120b | True | billing_subscription/P3/human=False | schema_error | ✅ |
| timeout x2 -> 3rd attempt ok (exp. backoff 1s, 2s) | gemini-flash-lite → gemini-flash-lite → gemini-flash-lite | [1.0, 2.0] | gemini-flash-lite | False | billing_subscription/P3/human=False | timeout | ✅ |
| timeout x3 -> fallback to Groq | gemini-flash-lite → gemini-flash-lite → gemini-flash-lite → groq-gpt-oss-120b | [1.0, 2.0] | groq-gpt-oss-120b | True | billing_subscription/P3/human=False | timeout | ✅ |
| 429 with Retry-After 7s -> waits 7s -> ok | gemini-flash-lite → gemini-flash-lite | [7.0] | gemini-flash-lite | False | billing_subscription/P3/human=False | rate_limit | ✅ |
| 429 Retry-After 120s is capped at 30s | gemini-flash-lite → gemini-flash-lite | [30.0] | gemini-flash-lite | False | billing_subscription/P3/human=False | rate_limit | ✅ |
| 429 persistent -> fallback provider | gemini-flash-lite → gemini-flash-lite → gemini-flash-lite → groq-gpt-oss-120b | [1.0, 1.0] | groq-gpt-oss-120b | True | billing_subscription/P3/human=False | rate_limit | ✅ |
| 503 then Groq also times out -> 3rd model in chain | gemini-flash-lite → gemini-flash-lite → gemini-flash-lite → groq-gpt-oss-120b → groq-gpt-oss-120b → groq-gpt-oss-120b → gemini-flash | [1.0, 2.0, 1.0, 2.0] | gemini-flash | True | billing_subscription/P3/human=False | server_error, timeout | ✅ |
| everything fails -> safe default (unclassified, P2, needs_human) | gemini-flash-lite → gemini-flash-lite → groq-gpt-oss-120b → groq-gpt-oss-120b → gemini-flash → gemini-flash | — | None | True | unclassified/P2/human=True | chain_exhausted, invalid_json | ✅ |
| cache: same ticket (normalised case/spaces) served from disk; new prompt version = new key | gemini-flash-lite → gemini-flash-lite | — | — | — | 2nd from_cache=True, other version from_cache=False | — | ✅ |
