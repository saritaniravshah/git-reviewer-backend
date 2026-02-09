from openai import OpenAI
from config import OPENROUTER_API_KEY
import json

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

def get_ai_review(prompt: str, model: str = "qwen/qwen3-next-80b-a3b-instruct:free"):
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

def parse_ai_response(response: str) -> dict:
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"error": "Failed to parse AI response", "raw": response}
