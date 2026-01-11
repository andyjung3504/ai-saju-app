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
# [핵심 수정 기능] 질문 내 날짜 추출 및 DB 강제 매핑
# ==============================================================================
def get_db_ganji_for_query(query_text):
    """
    사용자 질문에서 날짜를 감지하고, 해당 날짜의 만세력(간지) 데이터를 DB에서 가져온다.
    날짜 언급이 없으면 현재 시간(Now)을 기준으로 DB를 조회한다.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={FIXED_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # 1. 질문에서 날짜/시간 추출 (AI는 파싱만 수행, 계산 금지)
    now = datetime.now()
    prompt = f"""
    Current Time: {now.strftime('%Y-%m-%d %H:%M:%S')}
    Task: Extract the target date and time from the user's query: "{query_text}"
    - If the user asks about a specific date (e.g., "tomorrow", "next month", "2027-01-01"), return that date.
    - If no specific date is mentioned, return the Current Time.
    - Return JSON ONLY: {{"year": 2026, "month": 5, "day": 5, "hour": 14, "is_specific": true}}
    """
    try:
        r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": prompt}]}]})
        res_json = json.loads(r.json()['candidates'][0]['content']['parts'][0]['text'].replace("```json", "").replace("```", "").strip())
        
        t_y, t_m, t_d, t_h = res_json['year'], res_json['month'], res_json['day'], res_json.get('hour', 12)
        
        # 2. DB(saju_logic)에서 해당 시점의 간지 데이터 조회
        # analyze_user 함수를 '해당 시점의 사주 뽑기' 용도로 재사용 (성별/음양은 기본값 처리)
        # 이것이 곧 그 날짜의 연주, 월주, 일주, 시주가 된다.
        db_data = analyze_user(t_y, t_m, t_d, t_h, False, "남성") 
        
        if "error" in db_data:
            return f"[시스템 경고] DB 조회 오류: {db_data['error']}"

        return f"""
        [★ 시스템 강제 주입: DB 만세력 데이터]
        - 기준 시점(양력): {t_y}년 {t_m}월 {t_d}일 {t_h}시
        - DB 산출 간지(원국): {db_data['사주']}
        - 분석 지침: 너의 내부 지식을 사용하지 말고, 무조건 위 'DB 산출 간지'를 기준으로 운세를 분석하라. 
        """
    except Exception as e:
        # 오류 발생 시 현재 시간 기준 DB 데이터라도 가져옴
        return f"[시스템 로그] 날짜 파싱 실패, 현재 시간 기준 분석. ({e})"

# [기능 1] 타인 사주 DB 조회 (기존 유지)
def extract_and_analyze_target(text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={FIXED_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    prompt = f"""
    Task: Extract birth date from text: "{text}"
    Return JSON: {{"found": true, "year": 1964, "month": 6, "day": 30, "lunar": true, "gender": "여성"}}
    - Default to Lunar(true) if '음력' mentioned.
    - If 2-digit year (e.g., 64), assume 19xx.
    - If no date, return {{"found": false}}
    """
    try:
        r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": prompt}]}]})
        res_json = json.loads(r.json()['candidates'][0]['content']['parts'][0]['text'].replace("```json", "").replace("```", "").strip())
        if res_json.get("found"):
            y, m, d = res_json['year'], res_json['month'], res_json['day']
            is_lunar = res_json['lunar']
            gender = res_json['gender']
            target_res = analyze_user(y, m, d, 0, is_lunar, gender)
            if "error" in target_res: return f"\n[시스템] 상대방 DB 조회 실패: {target_res['error']}"
            return f"""
            \n[★ 상대방 명식 데이터 (DB 기반)]
            - 정보: {y}년 {m}월 {d}일 ({'음력' if is_lunar else '양력'}) / {gender}
            - 사주: {target_res['사주']} / 대운: {target_res['대운']}
            - 지침: 위 데이터를 바탕으로 본인(내담자)과의 궁합, 상생/상극 관계를 명리학적으로 분석하시오.
            """
        else: return ""
    except: return ""

# [기능 2] 1년치 월운 전수조사
def get_yearly_detailed_flow(year):
    flow_text = f"\n[★ {year}년 월별 상세 간지 데이터 (DB 기반)]\n"
    try:
        for m in range(1, 13):
            data = get_monthly_ganji(year, m)
            if data: flow_text += f"- {m}월: {data['month_ganji']} (세운 {data['year_ganji']}과의 관계 분석 필요)\n"
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
                st.session_state['chat_input_manual'] = kw + "에 대해 자평명리와 궁통보감의 관점에서 정밀하게 분석하고, 구체적인 인생 전략을 제시해 주십시오."
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

        # 1. DB에서 사주 원국 산출 (AI 계산 X)
        result = analyze_user(birth_date.year, birth_date.month, birth_date.day, birth_time.hour, is_lunar, gender)
        
        if "error" in result:
            st.error(result["error"])
        else:
            with st.expander("📊 정밀 명식 산출 결과", expanded=True):
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    st.info(f"내담자: {name} ({gender})")
                    st.write(f"자미두수 명궁: **{result['자미두수']['명궁위치']}**")
                with c2:
                    st.write(f"사주 원국: {result['사주']}")
                    st.write(f"대운 흐름: {result['대운']}")
                with c3:
                    if st.button("💾 상담 기록 DB 저장"):
                        save_consultation(st.session_state['user_id'], name, gender, birth_date, birth_time, memo="마스터 분석")
                        st.toast("저장 완료")

            if 'lifetime_script' not in st.session_state:
                now = datetime.now()
                # 초기 로딩 시 현재 연도의 데이터만 가져옴
                yearly_data = get_yearly_detailed_flow(now.year)
                
                # 시스템 프롬프트 (기존 지침 유지)
                system_instruction = f"""
                [Role Definition]
                당신은 '자평명리학(구조)', '궁통보감(조후)', '적천수(억부)', '맹파명리(시기)'를 통합하여 분석하는 40년 경력의 명리학 마스터입니다.
                단순한 운세 풀이를 넘어, 정밀한 산출과 논리적 추론을 통해 내담자의 인생 전략을 설계하십시오.

                [Input Data]
                - 내담자: {name} ({gender}, 만 {2025 - birth_date.year}세)
                - 사주 명식: {result['사주']} (DB 기반 정확한 데이터)
                - 대운 흐름: {result['대운']} (한국 나이 대운수 적용)
                - 올해 월별 운세 데이터: {yearly_data}

                [Analysis Protocol (Step-by-Step Thinking)]
                (이하 기존 프롬프트와 동일...)
                **STEP 1. 정밀 명식 분석**
                **STEP 2. 구조 및 물상(Imagery) 분석**
                **STEP 3. 통합 용신 도출 (Synthesis)**
                **STEP 4. 신살(神殺) 정밀 분석 (균형 잡힌 시각)**
                **STEP 5. 대운 및 세운 통변 (Prediction)**
                **STEP 6. 마스터 솔루션 (Advice)**
                
                [Output Style]
                - 전문 용어는 한자를 병기하되, 일반인이 이해하기 쉬운 비유를 섞어 품격 있게 서술할 것.
                - 억지스러운 악담이나 빈말은 배제하고, **냉철한 분석(Fact)과 따뜻한 조언(Solution)**의 균형을 유지할 것.
                - 분량: A4 3장 이상의 깊이 있는 보고서.
                """
                
                with st.spinner("명리학 마스터가 내담자의 사주를 정밀 분석하여 인생 전략을 수립 중입니다..."):
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
                elif u_in := st.chat_input("질문을 입력하십시오. (예: 내일 중요한 계약이 있는데 일진이 어떤가요?)"):
                    prompt = u_in
                
                if prompt:
                    st.session_state['chat_history'].append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.write(prompt)
                    
                    # 1. 타인 사주 조회 (기존 로직)
                    target_info = extract_and_analyze_target(prompt)
                    
                    # 2. [NEW] 질문 시점에 대한 DB 만세력 조회 (날짜 파싱 -> DB 조회)
                    # 질문에 특정 날짜가 없으면 '현재 시간' 기준으로 가져옴
                    query_time_ganji = get_db_ganji_for_query(prompt)

                    # 3. 프롬프트 구성
                    chat_ctx = f"{st.session_state['lifetime_script']}\n\n[이전 상담 내용]\n"
                    for m in st.session_state['chat_history'][:-1]:
                        chat_ctx += f"{m['role']}: {m['content']}\n"
                    
                    if target_info: chat_ctx += target_info
                    chat_ctx += f"\n{query_time_ganji}\n" # DB 데이터 주입
                    
                    chat_ctx += f"\n[현재 질문] {prompt}\n"
                    chat_ctx += """
                    [지침]
                    1. 반드시 위에서 제공된 '[시스템 강제 주입: DB 만세력 데이터]'를 기준으로 운세를 분석하시오. 네가 알고 있는 지식으로 날짜를 계산하지 마시오.
                    2. 질문에 타인의 생년월일이 포함된 경우, 제공된 [상대방 명식 데이터]를 내담자의 사주와 대조하여 궁합을 분석하시오.
                    3. 원국(내담자)과 운(DB 데이터)의 합/충/형/해 상호작용을 논리적으로 설명하시오.
                    """
                    
                    with st.spinner("DB 데이터를 기반으로 정밀 분석 중..."):
                        try:
                            r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": chat_ctx}]}]})
                            ai_msg = r.json()['candidates'][0]['content']['parts'][0]['text']
                            st.session_state['chat_history'].append({"role": "assistant", "content": ai_msg})
                            with st.chat_message("assistant"):
                                st.write(ai_msg)
                            st.rerun()
                        except: st.error("응답 생성 실패")