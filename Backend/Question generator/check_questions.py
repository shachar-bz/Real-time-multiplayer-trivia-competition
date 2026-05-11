import csv
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parent

load_dotenv(BACKEND_DIR / ".env")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
QUESTIONS_FILE = BASE_DIR / "questions.csv"
QUESTIONS_PER_CALL = 8
MAX_RETRIES = 2

ANSWER_MODELS = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "openai/gpt-oss-120b:free",
    "poolside/laguna-m.1:free",
]

ANSWER_SELECTOR_PROMPT = """You are a multiple-choice answer selector.

You will receive:
- {questions_per_call} questions
- Four possible answers labeled A, B, C, and D for each questions.

Your task is to choose a single correct answer for each question.

Return only the letter of the correct option.

Rules:
- Return exactly one uppercase letter: A, B, C, or D.
- Do not include explanations.
- Do not include punctuation.
- Do not include any extra text.
- If you are unsure, choose the most likely correct answer.

Because there are multiple questions, return one answer per line in the same order as the questions."""


def load_questions(csv_path: Path) -> tuple[list[dict], list[str]]:
    with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if not fieldnames:
        raise ValueError(f"{csv_path} does not contain a CSV header.")

    return rows, fieldnames


def chunk_questions(questions: list[dict], chunk_size: int) -> list[list[dict]]:
    return [
        questions[index:index + chunk_size]
        for index in range(0, len(questions), chunk_size)
    ]


def build_questions_prompt(questions: list[dict]) -> str:
    question_blocks = []

    for index, question in enumerate(questions, start=1):
        question_blocks.append(
            "\n".join(
                [
                    f"Question {index}: {question['question']}",
                    f"A. {question['option_a']}",
                    f"B. {question['option_b']}",
                    f"C. {question['option_c']}",
                    f"D. {question['option_d']}",
                ]
            )
        )

    questions_text = "\n\n".join(question_blocks)
    prompt = ANSWER_SELECTOR_PROMPT.format(questions_per_call=len(questions))
    return (
        f"{prompt}\n\n"
        f"Questions:\n\n"
        f"{questions_text}"
    )


def parse_model_answers(raw_answer: str, expected_answers_count: int) -> list[str]:
    cleaned_answer = raw_answer.strip().upper()
    answers = re.findall(r"\b[A-D]\b", cleaned_answer)

    if len(answers) != expected_answers_count:
        compact_answers = [
            character
            for character in cleaned_answer
            if character in {"A", "B", "C", "D"}
        ]
        answers = compact_answers

    if len(answers) != expected_answers_count:
        raise ValueError(
            f"Expected {expected_answers_count} answers, got {len(answers)}: {raw_answer}"
        )

    return answers


def call_answer_model(
    client: OpenAI,
    model: str,
    questions: list[dict],
    max_retries: int,
) -> list[str]:
    prompt = build_questions_prompt(questions)
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0,
            )
            raw_answer = response.choices[0].message.content or ""
            return parse_model_answers(raw_answer, len(questions))
        except Exception as exc:
            last_error = exc
            if attempt == max_retries:
                break
            time.sleep(2 * attempt)

    raise RuntimeError(f"Failed to check questions with {model}: {last_error}")


def get_wrong_question_ids(questions: list[dict], model_answers: list[str]) -> list[int]:
    wrong_question_ids = []

    for question, model_answer in zip(questions, model_answers):
        correct_option = question["correct_option"].strip().upper()
        if model_answer != correct_option:
            wrong_question_ids.append(int(question["id"]))
            print(
                f'Deleted question {question["id"]}: {question["question"]} '
                f'(model answered {model_answer}, correct answer is {correct_option})'
            )

    return wrong_question_ids


def delete_question(
    ids_to_delete: list[int],
    fieldnames: list[str],
    questions: list[dict],
    csv_file_name: str | Path = QUESTIONS_FILE,
) -> None:
    if not ids_to_delete:
        return

    ids_to_delete_set = {str(question_id) for question_id in ids_to_delete}
    rows_to_keep = [
        question
        for question in questions
        if question.get("id") not in ids_to_delete_set
    ]

    for question_id, question in enumerate(rows_to_keep, start=1):
        question["id"] = question_id

    with Path(csv_file_name).open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_to_keep)


def check_questions() -> None:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("Missing OPENROUTER_API_KEY in .env file.")

    csv_path = QUESTIONS_FILE
    if not csv_path.exists():
        raise FileNotFoundError(f"Could not find {QUESTIONS_FILE}.")

    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
    )
    questions, fieldnames = load_questions(csv_path)
    all_ids_to_delete = []

    for call_index, question_batch in enumerate(chunk_questions(questions, QUESTIONS_PER_CALL)):
        model = ANSWER_MODELS[call_index % len(ANSWER_MODELS)]
        print(f"Checking questions with {model}...")
        model_answers = call_answer_model(
            client=client,
            model=model,
            questions=question_batch,
            max_retries=MAX_RETRIES,
        )
        all_ids_to_delete.extend(get_wrong_question_ids(question_batch, model_answers))

    unique_ids_to_delete = sorted(set(all_ids_to_delete))
    delete_question(unique_ids_to_delete, fieldnames, questions)
    print(f"Deleted {len(unique_ids_to_delete)} difficult questions from {QUESTIONS_FILE}.")


if __name__ == "__main__":
    check_questions()
