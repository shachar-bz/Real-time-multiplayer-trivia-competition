# Question bank pipeline

The game asks questions from `Backend/data/questions.csv`. This directory holds
the offline scripts that grow and clean that file with LLMs, and the one that
turns it into the SQLite database the server reads. None of them run as part of
the game server.

```
generate_questions  ->  check_answers  ->  dedupe_questions  ->  build_database
 append new rows        drop rows whose     drop questions        data/questions.csv
 to the CSV             answer key looks    that ask the same     -> data/trivia.db
                        wrong               thing twice
```

| Step | Script | What it does | Needs |
| --- | --- | --- | --- |
| 1 | `generate_questions.py` | Asks an OpenAI model for `TOTAL_QUESTIONS` new questions, `NUM_OF_QUESTIONS` per call, cycling through `TOPICS`, and appends them to the CSV batch by batch. | `OPENAI_API_KEY` |
| 2 | `check_answers.py` | Free models on OpenRouter answer every question; a question whose `correct_option` a model disagrees with is deleted. | `OPENROUTER_API_KEY` |
| 3 | `dedupe_questions.py` | Per topic, an OpenAI model groups questions that ask for the same information; the first of each group stays, the rest are deleted. | `OPENAI_API_KEY` |
| 4 | `build_database.py` | Rebuilds the question database from the CSV. No API calls. | nothing |

`csv_store.py` holds the CSV helpers every step shares. Question ids are always
`1..n` in file order: steps 2 and 3 renumber the remaining rows after deleting.

## Running a step

Run every step from the `Backend/` directory, as a module, so the scripts can
import the `trivia` package:

```bash
cd Backend
pip install -r tools/question_bank/requirements.txt   # once

python -m tools.question_bank.generate_questions
python -m tools.question_bank.check_answers
python -m tools.question_bank.dedupe_questions
python -m tools.question_bank.build_database
```

API keys are read from `Backend/.env` (see `Backend/.env.example`). Model
names, batch sizes and topics are constants at the top of each script.

Steps 2 and 3 rewrite `data/questions.csv` in place, so commit (or copy) the
file before running them and review the diff afterwards.

The server builds `data/trivia.db` by itself when the database is missing, but
keeps using an existing one. After changing the CSV, run step 4 (or delete
`data/trivia.db`) so the game picks up the new questions.
