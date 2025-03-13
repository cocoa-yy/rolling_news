import mysql.connector
from mysql.connector import Error

db_config = {
    'host': '111.119.242.63',    # 只写 IP 地址或域名
    'port': 3306,                # 端口号单独指定，默认为 3306
    'user': 'zhukeyun',     # 替换为你的 MySQL 用户名
    'password': 'yytt0324', # 替换为你的 MySQL 密码
    'database': 'media_corpus'  # 替换为你的数据库名
}

try:
    conn = mysql.connector.connect(**db_config)
    print("连接成功！")
    conn.close()
except Error as e:
    print(f"连接失败: {e}")