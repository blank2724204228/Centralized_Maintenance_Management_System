from app import app, db, User, Task, Resource, ConstructionPlan
from datetime import datetime, timedelta
import random

def init_construction_plans():
    """初始化施工方案数据"""
    with app.app_context():
        # 检查是否已有施工方案数据
        if ConstructionPlan.query.count() > 0:
            print("数据库中已有施工方案数据，跳过初始化")
            return
        
        # 获取管理员用户
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            print("未找到管理员用户，无法创建施工方案")
            return
        
        # 获取所有任务
        tasks = Task.query.all()
        if not tasks:
            print("未找到任务数据，无法创建施工方案")
            return
        
        now = datetime.utcnow()
        plans_created = 0
        
        # 为每个任务创建1-2个施工方案
        for task in tasks:
            # 方案1 - 标准方案
            plan1 = ConstructionPlan(
                name=f'{task.name}标准方案',
                task_id=task.id,
                description=f'针对{task.name}的标准施工方案，按照常规流程执行。',
                traffic_impact='中' if task.task_type in ['道路养护', '桥梁维护'] else '低',
                estimated_duration=24,
                status=['草稿', '已提交', '已批准', '执行中', '已完成'][random.randint(0, 4)],
                is_selected=False,
                created_by=admin_user.id,
                created_at=now - timedelta(hours=random.randint(1, 48)),
                last_updated=now - timedelta(minutes=random.randint(5, 120))
            )
            db.session.add(plan1)
            plans_created += 1
            
            # 50%概率添加第二个方案 - 优化方案
            if random.random() > 0.5:
                plan2 = ConstructionPlan(
                    name=f'{task.name}优化方案',
                    task_id=task.id,
                    description=f'针对{task.name}的优化施工方案，减少交通影响，提高效率。',
                    traffic_impact='低',
                    estimated_duration=20,
                    status=['草稿', '已提交'][random.randint(0, 1)],
                    is_selected=False,
                    created_by=admin_user.id,
                    created_at=now - timedelta(hours=random.randint(1, 24)),
                    last_updated=now - timedelta(minutes=random.randint(5, 60))
                )
                db.session.add(plan2)
                plans_created += 1
        
        db.session.commit()
        print(f"成功创建 {plans_created} 个示例施工方案")

if __name__ == '__main__':
    print("开始初始化示例数据...")
    init_construction_plans()
    print("数据初始化完成！") 