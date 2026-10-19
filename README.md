# Quiz Battle

A two-player quiz game for the terminal. The game text is in Persian.

Each match has 5 rounds. In each round, both players answer the same multiple-choice question (A–D).

- A correct answer gets **10 points**.
- The fastest correct answer gets **+3 bonus** points.
- An answer that takes more than **30 seconds** gets 0 points.
- On a `"double"` power-up question, correct answers get double points.
- On a `"golden"` question, a correct answer is worth **50 points** instead of 10 (the speed bonus still applies).

A leaderboard, ranked by wins and then by points, is saved to `leaderboard.json`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Play

```bash
python game.py
```

## Test

```bash
pytest
```

## Files

| File | Purpose |
|------|---------|
| `game.py` | Terminal UI (menu, rounds, leaderboard) |
| `engine.py` | Game rules: `Question`, `Match`, scoring |
| `storage.py` | `QuestionBank` (reads `questions.json`) and `ScoreBoard` (`leaderboard.json`) |
| `app_log.py` | Logging setup (writes to `quiz_game.log`) |
| `questions.json` | Question bank |
| `tests/` | pytest tests for the engine and storage |

## Adding questions

Add an entry to `questions.json`:

```json
{
  "text": "Question text",
  "options": ["A", "B", "C", "D"],
  "correct": "A",
  "power_up": "double"
}
```

Each question needs exactly 4 options, and `correct` must be a letter from A to D. `power_up` is optional and can be `"double"` or `"golden"`.

### Golden question

Set `"power_up": "golden"` to make a question golden:

```json
{
  "text": "Question text",
  "options": ["A", "B", "C", "D"],
  "correct": "B",
  "power_up": "golden"
}
```

If the bank has at least one golden question, every match gets **exactly one** of them, at a random round. The points come from `GOLDEN_POINTS` in `engine.py`. To make golden questions appear only by chance, call `bank.pick(n, golden_guaranteed=False)`.

## Error handling

- **`questions.json`**: a missing file, invalid JSON, a wrong structure, or too few valid questions stops the game with a clear message. A single invalid question (missing keys, wrong number of options, unknown `power_up`...) is skipped and written to `quiz_game.log`, and the game warns you.
- **`leaderboard.json`**: if the file is corrupt, it is renamed to `leaderboard.json.corrupt` and the leaderboard starts fresh. Saves are atomic (written to a temp file, then swapped in), so a crash cannot leave a half-written file. If saving fails, the game continues and shows a warning.
- **Game loop**: unexpected errors are logged with a traceback and shown as a short message instead of being silently swallowed. Ctrl+C and Ctrl+D exit cleanly.
