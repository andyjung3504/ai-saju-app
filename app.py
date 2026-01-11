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
    with st.sidebar:
        st.info(f"👤 상담원: **{st.session_state['user_name']}** ({st.session_state['user_id']})")
        
        if st.button("로그아웃"):
            st.session_state['logged_in'] = False
            st.session_state.clear()
            st.rerun()
            
        st.divider()
        st.subheader("📋 최근 상담 이력")
        history = get_my_consultation_history(st.session_state['user_id'])
        if history:
            for h in history:
                st.caption(f"{h[0]}({h[1]}) - {h[3][:10]}")
        else:
            st.caption("저장된 이력이 없습니다.")

        st.divider()
        st.header("📝 고객 명조 입력")
        name = st.text_input("고객명", value="홍길동")
        gender = st.radio("성별", ["남성", "여성"], horizontal=True)
        calendar_type = st.radio("달력 기준", ["양력", "음력"], horizontal=True)
        is_lunar = True if calendar_type == "음력" else False
        
        col1, col2 = st.columns(2)
        with col1:
            # ★★★ [수정됨] 연도 입력 범위 확장 (1900년 ~ 2100년) ★★★
            # min_value를 지정하지 않으면 날짜 선택기가 제한될 수 있음.
            birth_date = st.date_input(
                "생년월일", 
                value=pd.to_datetime("1980-01-01"),
                min_value=pd.to_datetime("1900-01-01"),
                max_value=pd.to_datetime("2100-12-31")
            )
        with col2:
            birth_time = st.time_input("태어난 시간", value=pd.to_datetime("14:30").time())
        
        analyze_btn = st.button("천기통달 비법 분석 (Enter)", type="primary")

    st.title("🔮 AI 천기통달 역술 상담 (전문가용)")

    if analyze_btn:
        st.session_state['run_analysis'] = True
        st.session_state['chat_history'] = [] 
        st.session_state.pop('lifetime_script', None)

    if st.session_state.get('run_analysis'):
        if not FIXED_API_KEY or FIXED_API_KEY == "여기에_API_키를_붙여넣으세요":
            st.error("⚠️ API 키 오류")
            st.stop()

        model_name = "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={FIXED_API_KEY}"
        headers = {'Content-Type': 'application/json'}

        result = analyze_user(birth_date.year, birth_date.month, birth_date.day, birth_time.hour, is_lunar, gender)
        
        if "error" in result:
            st.error(result["error"])
        else:
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
                        success = save_consultation(
                            st.session_state['user_id'], 
                            name, 
                            gender, 
                            birth_date, 
                            birth_time, 
                            memo="자동 분석 결과"
                        )
                        if success:
                            st.toast("✅ 저장 완료!", icon="💾")
                        else:
                            st.error("저장 실패")

            if 'lifetime_script' not in st.session_state:
                system_instruction = f"""
                [역할] 천기를 통달한 전설적인 역술가. **요약 금지. A4 3장 분량 필수.**
                
                [분석 데이터]
                - 이름: {name} ({gender}, 현재 약 {2025 - birth_date.year}세)
                - 명식: {result['사주']}
                - ★대운 흐름: {result['대운']}
                - ★자미두수: {result['자미두수']['명궁위치']} ({result['자미두수']['명궁주성']})
                
                [★ 천기통달 13단계 분석 순서 (용어+주석 필수) ★]
                1. **원국 십성**: 기둥별 세력 분석.
                2. **지장간/12운성/12신살**: 속마음, 에너지, 신살 해부.
                3. **형충파해/공망/원진**: 합충 변화 및 **공망(空亡)** 경고.
                4. **길성/흉신**: 귀인 및 흉살 발굴.
                5. **오행세력/신강신약**: 성격의 결함 지적.
                6. **용신 정밀 타격**: 조후/억부 용신 선정.
                7. **격국/조후**: 그릇 크기 평가.
                8. **특수격/진가신살**: 검증.
                9. **물상론**: 자연 풍경 묘사.
                10. **★ 자미두수 별의 계시 (필수)**: 명궁 주성 해석 및 사주와 비교.
                11. **★ 대운 검증 (나열 시 파면) ★**: 
                    - **"지난 XX대운(간지)에는 사주의 OO와 (충/형)이 되어 (돈/건강) 문제로 죽을 만큼 힘들었을 것이다"**라고 구체적 사건 지목.
                12. **세운/미래**: 길흉 예언.
                13. **총평/개운법**: 현실적 조언.
                
                [작성 태도]
                - "~~입니다" 체.
                - 냉철한 팩트 위주.
                """
                
                try:
                    data = {"contents": [{"parts": [{"text": system_instruction}]}]}
                    with st.spinner("천기를 꿰뚫어 13단계 비법으로 정밀 해부 중입니다..."):
                        response = requests.post(url, headers=headers, json=data)
                        if response.status_code == 200:
                            st.session_state['lifetime_script'] = response.json()['candidates'][0]['content']['parts'][0]['text']
                        else:
                            st.error(f"API 호출 실패: {response.text}")
                except Exception as e:
                    st.error(f"시스템 오류: {e}")

            if 'lifetime_script' in st.session_state:
                st.markdown("### 📜 천기통달 심층 정밀 감정서")
                st.write(st.session_state['lifetime_script'])
                
                st.divider()
                
                st.subheader("💬 심층 질의응답")
                for msg in st.session_state.get('chat_history', []):
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])

                if user_input := st.chat_input("질문 입력"):
                    st.session_state['chat_history'].append({"role": "user", "content": user_input})
                    with st.chat_message("user"):
                        st.write(user_input)

                    chat_prompt = f"""
                    [기존 분석 데이터 기반]
                    질문: {user_input}
                    지침: 사주/대운/자미두수 근거로 직설적이고 명쾌하게 답변. 위로 금지.
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