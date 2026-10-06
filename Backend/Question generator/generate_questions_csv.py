import csv
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NUM_OF_QUESTIONS = 10
QUESTIONS_GENERATION_MODEL = "gpt-5.5"
TOTAL_QUESTIONS = 20
OUTPUT_FILE = BASE_DIR.parent / "data" / "questions.csv"
MAX_RETRIES = 2

TOPICS = [
    "Sport",
    "History of Israel",
    "History of the world",
    "Geography",
    "Science",
    "Movies & TV",
    "Technology",
    "Animals",
    "Music",
    "Famous people",
]

PROMPT_TEMPLATE = """Generate {num_of_questions} unique multiple-choice questions on the topic "{topic}".

Return the result as a valid JSON object only.

The JSON object must have this exact structure:

{{
  "questions": [
    {{
      "topic": "{topic}",
      "difficulty": 1,
      "question": "Question text here",
      "options": {{
        "A": "First option",
        "B": "Second option",
        "C": "Third option",
        "D": "Fourth option"
      }},
      "correct_option": "A"
    }}
  ]
}}

Rules:
- Generate exactly {num_of_questions} questions.
- Each question must be unique.
- Each question must have exactly 4 options: A, B, C, and D and only one correct answer.
- correct_option must be one of: A, B, C, or D.
- topic must be "{topic}" for every question.
- difficulty must be an integer from 1 to 10.
- Do not include explanations.
- Do not include text before or after the JSON.
- Do not make the correct answer longer than the others on purpose"""

CSV_FIELDS = [
    "id",
    "topic",
    "difficulty",
    "question",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "correct_option",
]

def build_prompt(topic: str, num_of_questions: int) -> str:
    return PROMPT_TEMPLATE.format(topic=topic, num_of_questions=num_of_questions)


def call_openai(
    client: OpenAI,
    model: str,
    topic: str,
    num_of_questions: int,
    max_retries: int,
) -> dict:
    prompt = build_prompt(topic, num_of_questions)
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.responses.create(
                model=model,
                input=prompt,
            )
            return json.loads(response.output_text)
        except Exception as exc:
            last_error = exc
            if attempt == max_retries:
                break
            time.sleep(2 * attempt)

    raise RuntimeError(f"Failed to generate questions for {topic}: {last_error}")


def validate_question(raw_question: dict, topic: str, question_id: int) -> dict:
    options = raw_question.get("options", {})
    correct_option = raw_question.get("correct_option")

    if raw_question.get("topic") != topic:
        raise ValueError(f"Question topic does not match requested topic: {topic}")
    if not isinstance(raw_question.get("difficulty"), int):
        raise ValueError("Question difficulty must be an integer.")
    if not 1 <= raw_question["difficulty"] <= 10:
        raise ValueError("Question difficulty must be from 1 to 10.")
    if set(options.keys()) != {"A", "B", "C", "D"}:
        raise ValueError("Question must contain exactly options A, B, C, and D.")
    if correct_option not in {"A", "B", "C", "D"}:
        raise ValueError("correct_option must be A, B, C, or D.")

    return {
        "id": question_id,
        "topic": raw_question["topic"],
        "difficulty": raw_question["difficulty"],
        "question": raw_question["question"],
        "option_a": options["A"],
        "option_b": options["B"],
        "option_c": options["C"],
        "option_d": options["D"],
        "correct_option": correct_option,
    }


def get_next_question_id(output_path: Path) -> int:
    if not output_path.exists():
        return 1

    with output_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        existing_ids = [
            int(row["id"])
            for row in reader
            if row.get("id") and row["id"].isdigit()
        ]

    if not existing_ids:
        return 1
    return max(existing_ids) + 1


def generate_questions(
    client: OpenAI,
    model: str,
    total_questions: int,
    num_of_questions: int,
    max_retries: int,
) -> None:
    output_path = Path(OUTPUT_FILE)
    file_exists = output_path.exists()
    next_question_id = get_next_question_id(output_path)
    generated_count = 0
    topic_index = 0

    with output_path.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()

        while generated_count < total_questions:
            topic = TOPICS[topic_index % len(TOPICS)]
            remaining = total_questions - generated_count
            batch_size = min(num_of_questions, remaining)
            print(f"Generating {batch_size} questions for {topic}...")

            data = call_openai(client, model, topic, batch_size, max_retries)
            batch = data.get("questions", [])

            if len(batch) != batch_size:
                raise ValueError(
                    f"Expected {batch_size} questions for {topic}, got {len(batch)}."
                )

            rows = []
            for raw_question in batch:
                row = validate_question(raw_question, topic, next_question_id)
                rows.append(row)
                next_question_id += 1
                generated_count += 1

            writer.writerows(rows)
            csv_file.flush()
            print(f"Stored {generated_count} questions in {OUTPUT_FILE}")

            topic_index += 1


def main() -> None:
    if TOTAL_QUESTIONS <= 0:
        raise ValueError("TOTAL_QUESTIONS must be greater than 0.")
    if NUM_OF_QUESTIONS <= 0:
        raise ValueError("NUM_OF_QUESTIONS must be greater than 0.")
    if not OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY in .env file.")

    client = OpenAI(api_key=OPENAI_API_KEY)
    generate_questions(
        client=client,
        model=QUESTIONS_GENERATION_MODEL,
        total_questions=TOTAL_QUESTIONS,
        num_of_questions=NUM_OF_QUESTIONS,
        max_retries=MAX_RETRIES,
    )
    print(f"Wrote {TOTAL_QUESTIONS} questions to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
