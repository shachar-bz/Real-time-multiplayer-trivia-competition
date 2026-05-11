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
REPETITIVE_RECOGNIZER_MODEL = "gpt-5.4"
QUESTIONS_FILE = BASE_DIR / "questions.csv"
MAX_RETRIES = 2

DEDUPE_PROMPT = """YOU are an expert data analyst specializing in semantic deduplication. You will be provided with a list of trivia questions from a single topic, where each entry is a pair consisting of a unique id and the question text.

Your Task:
Identify groups of questions that are fundamentally asking for the same information, even if the phrasing, syntax, or vocabulary differs.

Requirements:

Grouping: Every set of near-identical or semantically equivalent questions must be grouped together.

Format: Return only a valid JSON object.
Do not include any conversational filler, explanations, or Markdown formatting outside of the JSON block.

Output Structure:
{
  "repetitive_group_A": [id1, id2, id3],
  "repetitive_group_B": [id4, id5]
}
"""


def load_questions_by_topic(csv_path: Path) -> dict[str, list[dict]]:
    questions_by_topic = {}

    with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            question_id = row.get("id")
            topic = row.get("topic")
            question = row.get("question")

            if not question_id or not topic or not question:
                continue

            questions_by_topic.setdefault(topic, []).append(
                {
                    "id": int(question_id),
                    "question": question,
                }
            )

    return questions_by_topic


def call_repetitive_recognizer(
    client: OpenAI,
    model: str,
    topic: str,
    questions: list[dict],
    max_retries: int,
) -> dict:
    prompt = (
        f"{DEDUPE_PROMPT}\n"
        f'Topic: "{topic}"\n'
        f"Questions JSON:\n{json.dumps(questions, ensure_ascii=False)}"
    )
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

    raise RuntimeError(f"Failed to recognize repetitive questions for {topic}: {last_error}")


def get_ids_to_delete(llm_output: dict) -> list[int]:
    ids_to_delete = []

    for group_ids in llm_output.values():
        if not isinstance(group_ids, list) or len(group_ids) < 2:
            continue

        normalized_ids = [int(question_id) for question_id in group_ids]
        ids_to_delete.extend(normalized_ids[1:])

    return ids_to_delete


def print_deleted_questions(ids_to_delete: list[int], questions: list[dict]) -> None:
    ids_to_delete_set = set(ids_to_delete)

    for question in questions:
        if question["id"] in ids_to_delete_set:
            print(f'Deleted question {question["id"]}: {question["question"]}')


def delete_question(ids_to_delete: list[int], csv_file_name: str | Path = QUESTIONS_FILE) -> None:
    if not ids_to_delete:
        return

    csv_path = Path(csv_file_name)
    ids_to_delete_set = {str(question_id) for question_id in ids_to_delete}

    with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = reader.fieldnames
        rows_to_keep = []

        for row in reader:
            if row.get("id") not in ids_to_delete_set:
                rows_to_keep.append(row)

    if not fieldnames:
        raise ValueError(f"{csv_file_name} does not contain a CSV header.")

    for question_id, row in enumerate(rows_to_keep, start=1):
        row["id"] = question_id

    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_to_keep)


def delete_repetitive_questions() -> None:
    if not OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY in .env file.")

    csv_path = QUESTIONS_FILE
    if not csv_path.exists():
        raise FileNotFoundError(f"Could not find {QUESTIONS_FILE}.")

    client = OpenAI(api_key=OPENAI_API_KEY)
    questions_by_topic = load_questions_by_topic(csv_path)
    all_ids_to_delete = []

    for topic, questions in questions_by_topic.items():
        if len(questions) < 2:
            continue

        print(f"Checking repetitive questions for {topic}...")
        llm_output = call_repetitive_recognizer(
            client=client,
            model=REPETITIVE_RECOGNIZER_MODEL,
            topic=topic,
            questions=questions,
            max_retries=MAX_RETRIES,
        )
        topic_ids_to_delete = get_ids_to_delete(llm_output)
        print_deleted_questions(topic_ids_to_delete, questions)
        all_ids_to_delete.extend(topic_ids_to_delete)

    unique_ids_to_delete = sorted(set(all_ids_to_delete))
    delete_question(unique_ids_to_delete)
    print(f"Deleted {len(unique_ids_to_delete)} repetitive questions from {QUESTIONS_FILE}.")


if __name__ == "__main__":
    delete_repetitive_questions()
