import streamlit as st
import sys
import os

# 1. 페이지 설정 (가장 먼저 실행)
st.set_page_config(page_title="서버 진단 모드", layout="wide")

st.title("🚨 긴급 복구 모드")
st.write("앱이 실행되지 않아 진단 중입니다...")

# 2. 필수 파일 확인
st.subheader("1. 파일 점검")
files = os.listdir('.')
if "saju_logic.py" in files:
    st.success("✅ saju_logic.py 파일이 있습니다.")
else:
    st.error("❌ saju_logic.py 파일이 없습니다! 깃허브에 파일을 업로드해야 합니다.")
    st.stop() # 여기서 중단

if "saju.db" in files:
    st.success(f"✅ saju.db 파일이 있습니다. (크기: {os.path.getsize('saju.db')} bytes)")
else:
    st.warning("⚠️ saju.db 파일이 없습니다. (자동 생성 시도 예정)")

# 3. 라이브러리 및 모듈 로드 시도 (여기서 에러가 많이 남)
st.subheader("2. 모듈 불러오기 테스트")
try:
    import pandas as pd
    st.write(" - pandas 로드 성공")
    import requests
    st.write(" - requests 로드 성공")
    import sqlite3
    st.write(" - sqlite3 로드 성공")
    
    # ★ 여기가 핵심: saju_logic 불러오기
    import saju_logic
    st.success("✅ saju_logic 모듈을 정상적으로 불러왔습니다!")
    
except Exception as e:
    st.error(f"❌ 치명적 오류 발생: {e}")
    st.error("위 에러 메시지를 복사해서 AI에게 알려주세요.")
    st.stop()

# 4. DB 초기화 테스트
st.subheader("3. DB 연결 테스트")
try:
    saju_logic.check_and_init_db()
    st.success("✅ DB 초기화 함수 실행 성공")
except Exception as e:
    st.error(f"❌ DB 연결 실패: {e}")
    st.stop()

# 5. 모든 테스트 통과 시 원래 화면 로드 시도
st.divider()
st.success("🎉 모든 시스템이 정상입니다. 이제 아래 버튼을 누르면 원본 앱을 실행합니다.")

if st.button("앱 실행하기"):
    try:
        # 여기서부터 원래 app.py의 핵심 로직을 실행
        # (세션 초기화 등)
        if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
        
        # 로그인 화면 강제 렌더링
        st.title("🔒 명리학 마스터 로그인 (복구됨)")
        with st.form("login_form_rescue"):
            username = st.text_input("아이디")
            password = st.text_input("비밀번호", type="password")
            if st.form_submit_button("로그인"):
                user_name = saju_logic.login_user(username, password)
                if user_name:
                    st.success(f"환영합니다, {user_name}님!")
                else:
                    st.error("로그인 실패")
    except Exception as e:
        st.error(f"앱 실행 중 오류: {e}")