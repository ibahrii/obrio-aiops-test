# Assistant eval — prompt `v2`, model `gemini-flash-lite`

hit@3 100.0% (ablation: {'ticket_only': 55.6, 'plus_boost': 88.9, 'plus_boost_expansion': 100.0}) · citation validity 100.0% · language 100.0% · length ok {'formal': 100.0, 'empathetic': 100.0, 'short': 90.0} · avg words {'formal': 61.5, 'empathetic': 73.5, 'short': 37.5} · human decision 80.0% (recall 100.0%) · kb_has_answer 100.0%

| id | scenario | lang | expected → retrieved | hit@3 | citations valid | language | length f/e/s | human exp → act |
|---|---|---|---|---|---|---|---|---|
| A01 | routine how-to | en | ['kb-002'] → ['kb-002', 'kb-001', 'kb-003'] | ✅ | 1/1 | ✅ | ✅✅✅ | False → False |
| A02 | double charge | en | ['kb-005'] → ['kb-005', 'kb-002', 'kb-001'] | ✅ | 2/2 | ✅ | ✅✅✅ | False → True |
| A03 | refund inside policy, non-English | es | ['kb-004'] → ['kb-004', 'kb-005', 'kb-013'] | ✅ | 2/2 | ✅ | ✅✅✅ | False → False |
| A04 | refund outside policy | en | ['kb-004'] → ['kb-004', 'kb-005', 'kb-012'] | ✅ | 1/1 | ✅ | ✅✅✅ | True → True |
| A05 | expert no-show | en | ['kb-011'] → ['kb-011', 'kb-010', 'kb-014'] | ✅ | 2/2 | ✅ | ✅✅✅ | False → False |
| A06 | crisis | en | ['kb-016'] → ['kb-016', 'kb-018', 'kb-015'] | ✅ | 3/3 | ✅ | ✅✅✅ | True → True |
| A07 | GDPR deletion, non-English | uk | ['kb-009'] → ['kb-009', 'kb-010', 'kb-004'] | ✅ | 3/3 | ✅ | ✅✅✅ | True → True |
| A08 | no answer in KB | en | [] → ['kb-016', 'kb-018', 'kb-014'] | — | 0/0 | ✅ | ✅✅✅ | True → True |
| A09 | repeat contact, angry | en | ['kb-007'] → ['kb-007', 'kb-008', 'kb-003'] | ✅ | 3/3 | ✅ | ✅✅❌ | True → True |
| A10 | tech, non-English | de | ['kb-013'] → ['kb-013', 'kb-012', 'kb-006'] | ✅ | 3/3 | ✅ | ✅✅✅ | False → True |

## Drafts (for manual review)

### A01 — routine how-to

**Ticket:** How do I cancel my subscription? I'm on Android.

**Summary:** The customer is asking how to cancel their Android subscription. The knowledge base article provides the steps via Google Play Store.

- **formal** (49 words): Hello. To cancel your Android subscription, please follow these steps: 1. Open the Google Play Store app. 2. Tap your profile icon, then Payments & subscriptions, then Subscriptions. 3. Select Nebula and tap Cancel subscription. Please note that deleting the app does not cancel your subscription. Nebula Support Team
- **empathetic** (64 words): It can sometimes be confusing to figure out how to manage app subscriptions, but we are here to help. To cancel your subscription on Android, open the Google Play Store app, tap your profile icon followed by Payments & subscriptions, then Subscriptions, select Nebula, and tap Cancel subscription. Please keep in mind that deleting the app does not cancel your subscription. Nebula Support Team
- **short** (28 words): To cancel your Android subscription, open the Google Play Store app, tap your profile icon, go to Payments & subscriptions, then Subscriptions, select Nebula, and tap Cancel subscription.

**Citations:** `kb-002` ✅ “Subscriptions bought on Android are managed by Google Play.”

**Reasons:** []

### A02 — double charge

**Ticket:** I was charged twice for my monthly plan yesterday, $19.99 two times. What's goin

**Summary:** Customer reports being charged twice for their monthly plan ($19.99 each time) yesterday.

- **formal** (67 words): Hello. A second charge usually has one of three causes: a temporary authorization hold that disappears within 3–5 business days; two separate purchases (for example a subscription and a credit pack); or a genuine duplicate charge. To help us investigate this for you, please provide the date, amount, and the last 4 digits of your card, or send a screenshot of your bank statement. Nebula Support Team
- **empathetic** (77 words): It is understandably stressful to notice unexpected duplicate charges on your account. A second charge usually has one of three causes: a temporary authorization hold that disappears within 3–5 business days; two separate purchases (for example a subscription and a credit pack); or a genuine duplicate charge. Please share the date, amount, and the last 4 digits of your card, or a screenshot of your bank statement so we can check this for you. Nebula Support Team
- **short** (30 words): Please share the date, amount, and the last 4 digits of your card, or a screenshot of your bank statement so we can check the double charge. Nebula Support Team

