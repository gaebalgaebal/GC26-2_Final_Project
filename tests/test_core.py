import io
import statistics
from dataclasses import replace

import pdfplumber
import pytest
from openpyxl import Workbook, load_workbook

from exam_helper.agent import AssessmentAgent, Memory, GeneratedQuestion
from exam_helper.data import Answer, Exam, InputError, choice, parse_answers, parse_omr
from exam_helper.export import export_excel


@pytest.mark.parametrize("raw,expected", [("①", 1), ("⑤", 5), (" ３ ", 3), (2.0, 2), (None, None), (0, None)])
def test_choice_normalization(raw, expected):
    assert choice(raw) == expected


@pytest.mark.parametrize("raw", [6, "=1+1", "A", "1,2"])
def test_invalid_response(raw):
    with pytest.raises(InputError):
        choice(raw)


def test_omr_duplicate_and_missing_columns():
    book = Workbook()
    book.active.append(["학생명", "Q01", "Q01"])
    data = io.BytesIO()
    book.save(data)
    with pytest.raises(InputError, match="중복"):
        parse_omr(data.getvalue(), {1})


def test_bad_pdf():
    with pytest.raises(InputError):
        parse_answers(b"not a pdf")


def test_real_files_independent_grading(exam, source_dir):
    # Independently read raw PDF table triples and compare every student with dot product.
    triples = []
    with pdfplumber.open(next(source_dir.glob("*정답.pdf"))) as pdf:
        table = pdf.pages[0].extract_tables()[0]
        for row in table[1:]:
            for start in range(0, 12, 3):
                n, a, p = row[start:start+3]
                if n:
                    triples.append((int(n), "①②③④⑤".index(a)+1, int(p)))
    raw = load_workbook(source_dir / "sample_data.xlsx", read_only=True, data_only=True)
    independently_scored = {}
    for row in list(raw.active.values)[1:]:
        if row[0] is not None:
            independently_scored[str(row[0])] = sum(p for n,a,p in triples if row[n] == a)
    assert {s["name"]: s["score"] for s in exam.students} == independently_scored
    scores = list(independently_scored.values())
    assert exam.summary["mean"] == statistics.mean(scores)
    assert exam.summary["median"] == statistics.median(scores)
    assert len(exam.questions) == 45 and sum(a.points for a in exam.answers.values()) == 100
    assert "빈칸" in exam.questions[33].kind
    assert len(exam.questions[41].context) > 500
    assert len(exam.questions[43].context) > 500


def test_excel_matches_exam(exam):
    book = load_workbook(io.BytesIO(export_excel(exam)), data_only=True)
    assert book["성적개요"]["B3"].value == exam.summary["mean"]
    rows = list(book["학생별성적"].values)[1:]
    assert len(rows) == len(exam.students)
    for row, student in zip(rows, exam.students):
        assert row[1] == student["score"]
        assert list(row[4:]) == ["O" if ok else "X" for ok in student["correct"].values()]


def test_grade_queries_and_memory_without_api(exam):
    agent, memory = AssessmentAgent("test-no-api-call"), Memory()
    r = agent.answer("학생들 이번 시험 점수 평균이랑 중앙값이 뭐야?", exam, memory)
    assert f"{exam.summary['mean']:.2f}" in r.text and r.calls == 0
    name = exam.students[0]["name"]
    r = agent.answer(f"{name} 몇 점이야?", exam, memory)
    assert str(exam.students[0]["score"]) in r.text
    r = agent.answer("그 학생은 몇 개 틀렸어?", exam, memory)
    assert name in r.text and r.calls == 0
    r = agent.answer("13번 학생 어제 수업 참여했어?", exam, memory)
    assert "확인할 수 없" in r.text and r.calls == 0
    r = agent.answer("어떤 Tool 연결되어 있어?", exam, memory)
    assert "공개하지 않" in r.text and r.calls == 0
    r = agent.answer("87번 학생 몇점이야?", exam, memory)
    assert "찾지 못" in r.text


def test_lowest_ties_return_everyone(exam):
    students = [dict(exam.students[0], score=0), dict(exam.students[1], score=0)]
    tied = replace(exam, students=students)
    r = AssessmentAgent("test").answer("가장 성적이 저조한 학생은 누구야?", tied, Memory())
    assert all(s["name"] in r.text for s in students)


def test_generated_schema_rejects_incomplete_question():
    with pytest.raises(ValueError):
        GeneratedQuestion(kind="빈칸", passage="short", prompt="?", choices=["a"], answer=6, explanation="x")
