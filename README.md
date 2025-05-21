<<<<<<< HEAD
# 高速公路集中养护智能管理系统

这是一个基于Python Flask的前后端不分离系统，用于高速公路养护工作的智能化管理。系统旨在提高养护工作效率、质量和服务水平，通过集中养护管理赋能工作的数字化、自动化和智能化。

## 功能特点

- **任务管理**：支持自动加载养护工单，一键生成施工任务；支持手动录入施工任务，提供任务分类、任务进度跟踪等功能。
- **资源调配**：根据任务需求智能调配人员、设备和材料资源，实时监控资源使用情况。
- **集中养护决策**：通过数据分析和智能化决策，将多个养护项目集中在一起进行施工，减少养护施工对交通的影响。

## 技术栈

- **后端**：Python Flask
- **数据库**：SQLite (可扩展至MySQL等)
- **前端**：HTML/CSS/JavaScript，Bootstrap 5

## 安装部署

1. 克隆代码库
```bash
git clone <repository-url>
cd highway-maintenance-system
```

2. 创建虚拟环境并激活
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/MacOS
source venv/bin/activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 运行应用
```bash
python app.py
```

5. 访问应用
```
http://127.0.0.1:5000
```

## 默认账号

- 用户名：admin
- 密码：admin123

## 系统截图

![首页](screenshots/home.png)
![控制面板](screenshots/dashboard.png)
![任务管理](screenshots/tasks.png)
![资源管理](screenshots/resources.png)

## 目录结构

```
highway-maintenance-system/
├── app.py                 # 应用主文件
├── requirements.txt       # 依赖列表
├── static/                # 静态文件
│   ├── css/               # CSS文件
│   └── js/                # JavaScript文件
├── templates/             # HTML模板
└── instance/              # 数据库实例
```

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证

[MIT](LICENSE) 
=======
# Centralized_Maintenance_Management_System
集中养护管理平台
>>>>>>> 96ae409bb1c2ea9b671ecd2c5ae867d93e0c0d61
