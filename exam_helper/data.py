from __future__ import annotations

import hashlib
import io
import re
import statistics
import unicodedata
from dataclasses import dataclass

import pdfplumber
from openpyxl import load_workbook


class InputError(ValueError):
    """Actionable error in an uploaded file."""


def normalized(value) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip()


def compact(value) -> str:
    return re.sub(r"\s+", "", normalized(value))


def choice(value) -> int | None:
    if value is None or compact(value) in {"", "0", "-", "미응답", "무응답"}:
        return None
    text = compact(value)
    if re.fullmatch(r"[1-5](?:\.0)?", text):
        return int(float(text))
    raise InputError(f"선택지는 1~5 또는 빈칸이어야 합니다: {str(value)[:30]}")


@dataclass(frozen=True)
class Answer:
    number: int
    correct: int
    points: int


@dataclass(frozen=True)
class Question:
    number: int
    text: str
    kind: str
    page: int
    context: str = ""


def question_kind(number: int, text: str) -> str:
    if number <= 17:
        return "듣기 / " + text.lstrip().split("\n")[0].split(".", 1)[-1].strip()
    for token, label in [
        ("빈칸", "빈칸 추론"), ("순서", "글의 순서"), ("들어가기에", "문장 삽입"),
        ("어법", "어법"), ("낱말의 쓰임", "어휘"), ("요약", "요약문 완성"),
        ("흐름", "무관한 문장"), ("제목", "제목 추론"), ("주제", "주제 추론"),
        ("의미하는", "함축 의미 추론"), ("심경", "심경 변화"), ("목적", "글의 목적"),
        ("주장", "필자의 주장"), ("요지", "글의 요지"), ("일치하지", "내용 불일치"),
        ("일치", "내용 일치"),
    ]:
        if token in text[:300]:
            return label
    return "영어 독해"


def parse_answers(content: bytes) -> dict[int, Answer]:
    """Read triples inside PDF table cells; no stored answer key or model call."""
    answers = {}
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            if len(pdf.pages) > 10:
                raise InputError("정답 PDF는 10페이지 이하로 업로드해주세요.")
            for page in pdf.pages:
                for table in page.extract_tables():
                    for row in table:
                        for start in range(0, len(row) - 2, 3):
                            n, c, p = map(compact, row[start:start + 3])
                            if not (n.isdigit() and c in {"1", "2", "3", "4", "5"} and p.isdigit()):
                                continue
                            number = int(n)
                            answer = Answer(number, int(c), int(p))
                            if number in answers:
                                raise InputError(f"정답표에 {number}번이 중복되어 있습니다.")
                            answers[number] = answer
    except InputError:
        raise
    except Exception as exc:
        raise InputError("정답 PDF를 읽을 수 없습니다. 제공된 표 형식의 PDF인지 확인해주세요.") from exc
    if set(answers) != set(range(1, 46)):
        raise InputError("정답 PDF에서 1~45번을 모두 추출하지 못했습니다. 올바른 정답표를 업로드해주세요.")
    if any(a.points not in {2, 3} for a in answers.values()) or sum(a.points for a in answers.values()) != 100:
        raise InputError("정답표의 배점을 확인해주세요. 제공 형식은 2·3점 배점, 총 100점입니다.")
    return dict(sorted(answers.items()))


def parse_questions(content: bytes, numbers: set[int]) -> dict[int, Question]:
    questions = {}
    segments = []
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            if len(pdf.pages) > 30:
                raise InputError("문제 PDF는 30페이지 이하로 업로드해주세요.")
            for pno, page in enumerate(pdf.pages, 1):
                # The supplied exam has two columns; exclude repeated header/footer.
                for left, right in [(0, page.width / 2), (page.width / 2, page.width)]:
                    text = page.crop((left, 65, right, page.height - 40)).extract_text() or ""
                    segments.append((pno, text))
    except InputError:
        raise
    except Exception as exc:
        raise InputError("문제 PDF를 읽을 수 없습니다. 텍스트가 포함된 제공 형식 PDF를 사용해주세요.") from exc
    # Keep shared passages before 16, 41 and 43, including continuation across columns.
    shared = {}
    current_shared = None
    current_number = None
    for pno, text in segments:
        for line in text.splitlines():
            group = re.match(r"^\s*[\[［]\s*(\d+)\s*[~～∼〜-]\s*(\d+)\s*[\]］]", line)
            numbered = re.match(r"^\s*(\d{1,2})\.\s*(.*)", line)
            if group:
                current_shared = (int(group[1]), int(group[2]))
                shared.setdefault(current_shared, [])
                shared[current_shared].append(line)
                current_number = None
            elif numbered and int(numbered[1]) in numbers:
                current_number = int(numbered[1])
                if current_number in questions:
                    raise InputError(f"문제지에서 {current_number}번이 중복 인식됐습니다.")
                questions[current_number] = [pno, [line]]
                current_shared = None
            elif current_number is not None:
                questions[current_number][1].append(line)
            elif current_shared:
                shared[current_shared].append(line)
    if set(questions) != numbers:
        missing = sorted(numbers - set(questions))
        raise InputError(f"문제지에서 문항을 찾지 못했습니다: {missing}. 제공된 문제 PDF를 확인해주세요.")
    result = {}
    for n, (page, lines) in questions.items():
        text = "\n".join(lines).strip()
        context = "\n".join("\n".join(v) for (lo, hi), v in shared.items() if lo <= n <= hi)
        heading = context.split("\n")[0] if context else ""
        result[n] = Question(n, text, question_kind(n, heading + "\n" + text[:300]), page, context)
    return result


