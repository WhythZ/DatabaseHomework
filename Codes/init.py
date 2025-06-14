import psycopg2
from config import DB_CONFIG
import sys

def init_database():
    conn = None
    try:
        # 尝试连接数据库
        conn = psycopg2.connect(**DB_CONFIG)
        # 创建表需要自动提交
        conn.autocommit = True
        
        cursor = conn.cursor()
        print("Database Connect Success!")
        
        # 创建用户表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(50) NOT NULL,
            role INT NOT NULL,   -- 0:系统管理员 1:药店管理员 2:销售员
            pharmacy_id INT
        );
        """)
        print("Users Table Create Success!")
        
        # 创建药店表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pharmacies (
            pharmacy_id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            address TEXT
        );
        """)
        print("Pharmacies Table Create Success!")
        
        # 创建药品表（添加外键约束）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            medicine_id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            manufacturer VARCHAR(100),
            code VARCHAR(50) UNIQUE,
            price DECIMAL(10,2),
            stock INT,
            pharmacy_id INT NOT NULL REFERENCES pharmacies(pharmacy_id)
        );
        """)
        print("Medicines Table Create Success!")
        
        # 创建销售记录表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            sale_id SERIAL PRIMARY KEY,
            medicine_id INT REFERENCES medicines(medicine_id),
            quantity INT,
            sale_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INT REFERENCES users(user_id)
        );
        """)
        print("Sales Table Create Success!")
        
        # 插入初始测试数据，先插入药店
        cursor.execute("""
        INSERT INTO pharmacies (name, address) 
        VALUES ('总店', '北京市朝阳区') 
        RETURNING pharmacy_id;
        """)
        pharmacy_id = cursor.fetchone()[0]
        print(f"Pharmacy ID: {pharmacy_id}")
        
        # 然后插入用户
        cursor.execute("""
        INSERT INTO users (username, password, role, pharmacy_id) 
        VALUES 
            ('admin', 'admin@pw000', 0, %s),
            ('manager', 'manager@pw111', 1, %s),
            ('sales', 'sales@pw222', 2, %s);
        """, (pharmacy_id, pharmacy_id, pharmacy_id))
        print("User Data Insert Success!")
        
        # 然后插入药品
        cursor.execute("""
        INSERT INTO medicines (name, manufacturer, code, price, stock, pharmacy_id)
        VALUES 
            ('阿莫西林胶囊', '云南白药', 'AMXL123', 25.5, 100, %s),
            ('板蓝根颗粒', '同仁堂', 'BLG456', 18.0, 80, %s);
        """, (pharmacy_id, pharmacy_id))
        print("Medicine Data Insert Success!")
        
        conn.commit()
        print("Database Initialization Success!")
        
    except psycopg2.OperationalError as oe:
        print(f"Link Error: {str(oe)}")
        print("Please check the configurations in config.py")
    except psycopg2.ProgrammingError as pe:
        print(f"SQL Error: {str(pe)}")
        print("Please check SQL grammar or table structure")
    except psycopg2.IntegrityError as ie:
        print(f"Data Integrity Error: {str(ie)}")
    except Exception as e:
        print(f"Unknown Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    init_database()