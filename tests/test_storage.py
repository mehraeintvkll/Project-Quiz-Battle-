import json

import pytest

from storage import QuestionBank, ScoreBoard, QuestionBankError, ScoreBoardError


SAMPLE = [
    {"text": f"سؤال {i}", "options": ["الف", "ب", "پ", "ت"],
     "correct": "B", "power_up": "double" if i == 1 else None, "category": "آزمایشی"}
    for i in range(1, 9)
]


def make_bank(tmp_path, items=None) -> QuestionBank:
    path = tmp_path / "questions.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items or SAMPLE, f, ensure_ascii=False, indent=2)
    return QuestionBank(str(path))

def test_bank_reads_every_question_from_the_file(tmp_path):
    bank = make_bank(tmp_path)
    assert bank.count() == 8


def test_bank_reads_the_power_up_too(tmp_path):
    bank = make_bank(tmp_path)
    assert any(q.power_up == "double" for q in bank.pick(8))


def test_picked_questions_are_never_repeated(tmp_path):
    bank = make_bank(tmp_path)
    picked = bank.pick(5)
    assert len({q.text for q in picked}) == 5


def test_picking_more_than_the_bank_has_is_refused(tmp_path):
    import pytest
    bank = make_bank(tmp_path)
    with pytest.raises(ValueError):
        bank.pick(99)

def test_a_new_scoreboard_is_empty(tmp_path):
    board = ScoreBoard(str(tmp_path / "leaderboard.json"))
    assert board.is_empty()


def test_the_leaderboard_survives_a_restart(tmp_path):
    path = str(tmp_path / "leaderboard.json")

    board = ScoreBoard(path)
    board.record("سارا", "علی", 30, "سارا", 39)

    again = ScoreBoard(path)                  # انگار برنامه بسته و دوباره باز شد
    assert not again.is_empty()
    assert dict(again.top(5))["سارا"] == {"wins": 1, "points": 39}
    assert dict(again.top(5))["علی"] == {"wins": 0, "points": 30}


def test_points_add_up_across_matches(tmp_path):
    path = str(tmp_path / "leaderboard.json")
    board = ScoreBoard(path)
    board.record("علی", "علی", 20, "رضا", 10)
    board.record("علی", "علی", 15, "رضا", 30)

    assert dict(board.top(5))["علی"] == {"wins": 2, "points": 35}


def test_a_draw_gives_points_but_no_win(tmp_path):
    board = ScoreBoard(str(tmp_path / "leaderboard.json"))
    board.record(None, "علی", 12, "رضا", 12)

    assert dict(board.top(5))["علی"] == {"wins": 0, "points": 12}
    assert dict(board.top(5))["رضا"] == {"wins": 0, "points": 12}


def test_top_sorts_by_wins_then_points(tmp_path):
    board = ScoreBoard(str(tmp_path / "leaderboard.json"))
    board.record("سارا", "سارا", 10, "علی", 90)      # سارا ۱ برد، علی امتیاز بیشتر
    board.record(None, "رها", 5, "علی", 5)

    assert [name for name, _ in board.top(5)] == ["سارا", "علی", "رها"]


def test_persian_names_stay_persian_in_the_file(tmp_path):
    path = tmp_path / "leaderboard.json"
    ScoreBoard(str(path)).record("سارا", "علی", 1, "سارا", 2)

    raw = path.read_text(encoding="utf-8")
    assert "سارا" in raw
    assert "\\u" not in raw


# ---------- سؤال طلایی در بانک ----------

def make_item(i, power_up=None):
    return {"text": f"سؤال {i}", "options": ["الف", "ب", "پ", "ت"],
            "correct": "A", "power_up": power_up}


def test_every_match_gets_exactly_one_golden_question(tmp_path):
    items = [make_item(i) for i in range(6)] + [make_item(10, "golden"), make_item(11, "golden")]
    bank = make_bank(tmp_path, items)

    for _ in range(50):
        picked = bank.pick(5)
        assert len(picked) == 5
        assert sum(q.is_golden() for q in picked) == 1
        assert len({q.text for q in picked}) == 5


def test_golden_is_not_forced_when_the_bank_has_none(tmp_path):
    bank = make_bank(tmp_path, [make_item(i) for i in range(6)])
    assert not any(q.is_golden() for q in bank.pick(5))


def test_golden_guarantee_can_be_turned_off(tmp_path):
    items = [make_item(i) for i in range(30)] + [make_item(99, "golden")]
    bank = make_bank(tmp_path, items)

    picks = [sum(q.is_golden() for q in bank.pick(5, golden_guaranteed=False)) for _ in range(200)]
    assert 0 in picks            # بعضی مسابقه‌ها بدون طلایی‌اند


def test_picking_everything_still_works_with_golden(tmp_path):
    items = [make_item(i) for i in range(5)] + [make_item(10, "golden")]
    bank = make_bank(tmp_path, items)

    assert len(bank.pick(6)) == 6


def test_pick_needs_a_positive_count(tmp_path):
    bank = make_bank(tmp_path)
    with pytest.raises(ValueError):
        bank.pick(0)


# ---------- کنترل خطا: فایل سؤال‌ها ----------

def test_missing_question_file_gives_a_clear_error(tmp_path):
    with pytest.raises(QuestionBankError):
        QuestionBank(str(tmp_path / "nope.json"))


def test_broken_json_gives_a_clear_error(tmp_path):
    path = tmp_path / "questions.json"
    path.write_text("[ {\"text\": ", encoding="utf-8")
    with pytest.raises(QuestionBankError):
        QuestionBank(str(path))


def test_question_file_must_hold_a_list(tmp_path):
    path = tmp_path / "questions.json"
    path.write_text('{"text": "سؤال"}', encoding="utf-8")
    with pytest.raises(QuestionBankError):
        QuestionBank(str(path))


def test_a_file_that_is_not_utf8_is_reported(tmp_path):
    path = tmp_path / "questions.json"
    path.write_bytes("[]".encode("utf-16"))
    with pytest.raises(QuestionBankError):
        QuestionBank(str(path))


def test_invalid_questions_are_skipped_not_fatal(tmp_path):
    items = [make_item(i) for i in range(6)] + [
        {"text": "گزینه کم", "options": ["الف", "ب"], "correct": "A"},
        {"text": "جواب بد", "options": ["الف", "ب", "پ", "ت"], "correct": "Z"},
        {"text": "بدون جواب", "options": ["الف", "ب", "پ", "ت"]},
        "این اصلاً سؤال نیست",
        make_item(50, "triple"),
    ]
    bank = make_bank(tmp_path, items)

    assert bank.count() == 6
    assert len(bank.skipped) == 5


def test_too_few_valid_questions_is_an_error(tmp_path):
    items = [make_item(i) for i in range(3)] + [{"text": "خراب"}]
    with pytest.raises(QuestionBankError):
        make_bank(tmp_path, items)


def test_a_file_saved_with_bom_is_still_readable(tmp_path):
    path = tmp_path / "questions.json"
    path.write_text(json.dumps([make_item(i) for i in range(5)], ensure_ascii=False),
                    encoding="utf-8-sig")
    assert QuestionBank(str(path)).count() == 5


# ---------- کنترل خطا: فایل رده‌بندی ----------

def test_a_corrupt_leaderboard_is_backed_up_and_restarted(tmp_path):
    path = tmp_path / "leaderboard.json"
    path.write_text("{ این JSON نیست", encoding="utf-8")

    board = ScoreBoard(str(path))

    assert board.is_empty()
    assert board.load_warning
    assert (tmp_path / "leaderboard.json.corrupt").exists()     # نسخه‌ی خراب از بین نرفته
    board.record("علی", "علی", 10, "رضا", 5)                   # و بازی می‌تواند ادامه دهد
    assert ScoreBoard(str(path)).load_warning is None


def test_a_leaderboard_with_the_wrong_shape_is_treated_as_corrupt(tmp_path):
    for bad in ('["a", "b"]', '{"علی": 5}', '{"علی": {"wins": "x", "points": 1}}',
                '{"علی": {"wins": -1, "points": 1}}'):
        path = tmp_path / "leaderboard.json"
        path.write_text(bad, encoding="utf-8")

        board = ScoreBoard(str(path))

        assert board.is_empty(), bad
        assert board.load_warning, bad
        path.unlink(missing_ok=True)
        for old in tmp_path.glob("leaderboard.json.*"):
            old.unlink()


def test_an_unreadable_leaderboard_raises_scoreboard_error(tmp_path):
    # مسیر یک پوشه است، نه فایل → خواندنش OSError می‌دهد
    with pytest.raises(ScoreBoardError):
        ScoreBoard(str(tmp_path))


def test_failed_save_raises_but_keeps_the_result_in_memory(tmp_path):
    board = ScoreBoard(str(tmp_path / "no_such_folder" / "leaderboard.json"))

    with pytest.raises(ScoreBoardError):
        board.record("علی", "علی", 10, "رضا", 5)

    assert dict(board.top(5))["علی"] == {"wins": 1, "points": 10}


def test_saving_leaves_no_temp_file_behind(tmp_path):
    path = tmp_path / "leaderboard.json"
    ScoreBoard(str(path)).record("علی", "علی", 10, "رضا", 5)

    assert [p.name for p in tmp_path.iterdir()] == ["leaderboard.json"]


def test_record_refuses_bad_input(tmp_path):
    board = ScoreBoard(str(tmp_path / "leaderboard.json"))

    with pytest.raises(ValueError):
        board.record("علی", "علی", 10, "علی", 5)          # دو بازیکن هم‌نام
    with pytest.raises(ValueError):
        board.record("علی", "علی", -1, "رضا", 5)          # امتیاز منفی
    with pytest.raises(ValueError):
        board.record("غریبه", "علی", 1, "رضا", 5)         # برنده‌ای که بازی نکرده
    with pytest.raises(ValueError):
        board.record(None, "", 1, "رضا", 5)               # نام خالی

    assert board.is_empty()                               # هیچ‌کدام چیزی ثبت نکرد
