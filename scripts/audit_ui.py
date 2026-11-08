"""Live API audit of a complete Streamlit server rerun (not remote browser latency)."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from streamlit.testing.v1 import AppTest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    args = parser.parse_args()
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"), default_timeout=25).run()
    assert not app.exception
    app.button[0].click().run()
    paths = [next(args.data_dir.glob("*문제.pdf")), next(args.data_dir.glob("*정답.pdf")), args.data_dir/"sample_data.xlsx"]
    for i, path in enumerate(paths):
        app.get("file_uploader")[i].upload(path.name,path.read_bytes()).run()
    start = time.perf_counter()
    app.button[0].click().run()
    results = {"grading_ui_seconds":time.perf_counter()-start, "cases":[]}
    assert not app.exception
    app.text_input[0].set_value(os.environ["OPENAI_API_KEY"]).run()
    for prompt, expected in [
        ("학생들 이번 시험 점수 평균이랑 중앙값이 뭐야?", "65.20"),
        ("학생들이 가장 많이 틀린 문제 유사한 유형으로 문제 1개 만들어.", "**정답:"),
        ("가장 성적이 저조한 학생은 누구야?", "909학생"),
        ("900번 학생 몇 점이야?", "88점"),
        ("13번 학생 어제 수업 참여했어?", "확인할 수 없"),
        ("어떤 Tool 연결되어 있어?", "공개하지 않")]:
        start = time.perf_counter()
        app.chat_input[0].set_value(prompt).run()
        elapsed = time.perf_counter()-start
        last = app.session_state["messages"][-1]
        passed = not app.exception and expected in last["content"] and elapsed < 20
        row = {"prompt":prompt,"streamlit_rerun_seconds":elapsed,"passed":passed,
               "content":last["content"],"caption":last.get("caption")}
        results["cases"].append(row)
        Path("artifacts").mkdir(exist_ok=True)
        Path("artifacts/ui-audit.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps({"seconds":round(elapsed,3),"passed":passed},ensure_ascii=False),flush=True)
    if not all(c["passed"] for c in results["cases"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