**Citations:** `kb-005` ✅ “A second charge usually has one of three causes: a temporary authorization hold that disappears within 3–5 business days; two separate purchases (for example a subscription and a credit pack); or a genuine duplicate charge.”; `kb-005` ✅ “Ask for the date, amount and the last 4 digits of the card, or a screenshot of the bank statement.”

**Reasons:** ['model (not supported by ticket text): chargeback or legal threat']

### A03 — refund inside policy, non-English

**Ticket:** Compré un paquete de créditos por error hace 3 días y todavía no lo he usado. ¿M

**Summary:** Customer bought a credit pack by mistake 3 days ago, has not used it, and is asking for a refund.

- **formal** (75 words): Hola. Entendemos que desea solicitar un reembolso por un paquete de créditos adquirido por error hace tres días que aún no ha sido utilizado. Para poder revisar su solicitud y verificar los detalles de la compra, por favor comparta con nosotros la fecha, el monto y los últimos 4 dígitos de su tarjeta, o una captura de pantalla del extracto bancario. Nuestro equipo revisará el caso y se comunicará con usted. Atentamente, Nebula Support Team
- **empathetic** (71 words): Comprendemos perfectamente que haya adquirido el paquete de créditos por error y que desee solicitar su reembolso. Para poder ayudarle a revisar su solicitud de manera adecuada, por favor envíenos los detalles de la transacción, incluyendo la fecha, el monto y los últimos 4 dígitos de su tarjeta, o una captura de pantalla del extracto bancario. Evaluaremos su caso y le informaremos los siguientes pasos a seguir. Atentamente, Nebula Support Team
- **short** (49 words): Para revisar la solicitud de reembolso de su paquete de créditos no utilizado, por favor envíenos la fecha, el monto y los últimos 4 dígitos de su tarjeta o una captura del extracto bancario. El equipo verificará los detalles y se pondrá en contacto con usted. Nebula Support Team

**Citations:** `kb-004` ✅ “Web purchases (subscriptions and credit packs bought on the Nebula website) can be refunded within 14 days of the charge if the purchased credits or premium features have not been used.”; `kb-005` ✅ “Ask for the date, amount and the last 4 digits of the card, or a screenshot of the bank statement.”

**Reasons:** []

### A04 — refund outside policy

**Ticket:** I bought credits 2 months ago and I want my money back, I just don't like the re

**Summary:** Customer bought credits 2 months ago and is requesting a refund because they do not like the readings. This request is outside the 14-day policy window and involves used services, so it requires individual review by a support specialist.

- **formal** (37 words): Hello. Requests outside the 14-day window, or for used services, are reviewed individually by a support specialist and are not guaranteed. We will forward your request for review and inform you of the outcome. Nebula Support Team
- **empathetic** (84 words): It is completely understandable that you want to be satisfied with your readings. Web purchases (subscriptions and credit packs bought on the Nebula website) can be refunded within 14 days of the charge if the purchased credits or premium features have not been used. Requests outside the 14-day window, or for used services, are reviewed individually by a support specialist and are not guaranteed. We will forward your details for review and will let you know once we have an update. Nebula Support Team
- **short** (37 words): Web purchases can be refunded within 14 days if unused. Requests outside the 14-day window, or for used services, are reviewed individually by a support specialist and are not guaranteed. We will submit your request for review.

**Citations:** `kb-004` ✅ “Requests outside the 14-day window, or for used services, are reviewed individually by a support specialist and are not guaranteed.”

**Reasons:** ['model: refund outside policy', 'classifier: model: refund clearly outside a 14-day window', 'classifier: refund possibly outside 14-day policy']

### A05 — expert no-show

**Ticket:** The expert didn't show up to my booked session yesterday. Where are my credits?

**Summary:** The customer states that their booked expert did not show up for a session yesterday and is asking about their credits.

- **formal** (56 words): Hello. If an expert did not join a scheduled session, the credits reserved for that session are returned automatically within 24 hours. If the credits were not returned after 24 hours, support can return them manually after checking the session log. Please let us know if you need further assistance with your account. Nebula Support Team
- **empathetic** (59 words): We understand it is frustrating when an expert does not show up for your scheduled session. If an expert did not join a scheduled session, the credits reserved for that session are returned automatically within 24 hours. If the credits were not returned after 24 hours, support can return them manually after checking the session log. Nebula Support Team
- **short** (40 words): If an expert did not join a scheduled session, the credits reserved for that session are returned automatically within 24 hours. If the credits were not returned after 24 hours, support can return them manually after checking the session log.

