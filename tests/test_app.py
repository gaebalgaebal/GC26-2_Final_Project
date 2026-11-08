from pathlib import Path

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app.py"


def test_landing_and_disabled_analysis():
    at = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not at.exception
    at.button[0].click().run()
    assert not at.exception
    assert at.button[0].label == "분석 시작" and at.button[0].disabled
    assert at.chat_input[0].disabled


def test_upload_grade_chat_and_invalidate(source_dir):
    at = AppTest.from_file(str(APP), default_timeout=20).run()
    at.button[0].click().run()
    for i, path in enumerate([next(source_dir.glob("*문제.pdf")), next(source_dir.glob("*정답.pdf")), source_dir / "sample_data.xlsx"]):
        at.get("file_uploader")[i].upload(path.name, path.read_bytes()).run()
    assert not at.button[0].disabled
    at.button[0].click().run()
    assert not at.exception
    assert len(at.metric) == 4
    assert at.chat_input[0].disabled  # Grading works before any API key is provided.
    at.text_input[0].set_value("test-key-no-api-call").run()
    assert not at.chat_input[0].disabled
    at.chat_input[0].set_value("평균이랑 중앙값 알려줘").run()
    assert not at.exception
    assert any("65.20" in str(m.value) and "65.50" in str(m.value) for m in at.markdown)
    # Replacing/removing an input invalidates all previous results and chat.
    at.get("file_uploader")[2].clear().run()
    assert at.chat_input[0].disabled
    assert "exam" not in at.session_state
