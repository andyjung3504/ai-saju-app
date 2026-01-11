import streamlit as st
import pandas as pd
import requests
import json
import time
from saju_logic import analyze_user, login_user, save_consultation, get_my_consultation_history, check_and_init_db

# --- [설정] 페이지 기본 설정 ---
st.set_page_config(page_title="천기통달 상담 시스템", layout="wide")

# ★ DB 자동 점검
check_and_init_db()

# --- [설정] API 키 관리 ---
try:
    FIXED_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    FIXED_API_KEY = "여기에_API_키를_붙여넣으세요"

# --- 세션 상태 초기화 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'user_name' not in st.session_state:
    st.session_state['user_name'] = None
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

# ==========================================
# 1. 로그인 화면
# ==========================================
if not st.session_state['logged_in']:
    st.title("🔒 천기통달 상담원 로그인")
    st.markdown("### 전문가용 역술 상담 시스템")
    
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("아이디", placeholder="예: test1")
            password = st.text_input("비밀번호", type="password", placeholder="예: 1234")
            submit = st.form_submit_button("로그인", type="primary")
            
            if submit:
                user_name = login_user(username, password)
                if user_name:
                    st.session_state['logged_in'] = True
                    st.session_state['user_id'] = username
                    st.session_state['user_name'] = user_name
                    st.success(f"{user_name}님 환영합니다!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 틀렸습니다.")

