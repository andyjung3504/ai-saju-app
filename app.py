import streamlit as st
import pandas as pd
import requests
import json
import time
from saju_logic import analyze_user, login_user, save_consultation, get_my_consultation_history, check_and_init_db

# --- [설정] 페이지 기본 설정 ---
st.set_page_config(page_title="천기통달 상담 시스템", layout="wide")

# ★★★ [핵심 1] 앱 시작 시 DB 자동 점검 (테이블 없으면 자동 생성) ★★★
# 이 함수가 없으면 웹 배포 시 'no such table: users' 에러가 납니다.
check_and_init_db()

# --- [설정] API 키 관리 (웹 배포 호환) ---
try:
    # 1. 스트림릿 클라우드 배포 시 Secrets에서 가져옴
    FIXED_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    # 2. 로컬 테스트 시 직접 입력 (따옴표 안에 본인 키 입력)
    FIXED_API_KEY = "여기에_API_키를_붙여넣으세요"

# --- 세션 상태 초기화 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'user_name' not in st.session_state:
    st.session_state['user_name'] = None

# ==========================================
# 1. 로그인 화면 (비로그인 상태)
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
                    st.error("아이디 또는 비밀번호가 틀렸습니다. (기본: test1 / 1234)")

# ==========================================
# 2. 메인 상담 화면 (로그인 상태)
# ==========================================
else:
    # --- 사이드바: 입력 및 메뉴 ---
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
                # 이름(성별) - 날짜
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
            birth_date = st.date_input("생년월일", value=pd.to_datetime("1990-05-05"))
        with col2:
            birth_time = st.time_input("태어난 시간", value=pd.to_datetime("14:30").time())
        
        analyze_btn = st.button("천기통달 비법 분석 (Enter)", type="primary")

    # --- 메인 콘텐츠 ---
    st.title("🔮 AI 천기통달 역술 상담 (전문가용)")

    # [분석 실행]
    if analyze_btn:
        st.session_state['run_analysis'] = True
        st.session_state['chat_history'] = [] 
        st.session_state.pop('lifetime_script', None) # 기존 분석 내용 초기화

    # [결과 화면]
    if st.session_state.get('run_analysis'):
        if not FIXED_API_KEY or FIXED_API_KEY == "여기에_API_키를_붙여넣으세요":
            st.error("⚠️ API 키 오류: 스트림릿 클라우드의 Secrets에 키를 등록하거나 코드에 입력하세요.")
            st.stop()

        # ★★★ [핵심 2] API URL 및 헤더 정의 (채팅 오류 방지용 전역 변수화) ★★★
        model_name = "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={FIXED_API_KEY}"
        headers = {'Content-Type': 'application/json'}

        # 로직 실행
        result = analyze_user(birth_date.year, birth_date.month, birth_date.day, birth_time.hour, is_lunar, gender)
        
        if "error" in result:
            st.error(result["error"])
        else:
            # 1. 데이터 요약 및 저장 패널
            with st.expander("📊 명식 데이터 확인 및 DB 저장", expanded=True):
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    st.info(f"대상: {name} ({gender})")
                    st.write(f"자미 명궁: **{result['자미두수']['명궁위치']}**")
                    st.caption(f"주성: {result['자미두수']['명궁주성']}")
                with c2:
                    st.write(f"사주: {result['사주']}")
                    # 대운 리스트는 너무 기니까 접어서 보여줌
                    st.caption(f"대운 흐름: {result['대운']}")
                with c3:
                    st.write("상담 기록 저장")
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

            # 2. AI 분석 스크립트 생성 (13단계 비법)
            if 'lifetime_script' not in st.session_state:
                
                # ★★★ [핵심 3] 과거 대운 검증 강제 프롬프트 ★★★
                system_instruction = f"""
                [역할] 당신은 천기를 통달한 전설적인 역술가입니다. 
                고객은 인생의 기로에 서 있습니다. **절대 내용을 요약하거나 리스트만 나열하지 마십시오.**
                분량은 A4 3장 이상으로 아주 길고 상세하게 작성해야 합니다.
                
                [분석 데이터]
                - 이름: {name} ({gender}, 현재 약 {2025 - birth_date.year}세)
                - 명식: {result['사주']}
                - ★대운 흐름: {result['대운']}
                - ★자미두수: {result['자미두수']['명궁위치']} ({result['자미두수']['명궁주성']})
                
                [★ 천기통달 13단계 정밀 분석 프로토콜 (엄수) ★]
                각 단계별로 **전문 용어(한자 포함)**를 먼저 쓰고, 그 뒤에 반드시 **쉬운 해설(주석)**을 덧붙이세요.
                
                1. **원국 기본 분석 (천간/지지 십성)**: 각 기둥의 세력과 십성 정밀 분석.
                2. **지장간(支藏干), 12운성, 12신살**: 속마음(지장간)과 에너지 크기(12운성), 신살(도화, 역마 등) 해부.
                3. **궁성 및 상호작용 (형충파해/공망/원진)**: 
                   - 합, 충(沖), 형(刑), 파(破), 해(害), 원진살(怨嗔殺) 여부 샅샅이 분석.
                   - **공망(空亡)**을 찾아 비어있는 육친 경고.
                4. **길성(吉星)과 흉신(凶神)**: 천을귀인, 백호살, 괴강살 등.
                5. **오행 세력 및 신강/신약**: 오행 백분율 분석 및 성격의 장단점 적나라하게 지적.
                6. **용신(用神) 정밀 타격**: 조후/억부/통관 용신 선정 및 희신/기신 구분.
                7. **격국(格局)과 조후(調候)**: 그릇의 크기와 계절적 조화 평가.
                8. **특수격국 및 진가신살**: 종격 여부 및 신살 검증.
                9. **물상론(物象論)**: 사주를 한 폭의 자연 풍경으로 묘사.
                10. **★ 자미두수(紫微斗數) 별의 계시 (필수) ★**:
                    - 명궁 주성({result['자미두수']['명궁주성']})을 반드시 해석하고 사주와 비교 설명.
                
                11. **★ 대운(Great Luck) 흐름과 과거 검증 (나열 금지/매우 중요) ★**:
                    - **경고:** 대운 리스트를 단순히 나열하면 실패로 간주합니다.
                    - **미션:** 고객의 **과거 나이대(예: 10대, 20대)**에 해당하는 대운을 찾으세요.
                    - **작성법:** **"지난 XX대운(간지)에는 사주의 OOO와 (충/형/원진)이 되어, 이 시기에 (돈/건강/사람) 문제로 죽을 만큼 힘들었을 것입니다."** 라고 구체적인 사건을 콕 집어 맞추세요.
                
                12. **연도별 세운(歲運) 및 미래 예측**: 다가올 미래 예언.
                13. **종합 총평 및 개운법**: 냉철한 결론과 현실적 조언.
                
                [작성 태도]
                - 말투: "~~입니다" (정중하되 냉철함).
                - 내용: 듣기 좋은 소리만 하지 말고, 흉한 것은 흉하다고 확실히 말할 것.
                """
                
                try:
                    data = {"contents": [{"parts": [{"text": system_instruction}]}]}
                    with st.spinner("천기를 꿰뚫어 13단계 비법으로 정밀 해부 중입니다... (상세 분석)"):
                        response = requests.post(url, headers=headers, json=data)
                        if response.status_code == 200:
                            st.session_state['lifetime_script'] = response.json()['candidates'][0]['content']['parts'][0]['text']
                        else:
                            st.error(f"API 호출 실패: {response.text}")
                except Exception as e:
                    st.error(f"시스템 오류: {e}")

            # 3. 결과 출력
            if 'lifetime_script' in st.session_state:
                st.markdown("### 📜 천기통달 심층 정밀 감정서")
                st.write(st.session_state['lifetime_script'])
                
                st.divider()
                
                # 4. 채팅 (질문하기)
                st.subheader("💬 심층 질의응답 (무엇이든 물어보세요)")
                
                # 채팅 기록 표시
                for msg in st.session_state.get('chat_history', []):
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])

                # 채팅 입력
                if user_input := st.chat_input("예: 30대 때 왜 힘들었나요? 언제 돈이 벌리나요?"):
                    st.session_state['chat_history'].append({"role": "user", "content": user_input})
                    with st.chat_message("user"):
                        st.write(user_input)

                    # 채팅 프롬프트
                    chat_prompt = f"""
                    [기존 분석 데이터 기반]
                    질문: {user_input}
                    지침: 위에서 분석한 사주와 대운을 바탕으로, 전문 용어를 섞어가며 직설적이고 명쾌하게 답변하세요. 위로는 필요 없습니다.
                    """
                    
                    try:
                        # 위에서 정의한 url과 headers 사용
                        data = {"contents": [{"parts": [{"text": st.session_state['lifetime_script'] + "\n" + chat_prompt}]}]}
                        response = requests.post(url, headers=headers, json=data)
                        if response.status_code == 200:
                            ai_reply = response.json()['candidates'][0]['content']['parts'][0]['text']
                            st.session_state['chat_history'].append({"role": "assistant", "content": ai_reply})
                            with st.chat_message("assistant"):
                                st.write(ai_reply)
                    except Exception as e:
                        st.error(f"채팅 오류: {e}")