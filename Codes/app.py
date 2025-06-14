# app.py
import streamlit as st
import psycopg2
import pandas as pd
from config import DB_CONFIG

# 初始化数据库连接
def get_conn():
    return psycopg2.connect(**DB_CONFIG)

# 登录验证
def authenticate(username, password):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, role, pharmacy_id 
                FROM users 
                WHERE username = %s AND password = %s
            """, (username, password))
            return cur.fetchone()

# 获取当前用户药店的药品
def get_medicines(pharmacy_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT medicine_id, name, manufacturer, code, price, stock 
                FROM medicines 
                WHERE pharmacy_id = %s
            """, (pharmacy_id,))
            return cur.fetchall()

# 搜索药品
def search_medicines(pharmacy_id, keyword):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM medicines 
                WHERE pharmacy_id = %s 
                AND (name ILIKE %s 
                     OR manufacturer ILIKE %s 
                     OR code ILIKE %s)
            """, (pharmacy_id, f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
            return cur.fetchall()

# 销售药品
def sell_medicine(medicine_id, quantity, user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 检查库存
            cur.execute("SELECT stock FROM medicines WHERE medicine_id = %s", (medicine_id,))
            stock = cur.fetchone()[0]
            
            if stock >= quantity:
                # 更新库存
                cur.execute("""
                    UPDATE medicines 
                    SET stock = stock - %s 
                    WHERE medicine_id = %s
                """, (quantity, medicine_id))
                
                # 添加销售记录
                cur.execute("""
                    INSERT INTO sales (medicine_id, quantity, user_id)
                    VALUES (%s, %s, %s)
                """, (medicine_id, quantity, user_id))
                
                conn.commit()
                return True
            return False

# 用户管理
def manage_users(action, user_id=None, username=None, password=None, role=None, pharmacy_id=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            if action == "add":
                cur.execute("""
                    INSERT INTO users (username, password, role, pharmacy_id)
                    VALUES (%s, %s, %s, %s)
                """, (username, password, role, pharmacy_id))
            elif action == "delete":
                cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            elif action == "update":
                cur.execute("""
                    UPDATE users 
                    SET username = %s, password = %s, role = %s, pharmacy_id = %s
                    WHERE user_id = %s
                """, (username, password, role, pharmacy_id, user_id))
            conn.commit()

# 药店管理
def manage_pharmacies(action, pharmacy_id=None, name=None, address=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            if action == "add":
                cur.execute("""
                    INSERT INTO pharmacies (name, address)
                    VALUES (%s, %s)
                """, (name, address))
            elif action == "delete":
                cur.execute("DELETE FROM pharmacies WHERE pharmacy_id = %s", (pharmacy_id,))
            elif action == "update":
                cur.execute("""
                    UPDATE pharmacies 
                    SET name = %s, address = %s
                    WHERE pharmacy_id = %s
                """, (name, address, pharmacy_id))
            conn.commit()

# 药品管理
def manage_medicines(action, medicine_id=None, name=None, manufacturer=None, 
                     code=None, price=None, stock=None, pharmacy_id=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            if action == "add":
                cur.execute("""
                    INSERT INTO medicines (name, manufacturer, code, price, stock, pharmacy_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (name, manufacturer, code, price, stock, pharmacy_id))
            elif action == "delete":
                cur.execute("DELETE FROM medicines WHERE medicine_id = %s", (medicine_id,))
            elif action == "update":
                cur.execute("""
                    UPDATE medicines 
                    SET name = %s, manufacturer = %s, code = %s, price = %s, stock = %s
                    WHERE medicine_id = %s
                """, (name, manufacturer, code, price, stock, medicine_id))
            conn.commit()

# Streamlit UI
def main():
    st.set_page_config(page_title="连锁药店管理系统", layout="wide")
    
    if 'user' not in st.session_state:
        login_section()
    else:
        role = st.session_state.user[1]
        st.sidebar.title(f"角色: {'系统管理员' if role == 0 else '药店管理员' if role == 1 else '销售员'}")
        st.sidebar.button("退出登录", on_click=lambda: st.session_state.pop('user'))
        
        if role == 0: 
            admin_section()
        elif role == 1: 
            pharmacy_admin_section()
        elif role == 2: 
            sales_section()

