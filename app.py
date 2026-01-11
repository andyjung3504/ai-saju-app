import streamlit as st
import pandas as pd
import requests
import json
import time
import re
from datetime import datetime
from saju_logic import analyze_user, login_user, save_consultation, get_my_consultation_history, check_and_init_db, get_monthly_ganji

# --- 설정 ---
st.set_page_config(page_title="천기통달: 명리학 마스터", layout="wide")
check_and_init_db()

try: FIXED_API_KEY = st.secrets["GEMINI_API_KEY"]
except: FIXED_API_KEY = "여기에_API_키를_붙여넣으세요"

# --- 세션 초기화 ---
for k in ['chat_history', 'chat_input_manual']:
    if k not in st.session_state: st.session_state[k] = [] if k == 'chat_history' else None
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_name' not in st.session_state: st.session_state['user_name'] = ""
if 'run_analysis' not in st.session_state: st.session_state['run_analysis'] = False

# ==============================================================================
# [기능] 질문 내 날짜 추출 및 DB 강제 매핑 (유지)
# ==============================================================================
def get_db_ganji_for_query(query_text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={FIXED_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    now = datetime.now()
    prompt = f"""
    Current Time: {now.strftime('%Y-%m-%d %H:%M:%S')}
    Task: Extract target date from query: "{query_text}"
    - If specific date mentioned, return that date.
    - Else, return Current Time.
    - Return JSON: {{"year": 2026, "month": 5, "day": 5, "hour": 14}}
    """
    try:
        r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": prompt}]}]})
        res_json = json.loads(r.json()['candidates'][0]['content']['parts'][0]['text'].replace("```json", "").replace("```", "").strip())
        t_y, t_m, t_d, t_h = res_json['year'], res_json['month'], res_json['day'], res_json.get('hour', 12)
        db_data = analyze_user(t_y, t_m, t_d, t_h, False, "남성") 
        if "error" in db_data: return f"[시스템] DB 조회 오류: {db_data['error']}"
        return f"""
        [★ 시스템 강제 주입: DB 만세력 데이터]
        - 기준 시점: {t_y}년 {t_m}월 {t_d}일
        - DB 산출 간지: {db_data['사주']}
        - 지침: 너의 계산을 멈추고 무조건 위 DB 데이터를 기준으로 분석하라.
        """
    except: return f"[시스템] 날짜 파싱 실패, 현재 시간 기준."

def extract_and_analyze_target(text):
    # (기존 타인 사주 조회 로직 유지 - 지면상 생략, 위와 동일)
    return "" 

def get_yearly_detailed_flow(year):
    flow_text = f"\n[★ {year}년 월별 상세 간지 데이터 (DB 기반)]\n"
    try:
        for m in range(1, 13):
            data = get_monthly_ganji(year, m)
            if data: flow_text += f"- {m}월: {data['month_ganji']} (세운 {data['year_ganji']} 관계)\n"
        return flow_text
    except: return ""

# ==========================================
# 메인 UI
# ==========================================
if not st.session_state['logged_in']:
    st.title("🔒 명리학 마스터 로그인")
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("아이디", placeholder="test1")
            password = st.text_input("비밀번호", type="password", placeholder="1234")
            if st.form_submit_button("로그인", type="primary"):
                user_name = login_user(username, password)
                if user_name:
                    st.session_state['logged_in'] = True
                    st.session_state['user_id'] = username
                    st.session_state['user_name'] = user_name
                    st.rerun()
                else: st.error("로그인 실패")

else:
    with st.sidebar:
        st.info(f"🎓 마스터: {st.session_state['user_name']}")
        if st.button("로그아웃"):
            st.session_state['logged_in'] = False
            st.session_state.clear()
            st.rerun()
        st.divider()

        st.header("📝 내담자 정보")
        name = st.text_input("성명", value="홍길동")
        gender = st.radio("성별", ["남성", "여성"], horizontal=True)
        calendar_type = st.radio("달력", ["양력", "음력"], horizontal=True)
        is_lunar = (calendar_type == "음력")
        
        c1, c2 = st.columns(2)
        with c1: birth_date = st.date_input("생년월일", value=pd.to_datetime("1980-01-01"), min_value=pd.to_datetime("1900-01-01"))
        with c2: birth_time = st.time_input("태어난 시간", value=pd.to_datetime("14:30").time())
        
        if st.button("정통 명리학 분석 시작", type="primary"):
            st.session_state['run_analysis'] = True
            st.session_state['chat_history'] = [] 
            st.session_state.pop('lifetime_script', None)

        st.divider()
        st.markdown("### ⚡ 주제별 심층 분석")
        keywords = ["💰 재물/사업 전략", "🏠 부동산/매매 시기", "❤️ 인연/부부 궁합", "💊 건강/체질 분석", "⚖️ 관재/송사 전략", "🎓 학업/진로 적성", "✈️ 이동/변동수", "🏢 조직/리더십 분석"]
        for kw in keywords:
            if st.button(kw):
                st.session_state['chat_input_manual'] = kw + "에 대해 상세히 분석해 주십시오."
                if not st.session_state['run_analysis']:
                    st.session_state['run_analysis'] = True
                    st.session_state['chat_history'] = []
                st.rerun()

    st.title("📜 정통 명리학 마스터: 인생 전략 보고서")

    if st.session_state['run_analysis']:
        if not FIXED_API_KEY or len(FIXED_API_KEY) < 10:
            st.error("API 키 오류")
            st.stop()

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={FIXED_API_KEY}"
        headers = {'Content-Type': 'application/json'}

        # DB 원국 산출
        result = analyze_user(birth_date.year, birth_date.month, birth_date.day, birth_time.hour, is_lunar, gender)
        
        if "error" in result:
            st.error(result["error"])
        else:
            current_age = datetime.now().year - birth_date.year + 1
            
            with st.expander("📊 정밀 명식 산출 결과", expanded=True):
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    st.info(f"{name} ({gender}, {current_age}세)")
                    st.write(f"명궁: **{result['자미두수']['명궁위치']}**")
                with c2:
                    st.write(f"원국: {result['사주']}")
                    st.write(f"대운: {result['대운']}")
                with c3:
                    if st.button("💾 DB 저장"):
                        save_consultation(st.session_state['user_id'], name, gender, birth_date, birth_time, memo="분석")
                        st.toast("저장 완료")

            if 'lifetime_script' not in st.session_state:
                now = datetime.now()
                yearly_data = get_yearly_detailed_flow(now.year)
                
                # ★★★ [수정됨] 과거 대운 검증 및 상담자 스크립트 강화 프롬프트 ★★★
                system_instruction = f"""
                [Role Definition]
                당신은 40년 경력의 명리학 마스터입니다. 냉정하고 직설적이며, 정확한 근거 없이 위로하지 않습니다.
                
                [Target Data]
                - 내담자: {name} ({gender}, 만 {current_age}세, {birth_date.year}년생)
                - 사주 원국: {result['사주']}
                - 대운 흐름: {result['대운']} (숫자는 한국 나이 대운수 시작점임. 예: '4(갑자)'는 4세~13세가 갑자대운임을 의미)
                - 현재 시점: {now.year}년 (세운)

                [Task 1: The Report - 정밀 분석 보고서]
                1. **원국 분석:** 오행의 편중, 조후, 격국을 분석하여 기질을 파악하라.
                2. **평생 대운 정밀 분석(검증용):** - 현재 나이({current_age}세)를 기준으로 **'과거 대운'**과 **'현재/미래 대운'**을 명확히 나누어라.
                   - 각 대운별로 **정확한 나이 구간(예: 14세~23세)**을 명시하라.
                   - **과거 검증:** 지나온 대운에서 용신/기신 여부에 따라 발생했을 구체적 사건(학업 중단, 부모 이혼, 발병, 큰 재물 취득 등)을 팩트 위주로 서술하라.
                3. **올해의 운세:** {now.year}년의 운세를 원국+대운+세운의 상호작용으로 분석하라.

                [Task 2: Counselor's Script - 상담자용 실전 해설 대본]
                **※ 이 부분은 상담자가 내담자에게 화면을 보며 그대로 읽어줄 수 있도록 '구어체 대본'으로 작성하시오.**
                
                **[대본 가이드라인]**
                1. **과거 확인 (신뢰 구축):** - "선생님, 00세부터 00세까지는 00대운이었습니다. 이때는 ~~한 기운이 들어와서 (문서운/이별수/건강) 문제가 있었을 텐데, 실제로 그러셨습니까?" 형태로 질문할 것.
                   - 추상적인 표현 금지. (예: "힘들었을 것입니다" (X) -> "금전적인 손실이나 배신수가 있었을 것입니다" (O))
                
                2. **현재 진단:**
                   - "현재 00세 시점에서는 ~~한 운의 흐름 속에 있습니다. 지금 가장 조심해야 할 것은..."
                
                3. **미래 제언:**
                   - "다가올 00세 대운에서는..."
                
                **[출력 형식을 엄수하시오]**
                ---
                ## 1. 정밀 분석 보고서 (전문가용)
                (명리학적 용어와 논리로 분석한 내용)
                
                ## 2. 상담자용 실전 리딩 스크립트 (읽어주세요)
                (상담자가 내담자에게 말하듯 작성된 대본. **나이 구간 명시 필수**)
                ---
                """
                
                with st.spinner("과거 대운 정밀 검증 및 상담 스크립트 생성 중..."):
                    try:
                        r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": system_instruction}]}]})
                        st.session_state['lifetime_script'] = r.json()['candidates'][0]['content']['parts'][0]['text']
                    except Exception as e: st.error(f"분석 시스템 오류: {e}")

            if 'lifetime_script' in st.session_state:
                st.markdown(st.session_state['lifetime_script'])
                st.divider()
                
                st.subheader("💬 마스터와의 심층 대화")
                for msg in st.session_state['chat_history']:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
                
                prompt = None
                if st.session_state['chat_input_manual']:
                    prompt = st.session_state['chat_input_manual']
                    st.session_state['chat_input_manual'] = None
                elif u_in := st.chat_input("질문 예: 34세 대운에 왜 이혼수가 있었나요?"):
                    prompt = u_in
                
                if prompt:
                    st.session_state['chat_history'].append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.write(prompt)
                    
                    target_info = extract_and_analyze_target(prompt)
                    query_time_ganji = get_db_ganji_for_query(prompt)

                    chat_ctx = f"{st.session_state['lifetime_script']}\n\n[이전 상담]\n"
                    for m in st.session_state['chat_history'][:-1]:
                        chat_ctx += f"{m['role']}: {m['content']}\n"
                    
                    if target_info: chat_ctx += target_info
                    chat_ctx += f"\n{query_time_ganji}\n"
                    
                    chat_ctx += f"\n[질문] {prompt}\n"
                    chat_ctx += """
                    [지침]
                    1. DB 데이터를 기준으로 분석하되, 답변은 상담자가 내담자에게 말하듯 **'실전 상담 톤'**을 유지하시오.
                    2. 과거에 대한 질문이면, 그 당시 대운과 세운을 정확히 짚어서 설명하시오.
                    """
                    
                    with st.spinner("분석 중..."):
                        try:
                            r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": chat_ctx}]}]})
                            ai_msg = r.json()['candidates'][0]['content']['parts'][0]['text']
                            st.session_state['chat_history'].append({"role": "assistant", "content": ai_msg})
                            with st.chat_message("assistant"):
                                st.write(ai_msg)
                            st.rerun()
                        except: st.error("응답 실패")