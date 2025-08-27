import asyncio
from typing import Any, Dict, List, Optional

import httpx


class CoinGeckoClient:
    """
    Minimal async client for CoinGecko's public API.

    Notes:
    - Endpoints used are unauthenticated and rate-limited. Keep usage light.
    - Methods return parsed dicts/lists with only fields we need for the bot.
    """

    def __init__(
        self,
        base_url: str = "https://api.coingecko.com/api/v3",
        http_client: Optional[httpx.AsyncClient] = None,
        request_timeout_seconds: float = 15.0,
    ) -> None:
        self.base_url: str = base_url.rstrip("/")
        self._client: httpx.AsyncClient = http_client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(request_timeout_seconds),
            headers={
                "User-Agent": "crypto-telegram-bot/1.0 (+https://github.com/)",
                "Accept": "application/json",
            },
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def resolve_coin_id(self, query: str) -> Optional[str]:
        """
        Resolve a user-provided query (symbol or name) to a CoinGecko coin id.
        Strategy: use /search and pick the coin with the best market_cap_rank.
        """
        normalized_query: str = query.strip().lower()
        if not normalized_query:
            return None

        response: httpx.Response = await self._client.get(
            "/search", params={"query": normalized_query}
        )
        response.raise_for_status()
        data: Dict[str, Any] = response.json()
        coins: List[Dict[str, Any]] = data.get("coins", [])
        if not coins:
            return None

        # Prefer exact symbol match first (case-insensitive), then best market_cap_rank
        exact_symbol_matches: List[Dict[str, Any]] = [
            coin for coin in coins if coin.get("symbol", "").lower() == normalized_query
        ]
        candidate_list: List[Dict[str, Any]] = exact_symbol_matches or coins
        candidate_list.sort(key=lambda c: (c.get("market_cap_rank") or 10**9))
        return candidate_list[0].get("id")

    async def get_simple_price(
        self, coin_id_or_query: str, vs_currency: str = "usd"
    ) -> Optional[Dict[str, Any]]:
        """
        Get current price and 24h change using /simple/price.
        Returns a dict with keys: id, vs_currency, price, change_24h
        """
        resolved_id: Optional[str] = await self.resolve_coin_id(coin_id_or_query)
        if not resolved_id:
            return None

        params: Dict[str, Any] = {
            "ids": resolved_id,
            "vs_currencies": vs_currency,
            "include_24hr_change": "true",
        }
        response: httpx.Response = await self._client.get("/simple/price", params=params)
        response.raise_for_status()
        payload: Dict[str, Any] = response.json()
        coin_data: Optional[Dict[str, Any]] = payload.get(resolved_id)
        if coin_data is None:
            return None

        price_value: Optional[float] = coin_data.get(vs_currency)
        change_value: Optional[float] = coin_data.get(f"{vs_currency}_24h_change")
        if price_value is None:
            return None

        return {
            "id": resolved_id,
            "vs_currency": vs_currency,
            "price": price_value,
            "change_24h": change_value,
        }

    async def get_top_market_cap(
        self, count: int = 5, vs_currency: str = "usd"
    ) -> List[Dict[str, Any]]:
        """
        Get top N coins by market cap with current price and 24h change.
        Returns a list of dicts with id, symbol, name, price, change_24h, market_cap_rank.
        """
        safe_count: int = max(1, min(50, count))
        params: Dict[str, Any] = {
            "vs_currency": vs_currency,
            "order": "market_cap_desc",
            "per_page": safe_count,
            "page": 1,
            "price_change_percentage": "24h",
        }
        response: httpx.Response = await self._client.get("/coins/markets", params=params)
        response.raise_for_status()
        items: List[Dict[str, Any]] = response.json()
        results: List[Dict[str, Any]] = []
        for item in items:
            results.append(
                {
                    "id": item.get("id"),
                    "symbol": (item.get("symbol") or "").upper(),
                    "name": item.get("name"),
                    "market_cap_rank": item.get("market_cap_rank"),
                    "price": item.get("current_price"),
                    "change_24h": item.get("price_change_percentage_24h"),
                }
            )
        return results


async def _smoke_test() -> None:
    client = CoinGeckoClient()
    try:
        price = await client.get_simple_price("btc", "usd")
        print("BTC:", price)
        top3 = await client.get_top_market_cap(3, "usd")
        print("TOP3:", top3)
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(_smoke_test())

