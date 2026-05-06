"""Fetch and summarize 知识星球 topics from the past N hours."""
import datetime as dt
import time
import uuid
from typing import Any

import requests
from google.genai import types

# Matches the path used by the current zsxq web client (wx.zsxq.com).
ZSXQ_API = "https://api.zsxq.com/v2/groups/{group_id}/topics"
WEB_URL = "https://wx.zsxq.com/group/{group_id}/topic/{topic_id}"

# These mirror the zsxq web client's request signature. zsxq's API does a
# version check and returns code:2 ("版本太旧") if X-Version is missing.
# Update X-Version periodically if zsxq starts rejecting requests again —
# read the current value from a real browser request in DevTools → Network.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/147.0.0.0 Safari/537.36"
)
ZSXQ_VERSION = "2.91.0"


def _parse_zsxq_time(s: str) -> dt.datetime:
    """zsxq returns timestamps like '2026-05-04T08:30:45.123+0800'."""
    # Python's fromisoformat on 3.11+ handles this fine, but we normalize the
    # microseconds in case the format changes.
    return dt.datetime.fromisoformat(s)


def _extract_text(topic: dict) -> tuple[str, str]:
    """Return (title, body) from a topic dict."""
    ttype = topic.get("type", "")
    title = ""
    body = ""

    if ttype == "talk":
        talk = topic.get("talk", {}) or {}
        body = talk.get("text", "") or ""
        article = talk.get("article")
        if article:
            title = article.get("title", "") or title
            # Article posts have their core content in `article`, not `text`.
            article_text = article.get("article_summary") or article.get("text") or ""
            if article_text and article_text not in body:
                body = (body + "\n\n" + article_text).strip()
    elif ttype == "q&a":
        q = (topic.get("question", {}) or {}).get("text", "") or ""
        a = (topic.get("answer", {}) or {}).get("text", "") or ""
        title = q[:60].replace("\n", " ")
        body = f"Q: {q}\n\nA: {a}"
    elif ttype == "task":
        task = topic.get("task", {}) or {}
        title = task.get("text", "")[:60]
        body = task.get("text", "")
    else:
        # Unknown type — best effort
        body = str(topic.get("text", "") or "")

    if not title:
        title = (body[:60] or "(无标题)").replace("\n", " ")

    return title.strip(), body.strip()


def fetch_topics(
    group_id: str, cookie: str, lookback_hours: int = 24, count: int = 30
) -> list[dict[str, Any]]:
    """Fetch recent topics for one planet, filtered to the lookback window."""
    headers = {
        "Cookie": cookie,
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Origin": "https://wx.zsxq.com",
        "Referer": "https://wx.zsxq.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "X-Version": ZSXQ_VERSION,
        "X-Request-Id": uuid.uuid4().hex,
        "X-Timestamp": str(int(time.time())),
    }
    params = {"scope": "all", "count": count}
    url = ZSXQ_API.format(group_id=group_id)

    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if not data.get("succeeded"):
        raise RuntimeError(f"zsxq API error: {data}")

    raw_topics = (data.get("resp_data") or {}).get("topics", [])

    # Compute cutoff in the same tz as zsxq's timestamps (Asia/Shanghai +0800).
    tz = dt.timezone(dt.timedelta(hours=8))
    cutoff = dt.datetime.now(tz=tz) - dt.timedelta(hours=lookback_hours)

    out = []
    for t in raw_topics:
        try:
            ct = _parse_zsxq_time(t["create_time"])
        except (KeyError, ValueError):
            continue
        if ct < cutoff:
            continue

        title, body = _extract_text(t)
        if not body:
            continue

        out.append(
            {
                "topic_id": t.get("topic_id"),
                "title": title,
                "body": body,
                "create_time": t["create_time"],
                "url": WEB_URL.format(group_id=group_id, topic_id=t.get("topic_id")),
                "digested": t.get("digested", False),
                "likes": t.get("likes_count", 0),
                "comments": t.get("comments_count", 0),
            }
        )

    return out


def summarize_planet(
    planet_name: str,
    topics: list[dict],
    gemini_client,
    prompt_template: str,
    model: str = "gemini-2.5-flash",
) -> str:
    """Return a Markdown section for one planet."""
    if not topics:
        return f"### {planet_name}\n\n_过去24小时无新内容_\n"

    # Build the bundled content. Truncate each post to 4k chars to keep totals
    # reasonable (some 兔主席 posts are very long).
    parts = []
    for t in topics:
        body = t["body"]
        if len(body) > 4000:
            body = body[:4000] + "...[已截断]"
        parts.append(
            f"---\n"
            f"标题: {t['title']}\n"
            f"时间: {t['create_time']}\n"
            f"链接: {t['url']}\n"
            f"赞/评: {t['likes']}/{t['comments']}\n\n"
            f"{body}\n"
        )
    content = "\n\n".join(parts)

    prompt = prompt_template.format(planet=planet_name, content=content)

    response = gemini_client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=4096),
    )
    text = (response.text or "").strip()

    # Make sure the planet name appears as a level-3 heading at the top.
    return f"### {planet_name}\n\n{text}\n"
