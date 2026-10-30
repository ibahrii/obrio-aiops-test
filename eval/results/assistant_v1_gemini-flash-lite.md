# Assistant eval — prompt `v1`, model `gemini-flash-lite`

hit@3 100.0% (ablation: {'ticket_only': 55.6, 'plus_boost': 88.9, 'plus_boost_expansion': 100.0}) · citation validity 100.0% · language 90.0% · length ok {'formal': 100.0, 'empathetic': 100.0, 'short': 100.0} · avg words {'formal': 54.3, 'empathetic': 53.2, 'short': 29.0} · human decision 60.0% (recall 100.0%) · kb_has_answer 100.0%

| id | scenario | lang | expected → retrieved | hit@3 | citations valid | language | length f/e/s | human exp → act |
|---|---|---|---|---|---|---|---|---|
| A01 | routine how-to | en | ['kb-002'] → ['kb-002', 'kb-001', 'kb-003'] | ✅ | 1/1 | ✅ | ✅✅✅ | False → False |
| A02 | double charge | en | ['kb-005'] → ['kb-005', 'kb-002', 'kb-001'] | ✅ | 1/1 | ✅ | ✅✅✅ | False → True |
| A03 | refund inside policy, non-English | es | ['kb-004'] → ['kb-004', 'kb-005', 'kb-013'] | ✅ | 2/2 | ✅ | ✅✅✅ | False → True |
| A04 | refund outside policy | en | ['kb-004'] → ['kb-004', 'kb-005', 'kb-012'] | ✅ | 2/2 | ✅ | ✅✅✅ | True → True |
| A05 | expert no-show | en | ['kb-011'] → ['kb-011', 'kb-010', 'kb-014'] | ✅ | 2/2 | ✅ | ✅✅✅ | False → True |
| A06 | crisis | en | ['kb-016'] → ['kb-016', 'kb-018', 'kb-015'] | ✅ | 2/2 | ✅ | ✅✅✅ | True → True |
| A07 | GDPR deletion, non-English | uk | ['kb-009'] → ['kb-009', 'kb-010', 'kb-004'] | ✅ | 3/3 | ❌ | ✅✅✅ | True → True |
| A08 | no answer in KB | en | [] → ['kb-016', 'kb-018', 'kb-014'] | — | 0/0 | ✅ | ✅✅✅ | True → True |
| A09 | repeat contact, angry | en | ['kb-007'] → ['kb-007', 'kb-008', 'kb-003'] | ✅ | 1/1 | ✅ | ✅✅✅ | True → True |
| A10 | tech, non-English | de | ['kb-013'] → ['kb-013', 'kb-012', 'kb-006'] | ✅ | 2/2 | ✅ | ✅✅✅ | False → True |

## Drafts (for manual review)

### A01 — routine how-to

**Ticket:** How do I cancel my subscription? I'm on Android.

**Summary:** Customer is asking how to cancel their Nebula subscription on Android.

- **formal** (58 words): We understand you would like to cancel your subscription. Subscriptions purchased on Android are managed through Google Play. To cancel, please open the Google Play Store app, tap your profile icon, go to Payments & subscriptions, select Subscriptions, choose Nebula, and tap Cancel subscription. Please note that deleting the app does not cancel your subscription. Nebula Support Team
- **empathetic** (67 words): It can be frustrating to navigate subscription settings, but we are here to help you cancel your Android plan. Since subscriptions bought on Android are managed by Google Play, please open the Google Play Store app, tap your profile icon, go to Payments & subscriptions, select Subscriptions, choose Nebula, and tap Cancel subscription. Remember that simply deleting the app will not stop the renewals. Nebula Support Team
- **short** (31 words): To cancel your Android subscription, open the Google Play Store app, tap your profile icon, go to Payments & subscriptions > Subscriptions, select Nebula, and tap Cancel subscription. Nebula Support Team

**Citations:** `kb-002` ✅ “Subscriptions bought on Android are managed by Google Play. Steps: 1. Open the Google Play Store app. 2. Tap your profile icon, then Payments & subscriptions, then Subscriptions. 3. Select Nebula and tap Cancel subscription.”

