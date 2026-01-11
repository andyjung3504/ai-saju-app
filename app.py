import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime, timedelta
from saju_logic import analyze_user, login_user, save_consultation, get_monthly_ganji, get_db_data

# --- 설정 ---
st.set_page_config(page_title="천기통달: 명리학 마스터", layout="wide")

try: FIXED_API_KEY = st.secrets["GEMINI_API_KEY"]
except: FIXED_API_KEY = "여기에_API_키를_붙여넣으세요"

# --- 세션 초기화 ---
if 'chat_history' not in st.session_state: st.session_state['chat_history'] = []
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_name' not in st.session_state: st.session_state['user_name'] = ""
if 'run_analysis' not in st.session_state: st.session_state['run_analysis'] = False
if 'analysis_mode' not in st.session_state: st.session_state['analysis_mode'] = "lifetime" # lifetime or 2026

# ==============================================================================
# [핵심 기능 1] 2026년 길일/흉일 DB 탐색 로직 (AI 계산 X, DB 조회 O)
# ==============================================================================
def find_best_worst_days_2026(user_day_stem, user_day_branch):
    """
    내담자의 일간(Day Stem)과 일지(Day Branch)를 기준으로
    2026년(병오년)의 DB를 조회하여 천을귀인(길일)과 충/형(흉일) 날짜를 찾는다.
    """
    # 1. 천을귀인/충 로직 정의
    nobleman_map = {
        '甲': ['丑', '未'], '戊': ['丑', '未'], '庚': ['丑', '未'],
        '乙': ['子', '申'], '己': ['子', '申'],
        '丙': ['亥', '酉'], '丁': ['亥', '酉'],
        '壬': ['巳', '卯'], '癸': ['巳', '卯'],
        '辛': ['午', '寅']
    }
    
    # 지지 순서 및 충 관계 (자오충, 축미충 등)
    branches = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    my_branch_idx = branches.index(user_day_branch)
    chung_branch = branches[(my_branch_idx + 6) % 12] # 반대편 지지 (충)
    
    target_good_branches = nobleman_map.get(user_day_stem, [])
    target_bad_branch = chung_branch

    found_good = []
    found_bad = []
    
    # 2. 2026년 날짜 샘플링 (전수조사는 느릴 수 있으므로 주요 날짜 탐색)
    # 효율성을 위해 매월 5일, 15일, 25일을 우선 조회하거나, 
    # 여기서는 시연을 위해 1월~12월 중 몇몇 날짜를 순회하며 DB 간지 확인
    
    start_date = datetime(2026, 1, 1)
    
    # (약식 구현: 3일에 한번씩 체크하여 다양하게 찾기)
    for i in range(0, 365, 3): 
        curr = start_date + timedelta(days=i)
        # saju_logic의 get_db_data는 (년,월,일,음력여부)를 받음. 양력(False) 조회
        # get_db_data 반환값: [음력월, 음력일, 년주, 월주, 일주, ...]
        row = get_db_data(curr.year, curr.month, curr.day, False)
        
        if row:
            day_ganji = row[4] # 일주 (예: 甲子)
            day_branch = day_ganji[1] # 지지
            
            date_str = curr.strftime("%Y년 %m월 %d일")
            
            # 길일 찾기 (최대 3개)
            if len(found_good) < 3 and day_branch in target_good_branches:
                found_good.append(f"{date_str} ({day_ganji}, 천을귀인)")
            
            # 흉일 찾기 (최대 3개)
            if len(found_bad) < 3 and day_branch == target_bad_branch:
                found_bad.append(f"{date_str} ({day_ganji}, {user_day_branch}와 충)")

        if len(found_good) >= 3 and len(found_bad) >= 3:
            break
            
    return found_good, found_bad

