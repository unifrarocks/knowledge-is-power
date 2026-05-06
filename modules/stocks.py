"""Fetch AI supply-chain stock movers via yfinance."""
from typing import Any

import yfinance as yf


def get_movers(
    ai_tickers: dict[str, list[str]], threshold_pct: float = 2.0
) -> list[dict[str, Any]]:
    """Return tickers whose last-close vs prior-close exceeds threshold_pct."""
    movers: list[dict[str, Any]] = []

    for category, tickers in ai_tickers.items():
        for ticker in tickers:
            try:
                t = yf.Ticker(ticker)
                # 5d covers weekends/holidays; we want the last 2 trading days.
                hist = t.history(period="5d", auto_adjust=False)
                if len(hist) < 2:
                    continue

                prev_close = float(hist["Close"].iloc[-2])
                last_close = float(hist["Close"].iloc[-1])
                if prev_close == 0:
                    continue
                pct = (last_close / prev_close - 1) * 100

                if abs(pct) < threshold_pct:
                    continue

                # info can be slow / flaky — fall back to ticker symbol as name.
                try:
                    name = t.info.get("shortName") or t.info.get("longName") or ticker
                except Exception:
                    name = ticker

                movers.append(
                    {
                        "ticker": ticker,
                        "name": name,
                        "category": category,
                        "pct_change": pct,
                        "price": last_close,
                        "prev_close": prev_close,
                        "currency": _currency_for(ticker),
                    }
                )
            except Exception as e:
                print(f"  ! {ticker}: {e}")
                continue

    movers.sort(key=lambda m: abs(m["pct_change"]), reverse=True)
    return movers


def _currency_for(ticker: str) -> str:
    """Quick guess at the price currency from the suffix."""
    if ticker.endswith(".HK"):
        return "HKD"
    if ticker.endswith(".TW"):
        return "TWD"
    if ticker.endswith(".KS"):
        return "KRW"
    if ticker.endswith(".T"):
        return "JPY"
    if ticker.endswith(".SS") or ticker.endswith(".SZ"):
        return "CNY"
    return "USD"


def format_movers(movers: list[dict], threshold_pct: float) -> str:
    if not movers:
        return (
            f"## AI 产业链异动 (>{threshold_pct}%)\n\n"
            f"_今日所有标的均在 ±{threshold_pct}% 区间内。_\n"
        )

    lines = [f"## AI 产业链异动 (>{threshold_pct}%)\n"]

    by_cat: dict[str, list[dict]] = {}
    for m in movers:
        by_cat.setdefault(m["category"], []).append(m)

    for cat, items in by_cat.items():
        lines.append(f"### {cat}")
        for m in items:
            arrow = "🔺" if m["pct_change"] > 0 else "🔻"
            ccy = m["currency"]
            price_str = f"{m['price']:,.2f} {ccy}"
            lines.append(
                f"- {arrow} **{m['name']}** (`{m['ticker']}`): "
                f"{m['pct_change']:+.2f}% — {price_str}"
            )
        lines.append("")

    return "\n".join(lines)
