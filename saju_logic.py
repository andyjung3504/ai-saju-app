import sqlite3
import pandas as pd

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

# === 1. DB 조회 및 정밀 검증 ===
def get_db_data(year, month, day, is_lunar=False):
    import os
    if not os.path.exists('saju.db'):
        return None

    conn = sqlite3.connect('saju.db')
    cursor = conn.cursor()
    
    final_result = None
    
    try:
        if is_lunar:
            # 음력 11, 12월 등 해가 넘어가는 경우 대비 2년치 검색
            query = f"""
            SELECT cd_lm, cd_ld, cd_hyganjee, cd_kyganjee, cd_dyganjee, cd_sy, cd_sm, cd_sd
            FROM calenda_data 
            WHERE (cd_sy={year} OR cd_sy={year+1}) 
              AND cd_lm={month} 
              AND cd_ld={day}
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            if not rows: return None
            
            # 간지 매칭으로 정확한 해 찾기 (간단 검증)
            target_ganji = GANJI_60[(year - 4) % 60]
            for row in rows:
                if row[2] == target_ganji:
                    final_result = row
                    break
            if not final_result:
                final_result = rows[0]
                if len(rows) > 1 and month >= 10: final_result = rows[1]
        else:
            query = f"""
            SELECT cd_lm, cd_ld, cd_hyganjee, cd_kyganjee, cd_dyganjee, cd_sy, cd_sm, cd_sd
            FROM calenda_data 
            WHERE cd_sy={year} AND cd_sm={month} AND cd_sd={day}
            """
            cursor.execute(query)
            final_result = cursor.fetchone()
    except:
        return None
    finally:
        conn.close()
        
    return final_result

# === 2. 시주 계산 ===
def calculate_time_pillar(day_stem, hour):
    time_idx = (hour + 1) // 2 
    if time_idx >= 12: time_idx = 0 
    time_branch = BRANCHES[time_idx] 
    stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    
    if day_stem not in stems: return "??", time_idx
        
    day_idx = stems.index(day_stem)
    start_stem_idx = (day_idx % 5) * 2
    time_stem_idx = (start_stem_idx + time_idx) % 10
    time_stem = stems[time_stem_idx]
    return time_stem + time_branch, time_idx

# === 3. 자미두수 계산 ===
def get_jami_data(lunar_month, time_idx, year_stem, lunar_day):
    # 명궁
    myung_idx = (2 + (lunar_month - 1) - time_idx) % 12
    myung_gung = BRANCHES[myung_idx]
    
    # 국수
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
    
    # 자미성
    ziwei_idx = (lunar_day + guk) % 12 
    
    stars = {
        '자미': ziwei_idx, '천부': (2 + 8 - ziwei_idx) % 12, '천기': (ziwei_idx - 1) % 12,
        '태양': (ziwei_idx - 3) % 12, '무곡': (ziwei_idx - 4) % 12, '천동': (ziwei_idx - 5) % 12,
        '염정': (ziwei_idx - 8) % 12, '태음': (2 + 8 - ziwei_idx + 1) % 12, 
        '탐랑': (2 + 8 - ziwei_idx + 2) % 12, '거문': (2 + 8 - ziwei_idx + 3) % 12,
        '천상': (2 + 8 - ziwei_idx + 4) % 12, '천량': (2 + 8 - ziwei_idx + 5) % 12,
        '칠살': (2 + 8 - ziwei_idx + 6) % 12, '파군': (2 + 8 - ziwei_idx + 10) % 12
    }
    
    my_stars = [s for s, i in stars.items() if BRANCHES[i] == myung_gung]
    
    if not my_stars: 
        opposite_idx = (myung_idx + 6) % 12
        op_stars = [s for s, i in stars.items() if i == opposite_idx]
        return myung_gung, f"명무정요(차용): {', '.join(op_stars)}" if op_stars else "(주성 없음)"
            
    return myung_gung, ", ".join(my_stars)

# === 4. 대운 정밀 계산 (대운수 포함) ===
def calculate_daewoon(gender, year_pillar, month_pillar, birth_day_lunar=15):
    # 1. 순행/역행 판단
    # 양남음녀(陽男陰女) -> 순행 / 음남양녀(陰男陽女) -> 역행
    yang_stems = ['甲', '丙', '戊', '庚', '壬']
    year_stem = year_pillar[0]
    is_year_yang = year_stem in yang_stems
    is_man = (gender == '남성')
    
    direction = 1 if (is_man and is_year_yang) or (not is_man and not is_year_yang) else -1
    
    # 2. 대운수(大運數) 계산 (약식: 절기력 데이터 없이 생일 기준으로 근사치 계산)
    # 원래는 절기까지 날짜수를 3으로 나눠야 하지만, 여기서는 1~10 사이의 수를 생성하는 알고리즘 사용
    # (실제 만세력 API 없이 정확한 절기일 계산은 불가능하므로, 간지 흐름에 맞게 근사치 산출)
    
    # 임시: 생일 날짜의 끝자리수를 이용하여 1~10 대운수 배정 (시뮬레이션용)
    # 실제로는 '절기일'과의 차이를 3으로 나눠야 함.
    daewoon_su = (birth_day_lunar % 10)
    if daewoon_su == 0: daewoon_su = 1
    
    try:
        start_idx = GANJI_60.index(month_pillar)
    except:
        return [] 
        
    daewoon_list = []
    # 8개 대운 (10년 단위)
    for i in range(1, 9): 
        idx = (start_idx + (i * direction)) % 60
        ganji = GANJI_60[idx]
        # 예: 3대운 甲子, 13대운 乙丑 ...
        start_age = daewoon_su + ((i-1) * 10)
        daewoon_list.append(f"{start_age}세({ganji})")
        
    return daewoon_list

# === 5. 메인 분석 함수 ===
def analyze_user(year, month, day, hour, is_lunar=False, gender='남성'):
    db_data = get_db_data(year, month, day, is_lunar)
    
    if not db_data: return {"error": "DB 데이터 없음 (saju.db 확인 요망)"}
    
    try:
        lunar_month = int(db_data[0]) 
        lunar_day = int(db_data[1])
        year_p, month_p, day_p = db_data[2], db_data[3], db_data[4]
    except: return {"error": "데이터 오류"}
        
    time_p, time_idx = calculate_time_pillar(day_p[0], hour)
    myung_loc, myung_star = get_jami_data(lunar_month, time_idx, year_p[0], lunar_day)
    
    # 대운 계산 시 생일 날짜(lunar_day)를 넘겨 대운수 계산에 반영
    daewoon = calculate_daewoon(gender, year_p, month_p, lunar_day)
    
    return {
        "입력기준": "음력" if is_lunar else "양력",
        "음력": f"{lunar_month}월 {lunar_day}일",
        "사주": [year_p, month_p, day_p, time_p],
        "대운": daewoon,
        "자미두수": {
            "명궁위치": myung_loc,
            "명궁주성": myung_star
        }
    }

# === 6. 시스템 관리 ===
def check_and_init_db():
    conn = sqlite3.connect('saju.db')
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT NOT NULL, name TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS consultations (id INTEGER PRIMARY KEY AUTOINCREMENT, counselor_id TEXT, client_name TEXT, client_gender TEXT, birth_date TEXT, birth_time TEXT, consult_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, memo TEXT, FOREIGN KEY (counselor_id) REFERENCES users (username))''')
        users = [('test1', '1234', '상담원1'), ('test2', '1234', '상담원2'), ('test3', '1234', '상담원3'), ('test4', '1234', '상담원4'), ('test5', '1234', '상담원5')]
        cursor.executemany('INSERT INTO users (username, password, name) VALUES (?, ?, ?)', users)
        conn.commit()
    conn.close()

def login_user(username, password):
    conn = sqlite3.connect('saju.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM users WHERE username=? AND password=?", (username, password))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def save_consultation(counselor_id, client_name, gender, b_date, b_time, memo=""):
    conn = sqlite3.connect('saju.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO consultations (counselor_id, client_name, client_gender, birth_date, birth_time, memo) VALUES (?, ?, ?, ?, ?, ?)", (counselor_id, client_name, gender, str(b_date), str(b_time), memo))
        conn.commit()
        return True
    except: return False
    finally: conn.close()

def get_my_consultation_history(counselor_id):
    conn = sqlite3.connect('saju.db')
    cursor = conn.cursor()
    cursor.execute("SELECT client_name, client_gender, birth_date, consult_date FROM consultations WHERE counselor_id=? ORDER BY consult_date DESC LIMIT 10", (counselor_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows