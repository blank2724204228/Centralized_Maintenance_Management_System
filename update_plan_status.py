from app import db, ConstructionPlan, app
from datetime import datetime

def update_plan_statuses():
    """更新施工方案状态，使其在统计中可见"""
    print("开始更新施工方案状态...")
    
    with app.app_context():
        # 找出所有草稿状态的方案
        draft_plans = ConstructionPlan.query.filter_by(status='草稿').all()
        
        if not draft_plans:
            print("没有找到草稿状态的方案")
            return
        
        # 更新方案状态
        for i, plan in enumerate(draft_plans):
            # 每三个方案分配不同的状态
            if i % 4 == 0:
                plan.status = '草稿'  # 保持部分方案为草稿
            elif i % 4 == 1:
                plan.status = '已提交'  # 已批准方案对应的状态
            elif i % 4 == 2:
                plan.status = '执行中'  # 执行中方案对应的状态
            else:
                plan.status = '已完成'  # 已完成方案对应的状态
            
            # 更新时间
            plan.last_updated = datetime.utcnow()
        
        # 提交更改
        try:
            db.session.commit()
            print(f"成功更新了 {len(draft_plans)} 个方案的状态")
        except Exception as e:
            db.session.rollback()
            print(f"更新方案状态时出错: {str(e)}")

if __name__ == "__main__":
    update_plan_statuses() 