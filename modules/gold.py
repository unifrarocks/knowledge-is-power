"""Gold, silver, DXY, US10Y daily snapshot."""
from typing import Any

import yfinance as yf


def get_metals_data(specs: list[dict]) -> list[dict[str, Any]]:
    out = []
    for spec in specs:
        ticker = spec["ticker"]
        name = spec["name"]
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="1mo", auto_adjust=False)
            if len(hist) < 2:
                continue

            last = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2])
            day_pct = (last / prev - 1) * 100 if prev else 0.0

            # Weekly: ~5 trading days back
            week_idx = -6 if len(hist) >= 6 else 0
            week_ref = float(hist["Close"].iloc[week_idx])
            week_pct = (last / week_ref - 1) * 100 if week_ref else 0.0

            # Monthly: first row of the period
            month_ref = float(hist["Close"].iloc[0])
            month_pct = (last / month_ref - 1) * 100 if month_ref else 0.0

            out.append(
                {
                    "ticker": ticker,
                    "name": name,
                    "price": last,
                    "day_pct": day_pct,
                    "week_pct": week_pct,
                    "month_pct": month_pct,
                }
            )
        except Exception as e:
            print(f"  ! {ticker}: {e}")
    return out


def format_metals(rows: list[dict]) -> str:
    if not rows:
        return "## 贵金属 / 美元 / 利率\n\n_数据获取失败_\n"

    lines = ["## 贵金属 / 美元 / 利率\n"]
    lines.append("| 标的 | 现价 | 日 | 周 | 月 |")
    lines.append("|---|---:|---:|---:|---:|")
    for r in rows:
        # ^TNX is in % already (e.g. 4.32 means 4.32%)
        if r["ticker"] == "^TNX":
            price_s = f"{r['price']:.2f}%"
        else:
            price_s = f"{r['price']:,.2f}"
        lines.append(
            f"| **{r['name']}** (`{r['ticker']}`) | {price_s} "
            f"| {r['day_pct']:+.2f}% | {r['week_pct']:+.2f}% | {r['month_pct']:+.2f}% |"
        )
    lines.append("")
    return "\n".join(lines)
