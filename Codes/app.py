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
        cur.execute("SELECT user_id, username, password, role, pharmacy_id FROM users")
        rows = cur.fetchall()
        users_df = pd.DataFrame(rows, columns=[desc[0] for desc in cur.description])
        role_map = {0: "系统管理员", 1: "药店管理员", 2: "销售员"}
        users_df["角色"] = users_df["role"].map(role_map)
        users_df.rename(columns={
            "user_id": "用户ID",
            "username": "用户名",
            "password": "密码",
            "pharmacy_id": "药店ID"
        }, inplace=True)
        st.dataframe(users_df[["用户ID", "用户名", "密码", "角色", "药店ID"]], use_container_width=True)

    # 添加用户部分
    st.markdown("### 添加用户")
    with st.form("添加用户表单"):
        new_username = st.text_input("用户名", key="add_username")
        new_password = st.text_input("密码", type="password", key="add_password")
        new_role = st.selectbox("角色", options=[0, 1, 2], format_func=lambda x: role_map[x], key="add_role")
        new_pharmacy_id = st.number_input("药店ID", min_value=1, step=1, key="add_pharmacy_id")
        if st.form_submit_button("添加用户"):
            manage_users("add", username=new_username, password=new_password, role=new_role, pharmacy_id=new_pharmacy_id)
            st.success("用户添加成功")
            st.rerun()

    # 删除用户部分
    st.markdown("### 删除用户")
    user_ids = users_df["用户ID"].tolist()
    user_to_delete = st.selectbox("选择要删除的用户ID", user_ids)
    if st.button("删除用户"):
        manage_users("delete", user_id=user_to_delete)
        st.success(f"用户ID {user_to_delete} 已删除")
        st.rerun()

    # 更新用户部分
    st.markdown("### 更新用户")
    user_to_update = st.selectbox("选择要更新的用户ID", user_ids, key="update_user_select")
    if user_to_update:
        user_info = users_df[users_df["用户ID"] == user_to_update].iloc[0]
        with st.form("更新用户表单"):
            username = st.text_input("用户名", value=user_info["用户名"])
            role_option = st.selectbox("角色", options=[0, 1, 2],
                                       format_func=lambda x: role_map[x],
                                       index={0: 0, 1: 1, 2: 2}[user_info["角色"] == "系统管理员" and 0 or user_info["角色"] == "药店管理员" and 1 or 2])
            pharmacy_id = st.number_input("药店ID", min_value=1, step=1, value=int(user_info["药店ID"]))
            password = st.text_input("密码（留空则不修改）", type="password")
            if st.form_submit_button("更新"):
                if password == "":
                    with get_conn() as conn:
                        with conn.cursor() as cur:
                            cur.execute("SELECT password FROM users WHERE user_id = %s", (user_to_update,))
                            password = cur.fetchone()["password"]
                manage_users("update", user_id=user_to_update, username=username, password=password, role=role_option, pharmacy_id=pharmacy_id)
                st.success("用户更新成功")
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

    # 添加药店部分
    st.markdown("### 添加药店")
    with st.form("添加药店表单"):
        new_name = st.text_input("药店名称", key="add_pharmacy_name")
        new_address = st.text_area("地址", key="add_pharmacy_address")
        if st.form_submit_button("添加药店"):
            manage_pharmacies("add", name=new_name, address=new_address)
            st.success("药店添加成功")
            st.rerun()

    # 删除药店
    st.markdown("### 删除药店")
    pharmacy_ids = df["药店ID"].tolist()
    pharmacy_to_delete = st.selectbox("选择要删除的药店ID", pharmacy_ids)
    if st.button("删除药店"):
        manage_pharmacies("delete", pharmacy_id=pharmacy_to_delete)
        st.success(f"药店ID {pharmacy_to_delete} 已删除")
        st.rerun()

    # 更新药店
    st.markdown("### 更新药店")
    pharmacy_to_update = st.selectbox("选择要更新的药店ID", pharmacy_ids, key="update_pharmacy_select")
    if pharmacy_to_update:
        pharmacy_info = df[df["药店ID"] == pharmacy_to_update].iloc[0]
        with st.form("更新药店表单"):
            name = st.text_input("药店名称", value=pharmacy_info["药店名称"])
            address = st.text_area("地址", value=pharmacy_info["地址"])
            if st.form_submit_button("更新"):
                manage_pharmacies("update", pharmacy_id=pharmacy_to_update, name=name, address=address)
                st.success("药店更新成功")
                st.rerun()

def pharmacy_admin_section():
    st.subheader("💊 药品管理")
    pharmacy_id = st.session_state.user['pharmacy_id']
    medicines = get_medicines(pharmacy_id)

    if medicines:
        df = pd.DataFrame(medicines)
        df.rename(columns={
            "medicine_id": "药品ID",
            "name": "药品名称",
            "manufacturer": "药品产商",
            "code": "药品编码",
            "price": "药品价格",
            "stock": "药品库存"
        }, inplace=True)
        st.dataframe(df, use_container_width=True)

    # 添加药品 - 修改为统一风格
    st.markdown("---")
    st.subheader("➕ 添加药品")
    with st.form("添加药品表单"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("药品名称", key="add_name")
            manufacturer = st.text_input("药品产商", key="add_manufacturer")
            code = st.text_input("药品编码", key="add_code")
        with col2:
            price = st.number_input("药品价格", min_value=0.0, step=0.1, key="add_price")
            stock = st.number_input("药品库存", min_value=0, step=1, key="add_stock")
        
        if st.form_submit_button("添加药品"):
            manage_medicines("add", name=name, manufacturer=manufacturer, code=code, 
                             price=price, stock=stock, pharmacy_id=pharmacy_id)
            st.success("药品添加成功")
            st.rerun()

    # 更新药品 - 修改为统一风格
    st.markdown("---")
    st.subheader("✏️ 更新药品信息")
    
    if medicines:
        medicine_ids = [m["medicine_id"] for m in medicines]
        selected_id = st.selectbox("选择药品ID进行更新", medicine_ids, key="update_medicine_select")
        selected_med = next((m for m in medicines if m["medicine_id"] == selected_id), None)
        
        if selected_med:
            with st.form("更新药品表单"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("药品名称", value=selected_med["name"], key="update_name")
                    manufacturer = st.text_input("药品产商", value=selected_med["manufacturer"], key="update_manufacturer")
                    code = st.text_input("药品编码", value=selected_med["code"], key="update_code")
                with col2:
                    price = st.number_input("药品价格", min_value=0.0, step=0.1, 
                                          value=float(selected_med["price"]), key="update_price")
                    stock = st.number_input("药品库存", min_value=0, step=1, 
                                          value=selected_med["stock"], key="update_stock")
                
                if st.form_submit_button("更新药品"):
                    manage_medicines("update", medicine_id=selected_id, name=name, 
                                    manufacturer=manufacturer, code=code, price=price, stock=stock)
                    st.success("药品更新成功")
                    st.rerun()
        else:
            st.info("请选择要更新的药品")
    else:
        st.info("当前没有药品可供更新")

    # 删除药品 - 保持原有风格
    st.markdown("---")
    st.subheader("🗑️ 删除药品")
    
    if medicines:
        medicine_ids = [m["medicine_id"] for m in medicines]
        st.markdown("#### 选择药品")
        delete_id = st.selectbox("选择要删除的药品ID", medicine_ids, key="delete_medicine_select")
        
        # 检查该药品是否存在销售记录
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM sales WHERE medicine_id = %s", (delete_id,))
                ref_count = cur.fetchone()['count']
        
        selected_med = next((m for m in medicines if m["medicine_id"] == delete_id), None)
        if selected_med:
            st.markdown(f"**药品名称**：{selected_med['name']}")
            st.markdown(f"**药品产商**：{selected_med['manufacturer']}")
            st.markdown(f"**药品编码**：{selected_med['code']}")
        
        # 分支1: 没有销售记录引用 - 直接删除
        if ref_count == 0:
            if st.button("确认删除药品", key="safe_delete_btn"):
                manage_medicines("delete", medicine_id=delete_id)
                st.success(f"药品ID {delete_id} 已成功删除（无销售引用）")
                st.rerun()
        
        # 分支2: 存在销售记录引用 - 提供强制删除选项
        else:
            st.warning(f"⚠️ 该药品在销售记录中有 {ref_count} 条引用，删除将导致关联数据丢失！")
            
            # 显示关联销售记录预览
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT s.sale_id, s.quantity, s.sale_time, u.username 
                        FROM sales s
                        JOIN users u ON s.user_id = u.user_id
                        WHERE s.medicine_id = %s
                        ORDER BY s.sale_time DESC
                        LIMIT 10
                    """, (delete_id,))
                    sales = cur.fetchall()
                    if sales:
                        sales_df = pd.DataFrame(sales)
                        st.dataframe(sales_df)
                    else:
                        st.info("无销售记录")
            
            # 强制删除选项
            st.markdown("#### 强制删除")
            
            # 添加额外的确认步骤
            force_confirm = st.checkbox("我理解这将永久删除所有关联数据", key="force_confirm")
            if st.button("强制删除", disabled=not force_confirm, 
                       help="删除药品及其所有销售记录", key="force_delete_btn"):
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        # 先删除关联的销售记录
                        cur.execute("DELETE FROM sales WHERE medicine_id = %s", (delete_id,))
                        # 再删除药品
                        cur.execute("DELETE FROM medicines WHERE medicine_id = %s", (delete_id,))
                        conn.commit()
                st.success(f"药品ID {delete_id} 及其 {ref_count} 条销售记录已强制删除")
                st.cache_data.clear()
                st.rerun()
    else:
        st.info("当前没有药品可供删除")

def sales_section():
    st.subheader("🛒 药品检索")
    pharmacy_id = st.session_state.user['pharmacy_id']
    user_id = st.session_state.user['user_id']

    # 读取药品数据
    medicines = get_medicines(pharmacy_id)
    if not medicines:
        st.info("当前药店暂无药品")
        return

    med_map = {f"{m['name']} | {m['manufacturer']} | {m['code']}": m for m in medicines}

    keyword = st.text_input("🔍 搜索药品 (名称/生产商/编码)")
    if keyword:
        results = search_medicines(pharmacy_id, keyword)
        if results:
            st.markdown("#### 搜索结果")
            for med in results:
                st.write(f"- {med['name']} | {med['manufacturer']} | 编码：{med['code']} | 库存：{med['stock']} | 价格：¥{med['price']:.2f}")
        else:
            st.info("未找到匹配的药品")

    st.markdown("---")
    st.subheader("💳 药品销售")

    # 选择药品
    options = list(med_map.keys())
    selected = st.selectbox("选择药品", options)

    selected_med = med_map[selected]
    st.markdown(f"**药品详情**： 库存：{selected_med['stock']}  |  价格：¥{selected_med['price']:.2f}")

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
            # 立即刷新销售记录显示
            st.rerun()
        else:
            st.error("销售失败，库存不足或药品不存在")
    
    # 销售记录查看板块
    st.markdown("---")
    st.subheader("📊 销售记录")
    
    # 时间范围选择器
    time_range = st.selectbox("时间范围", 
                             ["今日", "最近7天", "最近30天", "全部"],
                             index=0)
    
    # 获取销售记录（修复时间范围查询）
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 基础查询
            base_query = """
                SELECT s.sale_id, s.sale_time, m.name AS medicine_name, 
                       m.manufacturer, s.quantity, m.price, 
                       (s.quantity * m.price) AS total_amount,
                       u.username
                FROM sales s
                JOIN medicines m ON s.medicine_id = m.medicine_id
                JOIN users u ON s.user_id = u.user_id
                WHERE s.user_id = %s
            """
            params = [user_id]
            
            # 添加精确的时间过滤条件
            if time_range == "今日":
                base_query += " AND s.sale_time >= CURRENT_DATE"
            elif time_range == "最近7天":
                base_query += " AND s.sale_time >= CURRENT_DATE - INTERVAL '6 days'"
            elif time_range == "最近30天":
                base_query += " AND s.sale_time >= CURRENT_DATE - INTERVAL '29 days'"
            
            base_query += " ORDER BY s.sale_time DESC"
            
            cur.execute(base_query, params)
            sales_records = cur.fetchall()
    
    # 显示销售记录
    if sales_records:
        # 创建数据框
        sales_df = pd.DataFrame(sales_records)
        sales_df.rename(columns={
            "sale_id": "销售ID",
            "sale_time": "销售时间",
            "medicine_name": "药品名称",
            "manufacturer": "生产商",
            "quantity": "数量",
            "price": "单价",
            "total_amount": "总金额",
            "username": "销售员"
        }, inplace=True)
        
        # 格式化时间列（精确到秒）
        sales_df["销售时间"] = sales_df["销售时间"].dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # 计算总销售金额
        total_sales = sales_df["总金额"].sum()
        total_quantity = sales_df["数量"].sum()
        
        # 显示统计信息
        col1, col2 = st.columns(2)
        with col1:
            st.metric("总销售额", f"¥{total_sales:.2f}")
        with col2:
            st.metric("总销售数量", f"{total_quantity} 件")
        
        # 显示数据表格
        st.dataframe(sales_df[["销售时间", "药品名称", "生产商", "数量", "单价", "总金额"]], 
                     use_container_width=True,
                     hide_index=True)
        
        # 添加数据导出功能
        csv = sales_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="导出销售记录",
            data=csv,
            file_name=f"销售记录_{time_range}.csv",
            mime="text/csv"
        )
    else:
        st.info("当前时间段内无销售记录")

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