# ==========================================
# 2. 메인 상담 화면
# ==========================================
else:
    # --- 사이드바 설정 ---
    with st.sidebar:
        st.info(f"👤 상담원: **{st.session_state['user_name']}**")
        
        if st.button("로그아웃"):
            st.session_state['logged_in'] = False
            st.session_state.clear()
            st.rerun()
            
        st.divider()

        # [1] 고객 정보 입력 섹션
        st.header("📝 고객 명조 입력")
        name = st.text_input("고객명", value="홍길동")
        gender = st.radio("성별", ["남성", "여성"], horizontal=True)
        calendar_type = st.radio("달력 기준", ["양력", "음력"], horizontal=True)
        is_lunar = True if calendar_type == "음력" else False
        
        col1, col2 = st.columns(2)
        with col1:
            birth_date = st.date_input(
                "생년월일", 
                value=pd.to_datetime("1980-01-01"),
                min_value=pd.to_datetime("1900-01-01"),
                max_value=pd.to_datetime("2100-12-31")
            )
        with col2:
            birth_time = st.time_input("태어난 시간", value=pd.to_datetime("14:30").time())
        
        analyze_btn = st.button("천기통달 비법 분석 (Enter)", type="primary")
        
        # [2] 분석 후 나타나는 '키워드 질문 버튼' 섹션
        if st.session_state.get('run_analysis'):
            st.divider()
            st.markdown("### ⚡ 키워드 빠른 질문")
            st.caption("클릭 시 '전문분석+비유' 자동 생성")
            
            # 선생님이 요청하신 키워드 + 필수 키워드 추가
            keywords = [
                "💰 금전운/재물운", "🏢 사업운/창업운", "🏠 매매운/부동산",
                "❤️ 연애운/부부운", "💊 본인 건강운", "👵 부모님 건강운",
                "💼 직장운/승진운", "🎓 자녀운/합격운", "⚖️ 관재구설/소송",
                "✈️ 이사운/이동운"
            ]
            
            # 버튼 클릭 시 처리 로직
            for kw in keywords:
                if st.button(kw):
                    st.session_state['chat_input_manual'] = kw + "에 대해 자세히 알려주세요."

        st.divider()
        st.subheader("📋 최근 상담 이력")
        history = get_my_consultation_history(st.session_state['user_id'])
        if history:
            for h in history:
                st.caption(f"{h[0]}({h[1]}) - {h[3][:10]}")

    # --- 메인 화면 콘텐츠 ---
    st.title("🔮 AI 천기통달 역술 상담 (전문가용)")

    # 분석 버튼 클릭 시 초기화
    if analyze_btn:
        st.session_state['run_analysis'] = True
        st.session_state['chat_history'] = [] 
        st.session_state.pop('lifetime_script', None)

    # 분석 로직 실행
    if st.session_state.get('run_analysis'):
        if not FIXED_API_KEY or FIXED_API_KEY == "여기에_API_키를_붙여넣으세요":
            st.error("⚠️ API 키 오류")
            st.stop()

        model_name = "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={FIXED_API_KEY}"
        headers = {'Content-Type': 'application/json'}

        # 사주 계산
        result = analyze_user(birth_date.year, birth_date.month, birth_date.day, birth_time.hour, is_lunar, gender)
        
        if "error" in result:
            st.error(result["error"])
        else:
            # 상단 데이터 요약 및 저장
            with st.expander("📊 명식 데이터 확인 및 DB 저장", expanded=True):
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    st.info(f"대상: {name} ({gender})")
                    st.write(f"자미 명궁: **{result['자미두수']['명궁위치']}**")
                    st.caption(f"주성: {result['자미두수']['명궁주성']}")
                with c2:
                    st.write(f"사주: {result['사주']}")
                    st.caption(f"대운 흐름: {result['대운']}")
                with c3:
                    if st.button("💾 DB에 저장하기"):
                        success = save_consultation(st.session_state['user_id'], name, gender, birth_date, birth_time, memo="자동 분석 결과")
                        if success: st.toast("✅ 저장 완료!", icon="💾")
                        else: st.error("저장 실패")

            # 메인 스크립트 생성 (13단계 비법)
            if 'lifetime_script' not in st.session_state:
                system_instruction = f"""
                [역할] 대한민국 최고의 역술가이자 상담 스크립트 라이터.
                [대상] {name} ({gender}, {2025 - birth_date.year}세)
                [명식] {result['사주']} / [대운] {result['대운']} / [자미] {result['자미두수']['명궁주성']}
                
                [★ 작성 원칙: 상담원 브리핑용 ★]
                1. 모든 항목은 **[① 전문 분석]**과 **[② 💡상담용 비유]**로 나누어 작성.
                2. 전문 분석: 십성, 신살, 용신 등 한자 용어 사용하여 냉철하게.
                3. 상담용 비유: "지갑에 구멍난 격", "브레이크 없는 차" 등 쉬운 비유 필수.
                4. 말투: 세련된 전문가 톤.
                
                [★ 13단계 분석 순서 ★]
                1. 원국 기본(성격/기질) - 자연물 비유
                2. 지장간/12운성(속마음)
                3. 형충파해/공망(인생 지뢰밭) - 공망은 '헛발질' 등으로 비유
                4. 길성/흉신 - 백호/양인 등 경고
                5. 오행 세력(건강/단점)
                6. 용신(해결사 글자)
                7. 격국/조후
                8. 특수격/신살
                9. ★ 자미두수 별의 계시 (사주와 비교 설명)
                10. ★ 대운 검증 (나열 금지, 사건 창조) - "지난 XX대운은 사주의 OO와 충돌하여 ~게 힘들었을 것"
                11. 세운/미래 (날씨 비유)
                12. 물상론 (풍경화 묘사)
                13. 총평 및 개운법 (구체적 행동 지침)
                """
                
                try:
                    data = {"contents": [{"parts": [{"text": system_instruction}]}]}
                    with st.spinner("천기를 꿰뚫어 '전문 분석'과 '상담용 비유'를 생성 중입니다..."):
                        response = requests.post(url, headers=headers, json=data)
                        if response.status_code == 200:
                            st.session_state['lifetime_script'] = response.json()['candidates'][0]['content']['parts'][0]['text']
                        else:
                            st.error(f"API 호출 실패: {response.text}")
                except Exception as e:
                    st.error(f"오류: {e}")

            # 결과 출력
            if 'lifetime_script' in st.session_state:
                st.markdown("### 📜 정밀 감정서")
                st.write(st.session_state['lifetime_script'])
                st.divider()
                
                # --- 채팅 인터페이스 ---
                st.subheader("💬 심층 질의응답")

                # 채팅 기록 표시
                for msg in st.session_state.get('chat_history', []):
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])

                # 사용자 입력 처리 (직접 입력 OR 사이드바 버튼 클릭)
                prompt_text = None
                
                # 1. 사이드바 버튼으로 들어온 입력 확인
                if st.session_state.get('chat_input_manual'):
                    prompt_text = st.session_state['chat_input_manual']
                    st.session_state['chat_input_manual'] = None # 초기화
                
                # 2. 채팅창 직접 입력 확인
                elif user_input := st.chat_input("질문 입력 (또는 왼쪽 키워드 버튼 클릭)"):
                    prompt_text = user_input

                # 실제 API 호출 및 답변 생성
                if prompt_text:
                    st.session_state['chat_history'].append({"role": "user", "content": prompt_text})
                    with st.chat_message("user"):
                        st.write(prompt_text)

                    # ★★★ 채팅용 프롬프트 (여기도 원문+비유 강제 적용) ★★★
                    chat_prompt = f"""
                    [기존 분석 데이터 기반]
                    질문: {prompt_text}
                    
                    [답변 지침: 상담원 브리핑용]
                    1. 질문에 대해 사주/대운/자미두수를 근거로 분석하십시오.
                    2. 반드시 **[① 전문 분석]** (용어 사용) 파트와 **[② 💡상담용 비유]** (쉬운 설명) 파트로 나누어 답변하십시오.
                    3. 결론은 명확하고 직설적으로 내리십시오.
                    """
                    
                    try:
                        data = {"contents": [{"parts": [{"text": st.session_state['lifetime_script'] + "\n" + chat_prompt}]}]}
                        response = requests.post(url, headers=headers, json=data)
                        if response.status_code == 200:
                            ai_reply = response.json()['candidates'][0]['content']['parts'][0]['text']
                            st.session_state['chat_history'].append({"role": "assistant", "content": ai_reply})
                            with st.chat_message("assistant"):
                                st.write(ai_reply)
                    except Exception as e:
                        st.error(f"채팅 오류: {e}")