# Webhook end-to-end demo

Real HTTP calls to `uvicorn src.api:app` on localhost; real LLM calls (gemini-flash-lite, fallback on); Telegram variables not set, so P1 alerts go to the notification log. Artefacts: `eval/results/webhook_demo/`.

| # | webhook | ticket_id | PII masked | category / priority | needs_human | actions | LLM calls | time, s |
|---|---|---|---|---|---|---|---|---|
| 1 | Zendesk: double charge, card + phone + signature | zendesk:48213 | {'CARD': 1, 'PHONE': 1, 'NAME': 1} | billing_subscription / P1 | False | p1_alert (log), crm_csv (written) | 1 | 1.87 |
| 2 | Intercom: indirect crisis | intercom:215467 | {'NAME': 1} | safety_wellbeing + product_question / P1 | True | p1_alert (log), review_queue (queued) | 1 | 4.26 |
| 3 | Zendesk: cancel on Android, email in body | zendesk:48215 | {'EMAIL': 1} | billing_subscription / P3 | False | crm_csv (written) | 1 | 4.31 |
| 4 | Intercom: GDPR deletion in Ukrainian, phone + intro | intercom:215470 | {'PHONE': 1, 'NAME': 1} | privacy_legal / P2 | True | review_queue (queued) | 1 | 4.61 |
| 5 | Zendesk: praise | zendesk:48217 | {'NAME': 1} | feedback_other / P4 | False | crm_csv (written) | 1 | 4.43 |
| 6 | Zendesk: SAME ticket 48213 re-delivered | zendesk:48213 | — | — | — | **duplicate: no side effects** | 0 | 0.04 |

## What the model actually received

Recorded at `llm.raw_call`, i.e. the last point before the HTTP request to the provider:

**#1 Zendesk: double charge, card + phone + signature** → `gemini-flash-lite`
```
Charged twice!
Hello, I see two identical charges of $29.99 on my card [CARD] from Oct 28. I only have one subscription. You can call me on [PHONE].
Regards,
[NAME]
```
**#2 Intercom: indirect crisis** → `gemini-flash-lite`
```
Hi, it's [NAME]. Lately I feel like nothing matters and maybe everyone would be better off without me.
Also how do I turn off the daily notifications?
```
**#3 Zendesk: cancel on Android, email in body** → `gemini-flash-lite`
```
Cancel
How do I cancel my subscription on Android? My account email is [EMAIL].
```
**#4 Intercom: GDPR deletion in Ukrainian, phone + intro** → `gemini-flash-lite`
```
Добрий день! Мене звати [NAME]. Прошу видалити мій акаунт і всі мої дані. Мій телефон [PHONE].
```
**#5 Zendesk: praise** → `gemini-flash-lite`
```
Thank you
The new moon calendar is lovely, thank you for adding it!
Cheers,
[NAME]
```

## Routing outputs

**notifications.log**
```
2026-10-31T00:10:17+00:00 TELEGRAM (not configured, logged instead): 🚨 P1 ticket zendesk:48213 (zendesk) | billing_subscription → Billing | Action: Check transaction logs for the duplicate $29.99 charges on October 28 and issue a refund for the extra charge. | Human review: no (—) |  | Charged twice! | Hello, I see two identical charges of $29.99 on my card [CARD] from Oct 28. I only have one subscription. You can call me on [PHONE]. | Regards, | [NAME]
2026-10-31T00:10:21+00:00 TELEGRAM (not configured, logged instead): 🚨 P1 ticket intercom:215467 (intercom) | safety_wellbeing + product_question → Trust & Safety | Action: Initiate safety protocols and provide crisis support resources immediately. | Human review: yes (model: safety_wellbeing; model: mixed topics where one is about money; safety_wellbeing: possible vulnerable user) |  | Hi, it's [NAME]. Lately I feel like nothing matters and maybe everyone would be better off without me. | Also how do I turn off the daily notifications?
```

**review_queue.jsonl**
```
{"ticket_id": "intercom:215467", "source": "intercom", "received_at": "2026-10-31T00:10:21+00:00", "text": "Hi, it's [NAME]. Lately I feel like nothing matters and maybe everyone would be better off without me.\nAlso how do I turn off the daily notifications?", "category": "safety_wellbeing", "secondary_category": "product_question", "priority": "P1", "reasons": ["model: safety_wellbeing", "model: mixed topics where one is about money", "safety_wellbeing: possible vulnerable user"], "route_to": "Trust & Safety", "model": "gemini-flash-lite", "prompt": "v4"}
{"ticket_id": "intercom:215470", "source": "intercom", "received_at": "2026-10-31T00:10:30+00:00", "text": "Добрий день! Мене звати [NAME]. Прошу видалити мій акаунт і всі мої дані. Мій телефон [PHONE].", "category": "privacy_legal", "secondary_category": null, "priority": "P2", "reasons": ["model: privacy_legal", "privacy_legal: legal/GDPR consequences"], "route_to": "Legal & Privacy", "model": "gemini-flash-lite", "prompt": "v4"}
```

**crm_tickets.csv**
```
ticket_id,source,received_at,category,secondary_category,priority,route_to,action,confidence,language,requester_type
zendesk:48213,zendesk,2026-10-31T00:10:17+00:00,billing_subscription,,P1,Billing,Check transaction logs for the duplicate $29.99 charges on October 28 and issue a refund for the extra charge.,0.95,en,user
zendesk:48215,zendesk,2026-10-31T00:10:25+00:00,billing_subscription,,P3,Billing,Provide instructions on how to cancel the subscription on Android,0.95,en,user
zendesk:48217,zendesk,2026-10-31T00:10:34+00:00,feedback_other,,P4,General Support,Log customer praise regarding the new moon calendar,1.0,en,user
```

