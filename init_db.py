import pymysql
import os
from config import Config
import sys
from app import app, db, User, Task, Resource, ConstructionPlan, PlanStep, PlanHistory
from datetime import datetime, timedelta

def create_database():
    """创建数据库和表结构"""
    # 连接到MySQL服务器（不指定数据库）
    try:
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # 创建数据库（如果不存在）
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.DB_NAME} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"数据库 {Config.DB_NAME} 创建成功或已存在")
            
            # 使用该数据库
            cursor.execute(f"USE {Config.DB_NAME}")
            
            # 提交更改
            connection.commit()
            
        connection.close()
        return True
    except Exception as e:
        print(f"创建数据库时出错: {e}")
        return False

def initialize_tables(app):
    """创建所有表结构"""
    # 仅在这里导入db，确保数据库已创建
    from app import db
    
    # 在Flask应用上下文中创建表
    with app.app_context():
        db.create_all()
        print("所有数据表创建成功")

def create_admin_user(app):
    """创建管理员账户"""
    # 导入User模型
    from app import db, User
    
    # 在Flask应用上下文中创建用户
    with app.app_context():
        # 检查是否已存在admin用户
        admin = User.query.filter_by(username='admin').first()
        if admin is None:
            admin = User(
                username='admin',
                department='系统管理',
                role='管理员'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("管理员账户创建成功")
        else:
            print("管理员账户已存在")

if __name__ == '__main__':
    # 先创建数据库
    success = create_database()
    
    if not success:
        print("数据库创建失败，无法继续。")
        sys.exit(1)
    
    # 导入Flask应用
    from app import app
    
    # 然后初始化表和用户
    initialize_tables(app)
    create_admin_user(app)
    print("数据库初始化完成")
    
    print("正在初始化数据库...")

    with app.app_context():
        print("删除所有表...")
        db.drop_all()
        
        print("创建所有表...")
        db.create_all()
        
        print("初始化完成！")
        
        print("查看进行中的任务和选中的方案...")
        
        # 查看进行中的任务
        tasks = Task.query.filter_by(status='进行中').all()
        print(f"进行中的任务数量: {len(tasks)}")
        for task in tasks:
            print(f"- {task.name} (ID: {task.id})")
            
            # 查看选中的方案
            plans = ConstructionPlan.query.filter_by(task_id=task.id, is_selected=True).all()
            print(f"  选中的方案数量: {len(plans)}")
            for plan in plans:
                print(f"  - {plan.name} (ID: {plan.id})")
                
                # 查看方案步骤
                steps = PlanStep.query.filter_by(plan_id=plan.id).all()
                print(f"    步骤数量: {len(steps)}")
                for step in steps:
                    print(f"    - {step.name}") 