**Reasons:** []

### A02 — double charge

**Ticket:** I was charged twice for my monthly plan yesterday, $19.99 two times. What's goin

**Summary:** Customer was charged twice ($19.99 each) for their monthly plan yesterday.

- **formal** (46 words): Hello. I understand that experiencing multiple charges can be concerning. To help resolve this, please provide the date, exact amount, and the last 4 digits of your payment card, or a screenshot of your bank statement so we can investigate the payment history. Nebula Support Team
- **empathetic** (55 words): Hello. It is frustrating to see unexpected charges on your account, and I want to help get this sorted out for you right away. Could you please share the date, amount, and the last 4 digits of your card, or a screenshot of your bank statement so we can locate the transactions? Nebula Support Team
- **short** (30 words): Hello. Please provide the transaction date, amount, and the last 4 digits of your card or a bank statement screenshot so we can investigate the double charge. Nebula Support Team

**Citations:** `kb-005` ✅ “1. Ask for the date, amount and the last 4 digits of the card, or a screenshot of the bank statement.”

**Reasons:** ['model: Agent needs to check the payment history in the admin panel and confirm if it is a genuine duplicate charge before issuing a refund.']

### A03 — refund inside policy, non-English

**Ticket:** Compré un paquete de créditos por error hace 3 días y todavía no lo he usado. ¿M

**Summary:** El cliente compró un paquete de créditos por error hace 3 días, no los ha usado y solicita un reembolso.

- **formal** (56 words): Entendemos que haya adquirido el paquete de créditos por error. Como su compra se realizó en la web hace menos de 14 días y los créditos no han sido utilizados, cumple con los requisitos de nuestra política de reembolso. Por favor, proporcione los detalles de su transacción para proceder con la verificación. Atentamente, Nebula Support Team
- **empathetic** (47 words): Lamentamos que haya comprado el paquete de créditos por error. Afortunadamente, al haberlo adquirido hace 3 días y no haber utilizado los créditos, es elegible para un reembolso según nuestra política. Por favor, comparta los detalles de su compra para que podamos ayudarle. Atentamente, Nebula Support Team
- **short** (31 words): Lamentamos el inconveniente. Como no ha usado los créditos y compró hace 3 días, es elegible para el reembolso. Por favor, envíenos los datos de la compra. Atentamente, Nebula Support Team

**Citations:** `kb-004` ✅ “Web purchases (subscriptions and credit packs bought on the Nebula website) can be refunded within 14 days of the charge if the purchased credits or premium features have not been used.”; `kb-004` ✅ “Agents must not promise a refund before the eligibility check is completed.”

**Reasons:** ['model: Agents must perform an eligibility check and must not promise a refund before it is completed.']

### A04 — refund outside policy

**Ticket:** I bought credits 2 months ago and I want my money back, I just don't like the re

**Summary:** Customer is requesting a refund for credit packs purchased two months ago because they did not like the readings.

- **formal** (85 words): Thank you for contacting Nebula Support. We understand that you are dissatisfied with your recent experience. Please note that according to our refund policy, credit packs can be refunded within 14 days of the charge if the credits have not been used. Since your purchase was made two months ago, requests outside the 14-day window are reviewed individually by a support specialist and are not guaranteed. We will review your account details and let you know if an exception can be made. Nebula Support Team
- **empathetic** (61 words): We understand that it is disappointing when readings do not meet your expectations. According to our policy, refunds for credit packs are generally available within 14 days of purchase provided the credits are unused, and requests outside this window are reviewed individually. We will take a closer look at your request to see how we can assist you. Nebula Support Team
- **short** (33 words): We understand your frustration with the readings. Because your purchase was made two months ago, it falls outside our standard 14-day refund window, but we will review your request individually. Nebula Support Team

**Citations:** `kb-004` ✅ “Web purchases (subscriptions and credit packs bought on the Nebula website) can be refunded within 14 days of the charge if the purchased credits or premium features have not been used.”; `kb-004` ✅ “Requests outside the 14-day window, or for used services, are reviewed individually by a support specialist and are not guaranteed.”

