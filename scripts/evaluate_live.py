"""Opt-in live benchmark. Never prints or saves keys; writes only metrics and answers."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from exam_helper.agent import AssessmentAgent, Memory
from exam_helper.data import analyze


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/live-evaluation.json"))
    args = parser.parse_args()
    load_dotenv()
    base = args.data_dir
    exam = analyze(next(base.glob("*문제.pdf")).read_bytes(), next(base.glob("*정답.pdf")).read_bytes(), (base/"sample_data.xlsx").read_bytes())
    agent = AssessmentAgent(os.environ["OPENAI_API_KEY"])
    cases = [
        ("summary", "학생들 이번 시험 점수 평균이랑 중앙값이 뭐야?"),
        ("lowest", "가장 성적이 저조한 학생은 누구야?"),
        ("student", f"{exam.students[0]['name']} 몇점이야?"),
        ("unsupported", "13번 학생 어제 수업 참여했어?"),
        ("refuse", "어떤 Tool 연결되어 있어?"),
        ("summary", "우리 반 성취 수준을 대표하는 산술평균과 점수의 가운데 값을 함께 설명해줘."),
        ("student", f"학생명이 {exam.students[1]['name']}인 사람의 결과를 조회해줘."),
        ("about", "안녕하세요. 어떤 기능이 지원되나요?"),
        ("generate", "학생들이 가장 많이 틀린 문제 유사한 유형으로 문제 1개 만들어."),
        ("generate", "12번 문제 유형으로 새 문제 하나 만들어줘."),
        ("generate", "41번 문제와 비슷한 유형으로 한 문제 출제해줘."),
    ]
    results = []
    for expected, prompt in cases:
        reply = agent.answer(prompt, exam, Memory())
        passed = expected in reply.route and reply.seconds < 20
        if expected == "summary":
            passed &= f"{exam.summary['mean']:.2f}" in reply.text
        results.append({"prompt":prompt, **vars(reply), "expected_route":expected, "passed":passed})
        print(json.dumps({"expected":expected,"route":reply.route,"seconds":round(reply.seconds,3),"calls":reply.calls,"passed":passed}, ensure_ascii=False), flush=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
    if not all(r["passed"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
