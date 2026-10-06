"""Multiple-choice questions."""

from dataclasses import dataclass

OPTION_KEYS = ("A", "B", "C", "D")


@dataclass(frozen=True)
class Question:
    id: int
    topic: str
    difficulty: int
    text: str
    options: dict[str, str]  # option key ("A".."D") -> answer text
    correct_option: str

    @property
    def correct_answer(self) -> str:
        return self.options[self.correct_option]

    @property
    def wrong_options(self) -> list[str]:
        return [key for key in OPTION_KEYS if key != self.correct_option]

    def is_correct(self, option: str | None) -> bool:
        return option == self.correct_option
