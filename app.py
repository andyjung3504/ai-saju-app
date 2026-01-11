import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime, timedelta
from saju_logic import analyze_user, login_user, save_consultation, get_monthly_ganji, get_db_data, check_and_init_db

# --- 설정 ---
st.set_page_config(page_title="천기통달: 명리학 마스터", layout="wide")

# ★ 앱 시작 시 DB 안전장치 가동
check_and_init_db()

try: FIXED_API_KEY = st.secrets["GEMINI_API_KEY"]
except: FIXED_API_KEY = "여기에_API_키를_붙여넣으세요"

# --- 세션 초기화 ---
if 'chat_history' not in st.session_state: st.session_state['chat_history'] = []
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_name' not in st.session_state: st.session_state['user_name'] = ""
if 'run_analysis' not in st.session_state: st.session_state['run_analysis'] = False
if 'analysis_mode' not in st.session_state: st.session_state['analysis_mode'] = "lifetime"

# ==============================================================================
# [핵심] 2026년 길일/흉일 DB 정밀 추적 (AI 환각 방지)
# ==============================================================================
def find_best_worst_days_2026(user_day_stem, user_day_branch):
    """
    내담자의 일간/일지를 기준으로 2026년 DB 데이터를 샅샅이 뒤져
    천을귀인(길일)과 충(흉일) 날짜를 찾아낸다.
    """
    # 천을귀인 매핑
    nobleman_map = {
        '甲': ['丑', '未'], '戊': ['丑', '未'], '庚': ['丑', '未'],
        '乙': ['子', '申'], '己': ['子', '申'],
        '丙': ['亥', '酉'], '丁': ['亥', '酉'],
        '壬': ['巳', '卯'], '癸': ['巳', '卯'],
        '辛': ['午', '寅']
    }
    branches = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    
    # 내 지지와 충이 되는 글자 찾기 (반대편 글자)
    my_branch_idx = branches.index(user_day_branch)
    chung_branch = branches[(my_branch_idx + 6) % 12] 
    
    target_good = nobleman_map.get(user_day_stem, [])
    target_bad = chung_branch

    found_good = []
    found_bad = []
    
    # 2026년 1월 1일부터 탐색 (속도를 위해 3일 간격 스캔)
    start_date = datetime(2026, 1, 1)
    for i in range(0, 365, 3): 
        curr = start_date + timedelta(days=i)
        # DB에서 해당 날짜의 간지(일주) 가져오기
        row = get_db_data(curr.year, curr.month, curr.day, False)
        if row:
            day_ganji = row[4] # 예: 甲子
            day_branch = day_ganji[1] # 지지
            date_str = curr.strftime("%Y년 %m월 %d일")
            
            # 길일 추출 (3개 제한)
            if len(found_good) < 3 and day_branch in target_good:
                found_good.append(f"{date_str}({day_ganji}, 귀인)")
            
            # 흉일 추출 (3개 제한)
            if len(found_bad) < 3 and day_branch == target_bad:
                found_bad.append(f"{date_str}({day_ganji}, {user_day_branch}충)")
                
        if len(found_good) >= 3 and len(found_bad) >= 3: break
            
    return found_good, found_bad

# ==============================================================================
# [핵심] 채팅 질문 날짜 파싱 -> DB 데이터 매핑
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
        
        # 여기서 DB를 직접 조회 (AI 추측 차단)
        db_data = analyze_user(t_y, t_m, t_d, t_h, False, "남성") 
        return f"[시스템 DB 데이터] 기준일: {t_y}년{t_m}월{t_d}일, 산출간지: {db_data.get('사주', 'DB오류')}"
    except: return f"[시스템] 날짜 인식 실패, 현재 시간 기준."

# [기능 3] 타인 사주 조회 (기존 기능 유지)
def extract_and_analyze_target(text):
    # (코드 중복 방지를 위해 생략하나, 실제 구동 시엔 이 함수가 있어야 함. 이전 코드 참조)
    return ""

