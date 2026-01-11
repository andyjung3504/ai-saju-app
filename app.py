import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime, timedelta
# saju_logic 모듈 함수 로드
from saju_logic import analyze_user, login_user, save_consultation, get_monthly_ganji, get_db_data, check_and_init_db

# --- 설정 ---
st.set_page_config(page_title="천기통달: 명리학 마스터", layout="wide")

# DB 안전장치 가동
check_and_init_db()

try: FIXED_API_KEY = st.secrets["GEMINI_API_KEY"]
except: FIXED_API_KEY = "여기에_API_키를_붙여넣으세요"

# --- 세션 초기화 ---
for k in ['chat_history', 'chat_input_manual']:
    if k not in st.session_state: st.session_state[k] = [] if k == 'chat_history' else None
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_name' not in st.session_state: st.session_state['user_name'] = ""
if 'run_analysis' not in st.session_state: st.session_state['run_analysis'] = False
if 'analysis_mode' not in st.session_state: st.session_state['analysis_mode'] = "lifetime"

# ==============================================================================
# [기능 1] 2026년 길일/흉일 정밀 산출 (합,충,형,해,공망,귀인 전체 고려) - 유지됨
# ==============================================================================
def find_best_worst_days_2026(user_day_stem, user_day_branch):
    """
    내담자의 일주(Day Pillar)를 기준으로 2026년 365일을 전수 조사하여
    길일(천을귀인, 육합)과 흉일(충, 형, 해, 공망)을 월별로 안배하여 추출한다.
    """
    branches = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    nobleman_map = {'甲': ['丑', '未'], '戊': ['丑', '未'], '庚': ['丑', '未'], '乙': ['子', '申'], '己': ['子', '申'], '丙': ['亥', '酉'], '丁': ['亥', '酉'], '壬': ['巳', '卯'], '癸': ['巳', '卯'], '辛': ['午', '寅']}
    yuk_hap_map = {'子': '丑', '丑': '子', '寅': '亥', '亥': '寅', '卯': '戌', '戌': '卯', '辰': '酉', '酉': '辰', '巳': '申', '申': '巳', '午': '未', '未': '午'}
    
    my_branch_idx = branches.index(user_day_branch)
    chung_branch = branches[(my_branch_idx + 6) % 12]
    
    yuk_hai_map = {'子': '未', '丑': '午', '寅': '巳', '巳': '寅', '卯': '辰', '辰': '卯', '申': '亥', '亥': '申', '酉': '戌', '戌': '酉', '午': '丑', '未': '子'}
    xing_map = {'寅': ['巳', '申'], '巳': ['寅', '申'], '申': ['寅', '巳'], '丑': ['戌', '未'], '戌': ['丑', '未'], '未': ['丑', '戌'], '子': ['卯'], '卯': ['子'], '辰': ['辰'], '午': ['午'], '酉': ['酉'], '亥': ['亥']}
    
    stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    stem_idx = stems.index(user_day_stem)
    branch_idx = branches.index(user_day_branch)
    diff = (branch_idx - stem_idx)
    if diff < 0: diff += 12
    gongmang_table = {10: ['戌', '亥'], 8: ['申', '酉'], 6: ['午', '未'], 4: ['辰', '巳'], 2: ['寅', '卯'], 0: ['子', '丑']}
    my_gongmang = gongmang_table.get(diff, [])

    found_good = []
    found_bad = []
    
    start_date = datetime(2026, 1, 1)
    for i in range(365): 
        curr = start_date + timedelta(days=i)
        row = get_db_data(curr.year, curr.month, curr.day, False)
        
        if row:
            day_ganji = row[4] 
            day_branch = day_ganji[1]
            date_str = curr.strftime("%m월 %d일")
            
            # 길일
            is_good = False
            reasons_good = []
            if day_branch in nobleman_map.get(user_day_stem, []): reasons_good.append("천을귀인")
            if yuk_hap_map.get(user_day_branch) == day_branch: reasons_good.append("육합")
            if reasons_good: found_good.append(f"{date_str}({day_ganji}: {','.join(reasons_good)})")

            # 흉일
            is_bad = False
            reasons_bad = []
            if day_branch == chung_branch: reasons_bad.append("충")
            if day_branch in my_gongmang: reasons_bad.append("공망")
            if yuk_hai_map.get(user_day_branch) == day_branch: reasons_bad.append("육해")
            if day_branch in xing_map.get(user_day_branch, []): reasons_bad.append("형살")
            if reasons_bad: found_bad.append(f"{date_str}({day_ganji}: {','.join(reasons_bad)})")

    def sample_dates(date_list, count=12):
        if not date_list: return []
        if len(date_list) <= count: return date_list
        step = len(date_list) // count
        return [date_list[i] for i in range(0, len(date_list), step)][:count]

    final_good = sample_dates(found_good, 10)
    final_bad = sample_dates(found_bad, 10)
            
    return final_good, final_bad

# ==============================================================================
# [기능 2] 질문 내 날짜 파싱 -> DB 데이터 매핑 (★이부분 강력 수정됨★)
# ==============================================================================
def get_db_ganji_for_query(query_text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={FIXED_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    now = datetime.now()
    
    # 1. 날짜 추출
    prompt = f"""
    Current Time: {now.strftime('%Y-%m-%d %H:%M:%S')}
    Task: Extract target date from: "{query_text}"
    - If user says "tomorrow", "Jan 12", etc., calculate exact YYYY-MM-DD.
    - Return JSON: {{"year": 2026, "month": 1, "day": 12, "hour": 14}}
    """
    try:
        r = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": prompt}]}]})
        res_json = json.loads(r.json()['candidates'][0]['content']['parts'][0]['text'].replace("```json", "").replace("```", "").strip())
        t_y, t_m, t_d, t_h = res_json['year'], res_json['month'], res_json['day'], res_json.get('hour', 12)
        
        # 2. DB에서 해당 날짜의 간지 직접 조회
        db_data = analyze_user(t_y, t_m, t_d, t_h, False, "남성") 
        
        if "error" in db_data:
            return f"[시스템 오류] DB에 해당 날짜({t_y}-{t_m}-{t_d}) 데이터가 없습니다."

        ganji_info = db_data['사주'] # [년주, 월주, 일주, 시주]
        
        # 3. AI에게 먹일 강력한 프롬프트 리턴 (날짜 환각 방지)
        return f"""
        [★ SYSTEM FORCED DATA: DB 만세력 정답지]
        - 질문 대상 날짜: {t_y}년 {t_m}월 {t_d}일
        - **DB 확정 간지**: 년({ganji_info[0]}), 월({ganji_info[1]}), 일({ganji_info[2]})
        - 경고: 네가 계산한 날짜나 간지는 모두 틀렸다. 무조건 위 'DB 확정 간지'인 '{ganji_info[2]}' 일주를 기준으로 답하라.
        """
    except Exception as e:
        return f"[시스템] 날짜 파싱 실패 ({e}). 현재 시간 기준으로 분석합니다."

# ==============================================================================
# [기능 3] 타인 사주 조회 (유지)
#