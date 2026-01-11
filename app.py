import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime, timedelta
# saju_logic 모듈 함수 로드
from saju_logic import analyze_user, login_user, save_consultation, get_monthly_ganji, get_db_data, check_and_init_db

# --- 설정 ---
st.set_page_config(page_title="천기통달: 명리학 마스터", layout="wide")

# DB 안전장치 가동
check_and_init_db()

try: FIXED_API_KEY = st.secrets["GEMINI_API_KEY"]
except: FIXED_API_KEY = "여기에_API_키를_붙여넣으세요"

# --- 세션 초기화 ---
for k in ['chat_history', 'chat_input_manual']:
    if k not in st.session_state: st.session_state[k] = [] if k == 'chat_history' else None
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_name' not in st.session_state: st.session_state['user_name'] = ""
if 'run_analysis' not in st.session_state: st.session_state['run_analysis'] = False
if 'analysis_mode' not in st.session_state: st.session_state['analysis_mode'] = "lifetime"

# ==============================================================================
# [기능 1] 2026년 길일/흉일 DB 정밀 추적 (DB 전수조사)
# ==============================================================================
def find_best_worst_days_2026(user_day_stem, user_day_branch):
    """
    내담자의 일간/일지를 기준으로 2026년 DB 데이터를 샅샅이 뒤져
    천을귀인(길일)과 충(흉일) 날짜를 찾아낸다.
    """
    nobleman_map = {
        '甲': ['丑', '未'], '戊': ['丑', '未'], '庚': ['丑', '未'],
        '乙': ['子', '申'], '己': ['子', '申'],
        '丙': ['亥', '酉'], '丁': ['亥', '酉'],
        '壬': ['巳', '卯'], '癸': ['巳', '卯'],
        '辛': ['午', '寅']
    }
    branches = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    
    my_branch_idx = branches.index(user_day_branch)
    chung_branch = branches[(my_branch_idx + 6) % 12] # 충
    
    target_good = nobleman_map.get(user_day_stem, [])
    target_bad = chung_branch

    found_good = []
    found_bad = []
    
    start_date = datetime(2026, 1, 1)
    # DB 부하를 줄이면서도 정확도를 위해 2일 간격 스캔 (필요시 1일로 수정 가능)
    for i in range(0, 365, 2): 
        curr = start_date + timedelta(days=i)
        row = get_db_data(curr.year, curr.month, curr.day, False) # 양력 조회
        if row:
            day_ganji = row[4] 
            day_branch = day_ganji[1]
            date_str = curr.strftime("%Y년 %m월 %d일")
            
            if len(found_good) < 3 and day_branch in target_good:
                found_good.append(f"{date_str}({day_ganji}, 천을귀인)")
            
            if len(found_bad) < 3 and day_branch == target_bad:
                found_bad.append(f"{date_str}({day_ganji}, {user_day_branch}충)")
                
        if len(found_good) >= 3 and len(found_bad) >= 3: break
            
    return found_good, found_bad

