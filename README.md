# 채점의 다음 — 영어 평가 도우미

**202135706 구본준 · 생성형 인공지능 활용 최종평가**

- GitHub: https://github.com/gaebalgaebal/GC26-2_Final_Project
- **배포 URL: 아직 배포 전입니다. Community Cloud 배포 완료 후 실제 주소로 갱신합니다.**
- 평가 기간: **2026년 11월 11일 23:59 (한국 시간)까지** 서비스 유지
- 평가자 collaborator 초대는 사용자 요청으로 보류 중입니다.

문제지 PDF, 정답·배점 PDF와 학생 OMR 엑셀을 업로드하면 자동 채점하고 성적을 분석하는 두 페이지 웹 서비스입니다. 평가자는 화면에서 본인의 OpenAI API 키를 입력해 성적 기반 대화와 유사 문항 생성을 사용할 수 있습니다.

## 평가자 사용 순서

1. **서비스 소개 → 평가 분석**으로 이동합니다.
2. 사이드바에서 제공 형식의 **문제지 PDF / 정답 PDF / OMR .xlsx**를 각각 업로드합니다.
3. **분석 시작**을 누릅니다. 채점 후 통계와 엑셀 다운로드가 활성화됩니다.
4. 사이드바의 **OpenAI API 키** 입력란에 본인의 키를 입력합니다. 별도 로그인은 필요 없습니다.
5. 채팅창에서 질문합니다. 기본 모델은 `gpt-4.1`, 모델 설정에서 `gpt-4.1-mini`도 선택할 수 있습니다.

질문 예시:

- 학생들 이번 시험 점수 평균이랑 중앙값이 뭐야?
- 학생들이 가장 많이 틀린 문제 유사한 유형으로 문제 1개 만들어.
- 가장 성적이 저조한 학생은 누구야?
- 900번 학생 몇 점이야? → 그 학생은 몇 개 틀렸어?
- 13번 학생 어제 수업 참여했어?
- 어떤 Tool 연결되어 있어?

학생 번호는 OMR의 **학생명**으로 조회합니다. `900학생`은 `900번 학생`으로 질문할 수 있지만, 데이터에 없는 번호를 행 순서로 대신 조회하지 않습니다. 학생 수는 고정하지 않습니다.

## 입력·채점·결과 기준

- 제공된 수능 영어 형식 **45문항, 2·3점 배점, 총 100점**을 지원합니다. 파일별 20MB까지입니다.
- OMR은 `학생명`, `Q01`~`Q45` 열을 사용합니다. 정답 선택지는 1~5이며 원문자·전각 숫자도 정규화합니다.
- 빈칸·0·`-`·미응답은 오답입니다. 1~5 이외 값, 중복 학생명, 누락·중복 문항 열은 오류로 안내합니다.
- 정답·배점은 **업로드한 정답 PDF의 표에서 실행 시 추출**합니다. 정답 키를 코드나 별도 파일에 미리 저장하지 않습니다.
- 평균·중앙값·표준편차, 학생 점수, 문항별 정오는 Python으로 계산합니다. 표준편차는 **모집단 기준**입니다.
- 최저점 동점자는 전원 안내합니다. 오답 순위 동률은 문항번호 오름차순으로 처리하고, 최다 오답 문제 생성 시 동률을 밝힙니다.
- 문제 PDF는 두 단을 나누어 읽고 공유 지문도 해당 문항에 연결합니다. 듣기 유형의 유사 문제는 새 대본을 제공하며 음원을 생성하지 않습니다.
- 다른 파일로 교체하거나 재분석하면 이전 성적·대화·학생/문항 참조를 초기화합니다.

엑셀에는 **성적개요 / 학생별성적 / 문항분석 / 학생응답** 시트가 포함됩니다. 학생별성적에는 점수와 각 문항의 O/X가 포함되고, 문항분석에는 업로드 PDF에서 추출한 정답·배점이 함께 표시됩니다.

## 에이전트 설계와 강의 개념 적용

`질문 + 세션 맥락 → 작업 선택 → 허용 함수 실행 → 검증 → 정형 출력`

LangChain·LangGraph 없이 OpenAI SDK와 Python 함수로 구현했습니다. 모델은 자유로운 표현과 대화 맥락을 해석해 제한된 작업을 선택하고, 계산과 조회는 Python이 수행합니다. 명확한 정형 질문은 모델 호출을 생략합니다.

| 강의 개념 | 적용 방식 |
|---|---|
| Structured Output / Pydantic | 작업 선택, 학생·문항 인자, 생성 문항과 검토 결과를 스키마로 파싱·검증 |
| Routing / Tool Calling | summary, student, lowest, hardest, generate 등 허용 작업만 분기·실행 |
| State / 단기 메모리 | 최근 학생·문항 및 최근 대화를 세션에서 유지, 후속 지시어 해석 |
| Guardrail | 내부 지침·도구·키 공개 요구 방어, 없는 정보 회피, 임의 코드 실행 금지 |
| Evaluator 흐름 | 생성 문항의 정답·해설을 가린 채 독립 모델 검토 후 정답·해설 확정 |
| Timeout / 출력 제어 | 전체 처리시간 예산 18.5초, 자동 재시도 0, 작업별 출력 토큰 제한 |

