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
# [수정 완료] 기능 1: 2026년 길일/흉일 정밀 산출 (합,충,형,해,공망,귀인 전체 고려)
# ==============================================================================
def find_best_worst_days_2026(user_day_stem, user_day_branch):
    """
    내담자의 일주(Day Pillar)를 기준으로 2026년 365일을 전수 조사하여
    길일(천을귀인, 육합)과 흉일(충, 형, 해, 공망)을 월별로 안배하여 추출한다.
    """
    # 1. 기초 매핑 데이터
    branches = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    
    # 천을귀인 (길신)
    nobleman_map = {
        '甲': ['丑', '未'], '戊': ['丑', '未'], '庚': ['丑', '未'],
        '乙': ['子', '申'], '己': ['子', '申'],
        '丙': ['亥', '酉'], '丁': ['亥', '酉'],
        '壬': ['巳', '卯'], '癸': ['巳', '卯'],
        '辛': ['午', '寅']
    }
    
    # 지지 육합 (길신)
    yuk_hap_map = {
        '子': '丑', '丑': '子', '寅': '亥', '亥': '寅',
        '卯': '戌', '戌': '卯', '辰': '酉', '酉': '辰',
        '巳': '申', '申': '巳', '午': '未', '未': '午'
    }

    # 칠충 (흉신) - 반대편 글자
    my_branch_idx = branches.index(user_day_branch)
    chung_branch = branches[(my_branch_idx + 6) % 12]
    
    # 지지 육해 (흉신)
    yuk_hai_map = {
        '子': '未', '丑': '午', '寅': '巳', '巳': '寅',
        '卯': '辰', '辰': '卯', '申': '亥', '亥': '申',
        '酉': '戌', '戌': '酉', '午': '丑', '未': '子'
    }

    # 삼형살 (흉신) - 약식 (주요 형살만 체크)
    xing_map = {
        '寅': ['巳', '申'], '巳': ['寅', '申'], '申': ['寅', '巳'],
        '丑': ['戌', '未'], '戌': ['丑', '未'], '未': ['丑', '戌'],
        '子': ['卯'], '卯': ['子'],
        '辰': ['辰'], '午': ['午'], '酉': ['酉'], '亥': ['亥'] # 자형
    }

    # 공망 (흉신) 계산
    stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    stem_idx = stems.index(user_day_stem)
    branch_idx = branches.index(user_day_branch)
    # (지지번호 - 천간번호)로 순공(旬空) 찾기
    diff = (branch_idx - stem_idx)
    if diff < 0: diff += 12
    # 순중공망: (diff)값에 따라 공망 글자가 정해짐
    gongmang_table = {
        10: ['戌', '亥'], 8: ['申', '酉'], 6: ['午', '未'],
        4: ['辰', '巳'], 2: ['寅', '卯'], 0: ['子', '丑']
    }
    my_gongmang = gongmang_table.get(diff, [])

    # 2. 2026년 전수 조사
    found_good = []
    found_bad = []
    
    start_date = datetime(2026, 1, 1)
    # 365일 전체 루프 (중단 없음)
    for i in range(365): 
        curr = start_date + timedelta(days=i)
        # DB에서 일진(Day Ganji) 가져오기 (양력)
        row = get_db_data(curr.year, curr.month, curr.day, False)
        
        if row:
            day_ganji = row[4] # 예: 甲子
            day_branch = day_ganji[1] # 지지
            date_str = curr.strftime("%m월 %d일")
            
            # --- 길일 판별 ---
            is_good = False
            reasons_good = []
            
            # 1) 천을귀인
            if day_branch in nobleman_map.get(user_day_stem, []):
                reasons_good.append("천을귀인")
            # 2) 육합
            if yuk_hap_map.get(user_day_branch) == day_branch:
                reasons_good.append("육합(도움)")
                
            if reasons_good:
                found_good.append(f"{date_str}({day_ganji}: {','.join(reasons_good)})")

            # --- 흉일 판별 ---
            is_bad = False
            reasons_bad = []
            
            # 1) 충
            if day_branch == chung_branch:
                reasons_bad.append("충(충돌)")
            # 2) 공망
            if day_branch in my_gongmang:
                reasons_bad.append("공망(빈손)")
            # 3) 해
            if yuk_hai_map.get(user_day_branch) == day_branch:
                reasons_bad.append("육해(방해)")
            # 4) 형
            if day_branch in xing_map.get(user_day_branch, []):
                reasons_bad.append("형살(분쟁)")

            if reasons_bad:
                found_bad.append(f"{date_str}({day_ganji}: {','.join(reasons_bad)})")

    # 3. 결과 필터링 (너무 많으면 월별로 골고루 안배하여 15개 내외만 추출)
    def sample_dates(date_list, count=12):
        if not date_list: return []
        if len(date_list) <= count: return date_list
        step = len(date_list) // count
        return [date_list[i] for i in range(0, len(date_list), step)][:count]

    final_good = sample_dates(found_good, 10)
    final_bad = sample_dates(found_bad, 10)
            
    return final_good, final_bad

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
        
        # [삭제됨] 불필요한 리셋 버튼 제거

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

        st.markdown("---")
        # 일반 분석 버튼은 하단에 배치
        if st.button("📜 정통 평생 심층 분석 (일반)", type="primary"):
            st.session_state['run_analysis'] = True
            st.session_state['analysis_mode'] = "lifetime"
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
                
                # ==========================================================
                # [MODE 1] 평생 심층 분석 (대운 검증 강화)
                # ==========================================================
                if st.session_state['analysis_mode'] == "lifetime":
                    now = datetime.now()
                    yearly_data = get_yearly_detailed_flow(now.year)
                    
                    system_instruction = f"""
                    [Role Definition]
                    당신은 '자평명리학', '궁통보감', '적천수'를 통합 분석하는 40년 경력의 명리학 마스터입니다.
                    추상적인 위로는 배제하고, 냉철한 논리와 팩트로 분석하십시오.

                    [Input Data]
                    - 내담자: {name} ({gender}, 만 {current_age}세)
                    - 사주 명식: {result['사주']}
                    - 대운 흐름: {result['대운']} (숫자는 한국 나이 시작점. 예: '4(갑자)' -> 4세~13세)
                    - 올해 데이터: {yearly_data}

                    [Analysis Protocol]
                    **STEP 1. 정밀 명식 분석**
                    - 오행의 편중, 조후, 격국을 분석하여 내담자의 그릇(기질)을 설명.

                    **STEP 2. ★ 평생 대운 정밀 검증 (Past Verification - 매우 중요)**
                    - **지나온 과거 대운의 나이 구간(예: 14세~23세, 24세~33세)을 정확히 명시할 것.**
                    - 과거 대운의 희기(喜忌)를 판별하여, 해당 시기에 발생했을 **구체적인 사건(학업 성취, 부모 이혼, 큰 재물 취득, 건강 악화, 관재수 등)**을 팩트 체크하듯 상세히 서술할 것.
                    - "지나온 00대운은 ~~한 시기였으므로 ~~한 일이 있었을 것이다"라고 단언할 것. (신뢰 형성의 핵심)

                    **STEP 3. 미래 대운 및 세운 예측**
                    - 현재 대운의 길흉과 향후 흐름을 예측.

                    **STEP 4. 마스터 솔루션**
                    - 용신 개운법 및 인생 전략 제시.

                    [Output Format]
                    ---
                    ## 1. 정밀 분석 보고서 (전문가용)
                    (명리학적 근거를 포함한 상세 분석. **특히 과거 대운 검증 파트를 별도 챕터로 상세히 작성할 것.**)
                    
                    ## 2. 상담자용 실전 리딩 스크립트 (구어체 대본)
                    - "선생님, 00세부터 00세까지(00대운)는 ~~한 운이라 많이 힘드셨을 텐데, 혹시 그때 금전 문제나 이별수가 있지 않으셨습니까?"
                    - "이 사주는 과거 흐름을 보면..."
                    ---
                    """

                # ==========================================================
                # [MODE 2] 2026년 병오년 총운 (합/충/형/해/공망/귀인 완벽 적용)
                # ==========================================================
                elif st.session_state['analysis_mode'] == "2026_fortune":
                    yearly_flow = get_yearly_detailed_flow(2026)
                    day_stem = result['사주'][2][0]
                    day_branch = result['사주'][2][1]
                    # [수정된 함수 호출] 전수조사 후 샘플링된 리스트 반환
                    good_days, bad_days = find_best_worst_days_2026(day_stem, day_branch)
                    
                    good_days_str = ", ".join(good_days) if good_days else "특이사항 없음"
                    bad_days_str = ", ".join(bad_days) if bad_days else "특이사항 없음"

                    system_instruction = f"""
                    [Role Definition]
                    당신은 40년 경력의 명리학 마스터입니다. 2026년 병오년(丙午年) 운세를 정밀 분석합니다.

                    [Input Data]
                    - 내담자: {name} ({gender}, {current_age}세)
                    - 사주 명식: {result['사주']}
                    - 2026년 월별 흐름(DB): {yearly_flow}
                    - **★ [시스템 정밀 산출] 길일(귀인/육합):** {good_days_str}
                    - **★ [시스템 정밀 산출] 흉일(충/형/해/공망):** {bad_days_str}

                    [Task 1: 2026년 병오년 정밀 운세 보고서]
                    다음 항목별로 **등급(상/중/하)**을 매기고, 월별 흐름과 결합하여 전략을 제시하시오.
                    특히 [시스템 정밀 산출] 날짜들을 적극 인용하여 조언하시오.
                    
                    1. **💰 재물/금전운**
                    2. **🏢 사업/직장운**
                    3. **❤️ 부부/연애운**
                    4. **💊 건강운**
                    5. **📅 월별 상세 전략 (1월~12월)**
                    6. **📅 길일/흉일 활용 가이드 (필수 포함)**
                       - "표시된 {good_days_str}은 귀인과 합이 드는 날이니 계약이나 중요 미팅을 잡으세요."
                       - "표시된 {bad_days_str}은 충, 형, 공망일이니 이동을 삼가고 언행을 조심하세요."

                    [Task 2: 상담자용 2026년 브리핑 대본]
                    **※ 상담자가 내담자에게 읽어줄 구어체 대본.**
                    - "내년에는 특히 이 날짜들을 조심하셔야 합니다..."
                    
                    [Output Format]
                    ---
                    ## 1. 2026년 병오년 정밀 운세 보고서
                    (상세 내용)
                    ## 2. 상담자용 2026년 브리핑 스크립트
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
                
                prompt = None
                if st.session_state['chat_input_manual']:
                    prompt = st.session_state['chat_input_manual']
                    st.session_state['chat_input_manual'] = None
                elif u_in := st.chat_input("추가 질문 (예: 26년 5월 5일에 이사해도 될까요?)"):
                    prompt = u_in
                
                if prompt:
                    st.session_state['chat_history'].append({"role": "user", "content": prompt})
                    with st.chat_message("user"): st.write(prompt)
                    
                    target_info = extract_and_analyze_target(prompt)
                    query_ganji = get_db_ganji_for_query(prompt)
                    
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