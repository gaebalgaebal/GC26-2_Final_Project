"""Application XLSX export: computed values are sourced from the graded Exam."""
import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.formatting.rule import CellIsRule

from .data import Exam


def literal(value):
    # Uploaded names must remain text, even when Excel would interpret a formula.
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def export_excel(exam: Exam) -> bytes:
    book = Workbook()
    summary = book.active
    summary.title = "성적개요"
    summary.append(["평가 결과", "값"])
    for label, key in [("학생 수", "count"), ("평균", "mean"), ("중앙값", "median"),
                       ("표준편차(모집단)", "std"), ("최저점", "min"), ("최고점", "max")]:
        summary.append([label, exam.summary[key]])
    summary.append(["총 배점", sum(a.points for a in exam.answers.values())])
    summary.append(["오답 순위 동률 기준", "문항번호 오름차순"])
    summary.append(["최다 오답 상위 3문항", ", ".join(map(str, exam.hardest[:3]))])
    result = book.create_sheet("학생별성적")
    result.append(["학생명", "점수", "정답수", "오답수"] + [f"Q{n:02d} 정오" for n in exam.answers])
    for s in exam.students:
        count = sum(s["correct"].values())
        result.append([literal(s["name"]), s["score"], count, len(exam.answers) - count]
                      + ["O" if s["correct"][n] else "X" for n in exam.answers])
    items = book.create_sheet("문항분석")
    items.append(["문항번호", "정답", "배점", "오답수", "오답률", "유형", "원문 페이지"])
    for n in exam.hardest:
        a, q = exam.answers[n], exam.questions[n]
        items.append([n, a.correct, a.points, exam.wrong_counts[n],
                      exam.wrong_counts[n] / len(exam.students), q.kind, q.page])
    for cell in list(items.columns)[4][1:]:
        cell.number_format = "0.0%"
    responses = book.create_sheet("학생응답")
    responses.append(["학생명"] + [f"Q{n:02d}" for n in exam.answers])
    for s in exam.students:
        responses.append([literal(s["name"])] + [s["responses"][n] for n in exam.answers])
    for sheet in book:
        sheet.freeze_panes = "B2" if sheet != summary else "A2"
        sheet.auto_filter.ref = sheet.dimensions
        sheet.row_dimensions[1].height = 28
        for c in sheet[1]:
            c.font = Font(color="FFFFFF", bold=True)
            c.fill = PatternFill("solid", fgColor="173C6B")
        for row in sheet.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(vertical="center")
                if c.row % 2 == 0:
                    c.fill = PatternFill("solid", fgColor="F0F5FB")
        for col in sheet.columns:
            letter = col[0].column_letter
            width = min(48, max(12, max(len(str(c.value or "")) for c in col) * 1.4 + 3))
            sheet.column_dimensions[letter].width = width
    summary.column_dimensions["A"].width = 30
    summary.column_dimensions["B"].width = 38
    for r in (3, 4, 5):
        summary.cell(r, 2).number_format = "0.00"
    result.conditional_formatting.add(f"E2:AW{result.max_row}", CellIsRule(
        operator="equal", formula=['"X"'], font=Font(color="B42318")))
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()
