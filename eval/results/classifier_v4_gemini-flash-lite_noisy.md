# Classifier eval (noisy) — prompt `v4`, model `gemini-flash-lite`

n=14 · category **92.9%** (lenient 92.9%) · priority **100.0%** · both **92.9%** · needs_human 71.4% (recall 100.0%, precision 50.0%)
edge cases: category 92.9% / priority 100.0% · regular: category 0.0% / priority 0.0%
valid JSON first try 100.0% · fallbacks 0 · safe defaults 0 · latency p50 1.596s / p95 2.023s · tokens in 1948 / out 168.1

| id | edge | input | expected cat / prio / human | actual cat / prio / human | cat | prio | human | conf |
|---|---|---|---|---|---|---|---|---|
| N01 | typos | i was charg twice for my subscripton this mnth pls chek wat hapend | billing_subscription / P1 / False | billing_subscription / P1 / False | ✅ | ✅ | ✅ | 0.95 |
| N02 | no_punctuation | hey so the app wont open since the update i click it and it closes right away i pay for pr | technical_issue / P1 / False | technical_issue+billing_subscription / P1 / True | ✅ | ✅ | ❌ | 0.95 |
| N03 | slang | yo how do i cancel my sub on iphone thx | billing_subscription / P3 / False | billing_subscription / P3 / False | ✅ | ✅ | ✅ | 0.95 |
| N04 | transliteration | Dobryi den, ne mozhu uviity v akaunt, pyshe shcho parol nepravylnyi, khocha vin pravylnyi | account_access / P2 / False | account_access / P2 / False | ✅ | ✅ | ✅ | 0.95 |
| N05 | surzhyk | Здравствуйте, у мене списали гроші двічі за підписку, верніть будь ласка зайве | refund_request / P1 / False | billing_subscription+refund_request / P1 / True | ❌ | ✅ | ❌ | 0.95 |
| N06 | code_switching | Hi, mi suscripción se renovó ayer pero I still dont have the premium features, ayuda pleas | billing_subscription / P2 / False | billing_subscription+technical_issue / P2 / True | ✅ | ✅ | ❌ | 0.95 |
| N07 | typos | i dont relly see the point anymor, evry reading is bad and im so tired of evrything | safety_wellbeing / P1 / True | safety_wellbeing+product_question / P1 / True | ✅ | ✅ | ✅ | 0.95 |
| N08 | typos | the expret was so rude to me, she calld me pathetic and laughed at my question | expert_complaint / P2 / True | expert_complaint / P2 / True | ✅ | ✅ | ✅ | 0.95 |
| N09 | caps_slang | WHERE IS MY REFUND I ASKED FOR IT 2 WEEKS AGO!!! U PEOPLE R SCAMMERS | refund_request / P2 / False | refund_request / P2 / False | ✅ | ✅ | ✅ | 0.95 |
| N10 | speech_to_text | hi um yes so i bought the credits pack and um it says payment failed but the money left my | billing_subscription / P2 / False | billing_subscription+technical_issue / P2 / True | ✅ | ✅ | ❌ | 0.95 |
| N11 | emoji | 😡😡😡 app crashed again 💀 lost my tarot spread 😭 | technical_issue / P3 / False | technical_issue / P3 / False | ✅ | ✅ | ✅ | 0.95 |
| N12 | non_native | pls delet all my datas and my acount, i dont want u keep my informations | privacy_legal / P2 / True | privacy_legal / P2 / True | ✅ | ✅ | ✅ | 0.99 |
| N13 | non_native | if u dont give my money back i will do charge back with my bank | privacy_legal+refund_request / P1 / True | privacy_legal+refund_request / P1 / True | ✅ | ✅ | ✅ | 0.95 |
| N14 | other_language | Не могу поменять email в аккаунте, подскажите как это сделать | account_access / P3 / False | account_access / P3 / False | ✅ | ✅ | ✅ | 0.95 |

## Errors

- **N02** (no_punctuation): expected technical_issue/P1/human=False, got technical_issue/P1/human=True. Model rationale: _The app is completely down for this paying customer due to a crash on launch, which makes it a P1 technical issue with a billing component._ Reasons: ['model: mixed topics where one is about money', 'mixed topics involving money']
- **N05** (surzhyk): expected refund_request/P1/human=False, got billing_subscription/P1/human=True. Model rationale: _The user reports a duplicate charge and asks to return the extra money, which combines a billing issue with an explicit refund request._ Reasons: ['model: mixed topics where one is about money']
- **N06** (code_switching): expected billing_subscription/P2/human=False, got billing_subscription/P2/human=True. Model rationale: _The customer paid for a renewal but premium features were not applied, which is classified as a billing error (P2)._ Reasons: ['mixed topics involving money']
- **N10** (speech_to_text): expected billing_subscription/P2/human=False, got billing_subscription/P2/human=True. Model rationale: _Payment taken but credits/plan not applied is classified as a billing error (P2)._ Reasons: ['mixed topics involving money']
