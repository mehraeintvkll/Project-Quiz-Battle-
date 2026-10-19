ROUNDS = 5          # هر مسابقه چند راند
TIME_LIMIT = 30     # مهلت هر جواب، به ثانیه
POINTS = 10         # امتیاز جواب درست
SPEED_BONUS = 3     # بونوس سریع‌ترین درست‌جواب
GOLDEN_POINTS = 50  # امتیاز جواب درستِ «سؤال طلایی» (به‌جای POINTS)

# قابلیت‌های ویژه‌ای که یک سؤال می‌تواند داشته باشد
POWER_UPS = ("double", "golden")


class Question:
    def __init__(self, text, options, correct, power_up=None):
        if not isinstance(text, str) or not text.strip():
            raise ValueError("متن سؤال نباید خالی باشد.")

        if not isinstance(options, (list, tuple)) or len(options) != 4:
            raise ValueError("هر سؤال باید دقیقاً ۴ گزینه داشته باشد.")

        if any(not isinstance(option, str) or not option.strip() for option in options):
            raise ValueError("همه‌ی گزینه‌ها باید متن غیرخالی باشند.")

        correct = str(correct).strip().upper()
        if correct not in ("A", "B", "C", "D"):
            raise ValueError(f"جواب درست باید A تا D باشد، نه {correct!r}")

        if isinstance(power_up, str):
            power_up = power_up.strip().lower() or None
        if power_up is not None and power_up not in POWER_UPS:
            raise ValueError(
                f"قابلیت ویژه‌ی {power_up!r} معتبر نیست (فقط {' یا '.join(POWER_UPS)})."
            )

        self.text = text
        self.options = list(options)
        self.correct = correct
        self.power_up = power_up

    def is_correct(self, choice):
        return str(choice).strip().upper() == self.correct

    def is_golden(self):
        return self.power_up == "golden"

    def correct_text(self):
        return self.options["ABCD".index(self.correct)]


class RoundResult:
    def __init__(self, status, points):
        self.status = status        # "correct" یا "wrong" یا "too_late"
        self.points = points


class Match:
    def __init__(self, player1, player2, questions):
        if player1 == player2:
            raise ValueError("نام دو بازیکن باید متفاوت باشد.")

        if len(questions) < ROUNDS:
            raise ValueError(f"هر مسابقه به {ROUNDS} سؤال نیاز دارد.")

        self.players = [player1, player2]
        self.questions = questions
        self.scores = {player1: 0, player2: 0}
        self.round = 0
        self.answers = {}
        self._resolved = False

    def start_round(self):
        if self.round >= len(self.questions):
            return None

        self.round += 1
        self.answers = {}
        self._resolved = False
        return self.questions[self.round - 1]

    def score_of(self, player):
        return self.scores[player]

    def submit(self, player, choice, elapsed):
        if self.round == 0:
            raise ValueError("هنوز هیچ راندی شروع نشده است.")

        if player not in self.players:
            raise ValueError(f"بازیکن ناشناخته: {player}")

        if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or elapsed < 0:
            raise ValueError(f"زمان پاسخ باید عددی غیرمنفی باشد، نه {elapsed!r}")

        self.answers[player] = (choice, elapsed)

    def resolve_round(self):
        if self.round == 0:
            return {}

        if self._resolved:
            raise ValueError("امتیاز این راند قبلاً محاسبه شده است.")
        self._resolved = True

        question = self.questions[self.round - 1]
        results = {}
        correct_players = []

        # امتیاز پایه‌ی جواب درست: در سؤال طلایی خیلی بیشتر است
        base_points = GOLDEN_POINTS if question.is_golden() else POINTS

        # ۱) درست بود، غلط بود، یا دیر؟
        for player in self.players:
            if player not in self.answers:
                continue

            choice, elapsed = self.answers[player]
            if elapsed > TIME_LIMIT:
                results[player] = RoundResult("too_late", 0)
            elif question.is_correct(choice):
                results[player] = RoundResult("correct", base_points)
                correct_players.append(player)
            else:
                results[player] = RoundResult("wrong", 0)

        # ۲) بونوس سرعت: بین درست‌جواب‌ها، سریع‌ترین
        if correct_players:
            fastest = min(correct_players, key=lambda p: self.answers[p][1])
            results[fastest].points += SPEED_BONUS

        # ۳) سؤال دوبل: امتیاز درست‌جواب‌ها دو برابر
        if question.power_up == "double":
            for player in correct_players:
                results[player].points *= 2

        # ۴) امتیازها را جمع کن
        for player, result in results.items():
            self.scores[player] += result.points

        return results

    def is_over(self):
        return self.round >= len(self.questions)

    def winner(self):
        player1, player2 = self.players
        if self.scores[player1] == self.scores[player2]:
            return None

        if self.scores[player1] > self.scores[player2]:
            return player1
        return player2
