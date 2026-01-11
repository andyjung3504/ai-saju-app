import sqlite3
import pandas as pd
import streamlit as st # 에러 출력을 위해 추가
import os

# 60갑자 리스트
GANJI_60 = [
    '甲子', '乙丑', '丙寅', '丁卯', '戊辰', '己巳', '庚午', '辛未', '壬申', '癸酉',
    '甲戌', '乙亥', '丙子', '丁丑', '戊寅', '己卯', '庚辰', '辛巳', '壬午', '癸未',
    '甲申', '乙酉', '丙戌', '丁亥', '戊子', '己丑', '庚寅', '辛卯', '壬辰', '癸巳',
    '甲午', '乙未', '丙申', '丁酉', '戊戌', '己亥', '庚子', '辛丑', '壬寅', '癸卯',
    '甲辰', '乙巳', '丙午', '丁未', '戊申', '己酉', '庚戌', '辛亥', '壬子', '癸丑',
    '甲寅', '乙卯', '丙辰', '丁巳', '戊午', '己未', '庚申', '辛酉', '壬戌', '癸亥'
]

BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

def get_db_path():
    # saju.db 파일 경로 확인
    if os.path.exists('saju.db'):
        return 'saju.db'
    else:
        # 파일이 없으면 경고
        return None

def get_db_data(year, month, day, is_lunar=False):
    db_path = get_db_path()
    if not db_path:
        return None # 파일이 없으면 데이터 조회 불가
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        final_result = None
        
        if is_lunar:
            # 음력 검색
            cursor.execute(f"SELECT cd_lm, cd_ld, cd_hyganjee, cd_kyganjee, cd_dyganjee, cd_sy, cd_sm, cd_sd FROM calenda_data WHERE (cd_sy={year} OR cd_sy={year+1}) AND cd_lm={month} AND cd_ld={day}")
            rows = cursor.fetchall()
            if not rows: 
                conn.close()
                return None
            target_ganji = GANJI_60[(year - 4) % 60]
            for row in rows:
                if row[2] == target_ganji:
                    final_result = row
                    break
            if not final_result: final_result = rows[0]
        else:
            # 양력 검색
            cursor.execute(f"SELECT cd_lm, cd_ld, cd_hyganjee, cd_kyganjee, cd_dyganjee, cd_sy, cd_sm, cd_sd FROM calenda_data WHERE cd_sy={year} AND cd_sm={month} AND cd_sd={day}")
            final_result = cursor.fetchone()
            
        conn.close()
        return final_result
    except Exception as e:
        # DB 조회 중 에러 발생 시 (테이블 없음 등)
        return None

def calculate_time_pillar(day_stem, hour):
    time_idx = (hour + 1) // 2 
    if time_idx >= 12: time_idx = 0 
    time_branch = BRANCHES[time_idx] 
    stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    if day_stem not in stems: return "??", time_idx
    day_idx = stems.index(day_stem)
    start_stem_idx = (day_idx % 5) * 2
    time_stem_idx = (start_stem_idx + time_idx) % 10
    return stems[time_stem_idx] + time_branch, time_idx

