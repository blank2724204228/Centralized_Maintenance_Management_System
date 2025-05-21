from app import app, db, User, Task, datetime, timedelta

# 创建东莞市任务的脚本
def add_dongguan_tasks():
    with app.app_context():
        # 获取管理员用户
        admin_user = User.query.filter_by(username='admin').first()
        
        if not admin_user:
            print("未找到admin用户，无法创建任务")
            return
        
        now = datetime.utcnow()
        
        # 东莞市的任务列表
        dongguan_tasks = [
            Task(
                name='东莞市常虎高速K35路段路面维修',
                task_type='道路养护',
                location='东莞市常虎高速K35+200段',
                latitude=23.050585,
                longitude=113.753440,
                description='路面出现多处坑洼和龟裂，需进行全面修复，确保行车安全。',
                traffic_impact='高',
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=3),
                priority=1,
                status='待处理',
                created_by=admin_user.id,
                created_at=now
            ),
            Task(
                name='东莞市莞深高速南段绿化修剪',
                task_type='绿化养护',
                location='东莞市莞深高速南段K45-K60',
                latitude=22.914580,
                longitude=113.930598,
                description='高速路两侧绿化带需要定期修剪，确保视线良好，提升行车环境。',
                traffic_impact='低',
                start_time=now + timedelta(days=2),
                end_time=now + timedelta(days=4),
                priority=2,
                status='待处理',
                created_by=admin_user.id,
                created_at=now
            ),
            Task(
                name='东莞市虎岭高速收费站设施检修',
                task_type='设施维护',
                location='东莞市虎岭高速虎门收费站',
                latitude=22.821620,
                longitude=113.626760,
                description='收费站的ETC设备和监控摄像头需要进行全面检修和升级，确保设备正常运行。',
                traffic_impact='中',
                start_time=now + timedelta(days=3),
                end_time=now + timedelta(days=5),
                priority=2,
                status='待处理',
                created_by=admin_user.id,
                created_at=now
            ),
            Task(
                name='东莞市长安大桥钢结构加固',
                task_type='桥梁维护',
                location='东莞市长安大桥',
                latitude=22.795842,
                longitude=113.708839,
                description='大桥主体钢结构有轻微锈蚀，需要进行防腐处理和加固，确保桥梁结构安全。',
                traffic_impact='高',
                start_time=now + timedelta(days=5),
                end_time=now + timedelta(days=10),
                priority=1,
                status='待处理',
                created_by=admin_user.id,
                created_at=now
            ),
            Task(
                name='东莞市东部快速路隧道排水系统疏通',
                task_type='隧道维护',
                location='东莞市东部快速路桥头隧道',
                latitude=23.112660,
                longitude=114.100520,
                description='隧道排水系统部分堵塞，雨季有积水风险，需要彻底疏通管道和检修排水泵。',
                traffic_impact='中',
                start_time=now + timedelta(days=4),
                end_time=now + timedelta(days=6),
                priority=1,
                status='待处理',
                created_by=admin_user.id,
                created_at=now
            ),
            Task(
                name='东莞市莞深高速服务区设施更新',
                task_type='设施维护',
                location='东莞市莞深高速道滘服务区',
                latitude=22.969116,
                longitude=113.661889,
                description='服务区公共设施老化，需更换洗手间设备，翻新休息区座椅，更新照明系统。',
                traffic_impact='低',
                start_time=now + timedelta(days=7),
                end_time=now + timedelta(days=10),
                priority=3,
                status='待处理',
                created_by=admin_user.id,
                created_at=now
            ),
            Task(
                name='东莞市樟木头立交桥防撞护栏维修',
                task_type='设施维护',
                location='东莞市樟木头立交桥',
                latitude=22.915879,
                longitude=114.066384,
                description='立交桥部分防撞护栏损坏，存在安全隐患，需要及时更换和加固。',
                traffic_impact='中',
                start_time=now + timedelta(days=2),
                end_time=now + timedelta(days=3),
                priority=1,
                status='待处理',
                created_by=admin_user.id,
                created_at=now
            ),
        ]
        
        # 将任务添加到数据库
        for task in dongguan_tasks:
            db.session.add(task)
        
        db.session.commit()
        print(f"成功添加 {len(dongguan_tasks)} 个东莞市任务")

if __name__ == "__main__":
    add_dongguan_tasks() 