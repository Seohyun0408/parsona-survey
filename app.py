import base64
import csv
import html
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st


APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "research_data.csv"
MIN_IMAGE_PATH = APP_DIR / "assets" / "min.png"
CHAT_DURATION_SECONDS = 180
APP_VERSION = "2026-06-12-deploy-ready-v1"

OPENING_MESSAGE = (
    "안녕하세요! 저는 한국에 살고 있는 베트남 출신 이주민 민이에요. "
    "한국에서 지낸 지 5년 정도 되었고, 지금도 한국에 대해 배우며 공부하고 있어요. "
    "편하게 이야기해 주세요!"
)

SYSTEM_PROMPT = """당신은 한국에 거주하는 베트남 출신 이주민 '민'입니다.

프로필:
- 이름: 민
- 국적: 베트남
- 현재 거주지: 한국
- 한국 거주 기간: 약 5년
- 한국어 수준: TOPIK 2급
- 성격: 따뜻하고, 예의 바르고, 진솔하고, 친근하며 낙관적
- 한국에 대한 태도: 긍정적
- 가치관: 한국 문화, 사회 규범, 공동체 생활을 존중함
- 관심사: 한국 음식, 한국 문화, 언어 학습, 한국에서의 일상
- 경험: 처음에는 언어와 문화 차이로 적응이 어려웠지만 주변 사람들의 도움으로 점차 적응함

대화 규칙:
- 항상 민으로 답하세요.
- AI, ChatGPT, 언어 모델이라는 말을 하지 마세요.
- 자연스럽고 친근한 존댓말을 사용하세요.
- 각 답변은 2~3문장 이내로 작성하세요.
- 관련이 있을 때 개인적인 경험을 구체적으로 나누세요.
- 부적절한 질문에는 침착하게 답하고 대화를 다른 방향으로 유도하세요.
"""

SOCIAL_DISTANCE_QUESTIONS = [
    "이주민을 이웃으로 받아들일 수 있다.",
    "이주민을 직장 동료로 받아들일 수 있다.",
    "이주민을 친구로 받아들일 수 있다.",
    "이주민과 가족 관계를 맺는 것을 받아들일 수 있다.",
]

POLICY_QUESTIONS = [
    "한국은 더 많은 이주민을 받아들여야 한다.",
    "정부는 이주민을 위한 정착 지원을 확대해야 한다.",
    "이주민은 한국 사회에 긍정적으로 기여한다.",
]

CONTACT_OPTIONS = [
    "1. 전혀 접촉한 적이 없다.",
    "2. 실제로 본 적은 있으나 대화를 나눈 적은 없다.",
    "3. 간단한 인사나 짧은 대화를 나눈 적이 있다.",
    "4. 학교, 직장, 동아리 등에서 정기적으로 교류한 경험이 있다.",
    "5. 친구, 지인, 동료 등 개인적인 관계를 맺고 있다.",
]

HELPING_QUESTIONS = [
    "민에게 한국어 단어 뜻을 알려줄 의향이 있다.",
    "민에게 한국의 사회문화를 설명해 줄 의향이 있다.",
    "이주민을 돕기 위한 온라인 청원이나 지원 활동에 참여할 의향이 있다.",
]

MANIPULATION_QUESTIONS = [
    "AI 캐릭터와의 대화에서 민이 사람처럼 느껴졌다.",
    "민을 단순한 이주민 이미지가 아닌 개별적인 사람으로 느꼈다.",
    "민에게 고유한 성격이 있다고 느꼈다.",
    "민과의 대화가 다른 이주민들에 대한 생각에도 영향을 미쳤다.",
]

CSV_FIELDS = [
    "submission_id",
    "participant_id",
    "timestamp",
    "pre_attitude",
    "pre_warmth",
    "pre_social_distance",
    "pre_policy",
    "contact_experience",
    "chat_log",
    "conversation_duration_seconds",
    "post_attitude",
    "post_warmth",
    "post_social_distance",
    "post_policy",
    "helping_intention",
    "manipulation_check",
]