def get_jami_data(lunar_month, time_idx, year_stem, lunar_day):
    myung_idx = (2 + (lunar_month - 1) - time_idx) % 12
    myung_gung = BRANCHES[myung_idx]
    stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    try: y_idx = stems.index(year_stem)
    except: y_idx = 0
    start = (y_idx % 5) * 2 + 2 
    off = myung_idx - 2
    if off < 0: off += 12
    m_stem = (start + off) % 10
    code = (m_stem // 2 + myung_idx // 2) % 5
    guk_map = {0: 4, 1: 2, 2: 6, 3: 5, 4: 3}
    guk = guk_map[code]
    ziwei_idx = (lunar_day + guk) % 12 
    stars = {'자미': ziwei_idx, '천부': (10 - ziwei_idx) % 12, '태양': (ziwei_idx - 3) % 12, '무곡': (ziwei_idx - 4) % 12, '천동': (ziwei_idx - 5) % 12, '염정': (ziwei_idx - 8) % 12, '천기': (ziwei_idx - 1) % 12, '태음': (10 - ziwei_idx + 1) % 12, '탐랑': (10 - ziwei_idx + 2) % 12, '거문': (10 - ziwei_idx + 3) % 12, '천상': (10 - ziwei_idx + 4) % 12, '천량': (10 - ziwei_idx + 5) % 12, '칠살': (10 - ziwei_idx + 6) % 12, '파군': (10 - ziwei_idx + 10) % 12}
    my_stars = [s for s, i in stars.items() if BRANCHES[i] == myung_gung]
    if not my_stars: return myung_gung, "명무정요"
    return myung_gung, ", ".join(my_stars)

def calculate_daewoon(gender, year_pillar, month_pillar, day_pillar, birth_date):
    yang_stems = ['甲', '丙', '戊', '庚', '壬']
    year_stem = year_pillar[0]
    is_year_yang = year_stem in yang_stems
    is_man = (gender == '남성')
    direction = 1 if (is_man and is_year_yang) or (not is_man and not is_year_yang) else -1
    daewoon_su = 6 
    try: start_idx = GANJI_60.index(month_pillar)
    except: return [] 
    daewoon_list = []
    for i in range(1, 9): 
        idx = (start_idx + (i * direction)) % 60
        ganji = GANJI_60[idx]
        start_age = daewoon_su + ((i-1) * 10)
        daewoon_list.append(f"{start_age}({ganji})")
    return daewoon_list

def analyze_user(year, month, day, hour, is_lunar=False, gender='남성'):
    db_data = get_db_data(year, month, day, is_lunar)
    if not db_data: 
        # DB 파일은 있는데 해당 날짜가 없는 경우 vs DB 파일 자체가 없는 경우
        if not get_db_path():
            return {"error": "saju.db 파일이 서버에 없습니다. 깃허브에 업로드해주세요."}
        return {"error": "만세력 데이터에 해당 날짜가 없습니다."}
    
    try:
        lunar_month, lunar_day = int(db_data[0]), int(db_data[1])
        year_p, month_p, day_p = db_data[2], db_data[3], db_data[4]
    except: return {"error": "데이터 파싱 오류"}
        
    time_p, time_idx = calculate_time_pillar(day_p[0], hour)
    myung_loc, myung_star = get_jami_data(lunar_month, time_idx, year_p[0], lunar_day)
    daewoon = calculate_daewoon(gender, year_p, month_p, day_p, day)
    
    return {
        "입력기준": "음력" if is_lunar else "양력",
        "음력": f"{lunar_month}월 {lunar_day}일",
        "사주": [year_p, month_p, day_p, time_p],
        "대운": daewoon,
        "자미두수": {"명궁위치": myung_loc, "명궁주성": myung_star}
    }

# =========================================================
# ★ [안전장치] DB 초기화 (기존 데이터 보존 + 유저 테이블만 추가)
# =========================================================
def check_and_init_db():
    db_path = 'saju.db'
    # DB 파일이 없으면 어쩔 수 없이 에러를 피하기 위해 생성은 하되, 만세력 데이터는 없는 상태가 됨
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. users 테이블이 없으면 생성 (만세력 테이블인 calenda_data는 건드리지 않음)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY, 
                password TEXT NOT NULL, 
                name TEXT
            )
        ''')
        
        # 2. consultations 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consultations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                counselor_id TEXT, 
                client_name TEXT, 
                client_gender TEXT, 
                birth_date TEXT, 
                birth_time TEXT, 
                consult_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                memo TEXT, 
                FOREIGN KEY (counselor_id) REFERENCES users (username)
            )
        ''')

        # 3. 기본 계정 확인 (없으면 추가)
        cursor.execute("SELECT count(*) FROM users WHERE username='test1'")
        if cursor.fetchone()[0] == 0:
            users = [('test1', '1234', '상담원1'), ('test2', '1234', '상담원2')]
            cursor.executemany('INSERT INTO users (username, password, name) VALUES (?, ?, ?)', users)
            
        conn.commit()
    except Exception as e:
        # 여기서 에러가 나면 화면에 출력해서 원인을 알려줌
        st.error(f"DB 초기화 중 오류 발생: {e}")
    finally:
        conn.close()

def login_user(username, password):
    check_and_init_db() 
    conn = sqlite3.connect('saju.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM users WHERE username=? AND password=?", (username, password))
        result = cursor.fetchone()
        return result[0] if result else None
    except: return None
    finally: conn.close()

def save_consultation(counselor_id, client_name, gender, b_date, b_time, memo=""):
    check_and_init_db()
    conn = sqlite3.connect('saju.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO consultations (counselor_id, client_name, client_gender, birth_date, birth_time, memo) VALUES (?, ?, ?, ?, ?, ?)", (counselor_id, client_name, gender, str(b_date), str(b_time), memo))
        conn.commit()
        return True
    except: return False
    finally: conn.close()

def get_my_consultation_history(counselor_id):
    check_and_init_db()
    conn = sqlite3.connect('saju.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT client_name, client_gender, birth_date, consult_date FROM consultations WHERE counselor_id=? ORDER BY consult_date DESC LIMIT 10", (counselor_id,))
        rows = cursor.fetchall()
        return rows
    except: return []
    finally: conn.close()

def get_monthly_ganji(year, month):
    db_path = get_db_path()
    if not db_path: return None
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # 15일 기준 조회
        cursor.execute(f"SELECT cd_hyganjee, cd_kyganjee FROM calenda_data WHERE cd_sy={year} AND cd_sm={month} AND cd_sd=15")
        result = cursor.fetchone()
        if result: return {"year_ganji": result[0], "month_ganji": result[1]}
        else: return None
    except: return None
    finally: conn.close()
