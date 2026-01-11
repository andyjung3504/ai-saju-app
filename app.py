import streamlit as st
import pandas as pd
import requests
import json
import time
from saju_logic import analyze_user, login_user, save_consultation, get_my_consultation_history, check_and_init_db

# --- 설정 ---
st.set_page_config(page_title="천기통달 VIP 상담 시스템", layout="wide")
check_and_init_db()

try: FIXED_API_KEY = st.secrets["GEMINI_API_KEY"]
except: FIXED_API_KEY = "여기에_API_키를_붙여넣으세요"

# --- 세션 초기화 ---
for key in ['logged_in', 'user_id', 'user_name', 'run_analysis']:
    if key not in st.session_state: st.session_state[key] = None if key != 'logged_in' else False
if 'chat_history' not in st.session_state: st.session_state['chat_history'] = []

# ==========================================
# 1. 로그인
# ==========================================
if not st.session_state['logged_in']:
    st.title("🔒 천기통달 전문가 로그인")
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("아이디", placeholder="예: test1")
            password = st.text_input("비밀번호", type="password", placeholder="예: 1234")
            if st.form_submit_button("로그인", type="primary"):
                user_name = login_user(username, password)
                if user_name:
                    st.session_state['logged_in'] = True
                    st.session_state['user_id'] = username
                    st.session_state['user_name'] = user_name
                    st.rerun()
                else:
                    st.error("로그인 실패")

