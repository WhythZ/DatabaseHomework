DB_CONFIG = {
    "host": "localhost",
    # 必须与docker run的-p参数左侧端口一致
    "port": 8888,
    "database": "postgres",
    "user": "gaussdb",
    # 必须与docker run的GS_PASSWORD参数值完全一致
    "password": "StrongPassword@1234567890"
}