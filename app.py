import streamlit as st
import pandas as pd
import json
from openai import OpenAI

# ──────────────────────────────────────────────────────────────
# 페이지 설정 (반드시 맨 처음에 와야 합니다!)
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="J-POP 가사 분석기",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────────────────────
# 2. 🔒 접속 비밀번호 잠금 화면
# ──────────────────────────────────────────────────────────────
def check_password():
    # 1) 이미 비밀번호를 맞췄던 기억(메모리)이 있다면 창을 띄우지 않고 바로 통과!
    if st.session_state.get("password_correct", False):
        return True

    # 2) 아직 안 맞췄다면 비밀번호 입력창 띄우기
    st.markdown("<h3 style='text-align: center; margin-top: 50px;'>🔒 J-POP 학습기 접근 권한 확인</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password = st.text_input("교수님/조원 전용 접속 비밀번호를 입력해 주세요.", type="password", placeholder="비밀번호 4자리")
        
        if password == "6802":  # 원하는 비밀번호
            st.session_state["password_correct"] = True  # 맞췄다는 사실을 메모리에 저장
            st.rerun()  # 화면을 즉시 새로고침해서 비밀번호 창을 날려버림!
        elif password != "":
            st.error("❌ 비밀번호가 일치하지 않습니다.")
            
    return False

if not check_password():
    st.stop() # 비밀번호가 맞을 때까지 아래의 모든 메인 화면은 절대 열리지 않습니다.

# ──────────────────────────────────────────────────────────────
# 커스텀 CSS (미니멀 & 태블릿 최적화)
# ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main .block-container {
        max-width: 1100px;
        padding-top: 2.5rem;
        padding-bottom: 3rem;
    }
    h1 {
        font-weight: 700;
        letter-spacing: -0.5px;
        color: #1a1a1a;
    }
    .app-subtitle {
        color: #6b7280;
        font-size: 1.05rem;
        margin-top: -0.5rem;
        margin-bottom: 2rem;
    }
    .stTextArea textarea {
        font-size: 1.05rem;
        line-height: 1.7;
        font-family: 'Hiragino Sans', 'Noto Sans JP', sans-serif;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
    }
    .stButton button {
        background: linear-gradient(135deg, #ec4899 0%, #8b5cf6 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: transform 0.15s ease;
    }
    .stButton button:hover {
        transform: translateY(-1px);
        color: white;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #e5e7eb;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 1rem;
        font-weight: 500;
        padding: 0.6rem 1.2rem;
    }
    .result-box {
        background: #fafafa;
        border-left: 4px solid #8b5cf6;
        padding: 1.2rem 1.5rem;
        border-radius: 8px;
        line-height: 1.9;
        font-size: 1.05rem;
        margin: 1rem 0;
    }
    .nuance-box {
        background: #fdf4ff;
        border-radius: 8px;
        padding: 1rem 1.3rem;
        margin-top: 1rem;
        color: #6b21a8;
        font-size: 0.95rem;
    }
    .grammar-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# 헤더
# ──────────────────────────────────────────────────────────────
st.markdown("# 🎵 J-POP 가사 분석 & 로컬라이징 번역 학습기")
st.markdown(
    '<p class="app-subtitle">좋아하는 J-POP 가사를 붙여넣으면, AI가 단어·문법·직역·의역을 한 번에 분석해 드려요.</p>',
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────
# OpenAI 클라이언트
# ──────────────────────────────────────────────────────────────
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    st.error("⚠️ `OPENAI_API_KEY`가 설정되지 않았습니다. `.streamlit/secrets.toml`을 확인해 주세요.")
    st.stop()

# ──────────────────────────────────────────────────────────────
# 입력 영역
# ──────────────────────────────────────────────────────────────
lyrics = st.text_area(
    "📝 J-POP 가사 입력 (일본어)",
    height=260,
    placeholder="例)\n夜に駆ける\n沈むように溶けてゆくように\n二人だけの空が広がる夜に…",
)

col1, col2 = st.columns([1, 5])
with col1:
    run = st.button("✨ 분석 및 번역 시작", use_container_width=True)

# ──────────────────────────────────────────────────────────────
# 프롬프트
# ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """당신은 J-POP 가사 분석 및 한일 번역 전문가입니다.
입력된 일본어 가사를 분석하여 반드시 아래 JSON 스키마에 맞춰 한국어로 응답하세요.

{
  "vocabulary": [
    {"word": "일본어 단어", "yomigana": "요미가나(히라가나)", "meaning": "한국어 뜻", "jlpt": "N1~N5"}
  ],
  "grammar": [
    {"pattern": "문법 표현", "morphology": "형태소 분석", "meaning": "한국어 뜻 설명", "example": "예문(일본어) — 한국어 해석"}
  ],
  "literal_translation": "가사의 직역 (줄바꿈은 \\n으로)",
  "localized_translation": "한국 정서에 맞는 자연스러운 의역 (줄바꿈은 \\n으로)",
  "localization_note": "의역 시 반영한 뉘앙스/문화적 배경 1~2줄 설명"
}

규칙:
- vocabulary는 **반드시 20개 이상** 추출하세요. 가사에 등장하는 명사·동사·형용사·부사를 빠짐없이 망라하되, 조사·기초 대명사는 제외합니다. 단어가 부족하면 활용형·파생어·관용 표현까지 포함해 20개를 채우세요.
- grammar는 **반드시 20개 이상** 추출하세요. 조동사(～た, ～ない, ～れる/られる), 접속 표현(～て, ～ながら, ～のに), 종조사(～ね, ～よ, ～かな), 회화체 축약(～ちゃう, ～じゃない), 고급 문형(～に違いない, ～っぱなし 등)을 폭넓게 포함합니다. 동일 표현 중복은 금지.
- 중요도/난이도 순으로 정렬해 주세요 (어휘는 핵심도 높은 순, 문법은 JLPT 난이도 높은 순).
- 모든 설명은 한국어로 작성.
- JSON 외 다른 텍스트는 절대 출력하지 말 것.
"""

# ──────────────────────────────────────────────────────────────
# 실행
# ──────────────────────────────────────────────────────────────
if run:
    if not lyrics.strip():
        st.warning("가사를 먼저 입력해 주세요.")
        st.stop()

    with st.spinner("AI가 가사를 분석 중입니다... 🎧"):
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"다음 J-POP 가사를 분석해 주세요:\n\n{lyrics}"},
                ],
                response_format={"type": "json_object"},
                temperature=0.5,
                max_tokens=4000,
            )
            data = json.loads(resp.choices[0].message.content)
        except Exception as e:
            st.error(f"분석 중 오류가 발생했습니다: {e}")
            st.stop()

    # ──────────────────────────────────────────────
    # 결과 탭
    # ──────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📚 핵심 단어장", "🔍 문법 분석", "📖 직역", "🌸 로컬라이징 (의역)"]
    )

    # ① 단어장
    with tab1:
        vocab_df = pd.DataFrame(data.get("vocabulary", []))
        st.subheader(f"핵심 단어장 ({len(vocab_df)}개)")
        if not vocab_df.empty:
            vocab_df.columns = ["단어", "요미가나", "뜻", "JLPT"]
            st.dataframe(vocab_df, use_container_width=True, hide_index=True, height=600)
        else:
            st.info("추출된 단어가 없습니다.")

    # ② 문법
    with tab2:
        grammar_list = data.get("grammar", [])
        st.subheader(f"핵심 문법 / 표현 ({len(grammar_list)}개)")
        for g in grammar_list:
            st.markdown(f"""
            <div class="grammar-card">
                <h4 style="margin:0 0 0.6rem 0; color:#8b5cf6;">▸ {g.get('pattern','')}</h4>
                <p><b>형태소 분석:</b> {g.get('morphology','')}</p>
                <p><b>의미:</b> {g.get('meaning','')}</p>
                <p><b>예문:</b> {g.get('example','')}</p>
            </div>
            """, unsafe_allow_html=True)

    # ③ 직역
    with tab3:
        st.subheader("직역 (Literal Translation)")
        literal = data.get("literal_translation", "").replace("\n", "<br>")
        st.markdown(f'<div class="result-box">{literal}</div>', unsafe_allow_html=True)

    # ④ 의역
    with tab4:
        st.subheader("로컬라이징 의역 (Localized Translation)")
        localized = data.get("localized_translation", "").replace("\n", "<br>")
        st.markdown(f'<div class="result-box">{localized}</div>', unsafe_allow_html=True)
        note = data.get("localization_note", "")
        if note:
            st.markdown(
                f'<div class="nuance-box">💡 <b>의역 노트:</b> {note}</div>',
                unsafe_allow_html=True,
            )

st.markdown("---")
st.caption("© 2026 J-POP Lyrics Analyzer · Powered by OpenAI GPT-4o-mini")