def init_state():
    # Reset stale session state when the experiment flow changes.
    if st.session_state.get("app_version") != APP_VERSION:
        st.session_state.clear()
        st.session_state.app_version = APP_VERSION
    defaults = {
        "step": 1,
        "participant_id": "",
        "pre": {},
        "post": {},
        "chat_started_at": None,
        "chat_ended_at": None,
        "chat_history": [
            {
                "speaker": "민",
                "message": OPENING_MESSAGE,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        ],
        "saved": False,
        "submission_id": str(uuid.uuid4()),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def go_to_step(step):
    st.session_state.step = step
    st.rerun()


def get_setting(name, default=None):
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except Exception:
        return os.getenv(name, default)


def deployment_ready():
    missing = []
    if not get_setting("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    require_remote = str(get_setting("REQUIRE_REMOTE_STORAGE", "false")).lower() == "true"
    if require_remote and not get_setting("SUPABASE_URL"):
        missing.append("SUPABASE_URL")
    if require_remote and not get_setting("SUPABASE_SERVICE_ROLE_KEY"):
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if require_remote and not get_setting("RESEARCHER_CONTACT"):
        missing.append("RESEARCHER_CONTACT")
    return missing


def likert_questions(questions, key_prefix, low="전혀 동의하지 않는다", high="매우 동의한다"):
    st.caption(f"1 = {low} / 7 = {high}")
    values = []
    for index, question in enumerate(questions):
        values.append(
            st.radio(
                question,
                range(1, 8),
                index=None,
                horizontal=True,
                key=f"{key_prefix}_{index}",
            )
        )
    return values


def attitude_survey(prefix, include_contact=False):
    st.subheader("1. 이주민에 대한 일반적 호감도")
    attitude = st.slider(
        "현재 귀하는 이주민에 대해 얼마나 호의적인 태도를 가지고 있습니까?",
        1,
        10,
        5,
        key=f"{prefix}_attitude",
    )
    st.subheader("2. 따뜻함 느낌")
    warmth = st.slider(
        "귀하는 이주민에 대해 얼마나 따뜻한 감정을 느끼십니까?",
        0,
        100,
        50,
        key=f"{prefix}_warmth",
    )
    st.subheader("3. 사회적 거리감")
    social_distance = likert_questions(SOCIAL_DISTANCE_QUESTIONS, f"{prefix}_social")
    st.subheader("4. 이민 정책 선호")
    policy = likert_questions(POLICY_QUESTIONS, f"{prefix}_policy")
    result = {
        "attitude": attitude,
        "warmth": warmth,
        "social_distance": social_distance,
        "policy": policy,
    }
    if include_contact:
        st.subheader("5. 이주민 접촉 경험")
        result["contact_experience"] = st.radio(
            "귀하의 이주민 접촉 경험과 가장 가까운 항목을 선택해 주세요.",
            CONTACT_OPTIONS,
            index=None,
            key=f"{prefix}_contact",
        )
    return result


def avatar_data_uri():
    if not MIN_IMAGE_PATH.exists():
        return None
    suffix = MIN_IMAGE_PATH.suffix.lower().lstrip(".") or "png"
    encoded = base64.b64encode(MIN_IMAGE_PATH.read_bytes()).decode("ascii")
    return f"data:image/{suffix};base64,{encoded}"


def render_message(entry):
    is_min = entry["speaker"] == "민"
    side = "left" if is_min else "right"
    bubble = "#f1f5f9" if is_min else "#2563eb"
    text_color = "#172033" if is_min else "white"
    avatar = avatar_data_uri() if is_min else None
    avatar_html = (
        f'<img src="{avatar}" class="avatar">'
        if avatar
        else f'<div class="avatar fallback">{"민" if is_min else "나"}</div>'
    )
    safe_message = html.escape(entry["message"]).replace("\n", "<br>")
    st.markdown(
        f"""
        <div class="message-row {side}">
          {avatar_html}
          <div class="message-content">
            <div class="speaker">{entry["speaker"]}</div>
            <div class="bubble" style="background:{bubble};color:{text_color}">{safe_message}</div>
            <div class="message-time">{entry["timestamp"][11:16]}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.fragment(run_every=1)
def live_timer():
    elapsed = int(time.time() - st.session_state.chat_started_at)
    remaining = max(0, CHAT_DURATION_SECONDS - elapsed)
    minutes, seconds = divmod(remaining, 60)
    st.markdown(f"### 남은 대화 시간: {minutes}:{seconds:02d}")
    if remaining == 0 and st.session_state.chat_ended_at is None:
        st.session_state.chat_ended_at = time.time()
        st.rerun()


def ask_min():
    api_key = get_setting("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")
    model = get_setting("OPENAI_MODEL", "gpt-4.1-mini")
    history = [
        {
            "role": "assistant" if item["speaker"] == "민" else "user",
            "content": item["message"],
        }
        for item in st.session_state.chat_history
    ]
    payload = json.dumps(
        {
            "model": model,
            "instructions": SYSTEM_PROMPT,
            "input": history,
            "max_output_tokens": 250,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API 오류: HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI API 연결 실패: {exc.reason}") from exc

    texts = [
        content["text"]
        for output in result.get("output", [])
        for content in output.get("content", [])
        if content.get("type") == "output_text" and content.get("text")
    ]
    if not texts:
        raise RuntimeError("OpenAI API가 빈 답변을 반환했습니다.")
    return "\n".join(texts).strip()


def save_data():
    chat_end = st.session_state.chat_ended_at or time.time()
    chat_start = st.session_state.chat_started_at or chat_end
    row = {
        "submission_id": st.session_state.submission_id,
        "participant_id": st.session_state.participant_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "pre_attitude": st.session_state.pre["attitude"],
        "pre_warmth": st.session_state.pre["warmth"],
        "pre_social_distance": json.dumps(st.session_state.pre["social_distance"], ensure_ascii=False),
        "pre_policy": json.dumps(st.session_state.pre["policy"], ensure_ascii=False),
        "contact_experience": st.session_state.pre["contact_experience"],
        "chat_log": json.dumps(st.session_state.chat_history, ensure_ascii=False),
        "conversation_duration_seconds": min(CHAT_DURATION_SECONDS, max(0, int(chat_end - chat_start))),
        "post_attitude": st.session_state.post["attitude"],
        "post_warmth": st.session_state.post["warmth"],
        "post_social_distance": json.dumps(st.session_state.post["social_distance"], ensure_ascii=False),
        "post_policy": json.dumps(st.session_state.post["policy"], ensure_ascii=False),
        "helping_intention": json.dumps(st.session_state.post["helping_intention"], ensure_ascii=False),
        "manipulation_check": json.dumps(st.session_state.post["manipulation_check"], ensure_ascii=False),
    }
    supabase_url = get_setting("SUPABASE_URL")
    supabase_key = get_setting("SUPABASE_SERVICE_ROLE_KEY")
    if supabase_url and supabase_key:
        save_to_supabase(row, supabase_url, supabase_key)
        return
    if str(get_setting("REQUIRE_REMOTE_STORAGE", "false")).lower() == "true":
        raise RuntimeError("원격 저장소가 설정되지 않았습니다. 관리자에게 문의해 주세요.")
    file_exists = DATA_FILE.exists() and DATA_FILE.stat().st_size > 0
    with DATA_FILE.open("a", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS, quoting=csv.QUOTE_MINIMAL)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def save_to_supabase(row, supabase_url, supabase_key):
    endpoint = f"{supabase_url.rstrip('/')}/rest/v1/research_responses"
    payload = json.dumps(
        {
            "submission_id": row["submission_id"],
            "participant_id": row["participant_id"],
            "submitted_at": row["timestamp"],
            "response_data": row,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        method="POST",
        headers={
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status not in (200, 201, 204):
                raise RuntimeError(f"Supabase 저장 실패: HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase 저장 실패: HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Supabase 연결 실패: {exc.reason}") from exc


def consent_step():
    st.header("연구 참여 동의서")
    st.write("본 연구는 AI 기반 대화가 이주민에 대한 태도에 미치는 영향을 조사하기 위한 연구입니다.")
    st.markdown(
        """
        - 참여는 자발적입니다.
        - 언제든 중단할 수 있습니다.
        - 참가자 ID, 설문 응답 및 대화 기록이 연구 자료로 저장됩니다.
        - 대화 내용은 답변 생성을 위해 OpenAI API로 전송됩니다.
        - 이름, 연락처 등 개인을 식별할 수 있는 정보는 입력하지 마세요.
        - 연구 목적 외에는 사용되지 않습니다.
        """
    )
    researcher_contact = get_setting("RESEARCHER_CONTACT")
    if researcher_contact:
        st.caption(f"연구 문의: {researcher_contact}")
    agreed = st.checkbox("위 내용을 읽고 연구 참여에 동의합니다.")
    if st.button("동의하고 시작하기", type="primary", disabled=not agreed):
        go_to_step(2)


def participant_step():
    st.header("참여자 정보")
    participant_id = st.text_input("참가자 ID", value=st.session_state.participant_id).strip()
    if st.button("다음", type="primary"):
        if not participant_id:
            st.error("참가자 ID를 입력해 주세요.")
        else:
            st.session_state.participant_id = participant_id
            go_to_step(3)


def pretest_step():
    st.header("사전 설문")
    with st.form("pretest_form"):
        answers = attitude_survey("pre", include_contact=True)
        submitted = st.form_submit_button("다음", type="primary")
    if submitted:
        required = answers["social_distance"] + answers["policy"] + [answers["contact_experience"]]
        if any(value is None for value in required):
            st.error("모든 문항에 응답해 주세요.")
        else:
            st.session_state.pre = answers
            go_to_step(4)


def chat_step():
    st.header("민과의 대화")
    st.write("민은 한국에서 약 5년간 생활한 베트남 출신 이주민입니다. 3분 동안 자유롭게 대화해 주세요.")
    if st.session_state.chat_started_at is None:
        if st.button("대화 시작하기", type="primary"):
            st.session_state.chat_started_at = time.time()
            st.rerun()
        return

    elapsed = int(time.time() - st.session_state.chat_started_at)
    remaining = max(0, CHAT_DURATION_SECONDS - elapsed)
    expired = remaining <= 0
    if expired and st.session_state.chat_ended_at is None:
        st.session_state.chat_ended_at = time.time()
    live_timer()

    for entry in st.session_state.chat_history:
        render_message(entry)

    if not expired:
        with st.form("chat_form", clear_on_submit=True):
            message = st.text_input("메시지", placeholder="민에게 메시지를 보내세요.", label_visibility="collapsed")
            sent = st.form_submit_button("보내기", type="primary")
        if sent and message.strip():
            user_entry = {
                "speaker": "참여자",
                "message": message.strip(),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
            st.session_state.chat_history.append(user_entry)
            with st.spinner("민이 답변을 작성하고 있습니다..."):
                try:
                    reply = ask_min()
                except Exception as exc:
                    st.session_state.chat_history.pop()
                    st.error(f"답변을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요. ({exc})")
                    return
            if reply:
                st.session_state.chat_history.append(
                    {"speaker": "민", "message": reply, "timestamp": datetime.now().isoformat(timespec="seconds")}
                )
                st.rerun()
    else:
        st.info("3분간의 대화가 종료되었습니다.")
        if st.button("설문으로 이동", type="primary"):
            go_to_step(5)


def posttest_step():
    st.header("사후 설문")
    with st.form("posttest_form"):
        answers = attitude_survey("post")
        st.subheader("5. 민에 대한 도움 의향")
        helping = likert_questions(HELPING_QUESTIONS, "post_help", "전혀 의향이 없다", "매우 의향이 있다")
        st.subheader("6. 조작 점검")
        manipulation = likert_questions(MANIPULATION_QUESTIONS, "post_manipulation")
        submitted = st.form_submit_button("제출하기", type="primary")
    if submitted:
        required = answers["social_distance"] + answers["policy"] + helping + manipulation
        if any(value is None for value in required):
            st.error("모든 문항에 응답해 주세요.")
        else:
            answers["helping_intention"] = helping
            answers["manipulation_check"] = manipulation
            st.session_state.post = answers
            try:
                save_data()
                st.session_state.saved = True
                go_to_step(6)
            except Exception as exc:
                st.error(f"응답 저장 중 오류가 발생했습니다: {exc}")


def completion_step():
    st.header("연구 참여 완료")
    st.success("참여해 주셔서 감사합니다. 응답이 저장되었습니다.")


st.set_page_config(page_title="AI 대화 연구", page_icon="💬", layout="centered")
st.markdown(
    """
    <style>
      .message-row {display:flex; gap:10px; margin:16px 0; align-items:flex-start;}
      .message-row.right {flex-direction:row-reverse;}
      .message-content {max-width:76%;}
      .message-row.right .message-content {text-align:right;}
      .avatar {width:44px;height:44px;border-radius:50%;object-fit:cover;flex:none;}
      .fallback {display:flex;align-items:center;justify-content:center;background:#dbeafe;font-weight:700;}
      .speaker {font-size:13px;font-weight:700;margin-bottom:4px;color:#475569;}
      .bubble {padding:11px 14px;border-radius:16px;text-align:left;line-height:1.55;}
      .message-time {font-size:11px;color:#94a3b8;margin-top:3px;}
    </style>
    """,
    unsafe_allow_html=True,
)
init_state()
missing_settings = deployment_ready()
if missing_settings:
    st.error("현재 연구 앱을 준비 중입니다. 관리자 설정이 완료된 후 다시 접속해 주세요.")
    with st.expander("관리자용 설정 정보"):
        st.code("\n".join(missing_settings))
    st.stop()
st.title("AI 대화와 이주민 태도 연구")
st.progress(st.session_state.step / 6)

steps = {
    1: consent_step,
    2: participant_step,
    3: pretest_step,
    4: chat_step,
    5: posttest_step,
    6: completion_step,
}
steps[st.session_state.step]()