def parse_omr(content: bytes, numbers: set[int]) -> list[dict]:
    try:
        book = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
        sheet = book["OMR_응답"] if "OMR_응답" in book.sheetnames else book.worksheets[0]
        if sheet.max_row > 10001 or sheet.max_column > 100:
            raise InputError("OMR은 10,000명·100열 이하로 업로드해주세요.")
        rows = iter(sheet.iter_rows(values_only=True))
        headers = next(rows)
        qcols = {}
        student_col = None
        for i, h in enumerate(headers):
            text = compact(h)
            if text in {"학생명", "학생번호", "학생", "이름", "학번"} and student_col is None:
                student_col = i
            match = re.fullmatch(r"[Qq]0*(\d+)", text)
            if match:
                n = int(match[1])
                if n in qcols:
                    raise InputError(f"OMR에 Q{n:02d} 열이 중복되어 있습니다.")
                qcols[n] = i
        if student_col is None or set(qcols) != numbers:
            raise InputError("OMR 첫 행에 학생명과 Q01~Q45 열이 있어야 합니다.")
        students, seen = [], set()
        for row in rows:
            if not any(v is not None for v in row):
                continue
            name = normalized(row[student_col])
            if not name or name in seen:
                raise InputError("학생명이 비어 있거나 중복되어 있습니다. 학생별 고유 이름을 사용해주세요.")
            seen.add(name)
            try:
                responses = {n: choice(row[c]) for n, c in qcols.items()}
            except InputError as exc:
                raise InputError(f"{name}: {exc}") from exc
            students.append({"name": name, "responses": responses})
        book.close()
        if not students:
            raise InputError("OMR에 학생 응답이 없습니다.")
        return students
    except InputError:
        raise
    except Exception as exc:
        raise InputError("OMR 엑셀을 읽을 수 없습니다. 제공 형식의 .xlsx 파일을 사용해주세요.") from exc


@dataclass
class Exam:
    fingerprint: str
    answers: dict[int, Answer]
    questions: dict[int, Question]
    students: list[dict]

    @property
    def summary(self):
        scores = [s["score"] for s in self.students]
        return {"count": len(scores), "mean": statistics.mean(scores),
                "median": statistics.median(scores), "std": statistics.pstdev(scores),
                "min": min(scores), "max": max(scores)}

    @property
    def wrong_counts(self):
        return {n: sum(not s["correct"][n] for s in self.students) for n in self.answers}

    @property
    def hardest(self):
        return sorted(self.wrong_counts, key=lambda n: (-self.wrong_counts[n], n))

    def find_student(self, query: str):
        text = compact(query)
        exact = [s for s in self.students if compact(s["name"]) == text]
        if exact:
            return exact[0]
        digits = re.fullmatch(r"(?:학생)?(\d+)(?:번)?(?:학생)?", text)
        if digits:
            matches = [s for s in self.students if re.sub(r"\D", "", s["name"]) == digits[1]]
            if len(matches) == 1:
                return matches[0]
        return None


def analyze(question_pdf: bytes, answer_pdf: bytes, omr_xlsx: bytes) -> Exam:
    for content in (question_pdf, answer_pdf, omr_xlsx):
        if not content or len(content) > 20 * 1024 * 1024:
            raise InputError("각 파일은 비어 있지 않은 20MB 이하 파일이어야 합니다.")
    answers = parse_answers(answer_pdf)
    questions = parse_questions(question_pdf, set(answers))
    students = parse_omr(omr_xlsx, set(answers))
    for s in students:
        s["correct"] = {n: s["responses"][n] == a.correct for n, a in answers.items()}
        s["score"] = sum(a.points for n, a in answers.items() if s["correct"][n])
    digest = hashlib.sha256()
    for content in (question_pdf, answer_pdf, omr_xlsx):
        digest.update(hashlib.sha256(content).digest())
    return Exam(digest.hexdigest(), answers, questions, students)