def login_section():
    st.title("连锁药店管理系统")
    with st.form("登录"):
        user = st.text_input("用户名")
        pwd = st.text_input("密码", type="password")
        if st.form_submit_button("登录"):
            auth = authenticate(user, pwd)
            if auth:
                st.session_state.user = auth
                st.rerun()
            else:
                st.error("用户名或密码错误")

def admin_section():
    st.header("系统管理")
    tab1, tab2 = st.tabs(["用户管理", "药店管理"])
    
    with tab1:
        st.subheader("用户列表")
        with get_conn() as conn:
            users_df = pd.read_sql("SELECT * FROM users", conn)
        st.dataframe(users_df)
        
        with st.expander("添加用户"):
            with st.form("添加用户表单"):
                username = st.text_input("用户名")
                password = st.text_input("密码", type="password")
                role = st.selectbox("角色", [("系统管理员", 0), ("药店管理员", 1), ("销售员", 2)], format_func=lambda x: x[0])[1]
                pharmacy_id = st.number_input("药店ID", min_value=1)
                if st.form_submit_button("添加"):
                    manage_users("add", username=username, password=password, role=role, pharmacy_id=pharmacy_id)
                    st.success("用户添加成功")
                    st.rerun()
    
    with tab2:
        st.subheader("药店列表")
        with get_conn() as conn:
            pharmacies_df = pd.read_sql("SELECT * FROM pharmacies", conn)
        st.dataframe(pharmacies_df)
        
        with st.expander("添加药店"):
            with st.form("添加药店表单"):
                name = st.text_input("药店名称")
                address = st.text_area("地址")
                if st.form_submit_button("添加"):
                    manage_pharmacies("add", name=name, address=address)
                    st.success("药店添加成功")
                    st.rerun()

def pharmacy_admin_section():
    st.header("药品管理")
    pharmacy_id = st.session_state.user[2]
    
    # 显示当前药店的药品
    medicines = get_medicines(pharmacy_id)
    if medicines:
        st.subheader("药品列表")
        df = pd.DataFrame(medicines, columns=["ID", "名称", "生产商", "编码", "价格", "库存"])
        st.dataframe(df)
    else:
        st.warning("当前药店没有药品")
    
    # 添加药品
    with st.expander("添加药品"):
        with st.form("添加药品表单"):
            name = st.text_input("药品名称")
            manufacturer = st.text_input("生产商")
            code = st.text_input("编码")
            price = st.number_input("价格", min_value=0.0, step=0.1)
            stock = st.number_input("库存", min_value=0, step=1)
            if st.form_submit_button("添加"):
                manage_medicines("add", name=name, manufacturer=manufacturer, 
                                code=code, price=price, stock=stock, pharmacy_id=pharmacy_id)
                st.success("药品添加成功")
                st.rerun()

def sales_section():
    st.header("药品销售")
    pharmacy_id = st.session_state.user[2]
    user_id = st.session_state.user[0]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("药品搜索")
        keyword = st.text_input("输入药品名称、生产商或编码")
        if keyword:
            results = search_medicines(pharmacy_id, keyword)
            if results:
                st.subheader("搜索结果")
                for med in results:
                    st.write(f"{med[1]} | {med[2]} | 库存: {med[5]} | 价格: ¥{med[4]}")
            else:
                st.info("未找到匹配的药品")
    
    with col2:
        st.subheader("销售操作")
        with st.form("销售表单"):
            medicine_id = st.number_input("药品ID", min_value=1)
            quantity = st.number_input("数量", min_value=1, value=1)
            if st.form_submit_button("销售"):
                if sell_medicine(medicine_id, quantity, user_id):
                    st.success(f"成功销售 {quantity} 件商品")
                else:
                    st.error("库存不足或药品不存在")

if __name__ == "__main__":
    main()