# ==========================================
# 2. 메인 상담
# ==========================================
else:
    # --- 사이드바 ---
    with st.sidebar:
        st.info(f"👤 상담원: **{st.session_state['user_name']}**")
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
        
        col1, col2 = st.columns(2)
        with col1:
            birth_date = st.date_input("생년월일", value=pd.to_datetime("1980-01-01"), min_value=pd.to_datetime("1900-01-01"), max_value=pd.to_datetime("2100-12-31"))
        with col2:
            birth_time = st.time_input("태어난 시간", value=pd.to_datetime("14:30").time())
        
        if st.button("천기통달 분석 실행 (Enter)", type="primary"):
            st.session_state['run_analysis'] = True
            st.session_state['chat_history'] = [] 
            st.session_state.pop('lifetime_script', None)

        st.divider()
        st.markdown("### ⚡ 상담 숏컷 (클릭)")
        
        keywords = [
            "💰 금전운/재물운", "🏢 사업운/창업운", "🏠 매매운/부동산",
            "❤️ 연애운/부부운", "💊 본인 건강운", "👵 부모님 건강운",
            "💼 직장운/승진운", "🎓 자녀운/합격운", "⚖️ 관재구설/소송",
            "✈️ 이사운/이동운"
        ]
        
        # 키워드 버튼을 누르면 'chat_input_manual'에 값을 저장하고 rerun
        for kw in keywords:
            if st.button(kw):
                st.session_state['chat_input_manual'] = kw + "에 대해 냉정하게, 위험 요소 위주로 분석해줘."
                if not st.session_state['run_analysis']:
                    st.session_state['run_analysis'] = True
                    st.session_state['chat_history'] = []

    # --- 메인 컨텐츠 ---
    st.title("🔮 AI 천기통달 VIP 상담 (전문가용)")

    if st.session_state['run_analysis']:
        if not FIXED_API_KEY or len(FIXED_API_KEY) < 10:
            st.error("API 키 오류")
            st.stop()

        model_name = "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={FIXED_API_KEY}"
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
                    # 대운을 3개씩 끊어서 보여줌
                    dw = result['대운']
                    st.caption(f"대운: {', '.join(dw[:4])} ...")
                with c3:
                    if st.button("💾 DB 저장"):
                        save_consultation(st.session_state['user_id'], name, gender, birth_date, birth_time, memo="자동 분석")
                        st.toast("저장 완료")

            # === 10만원 값어치 하는 메인 분석 생성 ===
            if 'lifetime_script' not in st.session_state:
                system_instruction = f"""
                [역할] 1회 상담료 10만원의 대한민국 상위 1% 역술가. 
                [대상] {name} ({gender}, {2025 - birth_date.year}세)
                [명식] {result['사주']} 
                [대운] {result['대운']} (숫자는 한국 나이 대운수임. 정확히 대입할 것)
                [자미] {result['자미두수']['명궁주성']}
                
                [★ 작성 지침: 10만원의 가치를 증명하라 ★]
                1. **분량:** A4 3장 분량으로 아주 상세하게 작성. 짧으면 환불감임.
                2. **태도:** 위로는 1도 필요 없음. 오직 '팩트'와 '위험 경고'만. 좋은 말보다 **나쁜 말(재앙, 사고, 이별, 파산)**을 집요하게 파고들 것.
                3. **형식:** 상담원이 읽기만 하면 되도록 **[① 🔎 팩트 폭격(전문용어)]**와 **[② 🗣️ 상담용 멘트(소름 돋는 비유)]**로 구분.
                4. **대운 분석:** "33세 갑자대운에는~" 처럼 정확한 나이를 찍어서, "직장 짤리고 길바닥에 나앉을 뻔했지?"라고 구체적인 사건을 맞춰야 함.
                
                [★ 13단계 정밀 분석 프로토콜 ★]
                1. **원국 기질:** 오행의 편중을 찾아 성격 파탄, 고집, 아집 등 인간관계의 문제를 지적.
                2. **지장간/12운성:** 겉과 속이 다른 이중성, 혹은 에너지가 고갈된 상태(死, 墓)를 경고.
                3. **형충파해/공망 (핵심):** "배우자 자리가 깨졌다", "돈 창고가 뚫렸다" 등 인생의 지뢰밭을 적나라하게 묘사.
                4. **흉신/악살:** 백호살(피를 봄), 도화살(이성 문제), 현침살(수술수) 등 구체적 재앙 예고.
                5. **오행 건강:** 취약 장기 지목. "이거 방치하면 5년 안에 수술한다"고 강력 경고.
                6. **용신/기신:** 살길(용신)과 죽을길(기신) 구분.
                7. **격국/조후:** 그릇의 크기 평가 (종지그릇인지 항아리인지).
                8. **특수격/신살**
                9. **★ 자미두수 크로스체크:** 별자리에서도 흉한게 보이면 "사주랑 똑같네, 넌 빼박이다"라고 강조.
                10. **★ 과거 대운 검증 (신뢰도):** 과거 가장 힘들었던 대운을 찾아 구체적 사건(이혼/부도/수술) 명시.
                11. **세운/미래 (일기예보):** 올해/내년의 구체적 위기(사기수, 관재수) 예고.
                12. **물상론:** 위태로운 풍경 묘사 (예: 태풍 앞의 촛불).
                13. **종합 총평 및 독설 솔루션:** "정신 안 차리면 노년에 폐지 줍는다"는 식의 강력한 멘트와 현실적 개운법.
                """
                
                with st.spinner("천기를 꿰뚫어 운명의 함정을 정밀 타격 중... (상세 분석)"):
                    try:
                        resp = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": system_instruction}]}]})
                        st.session_state['lifetime_script'] = resp.json()['candidates'][0]['content']['parts'][0]['text']
                    except Exception as e:
                        st.error(f"분석 오류: {e}")

            # 결과 표시
            if 'lifetime_script' in st.session_state:
                st.markdown(st.session_state['lifetime_script'])
                st.divider()
                
                # --- 채팅 영역 (항상 하단에 고정) ---
                st.subheader("💬 심층 독설 상담")
                st.info("왼쪽 키워드 버튼을 누르거나, 아래에 직접 질문하세요. (예: '남편 바람나?', '언제 망해?')")
                
                # 대화 기록 출력
                for msg in st.session_state['chat_history']:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])

                # 입력 처리 (버튼 클릭 or 직접 입력)
                prompt = None
                
                # 1. 키워드 버튼 눌렀을 때
                if st.session_state.get('chat_input_manual'):
                    prompt = st.session_state['chat_input_manual']
                    st.session_state['chat_input_manual'] = None
                
                # 2. 직접 입력했을 때 (항상 활성화)
                elif user_input := st.chat_input("질문을 입력하세요..."):
                    prompt = user_input
                
                # 질문 처리
                if prompt:
                    st.session_state['chat_history'].append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.write(prompt)
                    
                    # 채팅 프롬프트 (독설 유지)
                    chat_context = f"{st.session_state['lifetime_script']}\n\n[이전 대화]\n"
                    for m in st.session_state['chat_history'][:-1]:
                        chat_context += f"{m['role']}: {m['content']}\n"
                    chat_context += f"\n[현재 질문] {prompt}\n"
                    chat_context += """
                    [지침] 
                    1. 10만원짜리 상담이다. 대충 말하지 마라.
                    2. 부정적인 징조가 보이면 숨기지 말고 "위험하다", "망한다", "헤어진다"고 확실하게 말해라.
                    3. [① 팩트 분석]과 [② 🗣️ 상담 멘트] 형식을 지켜라.
                    """
                    
                    with st.spinner("냉철하게 분석 중..."):
                        try:
                            r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": chat_context}]}]})
                            ai_msg = r.json()['candidates'][0]['content']['parts'][0]['text']
                            st.session_state['chat_history'].append({"role": "assistant", "content": ai_msg})
                            with st.chat_message("assistant"):
                                st.write(ai_msg)
                        except: st.error("답변 생성 실패")