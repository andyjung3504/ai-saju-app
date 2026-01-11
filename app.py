import streamlit as st
import pandas as pd
import requests
import json
import time
from saju_logic import analyze_user, login_user, save_consultation, get_my_consultation_history, check_and_init_db

# --- 설정 ---
st.set_page_config(page_title="천기통달 VIP 상담", layout="wide")
check_and_init_db()

try: FIXED_API_KEY = st.secrets["GEMINI_API_KEY"]
except: FIXED_API_KEY = "여기에_API_키를_붙여넣으세요"

# --- 세션 초기화 ---
if 'chat_history' not in st.session_state: st.session_state['chat_history'] = []
if 'chat_input_manual' not in st.session_state: st.session_state['chat_input_manual'] = None
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
    # --- 사이드바 ---
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
        
        if st.button("천기통달 분석 실행", type="primary"):
            st.session_state['run_analysis'] = True
            st.session_state['chat_history'] = [] 
            st.session_state.pop('lifetime_script', None)

        st.divider()
        st.markdown("### ⚡ 상담 숏컷")
        keywords = ["💰 재물/금전운", "🏠 매매/부동산", "❤️ 부부/이혼수", "💊 건강/수술수", "⚖️ 관재/소송", "🎓 자녀/학업", "✈️ 이동/이사", "🏢 사업/폐업"]
        
        # ★★★ 키워드 버튼 로직 개선 ★★★
        # 버튼을 누르면 'chat_input_manual'에 값만 넣고, 화면 전체를 다시 그려서(rerun) 채팅 로직이 돌게 함.
        for kw in keywords:
            if st.button(kw):
                st.session_state['chat_input_manual'] = kw + "에 대해 냉정하게, 안 좋은 점 위주로 분석해줘."
                if not st.session_state['run_analysis']: # 분석 안 된 상태면 강제 실행
                    st.session_state['run_analysis'] = True
                    st.session_state['chat_history'] = []
                st.rerun() # 화면 새로고침 -> 아래 채팅 로직에서 처리됨

    # --- 메인 컨텐츠 ---
    st.title("🔮 AI 천기통달 VIP 상담 (전문가용)")

    if st.session_state['run_analysis']:
        if not FIXED_API_KEY or len(FIXED_API_KEY) < 10:
            st.error("API 키 오류")
            st.stop()

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={FIXED_API_KEY}"
        headers = {'Content-Type': 'application/json'}

        # 1. 사주 분석 결과 가져오기
        # (analyze_user 함수가 DB오류나면 'error' 키를 반환함)
        result = analyze_user(birth_date.year, birth_date.month, birth_date.day, birth_time.hour, is_lunar, gender)
        
        if "error" in result:
            st.error(result["error"])
        else:
            # 상단 정보 표시
            with st.expander("📊 명식 데이터 및 저장", expanded=True):
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    st.info(f"대상: {name} ({gender})")
                    st.write(f"자미: **{result['자미두수']['명궁위치']}** ({result['자미두수']['명궁주성']})")
                with c2:
                    st.write(f"사주: {result['사주']}")
                    st.write(f"대운: {result['대운']}") # 이제 6세, 16세.. 이렇게 정확히 나옴
                with c3:
                    if st.button("💾 DB 저장"):
                        save_consultation(st.session_state['user_id'], name, gender, birth_date, birth_time, memo="자동 분석")
                        st.toast("저장 완료")

            # 2. 메인 분석 스크립트 생성 (한 번만 생성 후 저장)
            if 'lifetime_script' not in st.session_state:
                # ★★★ 독설 + 미래 대운 포함 프롬프트 ★★★
                sys_msg = f"""
                [역할] 1회 10만원 상담료의 대한민국 최고 역술가.
                [대상] {name} ({gender}, {2025 - birth_date.year}세)
                [명식] {result['사주']}
                [대운] {result['대운']} (이 숫자는 만나이 대운수다. 정확히 적용해라.)
                
                [★ 작성 원칙: 돈값 하는 독설 ★]
                1. **위로 금지:** 고객은 재앙을 피하고 싶어서 돈을 냈다. "잘될 거야"라는 헛소리 말고 "이거 안 고치면 망한다"고 해라.
                2. **구성:** [① 🔎 팩트 폭격(전문용어)]와 [② 🗣️ 상담 멘트(소름 돋는 비유)]로 나눠라.
                3. **미래 대운 필수:** 과거만 맞추지 말고, **앞으로 다가올 60대, 70대 대운까지** 10년 단위로 쪼개서 "언제 아프고 언제 돈 나가는지" 예언해라.
                
                [★ 13단계 정밀 분석 ★]
                1. 원국 기질 (성격 결함 지적)
                2. 지장간/12운성 (속마음의 이중성)
                3. 형충파해/공망 (**인생의 지뢰밭 - 가장 중요**)
                4. 흉신/악살 (백호, 현침 등 수술/사고수 경고)
                5. 오행 건강 (취약 장기, 5년 내 수술 가능성)
                6. 용신/기신 (살길과 죽을길)
                7. 격국/조후
                8. 특수격/신살
                9. 자미두수 크로스체크 (사주와 엮어서 팩트 확인)
                10. **★ 과거 대운 검증:** 30대, 40대 대운을 콕 집어 "죽을 만큼 힘들었지?"라고 구체적 사건(이혼/파산) 언급.
                11. **★ 미래 대운 예언 (신규 추가):** 앞으로 다가올 대운(50대, 60대...)의 길흉화복을 '일기예보'처럼 상세히 기술.
                12. 세운(올해/내년) 위기 경고
                13. 총평 및 독설 솔루션 (안 지키면 미래 없다)
                """
                
                with st.spinner("천기를 꿰뚫어 '운명의 함정'을 정밀 타격 중..."):
                    try:
                        r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": sys_msg}]}]})
                        st.session_state['lifetime_script'] = r.json()['candidates'][0]['content']['parts'][0]['text']
                    except: st.error("분석 실패. API 키를 확인하세요.")

            # 3. 분석 결과 표시
            if 'lifetime_script' in st.session_state:
                st.markdown(st.session_state['lifetime_script'])
                st.divider()
                
                # --- 채팅창 (여기가 중요: 절대 사라지지 않음) ---
                st.subheader("💬 심층 독설 상담")
                
                # 대화 기록 표시
                for msg in st.session_state['chat_history']:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
                
                # 입력값 결정 (버튼 클릭값 OR 직접 입력값)
                prompt = None
                
                # 1. 버튼으로 들어온 값이 있으면 그걸 씀
                if st.session_state['chat_input_manual']:
                    prompt = st.session_state['chat_input_manual']
                    st.session_state['chat_input_manual'] = None # 쓰고 나서 비움 (중복 방지)
                
                # 2. 직접 입력 (st.chat_input)
                # 주의: st.chat_input은 맨 아래에 고정됨
                elif u_in := st.chat_input("질문을 입력하세요... (예: 남편 바람기, 부도 위기)"):
                    prompt = u_in
                
                # 질문이 들어왔으면 처리
                if prompt:
                    st.session_state['chat_history'].append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.write(prompt)
                    
                    # 채팅 프롬프트 (독설 유지)
                    chat_ctx = f"{st.session_state['lifetime_script']}\n\n[이전 대화]\n"
                    for m in st.session_state['chat_history'][:-1]:
                        chat_ctx += f"{m['role']}: {m['content']}\n"
                    chat_ctx += f"\n[현재 질문] {prompt}\n"
                    chat_ctx += """
                    [지침]
                    1. 10만원짜리 상담이다. 대충 짧게 하지 마라.
                    2. '남편 바람', '부도' 같은 질문에는 사주 원국(도화살, 충)을 근거로 **"위험하다", "징조가 보인다"**고 확실하게 답해라.
                    3. [① 팩트]와 [② 상담멘트] 형식을 지켜라.
                    """
                    
                    with st.spinner("냉철하게 분석 중..."):
                        try:
                            r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": chat_ctx}]}]})
                            ai_msg = r.json()['candidates'][0]['content']['parts'][0]['text']
                            st.session_state['chat_history'].append({"role": "assistant", "content": ai_msg})
                            with st.chat_message("assistant"):
                                st.write(ai_msg)
                            # 답변 후 리런(rerun)해서 화면 갱신 (선택사항이나, 입력창 초기화를 위해 추천)
                            st.rerun()
                        except: st.error("답변 실패")