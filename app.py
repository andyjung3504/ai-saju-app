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
                # ★★★ [수정] 날짜 강제 고정 및 DB 조회 ★★★
                now = datetime.now() # 실제 서버 시간 (2025/2026 등)
                
                # DB에서 현재 년/월의 간지를 가져옵니다.
                try:
                    monthly_data = get_monthly_ganji(now.year, now.month)
                    if monthly_data:
                        # 예: 2026년(병오), 1월(경인) -> 이 값을 프롬프트에 강제로 박아넣음
                        current_time_str = f"{now.year}년 {now.month}월 (세운: {monthly_data['year_ganji']}년, 월운: {monthly_data['month_ganji']}월)"
                        current_year_ganji = monthly_data['year_ganji']
                        current_month_ganji = monthly_data['month_ganji']
                    else:
                        current_time_str = f"{now.year}년 {now.month}월 (DB 조회 실패 - 기본값 사용)"
                        current_year_ganji = "확인불가"
                        current_month_ganji = "확인불가"
                except:
                    current_time_str = f"{now.year}년 {now.month}월"
                    current_year_ganji = "확인불가"
                    current_month_ganji = "확인불가"

                # ★★★ 독설 제거 & 논리 강화 & 날짜 고정 프롬프트 ★★★
                system_instruction = f"""
                [역할] 1회 상담료 100만원을 받는 대한민국 최고의 역술가.
                [대상] {name} ({gender}, 만 {2025 - birth_date.year}세)
                [명식] {result['사주']}
                [대운] {result['대운']} (한국 나이 대운수 적용)
                
                [★ 현재 시점 (절대 기준) ★]
                - 지금은 **{current_time_str}** 입니다.
                - 절대 2023년(계묘)이나 2024년(갑진) 이야기를 하지 마십시오.
                - 올해 세운 **[{current_year_ganji}]**와 이달의 월운 **[{current_month_ganji}]** 글자를 사주 원국과 대조하여 분석하십시오.
                
                [★ 작성 원칙: 100만원의 가치 = 논리적 근거 + 명확한 대안 ★]
                1. **추가금 요구 금지:** 상담료 얘기 꺼내지 마라.
                2. **톤 앤 매너:** - **긍정:** 확실하게 좋다, 대박 난다 말해줘라.
                   - **부정:** "죽는다/망한다"고 끝내지 말고, **"A와 B가 충돌하여 위험하니 C를 조심하라"**고 구체적이고 강하게 경고하되 대안을 줘라. (자살 유도 금지)
                3. **심층 연쇄 분석:** 하나의 단서를 돈, 사랑, 건강, 성격으로 확장하여 해석하라.
                4. **과거 디테일:** 부모운, 학업운을 사주 근거로 맞혀라.

                [★ 13단계 심층 분석 프로토콜 ★]
                1. **오행의 과다/결핍 총론:** 성격이 인생 전반(돈, 사랑, 건강)에 미치는 연쇄 작용.
                2. **★ 부모운 및 학창시절:** 년주/월주를 근거로 부모덕과 공부 머리 판단.
                3. **지장간/12운성 심리 분석**
                4. **형충파해/공망 (인생의 지뢰밭):** 무엇이 깨졌는지(재성? 관성?) 팩트 체크.
                5. **흉신/악살 정밀 진단:** 백호, 현침 등이 수술/사고로 이어지는지 확인.
                6. **건강 정밀 진단:** 취약 장기 및 발병 예상 시기.
                7. **직업 적성 (사업 vs 직장):** 사업하면 망하는 사주인지, 동업은 되는지 판결.
                8. **용신/기신과 개운법**
                9. **자미두수 크로스체크**
                10. **★ 과거 대운 검증:** 20대, 30대, 40대 대운별 핵심 사건(이별, 부도 등) 추리.
                11. **★ 미래 대운 예언:** 50대, 60대 이후 말년 운세의 흐름 (10년 단위).
                12. **★ 올해와 이달의 운세 ({current_time_str}):** - 올해 세운({current_year_ganji})이 내 사주에 미치는 영향.
                    - 이번 달 월운({current_month_ganji})이 일으킬 구체적 사건.
                13. **종합 총평 및 현실적 조언:** 뼈 때리는 조언과 희망적 대안 제시.
                """
                
                with st.spinner("천기를 꿰뚫어 인생 전체를 정밀 해부 중입니다... (심층 분석)"):
                    try:
                        r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": system_instruction}]}]})
                        st.session_state['lifetime_script'] = r.json()['candidates'][0]['content']['parts'][0]['text']
                    except Exception as e: st.error(f"오류: {e}")

            if 'lifetime_script' in st.session_state:
                st.markdown(st.session_state['lifetime_script'])
                st.divider()
                
                st.subheader("💬 심층 상담")
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
                    2. "사업운 어때?" -> "일지 편재가 충을 맞아 위험하지만, 대운이 돕고 있으니 소규모는 가능하다" 식으로 **조건부 시나리오** 제시.
                    3. 추가금 요구하지 마라.
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