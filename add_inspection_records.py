from app import db, Inspection, Task, User, app
from datetime import datetime, timedelta
import random
import json  # 添加json导入

def create_inspection_record(title, inspection_type, task_id, location, inspection_date, content, issues=None):
    """创建一个新的检查记录"""
    try:
        # 获取管理员用户
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            print("找不到admin用户")
            return None
        
        # 创建新的检查记录
        inspection = Inspection(
            title=title,
            inspection_type=inspection_type,
            task_id=task_id,
            location=location,
            inspection_date=inspection_date,
            inspector_id=admin_user.id,
            inspector_name=admin_user.username,
            inspector_organization=admin_user.department,
            content=content,
            issues=json.dumps(issues) if issues else None,
            status='已提交',
            created_at=datetime.utcnow()
        )
        
        db.session.add(inspection)
        db.session.commit()
        print(f"成功创建检查记录: {title}")
        return inspection
    except Exception as e:
        db.session.rollback()
        print(f"创建检查记录时出错: {str(e)}")
        return None

def main():
    """添加多个检查记录"""
    with app.app_context():
        # 获取可用的任务ID列表
        tasks = Task.query.all()
        if not tasks:
            print("找不到任务，请先创建任务")
            return
        
        task_ids = [task.id for task in tasks]
        
        # 检查类型列表
        inspection_types = ["安全检查", "质量检查", "进度检查", "环保检查", "交通组织检查"]
        
        # 检查地点列表
        locations = ["G30高速K245+500路段", "G30高速K246+200路段", "G30高速K247+100路段", 
                    "G15高速K123+400路段", "G15高速K124+300路段", "G4高速K567+800路段"]
        
        # 严重程度
        severities = ["一般", "严重", "紧急"]
        
        # 生成检查记录数据
        inspection_records = [
            {
                "title": "路面沥青层质量检查",
                "inspection_type": "质量检查",
                "location": "G30高速K245+500路段",
                "content": "对沥青路面进行了厚度、平整度和压实度检测，发现部分区域存在轻微离析现象，需进行修补处理。总体质量符合规范要求，但个别区域需要注意改进。",
                "issues": [
                    {
                        "description": "K245+520右侧车道沥青层存在轻微离析现象",
                        "severity": "一般"
                    }
                ]
            },
            {
                "title": "桥梁支座安全检查",
                "inspection_type": "安全检查",
                "location": "G15高速K123+400路段",
                "content": "对桥梁支座进行全面检查，检查支座位移、变形和锈蚀情况。发现3号桥墩支座存在明显锈蚀，存在安全隐患，需立即处理。其他支座状态良好，符合安全要求。",
                "issues": [
                    {
                        "description": "3号桥墩支座严重锈蚀，影响承载能力",
                        "severity": "紧急"
                    },
                    {
                        "description": "支座防水设施老化",
                        "severity": "一般"
                    }
                ]
            },
            {
                "title": "隧道通风系统检查",
                "inspection_type": "安全检查",
                "location": "G4高速K567+800路段",
                "content": "对隧道通风系统进行检查，包括风机运行状态、电气控制系统和监测设备。发现部分风机轴承磨损较大，噪音明显增加，需要更换。监控系统工作正常，数据传输稳定。",
                "issues": [
                    {
                        "description": "3号风机轴承磨损严重，需更换",
                        "severity": "严重"
                    }
                ]
            },
            {
                "title": "施工现场安全防护设施检查",
                "inspection_type": "安全检查",
                "location": "G30高速K246+200路段",
                "content": "检查施工现场的安全防护设施，包括警示标志、安全围栏、安全通道等。发现部分警示标志设置不规范，安全围栏存在断点，存在安全隐患，需立即整改。",
                "issues": [
                    {
                        "description": "K246+250处警示标志设置不规范",
                        "severity": "一般"
                    },
                    {
                        "description": "部分安全围栏存在断点，无法有效防护",
                        "severity": "严重"
                    }
                ]
            },
            {
                "title": "路面排水系统检查",
                "inspection_type": "质量检查",
                "location": "G15高速K124+300路段",
                "content": "检查路面排水系统，包括边沟、排水孔和集水井等设施。发现部分排水孔堵塞，影响排水效果，需及时清理。边沟整体状况良好，符合设计要求。",
                "issues": [
                    {
                        "description": "K124+350处排水孔堵塞严重",
                        "severity": "严重"
                    }
                ]
            },
            {
                "title": "施工进度检查",
                "inspection_type": "进度检查",
                "location": "G30高速K247+100路段",
                "content": "检查施工进度与计划进度的符合情况。路基工程已完成85%，比计划进度滞后约5%，主要受近期雨水天气影响。需调整施工计划和资源配置，确保总体进度不受影响。",
                "issues": [
                    {
                        "description": "路基工程进度滞后5%，需调整计划",
                        "severity": "一般"
                    }
                ]
            },
            {
                "title": "施工现场环保措施检查",
                "inspection_type": "环保检查",
                "location": "G30高速K247+100路段",
                "content": "检查施工现场的环保措施执行情况，包括扬尘控制、污水处理和废弃物处理等。发现部分区域未采取有效的扬尘控制措施，现场积尘较多。污水处理符合环保要求。",
                "issues": [
                    {
                        "description": "材料堆放区未覆盖防尘网，扬尘较多",
                        "severity": "严重"
                    }
                ]
            },
            {
                "title": "交通疏导措施检查",
                "inspection_type": "交通组织检查",
                "location": "G4高速K567+800路段",
                "content": "检查施工期间的交通疏导措施，包括交通标志、导向标志和交通管制等。发现部分交通标志设置不合理，存在安全隐患；夜间警示灯数量不足，影响夜间行车安全。",
                "issues": [
                    {
                        "description": "入口处交通指示牌设置不合理，容易引起驾驶员误解",
                        "severity": "严重"
                    },
                    {
                        "description": "夜间警示灯数量不足",
                        "severity": "一般"
                    }
                ]
            },
            {
                "title": "路面标线质量检查",
                "inspection_type": "质量检查",
                "location": "G15高速K123+400路段",
                "content": "对新铺设的路面标线进行质量检查，包括厚度、反光性能和粘结强度等。标线厚度符合设计要求，但部分区域反光性能不达标，需要重新施工。",
                "issues": [
                    {
                        "description": "K123+450至K123+500段标线反光性能不达标",
                        "severity": "一般"
                    }
                ]
            },
            {
                "title": "安全教育培训检查",
                "inspection_type": "安全检查",
                "location": "G30高速K245+500路段",
                "content": "检查施工人员的安全教育培训情况，包括培训记录、考核结果和现场操作等。发现部分新进场人员未经安全培训即上岗作业，存在重大安全隐患，需立即纠正。",
                "issues": [
                    {
                        "description": "5名新进场人员未经安全培训即上岗作业",
                        "severity": "紧急"
                    }
                ]
            }
        ]
        
        # 创建检查记录
        now = datetime.utcnow()
        for i, record in enumerate(inspection_records):
            # 随机选择任务ID
            task_id = random.choice(task_ids)
            
            # 计算检查日期（最近7天内的随机日期）
            days_ago = random.randint(0, 7)
            inspection_date = now - timedelta(days=days_ago)
            
            create_inspection_record(
                title=record["title"],
                inspection_type=record["inspection_type"],
                task_id=task_id,
                location=record["location"],
                inspection_date=inspection_date,
                content=record["content"],
                issues=record.get("issues")
            )
        
        print(f"总共创建了 {len(inspection_records)} 个检查记录")

if __name__ == "__main__":
    main() 