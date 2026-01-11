import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime
from saju_logic import analyze_user, login_user, save_consultation, get_my_consultation_history, check_and_init_db, get_monthly_ganji

# --- 설정 ---
st.set_page_config(page_title="천기통달 VIP 정밀 분석", layout="wide")
check_and_init_db()

try: FIXED_API_KEY = st.secrets["GEMINI_API_KEY"]
except: FIXED_API_KEY = "여기에_API_키를_붙여넣으세요"

# --- 세션 초기화 ---
for k in ['chat_history', 'chat_input_manual']:
    if k not in st.session_state: st.session_state[k] = [] if k == 'chat_history' else None
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
        
        if st.button("천기통달 정밀 분석 (Enter)", type="primary"):
            st.session_state['run_analysis'] = True
            st.session_state['chat_history'] = [] 
            st.session_state.pop('lifetime_script', None)

        st.divider()
        st.markdown("### ⚡ 정밀 분석 숏컷")
        keywords = ["💰 재물/사업운 (원국+대운)", "🏠 부동산/매매운", "❤️ 배우자/궁합 (합충분석)", "💊 건강/수술수 (장기분석)", "⚖️ 관재구설/소송", "🎓 자녀/진로/학업", "✈️ 이동/이사/해외", "🏢 직장/승진/이직"]
        
        for kw in keywords:
            if st.button(kw):
                st.session_state['chat_input_manual'] = kw + "에 대해 사주 원국의 구조(합충형파)와 대운의 흐름을 기술적으로 분석해서 답해줘."
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
                try:
                    monthly_data = get_monthly_ganji(now.year, now.month)
                    ganji_info = f"{now.year}년(세운): {monthly_data['year_ganji']}, {now.month}월(월운): {monthly_data['month_ganji']}" if monthly_data else f"{now.year}년 {now.month}월"
                except: ganji_info = f"{now.year}년 {now.month}월"

                # ★★★ [최종 수정] 논리적 인과관계 강제 주입 프롬프트 ★★★
                system_instruction = f"""
                [역할] 대한민국 상위 0.1% 정통 명리학자. (무당 아님, 논리로 승부함)
                [대상] {name} ({gender}, 만 {2025 - birth_date.year}세)
                [명식] {result['사주']}
                [대운] {result['대운']} (한국 나이 대운수)
                [현재] {ganji_info}
                
                [★ 분석 절대 원칙: 논리가 없으면 가짜다 ★]
                1. **근거 없는 주장 금지:** "재물운이 나쁘다"고 하지 말고, "일지 오화(午火) 편재가 월지 자수(子水)와 **자오충(子午沖)**을 하여 재물 창고가 깨졌다"라고 **기술적 근거**를 대라.
                2. **연쇄 작용 분석:**
                   - [현상] 자오충 발생 -> [1차 결과] 배우자와 불화 -> [2차 결과] 이혼 위기 -> [3차 결과] 위자료로 재산 손실.
                   - 이렇게 꼬리에 꼬리를 무는 디테일을 서술하라.
                3. **상반된 해석 금지:** 겨울생(자월)에게 물(수)이 들어오면 무조건 흉하다. "공부 잘했다"고 포장하지 마라.
                4. **분량:** A4 3장 이상. 짧으면 오류로 간주함.

                [★ 13단계 정밀 분석 보고서 목차 ★]
                1. **[총론] 오행의 득실과 조후:**
                   - 어느 오행이 과다한지, 조후(계절)는 맞는지 분석하고, 그게 성격/건강/사회성에 미치는 영향 서술.
                2. **[초년운] 부모 및 학업 정밀 검증:**
                   - 초년 대운의 희기(喜忌)를 따져 집안 형편과 학업 성취도 팩트 체크.
                3. **[심리] 지장간 및 12운성:**
                   - 겉마음(천간)과 속마음(지장간)의 괴리, 12운성 에너지의 강약 분석.
                4. **★ [핵심] 형충파해와 공망 분석:**
                   - 사주 내의 합(合), 충(沖), 형(刑) 관계를 낱낱이 파헤쳐라. (특히 일지와의 관계 필수)
                5. **[신살] 12신살 및 기타 신살 전수조사:**
                   - 백호, 양인, 괴강, 도화, 현침 등 있는 대로 다 찾아서 구체적 물상(피, 수술, 이성)으로 통변하라.
                6. **[건강] 오행 불균형에 따른 질병 예언:**
                   - 극(剋)을 받는 오행에 해당하는 장기 지목 및 발병 시기 경고.
                7. **[직업] 사회적 성취와 적성:**
                   - 사업가형(식상생재)인지 직장형(관인상생)인지 판별하고, 흉한 경우(상관견관 등) 경고.
                8. **[용신] 억부와 조후를 고려한 희기신 판단:**
                   - 자월생 -> 화(火) 용신. (이 원칙 준수)
                9. **[자미두수] 명반 크로스체크**
                10. **★ [평생 대운] 10년 단위 정밀 타격 (가장 중요):**
                    - 1대운부터 말년 대운까지, 각 대운의 간지가 원국과 어떻게 반응하여 무슨 일이 생기는지 **매 대운마다** 상세 서술.
                11. **★ [미래 예측] 노년의 삶:** 60대 이후의 길흉화복.
                12. **★ [현재 운세] {ganji_info} 분석:**
                    - 올해와 이달의 글자가 사주에 미치는 당장의 영향.
                13. **[결론] 종합 조언 및 개운법**

                [작성 스타일]
                - **[① 🔎 기술적 분석]**: 명리학 용어(자오충, 상관견관 등)를 사용하여 전문가처럼 분석.
                - **[② 🗣️ 통변(해석)]**: 일반인이 이해하기 쉽게 직설적으로 풀이. (긍정/부정 명확히)
                """
                
                with st.spinner("사주의 뼈대와 혈관까지 정밀 해부 중입니다... (심층 분석)"):
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
                elif u_in := st.chat_input("질문을 입력하세요..."):
                    prompt = u_in
                
                if prompt:
                    st.session_state['chat_history'].append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.write(prompt)
                    
                    chat_ctx = f"{st.session_state['lifetime_script']}\n\n[이전 대화]\n"
                    for m in st.session_state['chat_history'][:-1]:
                        chat_ctx += f"{m['role']}: {m['content']}\n"
                    chat_ctx += f"\n[현재 질문] {prompt}\n"
                    chat_ctx += """
                    [지침]
                    1. 질문에 대해 "사주 용어(근거)"를 대고 설명하라.
                    2. "왜냐하면 일지 오화가 자수와 충돌하기 때문입니다" 같은 식의 인과관계를 필수 포함하라.
                    3. 빈약한 답변 금지.
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