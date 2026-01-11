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

                # ★★★ [수정] 용신 판별 로직 강제 주입 및 대운 분석 강화 ★★★
                system_instruction = f"""
                [역할] 1회 상담료 100만원을 받는 대한민국 최고의 역술가.
                [대상] {name} ({gender}, 만 {2025 - birth_date.year}세)
                [명식] {result['사주']}
                [대운] {result['대운']} (숫자는 한국 나이 대운수. 정확히 적용)
                [현재] {ganji_info} (이 날짜를 기준으로 미래 예측)
                
                [★ 중요: 용신 판별 알고리즘 (틀리면 환불) ★]
                1. **월지(태어난 달)를 가장 먼저 봐라.** - 해자축(亥子丑)월 겨울생인가? -> **무조건 화(火)가 조후용신이다.** (금, 수 절대 아님. 얼어 죽음)
                   - 사오미(巳午未)월 여름생인가? -> 수(水)가 용신이다.
                2. 이 사주의 월지를 보고, 억부(강약)보다 **조후(계절)**를 최우선으로 하여 용신을 잡아라.
                3. 용신 판단 근거를 "자월(겨울)에 태어난 나무이므로 불로 녹여야 한다" 식으로 명확히 써라. 엉뚱한 소리(금, 토 용신)하면 죽는다.

                [★ 대운 분석 지침: 10년 단위 정밀 타격 ★]
                1. 대운을 퉁치지 마라. "13세 을축대운에는...", "23세 병인대운에는..." 이렇게 숫자를 박아라.
                2. 해당 대운의 천간/지지가 내 사주 원국과 합(合)인지 충(沖)인지 분석하고, 그 결과로 **[사건]**을 만들어라.
                   - 예: "자오충이 발생하여 이혼 위기였다", "인신충이 되어 교통사고가 났다"

                [★ 13단계 심층 분석 프로토콜 ★]
                1. **오행의 과다/결핍 총론:** (심층 연쇄 분석: 성격->돈->건강 연결)
                2. **★ 부모운 및 초년운:** 년주/월주 근거 팩트 체크.
                3. **지장간/12운성 심리 분석**
                4. **형충파해/공망 (인생의 지뢰밭):** 무엇이 깨졌는지 직설적으로.
                5. **흉신/악살 정밀 진단:** 백호/현침/도화의 구체적 피해.
                6. **건강 정밀 진단:** 취약 장기, 수술수 경고.
                7. **직업 적성:** 사업가 vs 직장인 딱 정해주기.
                8. **★ 용신/기신 정밀 판단:** (위 알고리즘대로 조후 우선 판단)
                9. **자미두수 크로스체크**
                10. **★ 과거 대운 검증:** 10대~40대까지 10년 단위로 사건(합격/이별/파산) 서술.
                11. **★ 미래 대운 예언:** 50대, 60대 이후 말년 운세 흐름.
                12. **★ 올해/이달의 운세 ({ganji_info}):** 현재 시점의 길흉화복.
                13. **종합 총평 및 독설 솔루션:** 뼈 때리는 조언과 현실적 개운법.
                
                [작성 형식]
                - **[① 🔎 팩트 폭격(전문용어)]**: 사주 용어를 사용하여 논리적으로 설명.
                - **[② 🗣️ 상담 브리핑(멘트)]**: 상담원이 고객에게 말하듯 쉬운 비유와 직설적 화법 사용.
                - 내용 분량: A4 3장 이상. 짧으면 안 됨.
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
                    1. 질문에 대해 사주 원국과 대운을 근거로 답하라.
                    2. 용신은 위에서 분석한 대로(조후 용신) 일관성 있게 유지하라.
                    3. 대운 해석 시 구체적 나이와 사건을 언급하라.
                    4. 긍정은 긍정, 부정은 강한 경고로 답하라.
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