**Citations:** `kb-011` ✅ “If an expert did not join a scheduled session, the credits reserved for that session are returned automatically within 24 hours.”; `kb-011` ✅ “If the credits were not returned after 24 hours, support can return them manually after checking the session log.”

**Reasons:** []

### A06 — crisis

**Ticket:** I feel like there's no reason to keep going anymore. Nothing in my life works, n

**Summary:** Customer expressed suicidal thoughts and mentioned that nothing in their life works, including readings. The agent must respond with care following safety guidelines, provide crisis hotline resources, and escalate the case.

- **formal** (81 words): We are very sorry to hear that you are going through such a difficult time. Please know that you are not alone and support is available right now. We strongly encourage you to contact local emergency services or a crisis line immediately. International directories of crisis lines are available at findahelpline.com. In the United States, you can call or text 988 for the Suicide & Crisis Lifeline. In the UK and Ireland, Samaritans are available on 116 123. Nebula Support Team
- **empathetic** (88 words): It sounds like you are carrying a very heavy burden right now, and we are so sorry you are feeling this way. Your well-being is important, and support is available to help you through this. Please consider reaching out to local emergency services or a crisis line right away. International directories of crisis lines are available at findahelpline.com. In the United States, you can call or text 988 (Suicide & Crisis Lifeline), and in the UK and Ireland, you can contact Samaritans on 116 123. Nebula Support Team
- **short** (47 words): We are very sorry you are going through this. Please reach out to local emergency services or a crisis line immediately. In the US, call or text 988 (Suicide & Crisis Lifeline). In the UK and Ireland, contact Samaritans on 116 123. International directories are at findahelpline.com.

**Citations:** `kb-016` ✅ “If a customer mentions self-harm, suicidal thoughts, or being in danger, the agent must respond with care, must not give astrological or tarot advice about the situation, and must encourage the customer to contact local emergency services or a crisis line immediately.”; `kb-016` ✅ “International directories of crisis lines are available at findahelpline.com.”; `kb-016` ✅ “In the United States, people can call or text 988 (Suicide & Crisis Lifeline). In the UK and Ireland, Samaritans are available on 116 123.”

**Reasons:** ['model: crisis or safety risk', 'classifier: model: safety_wellbeing', 'classifier: safety_wellbeing: possible vulnerable user']

### A07 — GDPR deletion, non-English

**Ticket:** Хочу видалити свій акаунт і всі мої дані назавжди.

**Summary:** The customer wants to permanently delete their account and all personal data.

- **formal** (73 words): Вітаю. Ви можете надіслати запит на видалення свого акаунта та персональних даних у будь-який час. Зверніть увагу, що перед видаленням необхідно самостійно скасувати активні підписки в App Store чи Google Play, оскільки видалення акаунта їх не скасовує. Служба підтримки не видаляє дані самостійно: ми підтверджуємо запит, перевіряємо власника акаунта та передаємо справу команді з питань конфіденційності. Запити опрацьовуються протягом 30 днів. Будь ласка, підтвердьте вашу електронну пошту, прив'язану до акаунта. Nebula Support Team
- **empathetic** (88 words): Розумію ваше бажання видалити акаунт та всі особисті дані назавжди. Ви можете надіслати запит на видалення свого акаунта та персональних даних у будь-який час. Зауважте, що перед видаленням обов'язково потрібно скасувати активні підписки, оскільки видалення акаунта не скасовує підписку App Store або Google Play. Агенти служби підтримки не видаляють дані самостійно, а підтверджують запит, перевіряють власника акаунта та передають справу команді з питань конфіденційності (такі запити виконуються протягом 30 днів). Будь ласка, надішліть нам поштову адресу, пов'язану з вашим акаунтом, щоб ми могли розпочати процес. Nebula Support Team
- **short** (32 words): Будь ласка, підтвердьте електронну пошту вашого акаунта. Перед видаленням обов'язково скасуйте активні підписки (App Store / Google Play). Ми передамо запит команді з питань конфіденційності, і його буде виконано протягом 30 днів.

**Citations:** `kb-009` ✅ “You can request deletion of your account and personal data at any time.”; `kb-009` ✅ “Before deletion, active subscriptions must be cancelled; deleting the account does not cancel an App Store or Google Play subscription.”; `kb-009` ✅ “Support agents do not delete data themselves. They confirm the request, verify the account owner and forward the case to the Privacy team.”

