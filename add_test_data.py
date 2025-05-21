from app import app, db, TrafficData, Task, ConstructionPlan, PlanStep, User
from datetime import datetime, timedelta
import random
import json

def add_traffic_data():
    """添加交通流量测试数据"""
    print("添加交通流量测试数据...")
    
    with app.app_context():
        # 检查是否已有数据
        if TrafficData.query.count() > 0:
            print("已存在交通流量数据，跳过添加")
            return
        
        # 添加24小时的交通流量数据
        now = datetime.utcnow()
        location = '莞深高速K15+300段'
        
        for hour in range(24):
            timestamp = now - timedelta(hours=24-hour)
            
            # 模拟交通流量数据（早晚高峰）
            if 7 <= hour <= 9:  # 早高峰
                traffic_volume = random.randint(150, 200)
                avg_speed = random.randint(30, 40)
                road_status = '拥堵'
            elif 17 <= hour <= 19:  # 晚高峰
                traffic_volume = random.randint(160, 210)
                avg_speed = random.randint(25, 35)
                road_status = '拥堵'
            elif 22 <= hour or hour <= 5:  # 夜间
                traffic_volume = random.randint(40, 80)
                avg_speed = random.randint(60, 75)
                road_status = '畅通'
            else:  # 其他时段
                traffic_volume = random.randint(90, 130)
                avg_speed = random.randint(45, 60)
                road_status = '正常'
            
            traffic_data = TrafficData(
                location=location,
                timestamp=timestamp,
                traffic_volume=traffic_volume,
                avg_speed=avg_speed,
                road_status=road_status,
                construction_impact='中'
            )
            db.session.add(traffic_data)
        
        db.session.commit()
        print(f"成功添加24小时交通流量数据")

def update_construction_steps():
    """更新施工步骤状态为进行中"""
    print("更新施工步骤状态...")
    
    with app.app_context():
        # 获取进行中的任务
        active_tasks = Task.query.filter_by(status='进行中').all()
        
        if not active_tasks:
            print("没有进行中的任务，无法更新施工步骤")
            return
        
        updated_count = 0
        
        for task in active_tasks:
            # 获取任务的选中方案
            selected_plan = ConstructionPlan.query.filter_by(task_id=task.id, is_selected=True).first()
            
            if not selected_plan:
                print(f"任务 {task.name} 没有选中的方案")
                continue
            
            # 获取方案的步骤
            steps = PlanStep.query.filter_by(plan_id=selected_plan.id).order_by(PlanStep.step_number).all()
            
            if not steps:
                print(f"方案 {selected_plan.name} 没有定义步骤")
                continue
            
            # 将前三个步骤标记为进行中
            for i, step in enumerate(steps[:3]):
                if step.status == '未开始':
                    step.status = '进行中'
                    updated_count += 1
            
            db.session.commit()
        
        print(f"成功更新 {updated_count} 个施工步骤状态为进行中")

