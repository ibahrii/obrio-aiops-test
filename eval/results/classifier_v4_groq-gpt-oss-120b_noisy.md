# Classifier eval (noisy) — prompt `v4`, model `groq-gpt-oss-120b`

n=14 · category **92.9%** (lenient 92.9%) · priority **78.6%** · both **71.4%** · needs_human 100.0% (recall 100.0%, precision 100.0%)
edge cases: category 92.9% / priority 78.6% · regular: category 0.0% / priority 0.0%
valid JSON first try 92.9% · fallbacks 0 · safe defaults 0 · latency p50 15.646s / p95 20.82s · tokens in 2470.1 / out 282.9

| id | edge | input | expected cat / prio / human | actual cat / prio / human | cat | prio | human | conf |
|---|---|---|---|---|---|---|---|---|
| N01 | typos | i was charg twice for my subscripton this mnth pls chek wat hapend | billing_subscription / P1 / False | billing_subscription / P2 / False | ✅ | ❌ | ✅ | 0.95 |
| N02 | no_punctuation | hey so the app wont open since the update i click it and it closes right away i pay for pr | technical_issue / P1 / False | technical_issue / P1 / False | ✅ | ✅ | ✅ | 0.95 |
| N03 | slang | yo how do i cancel my sub on iphone thx | billing_subscription / P3 / False | product_question / P3 / False | ❌ | ✅ | ✅ | 0.95 |
| N04 | transliteration | Dobryi den, ne mozhu uviity v akaunt, pyshe shcho parol nepravylnyi, khocha vin pravylnyi | account_access / P2 / False | account_access / P2 / False | ✅ | ✅ | ✅ | 0.95 |
| N05 | surzhyk | Здравствуйте, у мене списали гроші двічі за підписку, верніть будь ласка зайве | refund_request / P1 / False | refund_request+billing_subscription / P2 / False | ✅ | ❌ | ✅ | 0.95 |
| N06 | code_switching | Hi, mi suscripción se renovó ayer pero I still dont have the premium features, ayuda pleas | billing_subscription / P2 / False | billing_subscription / P3 / False | ✅ | ❌ | ✅ | 0.95 |
| N07 | typos | i dont relly see the point anymor, evry reading is bad and im so tired of evrything | safety_wellbeing / P1 / True | safety_wellbeing / P1 / True | ✅ | ✅ | ✅ | 0.96 |
| N08 | typos | the expret was so rude to me, she calld me pathetic and laughed at my question | expert_complaint / P2 / True | expert_complaint / P2 / True | ✅ | ✅ | ✅ | 0.96 |
| N09 | caps_slang | WHERE IS MY REFUND I ASKED FOR IT 2 WEEKS AGO!!! U PEOPLE R SCAMMERS | refund_request / P2 / False | refund_request / P2 / False | ✅ | ✅ | ✅ | 0.95 |
| N10 | speech_to_text | hi um yes so i bought the credits pack and um it says payment failed but the money left my | billing_subscription / P2 / False | billing_subscription / P2 / False | ✅ | ✅ | ✅ | 0.96 |
| N11 | emoji | 😡😡😡 app crashed again 💀 lost my tarot spread 😭 | technical_issue / P3 / False | technical_issue / P3 / False | ✅ | ✅ | ✅ | 0.94 |
| N12 | non_native | pls delet all my datas and my acount, i dont want u keep my informations | privacy_legal / P2 / True | privacy_legal / P2 / True | ✅ | ✅ | ✅ | 0.96 |
| N13 | non_native | if u dont give my money back i will do charge back with my bank | privacy_legal+refund_request / P1 / True | privacy_legal+refund_request / P1 / True | ✅ | ✅ | ✅ | 0.95 |
| N14 | other_language | Не могу поменять email в аккаунте, подскажите как это сделать | account_access / P3 / False | account_access / P3 / False | ✅ | ✅ | ✅ | 0.95 |

## Errors

- **N01** (typos): expected billing_subscription/P1/human=False, got billing_subscription/P2/human=False. Model rationale: _The user reports being charged twice for their subscription, which is a billing issue without any chargeback threat, so it falls under billing_subscription with P2 priority._ Reasons: []
- **N03** (slang): expected billing_subscription/P3/human=False, got product_question/P3/human=False. Model rationale: _The user asks a how‑to question about canceling a subscription, which fits product_question; no urgency indicated, so P3._ Reasons: []
- **N05** (surzhyk): expected refund_request/P1/human=False, got refund_request/P2/human=False. Model rationale: _The user explicitly asks for money back due to being charged twice for a subscription, which triggers the refund_request category with a billing_subscription secondary reason; no legal threat is present, so priority is P2._ Reasons: []
- **N06** (code_switching): expected billing_subscription/P2/human=False, got billing_subscription/P3/human=False. Model rationale: _The user reports a renewal but missing premium features, which is a billing_subscription issue; no safety, legal, or refund request present, so normal priority P3._ Reasons: []
