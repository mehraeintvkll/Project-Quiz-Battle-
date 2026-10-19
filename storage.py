import json
import os
import random
import time
from pathlib import Path

from app_log import AppLog
from engine import Question, ROUNDS

# مسیرها نسبت به همین پوشه‌ی پروژه‌اند، نه پوشه‌ای که برنامه از آن اجرا شده
BASE_DIR = Path(__file__).resolve().parent
QUESTIONS_PATH = str(BASE_DIR / "questions.json")
LEADERBOARD_PATH = str(BASE_DIR / "leaderboard.json")

log = AppLog.get("Storage")


class StorageError(Exception):
    """خطای خواندن یا نوشتن فایل‌های بازی؛ پیامش فارسی و قابل نمایش به بازیکن است."""


class QuestionBankError(StorageError):
    """فایل سؤال‌ها پیدا نشد، خراب است، یا سؤال معتبر کافی ندارد."""


class ScoreBoardError(StorageError):
    """خواندن یا ذخیره‌ی فایل رده‌بندی ممکن نشد."""


def _json_error_text(error: json.JSONDecodeError) -> str:
    return f"خط {error.lineno}، ستون {error.colno}: {error.msg}"


class QuestionBank:
    def __init__(self, path: str = QUESTIONS_PATH) -> None:
        data = self._read_json(path)

        if not isinstance(data, list):
            raise QuestionBankError(
                f"ساختار فایل سؤال‌ها ({path}) باید یک لیست از سؤال‌ها باشد."
            )

        self._questions: list[Question] = []
        # سؤال‌های نامعتبر کل بازی را از کار نمی‌اندازند؛ فقط رد می‌شوند و اینجا ثبت می‌شوند
        self.skipped: list[tuple[int, str]] = []

        for index, item in enumerate(data, start=1):
            try:
                self._questions.append(self._build_question(item))
            except (ValueError, TypeError) as error:
                log.warning("Skipping invalid question #%d in %s: %s", index, path, error)
                self.skipped.append((index, str(error)))

        if len(self._questions) < ROUNDS:
            raise QuestionBankError(
                f"فقط {len(self._questions)} سؤال معتبر در {path} هست، "
                f"ولی هر مسابقه به {ROUNDS} سؤال نیاز دارد."
            )

    @staticmethod
    def _read_json(path: str):
        try:
            # utf-8-sig: فایل‌هایی که ویندوز با BOM ذخیره کرده هم خوانده می‌شوند
            with open(path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except FileNotFoundError:
            raise QuestionBankError(f"فایل سؤال‌ها پیدا نشد: {path}") from None
        except json.JSONDecodeError as error:
            raise QuestionBankError(
                f"فایل سؤال‌ها ({path}) JSON معتبر نیست — {_json_error_text(error)}"
            ) from error
        except UnicodeDecodeError as error:
            raise QuestionBankError(
                f"فایل سؤال‌ها ({path}) با UTF-8 ذخیره نشده است."
            ) from error
        except OSError as error:
            raise QuestionBankError(
                f"خواندن فایل سؤال‌ها ممکن نیست ({path}): {error.strerror or error}"
            ) from error

    @staticmethod
    def _build_question(item) -> Question:
        if not isinstance(item, dict):
            raise ValueError("هر سؤال باید یک شیء JSON باشد.")

        missing = [key for key in ("text", "options", "correct") if key not in item]
        if missing:
            raise ValueError(f"کلیدهای لازم وجود ندارد: {', '.join(missing)}")

        return Question(
            text=item["text"],
            options=item["options"],
            correct=item["correct"],
            power_up=item.get("power_up"),
        )

    def count(self) -> int:
        return len(self._questions)

    def pick(self, n: int = ROUNDS, golden_guaranteed: bool = True) -> list[Question]:
        """n سؤال تصادفی و بدون تکرار.

        اگر در بانک سؤال طلایی باشد و golden_guaranteed=True، دقیقاً یکی از
        آن‌ها در هر مسابقه می‌آید (در جایگاهی تصادفی)؛ بقیه سؤال‌های معمولی‌اند.
        """
        if n < 1:
            raise ValueError("تعداد سؤال‌ها باید حداقل ۱ باشد.")
        if n > len(self._questions):
            raise ValueError(
                f"{n} سؤال خواسته شد ولی بانک فقط {len(self._questions)} سؤال دارد."
            )

        golden = [q for q in self._questions if q.is_golden()]
        if not golden_guaranteed or not golden:
            return random.sample(self._questions, k=n)

        chosen_golden = random.choice(golden)
        others = [q for q in self._questions if not q.is_golden()]
        if len(others) < n - 1:                      # سؤال معمولی کافی نیست
            others = [q for q in self._questions if q is not chosen_golden]

        picked = random.sample(others, k=n - 1) + [chosen_golden]
        random.shuffle(picked)
        return picked


class ScoreBoard:
    def __init__(self, path: str = LEADERBOARD_PATH) -> None:
        self._path = Path(path)
        self._data: dict[str, dict[str, int]] = {}
        # اگر فایل رده‌بندی خراب بود، توضیحش اینجا می‌آید تا برنامه به بازیکن بگوید
        self.load_warning: str | None = None

        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return

        try:
            with open(self._path, encoding="utf-8-sig") as f:
                self._data = self._validate(json.load(f))
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
            # فایل خراب است: نسخه‌اش را نگه می‌داریم و از صفر شروع می‌کنیم
            # (وگرنه اولین ذخیره‌ی بعدی، فایل خراب را برای همیشه از بین می‌برد)
            self._data = {}
            backup = self._back_up_corrupt_file()
            log.error("Leaderboard %s is corrupt (%s); backup: %s", self._path, error, backup)
            self.load_warning = (
                "فایل رده‌بندی خراب بود و رده‌بندی از نو شروع شد."
                + (f" نسخه‌ی قبلی با نام {backup.name} نگه داشته شد." if backup else "")
            )
        except OSError as error:
            log.error("Cannot read leaderboard %s: %s", self._path, error)
            raise ScoreBoardError(
                f"خواندن فایل رده‌بندی ممکن نیست ({self._path}): {error.strerror or error}"
            ) from error

    @staticmethod
    def _validate(data) -> dict[str, dict[str, int]]:
        if not isinstance(data, dict):
            raise ValueError("ساختار فایل رده‌بندی باید یک شیء JSON باشد.")

        clean: dict[str, dict[str, int]] = {}
        for name, stat in data.items():
            if not isinstance(stat, dict):
                raise ValueError(f"اطلاعات بازیکن {name!r} نامعتبر است.")

            wins, points = stat.get("wins"), stat.get("points")
            for value in (wins, points):
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError(f"برد یا امتیاز بازیکن {name!r} نامعتبر است.")

            clean[name] = {"wins": wins, "points": points}
        return clean

    def _back_up_corrupt_file(self) -> Path | None:
        backup = self._path.with_name(self._path.name + ".corrupt")
        if backup.exists():
            backup = self._path.with_name(f"{self._path.name}.{int(time.time())}.corrupt")
        try:
            self._path.replace(backup)
        except OSError as error:
            log.error("Could not back up corrupt leaderboard: %s", error)
            return None
        return backup

    def is_empty(self) -> bool:
        return not self._data

    def record(self, winner, player1, score1, player2, score2) -> None:
        """نتیجه‌ی مسابقه را ثبت می‌کند.

        ورودی نامعتبر → ValueError. اگر ذخیره روی دیسک نشود → ScoreBoardError؛
        در این حالت نتیجه در حافظه می‌ماند و در ذخیره‌ی موفق بعدی نوشته می‌شود.
        """
        for name in (player1, player2):
            if not isinstance(name, str) or not name.strip():
                raise ValueError("نام بازیکن نباید خالی باشد.")
        if player1 == player2:
            raise ValueError("نام دو بازیکن باید متفاوت باشد.")
        for score in (score1, score2):
            if isinstance(score, bool) or not isinstance(score, int) or score < 0:
                raise ValueError(f"امتیاز باید عدد صحیح غیرمنفی باشد، نه {score!r}")
        if winner is not None and winner not in (player1, player2):
            raise ValueError("برنده باید یکی از دو بازیکن باشد.")

        for name, points in [(player1, score1), (player2, score2)]:
            if name not in self._data:
                self._data[name] = {"wins": 0, "points": 0}
            self._data[name]["points"] += points

        if winner is not None:
            self._data[winner]["wins"] += 1

        self._save()

    def top(self, n: int = 5) -> list[tuple[str, dict[str, int]]]:
        def wins_then_points(item):
            return item[1]["wins"], item[1]["points"]

        return sorted(self._data.items(), key=wins_then_points, reverse=True)[:n]

    def _save(self) -> None:
        # اول در فایل موقت می‌نویسیم و بعد جایگزین می‌کنیم؛
        # اگر وسط نوشتن مشکلی پیش بیاید، فایل رده‌بندی قبلی سالم می‌ماند.
        tmp = self._path.with_name(self._path.name + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self._path)
        except OSError as error:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            log.error("Cannot save leaderboard %s: %s", self._path, error)
            raise ScoreBoardError(
                f"ذخیره‌ی رده‌بندی ممکن نشد ({self._path}): {error.strerror or error}"
            ) from error