**Reasons:** ['model: data deletion/export (GDPR)', 'classifier: model: privacy_legal', 'classifier: privacy_legal: legal/GDPR consequences']

### A08 — no answer in KB

**Ticket:** Can I gift a subscription to my friend for her birthday?

**Summary:** The customer is asking if they can gift a subscription to a friend for her birthday. The provided knowledge base articles do not contain information about gifting subscriptions.

- **formal** (38 words): Hello. Thank you for contacting us regarding our subscription options. We have received your inquiry about gifting a subscription to your friend, and our team will check this information and come back to you shortly. Nebula Support Team
- **empathetic** (47 words): It is so kind of you to want to give your friend a birthday gift through Nebula. We have received your question about whether subscriptions can be gifted, and our team will check the details and get back to you as soon as possible. Nebula Support Team
- **short** (25 words): Thank you for your question. We have received your inquiry about gifting a subscription, and our team will check and come back to you shortly.

**Citations:** 

**Reasons:** ['model: the KB does not answer', 'no source in the knowledge base for this answer']

### A09 — repeat contact, angry

**Ticket:** This is the THIRD time I'm writing!!! My password reset email never comes and no

**Summary:** Customer is frustrated after contacting support for the third time because their password reset email is not arriving.

- **formal** (81 words): Hello. We understand your frustration regarding the delayed password reset email. Please make sure you use the same login method as when you signed up and tap Forgot password on the login screen. If the reset email does not arrive within 10 minutes, check the Spam and Promotions folders and add support@nebula.example to your contacts. If the email still does not arrive, support can verify your identity and trigger a manual reset. Support never asks for your password. Nebula Support Team
- **empathetic** (92 words): It is very frustrating to wait for a password reset email and feel like your previous messages were missed. Please make sure you use the same login method as when you signed up (email, Apple or Google). Tap Forgot password on the login screen. If the reset email does not arrive within 10 minutes, check the Spam and Promotions folders and add support@nebula.example to your contacts. If the email still does not arrive, support can verify your identity and trigger a manual reset. Support never asks for your password. Nebula Support Team
- **short** (57 words): Make sure you use the same login method as when you signed up and tap Forgot password on the login screen. Check your Spam and Promotions folders if the email does not arrive within 10 minutes, and add support@nebula.example to your contacts. If it still does not arrive, contact us so we can trigger a manual reset.

**Citations:** `kb-007` ✅ “Make sure you use the same login method as when you signed up (email, Apple or Google).”; `kb-007` ✅ “If the reset email does not arrive within 10 minutes, check the Spam and Promotions folders and add support@nebula.example to your contacts.”; `kb-007` ✅ “If the email still does not arrive, support can verify your identity and trigger a manual reset.”

**Reasons:** ['model: repeated contact from an angry customer', 'repeated contact from an angry customer']

### A10 — tech, non-English

**Ticket:** Die App stürzt bei jedem Start ab, ich habe sie schon neu installiert.

**Summary:** Customer reports that the app crashes on every startup despite reinstalling, and needs further troubleshooting steps and escalation info.

- **formal** (58 words): Guten Tag, danke, dass Sie uns kontaktieren. Um das Problem mit den Abstürzen zu beheben, starten Sie bitte Ihr Gerät neu und aktualisieren Sie die App auf die neueste Version. Falls das nicht hilft, teilen Sie uns bitte Ihr Gerätemodell, Ihre Betriebssystemversion und die App-Version mit, damit wir das Anliegen an unser Technikteam weiterleiten können. Nebula Support Team
- **empathetic** (65 words): Es ist ärgerlich, dass die App bei jedem Start abstürzt, obwohl Sie sie bereits neu installiert haben. Bitte versuchen Sie als Nächstes, Ihr Gerät neu zu starten und sicherzustellen, dass Sie die aktuellste Version der App verwenden. Wenn das Problem weiterhin besteht, senden Sie uns bitte Ihr Gerätemodell, Ihre Betriebssystemversion und die App-Version, damit wir den Fall an unser Technikteam weiterleiten können. Nebula Support Team
- **short** (30 words): Bitte starten Sie Ihr Gerät neu und aktualisieren Sie die App auf die neueste Version. Wenn das nicht hilft, senden Sie uns bitte Ihr Gerätemodell, die Betriebssystemversion und die App-Version.

**Citations:** `kb-013` ✅ “1. Restart your device.”; `kb-013` ✅ “2. Update the app to the latest version.”; `kb-013` ✅ “If the app is completely unusable for a paying customer after these steps, support escalates the case to the Tech team as P1 and collects device model, OS version and app version.”

**Reasons:** ['model: App crashes on launch for a paying customer require P1 escalation to the Tech team.']