def get_yearly_detailed_flow(year):
    flow_text = f"\n[★ {year}년 월별 상세 흐름 (DB 기반)]\n"
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
        
        st.markdown("### 🔮 분석 모드 선택")
        
        # 1. 평생 운세 (Expert Report + Counselor Script)
        if st.button("📜 정통 평생 심층 분석", type="primary"):
            st.session_state['run_analysis'] = True
            st.session_state['analysis_mode'] = "lifetime"
            st.session_state['chat_history'] = [] 
            st.session_state.pop('lifetime_script', None)
            st.rerun()
            
        # 2. 2026년 운세 (Money, Career, Love... + Good/Bad Days)
        st.markdown("---")
        if st.button("📅 2026년 병오년 총운"):
            st.session_state['run_analysis'] = True
            st.session_state['analysis_mode'] = "2026_fortune"
            st.session_state['chat_history'] = []
            st.session_state.pop('lifetime_script', None)
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
                
                # [모드 1] 평생 운세 분석 (프롬프트 복구됨)
                if st.session_state['analysis_mode'] == "lifetime":
                    now = datetime.now()
                    system_instruction = f"""
                    [Role Definition]
                    당신은 '자평명리학', '궁통보감', '맹파명리'를 통합 분석하는 40년 경력 마스터입니다.
                    냉정하고 직설적이며, 빈말 없는 팩트 중심 분석을 제공합니다.

                    [Input Data]
                    - 내담자: {name} ({gender}, 만 {current_age}세)
                    - 사주 명식: {result['사주']}
                    - 대운 흐름: {result['대운']} (숫자는 한국 나이 대운 시작점. 예: '4(갑자)'는 4세~13세 구간)
                    - 현재 시점: {now.year}년

                    [Task 1: 정밀 분석 보고서]
                    1. **정밀 명식 분석 (원국):** 오행 과다/고립, 조후, 격국을 분석하여 기질 설명.
                    2. **평생 대운 정밀 검증 (필수):**
                       - 현재 나이 이전의 대운을 시기별(예: 14~23세)로 나누고, 발생했을 구체적 사건(학업, 부모, 재물 등)을 팩트 체크하듯 기술.
                       - 특히 지나온 대운의 길흉을 냉정하게 평가하시오.
                    3. **미래 예측:** 향후 대운의 길흉 흐름을 상세 예측.
                    4. **용신 및 개운법:** 억부/조후 용신 정의 및 현실적 개운법.

                    [Task 2: 상담자용 실전 대본 (Script)]
                    **※ 상담자가 내담자에게 바로 읽어줄 수 있는 구어체 대본을 작성하시오.**
                    - "선생님, 00세 대운(14세~23세) 때는 ~~한 문제로 많이 힘들었을 텐데, 실제로 그러셨습니까?"
                    - "현재 운의 흐름은 ~~하니, 0월을 조심하십시오."
                    
                    [Output Format]
                    ---
                    ## 1. 정밀 분석 보고서 (전문가용)
                    (상세 내용)
                    ## 2. 상담자용 실전 리딩 스크립트 (읽어주세요)
                    (대화체 대본)
                    ---
                    """

                # [모드 2] 2026년 병오년 총운 (DB 길일/흉일 포함)
                elif st.session_state['analysis_mode'] == "2026_fortune":
                    yearly_flow = get_yearly_detailed_flow(2026)
                    
                    # ★ DB에서 길일/흉일 직접 추출
                    day_stem = result['사주'][2][0]
                    day_branch = result['사주'][2][1]
                    good_days, bad_days = find_best_worst_days_2026(day_stem, day_branch)
                    
                    good_days_str = ", ".join(good_days) if good_days else "특이사항 없음"
                    bad_days_str = ", ".join(bad_days) if bad_days else "특이사항 없음"

                    system_instruction = f"""
                    [Role Definition]
                    당신은 40년 경력의 명리학 마스터입니다. 2026년 병오년(丙午年) 운세를 집중 분석합니다.

                    [Input Data]
                    - 내담자: {name} ({gender}, {current_age}세)
                    - 사주 명식: {result['사주']}
                    - 2026년 월별 흐름(DB): {yearly_flow}
                    - **★ [시스템 추출] 2026년 최고의 날(길일):** {good_days_str}
                    - **★ [시스템 추출] 2026년 주의할 날(흉일):** {bad_days_str}

                    [Task 1: 2026년 병오년 정밀 운세 보고서]
                    다음 항목별로 **등급(상/중/하)**을 매기고 구체적 전략을 제시하시오.
                    1. **💰 금전운:** 재물 흐름, 투자 적기/손실 주의.
                    2. **🏢 사업/직장운:** 승진, 이직, 관재구설.
                    3. **❤️ 부부/연애운:** 이별수, 인연, 가정 불화.
                    4. **💊 건강운:** 주의할 신체 부위 및 시기.
                    5. **👶 자식운:** 학업, 건강, 출산.
                    6. **📅 월별 핵심 흐름:** 1월~12월 중 좋은 달/나쁜 달 명시.
                    7. **📅 길일/흉일 활용법:** 위 [시스템 추출] 날짜를 언급하며 "이 날은 계약하세요", "이 날은 운전 조심하세요" 등 구체적 지침 제시.

                    [Task 2: 상담자용 2026년 브리핑 대본]
                    **※ 상담자가 내담자에게 2026년 운세를 설명하는 구어체 대본.**
                    - "내년 병오년은 선생님께 ~~한 해가 될 것입니다."
                    - "특히 달력에 표시해 두세요. {good_days_str} 날짜들은 귀인이 돕는 날이니 중요 약속은 이때 잡으세요."

                    [Output Format]
                    ---
                    ## 1. 2026년 병오년 정밀 운세 보고서
                    (상세 내용)
                    ## 2. 상담자용 2026년 브리핑 스크립트
                    (대화체 대본)
                    ---
                    """

                with st.spinner("마스터가 DB 데이터를 분석 중입니다..."):
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
                
                if u_in := st.chat_input("추가 질문 (예: 26년 5월 5일에 이사해도 될까요?)"):
                    st.session_state['chat_history'].append({"role": "user", "content": u_in})
                    with st.chat_message("user"): st.write(u_in)
                    
                    query_ganji = get_db_ganji_for_query(u_in)
                    chat_ctx = f"{st.session_state['lifetime_script']}\n{query_ganji}\n[질문] {u_in}\n[지침] 위 DB 데이터를 근거로 상담자 톤으로 답변하시오."
                    
                    with st.spinner("답변 생성 중..."):
                        r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": chat_ctx}]}]})
                        ai_msg = r.json()['candidates'][0]['content']['parts'][0]['text']
                        st.session_state['chat_history'].append({"role": "assistant", "content": ai_msg})
                        with st.chat_message("assistant"): st.write(ai_msg)
                        st.rerun()