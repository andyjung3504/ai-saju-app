import streamlit as st
import pandas as pd
import requests
import json
import time
import re
from datetime import datetime
from saju_logic import analyze_user, login_user, save_consultation, get_my_consultation_history, check_and_init_db, get_monthly_ganji

# --- 설정 ---
st.set_page_config(page_title="천기통달 VIP 정밀 상담", layout="wide")
check_and_init_db()

try: FIXED_API_KEY = st.secrets["GEMINI_API_KEY"]
except: FIXED_API_KEY = "여기에_API_키를_붙여넣으세요"

# --- 세션 초기화 ---
for k in ['chat_history', 'chat_input_manual']:
    if k not in st.session_state: st.session_state[k] = [] if k == 'chat_history' else None
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_name' not in st.session_state: st.session_state['user_name'] = ""
if 'run_analysis' not in st.session_state: st.session_state['run_analysis'] = False

# ==============================================================================
# [기능 1] 채팅창 날짜 감지 -> DB 조회 -> 타인 사주 분석
# ==============================================================================
def extract_and_analyze_target(text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={FIXED_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    prompt = f"""
    Analyze this text: "{text}"
    If there is a birth date, extract it.
    Return ONLY a JSON object: {{"found": true, "year": 1964, "month": 6, "day": 30, "lunar": true, "gender": "여성"}}
    - "음력" word exists -> lunar: true
    - "여자", "녀", "아내" -> gender: "여성" / else "남성"
    - If year is 2 digits (64), add 1900.
    - If no date found, return {{"found": false}}
    """
    try:
        r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": prompt}]}]})
        res_json = json.loads(r.json()['candidates'][0]['content']['parts'][0]['text'].replace("```json", "").replace("```", "").strip())
        if res_json.get("found"):
            y, m, d = res_json['year'], res_json['month'], res_json['day']
            is_lunar = res_json['lunar']
            gender = res_json['gender']
            target_res = analyze_user(y, m, d, 0, is_lunar, gender)
            if "error" in target_res: return f"\n[시스템] 상대방 DB 조회 실패: {target_res['error']}"
            return f"""
            \n[★ 상대방 사주 DB 조회 결과]
            - 정보: {y}년 {m}월 {d}일 ({'음력' if is_lunar else '양력'}) / {gender}
            - 사주: {target_res['사주']} / 대운: {target_res['대운']}
            - 지침: 내 사주와 상대방의 합(合), 충(沖), 원진(元嗔)을 분석하여 궁합 및 거래 길흉을 판단하라.
            """
        else: return ""
    except: return ""

# [기능 2] 1년치 월운 전수조사
def get_yearly_detailed_flow(year):
    flow_text = f"\n[★ {year}년 월별 운세 DB 데이터]\n"
    try:
        for m in range(1, 13):
            data = get_monthly_ganji(year, m)
            if data: flow_text += f"- {m}월: {data['month_ganji']} (세운 {data['year_ganji']}과 작용)\n"
        return flow_text
    except: return ""

# ==========================================
# 메인 UI
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

else:
    with st.sidebar:
        st.info(f"👤 상담원: {st.session_state['user_name']}")
        if st.button("로그아웃"):
            st.session_state['logged_in'] = False
            st.session_state.clear()
            st.rerun()
        st.divider()

        st.header("📝 본인 명조")
        name = st.text_input("고객명", value="홍길동")
        gender = st.radio("성별", ["남성", "여성"], horizontal=True)
        calendar_type = st.radio("달력", ["양력", "음력"], horizontal=True)
        is_lunar = (calendar_type == "음력")
        
        c1, c2 = st.columns(2)
        with c1: birth_date = st.date_input("생년월일", value=pd.to_datetime("1980-01-01"), min_value=pd.to_datetime("1900-01-01"))
        with c2: birth_time = st.time_input("태어난 시간", value=pd.to_datetime("14:30").time())
        
        if st.button("천기통달 정밀 분석", type="primary"):
            st.session_state['run_analysis'] = True
            st.session_state['chat_history'] = [] 
            st.session_state.pop('lifetime_script', None)

        st.divider()
        st.markdown("### ⚡ 정밀 분석 숏컷")
        keywords = ["💰 재물/사업운 (원국+대운)", "🏠 부동산/매매운", "❤️ 배우자/궁합 (합충분석)", "💊 건강/수술수 (장기분석)", "⚖️ 관재구설/소송", "🎓 자녀/진로/학업", "✈️ 이동/이사/해외", "🏢 직장/승진/이직"]
        
        for kw in keywords:
            if st.button(kw):
                st.session_state['chat_input_manual'] = kw + "에 대해 사주 원국과 대운을 대조하고, 신살(길신/흉신)의 작용까지 포함해 정밀 분석해줘."
                if not st.session_state['run_analysis']:
                    st.session_state['run_analysis'] = True
                    st.session_state['chat_history'] = []
                st.rerun()

    st.title("🔮 AI 천기통달 VIP 정밀 상담 (전문가용)")

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
                        save_consultation(st.session_state['user_id'], name, gender, birth_date, birth_time, memo="정밀 분석")
                        st.toast("저장 완료")

            if 'lifetime_script' not in st.session_state:
                now = datetime.now()
                yearly_data = get_yearly_detailed_flow(now.year)
                try:
                    monthly_data = get_monthly_ganji(now.year, now.month)
                    ganji_info = f"{now.year}년(세운): {monthly_data['year_ganji']}, {now.month}월(월운): {monthly_data['month_ganji']}" if monthly_data else f"{now.year}년 {now.month}월"
                except: ganji_info = f"{now.year}년 {now.month}월"

                # ★★★ [최종 완결] 길신/흉신 전수조사 및 인과관계 강제 프롬프트 ★★★
                system_instruction = f"""
                [역할] 대한민국 상위 0.1% 정통 명리학자. (논리와 팩트 중심)
                [대상] {name} ({gender}, 만 {2025 - birth_date.year}세)
                [명식] {result['사주']}
                [대운] {result['대운']} (한국 나이 대운수)
                [현재] {ganji_info}
                [올해 월운] {yearly_data}

                [★ 분석 절대 원칙: 100만원의 가치 ★]
                1. **신살(神殺) 정밀 전수조사 (가장 중요):**
                   - 나쁜 것만 찾지 말고 **좋은 신살(길신)**도 샅샅이 찾아라.
                   - **[필수 체크 길신]:** 천을귀인(최고의 길신), 천덕/월덕귀인(재앙 해소), 문창귀인(지능), 반안살(승진/안정), 장성살(리더십).
                   - **[필수 체크 흉신]:** 백호, 괴강, 양인, 현침, 도화, 원진, 귀문.
                   - **분석 방법:** "흉신이 있어서 위험하지만, 천을귀인이 있어서 구제된다" 혹은 "좋은 게 하나도 없어 위험하다" 식으로 **길흉의 밸런스**를 맞춰라.
                2. **대운 논리:** 기신운엔 "망했다", 용신운엔 "흥했다" 명확히 구분.
                3. **직업/적성:** "상관"이나 "충"이 있으면 직장 부적합. 사업/전문직 추천.
                4. **분량:** A4 3장 이상.

                [★ 13단계 정밀 분석 보고서 ★]
                1. **오행 총론:** 기질이 돈과 건강에 미치는 영향.
                2. **부모/초년운:** 초년 대운의 길흉에 따른 팩트(가난/유복).
                3. **심리 분석:** 겉과 속의 괴리(지장간).
                4. **형충파해/공망:** 자오충 등 깨진 글자의 현실적 피해.
                5. **★ 신살(神殺) 대해부 (길신 vs 흉신):**
                   - **[길신(Good)]:** 나를 지켜주는 무기(천을, 문창 등)가 무엇인지, 어떻게 써먹어야 하는지.
                   - **[흉신(Bad)]:** 나를 해치는 흉기가 무엇인지, 언제 발동하는지 경고.
                6. **건강 정밀 진단:** 수술수 및 취약 장기.
                7. **직업 적성:** "남 밑에 못 있는 사주"인지 판별.
                8. **용신/기신 정밀 판단:** (조후 우선 - 겨울생 화 용신)
                9. **자미두수 크로스체크**
                10. **★ 평생 대운 정밀 해부:** 10년 단위로 사건(합격, 이별, 대박) 서술.
                11. **미래 예언:** 노년의 삶.
                12. **★ 올해 월별 정밀 운세:** 1월~12월 흐름.
                13. **종합 총평 및 솔루션**

                [작성 형식]
                - **[① 🔎 팩트 폭격]**: 신살 명칭과 작용력 상세 기술.
                - **[② 🗣️ 상담 브리핑]**: 직설적이고 명쾌한 설명. (좋은 건 확실히 좋다고 칭찬)
                """
                
                with st.spinner("사주의 '숨겨진 보물(길신)'과 '지뢰(흉신)'를 전수조사 중입니다..."):
                    try:
                        r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": system_instruction}]}]})
                        st.session_state['lifetime_script'] = r.json()['candidates'][0]['content']['parts'][0]['text']
                    except Exception as e: st.error(f"오류: {e}")

            if 'lifetime_script' in st.session_state:
                st.markdown(st.session_state['lifetime_script'])
                st.divider()
                
                st.subheader("💬 심층 정밀 상담")
                for msg in st.session_state['chat_history']:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
                
                prompt = None
                if st.session_state['chat_input_manual']:
                    prompt = st.session_state['chat_input_manual']
                    st.session_state['chat_input_manual'] = None
                elif u_in := st.chat_input("질문을 입력하세요... (예: 64년 6월 30일생 여자 돈 빌려줘?)"):
                    prompt = u_in
                
                if prompt:
                    st.session_state['chat_history'].append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.write(prompt)
                    
                    # 타인 사주 조회
                    target_info = extract_and_analyze_target(prompt)
                    
                    chat_ctx = f"{st.session_state['lifetime_script']}\n\n[이전 대화]\n"
                    for m in st.session_state['chat_history'][:-1]:
                        chat_ctx += f"{m['role']}: {m['content']}\n"
                    
                    if target_info: chat_ctx += target_info
                    
                    chat_ctx += f"\n[현재 질문] {prompt}\n"
                    chat_ctx += """
                    [지침]
                    1. 질문에 타인 정보가 있으면 궁합/원진/겁재 여부를 보고 돈 거래 위험성을 경고하라.
                    2. **신살(길신/흉신)을 모두 고려**하여 답변하라. (예: 귀인이 있어서 해결된다 등)
                    3. 긍정은 확실히, 부정은 강하게.
                    """
                    
                    with st.spinner("정밀 분석 중..."):
                        try:
                            r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": chat_ctx}]}]})
                            ai_msg = r.json()['candidates'][0]['content']['parts'][0]['text']
                            st.session_state['chat_history'].append({"role": "assistant", "content": ai_msg})
                            with st.chat_message("assistant"):
                                st.write(ai_msg)
                            st.rerun()
                        except: st.error("답변 실패")