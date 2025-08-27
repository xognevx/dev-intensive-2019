import asyncio
import logging
import os
from typing import List, Optional, Tuple

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from crypto_client import CoinGeckoClient


load_dotenv()

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("crypto-bot")


def _parse_price_args(args: List[str]) -> Tuple[Optional[str], str]:
    """Parse arguments for /price command. Returns (coin_query, vs_currency)."""
    if not args:
        return None, "usd"

    coin_query: Optional[str] = None
    vs_currency: str = "usd"

    # Accept forms like: /price btc, /price btc usd, /price btc vs=eur
    for token in args:
        lowered = token.strip().lower()
        if lowered.startswith("vs="):
            vs_currency = lowered.split("=", 1)[1] or vs_currency
        elif coin_query is None:
            coin_query = lowered
        else:
            # Treat second positional as vs_currency if provided
            vs_currency = lowered

    return coin_query, vs_currency


def _format_change(change: Optional[float]) -> str:
    if change is None:
        return "?"
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.2f}%"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Welcome! Use /price <coin> [vs] e.g. /price btc usd, and /top [n] [vs]."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        """
Commands:
/start - Welcome and basic usage
/help - This help
/price <coin> [vs] or /price <coin> vs=<currency> - Show price
/top [n] [vs] - Top N coins by market cap
Examples:
  /price btc
  /price eth eur
  /price sol vs=usd
  /top 5 eur
        """.strip()
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    coin_query, vs_currency = _parse_price_args(context.args or [])
    if not coin_query:
        await update.message.reply_text(
            "Usage: /price <coin> [vs] e.g. /price btc usd"
        )
        return

    client: CoinGeckoClient = context.application.bot_data["coingecko_client"]
    try:
        result = await client.get_simple_price(coin_query, vs_currency)
    except Exception as exc:
        logger.exception("Error fetching price: %s", exc)
        await update.message.reply_text("Failed to fetch price. Try again later.")
        return

    if not result:
        await update.message.reply_text("Coin not found or no data available.")
        return

    price_value = result["price"]
    change_text = _format_change(result.get("change_24h"))
    vs = result["vs_currency"].upper()
    coin_id = result["id"]
    text = f"<b>{coin_id}</b>\nPrice: <b>{price_value:.6g} {vs}</b>\n24h: {change_text}"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


def _parse_top_args(args: List[str]) -> Tuple[int, str]:
    count: int = 5
    vs_currency: str = "usd"
    if not args:
        return count, vs_currency
    # Accept /top 10, /top 10 eur, /top eur
    first = args[0].lower()
    if first.isdigit():
        count = int(first)
        if len(args) > 1:
            vs_currency = args[1].lower()
    else:
        vs_currency = first
        if len(args) > 1 and args[1].isdigit():
            count = int(args[1])
    return count, vs_currency


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    count, vs_currency = _parse_top_args(context.args or [])
    client: CoinGeckoClient = context.application.bot_data["coingecko_client"]

    try:
        items = await client.get_top_market_cap(count, vs_currency)
    except Exception as exc:
        logger.exception("Error fetching top list: %s", exc)
        await update.message.reply_text("Failed to fetch top coins. Try again later.")
        return

    if not items:
        await update.message.reply_text("No data available.")
        return

    lines: List[str] = []
    for item in items:
        price_value = item.get("price")
        change_text = _format_change(item.get("change_24h"))
        rank_text = f"#{item.get('market_cap_rank')}" if item.get("market_cap_rank") else ""
        symbol_text = item.get("symbol") or "?"
        name_text = item.get("name") or item.get("id") or "?"
        lines.append(
            f"{rank_text} <b>{symbol_text}</b> {name_text}: <b>{price_value:.6g} {vs_currency.upper()}</b> ({change_text})"
        )

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def on_startup(application: Application) -> None:
    application.bot_data["coingecko_client"] = CoinGeckoClient()
    logger.info("CoinGecko client initialized")


async def on_shutdown(application: Application) -> None:
    client: CoinGeckoClient = application.bot_data.get("coingecko_client")
    if client:
        await client.aclose()
        logger.info("CoinGecko client closed")


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    token = require_env("TELEGRAM_BOT_TOKEN")
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("price", price))
    application.add_handler(CommandHandler("top", top))

    application.run_polling(
        allowed_updates=None,
        close_loop=False,
        stop_signals=None,
        drop_pending_updates=True,
        poll_interval=1.5,
        bootstrap_retries=3,
        before_startup=on_startup,
        after_shutdown=on_shutdown,
    )


if __name__ == "__main__":
    main()

