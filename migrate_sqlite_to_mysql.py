import sqlite3
import pymysql
import json
import os
from datetime import datetime
from config import Config

def convert_datetime(sqlite_datetime):
    """转换SQLite的datetime格式为MySQL兼容格式"""
    if not sqlite_datetime:
        return None
    try:
        dt = datetime.fromisoformat(sqlite_datetime.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return sqlite_datetime

def get_sqlite_tables():
    """获取SQLite数据库中的所有表"""
    conn = sqlite3.connect('instance/highway_maintenance.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [table[0] for table in cursor.fetchall()]
    conn.close()
    return tables

def get_table_columns(table):
    """获取表的列信息"""
    conn = sqlite3.connect('instance/highway_maintenance.db')
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table});")
    columns = [column[1] for column in cursor.fetchall()]
    conn.close()
    return columns

def migrate_table(table, columns):
    """迁移单个表的数据"""
    sqlite_conn = sqlite3.connect('instance/highway_maintenance.db')
    sqlite_cursor = sqlite_conn.cursor()
    
    # 连接MySQL
    mysql_conn = pymysql.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset='utf8mb4'
    )
    mysql_cursor = mysql_conn.cursor()
    
    try:
        # 获取SQLite表中的所有数据
        sqlite_cursor.execute(f"SELECT * FROM {table}")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            print(f"表 {table} 没有数据，跳过")
            return
        
        print(f"开始迁移表 {table}，共 {len(rows)} 条记录")
        
        # 为每一行数据构建INSERT语句
        for row in rows:
            # 处理数据，转换日期时间格式等
            processed_row = []
            for i, value in enumerate(row):
                if isinstance(value, str) and ('time' in columns[i].lower() or 'date' in columns[i].lower()):
                    processed_row.append(convert_datetime(value))
                else:
                    processed_row.append(value)
            
            # 构建INSERT语句
            placeholders = ', '.join(['%s'] * len(processed_row))
            columns_str = ', '.join(columns)
            sql = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
            
            # 执行INSERT
            try:
                mysql_cursor.execute(sql, processed_row)
            except Exception as e:
                print(f"插入数据时出错: {e}")
                print(f"SQL: {sql}")
                print(f"数据: {processed_row}")
                continue
        
        # 提交事务
        mysql_conn.commit()
        print(f"表 {table} 迁移完成")
        
    except Exception as e:
        print(f"迁移表 {table} 时出错: {e}")
    finally:
        sqlite_conn.close()
        mysql_conn.close()

def main():
    """主函数，执行迁移过程"""
    print("开始从SQLite迁移数据到MySQL...")
    
    # 检查SQLite数据库文件是否存在
    if not os.path.exists('instance/highway_maintenance.db'):
        print("错误: SQLite数据库文件不存在")
        return
    
    # 获取所有表
    tables = get_sqlite_tables()
    if not tables:
        print("SQLite数据库中没有找到表")
        return
    
    print(f"找到 {len(tables)} 个表: {', '.join(tables)}")
    
    # 迁移每个表
    for table in tables:
        columns = get_table_columns(table)
        migrate_table(table, columns)
    
    print("数据迁移完成")

if __name__ == "__main__":
    main() 