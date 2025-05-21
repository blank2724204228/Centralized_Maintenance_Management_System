from app import db, EvaluationReport, Task, User, app
from datetime import datetime, timedelta
import random
import json

def create_evaluation_report(title, task_id, start_date, end_date, total_score, rank, grade, summary, strength_points, improvement_points, inspection_ids, category_scores):
    """创建一个新的考核报告"""
    try:
        # 获取管理员用户
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            print("找不到admin用户")
            return None
        
        # 创建新的考核报告
        report = EvaluationReport(
            title=title,
            task_id=task_id,
            start_date=start_date,
            end_date=end_date,
            total_score=total_score,
            rank=rank,
            grade=grade,
            summary=summary,
            strength_points=json.dumps(strength_points),
            improvement_points=json.dumps(improvement_points),
            inspection_ids=json.dumps(inspection_ids),
            category_scores=json.dumps(category_scores),
            generated_by=admin_user.id,
            generated_at=datetime.utcnow()
        )
        
        db.session.add(report)
        db.session.commit()
        print(f"成功创建考核报告: {title}")
        return report
    except Exception as e:
        db.session.rollback()
        print(f"创建考核报告时出错: {str(e)}")
        return None

def main():
    """添加多个考核报告"""
    with app.app_context():
        # 获取可用的任务ID列表
        tasks = Task.query.all()
        if not tasks:
            print("找不到任务，请先创建任务")
            return
        
        task_ids = [task.id for task in tasks]
        
        # 生成考核报告数据
        evaluation_reports = [
            {
                "title": "G30高速路面养护工程季度考核报告",
                "start_date": datetime(2023, 1, 1),
                "end_date": datetime(2023, 3, 31),
                "total_score": 92.5,
                "rank": 1,
                "grade": "优秀",
                "summary": "G30高速路面养护工程在本季度整体表现优秀，各项指标达到或超过预期目标。安全管理严格规范，质量控制有效，进度符合计划要求。施工现场管理有序，环保措施到位，交通组织合理。",
                "strength_points": [
                    "安全管理体系完善，安全教育培训执行到位",
                    "质量控制措施严格，施工质量符合规范要求",
                    "进度管理科学有效，各阶段工作按计划完成",
                    "文明施工措施到位，施工现场整洁有序"
                ],
                "improvement_points": [
                    "部分区域材料堆放不够规范，建议加强现场管理",
                    "夜间施工警示标志设置不足，需要增加数量和亮度"
                ],
                "category_scores": {
                    "安全管理": 93,
                    "质量控制": 94,
                    "进度管理": 91,
                    "文明施工": 92,
                    "环保措施": 90,
                    "交通组织": 95
                }
            },
            {
                "title": "G15高速桥梁加固工程月度考核报告",
                "start_date": datetime(2023, 4, 1),
                "end_date": datetime(2023, 4, 30),
                "total_score": 88.0,
                "rank": 2,
                "grade": "良好",
                "summary": "G15高速桥梁加固工程在本月度考核中整体表现良好。安全管理基本到位，质量控制有效，但在进度管理和文明施工方面存在一些不足。施工团队积极响应整改意见，持续改进工作方法。",
                "strength_points": [
                    "桥梁加固技术应用合理，施工工艺规范",
                    "材料检测严格，质量控制到位",
                    "团队协作良好，沟通顺畅高效"
                ],
                "improvement_points": [
                    "进度略有滞后，建议调整资源配置以确保按期完成",
                    "施工噪音控制不足，需加强降噪措施",
                    "部分施工区域标示不清，需规范警示标志设置"
                ],
                "category_scores": {
                    "安全管理": 90,
                    "质量控制": 92,
                    "进度管理": 85,
                    "文明施工": 84,
                    "环保措施": 87,
                    "交通组织": 90
                }
            },
            {
                "title": "G4高速隧道维修工程半年度考核报告",
                "start_date": datetime(2023, 1, 1),
                "end_date": datetime(2023, 6, 30),
                "total_score": 96.0,
                "rank": 1,
                "grade": "优秀",
                "summary": "G4高速隧道维修工程在半年度考核中表现突出，各项考核指标均达到优秀水平。项目团队安全意识强，质量管理严格，进度控制精准，文明施工成效显著，是其他项目的标杆。",
                "strength_points": [
                    "安全管理体系完善，安全培训全面深入",
                    "隧道维修技术先进，工艺精细，质量优异",
                    "进度管控精准，提前完成多个关键节点",
                    "环保意识强，废弃物处理规范环保",
                    "交通组织科学合理，对通行影响降至最低"
                ],
                "improvement_points": [
                    "可进一步完善文档管理，提高信息化水平"
                ],
                "category_scores": {
                    "安全管理": 97,
                    "质量控制": 98,
                    "进度管理": 96,
                    "文明施工": 94,
                    "环保措施": 95,
                    "交通组织": 96
                }
            },
            {
                "title": "G30高速边坡治理工程月度考核报告",
                "start_date": datetime(2023, 5, 1),
                "end_date": datetime(2023, 5, 31),
                "total_score": 84.5,
                "rank": 3,
                "grade": "良好",
                "summary": "G30高速边坡治理工程本月度考核结果为良好。项目在质量控制方面表现较好，但安全管理和进度控制方面存在不足。团队已针对发现的问题制定了整改计划，预计下月将有所改善。",
                "strength_points": [
                    "边坡加固技术应用恰当，质量控制有效",
                    "团队专业素质高，技术方案合理"
                ],
                "improvement_points": [
                    "安全防护设施不足，特别是高空作业区域，需立即加强",
                    "进度滞后较多，需调整施工计划并增加资源投入",
                    "环保措施执行不到位，需加强扬尘控制",
                    "现场管理较混乱，材料堆放无序，需规范整理"
                ],
                "category_scores": {
                    "安全管理": 80,
                    "质量控制": 89,
                    "进度管理": 78,
                    "文明施工": 82,
                    "环保措施": 81,
                    "交通组织": 86
                }
            },
            {
                "title": "G15高速排水系统改造工程季度考核报告",
                "start_date": datetime(2023, 4, 1),
                "end_date": datetime(2023, 6, 30),
                "total_score": 91.0,
                "rank": 2,
                "grade": "优秀",
                "summary": "G15高速排水系统改造工程季度考核结果为优秀。项目团队在安全管理、质量控制和环保措施方面表现突出，进度控制和文明施工方面有待加强。总体而言，项目执行良好，圆满完成了季度目标任务。",
                "strength_points": [
                    "排水系统设计合理，施工质量优良",
                    "安全管理规范，无安全事故发生",
                    "环保意识强，施工对环境影响小",
                    "技术方案创新，解决了多处技术难题"
                ],
                "improvement_points": [
                    "部分路段进度略有滞后，需加强协调",
                    "现场材料管理不够规范，需改进",
                    "夜间施工照明不足，需增加照明设备"
                ],
                "category_scores": {
                    "安全管理": 93,
                    "质量控制": 94,
                    "进度管理": 88,
                    "文明施工": 87,
                    "环保措施": 95,
                    "交通组织": 90
                }
            },
            {
                "title": "G4高速沥青路面养护工程月度考核报告",
                "start_date": datetime(2023, 6, 1),
                "end_date": datetime(2023, 6, 30),
                "total_score": 79.0,
                "rank": 4,
                "grade": "合格",
                "summary": "G4高速沥青路面养护工程本月度考核结果为合格。项目在多个方面存在明显不足，特别是安全管理、进度控制和文明施工方面问题较多。项目团队需要认真总结经验教训，加强管理，提高工作质量。",
                "strength_points": [
                    "材料质量控制较好，沥青混合料符合要求",
                    "核心施工人员技术水平较高"
                ],
                "improvement_points": [
                    "安全管理混乱，多处存在安全隐患，需立即整改",
                    "进度严重滞后，需全面调整计划",
                    "现场管理杂乱，材料堆放无序，设备摆放随意",
                    "环保措施不到位，扬尘污染严重",
                    "夜间施工警示不足，存在交通安全隐患"
                ],
                "category_scores": {
                    "安全管理": 75,
                    "质量控制": 83,
                    "进度管理": 70,
                    "文明施工": 72,
                    "环保措施": 75,
                    "交通组织": 78
                }
            },
            {
                "title": "G30高速声屏障安装工程月度考核报告",
                "start_date": datetime(2023, 7, 1),
                "end_date": datetime(2023, 7, 31),
                "total_score": 87.5,
                "rank": 3,
                "grade": "良好",
                "summary": "G30高速声屏障安装工程月度考核结果为良好。项目在质量控制和安全管理方面表现较好，进度控制基本符合计划，但在文明施工和环保措施方面存在一些不足。总体而言，项目执行情况良好。",
                "strength_points": [
                    "声屏障安装质量优良，降噪效果明显",
                    "安全管理较为规范，安全培训到位",
                    "进度控制合理，基本按计划推进"
                ],
                "improvement_points": [
                    "施工现场材料堆放不够整齐，需加强管理",
                    "环保措施执行不够到位，特别是废弃物处理",
                    "部分施工区域标示不明确，需完善警示标志"
                ],
                "category_scores": {
                    "安全管理": 89,
                    "质量控制": 91,
                    "进度管理": 88,
                    "文明施工": 83,
                    "环保措施": 84,
                    "交通组织": 87
                }
            },
            {
                "title": "G15高速标志标线更新工程季度考核报告",
                "start_date": datetime(2023, 7, 1),
                "end_date": datetime(2023, 9, 30),
                "total_score": 93.0,
                "rank": 1,
                "grade": "优秀",
                "summary": "G15高速标志标线更新工程季度考核结果为优秀。项目各方面表现均达到高水平，特别是在质量控制、安全管理和交通组织方面成绩突出。项目团队协作高效，管理规范，是养护工程的标杆项目。",
                "strength_points": [
                    "标线施工质量优异，反光效果良好，附着牢固",
                    "标志安装规范，位置准确，视认性好",
                    "安全管理严格，无安全事故发生",
                    "交通组织科学合理，施工对交通影响小",
                    "进度控制精准，提前完成计划任务"
                ],
                "improvement_points": [
                    "个别路段施工现场清理不及时，需加强管理",
                    "部分废弃材料回收处理不规范，需改进"
                ],
                "category_scores": {
                    "安全管理": 94,
                    "质量控制": 96,
                    "进度管理": 93,
                    "文明施工": 90,
                    "环保措施": 89,
                    "交通组织": 95
                }
            }
        ]
        
        # 创建考核报告
        for i, report_data in enumerate(evaluation_reports):
            # 随机选择任务ID
            task_id = random.choice(task_ids)
            
            # 随机生成检查IDs (模拟1-5个检查ID)
            inspection_ids = [random.randint(1, 20) for _ in range(random.randint(1, 5))]
            
            create_evaluation_report(
                title=report_data["title"],
                task_id=task_id,
                start_date=report_data["start_date"],
                end_date=report_data["end_date"],
                total_score=report_data["total_score"],
                rank=report_data["rank"],
                grade=report_data["grade"],
                summary=report_data["summary"],
                strength_points=report_data["strength_points"],
                improvement_points=report_data["improvement_points"],
                inspection_ids=inspection_ids,
                category_scores=report_data["category_scores"]
            )
        
        print(f"总共创建了 {len(evaluation_reports)} 个考核报告")

if __name__ == "__main__":
    main() 