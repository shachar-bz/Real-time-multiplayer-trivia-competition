import pytest

from tests.fakes import make_question
from trivia.adapters.openai_friend import MISSING_KEY_MESSAGE, OpenAIFriendAdvisor, build_prompt


def test_prompt_lists_the_question_options_and_confidence():
    prompt = build_prompt(make_question(), confidence=72)
    assert "Question: Question number 1?\nOptions:\nA. Answer A\nB. Answer B" in prompt
    assert "D. Answer D" in prompt
    assert "Your private certainty level is 72 out of 100." in prompt


async def test_a_missing_api_key_is_reported_without_calling_openai():
    advisor = OpenAIFriendAdvisor(api_key=None, model="gpt-5-nano")
    with pytest.raises(RuntimeError, match=MISSING_KEY_MESSAGE):
        await advisor.advise(make_question(), confidence=50)