def add_test_data():
    """向数据库添加测试数据，用于可视化展示"""
    with app.app_context():
        # 确保数据库已创建
        db.create_all()
        
        # 获取管理员用户
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            print("未找到管理员用户，请先运行应用创建基础数据")
            return
        
        # 获取所有任务
        tasks = Task.query.all()
        if not tasks:
            print("未找到任务数据，请先运行应用创建基础数据")
            return
        
        # 为每个任务创建施工方案和步骤
        for task in tasks:
            # 检查是否已有选中的方案
            existing_selected = ConstructionPlan.query.filter_by(task_id=task.id, is_selected=True).first()
            if existing_selected:
                print(f"任务 '{task.name}' 已有选中方案，跳过")
                continue
            
            # 创建一个新的施工方案
            plan = ConstructionPlan(
                name=f"{task.name}标准方案",
                task_id=task.id,
                description=f"{task.name}的标准施工方案",
                traffic_impact="中" if random.random() > 0.5 else "低",
                estimated_duration=random.randint(8, 48),
                status="已执行" if task.status == "进行中" else "已批准",
                is_selected=True,
                created_by=admin_user.id,
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow()
            )
            db.session.add(plan)
            db.session.flush()  # 获取plan.id
            
            # 根据任务类型创建不同的步骤
            steps = []
            if "路面" in task.name or "道路" in task.task_type:
                steps = [
                    {"name": "现场勘察", "duration": 2, "status": "已完成" if task.status == "进行中" else "未开始"},
                    {"name": "交通管制", "duration": 1, "status": "进行中" if task.status == "进行中" else "未开始"},
                    {"name": "路面清理", "duration": 2, "status": "未开始"},
                    {"name": "沥青铺设", "duration": 4, "status": "未开始"},
                    {"name": "压实固化", "duration": 3, "status": "未开始"},
                    {"name": "质量检查", "duration": 1, "status": "未开始"},
                    {"name": "恢复通行", "duration": 1, "status": "未开始"}
                ]
            elif "桥梁" in task.name or "桥梁" in task.task_type:
                steps = [
                    {"name": "结构检查", "duration": 4, "status": "进行中" if task.status == "进行中" else "未开始"},
                    {"name": "除锈处理", "duration": 5, "status": "未开始"},
                    {"name": "螺栓更换", "duration": 8, "status": "未开始"},
                    {"name": "钢架加固", "duration": 12, "status": "未开始"},
                    {"name": "涂装防腐", "duration": 6, "status": "未开始"},
                    {"name": "质量验收", "duration": 2, "status": "未开始"}
                ]
            elif "隧道" in task.name or "隧道" in task.task_type:
                steps = [
                    {"name": "安全检查", "duration": 3, "status": "已完成" if task.status == "进行中" else "未开始"},
                    {"name": "交通管制", "duration": 2, "status": "进行中" if task.status == "进行中" else "未开始"},
                    {"name": "清洗墙面", "duration": 8, "status": "未开始"},
                    {"name": "防水检测", "duration": 4, "status": "未开始"},
                    {"name": "设备维护", "duration": 6, "status": "未开始"},
                    {"name": "照明检修", "duration": 4, "status": "未开始"},
                    {"name": "恢复通行", "duration": 1, "status": "未开始"}
                ]
            elif "绿化" in task.name or "绿化" in task.task_type:
                steps = [
                    {"name": "现场勘察", "duration": 1, "status": "已完成" if task.status == "进行中" else "未开始"},
                    {"name": "修剪准备", "duration": 2, "status": "进行中" if task.status == "进行中" else "未开始"},
                    {"name": "绿植修剪", "duration": 6, "status": "未开始"},
                    {"name": "清理垃圾", "duration": 3, "status": "未开始"},
                    {"name": "施肥养护", "duration": 2, "status": "未开始"},
                    {"name": "质量检查", "duration": 1, "status": "未开始"}
                ]
            else:  # 设施维护
                steps = [
                    {"name": "现场勘察", "duration": 2, "status": "已完成" if task.status == "进行中" else "未开始"},
                    {"name": "设备检测", "duration": 3, "status": "进行中" if task.status == "进行中" else "未开始"},
                    {"name": "更换部件", "duration": 4, "status": "未开始"},
                    {"name": "系统调试", "duration": 2, "status": "未开始"},
                    {"name": "功能验收", "duration": 1, "status": "未开始"}
                ]
            
            # 添加步骤到数据库
            for i, step_data in enumerate(steps, 1):
                step = PlanStep(
                    plan_id=plan.id,
                    step_number=i,
                    name=step_data["name"],
                    description=f"{step_data['name']}步骤描述",
                    duration=step_data["duration"],
                    resource_requirements="[]",  # 空的资源需求
                    prerequisites=str(i-1) if i > 1 else "",  # 前一步为前置条件
                    status=step_data["status"]
                )
                db.session.add(step)
            
            # 如果任务已完成，将部分步骤标记为已完成
            if task.status == "已完成":
                for step in steps:
                    step["status"] = "已完成"
        
        # 提交所有更改
        db.session.commit()
        print("测试数据添加成功！")

def main():
    """主函数"""
    print("开始添加测试数据...")
    
    # 添加交通流量数据
    add_traffic_data()
    
    # 更新施工步骤状态
    update_construction_steps()
    
    # 添加测试数据
    add_test_data()
    
    print("测试数据添加完成！")

if __name__ == "__main__":
    main() 