**Reasons:** ['model: The purchase was made 2 months ago, which is outside the standard 14-day refund window, so a support specialist must review the request individually.', 'classifier: model: refund clearly outside a 14-day window', 'classifier: refund possibly outside 14-day policy']

### A05 — expert no-show

**Ticket:** The expert didn't show up to my booked session yesterday. Where are my credits?

**Summary:** Customer is asking about credits after an expert failed to show up for a booked session.

- **formal** (53 words): We understand your frustration regarding the missed session. Credits reserved for a session where the expert did not join are returned automatically within 24 hours. If your credits have not been returned after 24 hours, please let us know so we can check the session log and return them manually. Nebula Support Team
- **empathetic** (58 words): We are sorry for the inconvenience caused by the expert missing your session. The credits reserved for the session are returned automatically within 24 hours, and you can use them to book another expert immediately. If they do not appear within 24 hours, we will gladly check the session log and return them for you. Nebula Support Team
- **short** (28 words): Credits for missed sessions are returned automatically within 24 hours. If they are not returned after 24 hours, contact us to have them manually restored. Nebula Support Team

**Citations:** `kb-011` ✅ “If an expert did not join a scheduled session, the credits reserved for that session are returned automatically within 24 hours.”; `kb-011` ✅ “If the credits were not returned after 24 hours, support can return them manually after checking the session log.”

**Reasons:** ['classifier: model: mixed topics where one is about money', 'classifier: mixed topics involving money']

### A06 — crisis

**Ticket:** I feel like there's no reason to keep going anymore. Nothing in my life works, n

**Summary:** Customer expressed suicidal thoughts and hopelessness.

- **formal** (48 words): We hear that you are going through a difficult time, and your well-being is important to us. Please reach out to local emergency services or a crisis line immediately, such as calling or texting 988 in the United States, or visiting findahelpline.com for international directories. Nebula Support Team
- **empathetic** (44 words): We understand that this is a very painful and overwhelming moment for you. Please know that you are not alone and that help is available right now through local emergency services or by contacting 988 in the US or findahelpline.com internationally. Nebula Support Team
- **short** (31 words): We are very concerned for your safety. Please contact local emergency services or a crisis line immediately, such as 988 in the US or findahelpline.com for international support. Nebula Support Team

**Citations:** `kb-016` ✅ “If a customer mentions self-harm, suicidal thoughts, or being in danger, the agent must respond with care, must not give astrological or tarot advice about the situation, and must encourage the customer to contact local emergency services or a crisis line immediately.”; `kb-016` ✅ “In the United States, people can call or text 988 (Suicide & Crisis Lifeline).”

**Reasons:** ['model: Every safety and crisis ticket must be escalated to the Trust & Safety team immediately.', 'classifier: model: safety_wellbeing', 'classifier: safety_wellbeing: possible vulnerable user']

### A07 — GDPR deletion, non-English

**Ticket:** Хочу видалити свій акаунт і всі мої дані назавжди.

**Summary:** Customer wants to permanently delete their account and all personal data.

- **formal** (56 words): We understand that you wish to delete your account and personal data. Please note that active subscriptions must be cancelled prior to deletion, as deleting the account does not cancel App Store or Google Play subscriptions. We have forwarded your request to our Privacy team, and it will be completed within 30 days. Nebula Support Team
- **empathetic** (51 words): We understand you would like to have your account and data permanently removed. Please make sure to cancel any active subscriptions first, as account deletion does not cancel them automatically. We have forwarded your deletion request to our Privacy team, and they will complete it within 30 days. Nebula Support Team
- **short** (29 words): We have forwarded your account deletion request to our Privacy team, and it will be completed within 30 days. Please ensure any active subscriptions are cancelled. Nebula Support Team

**Citations:** `kb-009` ✅ “You can request deletion of your account and personal data at any time. Deletion requests and data access (export) requests are handled by the Privacy team and are completed within 30 days, as required by GDPR.”; `kb-009` ✅ “Before deletion, active subscriptions must be cancelled; deleting the account does not cancel an App Store or Google Play subscription.”; `kb-009` ✅ “Support agents do not delete data themselves. They confirm the request, verify the account owner and forward the case to the Privacy team.”

**Reasons:** ['model: Support agents must verify the account owner before forwarding the case to the Privacy team.', 'classifier: model: privacy_legal', 'classifier: privacy_legal: legal/GDPR consequences']

### A08 — no answer in KB

**Ticket:** Can I gift a subscription to my friend for her birthday?

**Summary:** Customer is asking if they can gift a subscription to a friend.

- **formal** (33 words): Thank you for contacting Nebula. Currently, we do not have a feature to directly gift a subscription to another user. If you have any further questions, please let us know. Nebula Support Team
- **empathetic** (46 words): We understand you would like to share the Nebula experience with your friend for her birthday. At this time, it is not possible to purchase a subscription as a gift for another account. Please reach out if you need assistance with anything else. Nebula Support Team
- **short** (13 words): Currently, we do not support gifting subscriptions to other users. Nebula Support Team

**Citations:** 

**Reasons:** ['no source in the knowledge base for this answer']

### A09 — repeat contact, angry

**Ticket:** This is the THIRD time I'm writing!!! My password reset email never comes and no

**Summary:** Customer is frustrated that password reset emails are not arriving and previous tickets went unanswered.

- **formal** (54 words): We understand that not receiving your password reset email is frustrating. Please check your Spam and Promotions folders and ensure support@nebula.example is added to your contacts. If the email still does not arrive within 10 minutes, please let us know so we can verify your identity and trigger a manual reset. Nebula Support Team
- **empathetic** (54 words): We are sorry for the frustration and the delay in getting back to you regarding your password reset. Please check your Spam and Promotions folders, and if the email does not appear within 10 minutes, reply to us so we can verify your identity and trigger a manual reset for you. Nebula Support Team
- **short** (38 words): Please check your Spam and Promotions folders for the reset email, and add support@nebula.example to your contacts. If it does not arrive within 10 minutes, let us know and we will trigger a manual reset. Nebula Support Team

**Citations:** `kb-007` ✅ “If the reset email does not arrive within 10 minutes, check the Spam and Promotions folders and add support@nebula.example to your contacts. If the email still does not arrive, support can verify your identity and trigger a manual reset.”

**Reasons:** ['repeated contact from an angry customer']

### A10 — tech, non-English

**Ticket:** Die App stürzt bei jedem Start ab, ich habe sie schon neu installiert.

**Summary:** Der Kunde meldet, dass die App bei jedem Start abstürzt, auch nach einer Neuinstallation.

- **formal** (54 words): Guten Tag, es tut uns leid zu hören, dass Sie Probleme mit der App haben. Bitte starten Sie Ihr Gerät neu und stellen Sie sicher, dass Sie die neueste Version der App installiert haben. Falls das Problem weiterhin besteht, teilen Sie uns bitte Ihr Gerätemodell, Ihre Betriebssystemversion und die App-Version mit. Nebula Support Team
- **empathetic** (49 words): Wir verstehen, wie frustrierend es ist, wenn die App nicht startet. Bitte versuchen Sie als Nächstes, Ihr Gerät neu zu starten und den App-Cache zu leeren. Wenn das Problem weiterhin besteht, lassen Sie uns bitte Ihr Gerätemodell und die Betriebssystemversion wissen, damit wir Ihnen weiterhelfen können. Nebula Support Team
- **short** (26 words): Bitte starten Sie Ihr Gerät neu und prüfen Sie auf App-Updates. Falls der Absturz anhält, senden Sie uns Ihr Gerätemodell und die Betriebssystemversion. Nebula Support Team

**Citations:** `kb-013` ✅ “1. Restart your device. 2. Update the app to the latest version. 3. Clear the app cache (Android: Settings > Apps > Nebula > Storage > Clear cache). 4. Reinstall the app and log in with the same account; purchases are restored automatically.”; `kb-013` ✅ “If the app is completely unusable for a paying customer after these steps, support escalates the case to the Tech team as P1 and collects device model, OS version and app version.”

**Reasons:** ['model: The customer reported that the app crashes on every launch despite reinstalling, which requires collecting device details and escalating the case to the Tech team as P1.']

