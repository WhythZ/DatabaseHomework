# init_db.py
import psycopg2
from config import DB_CONFIG

def init_database():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 创建表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password VARCHAR(50) NOT NULL,
        role INT NOT NULL,   -- 0:系统管理员 1:药店管理员 2:销售员
        pharmacy_id INT
    );
    
    CREATE TABLE IF NOT EXISTS pharmacies (
        pharmacy_id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        address TEXT
    );
    
    CREATE TABLE IF NOT EXISTS medicines (
        medicine_id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        manufacturer VARCHAR(100),
        code VARCHAR(50) UNIQUE,
        price DECIMAL(10,2),
        stock INT,
        pharmacy_id INT NOT NULL REFERENCES pharmacies(pharmacy_id)
    );
    
    CREATE TABLE IF NOT EXISTS sales (
        sale_id SERIAL PRIMARY KEY,
        medicine_id INT REFERENCES medicines(medicine_id),
        quantity INT,
        sale_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user_id INT REFERENCES users(user_id)
    );
    """)
    
    # 插入初始测试数据
    cursor.execute("""
    INSERT INTO pharmacies (name, address) 
    VALUES ('总店', '北京市朝阳区') 
    RETURNING pharmacy_id;
    """)
    pharmacy_id = cursor.fetchone()[0]
    
    cursor.execute("""
    INSERT INTO users (username, password, role, pharmacy_id) 
    VALUES 
        ('admin', 'admin123', 0, %s),
        ('manager', 'manager123', 1, %s),
        ('sales', 'sales123', 2, %s);
    """, (pharmacy_id, pharmacy_id, pharmacy_id))
    
    cursor.execute("""
    INSERT INTO medicines (name, manufacturer, code, price, stock, pharmacy_id)
    VALUES 
        ('阿莫西林胶囊', '云南白药', 'AMXL123', 25.5, 100, %s),
        ('板蓝根颗粒', '同仁堂', 'BLG456', 18.0, 80, %s);
    """, (pharmacy_id, pharmacy_id))
    
    conn.commit()
    print("数据库初始化完成！")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    init_database()