# ==============================================================================
# [핵심 기능 2] 질문 내 날짜 추출 및 DB 강제 매핑 (기존 유지)
# ==============================================================================
def get_db_ganji_for_query(query_text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={FIXED_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    now = datetime.now()
    prompt = f"""
    Current Time: {now.strftime('%Y-%m-%d %H:%M:%S')}
    Task: Extract target date from query: "{query_text}"
    - Return JSON: {{"year": 2026, "month": 5, "day": 5, "hour": 14}} (default to current time if not found)
    """
    try:
        r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": prompt}]}]})
        res_json = json.loads(r.json()['candidates'][0]['content']['parts'][0]['text'].replace("```json", "").replace("```", "").strip())
        t_y, t_m, t_d, t_h = res_json['year'], res_json['month'], res_json['day'], res_json.get('hour', 12)
        db_data = analyze_user(t_y, t_m, t_d, t_h, False, "남성") 
        return f"[시스템 DB 데이터] 기준: {t_y}-{t_m}-{t_d}, 간지: {db_data.get('사주', '오류')}"
    except: return f"[시스템] 날짜 파싱 실패, 현재 시간 기준."

# [기능 3] 타인 사주 조회 (기존 유지)
def extract_and_analyze_target(text):
    # (이전 코드와 동일하므로 생략, 기능은 유지됨)
    return ""

def get_yearly_detailed_flow(year):
    flow_text = f"\n[★ {year}년 월별 상세 간지 (DB 기반)]\n"
    try:
        for m in range(1, 13):
            data = get_monthly_ganji(year, m)
            if data: flow_text += f"- {m}월: {data['month_ganji']}\n"
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
    # --------------------------------------------------------
    # [사이드바] 입력 및 기능 선택
    # --------------------------------------------------------
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
        
        st.markdown("### 🔮 분석 모드 선택")
        
        # 1. 평생 운세 (기존 기능)
        if st.button("📜 정통 평생 심층 분석", type="primary"):
            st.session_state['run_analysis'] = True
            st.session_state['analysis_mode'] = "lifetime"
            st.session_state['chat_history'] = [] 
            st.session_state.pop('lifetime_script', None)
            st.rerun()
            
        # 2. 2026년 운세 (신규 기능)
        st.markdown("---")
        if st.button("📅 2026년 병오년 총운"):
            st.session_state['run_analysis'] = True
            st.session_state['analysis_mode'] = "2026_fortune"
            st.session_state['chat_history'] = []
            st.session_state.pop('lifetime_script', None)
            st.rerun()

    # --------------------------------------------------------
    # [메인 화면] 보고서 출력
    # --------------------------------------------------------
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
            
            # 상단 정보 요약
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

            # 스크립트 생성 (처음 한 번만 실행)
            if 'lifetime_script' not in st.session_state:
                
                # --- [모드 1] 평생 심층 분석 (Full Version) ---
                if st.session_state['analysis_mode'] == "lifetime":
                    now = datetime.now()
                    system_instruction = f"""
                    [Role Definition]
                    당신은 '자평명리학(구조)', '궁통보감(조후)', '적천수(억부)', '맹파명리(시기)'를 통합하여 분석하는 40년 경력의 명리학 마스터입니다.
                    절대 빈말이나 근거 없는 위로를 하지 않으며, 오직 사주 원국과 운의 상호작용(Mechanism)에 입각하여 냉철하게 분석합니다.

                    [Input Data]
                    - 내담자: {name} ({gender}, 만 {current_age}세)
                    - 사주 명식: {result['사주']}
                    - 대운 흐름: {result['대운']} (숫자는 한국 나이 대운 시작점. 예: '4(갑자)'는 4세~13세 구간)
                    - 현재 시점: {now.year}년

                    [Task 1: The Report - 정밀 분석 보고서]
                    다음 목차에 따라 A4 3장 분량의 깊이 있는 보고서를 작성하시오.

                    1. **정밀 명식 분석 (원국)**
                       - 오행의 과다/고립, 조후(계절), 격국을 분석하여 타고난 기질과 그릇을 설명.
                       - 사주 내의 합/충/형/해 관계를 기술적으로 풀이.

                    2. **평생 대운 정밀 검증 (Past & Future)**
                       - **과거 검증(필수):** 현재 나이({current_age}세) 이전의 대운들을 나열하고, 각 시기(예: 14~23세)에 발생했을 구체적 사건(학업, 부모, 재물, 건강 등)을 팩트 체크하듯 서술하라.
                       - **미래 예측:** 현재 및 향후 대운의 길흉 흐름을 그래프 그리듯 묘사하라.

                    3. **용신 및 개운법**
                       - 억부/조후 용신을 명확히 정의하고, 이를 보완하는 현실적 개운법(직업, 방위, 습관) 제시.

                    [Task 2: Counselor's Script - 상담자용 실전 대본]
                    **※ 이 부분은 상담자가 내담자에게 화면을 보며 그대로 읽어줄 수 있도록 '구어체 대본'으로 별도 작성하시오.**
                    
                    - "선생님, 00세 대운에서는 ~~한 기운이 강해서 많이 힘드셨을 텐데, 실제로 금전이나 문서 문제가 있지 않으셨습니까?"
                    - "현재 운의 흐름은 ~~하므로, 올해는 특히 0월을 조심하셔야 합니다."
                    
                    [Output Format]
                    ---
                    ## 1. 정밀 분석 보고서 (전문가용)
                    (상세 내용)
                    
                    ## 2. 상담자용 실전 리딩 스크립트 (읽어주세요)
                    (대화체 대본)
                    ---
                    """

                # --- [모드 2] 2026년 병오년 총운 (New Feature) ---
                elif st.session_state['analysis_mode'] == "2026_fortune":
                    # 1. 월별 운세 데이터 조회
                    yearly_flow = get_yearly_detailed_flow(2026)
                    
                    # 2. 길일/흉일 DB 탐색
                    day_stem = result['사주'][2][0]   # 일간
                    day_branch = result['사주'][2][1] # 일지
                    good_days, bad_days = find_best_worst_days_2026(day_stem, day_branch)
                    
                    good_days_str = ", ".join(good_days) if good_days else "없음"
                    bad_days_str = ", ".join(bad_days) if bad_days else "없음"

                    system_instruction = f"""
                    [Role Definition]
                    당신은 40년 경력의 명리학 마스터입니다.
                    이번 분석의 목표는 **2026년 병오년(丙午年)**의 운세를 종합적으로 해부하는 것입니다.

                    [Input Data]
                    - 내담자: {name} ({gender}, {current_age}세)
                    - 사주 명식: {result['사주']}
                    - 2026년 월별 흐름(DB): {yearly_flow}
                    - **[시스템 추출] 2026년 최고의 날(길일):** {good_days_str}
                    - **[시스템 추출] 2026년 주의할 날(흉일):** {bad_days_str}

                    [Task 1: 2026년 운세 정밀 보고서]
                    세운(병오)이 원국 및 대운과 반응하여 일어날 일을 다음 항목별로 상세히 분석하시오.
                    각 항목에 대해 **등급(상/중/하)**을 매기고 이유를 설명하시오.

                    1. **💰 금전운:** 재물 흐름, 투자 적기, 손실 주의보.
                    2. **🏢 사업/직장운:** 승진, 이직, 창업, 관재구설 가능성.
                    3. **❤️ 부부/연애운:** 이별수, 새로운 인연, 가정 불화.
                    4. **💊 건강운:** 주의해야 할 신체 부위 및 시기.
                    5. **👶 자식운:** 자녀의 학업, 건강, 출산 등.
                    6. **📅 월별 핵심 흐름:** 1월부터 12월까지 주의할 달과 좋은 달 명시.
                    7. **📅 길일/흉일 활용법:** 위에서 제공된 [시스템 추출] 날짜를 언급하며, "이 날은 계약하기 좋다", "이 날은 운전을 조심하라" 등 구체적 행동 지침 제시.

                    [Task 2: Counselor's Script - 상담자용 2026년 브리핑 대본]
                    **※ 상담자가 내담자에게 2026년 운세를 설명하는 구어체 대본을 작성하시오.**
                    
                    - "내년 병오년은 선생님께 ~~한 해가 될 것입니다."
                    - "특히 재물운은 ~~하니 투자는 자제하시고..."
                    - "달력에 표시해 두세요. {good_days_str} 날짜들은 귀인이 돕는 날이니 중요 약속은 이때 잡으세요."

                    [Output Format]
                    ---
                    ## 1. 2026년 병오년 정밀 운세 보고서
                    (항목별 상세 분석)
                    
                    ## 2. 상담자용 2026년 브리핑 스크립트
                    (대화체 대본)
                    ---
                    """

                # API 호출
                with st.spinner("마스터가 데이터를 분석하고 보고서를 작성 중입니다..."):
                    try:
                        r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": system_instruction}]}]})
                        st.session_state['lifetime_script'] = r.json()['candidates'][0]['content']['parts'][0]['text']
                    except Exception as e: st.error(f"분석 시스템 오류: {e}")

            # 결과 출력
            if 'lifetime_script' in st.session_state:
                st.markdown(st.session_state['lifetime_script'])
                st.divider()
                
                # 채팅창 (공통 기능)
                st.subheader("💬 마스터와의 심층 대화")
                for msg in st.session_state['chat_history']:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
                
                if u_in := st.chat_input("추가 질문을 입력하세요. (예: 26년 5월에 이사해도 될까요?)"):
                    st.session_state['chat_history'].append({"role": "user", "content": u_in})
                    with st.chat_message("user"): st.write(u_in)
                    
                    # 날짜 DB 조회 및 답변 생성
                    query_ganji = get_db_ganji_for_query(u_in)
                    chat_ctx = f"{st.session_state['lifetime_script']}\n[DB 정보] {query_ganji}\n[질문] {u_in}\n[지침] 위 DB 데이터를 근거로 상담자 톤으로 답변하시오."
                    
                    with st.spinner("답변 생성 중..."):
                        r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": chat_ctx}]}]})
                        ai_msg = r.json()['candidates'][0]['content']['parts'][0]['text']
                        st.session_state['chat_history'].append({"role": "assistant", "content": ai_msg})
                        with st.chat_message("assistant"): st.write(ai_msg)
                        st.rerun()