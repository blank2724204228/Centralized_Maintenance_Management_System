from app import db, Task, ConstructionPlan, PlanTemplate, PlanStep, PlanHistory, User, app
from datetime import datetime
import json
import random

def create_construction_plan(task_id, name, description, traffic_impact, estimated_duration, template_id=None):
    """创建一个新的施工方案"""
    # 检查任务是否存在
    task = Task.query.get(task_id)
    if not task:
        print(f"任务ID {task_id} 不存在")
        return None
    
    # 获取管理员用户
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        print("找不到admin用户")
        return None
    
    # 创建新方案
    plan = ConstructionPlan(
        name=name,
        task_id=task_id,
        template_id=template_id,
        description=description,
        traffic_impact=traffic_impact,
        estimated_duration=estimated_duration,
        status='草稿',  # 初始状态为草稿
        created_by=admin_user.id,
        created_at=datetime.utcnow()
    )
    db.session.add(plan)
    db.session.flush()  # 获取plan.id
    
    # 如果提供了模板ID，添加模板中的步骤
    if template_id:
        template = PlanTemplate.query.get(template_id)
        if template and template.steps_template:
            steps_data = json.loads(template.steps_template)
            for idx, step_data in enumerate(steps_data):
                step = PlanStep(
                    plan_id=plan.id,
                    step_number=idx + 1,
                    name=step_data.get('name', f'步骤 {idx+1}'),
                    description=step_data.get('description', ''),
                    duration=step_data.get('duration', 0),
                    resource_requirements=json.dumps(step_data.get('resource_requirements', [])),
                    prerequisites=step_data.get('prerequisites', '')
                )
                db.session.add(step)
    
    # 记录创建历史
    history = PlanHistory(
        plan_id=plan.id,
        change_type='创建',
        change_details=json.dumps({'action': '创建新方案', 'script': '自动创建'}),
        changed_by=admin_user.id
    )
    db.session.add(history)
    
    # 提交更改
    try:
        db.session.commit()
        print(f"成功创建方案: {name}, ID: {plan.id}")
        return plan
    except Exception as e:
        db.session.rollback()
        print(f"创建方案时出错: {str(e)}")
        return None

def main():
    """创建多个施工方案示例"""
    print("开始创建施工方案...")
    
    # 获取可用任务
    tasks = Task.query.all()
    if not tasks:
        print("没有可用的任务")
        return
    
    # 获取可用模板
    templates = PlanTemplate.query.all()
    template_by_task_type = {}
    for template in templates:
        if template.task_type not in template_by_task_type:
            template_by_task_type[template.task_type] = []
        template_by_task_type[template.task_type].append(template)
    
    # 为每个任务创建1-2个施工方案
    for task in tasks:
        # 创建标准方案
        standard_plan_name = f"{task.name}标准施工方案"
        standard_plan_desc = f"针对{task.location}的标准施工流程，按常规操作进行。"
        
        # 尝试找到匹配的模板
        template_id = None
        if task.task_type in template_by_task_type and template_by_task_type[task.task_type]:
            template = template_by_task_type[task.task_type][0]
            template_id = template.id
        
        create_construction_plan(
            task_id=task.id,
            name=standard_plan_name,
            description=standard_plan_desc,
            traffic_impact=random.choice(['低', '中', '高']),
            estimated_duration=random.randint(8, 48),
            template_id=template_id
        )
        
        # 50%的概率创建第二个方案（优化版）
        if random.random() > 0.5:
            optimized_plan_name = f"{task.name}优化施工方案"
            optimized_plan_desc = f"针对{task.location}的优化施工方案，减少交通影响并缩短工期。"
            
            create_construction_plan(
                task_id=task.id,
                name=optimized_plan_name,
                description=optimized_plan_desc,
                traffic_impact='低',  # 优化方案通常有较低的交通影响
                estimated_duration=int(random.randint(8, 48) * 0.8),  # 工期缩短
                template_id=template_id
            )
    
    print("施工方案创建完成！")

if __name__ == "__main__":
    with app.app_context():
        main() 