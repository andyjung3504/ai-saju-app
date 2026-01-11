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
if 'run_analysis' not in st.session_state:
    st.session_state['run_analysis'] = False

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
        
        # [2] 키워드 버튼 (상시 노출)
        st.divider()
        st.markdown("### ⚡ 빠른 질문 (단축키)")
        
        keywords = [
            "💰 금전운/재물운", "🏢 사업운/창업운", "🏠 매매운/부동산",
            "❤️ 연애운/부부운", "💊 본인 건강운", "👵 부모님 건강운",
            "💼 직장운/승진운", "🎓 자녀운/합격운", "⚖️ 관재구설/소송",
            "✈️ 이사운/이동운"
        ]
        
        for kw in keywords:
            if st.button(kw):
                st.session_state['chat_input_manual'] = kw + "에 대해 냉정하게 분석해줘. 안 좋은 점 위주로."
                if not st.session_state['run_analysis']:
                    st.session_state['run_analysis'] = True
                    st.session_state.pop('lifetime_script', None)
                    st.session_state['chat_history'] = []

        st.divider()
        st.subheader("📋 최근 상담 이력")
        history = get_my_consultation_history(st.session_state['user_id'])
        if history:
            for h in history:
                st.caption(f"{h[0]}({h[1]}) - {h[3][:10]}")

    # --- 메인 화면 콘텐츠 ---
    st.title("🔮 AI 천기통달 역술 상담 (전문가용)")

    if analyze_btn:
        st.session_state['run_analysis'] = True
        st.session_state['chat_history'] = [] 
        st.session_state.pop('lifetime_script', None)

    if st.session_state['run_analysis']:
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
                        success = save_consultation(st.session_state['user_id'], name, gender, birth_date, birth_time, memo="자동 분석 결과")
                        if success: st.toast("✅ 저장 완료!", icon="💾")
                        else: st.error("저장 실패")

            # 메인 스크립트 생성 (10만원 값어치 하는 독설 프롬프트)
            if 'lifetime_script' not in st.session_state:
                # ★★★ 독설 및 위험 강조 프롬프트 적용 ★★★
                system_instruction = f"""
                [역할] 당신은 1회 상담료 10만 원을 받는 대한민국 상위 1% 역술가이자, '위험 관리 전문가'입니다.
                [대상] {name} ({gender}, {2025 - birth_date.year}세)
                [명식] {result['사주']} / [대운] {result['대운']} / [자미] {result['자미두수']['명궁주성']}
                
                [★ 핵심 지침: 10만 원의 가치를 증명하라 ★]
                1. **냉정함 유지:** 절대 빈말이나 위로를 하지 마십시오. 고객은 '듣기 좋은 소리'가 아니라 **'피해야 할 재앙'**을 듣고 싶어 돈을 냈습니다.
                2. **나쁜 일(흉사) 강조:** 충(沖), 형(刑), 파(破), 해(害), 공망(空亡), 흉신(백호, 양인 등)을 찾아내어 **집요하게 경고**하십시오. (예: "돈 좀 번다고 좋아하지 마라, 건강 잃으면 끝이다.")
                3. **구조:** **[① 팩트 폭격(전문 분석)]**과 **[② 💡상담용 브리핑(비유)]**로 나누되, 비유는 **섬뜩할 정도로 정확하고 직설적**이어야 합니다.
                
                [★ 13단계 정밀 분석 순서 ★]
                1. **원국 기질 분석:** 오행의 편중을 찾아 성격의 결함부터 지적하십시오.
                2. **지장간/12운성:** 겉과 속이 다른 이중성이나, 쇠약한 기운을 찾아내십시오.
                3. **형충파해/공망 (★가장 중요):** 인생의 지뢰밭입니다. 부부궁이 깨졌는지, 재물 창고가 뚫렸는지 적나라하게 밝히십시오.
                4. **흉신/악살:** 백호살, 도화살, 역마살 등이 가져올 **재앙(사고, 이성 문제, 객사 등)**을 경고하십시오.
                5. **오행 건강:** 취약한 장기를 지목하고, 방치하면 어떤 수술을 받게 될지 경고하십시오.
                6. **용신:** 이 사주가 살길은 이것뿐임을 강조하십시오.
                7. **격국:** 그릇의 크기를 냉정하게 평가하십시오.
                8. **특수격/신살**
                9. **★ 자미두수 팩트 체크:** 별자리에서도 흉한 징조가 보이면 사주와 엮어서 "빼도 박도 못한다"고 말하십시오.
                10. **★ 과거 대운 검증 (신뢰도 확보):** 과거의 가장 힘들었던 시기를 찾아, **"지난 XX대운에는 죽고 싶을 만큼 힘들었을 것입니다. (구체적 사건: 돈/이혼/수술)"**라고 단언하십시오.
                11. **세운/미래 예측:** 올해와 내년에 닥칠 위기를 '일기예보'처럼(태풍, 한파) 예고하십시오.
                12. **물상론:** 사주의 형상을 위태로운 풍경(예: 벼랑 끝의 소나무)으로 묘사하십시오.
                13. **종합 총평 및 생존 전략:** "이것 안 고치면 미래 없다"는 식으로 강하게 조언하고 개운법을 제시하십시오.
                """
                
                try:
                    data = {"contents": [{"parts": [{"text": system_instruction}]}]}
                    with st.spinner("천기를 꿰뚫어 '운명의 함정'과 '위험'을 정밀 타격 중입니다..."):
                        response = requests.post(url, headers=headers, json=data)
                        if response.status_code == 200:
                            st.session_state['lifetime_script'] = response.json()['candidates'][0]['content']['parts'][0]['text']
                        else:
                            st.error(f"API 호출 실패: {response.text}")
                except Exception as e:
                    st.error(f"오류: {e}")

            if 'lifetime_script' in st.session_state:
                st.markdown("### 📜 심층 정밀 감정서 (VIP용)")
                st.write(st.session_state['lifetime_script'])
                st.divider()
                
                st.subheader("💬 심층 질의응답 (무엇이든 물어보세요)")
                st.caption("👇 '남편 바람', '부도 위기' 등 민감한 질문을 던져보세요. AI가 냉정하게 답합니다.")

                for msg in st.session_state.get('chat_history', []):
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])

                prompt_text = None
                if st.session_state.get('chat_input_manual'):
                    prompt_text = st.session_state['chat_input_manual']
                    st.session_state['chat_input_manual'] = None 
                elif user_input := st.chat_input("질문 입력"):
                    prompt_text = user_input

                if prompt_text:
                    st.session_state['chat_history'].append({"role": "user", "content": prompt_text})
                    with st.chat_message("user"):
                        st.write(prompt_text)

                    # ★★★ 채팅 프롬프트: 10만원 값어치 하는 독설 ★★★
                    full_context = st.session_state['lifetime_script'] + "\n\n[이전 대화]\n"
                    for msg in st.session_state['chat_history'][:-1]:
                        full_context += f"{msg['role']}: {msg['content']}\n"
                    
                    full_context += f"\n[현재 질문]\nuser: {prompt_text}\n"
                    full_context += """
                    [답변 지침: 10만원짜리 유료 상담]
                    1. 빈말이나 위로는 절대 하지 마십시오.
                    2. 질문에 부정적인 징조(바람, 사고, 손재)가 보이면, **"네, 보입니다. 위험합니다."**라고 확실하게 말하십시오.
                    3. **[① 팩트 폭격]**과 **[② 💡상담용 브리핑]** 형식을 유지하십시오.
                    4. 고객이 방심하지 않도록 강하게 경고하십시오.
                    """

                    try:
                        data = {"contents": [{"parts": [{"text": full_context}]}]}
                        with st.spinner("냉철하게 분석 중..."):
                            response = requests.post(url, headers=headers, json=data)
                            if response.status_code == 200:
                                ai_reply = response.json()['candidates'][0]['content']['parts'][0]['text']
                                st.session_state['chat_history'].append({"role": "assistant", "content": ai_reply})
                                with st.chat_message("assistant"):
                                    st.write(ai_reply)
                    except Exception as e:
                        st.error(f"채팅 오류: {e}")