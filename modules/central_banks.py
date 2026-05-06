"""Central bank news summary via Gemini's Google Search grounding."""
from google.genai import types


def get_central_bank_summary(
    gemini_client, prompt: str, model: str = "gemini-2.5-flash"
) -> str:
    """Call Gemini with Google Search grounding and return the synthesized text."""
    response = gemini_client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            max_output_tokens=4096,
        ),
    )
    return (response.text or "").strip()


def format_central_banks(text: str) -> str:
    if not text.strip():
        return "## 央行动态\n\n_今日无重大央行动态，或获取失败。_\n"
    return f"## 央行动态\n\n{text.strip()}\n"
