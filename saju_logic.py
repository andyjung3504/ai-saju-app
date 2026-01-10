import sqlite3
import pandas as pd

# 60갑자 리스트 (계산을 위해 필요)
GANJI_60 = [
    '甲子', '乙丑', '丙寅', '丁卯', '戊辰', '己巳', '庚午', '辛未', '壬申', '癸酉',
    '甲戌', '乙亥', '丙子', '丁丑', '戊寅', '己卯', '庚辰', '辛巳', '壬午', '癸未',
    '甲申', '乙酉', '丙戌', '丁亥', '戊子', '己丑', '庚寅', '辛卯', '壬辰', '癸巳',
    '甲午', '乙未', '丙申', '丁酉', '戊戌', '己亥', '庚子', '辛丑', '壬寅', '癸卯',
    '甲辰', '乙巳', '丙午', '丁未', '戊申', '己酉', '庚戌', '辛亥', '壬子', '癸丑',
    '甲寅', '乙卯', '丙辰', '丁巳', '戊午', '己未', '庚申', '辛酉', '壬戌', '癸亥'
]

# 1. DB 조회
def get_db_data(year, month, day, is_lunar=False):
    conn = sqlite3.connect('saju.db')
    cursor = conn.cursor()
    if is_lunar:
        query = f"SELECT cd_lm, cd_ld, cd_hyganjee, cd_kyganjee, cd_dyganjee FROM calenda_data WHERE cd_sy={year} AND cd_lm={month} AND cd_ld={day}"
    else:
        query = f"SELECT cd_lm, cd_ld, cd_hyganjee, cd_kyganjee, cd_dyganjee FROM calenda_data WHERE cd_sy={year} AND cd_sm={month} AND cd_sd={day}"
    cursor.execute(query)
    result = cursor.fetchone()
    conn.close()
    return result

# 2. 시주 계산
def calculate_time_pillar(day_stem, hour):
    time_idx = (hour + 1) // 2 
    if time_idx >= 12: time_idx = 0 
    branches = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    time_branch = branches[time_idx] 
    stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    if day_stem not in stems: return "??", 0
    day_idx = stems.index(day_stem)
    start_stem_idx = (day_idx % 5) * 2
    time_stem_idx = (start_stem_idx + time_idx) % 10
    time_stem = stems[time_stem_idx]
    return time_stem + time_branch, time_idx