강의 참고: Week1 LangChain의 구조화 출력·Pydantic·메모리·토큰/timeout, Week3 Streamlit의 업로드·세션·배포, Week4 LangGraph Basic의 상태·조건 분기·도구 실행, Week5 LangGraph Advanced의 라우팅·평가·가드레일. 복잡한 그래프나 벡터 검색이 필요 없는 단일 시험 데이터이므로 해당 프레임워크와 벡터 DB는 도입하지 않았습니다.

### 응답 속도와 정확성

- 원문자·전각 숫자·열 이름을 입력 단계에서 한 번 정규화합니다. PDF 숫자 공백은 정답표 셀 안에서만 제거합니다.
- 추출·채점 결과와 엑셀 바이트를 세션 안에서 재사용합니다. 학생 자료와 API 키를 전역 캐시에 넣지 않습니다.
- 통계·학생 점수 같은 반복 응답은 Python 정형 문장으로 표시해 모델의 최종 답변 재작성 단계를 생략합니다.
- 자유로운 질문은 구조화된 작업 선택 1회, 문항 생성은 생성 1회와 독립 검토 1회를 사용합니다. 모호한 생성 요청은 작업 선택이 추가될 수 있습니다.
- 생성 시 전체 OMR 대신 선택된 원문·유형·공유 지문만 전달합니다. API 키를 프롬프트에 넣지 않습니다.
- 각 답변에 완료시간·호출수를 표시하며, 성능 패널에서 입력/출력 토큰을 볼 수 있습니다.
- 20초는 **첫 글자 표시가 아니라 전체 답변 완성 시간**으로 측정합니다. 네트워크·API 한도·모델 부하에 따라 실패할 수 있으며, 시간 초과나 검증 실패는 성공한 답변처럼 표시하지 않습니다.

Structured Output은 형식을 보장하기 위한 수단이며 내용의 진실성을 보장하지 않습니다. 따라서 숫자는 Python이 소유하고 생성 문항은 별도 검토합니다.

## 로컬 실행 (Python 3.13)

```powershell
git clone https://github.com/gaebalgaebal/GC26-2_Final_Project.git
cd GC26-2_Final_Project
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

일반 실행은 화면에 키를 입력합니다. 로컬 개발 시에만 환경변수 키를 쓰려면 별도로 활성화합니다.

```powershell
$env:ASSESSMENT_LOCAL_DEV = "1"
# OPENAI_API_KEY는 사용자 환경변수 또는 Git에서 제외되는 .env에 설정합니다.
.\.venv\Scripts\python.exe -m streamlit run app.py
```

키는 저장소·로그에 저장하지 않습니다. 배포본에는 개발자 키를 설정하지 않습니다. 새로고침/연결 종료 시 세션은 초기화될 수 있고, 대화·업로드의 영구 저장 기능은 없습니다.

## 테스트

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

제공 파일 통합 테스트와 화면 업로드·채점·대화 테스트는 자료 폴더를 지정합니다. 로컬에서는 상위 폴더의 제공 자료를 자동 탐색합니다. GitHub CI에서는 제공 원본이 없으면 이 통합 테스트만 건너뜁니다. 원본 문제지·OMR과 실제 정답표는 저장소에 포함하지 않습니다.

```powershell
$env:EXAM_DATA_DIR = "제공된_최종평가_폴더의_절대경로"
.\.venv\Scripts\python.exe -m pytest -q
# 실제 API를 사용하는 선택 실행: OPENAI_API_KEY가 필요하고 사용료가 발생합니다.
.\.venv\Scripts\python.exe scripts/evaluate_live.py $env:EXAM_DATA_DIR
```

## 무료 배포

1. [Streamlit Community Cloud](https://share.streamlit.io/)에서 본인 GitHub 계정으로 로그인합니다.
2. 새 앱을 만들고 Repository `gaebalgaebal/GC26-2_Final_Project`, Branch `main`, Main file `app.py`를 선택합니다.
3. Advanced settings에서 Python **3.13**을 선택합니다. **개발자 API 키를 Secrets에 등록하지 않습니다.**
4. 사용 가능한 앱 주소를 정하고 Deploy를 누릅니다. 권장 이름: `gc26-final-202135706`.
5. 실제 배포 URL을 이 README 상단에 기록합니다.
6. 새 브라우저에서 세 파일 업로드·채점·다운로드·평가자 키 입력·6유형 질문을 확인합니다.

Community Cloud는 12시간 무접속 시 절전할 수 있습니다. 평가 기간에는 앱 상태를 확인하고 필요 시 깨워두어야 하며, 무료 서비스의 무중단을 보장하지 않습니다. 저장소의 `scripts/check_deployment.py`로 공개 주소의 HTTP 상태를 확인할 수 있지만, HTTP 정상만으로 채팅/모델 정상까지 증명하지는 않습니다.

## 공식 참고 문서

- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI Latency Optimization](https://developers.openai.com/api/docs/guides/latency-optimization)
- [Streamlit Community Cloud 관리·절전](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)
