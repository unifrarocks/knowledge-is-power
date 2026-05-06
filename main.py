"""Daily brief orchestrator.

Reads config.yaml, fetches each section, writes daily/YYYY-MM-DD.md.
Each section is independently try/except'd so one failure doesn't kill the brief.
"""
import datetime as dt
import os
import sys
import traceback

import yaml
from google import genai

from modules import central_banks, gold, stocks, zsxq


def _section_or_error(label: str, fn) -> str:
    try:
        return fn()
    except Exception as e:
        print(f"[{label}] FAILED: {e}", file=sys.stderr)
        traceback.print_exc()
        return f"## {label}\n\n_⚠️ 该模块运行失败：`{e}`_\n"


def main() -> None:
    config = yaml.safe_load(open("config.yaml", encoding="utf-8"))
    cookie = os.environ.get("ZSXQ_COOKIE", "")
    if not cookie:
        print("WARN: ZSXQ_COOKIE not set — 知识星球 section will be skipped.")

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY (or GOOGLE_API_KEY) not set", file=sys.stderr)
        sys.exit(1)
    gemini = genai.Client(api_key=api_key)
    model = config.get("model", "gemini-2.5-flash")

    # HK timezone for the file name (cron runs at 23:00 UTC = 07:00 HK next day).
    hk_now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    today_str = hk_now.strftime("%Y-%m-%d")
    timestamp = hk_now.strftime("%Y-%m-%d %H:%M %Z")

    sections: list[str] = []
    sections.append(f"# 每日简报 — {today_str}")
    sections.append(f"_生成时间: {timestamp}_\n")

    # 1. Central banks (macro context first)
    print("→ Fetching central bank news...")
    sections.append(
        _section_or_error(
            "央行动态",
            lambda: central_banks.format_central_banks(
                central_banks.get_central_bank_summary(
                    gemini, config["central_bank_prompt"], model=model
                )
            ),
        )
    )

    # 2. AI supply chain movers
    print("→ Fetching AI stock movers...")
    threshold = float(config.get("stock_threshold_pct", 2.0))
    sections.append(
        _section_or_error(
            "AI 产业链异动",
            lambda: stocks.format_movers(
                stocks.get_movers(config["ai_tickers"], threshold_pct=threshold),
                threshold_pct=threshold,
            ),
        )
    )

    # 3. Gold / DXY / yields
    print("→ Fetching metals & rates...")
    sections.append(
        _section_or_error(
            "贵金属 / 美元 / 利率",
            lambda: gold.format_metals(gold.get_metals_data(config["gold_tickers"])),
        )
    )

    # 4. 知识星球
    print("→ Fetching 知识星球...")
    if cookie:
        zsxq_parts = ["## 知识星球摘要\n"]
        for planet in config["planets"]:
            name = planet["name"]
            gid = planet["group_id"]
            if gid == "REPLACE_ME":
                zsxq_parts.append(
                    f"### {name}\n\n_⚠️ group_id 未配置，跳过_\n"
                )
                continue
            print(f"  · {name}")
            zsxq_parts.append(
                _section_or_error(
                    name,
                    lambda p=planet: zsxq.summarize_planet(
                        p["name"],
                        zsxq.fetch_topics(
                            p["group_id"],
                            cookie,
                            lookback_hours=config.get("zsxq_lookback_hours", 24),
                        ),
                        gemini,
                        config["prompts"][p["prompt_style"]],
                        model=model,
                    ),
                )
            )
        sections.append("\n".join(zsxq_parts))
    else:
        sections.append(
            "## 知识星球摘要\n\n_⚠️ ZSXQ_COOKIE 环境变量未配置，跳过_\n"
        )

    # Write output
    os.makedirs("daily", exist_ok=True)
    out_path = f"daily/{today_str}.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(sections))
    print(f"\n✓ Wrote {out_path}")


if __name__ == "__main__":
    main()
