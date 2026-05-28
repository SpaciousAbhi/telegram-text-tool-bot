# Telegram Text Tool Bot

Premium category-based Telegram text utility bot built with aiogram 3 and MongoDB.

## Features

- Compact `/start` menu with user navigation and main text categories only.
- Text Style & Fonts tools: stylish text, fancy fonts, bold, italic, underline, strikethrough, monospace, small caps, aesthetic, emoji text, font preview, stylish names, and message formatting.
- Text Cleaning & Utility tools: cleaner, case converter, counters, duplicate-line removal, extra-space removal, emoji removal, link extraction, formatting, slug generation, and simple Base64 encrypt/decrypt.
- MongoDB users, settings, tasks, referrals, premium, force-subscription channels, broadcasts, logs, limits, and admin state.
- `/admin` only admin panel with stats, broadcast, premium management, force subscription, referral settings, ban/unban, maintenance, settings, and logs.
- Telegram Stars premium invoice flow.
- Runtime admin settings for start caption/photo, support username, update channel, limits, cooldown, force subscription, and referral rewards.
- Heroku worker deployment with `Procfile`.

## Required Config

Copy `.env.example` to `.env` locally or set these config vars on Heroku:

```text
BOT_TOKEN
MONGO_URL
ADMIN_IDS
OWNER_IDS
SUPPORT_USERNAME
UPDATE_CHANNEL
```

Optional:

```text
MONGO_DB_NAME
START_PHOTO_URL
FREE_DAILY_LIMIT
PREMIUM_DAILY_LIMIT
MAX_TEXT_CHARS
```

Most operational values can also be changed later from `/admin` -> `BOT SETTINGS`, so redeploying is not required for routine support links, captions, limits, or cooldown changes.

## Run Locally

```powershell
python -m pip install -r requirements.txt
$env:BOT_TOKEN="123456:token"
$env:MONGO_URL="mongodb://localhost:27017/text_tool_bot"
$env:ADMIN_IDS="123456789"
$env:OWNER_IDS="123456789"
python -m app.main
```

## Heroku

```powershell
heroku create your-text-tool-bot
heroku config:set BOT_TOKEN="..." MONGO_URL="..." ADMIN_IDS="123456789" OWNER_IDS="123456789" SUPPORT_USERNAME="support" UPDATE_CHANNEL="updates" -a your-text-tool-bot
git push heroku main
heroku ps:scale worker=1 -a your-text-tool-bot
heroku logs --tail -a your-text-tool-bot
```

The bot uses long polling through a worker dyno. Do not run multiple worker dynos with the same bot token.
