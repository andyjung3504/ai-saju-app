import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime
from saju_logic import analyze_user, login_user, save_consultation, get_my_consultation_history, check_and_init_db, get_monthly_ganji

# --- 설정 ---
st.set_page_config(page_title="천기통달 VIP 심층 상담", layout="wide")
check_and_init_db()

try: FIXED_API_KEY = st.secrets["GEMINI_API_KEY"]
except: FIXED_API_KEY = "여기에_API_키를_붙여넣으세요"

# --- 세션 초기화 ---
for k in ['chat_history', 'chat_input_manual']:
    if k not in st.session_state: st.session_state[k] = [] if k == 'chat_history' else None
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_name' not in st.session_state: st.session_state['user_name'] = ""
if 'run_analysis' not in st.session_state: st.session_state['run_analysis'] = False

# ==========================================
# 1. 로그인
# ==========================================
if not st.session_state['logged_in']:
    st.title("🔒 천기통달 전문가 로그인")
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

# ==========================================
# 2. 메인 상담
# ==========================================
else:
    with st.sidebar:
        st.info(f"👤 상담원: {st.session_state['user_name']}")
        if st.button("로그아웃"):
            st.session_state['logged_in'] = False
            st.session_state.clear()
            st.rerun()
        st.divider()

        st.header("📝 명조 입력")
        name = st.text_input("고객명", value="홍길동")
        gender = st.radio("성별", ["남성", "여성"], horizontal=True)
        calendar_type = st.radio("달력", ["양력", "음력"], horizontal=True)
        is_lunar = (calendar_type == "음력")
        
        c1, c2 = st.columns(2)
        with c1: birth_date = st.date_input("생년월일", value=pd.to_datetime("1980-01-01"), min_value=pd.to_datetime("1900-01-01"))
        with c2: birth_time = st.time_input("태어난 시간", value=pd.to_datetime("14:30").time())
        
        if st.button("천기통달 심층 분석 (Enter)", type="primary"):
            st.session_state['run_analysis'] = True
            st.session_state['chat_history'] = [] 
            st.session_state.pop('lifetime_script', None)

        st.divider()
        st.markdown("### ⚡ 심층 질문 숏컷")
        keywords = ["💰 재물/사업운 심층분석", "🏠 부동산/매매운", "❤️ 배우자/이성운", "💊 건강/수술수 정밀", "⚖️ 관재구설/소송", "🎓 자녀/진로/학업", "✈️ 이동/이사/해외", "🏢 직장/승진/이직"]
        
        for kw in keywords:
            if st.button(kw):
                st.session_state['chat_input_manual'] = kw + "에 대해 오행의 득실과 십성의 작용을 근거로 아주 상세하게, 인생 전체와 연결지어 분석해줘."
                if not st.session_state['run_analysis']:
                    st.session_state['run_analysis'] = True
                    st.session_state['chat_history'] = []
                st.rerun()

    st.title("🔮 AI 천기통달 VIP 심층 상담 (전문가용)")

    if st.session_state['run_analysis']:
        if not FIXED_API_KEY or len(FIXED_API_KEY) < 10:
            st.error("API 키 오류")
            st.stop()

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={FIXED_API_KEY}"
        headers = {'Content-Type': 'application/json'}

        result = analyze_user(birth_date.year, birth_date.month, birth_date.day, birth_time.hour, is_lunar, gender)
        
        if "error" in result:
            st.error(result["error"])
        else:
            with st.expander("📊 명식 데이터 및 저장", expanded=True):
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    st.info(f"대상: {name} ({gender})")
                    st.write(f"자미: **{result['자미두수']['명궁위치']}** ({result['자미두수']['명궁주성']})")
                with c2:
                    st.write(f"사주: {result['사주']}")
                    st.write(f"대운: {result['대운']}")
                with c3:
                    if st.button("💾 DB 저장"):
                        save_consultation(st.session_state['user_id'], name, gender, birth_date, birth_time, memo="심층 분석")
                        st.toast("저장 완료")

            if 'lifetime_script' not in st.session_state:
                # 현재 날짜 및 월운 DB 조회
                now = datetime.now()
                try:
                    monthly_data = get_monthly_ganji(now.year, now.month)
                    ganji_info = f"{now.year}년(세운): {monthly_data['year_ganji']}, {now.month}월(월운): {monthly_data['month_ganji']}" if monthly_data else f"{now.year}년 {now.month}월"
                except: ganji_info = f"{now.year}년 {now.month}월"

                # ★★★ 내용 부실 방지: 심층 연쇄 분석 프롬프트 ★★★
                system_instruction = f"""
                [역할] 1회 상담료 100만원을 받는 대한민국 최고의 역술가. 빈약한 분석은 용납하지 않는다.
                [대상] {name} ({gender}, 만 {2025 - birth_date.year}세)
                [명식] {result['사주']}
                [대운] {result['대운']} (한국 나이 대운수 적용)
                [현재] {ganji_info}
                
                [★ 작성 절대 원칙: 꼬리에 꼬리를 무는 연쇄 분석 ★]
                1. **단편적 해석 금지:** "목이 많다 -> 고집이 세다"에서 끝내지 마라.
                   -> "목이 많아 고집이 세므로 **사업을 하면 독단적으로 결정하다 사기를 당하고**, **연애에서는 상대를 가르치려다 차이며**, 건강으로는 **간과 신경계통이 망가질 것이다**"라고 **인생 전체로 확장**해라.
                2. **상황별 시뮬레이션:** - "이 사주가 사업을 한다면?"
                   - "이 사주가 직장생활을 한다면?" 
                   - "이 사주가 결혼을 한다면?"
                   구체적인 가정 상황을 두고 결과를 예측하라.
                3. **대운 정밀 대입:** 과거 대운의 사건을 맞추고, 미래 대운의 길흉을 10년 단위로 쪼개서 설명하라.
                4. **형식:** [① 🔎 팩트 폭격(전문용어)]와 [② 🗣️ 상담 브리핑(비유)]로 구분하되, **내용은 무조건 A4 3장 이상**의 깊이여야 한다.

                [★ 13단계 심층 분석 프로토콜 ★]
                1. **오행의 과다/결핍에 따른 인생 총론 (가장 중요)**
                   - 특정 오행이 많거나 없을 때 생기는 **성격적 결함**이 **돈, 사랑, 건강**에 각각 어떤 악영향을 미치는지 상세 서술.
                2. **부모운 및 학창시절 정밀 추리**
                   - 년/월주를 통해 부모의 능력과 유산 여부, 학업 성취도를 냉정하게 판단.
                3. **지장간/12운성으로 본 내면 심리**
                4. **형충파해/공망 (인생의 지뢰밭)**
                   - 깨진 글자가 십성 중 무엇인지 확인하여 (예: 재성이 깨지면 -> 처와 돈이 나감) 구체적 피해 서술.
                5. **흉신/악살의 작용력**
                6. **건강 정밀 진단 (장기 및 질병명 구체화)**
                7. **사회적 성취와 직업 적성 (사업가 vs 직장인)**
                   - 이 사주가 사업하면 망하는지 흥하는지, 어떤 업종이 맞는지 딱 정해줄 것.
                8. **용신/기신과 개운법**
                9. **자미두수 정밀 대조**
                10. **★ 대운 흐름 분석 (과거):** 10대, 20대, 30대, 40대... 각 대운별로 일어났을 법한 구체적 사건(합격, 이별, 파산) 서술.
                11. **★ 대운 흐름 분석 (미래):** 앞으로 다가올 50대, 60대 이후의 삶을 '한 편의 드라마'처럼 예고.
                12. **★ 이달의 운세 ({now.month}월):** {ganji_info}의 글자가 사주와 반응하여 이번 달에 터질 사건 예고.
                13. **종합 총평 및 독설 솔루션**
                """
                
                with st.spinner("천기를 꿰뚫어 인생 전체를 정밀 해부 중입니다... (심층 분석)"):
                    try:
                        r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": system_instruction}]}]})
                        st.session_state['lifetime_script'] = r.json()['candidates'][0]['content']['parts'][0]['text']
                    except Exception as e: st.error(f"오류: {e}")

            if 'lifetime_script' in st.session_state:
                st.markdown(st.session_state['lifetime_script'])
                st.divider()
                
                st.subheader("💬 심층 독설 상담")
                for msg in st.session_state['chat_history']:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
                
                prompt = None
                if st.session_state['chat_input_manual']:
                    prompt = st.session_state['chat_input_manual']
                    st.session_state['chat_input_manual'] = None
                elif u_in := st.chat_input("질문을 입력하세요..."):
                    prompt = u_in
                
                if prompt:
                    st.session_state['chat_history'].append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.write(prompt)
                    
                    chat_ctx = f"{st.session_state['lifetime_script']}\n\n[이전 대화]\n"
                    for m in st.session_state['chat_history'][:-1]:
                        chat_ctx += f"{m['role']}: {m['content']}\n"
                    chat_ctx += f"\n[현재 질문] {prompt}\n"
                    chat_ctx += """
                    [지침]
                    1. 질문에 대해 단편적으로 답하지 말고, 사주 원국의 오행/십성 구조와 대운을 엮어서 **입체적으로 설명**하라.
                    2. "사업운 어때?"라고 물으면 -> "일지에 편재가 있고 역마가 강하니 무역업은 좋으나, 겁재가 강해 동업하면 100% 소송 걸립니다" 식으로 **조건부 시나리오**를 제시하라.
                    3. 내용이 부실하면 상담료 환불이다. 최대한 자세히 적어라.
                    """
                    
                    with st.spinner("심층 분석 중..."):
                        try:
                            r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": chat_ctx}]}]})
                            ai_msg = r.json()['candidates'][0]['content']['parts'][0]['text']
                            st.session_state['chat_history'].append({"role": "assistant", "content": ai_msg})
                            with st.chat_message("assistant"):
                                st.write(ai_msg)
                            st.rerun()
                        except: st.error("답변 실패")