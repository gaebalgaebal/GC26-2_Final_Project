from __future__ import annotations

import hashlib
import os
from dataclasses import asdict

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from exam_helper.agent import AssessmentAgent, AgentError, Memory
from exam_helper.data import analyze, InputError
from exam_helper.export import export_excel

st.set_page_config(page_title="채점의 다음 | 영어 평가 도우미", page_icon="📘", layout="wide")
load_dotenv()

st.markdown("""<style>
.block-container {max-width:1200px;padding-top:2.5rem;padding-bottom:4rem}
h1,h2,h3 {letter-spacing:-.04em}
.eyebrow {font-size:.78rem;letter-spacing:.17em;color:#2563eb;font-weight:750;margin-bottom:1rem}
.hero {padding:2.8rem;border-radius:24px;background:linear-gradient(120deg,#132d50,#254f82);color:white;margin:1rem 0 2rem}
.hero h1 {color:white;font-size:3.1rem;line-height:1.2;margin:.3rem 0 1rem}
.hero p {color:#dbe7f6;font-size:1.05rem;max-width:640px;line-height:1.8}
.hero small {color:#99c3ff;letter-spacing:.12em}
[data-testid="stMetric"] {background:white;border:1px solid #dfe7f1;border-radius:16px;padding:1.1rem}
[data-testid="stChatMessage"] {border:1px solid #e2e8f0;border-radius:16px}
.step {color:#2563eb;font-weight:700;font-size:.8rem;letter-spacing:.12em}
</style>""", unsafe_allow_html=True)


def clear_analysis():
    for key in ("exam", "excel", "memory", "messages", "measurements", "analyzed_signature"):
        st.session_state.pop(key, None)


def landing():
    st.markdown('<div class="eyebrow">ENGLISH ASSESSMENT ASSISTANT</div>', unsafe_allow_html=True)
    st.markdown('''<div class="hero"><small>채점의 다음</small><h1>채점은 빠르게.<br>수업 준비는 깊이 있게.</h1>
    <p>수능 영어 형식의 모의고사 문제지, 정답표, OMR 응답을 올리면<br>성적 분석부터 학생들이 어려워한 유형의 새 문제까지 준비합니다.</p></div>''', unsafe_allow_html=True)
    if st.button("평가 분석 시작하기 →", type="primary", use_container_width=False):
        st.switch_page(analysis_navigation)
    st.write("")
    cols = st.columns(3, gap="large")
    for col, number, title, body in zip(cols, ["01 / GRADE", "02 / UNDERSTAND", "03 / TEACH"],
            ["파일 세 개로 자동 채점", "질문으로 이해하는 성적", "오답에서 시작하는 다음 수업"],
            ["정답 PDF의 배점을 읽어 정확히 채점하고, 학생별 결과를 엑셀로 내려받으세요.",
             "평균과 중앙값, 학생별 점수와 오답을 자연스러운 대화로 확인하세요.",
             "많이 틀린 문항과 같은 유형의 새 영어 문제와 해설을 만들어보세요."]):
        with col:
            with st.container(border=True):
                st.markdown(f'<div class="step">{number}</div>', unsafe_allow_html=True)
                st.subheader(title)
                st.write(body)
    st.divider()
    st.subheader("이렇게 사용하세요")
    st.write("**① 파일 업로드 → ② 분석 시작 → ③ 엑셀 다운로드 · API 키 입력 → ④ 성적 질문과 문제 생성**")
    st.caption("제공된 수능 영어 형식: 45문항 · 100점 · OMR 엑셀의 학생명, Q01~Q45 열. 채점과 엑셀 다운로드에는 API 키가 필요하지 않습니다.")
    st.caption("202135706 구본준 · 생성형 인공지능 활용 최종평가")


def analysis_page():
    st.markdown('<div class="eyebrow">ASSESSMENT WORKSPACE</div>', unsafe_allow_html=True)
    st.title("우리 반의 시험을 이해하는 시간")
    st.write("파일을 올리고 분석을 시작하세요. 결과를 확인한 뒤 대화로 수업을 준비할 수 있습니다.")
    with st.sidebar:
        st.subheader("시험 자료")
        questions = st.file_uploader("1. 문제지 PDF", type=["pdf"], key="questions_upload")
        answers = st.file_uploader("2. 정답·배점 PDF", type=["pdf"], key="answers_upload")
        omr = st.file_uploader("3. OMR 응답 엑셀", type=["xlsx"], key="omr_upload")
        uploads = [questions, answers, omr]
        ready = all(f is not None for f in uploads)
        signature = hashlib.sha256(b"".join(hashlib.sha256(f.getvalue()).digest() if f is not None else b"missing" for f in uploads)).hexdigest()
        if st.session_state.get("upload_signature") != signature:
            clear_analysis()
            st.session_state.upload_signature = signature
        if st.button("분석 시작", type="primary", disabled=not ready, use_container_width=True):
            clear_analysis()
            try:
                with st.spinner("정답표를 읽고 학생 응답을 채점하고 있습니다…"):
                    exam = analyze(*(f.getvalue() for f in uploads))
                    st.session_state.exam = exam
                    st.session_state.excel = export_excel(exam)
                    st.session_state.memory = Memory()
                    st.session_state.messages = []
                    st.session_state.measurements = []
                    st.session_state.analyzed_signature = signature
                st.success("채점이 완료되었습니다.")
            except InputError as exc:
                clear_analysis()
                st.error(str(exc))
            except Exception:
                clear_analysis()
                st.error("자료를 처리하지 못했습니다. 파일이 손상되지 않았는지 확인해주세요.")
        st.download_button("결과 엑셀 다운로드", data=st.session_state.get("excel", b""),
                           file_name="영어_평가결과.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           disabled="exam" not in st.session_state, use_container_width=True)
        st.divider()
        st.subheader("AI 연결")
        st.text_input("OpenAI API 키", type="password", key="evaluator_api_key", placeholder="sk-…", help="입력한 키는 현재 세션에서만 사용합니다. 저장소나 공용 캐시에 저장하지 않습니다.")
        # Environment key is available only when explicitly enabled for local development.
        development = os.getenv("ASSESSMENT_LOCAL_DEV") == "1"
        api_key = st.session_state.get("evaluator_api_key", "").strip()
        if development and not api_key:
            api_key = os.getenv("OPENAI_API_KEY", "")
            st.caption("로컬 개발용 환경변수 키 사용 중")
        with st.expander("모델 설정"):
            model = st.selectbox("모델", ["gpt-4.1", "gpt-4.1-mini"], help="기본값은 문항 품질을 우선한 GPT-4.1입니다. 비용을 줄이려면 mini를 선택할 수 있습니다. 모델별 접근 권한이 필요합니다.")
        if st.button("대화 초기화", disabled="exam" not in st.session_state, use_container_width=True):
            st.session_state.memory = Memory()
            st.session_state.messages = []
            st.session_state.measurements = []
        st.caption("키는 서버를 통해 OpenAI 요청에 사용됩니다. 업로드 자료와 대화는 이 브라우저 세션에서 관리됩니다.")
    if "exam" not in st.session_state:
        st.info("왼쪽에서 문제지 PDF, 정답 PDF, OMR 엑셀을 올린 후 ‘분석 시작’을 눌러주세요.")
        with st.container(border=True):
            st.subheader("분석이 끝나면 확인할 수 있어요")
            st.write("전체 성적 요약 · 학생별 점수와 정오 · 오답률 · 결과 엑셀 · 성적 기반 AI 대화")
        st.chat_input("채점 완료 후 질문할 수 있습니다", disabled=True)
        return
    exam = st.session_state.exam
    s = exam.summary
    cols = st.columns(4)
    for col, label, val in zip(cols, ["채점한 학생", "평균", "중앙값", "표준편차"],
                                [f"{s['count']}명", f"{s['mean']:.2f}점", f"{s['median']:.2f}점", f"{s['std']:.2f}점"]):
        col.metric(label, val)
    st.caption("45문항 · 총 100점 · 표준편차는 모집단 기준 · 오답 수 동률은 문항번호 오름차순")
    top = exam.hardest[:3]
    st.write("**많이 틀린 문항**　" + "　 /　 ".join(f"{n}번 · {exam.wrong_counts[n]}명" for n in top))
    with st.expander("학생별 성적과 문항별 오답 보기"):
        a, b, c = st.tabs(["학생별 성적", "문항별 분석", "추출된 정답·배점"])
        a.dataframe(pd.DataFrame([{"학생명": p["name"], "점수": p["score"], "정답수": sum(p["correct"].values()),
                                  "오답수": 45-sum(p["correct"].values())} for p in exam.students]), hide_index=True, use_container_width=True)
        b.dataframe(pd.DataFrame([{"문항": n, "오답수": exam.wrong_counts[n], "오답률": f"{exam.wrong_counts[n]/s['count']:.1%}",
                                  "유형": exam.questions[n].kind} for n in exam.hardest]), hide_index=True, use_container_width=True)
        c.dataframe(pd.DataFrame([asdict(a) for a in exam.answers.values()]).rename(columns={"number":"문항", "correct":"정답", "points":"배점"}), hide_index=True, use_container_width=True)
    st.divider()
    st.subheader("성적에 대해 물어보세요")
    st.caption("예: 평균이랑 중앙값이 뭐야? · 가장 성적이 저조한 학생은? · 가장 많이 틀린 문제와 유사한 문제 하나 만들어줘")
    if not api_key:
        st.info("AI 대화를 시작하려면 왼쪽에 본인의 OpenAI API 키를 입력해주세요.")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "caption" in message:
                st.caption(message["caption"])
    prompt = st.chat_input("학생의 점수, 오답, 다음 연습 문제까지", disabled=not bool(api_key), max_chars=4000)
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            try:
                with st.spinner("질문을 확인하고 있습니다…"):
                    reply = AssessmentAgent(api_key, model).answer(prompt, exam, st.session_state.memory)
                st.markdown(reply.text)
                caption = f"{reply.seconds:.2f}초 · 모델 호출 {reply.calls}회"
                st.caption(caption)
                st.session_state.messages.append({"role": "assistant", "content": reply.text, "caption": caption})
                st.session_state.measurements.append({"초": round(reply.seconds, 3), "호출수": reply.calls,
                    "입력토큰": reply.input_tokens, "출력토큰": reply.output_tokens, "처리": reply.route})
            except AgentError as exc:
                st.error(str(exc))
                st.session_state.messages.append({"role": "assistant", "content": str(exc)})
    if st.session_state.measurements:
        with st.expander("응답 성능 보기"):
            st.dataframe(pd.DataFrame(st.session_state.measurements), hide_index=True, use_container_width=True)


landing_navigation = st.Page(landing, title="서비스 소개", icon="🏠", default=True)
analysis_navigation = st.Page(analysis_page, title="평가 분석", icon="📊", url_path="analysis")
st.navigation([landing_navigation, analysis_navigation]).run()
