import streamlit as st
import pandas as pd
import requests
import json
import time
from saju_logic import analyze_user, login_user, save_consultation, get_my_consultation_history, check_and_init_db

# --- [설정] 페이지 기본 설정 ---
st.set_page_config(page_title="천기통달 상담 시스템", layout="wide")

# ★ DB 자동 점검 및 생성
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
            st.caption("이력 없음")

        st.divider()
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
                
                # ★★★ [수정됨] 상담원 전용: 원문 + 비유 프롬프트 ★★★
                system_instruction = f"""
                [역할] 당신은 대한민국 최고의 역술가이자, 30대 전문 상담원들을 위한 '상담 스크립트 라이터'입니다.
                
                [분석 대상]
                - 이름: {name} ({gender}, 현재 약 {2025 - birth_date.year}세)
                - 명식: {result['사주']}
                - ★대운 흐름: {result['대운']}
                - ★자미두수: {result['자미두수']['명궁위치']} ({result['자미두수']['명궁주성']})
                
                [★ 작성 절대 원칙 (매우 중요) ★]
                1. 모든 항목은 **[① 전문 분석]**과 **[② 💡상담용 핵심 비유]** 두 파트로 나눠서 작성하십시오.
                2. **전문 분석:** 한자 용어(십성, 신살 등)를 정확히 사용하여 냉철하게 분석하십시오.
                3. **상담용 비유:** 상담원이 고객에게 바로 읽어줄 수 있도록, 쉬운 단어와 '찰떡같은 비유'를 사용하여 설명하십시오.
                   (예: "재성이 충을 맞았습니다" -> "지갑에 구멍이 난 형국이라 돈이 들어오자마자 나갑니다.")
                4. 말투: 전문적이면서도 세련된 '브리핑 톤'을 유지하십시오. (반말 금지, 과한 격식 금지)
                
                [★ 13단계 분석 순서 ★]
                1. **원국 기본 분석 (성격/기질)**
                   - 각 기둥의 십성을 분석하고, 이를 **자연물(나무, 불, 바위 등)**에 비유하여 묘사하십시오.
                
                2. **지장간/12운성/12신살 (속마음/에너지)**
                   - 겉마음과 속마음의 차이를 분석하고, 12운성 에너지를 **'사람의 일생'**이나 **'계절'**에 비유하십시오.
                
                3. **형충파해/공망 (인생의 지뢰밭)**
                   - 충/형/원진을 찾고, 공망(空亡)을 **"구멍 난 독"**이나 **"헛발질"** 등으로 비유하여 경고하십시오.
                
                4. **길성/흉신 (보너스와 벌칙)**
                   - 귀인과 흉살(백호, 양인 등)을 찾아 **"브레이크 없는 스포츠카"** 등의 비유로 설명하십시오.
                
                5. **오행 세력 (건강/적성)**
                   - 오행의 과다/결핍을 분석하고, 이를 통해 **건강**과 **성격의 단점**을 지적하십시오.
                
                6. **용신 정밀 타격 (해결사)**
                   - 인생을 풀리게 하는 글자(용신)를 **"한겨울의 난로"**나 **"가뭄의 단비"**처럼 표현하십시오.
                
                7. **격국과 조후 (그릇의 크기)**
                
                8. **특수격국 및 진가신살**
                
                9. **★ 자미두수 별의 계시 (필수)**
                   - 명궁 주성({result['자미두수']['명궁주성']})을 해석하고, 사주와의 차이점을 설명하십시오.
                   - **비유:** "사주는 겉모습이고 자미두수는 X-ray 찍은 속마음입니다."
                
                10. **★ 대운(Great Luck) 과거 검증 (신뢰 확보 구간) ★**
                    - **절대 나열 금지.** - 고객의 과거(10대~40대) 대운을 찾아, **"지난 XX대운은 사주의 OO와 충돌하여, 마치 '달리는 차가 가로수를 들이받은 격'이라 직장/가정 문제로 죽을 만큼 힘들었을 것입니다"**라고 구체적으로 서술하십시오.
                
                11. **세운(歲運) 및 미래 예측**
                    - 올해와 내년의 운세를 **날씨(비 갠 뒤 맑음 등)**에 비유하여 설명하십시오.
                
                12. **물상론 (한 폭의 그림)**
                    - 사주 전체를 한 폭의 풍경화로 묘사하십시오.
                
                13. **종합 총평 및 현실적 개운법**
                    - 색깔, 숫자, 방향, 마음가짐 등 당장 실천할 수 있는 행동 지침을 제시하십시오.
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
                    st.error(f"시스템 오류: {e}")

            if 'lifetime_script' in st.session_state:
                st.markdown("### 📜 천기통달 심층 정밀 감정서")
                st.write(st.session_state['lifetime_script'])
                
                st.divider()
                
                st.subheader("💬 심층 질의응답 (무엇이든 물어보세요)")
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
                    지침: 상담원이 고객에게 말하듯이, 전문 용어와 쉬운 비유를 섞어서 명쾌하게 답변하십시오.
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