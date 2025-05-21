from app import db, EvaluationCriteria, User, app
from datetime import datetime

def create_evaluation_criteria(name, category, description, max_score=10.0, weight=1.0):
    """创建一个新的评分标准"""
    try:
        # 获取管理员用户
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            print("找不到admin用户")
            return None
        
        # 创建新的评分标准
        criteria = EvaluationCriteria(
            name=name,
            category=category,
            description=description,
            max_score=max_score,
            weight=weight,
            is_active=True,
            created_by=admin_user.id,
            created_at=datetime.utcnow()
        )
        
        db.session.add(criteria)
        db.session.commit()
        print(f"成功创建评分标准: {name}")
        return criteria
    except Exception as e:
        db.session.rollback()
        print(f"创建评分标准时出错: {str(e)}")
        return None

def main():
    """添加多个评分标准"""
    with app.app_context():
        # 安全管理评分标准
        safety_criteria = [
            {
                "name": "安全防护设施配置",
                "category": "安全管理",
                "description": "评估施工现场安全防护设施的配置是否符合规范要求，包括安全网、安全帽、警示标志等。",
                "max_score": 10.0,
                "weight": 1.2
            },
            {
                "name": "安全教育培训",
                "category": "安全管理",
                "description": "评估施工人员是否接受了安全教育培训，掌握相关安全知识和应急处理能力。",
                "max_score": 10.0,
                "weight": 1.0
            },
            {
                "name": "危险作业管理",
                "category": "安全管理",
                "description": "评估高空作业、电气作业等危险作业是否按规定办理审批手续，采取安全措施。",
                "max_score": 10.0,
                "weight": 1.5
            }
        ]
        
        # 施工质量评分标准
        quality_criteria = [
            {
                "name": "材料质量控制",
                "category": "施工质量",
                "description": "评估施工材料是否符合设计和规范要求，材料进场检验是否规范。",
                "max_score": 10.0,
                "weight": 1.3
            },
            {
                "name": "施工工艺规范性",
                "category": "施工质量",
                "description": "评估施工工艺是否符合技术规范和操作标准，工艺流程是否规范。",
                "max_score": 10.0,
                "weight": 1.2
            },
            {
                "name": "质量检测记录",
                "category": "施工质量",
                "description": "评估是否按要求进行质量检测，检测记录是否完整、准确。",
                "max_score": 10.0,
                "weight": 1.0
            }
        ]
        
        # 施工进度评分标准
        progress_criteria = [
            {
                "name": "进度计划执行",
                "category": "施工进度",
                "description": "评估实际施工进度是否符合计划进度，偏差是否在允许范围内。",
                "max_score": 10.0,
                "weight": 1.0
            },
            {
                "name": "资源配置合理性",
                "category": "施工进度",
                "description": "评估人力、设备、材料等资源配置是否合理，是否满足进度要求。",
                "max_score": 10.0,
                "weight": 0.8
            }
        ]
        
        # 文明施工评分标准
        civilization_criteria = [
            {
                "name": "施工现场环境管理",
                "category": "文明施工",
                "description": "评估施工现场环境是否整洁有序，是否符合文明施工要求。",
                "max_score": 10.0,
                "weight": 0.8
            },
            {
                "name": "噪音控制",
                "category": "文明施工",
                "description": "评估是否采取有效措施控制施工噪音，减少对周边环境的影响。",
                "max_score": 10.0,
                "weight": 0.7
            },
            {
                "name": "扬尘控制",
                "category": "文明施工",
                "description": "评估是否采取有效措施控制施工扬尘，如洒水、覆盖等措施。",
                "max_score": 10.0,
                "weight": 0.7
            }
        ]
        
        # 交通组织评分标准
        traffic_criteria = [
            {
                "name": "交通疏导方案",
                "category": "交通组织",
                "description": "评估是否制定科学、合理的交通疏导方案，有效减少施工对交通的影响。",
                "max_score": 10.0,
                "weight": 1.2
            },
            {
                "name": "交通标志设置",
                "category": "交通组织",
                "description": "评估交通标志、标线等是否设置规范、清晰，能够有效引导交通。",
                "max_score": 10.0,
                "weight": 1.0
            },
            {
                "name": "施工区域隔离",
                "category": "交通组织",
                "description": "评估施工区域是否有效隔离，防止施工活动影响正常交通。",
                "max_score": 10.0,
                "weight": 1.1
            }
        ]
        
        # 环保措施评分标准
        environment_criteria = [
            {
                "name": "污水处理",
                "category": "环保措施",
                "description": "评估施工过程中产生的污水是否得到妥善处理，防止污染环境。",
                "max_score": 10.0,
                "weight": 0.9
            },
            {
                "name": "废弃物管理",
                "category": "环保措施",
                "description": "评估施工废弃物是否分类收集、及时清运，避免环境污染。",
                "max_score": 10.0,
                "weight": 0.9
            }
        ]
        
        # 合并所有标准
        all_criteria = safety_criteria + quality_criteria + progress_criteria + civilization_criteria + traffic_criteria + environment_criteria
        
        # 创建所有评分标准
        for criteria in all_criteria:
            create_evaluation_criteria(
                name=criteria["name"],
                category=criteria["category"],
                description=criteria["description"],
                max_score=criteria["max_score"],
                weight=criteria["weight"]
            )
        
        print(f"总共创建了 {len(all_criteria)} 个评分标准")

if __name__ == "__main__":
    main() 