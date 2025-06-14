import streamlit as st
import psycopg2
import pandas as pd
from config import DB_CONFIG
from psycopg2.extras import RealDictCursor

# 缓存数据库连接（生命周期为 session）
@st.cache_resource
def get_conn():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

@st.cache_data(ttl=300)
def authenticate(username, password):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, role, pharmacy_id 
                FROM users 
                WHERE username = %s AND password = %s
            """, (username, password))
            return cur.fetchone()

@st.cache_data(ttl=60)
def get_medicines(pharmacy_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT medicine_id, name, manufacturer, code, price, stock 
                FROM medicines 
                WHERE pharmacy_id = %s
            """, (pharmacy_id,))
            return cur.fetchall()

@st.cache_data(ttl=60)
def search_medicines(pharmacy_id, keyword):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM medicines 
                WHERE pharmacy_id = %s 
                AND (name ILIKE %s OR manufacturer ILIKE %s OR code ILIKE %s)
            """, (pharmacy_id, f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
            return cur.fetchall()

def sell_medicine(medicine_id, quantity, user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT stock FROM medicines WHERE medicine_id = %s", (medicine_id,))
            row = cur.fetchone()
            if row and row['stock'] >= quantity:
                cur.execute("UPDATE medicines SET stock = stock - %s WHERE medicine_id = %s", (quantity, medicine_id))
                cur.execute("INSERT INTO sales (medicine_id, quantity, user_id) VALUES (%s, %s, %s)", (medicine_id, quantity, user_id))
                conn.commit()
                st.cache_data.clear()
                return True
            return False

def manage_users(action, **kwargs):
    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                if action == "add":
                    cur.execute("INSERT INTO users (username, password, role, pharmacy_id) VALUES (%s, %s, %s, %s)",
                                (kwargs['username'], kwargs['password'], kwargs['role'], kwargs['pharmacy_id']))
                elif action == "delete":
                    cur.execute("DELETE FROM users WHERE user_id = %s", (kwargs['user_id'],))
                elif action == "update":
                    cur.execute("UPDATE users SET username = %s, password = %s, role = %s, pharmacy_id = %s WHERE user_id = %s",
                                (kwargs['username'], kwargs['password'], kwargs['role'], kwargs['pharmacy_id'], kwargs['user_id']))
                conn.commit()
                st.cache_data.clear()
            except psycopg2.IntegrityError:
                st.error("操作失败：用户名已存在或其他约束冲突")

def manage_pharmacies(action, **kwargs):
    with get_conn() as conn:
        with conn.cursor() as cur:
            if action == "add":
                cur.execute("INSERT INTO pharmacies (name, address) VALUES (%s, %s)", (kwargs['name'], kwargs['address']))
            elif action == "delete":
                cur.execute("DELETE FROM pharmacies WHERE pharmacy_id = %s", (kwargs['pharmacy_id'],))
            elif action == "update":
                cur.execute("UPDATE pharmacies SET name = %s, address = %s WHERE pharmacy_id = %s",
                            (kwargs['name'], kwargs['address'], kwargs['pharmacy_id']))
            conn.commit()
            st.cache_data.clear()

def manage_medicines(action, **kwargs):
    with get_conn() as conn:
        with conn.cursor() as cur:
            if action == "add":
                cur.execute("""
                    INSERT INTO medicines (name, manufacturer, code, price, stock, pharmacy_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (kwargs['name'], kwargs['manufacturer'], kwargs['code'], kwargs['price'], kwargs['stock'], kwargs['pharmacy_id']))
            elif action == "delete":
                cur.execute("DELETE FROM medicines WHERE medicine_id = %s", (kwargs['medicine_id'],))
            elif action == "update":
                cur.execute("""
                    UPDATE medicines 
                    SET name = %s, manufacturer = %s, code = %s, price = %s, stock = %s
                    WHERE medicine_id = %s
                """, (kwargs['name'], kwargs['manufacturer'], kwargs['code'], kwargs['price'], kwargs['stock'], kwargs['medicine_id']))
            conn.commit()
            st.cache_data.clear()

def login_section():
    st.title("💊 连锁药店管理系统")
    st.markdown("欢迎使用，请输入账号密码进行登录")
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

def admin_user_section():
    st.subheader("👤 用户管理")
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id, username, role, pharmacy_id FROM users")
        rows = cur.fetchall()
        users_df = pd.DataFrame(rows, columns=[desc[0] for desc in cur.description])
        role_map = {0: "系统管理员", 1: "药店管理员", 2: "销售员"}
        users_df["角色"] = users_df["role"].map(role_map)
        users_df.rename(columns={"user_id": "用户ID", "username": "用户名", "pharmacy_id": "药店ID"}, inplace=True)
        st.dataframe(users_df[["用户ID", "用户名", "角色", "药店ID"]], use_container_width=True)

    with st.expander("➕ 添加用户"):
        with st.form("添加用户表单"):
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            role_option = st.selectbox("角色", options=[0, 1, 2], format_func=lambda x: role_map[x])
            pharmacy_id = st.number_input("药店ID", min_value=1, step=1)
            if st.form_submit_button("添加"):
                manage_users("add", username=username, password=password, role=role_option, pharmacy_id=pharmacy_id)
                st.success("用户添加成功！")
                st.rerun()

def admin_pharmacy_section():
    st.subheader("🏪 药店管理")
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT pharmacy_id, name, address FROM pharmacies")
        rows = cur.fetchall()
        df = pd.DataFrame(rows, columns=[desc[0] for desc in cur.description])
        df.rename(columns={"pharmacy_id": "药店ID", "name": "药店名称", "address": "地址"}, inplace=True)
    st.dataframe(df, use_container_width=True)

    with st.expander("➕ 添加药店"):
        with st.form("添加药店表单"):
            name = st.text_input("药店名称")
            address = st.text_area("地址")
            if st.form_submit_button("添加"):
                manage_pharmacies("add", name=name, address=address)
                st.success("药店添加成功")
                st.rerun()

def pharmacy_admin_section():
    st.subheader("💊 药品管理")
    pharmacy_id = st.session_state.user['pharmacy_id']
    medicines = get_medicines(pharmacy_id)
    if medicines:
        df = pd.DataFrame(medicines)
        df.rename(columns={"name": "名称", "manufacturer": "生产商", "code": "编码", "price": "价格", "stock": "库存"}, inplace=True)
        st.dataframe(df)

    with st.expander("➕ 添加药品"):
        with st.form("添加药品表单"):
            name = st.text_input("药品名称")
            manufacturer = st.text_input("生产商")
            code = st.text_input("编码")
            price = st.number_input("价格", min_value=0.0, step=0.1)
            stock = st.number_input("库存", min_value=0, step=1)
            if st.form_submit_button("添加"):
                manage_medicines("add", name=name, manufacturer=manufacturer, code=code, price=price, stock=stock, pharmacy_id=pharmacy_id)
                st.success("药品添加成功")
                st.rerun()

def sales_section():
    st.subheader("🛒 药品销售")
    pharmacy_id = st.session_state.user['pharmacy_id']
    user_id = st.session_state.user['user_id']

    # 读取药品数据
    medicines = get_medicines(pharmacy_id)
    if not medicines:
        st.info("当前药店暂无药品")
        return

    med_map = {f"{m['name']} | {m['manufacturer']} | 编码: {m['code']}": m for m in medicines}

    keyword = st.text_input("🔍 搜索药品 (名称/生产商/编码)")
    if keyword:
        results = search_medicines(pharmacy_id, keyword)
        if results:
            st.markdown("#### 搜索结果:")
            for med in results:
                st.write(f"- {med['name']} | {med['manufacturer']} | 库存: {med['stock']} | 价格: ¥{med['price']:.2f}")
        else:
            st.info("未找到匹配的药品")

    st.markdown("---")
    st.subheader("💳 执行销售")

    # 选择药品
    options = list(med_map.keys())
    selected = st.selectbox("选择药品", options)

    selected_med = med_map[selected]
    st.markdown(f"**药品详情:** 库存: {selected_med['stock']}  |  价格: ¥{selected_med['price']:.2f}")

    max_qty = selected_med['stock']
    if max_qty == 0:
        st.warning("该药品库存为0，无法销售")
        quantity = st.number_input("数量", min_value=0, max_value=0, value=0, disabled=True)
        sell_enabled = False
    else:
        quantity = st.number_input("数量", min_value=1, max_value=max_qty, value=1)
        sell_enabled = True

    if st.button("销售", disabled=not sell_enabled):
        success = sell_medicine(selected_med['medicine_id'], quantity, user_id)
        if success:
            st.success(f"成功销售 {quantity} 件《{selected_med['name']}》")
            # 清除缓存，刷新 medicines 数据
            st.cache_data.clear()
            medicines = get_medicines(pharmacy_id)
            med_map = {f"{m['name']} | {m['manufacturer']} | 编码: {m['code']}": m for m in medicines}
            # 更新选中药品库存信息
            selected_med = med_map.get(selected)
            if selected_med:
                st.markdown(f"**更新后库存:** {selected_med['stock']}")
        else:
            st.error("销售失败，库存不足或药品不存在")

def main():
    st.set_page_config(page_title="连锁药店管理系统", layout="wide")
    if 'user' not in st.session_state:
        login_section()
    else:
        role = st.session_state.user['role']
        st.sidebar.title(f"当前角色: {'系统管理员' if role == 0 else '药店管理员' if role == 1 else '销售员'}")
        if st.sidebar.button("退出登录"):
            st.session_state.pop('user')
            st.rerun()

        if role == 0:
            section = st.sidebar.radio("模块", ["用户管理", "药店管理"])
            if section == "用户管理":
                admin_user_section()
            else:
                admin_pharmacy_section()
        elif role == 1:
            pharmacy_admin_section()
        elif role == 2:
            sales_section()

if __name__ == "__main__":
    main()