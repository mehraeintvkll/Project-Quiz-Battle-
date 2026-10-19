import pytest

from engine import Match, Question, ROUNDS, POINTS, SPEED_BONUS, TIME_LIMIT, GOLDEN_POINTS


def make_questions(power_up: str | None = None) -> list[Question]:
    return [Question("۲+۲؟", ["4", "5", "6", "7"], "A", power_up) for _ in range(ROUNDS)]


def make_match(power_up: str | None = None) -> Match:
    return Match("علی", "رضا", make_questions(power_up))

def test_correct_answer_gives_points():
    m = make_match()
    m.start_round()
    m.submit("علی", "A", 5.0)
    m.submit("رضا", "B", 8.0)
    m.resolve_round()

    assert m.score_of("علی") == POINTS + SPEED_BONUS
    assert m.score_of("رضا") == 0


def test_speed_bonus_goes_to_the_faster_player():
    m = make_match()
    m.start_round()
    m.submit("علی", "A", 12.0)
    m.submit("رضا", "A", 4.0)
    m.resolve_round()

    assert m.score_of("رضا") == 13
    assert m.score_of("علی") == 10


def test_no_bonus_when_both_are_wrong():
    m = make_match()
    m.start_round()
    m.submit("علی", "B", 2.0)
    m.submit("رضا", "C", 3.0)
    m.resolve_round()

    assert m.score_of("علی") == 0
    assert m.score_of("رضا") == 0


def test_wrong_answer_is_marked_wrong():
    m = make_match()
    m.start_round()
    m.submit("علی", "A", 5.0)
    m.submit("رضا", "D", 5.0)
    results = m.resolve_round()

    assert results["علی"].status == "correct"
    assert results["رضا"].status == "wrong"


def test_answer_is_not_case_sensitive():
    m = make_match()
    m.start_round()
    m.submit("علی", " a ", 5.0)
    m.submit("رضا", "B", 5.0)
    m.resolve_round()

    assert m.score_of("علی") == 13

def test_late_answer_gets_nothing():
    m = make_match()
    m.start_round()
    m.submit("علی", "A", TIME_LIMIT + 1)
    m.submit("رضا", "A", 5.0)
    results = m.resolve_round()

    assert results["علی"].status == "too_late"
    assert m.score_of("علی") == 0
    assert m.score_of("رضا") == 13


def test_late_but_correct_still_gets_nothing():
    m = make_match()
    m.start_round()
    m.submit("علی", "A", 99.0)
    m.submit("رضا", "B", 99.0)
    m.resolve_round()

    assert m.score_of("علی") == 0

# def test_double_power_up_doubles_the_points():
#     """قاعده‌ی تیمِ ما: اول بونوس سرعت، بعد دوبل → (۱۰+۳)×۲ = ۲۶

#     این تست، **تصمیمِ تیم** را سند می‌کند. اگر تیمی قاعده‌ی دیگری بخواهد
#        — مثلاً ۱۰×۲+۳ — هم کد و هم همین تست عوض می‌شود. تست، قانونِ نوشته‌شده است.
#     """
#     m = make_match("double")
#     m.start_round()
#     m.submit("علی", "A", 3.0)
#     m.submit("رضا", "A", 9.0)
#     m.resolve_round()

#     assert m.score_of("علی") == (POINTS + SPEED_BONUS) * 2    # ۲۶
#     assert m.score_of("رضا") == POINTS * 2                    # ۲۰


# def test_double_does_not_reward_a_wrong_answer():
#     m = make_match("double")
#     m.start_round()
#     m.submit("علی", "C", 3.0)
#     m.submit("رضا", "C", 4.0)
#     m.resolve_round()

#     assert m.score_of("علی") == 0
#     assert m.score_of("رضا") == 0


def test_winner_is_the_one_with_more_points():
    m = make_match()
    for _ in range(ROUNDS):
        m.start_round()
        m.submit("علی", "A", 2.0)
        m.submit("رضا", "B", 2.0)
        m.resolve_round()

    assert m.is_over()
    assert m.winner() == "علی"


