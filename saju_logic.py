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

# === 1. DB 조회 (여기가 핵심 수정됨) ===
def get_db_data(year, month, day, is_lunar=False):
    conn = sqlite3.connect('saju.db')
    cursor = conn.cursor()
    
    if is_lunar:
        # [수정] 음력 선택 시: 무조건 cd_ly(음력년), cd_lm(음력월), cd_ld(음력일)로만 검색
        # 양력(cd_sy)은 절대 보지 않음.
        query = f"""
        SELECT cd_lm, cd_ld, cd_hyganjee, cd_kyganjee, cd_dyganjee 
        FROM calenda_data 
        WHERE cd_ly={year} AND cd_lm={month} AND cd_ld={day}
        """
    else:
        # [수정] 양력 선택 시: cd_sy, cd_sm, cd_sd로 검색
        query = f"""
        SELECT cd_lm, cd_ld, cd_hyganjee, cd_kyganjee, cd_dyganjee 
        FROM calenda_data 
        WHERE cd_sy={year} AND cd_sm={month} AND cd_sd={day}
        """
        
    cursor.execute(query)
    result = cursor.fetchone()
    conn.close()
    return result

# === 2. 시주 계산 ===
def calculate_time_pillar(day_stem, hour):
    time_idx = (hour + 1) // 2 
    if time_idx >= 12: time_idx = 0 
    time_branch = BRANCHES[time_idx] 
    stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    if day_stem not in stems: return "??", 0
    day_idx = stems.index(day_stem)
    start_stem_idx = (day_idx % 5) * 2
    time_stem_idx = (start_stem_idx + time_idx) % 10
    time_stem = stems[time_stem_idx]
    return time_stem + time_branch, time_idx

# === 3. 자미두수 계산 ===
def get_jami_data(lunar_month, time_idx, year_stem, lunar_day):
    myung_idx = (2 + (lunar_month - 1) - time_idx) % 12
    myung_gung = BRANCHES[myung_idx]
    
    stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    y_idx = stems.index(year_stem)
    start = (y_idx % 5) * 2 + 2 
    off = myung_idx - 2
    if off < 0: off += 12
    m_stem = (start + off) % 10
    
    code = (m_stem // 2 + myung_idx // 2) % 5
    guk_map = {0: 4, 1: 2, 2: 6, 3: 5, 4: 3}
    guk = guk_map[code]
    
    ziwei_idx = (lunar_day + guk) % 12 
    
    stars = {}
    stars['자미'] = ziwei_idx
    stars['천부'] = (2 + 8 - ziwei_idx) % 12
    stars['천기'] = (ziwei_idx - 1) % 12
    stars['태양'] = (ziwei_idx - 3) % 12
    stars['무곡'] = (ziwei_idx - 4) % 12
    stars['천동'] = (ziwei_idx - 5) % 12
    stars['염정'] = (ziwei_idx - 8) % 12
    stars['태음'] = (stars['천부'] + 1) % 12
    stars['탐랑'] = (stars['천부'] + 2) % 12
    stars['거문'] = (stars['천부'] + 3) % 12
    stars['천상'] = (stars['천부'] + 4) % 12
    stars['천량'] = (stars['천부'] + 5) % 12
    stars['칠살'] = (stars['천부'] + 6) % 12
    stars['파군'] = (stars['천부'] + 10) % 12
    
    my_stars = []
    for s, i in stars.items():
        if BRANCHES[i] == myung_gung: my_stars.append(s)
    
    if not my_stars: 
        opposite_idx = (myung_idx + 6) % 12
        op_stars = []
        for s, i in stars.items():
            if i == opposite_idx: op_stars.append(s)
        if op_stars:
            return myung_gung, f"명무정요(차용): {', '.join(op_stars)}"
        else:
            return myung_gung, "(주성 없음)"
            
    return myung_gung, ", ".join(my_stars)

# === 4. 대운 계산 ===
def calculate_daewoon(gender, year_pillar, month_pillar):
    yang_stems = ['甲', '丙', '戊', '庚', '壬']
    year_stem = year_pillar[0]
    is_year_yang = year_stem in yang_stems
    is_man = (gender == '남성')
    
    if (is_man and is_year_yang) or (not is_man and not is_year_yang):
        direction = 1 
    else:
        direction = -1 
        
    try:
        start_idx = GANJI_60.index(month_pillar)
    except:
        return [] 
        
    daewoon_list = []
    for i in range(1, 9): 
        idx = (start_idx + (i * direction)) % 60
        ganji = GANJI_60[idx]
        daewoon_list.append(f"{i*10}대운: {ganji}")
        
    return daewoon_list

# === 5. 메인 분석 함수 ===
def analyze_user(year, month, day, hour, is_lunar=False, gender='남성'):
    db_data = get_db_data(year, month, day, is_lunar)
    if not db_data: 
        return {"error": f"데이터 없음: {year}년 {month}월 {day}일 ({'음력' if is_lunar else '양력'}) 데이터가 DB에 없습니다."}
    
    try:
        lunar_month = int(db_data[0]) 
        lunar_day = int(db_data[1])
    except: return {"error": "날짜 형변환 오류"}
        
    year_p, month_p, day_p = db_data[2], db_data[3], db_data[4]
    time_p, time_idx = calculate_time_pillar(day_p[0], hour)
    
    myung_loc, myung_star = get_jami_data(lunar_month, time_idx, year_p[0], lunar_day)
    daewoon = calculate_daewoon(gender, year_p, month_p)
    
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

# === 6. 시스템 관리 (로그인, 저장, DB생성) ===
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