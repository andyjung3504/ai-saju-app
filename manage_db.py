import sqlite3

def init_system_db():
    conn = sqlite3.connect('saju.db')
    cursor = conn.cursor()
    
    # 1. 상담원(Users) 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        name TEXT
    )
    ''')
    
    # 2. 상담 기록(Consultations) 테이블 생성
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
    
    # 3. 초기 상담원 데이터 삽입 (test1 ~ test5)
    users = [
        ('test1', '1234', '상담원1'),
        ('test2', '1234', '상담원2'),
        ('test3', '1234', '상담원3'),
        ('test4', '1234', '상담원4'),
        ('test5', '1234', '상담원5')
    ]
    
    try:
        cursor.executemany('INSERT INTO users (username, password, name) VALUES (?, ?, ?)', users)
        print("상담원 계정 생성 완료 (test1~test5 / 비번 1234)")
    except sqlite3.IntegrityError:
        print("이미 계정이 존재합니다. 패스합니다.")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_system_db()