def test_a_draw_has_no_winner():
    m = make_match()
    for _ in range(ROUNDS):
        m.start_round()
        m.submit("علی", "B", 2.0)
        m.submit("رضا", "C", 2.0)
        m.resolve_round()

    assert m.winner() is None


def test_match_is_not_over_before_the_last_round():
    m = make_match()
    m.start_round()
    assert not m.is_over()

def test_two_players_cannot_have_the_same_name():
    with pytest.raises(ValueError):
        Match("علی", "علی", make_questions())


def test_a_stranger_cannot_submit_an_answer():
    m = make_match()
    m.start_round()
    with pytest.raises(ValueError):
        m.submit("غریبه", "A", 5.0)


def test_a_match_needs_enough_questions():
    with pytest.raises(ValueError):
        Match("علی", "رضا", make_questions()[:2])


def test_a_question_needs_exactly_four_options():
    with pytest.raises(ValueError):
        Question("۲+۲؟", ["4", "5"], "A")


def test_the_correct_answer_must_be_a_b_c_or_d():
    with pytest.raises(ValueError):
        Question("۲+۲؟", ["4", "5", "6", "7"], "E")


# ---------- سؤال طلایی ----------

def test_golden_question_is_worth_much_more_than_a_normal_one():
    assert GOLDEN_POINTS >= 5 * POINTS


def test_golden_correct_answer_gives_golden_points():
    m = make_match("golden")
    m.start_round()
    m.submit("علی", "A", 3.0)     # سریع‌تر → بونوس سرعت هم می‌گیرد
    m.submit("رضا", "A", 9.0)
    m.resolve_round()

    assert m.score_of("علی") == GOLDEN_POINTS + SPEED_BONUS
    assert m.score_of("رضا") == GOLDEN_POINTS


def test_golden_does_not_reward_a_wrong_answer():
    m = make_match("golden")
    m.start_round()
    m.submit("علی", "C", 3.0)
    m.submit("رضا", "D", 4.0)
    m.resolve_round()

    assert m.score_of("علی") == 0
    assert m.score_of("رضا") == 0


def test_golden_late_answer_gets_nothing():
    m = make_match("golden")
    m.start_round()
    m.submit("علی", "A", TIME_LIMIT + 1)
    m.submit("رضا", "B", 5.0)
    m.resolve_round()

    assert m.score_of("علی") == 0


def test_power_up_name_is_not_case_sensitive():
    q = Question("۲+۲؟", ["4", "5", "6", "7"], "A", " Golden ")
    assert q.power_up == "golden"
    assert q.is_golden()


def test_an_unknown_power_up_is_refused():
    with pytest.raises(ValueError):
        Question("۲+۲؟", ["4", "5", "6", "7"], "A", "triple")


# ---------- کنترل خطا ----------

def test_a_question_needs_some_text():
    with pytest.raises(ValueError):
        Question("   ", ["4", "5", "6", "7"], "A")


def test_options_must_be_text():
    with pytest.raises(ValueError):
        Question("۲+۲؟", [4, 5, 6, 7], "A")


def test_options_must_be_a_list_not_a_string():
    with pytest.raises(ValueError):
        Question("۲+۲؟", "ABCD", "A")


def test_cannot_submit_before_a_round_starts():
    m = make_match()
    with pytest.raises(ValueError):
        m.submit("علی", "A", 5.0)


def test_elapsed_time_cannot_be_negative_or_text():
    m = make_match()
    m.start_round()
    with pytest.raises(ValueError):
        m.submit("علی", "A", -1)
    with pytest.raises(ValueError):
        m.submit("علی", "A", "سریع")


def test_a_round_cannot_be_scored_twice():
    m = make_match()
    m.start_round()
    m.submit("علی", "A", 5.0)
    m.resolve_round()

    with pytest.raises(ValueError):
        m.resolve_round()
    assert m.score_of("علی") == POINTS + SPEED_BONUS      # دوباره جمع نشده
