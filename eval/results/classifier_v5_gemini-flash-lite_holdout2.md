# Classifier eval (holdout2) — prompt `v5`, model `gemini-flash-lite`

n=10 · category **80.0%** (lenient 80.0%) · priority **100.0%** · both **80.0%** · needs_human 100.0% (recall 100.0%, precision 100.0%)
edge cases: category 80.0% / priority 100.0% · regular: category 0.0% / priority 0.0%
valid JSON first try 100.0% · fallbacks 0 · safe defaults 0 · latency p50 1.568s / p95 1.729s · tokens in 2106.4 / out 172.9

| id | edge | input | expected cat / prio / human | actual cat / prio / human | cat | prio | human | conf |
|---|---|---|---|---|---|---|---|---|
| Q01 | single_topic_paid_not_applied | I renewed my yearly plan this morning, the bank already took $59.99, but the app still say | billing_subscription / P2 / False | billing_subscription / P2 / False | ✅ | ✅ | ✅ | 0.95 |
| Q02 | single_topic_paid_not_applied | Bought 200 credits ten minutes ago, Apple sent the receipt, but my balance in the app stil | billing_subscription / P2 / False | billing_subscription / P2 / False | ✅ | ✅ | ✅ | 0.95 |
| Q03 | single_topic_mentions_paying | The horoscope page has been blank for two days on my phone. I'm a premium member btw. | technical_issue / P3 / False | technical_issue / P3 / False | ✅ | ✅ | ✅ | 0.95 |
| Q04 | single_topic_question | Can I switch from monthly to yearly without losing the credits I already have? | product_question / P3 / False | billing_subscription / P3 / False | ❌ | ✅ | ✅ | 0.95 |
| Q05 | mixed_money | The chat with my astrologer kept freezing and I lost 15 paid minutes. I want those credits | refund_request+technical_issue / P2 / True | refund_request+technical_issue / P2 / True | ✅ | ✅ | ✅ | 0.90 |
| Q06 | mixed_money | Your app keeps logging me out, and on top of that I was charged $29.99 for a plan I never  | billing_subscription+technical_issue / P1 / True | refund_request+technical_issue / P1 / True | ❌ | ✅ | ✅ | 0.90 |
| Q07 | mixed_money | I can't log in, and my subscription renews tomorrow. I need to cancel it before I'm charge | account_access+billing_subscription / P2 / True | account_access+billing_subscription / P2 / True | ✅ | ✅ | ✅ | 0.90 |
| Q08 | mixed_money_crisis | I can't afford this anymore and honestly I can't keep living like this. Please just cancel | safety_wellbeing+billing_subscription / P1 / True | safety_wellbeing+billing_subscription / P1 / True | ✅ | ✅ | ✅ | 0.95 |
| Q09 | control | What is this $4.99 'NEBULA DIGITAL' charge from yesterday? | billing_subscription / P2 / False | billing_subscription / P2 / False | ✅ | ✅ | ✅ | 0.95 |
| Q10 | control | how 2 cancel my subscription on android?? | billing_subscription / P3 / False | billing_subscription / P3 / False | ✅ | ✅ | ✅ | 1.00 |

## Errors

- **Q04** (single_topic_question): expected product_question/P3/human=False, got billing_subscription/P3/human=False. Model rationale: _The customer is asking a straightforward question about changing their subscription plan and retaining credits._ Reasons: []
- **Q06** (mixed_money): expected billing_subscription/P1/human=True, got refund_request/P1/human=True. Model rationale: _The customer explicitly demands money back for an unauthorized charge, making it a refund request, while also mentioning a separate technical login issue._ Reasons: ['model: mixed topics where one is about money', 'mixed topics involving money']
