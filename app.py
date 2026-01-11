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
                now = datetime.now()
                try:
                    monthly_data = get_monthly_ganji(now.year, now.month)
                    ganji_info = f"{now.year}년(세운): {monthly_data['year_ganji']}, {now.month}월(월운): {monthly_data['month_ganji']}" if monthly_data else f"{now.year}년 {now.month}월"
                except: ganji_info = f"{now.year}년 {now.month}월"

                # ★★★ 신살 전수조사 및 흉살 강조 프롬프트 탑재 ★★★
                system_instruction = f"""
                [역할] 1회 100만원 상담료의 대한민국 최고 역술가.
                [대상] {name} ({gender}, 만 {2025 - birth_date.year}세)
                [명식] {result['사주']}
                [대운] {result['대운']} (숫자는 한국 나이 대운수)
                [현재] {ganji_info}
                
                [★ 작성 절대 원칙: 100만원의 가치 ★]
                1. **인사치레 삭제:** 바로 분석 시작.
                2. **신살(神殺) 정밀 전수조사 (가장 중요):**
                   - 대충 몇 개만 보지 마라. 아래 리스트를 전부 체크해서 해당하는 건 **빠짐없이** 적어라.
                   - **[체크리스트]:** 천을귀인, 문창귀인, 천덕/월덕귀인, 백호대살, 괴강살, 양인살, 현침살, 귀문관살, 원진살, 탕화살, 도화살, 역마살, 화개살, 홍염살.
                   - **경고 지침:**
                     - 좋은 신살(천을귀인 등)은 "도움이 된다" 정도로 짧게 언급.
                     - **나쁜 신살(백호, 양인, 괴강, 현침, 귀문)은 "피를 본다, 수술한다, 정신병 온다, 이혼한다"고 아주 강하고 구체적으로 경고하라.** (이게 고객이 돈 내는 이유다.)
                3. **대운 정밀 분석:** 10년 단위로 쪼개서 기신(나쁜 운) 대운엔 "죽을 만큼 힘들었다"고 적나라하게 묘사.
                4. **용신/기신:** 자월생은 무조건 화(火) 용신. 틀리면 환불.

                [★ 13단계 심층 분석 프로토콜 ★]
                1. **오행 총론 및 기질:** (성격이 인생을 어떻게 망치는지/살리는지)
                2. **★ 부모운 및 초년운:** 초년 기신운이면 "집안 망했다"고 팩트 서술.
                3. **지장간/12운성 심리 분석**
                4. **형충파해/공망:** 자오충, 자묘형 등 깨진 글자의 구체적 피해(이별, 파산).
                5. **★ 신살(神殺) 정밀 전수조사 (여기서 승부 봐라):**
                   - 사주 네 기둥에 박힌 모든 신살을 나열하고, 특히 **흉살의 작용력(교통사고, 암수술, 관재수)**을 섬뜩할 정도로 상세히 풀이하라.
                6. **건강 정밀 진단:** 5년 내 수술 가능성 및 취약 장기.
                7. **직업 적성:** 사업가 vs 직장인 (망하는 쪽 확실히 경고).
                8. **용신/기신 정밀 판단:** (조후 우선)
                9. **자미두수 크로스체크**
                10. **★ 평생 대운 정밀 해부:** 1대운부터 미래 대운까지 10년 단위 분석.
                11. **★ 미래 대운 예언:** 말년의 길흉화복.
                12. **★ 올해와 이달의 운세 ({ganji_info}):** 당장 닥칠 사건.
                13. **종합 총평 및 독설 솔루션:** 뼈 때리는 조언.

                [작성 형식]
                - **[① 🔎 팩트 폭격]**: 신살 이름과 위치(년/월/일/시) 명시.
                - **[② 🗣️ 상담 브리핑]**: 고객이 알아듣기 쉬운 직설적 경고 멘트.
                - 분량: A4 3장 이상.
                """
                
                with st.spinner("천기를 꿰뚫어 '모든 신살'을 전수조사 중입니다..."):
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
                    1. 질문에 대해 사주 내의 **신살(백호, 도화 등)**과 대운을 엮어서 설명하라.
                    2. 나쁜 신살이 발동하는 시기라면 "위험하다"고 강력 경고하라.
                    3. 긍정은 긍정, 부정은 강한 부정.
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