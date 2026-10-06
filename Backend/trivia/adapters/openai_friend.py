"""Phone-a-friend: an OpenAI model (via pydantic-ai) plays the friend on the phone."""

from trivia.domain.questions import OPTION_KEYS, Question

MISSING_KEY_MESSAGE = "Missing OPENAI_API_KEY in .env file."
MODEL_SETTINGS = {
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
Do not mention any percentage, certainty score, search time, response time, or how long anything took."""  # noqa: E501


def build_prompt(question: Question, confidence: int) -> str:
    options = "\n".join(f"{key}. {question.options[key]}" for key in OPTION_KEYS)
    question_data = f"Question: {question.text}\nOptions:\n{options}"
    return PHONE_A_FRIEND_PROMPT.format(question_data=question_data, confidence=confidence)


class OpenAIFriendAdvisor:
    def __init__(self, api_key: str | None, model: str):
        self.api_key = api_key
        self.model = model
        self._agent = None

    async def advise(self, question: Question, confidence: int) -> str:
        if not self.api_key:
            raise RuntimeError(MISSING_KEY_MESSAGE)

        result = await self._get_agent().run(
            build_prompt(question, confidence),
            model_settings=MODEL_SETTINGS,
        )
        return result.output

    def _get_agent(self):
        if self._agent is None:
            # Imported on first use, so starting the server (or running the tests)
            # never loads pydantic-ai until somebody actually phones a friend.
            from pydantic_ai import Agent
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.openai import OpenAIProvider

            model = OpenAIChatModel(self.model, provider=OpenAIProvider(api_key=self.api_key))
            self._agent = Agent(model)
        return self._agent
