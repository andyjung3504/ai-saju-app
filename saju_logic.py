import sqlite3
import pandas as pd

# 60갑자 리스트 (검증용 필수 데이터)
GANJI_60 = [
    '甲子', '乙丑', '丙寅', '丁卯', '戊辰', '己巳', '庚午', '辛未', '壬申', '癸酉',
    '甲戌', '乙亥', '丙子', '丁丑', '戊寅', '己卯', '庚辰', '辛巳', '壬午', '癸未',
    '甲申', '乙酉', '丙戌', '丁亥', '戊子', '己丑', '庚寅', '辛卯', '壬辰', '癸巳',
    '甲午', '乙未', '丙申', '丁酉', '戊戌', '己亥', '庚子', '辛丑', '壬寅', '癸卯',
    '甲辰', '乙巳', '丙午', '丁未', '戊申', '己酉', '庚戌', '辛亥', '壬子', '癸丑',
    '甲寅', '乙卯', '丙辰', '丁巳', '戊午', '己未', '庚申', '辛酉', '壬戌', '癸亥'
]

BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

# === 1. DB 조회 및 정밀 검증 (여기가 핵심) ===
def get_db_data(year, month, day, is_lunar=False):
    conn = sqlite3.connect('saju.db')
    cursor = conn.cursor()
    
    # 결과 담을 변수
    final_result = None
    
    if is_lunar:
        # [핵심 로직]
        # 음력 1973년 11월은 양력으로 1974년 1월일 수 있음.
        # 따라서 입력받은 year(1973)와 year+1(1974) 두 해를 모두 뒤져야 함.
        # cd_ly 컬럼이 없어도 작동하도록 cd_sy(양력) 기준으로 2년치를 검색.
        query = f"""
        SELECT cd_lm, cd_ld, cd_hyganjee, cd_kyganjee, cd_dyganjee, cd_sy, cd_sm, cd_sd
        FROM calenda_data 
        WHERE (cd_sy={year} OR cd_sy={year+1}) 
          AND cd_lm={month} 
          AND cd_ld={day}
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        if not rows:
            conn.close()
            return None
            
        # 검색된 후보들 중에서 "진짜 입력한 연도(1973)"에 맞는 놈을 찾아야 함.
        # 방법: 입력한 연도(1973)에 해당하는 간지(계축)가 맞는지 확인.
        # 1973년의 간지 인덱스 = (1973 - 4) % 60 = 49 (癸丑 - 계축)
        target_ganji = GANJI_60[(year - 4) % 60]
        
        found_match = False
        for row in rows:
            # DB에 저장된 년주(cd_hyganjee)와 우리가 찾는 년주(target_ganji)가 같은지 비교
            # 주의: 한자 텍스트가 정확히 일치해야 함.
            if row[2] == target_ganji:
                final_result = row
                found_match = True
                break
        
        # 만약 정확한 간지 일치자가 없으면? (입춘 전후 문제 등)
        # 우선순위: 양력 연도가 입력 연도와 가까운 것보다는, 
        # 음력은 보통 양력보다 뒤로 밀리므로, 만약 11월, 12월이면 year+1 쪽이 맞을 확률이 높음.
        if not found_match:
            # 1순위: 그냥 첫번째꺼라도 가져온다 (데이터 없는것보단 나음)
            final_result = rows[0]
            # 보정: 만약 후보가 2개고, 우리가 찾는게 하반기(10월~12월)라면 뒤에꺼(year+1) 선택
            if len(rows) > 1 and month >= 10:
                final_result = rows[1]

    else:
        # 양력은 심플하게 검색 (기존 유지)
        query = f"""
        SELECT cd_lm, cd_ld, cd_hyganjee, cd_kyganjee, cd_dyganjee, cd_sy, cd_sm, cd_sd
        FROM calenda_data 
        WHERE cd_sy={year} AND cd_sm={month} AND cd_sd={day}
        """
        cursor.execute(query)
        final_result = cursor.fetchone()
        
    conn.close()
    return final_result

# === 2. 시주 계산 ===
def calculate_time_pillar(day_stem, hour):
    time_idx = (hour + 1) // 2 
    if time_idx >= 12: time_idx = 0 
    time_branch = BRANCHES[time_idx] 
    stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    
    # 예외처리: DB에 천간 글자가 이상하게 박혀있을 경우 대비
    if day_stem not in stems: 
        # 만약 day_stem이 안 잡히면 기본값 처리하거나 에러 방지
        return "??", time_idx
        
    day_idx = stems.index(day_stem)
    start_stem_idx = (day_idx % 5) * 2
    time_stem_idx = (start_stem_idx + time_idx) % 10
    time_stem = stems[time_stem_idx]
    return time_stem + time_branch, time_idx

# === 3. 자미두수 계산 ===
def get_jami_data(lunar_month, time_idx, year_stem, lunar_day):
    # 명궁 계산
    myung_idx = (2 + (lunar_month - 1) - time_idx) % 12
    myung_gung = BRANCHES[myung_idx]
    
    # 국수 계산
    stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    try:
        y_idx = stems.index(year_stem)
    except:
        y_idx = 0 # 에러 방지용 기본값
        
    start = (y_idx % 5) * 2 + 2 
    off = myung_idx - 2
    if off < 0: off += 12
    m_stem = (start + off) % 10
    
    code = (m_stem // 2 + myung_idx // 2) % 5
    guk_map = {0: 4, 1: 2, 2: 6, 3: 5, 4: 3}
    guk = guk_map[code]
    
    ziwei_idx = (lunar_day + guk) % 12 
    
    # 별 배치
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
        return {"error": f"데이터 없음: {year}년 {month}월 {day}일 데이터를 찾을 수 없습니다."}
    
    try:
        lunar_month = int(db_data[0]) 
        lunar_day = int(db_data[1])
        # [수정] DB 조회 결과 인덱스가 쿼리 변경으로 밀릴 수 있으므로 정확히 매핑
        # query: cd_lm, cd_ld, cd_hyganjee, cd_kyganjee, cd_dyganjee, ...
        year_p = db_data[2]
        month_p = db_data[3]
        day_p = db_data[4]
    except Exception as e: 
        return {"error": f"데이터 처리 오류: {e}"}
        
    # 시주 계산
    time_p, time_idx = calculate_time_pillar(day_p[0], hour)
    
    # 자미두수
    myung_loc, myung_star = get_jami_data(lunar_month, time_idx, year_p[0], lunar_day)
    
    # 대운
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