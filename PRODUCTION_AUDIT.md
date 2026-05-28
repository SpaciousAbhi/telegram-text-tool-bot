# Production Audit

This audit covers the Telegram Text Tool Bot feature set end to end.

## User Flows

- `/start` shows only profile, premium, referral, settings, help, support, two main categories, My Tasks, and System Status.
- Text Style & Fonts opens its category screen and exposes every listed style tool once.
- Text Cleaning & Utility opens its category screen and exposes every listed utility tool once.
- Every tool accepts text, validates empty/long input, shows processing, returns copy-friendly output, and supports retry/back/home/task actions.
- My Tasks supports saved task listing, open result, confirmed delete, confirmed clear history, and restart-safe persistence.
- Settings supports language, output style, auto-save, notifications, privacy mode, confirmed clear data, confirmed reset, terms, and support.
- Profile, Premium, Referral, Help, Support, and System Status are routed through the same access checks as the main menu.

## Admin Flows

- `/admin` is the only admin entry point and rejects non-admins.
- Admin stats read live Mongo counts.
- Broadcast copies text/media/files/forwarded messages to non-banned users, tracks progress, and records completion.
- Premium management adds/removes premium by user ID, and expired premium is cleaned before stats.
- Force Subscription supports global on/off, add, per-channel enable/disable, confirmed delete, join mode, request mode, hidden joined channels, and stored join-request checks.
- Referral settings support rewards on/off, required joins, reward days, and leaderboard.
- Ban/unban, maintenance mode, bot settings, and logs are DB-backed.
- Bot settings update start caption, start photo, support username, update channel, free limit, premium limit, cooldown, and max text length without redeploying.

## Verification

Local verification commands:

```powershell
python -m compileall app tests
python -m pytest -q
python -c "import app.main; import app.handlers; print('imports ok')"
```

Current result:

```text
43 passed
imports ok
```

## Live Runtime Notes

- Real Telegram payments, force-sub membership checks, and broadcast delivery require a real `BOT_TOKEN`.
- Mongo persistence requires a reachable `MONGO_URL`.
- Request-to-join tracking requires the bot to receive `chat_join_request` updates and be an admin in the target channel.
