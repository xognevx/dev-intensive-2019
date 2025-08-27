# Crypto Telegram Bot

Simple Telegram bot that fetches cryptocurrency prices using CoinGecko.

## Features

- /price <coin> [vs] — Get current price and 24h change (default vs=USD)
- /top [n] [vs] — Top N coins by market cap with price and 24h change
- Robust symbol search (e.g., "btc", "bitcoin")

## Setup

1. Create a Telegram bot with BotFather and get the token.
2. Clone/copy this project to your machine.
3. Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. Configure environment variables:

```bash
cp .env.example .env
# edit .env and set TELEGRAM_BOT_TOKEN
```

## Run

```bash
python bot.py
```

The bot uses polling. Ensure the `TELEGRAM_BOT_TOKEN` is set.

## Usage Examples

In your Telegram chat with the bot:

- /price btc
- /price eth eur
- /price sol vs=usd
- /top 5
- /top 10 eur

## Notes

- This bot uses CoinGecko's public API. It may be rate-limited under heavy usage.
- The code is async and uses `python-telegram-bot` v21 and `httpx`.
