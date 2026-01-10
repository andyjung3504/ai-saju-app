import streamlit as st
import pandas as pd
import requests
import json
import time
# saju_logic에서 기존 함수들 + 새로 만든 함수들(login_user, save_consultation, get_my_consultation_history) 가져오기
from saju_logic import analyze_user, login_user, save_consultation, get_my_consultation_history

# --- [설정] API 키 관리 (수정됨) ---
# 로컬에서는 FIXED_API_KEY를 쓰고, 웹에서는 st.secrets를 쓴다.
try:
    # 1. 웹사이트(Streamlit Cloud)에 올렸을 때 비밀번호 가져오기
    FIXED_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    # 2. 내 컴퓨터에서 돌릴 때 (기존 키 사용)
    FIXED_API_KEY = "AIzaSyBUyzqFInhOChfPv0mMqVt0jJWw4wtFc1g"
# --------------------------------

st.set_page_config(page_title="천기통달 상담 시스템", layout="wide")

# --- 세션 상태 초기화 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'user_name' not in st.session_state:
    st.session_state['user_name'] = None

# ==========================================
# 1. 로그인 화면 (로그인 안 된 경우)
# ==========================================
if not st.session_state['logged_in']:
    st.title("🔒 천기통달 상담원 로그인")
    
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("아이디", placeholder="예: test1")
            password = st.text_input("비밀번호", type="password", placeholder="예: 1234")
            submit = st.form_submit_button("로그인")
            
            if submit:
                user_name = login_user(username, password)
                if user_name:
                    st.session_state['logged_in'] = True
                    st.session_state['user_id'] = username
                    st.session_state['user_name'] = user_name
                    st.success(f"{user_name}님 환영합니다!")
                    time.sleep(0.5)
                    st.rerun() # 화면 새로고침
                else:
                    st.error("아이디 또는 비밀번호가 틀렸습니다.")

# ==========================================
# 2. 메인 상담 화면 (로그인 된 경우)
# ==========================================
else:
    # 사이드바: 상담원 정보 및 로그아웃
    with st.sidebar:
        st.info(f"👤 상담원: **{st.session_state['user_name']}** ({st.session_state['user_id']})")
        
        if st.button("로그아웃"):
            st.session_state['logged_in'] = False
            st.rerun()
            
        st.divider()
        st.subheader("📋 최근 상담 이력 (10건)")
        history = get_my_consultation_history(st.session_state['user_id'])
        if history:
            for h in history:
                st.caption(f"{h[0]}({h[1]}) - {h[3][:10]}")
        else:
            st.caption("이력 없음")

        st.divider()
        st.header("📝 명조 입력")
        name = st.text_input("고객명", value="홍길동")
        gender = st.radio("성별", ["남성", "여성"], horizontal=True)
        calendar_type = st.radio("달력 기준", ["양력", "음력"], horizontal=True)
        is_lunar = True if calendar_type == "음력" else False
        
        col1, col2 = st.columns(2)
        with col1:
            birth_date = st.date_input("생년월일", value=pd.to_datetime("1990-05-05"))
        with col2:
            birth_time = st.time_input("태어난 시간", value=pd.to_datetime("14:30").time())
        
        analyze_btn = st.button("천기통달 비법 분석 (Enter)", type="primary")

    # 메인 타이틀
    st.title("🔮 AI 천기통달 역술 상담 (전문가용)")

    # 분석 버튼 로직
    if analyze_btn:
        st.session_state['run_analysis'] = True
        st.session_state['current_client'] = {'name': name, 'gender': gender, 'date': birth_date, 'time': birth_time}
        st.session_state['chat_history'] = [] 
        st.session_state.pop('lifetime_script', None) # 새 분석 시 기존 스크립트 삭제

    # 분석 결과 표출
    if st.session_state.get('run_analysis'):
        if not FIXED_API_KEY or FIXED_API_KEY == "여기에_API_키를_붙여넣으세요":
            st.error("⚠️ API 키 오류: app.py 파일에 API 키를 입력하세요.")
            st.stop()

        # 모델 설정
        model_name = "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={FIXED_API_KEY}"
        headers = {'Content-Type': 'application/json'}

        # 로직 실행
        result = analyze_user(birth_date.year, birth_date.month, birth_date.day, birth_time.hour, is_lunar, gender)
        
        if "error" in result:
            st.error(result["error"])
        else:
            # 1. 데이터 요약 및 저장 버튼
            with st.expander("📊 명식 데이터 및 상담 저장", expanded=True):
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    st.info(f"대상: {name} ({gender})")
                    st.write(f"명궁: {result['자미두수']['명궁위치']}")
                with c2:
                    st.write(f"사주: {result['사주']}")
                    st.caption(f"대운: {result['대운']}")
                with c3:
                    # ★★★ 상담 저장 기능 ★★★
                    if st.button("💾 상담 기록 DB 저장"):
                        success = save_consultation(
                            st.session_state['user_id'], 
                            name, 
                            gender, 
                            birth_date, 
                            birth_time, 
                            memo="자동 분석 실행"
                        )
                        if success:
                            st.toast("✅ DB에 저장되었습니다!", icon="💾")
                        else:
                            st.error("저장 실패")

            # 2. AI 분석 스크립트 생성 (기존 프롬프트 유지)
            if 'lifetime_script' not in st.session_state:
                
                # (프롬프트는 너무 기니까 생략하지 않고 핵심만 유지 - 기존 전문가용 프롬프트 그대로 사용)
                system_instruction = f"""
                [역할] 천기통달 역술가. 내용 길게 A4 3장 분량.
                [대상] {name} ({gender}, {result['사주']})
                [분석] 
                1. 원국(십성)
                2. 지장간/12운성/12신살
                3. 형충파해/공망/원진
                4. 길성/흉신
                5. 오행세력/신강신약
                6. 용신
                7. 격국/조후
                8. 특수격/신살
                9. 물상론
                10. 자미두수({result['자미두수']['명궁주성']})
                11. 대운검증(과거 {result['대운']} 활용하여 구체적 사건 지적)
                12. 세운/미래
                13. 총평/개운법
                [스타일] 정중하고 냉철하게. 리스트 나열 금지. 서술형으로 상세히.
                """
                
                try:
                    data = {"contents": [{"parts": [{"text": system_instruction}]}]}
                    with st.spinner("천기누설 13단계 정밀 분석 중..."):
                        response = requests.post(url, headers=headers, json=data)
                        if response.status_code == 200:
                            st.session_state['lifetime_script'] = response.json()['candidates'][0]['content']['parts'][0]['text']
                        else:
                            st.error(f"API 호출 실패: {response.text}")
                except Exception as e:
                    st.error(f"오류: {e}")

            # 3. 결과 출력
            if 'lifetime_script' in st.session_state:
                st.markdown("### 📜 정밀 감정서")
                st.write(st.session_state['lifetime_script'])
                st.divider()
                
                # 4. 채팅
                st.subheader("💬 상담 챗봇")
                for msg in st.session_state.get('chat_history', []):
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])

                if user_input := st.chat_input("질문 입력"):
                    st.session_state['chat_history'].append({"role": "user", "content": user_input})
                    with st.chat_message("user"):
                        st.write(user_input)

                    chat_prompt = f"""
                    [기존 분석 바탕 답변]
                    질문: {user_input}
                    화법: 전문가답게 직설적으로.
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
                        st.error(f"오류: {e}")
    else:
        st.info("👈 왼쪽에서 고객 정보를 입력하고 분석을 시작하세요.")