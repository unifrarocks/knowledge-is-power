"""Central bank news summary via Claude's built-in web_search tool."""


def get_central_bank_summary(
    claude_client, prompt: str, model: str = "claude-sonnet-4-6"
) -> str:
    """Call Claude with web_search and return the synthesized text."""
    msg = claude_client.messages.create(
        model=model,
        max_tokens=4096,
        tools=[
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 8,
            }
        ],
        messages=[{"role": "user", "content": prompt}],
    )

    # The response is a mix of server_tool_use, web_search_tool_result, and
    # text blocks. We only want the final text Claude wrote.
    text_parts = [
        b.text for b in msg.content if getattr(b, "type", "") == "text"
    ]
    return "\n\n".join(p for p in text_parts if p.strip())


def format_central_banks(text: str) -> str:
    if not text.strip():
        return "## 央行动态\n\n_今日无重大央行动态，或获取失败。_\n"
    return f"## 央行动态\n\n{text.strip()}\n"
