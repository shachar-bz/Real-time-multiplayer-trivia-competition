import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PHONE_A_FRIEND_MODEL = "gpt-5-nano"
PHONE_A_FRIEND_MODEL_SETTINGS = {
    "openai_reasoning_effort": "minimal",
    "max_tokens": 500,
}

PHONE_A_FRIEND_PROMPT = """You are a hilarious "Phone a Friend" lifeline in a quiz game.
this is the question and the possible answer:
{question_data}
Your private certainty level is {confidence} out of 100.
Use that only to decide how strongly to phrase the answer.
You are chaotic and extremely funny, help your friend.
Answer in 2-4 short sentences.
Do not mention any percentage, certainty score, search time, response time, or how long anything took."""


def question_data_for_friend(question):
    options = [
        f"A. {question['option_a']}",
        f"B. {question['option_b']}",
        f"C. {question['option_c']}",
        f"D. {question['option_d']}",
    ]
    return f"Question: {question['question']}\nOptions:\n" + "\n".join(options)


async def call_a_friend(question, confidence):
    if not OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY in .env file.")

    from pydantic_ai import Agent
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    model = OpenAIChatModel(
        PHONE_A_FRIEND_MODEL,
        provider=OpenAIProvider(api_key=OPENAI_API_KEY),
    )
    agent = Agent(model)
    prompt = PHONE_A_FRIEND_PROMPT.format(
        question_data=question_data_for_friend(question),
        confidence=confidence,
    )
    result = await agent.run(prompt, model_settings=PHONE_A_FRIEND_MODEL_SETTINGS)
    return result.output