# 3. 자미두수 (생략 없이 포함)
BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
def get_jami_data(lunar_month, time_idx, year_stem, lunar_day):
    # 명궁
    myung_idx = (2 + (lunar_month - 1) - time_idx) % 12
    myung_gung = BRANCHES[myung_idx]
    
    # 국수 (약식)
    stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    y_idx = stems.index(year_stem)
    start = (y_idx % 5) * 2 + 2
    off = myung_idx - 2
    if off < 0: off += 12
    m_stem = (start + off) % 10
    code = (m_stem // 2 + myung_idx // 2) % 5
    guk_map = {0: 4, 1: 2, 2: 6, 3: 5, 4: 3}
    guk = guk_map[code]
    
    # 자미성
    ziwei_idx = (lunar_day + guk) % 12 # 약식
    
    # 별 배치 (간단히 자미 계열만)
    stars = {}
    stars['자미'] = ziwei_idx
    stars['천부'] = (2 + 8 - ziwei_idx) % 12
    # 필요한 만큼 추가...
    
    my_stars = []
    for s, i in stars.items():
        if BRANCHES[i] == myung_gung: my_stars.append(s)
    if not my_stars: my_stars.append("(명궁 주성 없음)")
    
    return myung_gung, ", ".join(my_stars)

# 4. ★대운(Daewoon) 계산 로직 (New)★
def calculate_daewoon(gender, year_pillar, month_pillar):
    # 양남음녀: 순행, 음남양녀: 역행
    # 양천간: 갑, 병, 무, 경, 임
    yang_stems = ['甲', '丙', '戊', '庚', '壬']
    year_stem = year_pillar[0]
    
    is_year_yang = year_stem in yang_stems
    is_man = (gender == '남성')
    
    # 순행 조건: (남자&양년) or (여자&음년)
    if (is_man and is_year_yang) or (not is_man and not is_year_yang):
        direction = 1 # 순행
    else:
        direction = -1 # 역행
        
    # 월주 인덱스 찾기
    try:
        start_idx = GANJI_60.index(month_pillar)
    except:
        return [] # 에러시 빈칸
        
    # 대운 뽑기 (1대운 ~ 8대운 정도)
    daewoon_list = []
    # 대운수는 절기 데이터가 없어 정확한 계산 불가하므로 
    # 통상적인 10년 단위 흐름만 제공 (AI가 나이는 추정하게 둠 or 10세 단위 가정)
    
    for i in range(1, 9): # 8개 대운
        idx = (start_idx + (i * direction)) % 60
        ganji = GANJI_60[idx]
        # 대운수(Age)는 DB 절기 시간 데이터 부재로 정확한 계산 불가 -> 임의로 10단위 표기
        # 실전에서는 "초년, 청년, 중년" 흐름 파악용
        daewoon_list.append(f"{i*10}대운: {ganji}")
        
    return daewoon_list

# === 메인 함수 ===
def analyze_user(year, month, day, hour, is_lunar=False, gender='남성'):
    db_data = get_db_data(year, month, day, is_lunar)
    if not db_data: return {"error": "DB 날짜 없음"}
    
    try:
        lunar_month = int(db_data[0]) 
        lunar_day = int(db_data[1])
    except: return {"error": "날짜 형변환 오류"}
        
    year_p, month_p, day_p = db_data[2], db_data[3], db_data[4]
    
    # 시주
    time_p, time_idx = calculate_time_pillar(day_p[0], hour)
    
    # 자미두수
    myung_loc, myung_star = get_jami_data(lunar_month, time_idx, year_p[0], lunar_day)
    
    # ★대운 계산 실행
    daewoon = calculate_daewoon(gender, year_p, month_p)
    
    return {
        "입력기준": "음력" if is_lunar else "양력",
        "음력": f"{lunar_month}월 {lunar_day}일",
        "사주": [year_p, month_p, day_p, time_p],
        "대운": daewoon, # 계산된 대운 리스트 반환
        "자미두수": {
            "명궁위치": myung_loc,
            "명궁주성": myung_star
        }
    }
# ... (위에는 기존 사주/대운/자미두수 로직 그대로 유지) ...

# === 5. 시스템 관리 함수 (로그인/저장) ===

def login_user(username, password):
    """로그인 검증 함수"""
    conn = sqlite3.connect('saju.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM users WHERE username=? AND password=?", (username, password))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0] # 상담원 이름 반환 (예: 상담원1)
    else:
        return None

def save_consultation(counselor_id, client_name, gender, b_date, b_time, memo=""):
    """상담 이력 저장 함수"""
    conn = sqlite3.connect('saju.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO consultations (counselor_id, client_name, client_gender, birth_date, birth_time, memo)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (counselor_id, client_name, gender, str(b_date), str(b_time), memo))
        conn.commit()
        return True
    except Exception as e:
        print(f"DB 저장 오류: {e}")
        return False
    finally:
        conn.close()

def get_my_consultation_history(counselor_id):
    """내 상담 이력 조회"""
    conn = sqlite3.connect('saju.db')
    # 결과를 딕셔너리처럼 쓰기 위해 row_factory 설정 가능하나 여기선 생략
    cursor = conn.cursor()
    cursor.execute("""
    SELECT client_name, client_gender, birth_date, consult_date 
    FROM consultations 
    WHERE counselor_id=? 
    ORDER BY consult_date DESC
    LIMIT 10
    """, (counselor_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows