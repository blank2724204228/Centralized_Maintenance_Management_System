import pymysql
from config import Config

# 连接到数据库
def connect_to_db():
    # 从Config获取数据库连接信息
    db_uri = Config.SQLALCHEMY_DATABASE_URI
    # 解析连接字符串
    # 格式: mysql+pymysql://username:password@host:port/database
    db_parts = db_uri.replace('mysql+pymysql://', '').split('/')
    credentials = db_parts[0].split('@')
    user_pass = credentials[0].split(':')
    host_port = credentials[1].split(':')
    
    username = user_pass[0]
    password = user_pass[1] if len(user_pass) > 1 else ''
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 3306
    database = db_parts[1]
    
    # 连接到数据库
    connection = pymysql.connect(
        host=host,
        user=username,
        password=password,
        database=database,
        port=port
    )
    
    return connection

def add_column():
    connection = connect_to_db()
    cursor = connection.cursor()
    
    try:
        # 检查列是否已存在
        cursor.execute("SHOW COLUMNS FROM task LIKE 'traffic_impact'")
        if cursor.fetchone():
            print("列traffic_impact已存在")
        else:
            # 添加列
            cursor.execute("ALTER TABLE task ADD COLUMN traffic_impact VARCHAR(50)")
            connection.commit()
            print("成功添加traffic_impact列到task表")
    except Exception as e:
        print(f"添加列时出错: {e}")
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    add_column()
    print("数据库更新完成")

print("此脚本将暂时修改app.py，以便应用可以启动")

# 读取app.py文件内容
with open('app.py', 'r', encoding='utf-8') as file:
    lines = file.readlines()

# 寻找并修改Task模型中的traffic_impact行
modified = False
for i, line in enumerate(lines):
    if 'traffic_impact = db.Column' in line:
        # 注释掉该行
        lines[i] = '    # ' + line.strip() + ' # 临时注释\n'
        modified = True
        print(f"已找到并注释第{i+1}行: {line.strip()}")
        break

# 如果找到并修改了，写回文件
if modified:
    with open('app.py', 'w', encoding='utf-8') as file:
        file.writelines(lines)
    print("已修改app.py，现在您可以启动应用")
    print("请使用数据库客户端执行以下SQL语句来添加字段:")
    print("ALTER TABLE task ADD COLUMN traffic_impact VARCHAR(50);")
    print("\n修改完成后，请恢复app.py文件（取消注释traffic_impact行）")
else:
    print("未找到traffic_impact字段行，请检查app.py文件") 