# ==============================================================================
# [기능 2] 질문 내 날짜 파싱 -> DB 데이터 매핑
# ==============================================================================
def get_db_ganji_for_query(query_text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={FIXED_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    now = datetime.now()
    prompt = f"""
    Current Time: {now.strftime('%Y-%m-%d %H:%M:%S')}
    Task: Extract target date from: "{query_text}"
    - If specific date, return it. Else return current time.
    - Return JSON: {{"year": 2026, "month": 5, "day": 5, "hour": 14}}
    """
    try:
        r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": prompt}]}]})
        res_json = json.loads(r.json()['candidates'][0]['content']['parts'][0]['text'].replace("```json", "").replace("```", "").strip())
        t_y, t_m, t_d, t_h = res_json['year'], res_json['month'], res_json['day'], res_json.get('hour', 12)
        
        db_data = analyze_user(t_y, t_m, t_d, t_h, False, "남성") 
        return f"[시스템 DB 데이터] 기준일: {t_y}년{t_m}월{t_d}일, 산출간지: {db_data.get('사주', 'DB오류')}"
    except: return f"[시스템] 날짜 인식 실패, 현재 시간 기준."

# ==============================================================================
# [기능 3] 타인 사주(궁합) 조회
# ==============================================================================
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

def get_yearly_detailed_flow(year):
    flow_text = f"\n[★ {year}년 월별 상세 흐름 (DB 기반)]\n"
    try:
        for m in range(1, 13):
            data = get_monthly_ganji(year, m)
            if data: flow_text += f"- {m}월: {data['month_ganji']} (세운 {data['year_ganji']}과의 관계)\n"
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
                else: st.error("로그인 실패 (ID/PW 확인 또는 DB 오류)")

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
        
        if st.button("🔄 정보 수정 및 리셋"):
            st.session_state['run_analysis'] = False
            st.session_state['chat_history'] = []
            st.session_state.pop('lifetime_script', None)
            st.rerun()

        st.divider()
        st.markdown("### ⚡ 주제별 심층 분석")
        
        # [NEW] 2026년 운세 버튼 (최상단 배치)
        if st.button("📅 2026년 병오년 총운 (길일/흉일 포함)"):
            st.session_state['run_analysis'] = True
            st.session_state['analysis_mode'] = "2026_fortune"
            st.session_state['chat_history'] = []
            st.session_state.pop('lifetime_script', None)
            st.rerun()

        # 기존 키워드들
        keywords = ["💰 재물/사업 전략", "🏠 부동산/매매 시기", "❤️ 인연/부부 궁합", "💊 건강/체질 분석", "⚖️ 관재/송사 전략", "🎓 학업/진로 적성", "✈️ 이동/변동수", "🏢 조직/리더십 분석"]
        
        for kw in keywords:
            if st.button(kw):
                st.session_state['chat_input_manual'] = kw + "에 대해 자평명리와 궁통보감의 관점에서 정밀하게 분석하고, 구체적인 인생 전략을 제시해 주십시오."
                st.session_state['run_analysis'] = True
                st.session_state['analysis_mode'] = "lifetime" # 일반 분석 모드
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
                    if st.button("💾 상담 기록 DB 저장"):
                        save_consultation(st.session_state['user_id'], name, gender, birth_date, birth_time, memo="분석")
                        st.toast("저장 완료")

            if 'lifetime_script' not in st.session_state:
                
                # ==========================================================
                # [MODE 1] 평생 심층 분석 (기존 app1.py 프롬프트 완벽 복구 + 상담 대본 추가)
                # ==========================================================
                if st.session_state['analysis_mode'] == "lifetime":
                    now = datetime.now()
                    yearly_data = get_yearly_detailed_flow(now.year)
                    
                    system_instruction = f"""
                    [Role Definition]
                    당신은 '자평명리학(구조)', '궁통보감(조후)', '적천수(억부)', '맹파명리(시기)'를 통합하여 분석하는 40년 경력의 명리학 마스터입니다.
                    단순한 운세 풀이를 넘어, 정밀한 산출과 논리적 추론을 통해 내담자의 인생 전략을 설계하십시오.

                    [Input Data]
                    - 내담자: {name} ({gender}, 만 {current_age}세)
                    - 사주 명식: {result['사주']} (DB 기반 정확한 데이터)
                    - 대운 흐름: {result['대운']} (한국 나이 대운수 적용)
                    - 올해 월별 운세 데이터: {yearly_data}

                    [Analysis Protocol (Step-by-Step Thinking)]
                    **STEP 1. 정밀 명식 분석**
                    - 일간(본원)의 강약과 특성을 파악하고, 월지(계절)와의 관계를 통해 조후를 분석한다.
                    - 오행의 과다, 고립, 결핍을 찾아내어 기질적 장단점을 진단한다.
                    - 합(合), 충(沖), 형(刑), 해(害), 파(破)의 작용을 원국 내에서 분석한다.

                    **STEP 2. 구조 및 물상(Imagery) 분석**
                    - 사주를 자연의 물상(예: 겨울의 태양, 가을의 거목 등)으로 비유하여 설명한다.
                    - 격국(사회적 활동성)을 정의하고, 이를 통해 직업적 적성을 도출한다.

                    **STEP 3. 통합 용신 도출 (Synthesis)**
                    - 억부용신(균형), 조후용신(기후), 병약용신(치료), 통관용신(소통)을 종합하여 최적의 용신(희신)과 기신(흉신)을 확정한다.

                    **STEP 4. 신살(神殺) 정밀 분석 (균형 잡힌 시각)**
                    - 귀인(천을, 천덕 등)과 흉살(양인, 백호, 도화 등)의 작용력을 분석하되, 현대적 관점에서 재해석한다.

                    **STEP 5. 대운 및 세운 통변 (Prediction)**
                    - 현재 대운의 특징과 흐름을 분석한다.
                    - 올해(세운)와 원국/대운의 상호작용을 통해 발생 가능한 구체적 사건(재물, 승진, 이별, 건강 등)을 예측한다.
                    - **과거 검증(필수):** 지나온 대운의 특징을 언급하며 상담 신뢰도를 높인다.

                    **STEP 6. 마스터 솔루션 (Advice)**
                    - 용신을 활용한 개운법(방위, 색상, 숫자, 습관)을 제시한다.
                    - 구체적인 행동 강령과 전략을 제안한다.

                    [Output Style - Report & Script]
                    **1. 정밀 분석 보고서 (전문가용):**
                       - 전문 용어는 한자를 병기하되, 논리적으로 서술할 것.
                       - 억지스러운 악담이나 빈말은 배제하고, 냉철한 팩트와 따뜻한 솔루션의 균형 유지.
                    
                    **2. 상담자용 실전 리딩 스크립트 (구어체 대본):**
                       - **반드시 포함할 것.** 상담자가 내담자에게 화면을 보며 바로 읽어줄 수 있도록 "선생님, 지금 운세는..." 형태로 작성.
                       - 과거 적중 질문 포함: "00세~00세 대운 때는 ~~한 어려움이 있었을 텐데 실제로 어떠셨습니까?"

                    - 분량: 전체 A4 3장 이상의 깊이 있는 내용.
                    """

                # ==========================================================
                # [MODE 2] 2026년 병오년 총운 (DB 길일/흉일 포함)
                # ==========================================================
                elif st.session_state['analysis_mode'] == "2026_fortune":
                    # 1. 월별 운세 DB 가져오기
                    yearly_flow = get_yearly_detailed_flow(2026)
                    
                    # 2. 길일/흉일 DB 직접 추출
                    day_stem = result['사주'][2][0]
                    day_branch = result['사주'][2][1]
                    good_days, bad_days = find_best_worst_days_2026(day_stem, day_branch)
                    
                    good_days_str = ", ".join(good_days) if good_days else "특이사항 없음"
                    bad_days_str = ", ".join(bad_days) if bad_days else "특이사항 없음"

                    system_instruction = f"""
                    [Role Definition]
                    당신은 40년 경력의 명리학 마스터입니다. 이번 분석의 핵심은 **2026년 병오년(丙午年)**의 운세를 DB 데이터를 기반으로 정밀 해부하는 것입니다.

                    [Input Data]
                    - 내담자: {name} ({gender}, {current_age}세)
                    - 사주 명식: {result['사주']}
                    - 2026년 월별 흐름(DB): {yearly_flow}
                    - **★ [시스템 추출] 2026년 최고의 날(길일):** {good_days_str}
                    - **★ [시스템 추출] 2026년 주의할 날(흉일):** {bad_days_str}

                    [Task 1: 2026년 병오년 정밀 운세 보고서]
                    다음 항목별로 **등급(상/중/하)**을 매기고, 월별 흐름과 결합하여 구체적 전략을 제시하시오.
                    
                    1. **💰 재물/금전운:** 투자 타이밍, 손실 주의보, 현금 흐름 예측.
                    2. **🏢 사업/직장운:** 승진, 이직, 창업 적기, 관재구설 가능성.
                    3. **❤️ 부부/연애운:** 이별수, 새로운 인연, 가정 불화 및 화합.
                    4. **💊 건강운:** 주의해야 할 신체 부위 및 취약한 달(Month).
                    5. **📅 월별 상세 전략:** 1월부터 12월까지, 제공된 DB 월운 데이터를 바탕으로 월별 길흉을 분석.
                    6. **📅 길일/흉일 활용 가이드:** 위 [시스템 추출] 날짜를 구체적으로 언급하며, "이 날은 계약하세요", "이 날은 운전을 피하세요" 등 행동 지침 제시.

                    [Task 2: 상담자용 2026년 실전 브리핑 대본]
                    **※ 상담자가 내담자에게 2026년 운세를 브리핑하는 구어체 대본.**
                    - "내년 병오년은 선생님께 ~~한 해가 될 것으로 보입니다."
                    - "특히 재물운은 ~~월이 가장 좋으니 이때를 노리시고..."
                    - "달력에 꼭 표시해 두세요. {good_days_str} 날짜들은 귀인이 돕는 날입니다."
                    
                    [Output Format]
                    ---
                    ## 1. 2026년 병오년 정밀 운세 보고서
                    (상세 내용)
                    ## 2. 상담자용 2026년 브리핑 스크립트 (읽어주세요)
                    (대화체 대본)
                    ---
                    """

                with st.spinner("마스터가 데이터를 분석하고 보고서를 작성 중입니다..."):
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
                
                # 수동 입력(버튼) 처리
                prompt = None
                if st.session_state['chat_input_manual']:
                    prompt = st.session_state['chat_input_manual']
                    st.session_state['chat_input_manual'] = None
                elif u_in := st.chat_input("추가 질문 (예: 26년 5월 5일에 이사해도 될까요?)"):
                    prompt = u_in
                
                if prompt:
                    st.session_state['chat_history'].append({"role": "user", "content": prompt})
                    with st.chat_message("user"): st.write(prompt)
                    
                    # 1. 타인 사주 조회 (기능 유지)
                    target_info = extract_and_analyze_target(prompt)
                    
                    # 2. 날짜 DB 매핑 (기능 유지)
                    query_ganji = get_db_ganji_for_query(prompt)
                    
                    # 3. 프롬프트 구성
                    chat_ctx = f"{st.session_state['lifetime_script']}\n\n[이전 대화]\n"
                    for m in st.session_state['chat_history'][:-1]:
                        chat_ctx += f"{m['role']}: {m['content']}\n"
                    
                    if target_info: chat_ctx += target_info
                    chat_ctx += f"\n{query_ganji}\n"
                    
                    chat_ctx += f"\n[현재 질문] {prompt}\n"
                    chat_ctx += """
                    [지침]
                    1. 반드시 위에서 제공된 '[DB 만세력 데이터]'를 기준으로 분석하시오.
                    2. 답변은 상담자가 내담자에게 말하듯 따뜻하고 구체적인 '상담자 톤'으로 하시오.
                    """
                    
                    with st.spinner("답변 생성 중..."):
                        try:
                            r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": chat_ctx}]}]})
                            ai_msg = r.json()['candidates'][0]['content']['parts'][0]['text']
                            st.session_state['chat_history'].append({"role": "assistant", "content": ai_msg})
                            with st.chat_message("assistant"): st.write(ai_msg)
                            st.rerun()
                        except: st.error("응답 생성 실패")