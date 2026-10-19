import sys
import time
import traceback

from rich.console import Console  # pyright: ignore[reportMissingImports]

from engine import Match, ROUNDS, GOLDEN_POINTS
from storage import QuestionBank, ScoreBoard, QuestionBankError, ScoreBoardError
from app_log import AppLog

AppLog.setup()

console = Console()
logger = AppLog.get("Game")


def show_error(message):
    # markup=False: اگر پیام شامل [ ] بود (مثلاً در مسیر فایل) rich آن را دستور استایل نفهمد
    console.print(message, style="bold red", markup=False)


def show_warning(message):
    console.print(message, style="yellow", markup=False)


def show_menu():
    console.print("\nQuiz Battle", style="bold cyan")
    console.print("۱) بازی جدید", style="bold green")
    console.print("۲) خروج", style="bold red")


def show_leaderboard(board):
    console.print("\nرده‌بندی کل", style="bold cyan")

    if board is None:
        console.print("  رده‌بندی در دسترس نیست.")
        return

    if board.is_empty():
        console.print("  هنوز هیچ مسابقه‌ای ثبت نشده.")
        return

    for rank, (name, stat) in enumerate(board.top(5), start=1):
        console.print(
            f"  {rank}) {name} — {stat['wins']} برد، {stat['points']} امتیاز",
            markup=False,
        )


def show_power_up(question):
    if question.is_golden():
        console.print(
            f"\n*** سؤال طلایی! جواب درست {GOLDEN_POINTS} امتیاز دارد! ***",
            style="bold yellow",
        )
    elif question.power_up == "double":
        console.print("\nسؤال دوبل! امتیاز جواب درست دو برابر می‌شود.", style="bold magenta")


def prompt_choice(player_name, question):
    console.print(f"\n{player_name}", style="bold cyan", markup=False)
    console.print(question.text, style="bold", markup=False)
    for letter, option in zip("ABCD", question.options):
        console.print(f"  {letter}) {option}", style="bold", markup=False)

    while True:
        start = time.perf_counter()
        choice = input("جواب تو (A-D): ").strip().upper()
        elapsed = time.perf_counter() - start

        if choice in ("A", "B", "C", "D"):
            return choice, elapsed

        console.print("لطفاً فقط یکی از گزینه‌های A تا D را وارد کن.", style="yellow")


def play_match(questions, player1_name="بازیکن 1", player2_name="بازیکن 2"):
    match = Match(player1_name, player2_name, questions)

    while not match.is_over():
        question = match.start_round()
        console.print(f"\nراند {match.round} از {ROUNDS}", style="bold yellow")
        show_power_up(question)

        for player in match.players:
            choice, elapsed = prompt_choice(player, question)
            match.submit(player, choice, elapsed)

        results = match.resolve_round()

        for player, result in results.items():
            if result.status == "too_late":
                console.print(f"  {player}: زمان تمام شد", style="red", markup=False)
            elif result.status == "correct":
                console.print(f"  {player}: درست (+{result.points})", style="green", markup=False)
            else:
                console.print(
                    f"  {player}: اشتباه — جواب درست: {question.correct_text()}",
                    style="red",
                    markup=False,
                )

        console.print("\nامتیاز فعلی:", style="bold")
        for player in match.players:
            console.print(f"  {player}: {match.score_of(player)}", style="green", markup=False)

    winner = match.winner()
    if winner is None:
        console.print("\nبازی به تساوی پایان یافت!", style="bold yellow")
    else:
        console.print(f"\nبرنده: {winner}", style="bold green", markup=False)

    console.print("امتیاز نهایی:", style="bold")
    for player in match.players:
        console.print(f"  {player}: {match.score_of(player)}", style="bold", markup=False)

    return match


def ask_player_names():
    player1_name = input("نام بازیکن اول: ").strip() or "بازیکن 1"

    while True:
        player2_name = input("نام بازیکن دوم: ").strip() or "بازیکن 2"
        if player2_name != player1_name:
            return player1_name, player2_name
        show_warning("نام دو بازیکن باید متفاوت باشد؛ یک نام دیگر وارد کن.")


# Ask for Player names and then play match
def play(bank, board):
    player1_name, player2_name = ask_player_names()

    try:
        questions = bank.pick(ROUNDS)
    except ValueError as e:
        logger.error(f"Cannot pick questions: {e}")
        show_error(f"شروع بازی ممکن نیست: {e}")
        return

    match = play_match(questions, player1_name, player2_name)

    if board is not None:
        try:
            board.record(
                match.winner(),
                match.players[0], match.score_of(match.players[0]),
                match.players[1], match.score_of(match.players[1]),
            )
        except ScoreBoardError as e:
            # بازی تمام شده؛ فقط ثبت نتیجه روی دیسک ناموفق بوده
            show_warning(f"نتیجه‌ی این مسابقه روی دیسک ذخیره نشد: {e}")
    show_leaderboard(board)


def load_bank():
    try:
        bank = QuestionBank()
    except QuestionBankError as e:
        logger.error(f"Cannot load question bank: {e}")
        show_error(f"خطا در بارگذاری سؤال‌ها: {e}")
        return None

    if bank.skipped:
        show_warning(
            f"هشدار: {len(bank.skipped)} سؤال نامعتبر در questions.json نادیده گرفته شد "
            "(جزئیات در quiz_game.log)."
        )
    return bank


def load_board():
    try:
        board = ScoreBoard()
    except ScoreBoardError as e:
        logger.error(f"Cannot load score board: {e}")
        show_warning(f"{e}\nبازی بدون رده‌بندی ادامه پیدا می‌کند.")
        return None

    if board.load_warning:
        show_warning(board.load_warning)
    return board


def main():
    logger.info("Game started")

    bank = load_bank()
    if bank is None:
        return 1
    logger.info("Question bank initialized")

    board = load_board()
    logger.info("Score board initialized")
    show_leaderboard(board)
    logger.info("Initial leaderboard displayed")

    try:
        while True:
            show_menu()
            try:
                choice = input("انتخاب تو (۱ یا ۲): ").strip()
                logger.info(f"User choice: {choice}")
                if choice in ("1", "۱"):
                    logger.info("Starting a new match")
                    play(bank, board)
                    logger.info("Match finished")
                elif choice in ("2", "۲"):
                    console.print("خداحافظ!", style="bold cyan")
                    break
                else:
                    console.print(" فقط ۱ یا ۲ را وارد کن.", style="bold yellow")
            except (EOFError, KeyboardInterrupt):
                raise
            except Exception:
                # خطای پیش‌بینی‌نشده: جزئیات در لاگ، پیام کوتاه برای بازیکن؛ برنامه می‌ماند
                logger.error(f"Something went wrong - {traceback.format_exc()}")
                show_error("مشکلی پیش آمد و مسابقه متوقف شد (جزئیات در quiz_game.log).")
    except (EOFError, KeyboardInterrupt):
        logger.info("Game interrupted by the user")
        console.print("\nخداحافظ!", style="bold cyan")

    return 0


if __name__ == "__main__":
    sys.exit(main())
