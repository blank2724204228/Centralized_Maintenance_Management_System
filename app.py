from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import inspect
import functools
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import random
from werkzeug.datastructures import MultiDict
import uuid
import pymysql
from config import Config

# 注册MySQL驱动
pymysql.install_as_MySQLdb()

# 创建应用实例
app = Flask(__name__)
app.config.from_object(Config)

# 添加响应头，解决可能的跨域问题
@app.after_request
def add_headers(response):
    # 允许从地图服务提供商加载资源
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# 添加nl2br过滤器到Jinja2环境
@app.template_filter('nl2br')
def nl2br_filter(s):
    """将文本中的换行符转换为HTML的<br>标签"""
    if s is None:
        return ''
    return s.replace('\n', '<br>')

# 添加from_json过滤器到Jinja2环境
@app.template_filter('from_json')
def from_json(value):
    """将JSON字符串转换为Python对象的过滤器"""
    if value is None or value == '':
        return []
    try:
        return json.loads(value)
    except:
        return []

# 添加enumerate函数到Jinja2环境
app.jinja_env.globals.update(enumerate=enumerate)

# 猴子补丁以解决Werkzeug版本兼容性问题
from flask.sessions import SecureCookieSession

original_set_cookie = app.response_class.set_cookie

@functools.wraps(original_set_cookie)
def set_cookie_without_partitioned(self, *args, **kwargs):
    # 移除partitioned参数，如果它存在
    kwargs.pop('partitioned', None)
    return original_set_cookie(self, *args, **kwargs)

app.response_class.set_cookie = set_cookie_without_partitioned

# 为delete_cookie方法添加类似的补丁
original_delete_cookie = app.response_class.delete_cookie

@functools.wraps(original_delete_cookie)
def delete_cookie_without_partitioned(self, *args, **kwargs):
    # 移除partitioned参数，如果它存在
    kwargs.pop('partitioned', None)
    return original_delete_cookie(self, *args, **kwargs)

app.response_class.delete_cookie = delete_cookie_without_partitioned

# 初始化数据库
db = SQLAlchemy(app)

# 初始化登录管理器
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# 数据模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    department = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    task_type = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float)  # 纬度
    longitude = db.Column(db.Float)  # 经度
    description = db.Column(db.Text)
    traffic_impact = db.Column(db.String(50))  # 交通影响程度：低、中、高
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    priority = db.Column(db.Integer)
    status = db.Column(db.String(20), default='待处理')
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resources = db.relationship('ResourceAllocation', backref='task', lazy=True)
    plans = db.relationship('ConstructionPlan', backref='task', lazy=True)

class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)  # 人员、设备、材料
    specialty = db.Column(db.String(100))  # 专业技能
    status = db.Column(db.String(20), default='可用')
    location = db.Column(db.String(200))
    allocations = db.relationship('ResourceAllocation', backref='resource', lazy=True)

class ResourceAllocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)

# 施工方案模型
class ConstructionPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('plan_template.id'), nullable=True)
    description = db.Column(db.Text)
    traffic_impact = db.Column(db.String(50))  # 交通影响程度：低、中、高
    estimated_duration = db.Column(db.Integer)  # 预计工期(小时)
    status = db.Column(db.String(20), default='草稿')  # 草稿、已提交、已批准、已执行、已完成
    is_selected = db.Column(db.Boolean, default=False)  # 是否被选为最终方案
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    steps = db.relationship('PlanStep', backref='plan', lazy=True, cascade='all, delete-orphan')
    history = db.relationship('PlanHistory', backref='plan', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'task_id': self.task_id,
            'template_id': self.template_id,
            'description': self.description,
            'traffic_impact': self.traffic_impact,
            'estimated_duration': self.estimated_duration,
            'status': self.status,
            'is_selected': self.is_selected,
            'created_by': self.created_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'last_updated': self.last_updated.strftime('%Y-%m-%d %H:%M')
        }

# 施工方案模板
class PlanTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    task_type = db.Column(db.String(50), nullable=False)  # 对应的任务类型
    description = db.Column(db.Text)
    steps_template = db.Column(db.Text)  # JSON格式存储步骤模板
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    plans = db.relationship('ConstructionPlan', backref='template', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'task_type': self.task_type,
            'description': self.description,
            'steps_template': json.loads(self.steps_template) if self.steps_template else [],
            'created_by': self.created_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

# 施工步骤
class PlanStep(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('construction_plan.id'), nullable=False)
    step_number = db.Column(db.Integer, nullable=False)  # 步骤序号
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    duration = db.Column(db.Integer)  # 预计时长(小时)
    resource_requirements = db.Column(db.Text)  # JSON格式存储资源需求
    prerequisites = db.Column(db.String(200))  # 前置步骤ID，逗号分隔
    status = db.Column(db.String(20), default='未开始')  # 未开始、进行中、已完成
    
    def to_dict(self):
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'step_number': self.step_number,
            'name': self.name,
            'description': self.description,
            'duration': self.duration,
            'resource_requirements': json.loads(self.resource_requirements) if self.resource_requirements else [],
            'prerequisites': self.prerequisites,
            'status': self.status
        }

# 方案变更历史
class PlanHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('construction_plan.id'), nullable=False)
    change_type = db.Column(db.String(50), nullable=False)  # 创建、修改、状态变更
    change_details = db.Column(db.Text)  # JSON格式存储变更详情
    changed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'change_type': self.change_type,
            'change_details': json.loads(self.change_details) if self.change_details else {},
            'changed_by': self.changed_by,
            'changed_at': self.changed_at.strftime('%Y-%m-%d %H:%M')
        }

# 考核监管模块数据模型
class Inspection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    inspection_type = db.Column(db.String(50), nullable=False)  # 施工单位内部检查、监理单位检查、其他
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    inspection_date = db.Column(db.DateTime, nullable=False)
    inspector_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    inspector_name = db.Column(db.String(80))  # 冗余存储检查人姓名
    inspector_organization = db.Column(db.String(100))  # 检查人所属单位/部门
    content = db.Column(db.Text)  # 检查内容
    issues = db.Column(db.Text)  # JSON格式存储发现的问题
    images = db.Column(db.Text)  # JSON格式存储相关图片URL
    attachments = db.Column(db.Text)  # JSON格式存储附件URL
    status = db.Column(db.String(20), default='已提交')  # 已提交、已评分、已处理
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'inspection_type': self.inspection_type,
            'task_id': self.task_id,
            'location': self.location,
            'inspection_date': self.inspection_date.strftime('%Y-%m-%d %H:%M'),
            'inspector_id': self.inspector_id,
            'inspector_name': self.inspector_name,
            'inspector_organization': self.inspector_organization,
            'content': self.content,
            'issues': json.loads(self.issues) if self.issues else [],
            'images': json.loads(self.images) if self.images else [],
            'attachments': json.loads(self.attachments) if self.attachments else [],
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

class EvaluationCriteria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 施工进度、质量、安全、文明施工等
    description = db.Column(db.Text)
    max_score = db.Column(db.Float, default=10.0)
    weight = db.Column(db.Float, default=1.0)  # 权重
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'max_score': self.max_score,
            'weight': self.weight,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

class EvaluationScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inspection_id = db.Column(db.Integer, db.ForeignKey('inspection.id'), nullable=False)
    criteria_id = db.Column(db.Integer, db.ForeignKey('evaluation_criteria.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    comment = db.Column(db.Text)
    evaluator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    evaluated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'inspection_id': self.inspection_id,
            'criteria_id': self.criteria_id,
            'score': self.score,
            'comment': self.comment,
            'evaluator_id': self.evaluator_id,
            'evaluated_at': self.evaluated_at.strftime('%Y-%m-%d %H:%M')
        }

class EvaluationReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    total_score = db.Column(db.Float)  # 总分
    rank = db.Column(db.Integer)  # 排名
    grade = db.Column(db.String(20))  # 等级评定：优秀、良好、合格、不合格
    summary = db.Column(db.Text)  # 评估摘要
    strength_points = db.Column(db.Text)  # 优点，JSON格式
    improvement_points = db.Column(db.Text)  # 改进建议，JSON格式
    inspection_ids = db.Column(db.Text)  # JSON格式存储相关检查ID
    category_scores = db.Column(db.Text)  # JSON格式存储各类别得分
    generated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'task_id': self.task_id,
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'end_date': self.end_date.strftime('%Y-%m-%d'),
            'total_score': self.total_score,
            'rank': self.rank,
            'grade': self.grade,
            'summary': self.summary,
            'strength_points': json.loads(self.strength_points) if self.strength_points else [],
            'improvement_points': json.loads(self.improvement_points) if self.improvement_points else [],
            'inspection_ids': json.loads(self.inspection_ids) if self.inspection_ids else [],
            'category_scores': json.loads(self.category_scores) if self.category_scores else {},
            'generated_by': self.generated_by,
            'generated_at': self.generated_at.strftime('%Y-%m-%d %H:%M')
        }

# 可视化相关数据模型
class TrafficData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    traffic_volume = db.Column(db.Integer)  # 交通流量
    avg_speed = db.Column(db.Float)  # 平均速度
    road_status = db.Column(db.String(50))  # 道路状态
    construction_impact = db.Column(db.String(50))  # 施工影响程度

# 方案调整记录模型
class PlanAdjustment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('construction_plan.id'), nullable=False)
    adjustment_type = db.Column(db.String(50), nullable=False)  # 步骤调整、资源调整、时间调整、交通措施调整
    adjustment_reason = db.Column(db.Text)  # 调整原因
    before_state = db.Column(db.Text)  # 调整前状态，JSON格式
    after_state = db.Column(db.Text)  # 调整后状态，JSON格式
    impact_assessment = db.Column(db.Text)  # 影响评估，JSON格式
    adjusted_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    adjusted_at = db.Column(db.DateTime, default=datetime.utcnow)
    system_recommendations = db.Column(db.Text)  # 系统建议，JSON格式
    
    def to_dict(self):
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'adjustment_type': self.adjustment_type,
            'adjustment_reason': self.adjustment_reason,
            'before_state': json.loads(self.before_state) if self.before_state else {},
            'after_state': json.loads(self.after_state) if self.after_state else {},
            'impact_assessment': json.loads(self.impact_assessment) if self.impact_assessment else {},
            'adjusted_by': self.adjusted_by,
            'adjusted_at': self.adjusted_at.strftime('%Y-%m-%d %H:%M'),
            'system_recommendations': json.loads(self.system_recommendations) if self.system_recommendations else {}
        }

# 优化方案模型
class PlanOptimization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('construction_plan.id'), nullable=False)
    optimization_type = db.Column(db.String(50), nullable=False)  # 任务顺序优化、资源分配优化、时间优化
    optimization_criteria = db.Column(db.String(50))  # 优化标准：工期最短、资源最少、交通影响最小等
    original_plan_state = db.Column(db.Text)  # 原方案状态，JSON格式
    optimized_plan_state = db.Column(db.Text)  # 优化后方案状态，JSON格式
    improvement_metrics = db.Column(db.Text)  # 改进指标，JSON格式
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_applied = db.Column(db.Boolean, default=False)  # 是否已应用到实际方案
    applied_at = db.Column(db.DateTime)  # 应用时间
    applied_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'optimization_type': self.optimization_type,
            'optimization_criteria': self.optimization_criteria,
            'original_plan_state': json.loads(self.original_plan_state) if self.original_plan_state else {},
            'optimized_plan_state': json.loads(self.optimized_plan_state) if self.optimized_plan_state else {},
            'improvement_metrics': json.loads(self.improvement_metrics) if self.improvement_metrics else {},
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'is_applied': self.is_applied,
            'applied_at': self.applied_at.strftime('%Y-%m-%d %H:%M') if self.applied_at else None,
            'applied_by': self.applied_by
        }

# 交通组织措施模型
class TrafficMeasure(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('construction_plan.id'), nullable=False)
    measure_type = db.Column(db.String(50), nullable=False)  # 交通疏导、交通管制、临时绕行
    location = db.Column(db.String(200))  # 措施位置
    description = db.Column(db.Text)  # 措施描述
    start_time = db.Column(db.DateTime)  # 开始时间
    end_time = db.Column(db.DateTime)  # 结束时间
    impact_level = db.Column(db.String(20))  # 影响程度：低、中、高
    status = db.Column(db.String(20), default='计划中')  # 计划中、执行中、已完成
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'measure_type': self.measure_type,
            'location': self.location,
            'description': self.description,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M') if self.end_time else None,
            'impact_level': self.impact_level,
            'status': self.status,
            'created_by': self.created_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 路由
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            # 记录登录日志
            log_operation(
                operation_type='用户登录',
                operation_details={'username': username},
                user_id=user.id,
                result='成功'
            )
            return redirect(url_for('dashboard'))
        flash('用户名或密码错误')
        # 记录登录失败日志
        log_operation(
            operation_type='用户登录',
            operation_details={'username': username},
            result='失败'
        )
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    # 记录登出日志
    log_operation(
        operation_type='用户登出',
        operation_details={'username': current_user.username},
        user_id=current_user.id
    )
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    tasks = Task.query.all()
    plans = ConstructionPlan.query.all()
    now = datetime.utcnow()  # 添加当前时间
    return render_template('dashboard.html', tasks=tasks, plans=plans, now=now)

@app.route('/tasks')
@login_required
def tasks():
    tasks = Task.query.all()
    return render_template('tasks.html', tasks=tasks)

@app.route('/task/new', methods=['GET', 'POST'])
@login_required
def new_task():
    if request.method == 'POST':
        # 处理经纬度字段，如果为空则设为None
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        
        task = Task(
            name=request.form.get('name'),
            task_type=request.form.get('task_type'),
            location=request.form.get('location'),
            latitude=float(latitude) if latitude else None,
            longitude=float(longitude) if longitude else None,
            description=request.form.get('description'),
            traffic_impact=request.form.get('traffic_impact'),
            start_time=datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M'),
            end_time=datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M'),
            priority=request.form.get('priority'),
            created_by=current_user.id
        )
        db.session.add(task)
        db.session.commit()
        
        # 记录创建任务日志
        log_operation(
            operation_type='创建任务',
            operation_details={
                'task_name': task.name,
                'task_type': task.task_type,
                'location': task.location,
                'traffic_impact': task.traffic_impact,
                'has_coordinates': bool(latitude and longitude)
            },
            task_id=task.id
        )
        
        flash('任务已创建')
        return redirect(url_for('tasks'))
    return render_template('new_task.html')

@app.route('/resources')
@login_required
def resources():
    resources = Resource.query.all()
    return render_template('resources.html', resources=resources)

@app.route('/resource/new', methods=['GET', 'POST'])
@login_required
def new_resource():
    if request.method == 'POST':
        resource = Resource(
            name=request.form.get('name'),
            resource_type=request.form.get('resource_type'),
            specialty=request.form.get('specialty'),
            status=request.form.get('status'),
            location=request.form.get('location')
        )
        db.session.add(resource)
        db.session.commit()
        flash('资源已添加')
        return redirect(url_for('resources'))
    return render_template('new_resource.html')

@app.route('/task/<int:task_id>')
@login_required
def task_detail(task_id):
    task = Task.query.get_or_404(task_id)
    return render_template('task_detail.html', task=task)

@app.route('/task/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    if request.method == 'POST':
        task.name = request.form.get('name')
        task.task_type = request.form.get('task_type')
        task.location = request.form.get('location')
        task.description = request.form.get('description')
        task.start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M')
        task.end_time = datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M')
        task.priority = int(request.form.get('priority'))
        task.traffic_impact = request.form.get('traffic_impact')
        
        # 可选字段
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        task.latitude = float(latitude) if latitude else None
        task.longitude = float(longitude) if longitude else None
        
        db.session.commit()
        
        # 记录任务编辑操作
        log_operation(
            operation_type='任务编辑',
            operation_details={
                'task_id': task.id,
                'task_name': task.name,
                'changes': '任务信息已更新'
            },
            task_id=task.id
        )
        
        flash('任务已更新')
        return redirect(url_for('task_detail', task_id=task.id))
    
    return render_template('edit_task.html', task=task)

@app.route('/task/<int:task_id>/allocate', methods=['GET', 'POST'])
@login_required
def allocate_resources(task_id):
    task = Task.query.get_or_404(task_id)
    resources = Resource.query.filter_by(status='可用').all()
    
    if request.method == 'POST':
        resource_ids = request.form.getlist('resources')
        quantities = request.form.getlist('quantities')
        
        # 记录资源分配详情
        allocation_details = []
        
        for i, resource_id in enumerate(resource_ids):
            if resource_id and quantities[i]:
                resource = Resource.query.get(int(resource_id))
                allocation = ResourceAllocation(
                    task_id=task.id,
                    resource_id=int(resource_id),
                    quantity=int(quantities[i]),
                    start_time=task.start_time,
                    end_time=task.end_time
                )
                db.session.add(allocation)
                
                allocation_details.append({
                    'resource_id': int(resource_id),
                    'resource_name': resource.name if resource else '未知资源',
                    'quantity': int(quantities[i])
                })
        
        db.session.commit()
        
        # 记录资源分配日志
        log_operation(
            operation_type='资源分配',
            operation_details={
                'task_name': task.name,
                'allocations': allocation_details
            },
            task_id=task.id
        )
        
        flash('资源已分配')
        return redirect(url_for('task_detail', task_id=task.id))
    
    return render_template('allocate_resources.html', task=task, resources=resources)

@app.route('/task/<int:task_id>/update_status', methods=['POST'])
@login_required
def update_task_status(task_id):
    task = Task.query.get_or_404(task_id)
    task.status = request.form.get('status')
    db.session.commit()
    flash('任务状态已更新')
    return redirect(url_for('task_detail', task_id=task.id))

@app.route('/task/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    task_name = task.name
    
    # 记录删除操作的详情
    log_details = {
        'task_id': task.id,
        'task_name': task.name,
        'task_type': task.task_type,
        'location': task.location
    }
    
    try:
        # 删除任务相关的资源分配
        ResourceAllocation.query.filter_by(task_id=task.id).delete()
        
        # 删除任务相关的施工方案和步骤
        plans = ConstructionPlan.query.filter_by(task_id=task.id).all()
        for plan in plans:
            # 删除方案相关的优化记录
            PlanOptimization.query.filter_by(plan_id=plan.id).delete()
            
            # 删除方案相关的调整记录
            PlanAdjustment.query.filter_by(plan_id=plan.id).delete()
            
            # 删除方案相关的交通措施
            TrafficMeasure.query.filter_by(plan_id=plan.id).delete()
            
            # 删除方案步骤
            PlanStep.query.filter_by(plan_id=plan.id).delete()
            
            # 删除方案历史记录
            PlanHistory.query.filter_by(plan_id=plan.id).delete()
            
            # 删除方案
            db.session.delete(plan)
        
        # 删除任务相关的检查记录
        inspections = Inspection.query.filter_by(task_id=task.id).all()
        for inspection in inspections:
            # 删除检查相关的评分
            EvaluationScore.query.filter_by(inspection_id=inspection.id).delete()
            # 删除检查记录
            db.session.delete(inspection)
        
        # 删除任务相关的评估报告
        EvaluationReport.query.filter_by(task_id=task.id).delete()
        
        # 删除任务相关的系统日志
        SystemLog.query.filter_by(task_id=task.id).update({'task_id': None})
        
        # 删除任务
        db.session.delete(task)
        db.session.commit()
        
        # 记录删除任务的日志
        log_operation(
            operation_type='删除任务',
            operation_details=log_details,
            user_id=current_user.id
        )
        
        flash(f'任务 "{task_name}" 已删除')
    except Exception as e:
        db.session.rollback()
        flash(f'删除任务失败: {str(e)}', 'danger')
        print(f"删除任务错误: {e}")
    
    return redirect(url_for('tasks'))

# 施工方案相关路由
@app.route('/plans')
@login_required
def plans():
    # 获取筛选参数
    status = request.args.get('status', '')
    traffic_impact = request.args.get('traffic_impact', '')
    task_type = request.args.get('task_type', '')
    
    # 构建查询
    query = ConstructionPlan.query
    
    # 应用筛选条件
    if status:
        query = query.filter(ConstructionPlan.status == status)
    if traffic_impact:
        query = query.filter(ConstructionPlan.traffic_impact == traffic_impact)
    
    # 获取所有符合条件的方案
    plans = query.all()
    
    # 为每个方案添加关联任务的信息
    plans_with_task = []
    for plan in plans:
        task = Task.query.get(plan.task_id)
        
        # 如果指定了任务类型筛选，且当前方案的任务类型不匹配，则跳过
        if task_type and task.task_type != task_type:
            continue
            
        plan_info = plan.to_dict()
        plan_info['task_name'] = task.name
        plan_info['task_location'] = task.location
        plan_info['task_type'] = task.task_type
        plans_with_task.append(plan_info)
    
    return render_template('plans.html', plans=plans_with_task)

@app.route('/plan_templates')
@login_required
def plan_templates():
    templates = PlanTemplate.query.all()
    
    # 预处理模板数据
    processed_templates = []
    for template in templates:
        template_dict = template.to_dict()
        # 确保steps_template是Python列表
        if template.steps_template:
            try:
                steps = json.loads(template.steps_template)
                template_dict['steps_count'] = len(steps)
            except:
                template_dict['steps_count'] = 0
        else:
            template_dict['steps_count'] = 0
        processed_templates.append(template_dict)
        
    return render_template('plan_templates.html', templates=processed_templates)

@app.route('/plan_template/new', methods=['GET', 'POST'])
@login_required
def new_plan_template():
    if request.method == 'POST':
        steps_template = request.form.get('steps_template')
        try:
            # 验证JSON格式
            if steps_template:
                json.loads(steps_template)
        except json.JSONDecodeError:
            flash('步骤模板格式错误，请提供有效的JSON格式')
            return render_template('new_plan_template.html')
            
        template = PlanTemplate(
            name=request.form.get('name'),
            task_type=request.form.get('task_type'),
            description=request.form.get('description'),
            steps_template=steps_template,
            created_by=current_user.id
        )
        db.session.add(template)
        db.session.commit()
        flash('方案模板已创建')
        return redirect(url_for('plan_templates'))
    return render_template('new_plan_template.html')

@app.route('/plan_template/<int:template_id>')
@login_required
def plan_template_detail(template_id):
    template = PlanTemplate.query.get_or_404(template_id)
    steps_data = []
    if template.steps_template:
        steps_data = json.loads(template.steps_template)
    return render_template('plan_template_detail.html', template=template, steps_data=steps_data)

@app.route('/task/<int:task_id>/plans')
@login_required
def task_plans(task_id):
    task = Task.query.get_or_404(task_id)
    plans = ConstructionPlan.query.filter_by(task_id=task_id).all()
    return render_template('task_plans.html', task=task, plans=plans)

@app.route('/task/<int:task_id>/plan/new', methods=['GET', 'POST'])
@login_required
def new_plan(task_id):
    task = Task.query.get_or_404(task_id)
    templates = PlanTemplate.query.filter_by(task_type=task.task_type).all()
    
    if request.method == 'POST':
        template_id = request.form.get('template_id')
        template = None
        
        if template_id and template_id != '0':
            template = PlanTemplate.query.get(template_id)
        
        plan = ConstructionPlan(
            name=request.form.get('name'),
            task_id=task.id,
            template_id=template_id if template_id and template_id != '0' else None,
            description=request.form.get('description'),
            traffic_impact=request.form.get('traffic_impact'),
            estimated_duration=request.form.get('estimated_duration'),
            created_by=current_user.id
        )
        db.session.add(plan)
        db.session.commit()
        
        # 如果选择了模板，自动添加模板步骤
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
            change_details=json.dumps({'action': '创建新方案'}),
            changed_by=current_user.id
        )
        db.session.add(history)
        db.session.commit()
        
        flash('施工方案已创建')
        return redirect(url_for('plan_detail', plan_id=plan.id))
    
    return render_template('new_plan.html', task=task, templates=templates)

@app.route('/plan/<int:plan_id>')
@login_required
def plan_detail(plan_id):
    plan = ConstructionPlan.query.get_or_404(plan_id)
    steps = PlanStep.query.filter_by(plan_id=plan_id).order_by(PlanStep.step_number).all()
    history = PlanHistory.query.filter_by(plan_id=plan_id).order_by(PlanHistory.changed_at.desc()).all()
    return render_template('plan_detail.html', plan=plan, steps=steps, history=history)

@app.route('/plan/<int:plan_id>/step/new', methods=['GET', 'POST'])
@login_required
def new_step(plan_id):
    plan = ConstructionPlan.query.get_or_404(plan_id)
    existing_steps = PlanStep.query.filter_by(plan_id=plan_id).all()
    
    if request.method == 'POST':
        resource_requirements = request.form.get('resource_requirements')
        try:
            # 验证JSON格式
            if resource_requirements:
                json.loads(resource_requirements)
        except json.JSONDecodeError:
            flash('资源需求格式错误，请提供有效的JSON格式')
            return render_template('new_step.html', plan=plan, existing_steps=existing_steps)
            
        next_step_number = len(existing_steps) + 1
        step = PlanStep(
            plan_id=plan.id,
            step_number=next_step_number,
            name=request.form.get('name'),
            description=request.form.get('description'),
            duration=request.form.get('duration'),
            resource_requirements=resource_requirements,
            prerequisites=request.form.get('prerequisites')
        )
        db.session.add(step)
        
        # 记录步骤添加历史
        history = PlanHistory(
            plan_id=plan.id,
            change_type='修改',
            change_details=json.dumps({'action': '添加步骤', 'step_name': step.name}),
            changed_by=current_user.id
        )
        db.session.add(history)
        
        # 更新方案最后修改时间
        plan.last_updated = datetime.utcnow()
        db.session.commit()
        
        flash('施工步骤已添加')
        return redirect(url_for('plan_detail', plan_id=plan.id))
    
    return render_template('new_step.html', plan=plan, existing_steps=existing_steps)

@app.route('/plan/<int:plan_id>/update_status', methods=['POST'])
@login_required
def update_plan_status(plan_id):
    plan = ConstructionPlan.query.get_or_404(plan_id)
    new_status = request.form.get('status')
    old_status = plan.status
    plan.status = new_status
    
    # 记录状态变更历史
    if old_status != new_status:
        history = PlanHistory(
            plan_id=plan.id,
            change_type='状态变更',
            change_details=json.dumps({
                'old_status': old_status,
                'new_status': new_status
            }),
            changed_by=current_user.id
        )
        db.session.add(history)
    
    db.session.commit()
    flash('方案状态已更新')
    return redirect(url_for('plan_detail', plan_id=plan.id))

@app.route('/task/<int:task_id>/compare_plans')
@login_required
def compare_plans(task_id):
    task = Task.query.get_or_404(task_id)
    plans = ConstructionPlan.query.filter_by(task_id=task_id).all()
    return render_template('compare_plans.html', task=task, plans=plans)

@app.route('/plan/<int:plan_id>/select', methods=['POST'])
@login_required
def select_plan(plan_id):
    plan = ConstructionPlan.query.get_or_404(plan_id)
    task = Task.query.get(plan.task_id)
    
    # 先将该任务的所有方案设为未选中
    for other_plan in task.plans:
        if other_plan.id != plan.id and other_plan.is_selected:
            other_plan.is_selected = False
            history = PlanHistory(
                plan_id=other_plan.id,
                change_type='选择状态',
                change_details=json.dumps({'is_selected': False}),
                changed_by=current_user.id
            )
            db.session.add(history)
    
    # 设置当前方案为选中
    plan.is_selected = True
    history = PlanHistory(
        plan_id=plan.id,
        change_type='选择状态',
        change_details=json.dumps({'is_selected': True}),
        changed_by=current_user.id
    )
    db.session.add(history)
    
    db.session.commit()
    flash('已选定该方案作为最终施工方案')
    return redirect(url_for('task_plans', task_id=task.id))

# 方案调整与优化模块路由
@app.route('/plan_adjustment')
@login_required
def plan_adjustment_list():
    # 获取所有方案调整记录
    adjustments = PlanAdjustment.query.order_by(PlanAdjustment.adjusted_at.desc()).all()
    
    # 获取方案和用户信息
    adjustments_with_details = []
    for adjustment in adjustments:
        plan = ConstructionPlan.query.get(adjustment.plan_id)
        task = Task.query.get(plan.task_id) if plan else None
        user = User.query.get(adjustment.adjusted_by)
        
        adjustment_dict = adjustment.to_dict()
        adjustment_dict['plan_name'] = plan.name if plan else '未知方案'
        adjustment_dict['task_name'] = task.name if task else '未知任务'
        adjustment_dict['task_id'] = task.id if task else None
        adjustment_dict['adjusted_by_name'] = user.username if user else '未知用户'
        
        adjustments_with_details.append(adjustment_dict)
    
    return render_template('plan_adjustment/list.html', adjustments=adjustments_with_details)

@app.route('/plan/<int:plan_id>/adjust', methods=['GET', 'POST'])
@login_required
def adjust_plan(plan_id):
    plan = ConstructionPlan.query.get_or_404(plan_id)
    task = Task.query.get(plan.task_id)
    steps = PlanStep.query.filter_by(plan_id=plan_id).order_by(PlanStep.step_number).all()
    traffic_measures = TrafficMeasure.query.filter_by(plan_id=plan_id).all()
    
    if request.method == 'POST':
        adjustment_type = request.form.get('adjustment_type')
        adjustment_reason = request.form.get('adjustment_reason')
        
        # 获取调整前的状态
        if adjustment_type == '步骤调整':
            before_state = json.dumps([step.to_dict() for step in steps])
            
            # 处理步骤调整
            for step in steps:
                step_id = str(step.id)
                if f'step_name_{step_id}' in request.form:
                    step.name = request.form.get(f'step_name_{step_id}')
                    step.description = request.form.get(f'step_description_{step_id}')
                    step.duration = request.form.get(f'step_duration_{step_id}')
                    step.prerequisites = request.form.get(f'step_prerequisites_{step_id}')
            
            # 重新排序步骤
            new_order = request.form.getlist('step_order')
            for i, step_id in enumerate(new_order):
                step = PlanStep.query.get(int(step_id))
                if step and step.plan_id == plan_id:
                    step.step_number = i + 1
            
            after_state = json.dumps([step.to_dict() for step in PlanStep.query.filter_by(plan_id=plan_id).all()])
            
        elif adjustment_type == '交通措施调整':
            before_state = json.dumps([measure.to_dict() for measure in traffic_measures])
            
            # 处理现有交通措施的调整
            for measure in traffic_measures:
                measure_id = str(measure.id)
                if f'measure_description_{measure_id}' in request.form:
                    measure.description = request.form.get(f'measure_description_{measure_id}')
                    measure.impact_level = request.form.get(f'measure_impact_{measure_id}')
                    measure.start_time = datetime.strptime(request.form.get(f'measure_start_{measure_id}'), '%Y-%m-%dT%H:%M')
                    measure.end_time = datetime.strptime(request.form.get(f'measure_end_{measure_id}'), '%Y-%m-%dT%H:%M')
            
            # 处理新增的交通措施
            if 'new_measure_type' in request.form and request.form.get('new_measure_type'):
                new_measure = TrafficMeasure(
                    plan_id=plan_id,
                    measure_type=request.form.get('new_measure_type'),
                    location=request.form.get('new_measure_location'),
                    description=request.form.get('new_measure_description'),
                    impact_level=request.form.get('new_measure_impact'),
                    start_time=datetime.strptime(request.form.get('new_measure_start'), '%Y-%m-%dT%H:%M'),
                    end_time=datetime.strptime(request.form.get('new_measure_end'), '%Y-%m-%dT%H:%M'),
                    created_by=current_user.id
                )
                db.session.add(new_measure)
            
            after_state = json.dumps([measure.to_dict() for measure in TrafficMeasure.query.filter_by(plan_id=plan_id).all()])
            
        else:  # 资源或时间调整
            before_state = json.dumps(plan.to_dict())
            
            # 处理方案基本信息调整
            plan.name = request.form.get('plan_name')
            plan.description = request.form.get('plan_description')
            plan.traffic_impact = request.form.get('traffic_impact')
            plan.estimated_duration = request.form.get('estimated_duration')
            
            after_state = json.dumps(plan.to_dict())
        
        # 计算调整影响
        impact_assessment = calculate_adjustment_impact(plan_id, adjustment_type, before_state, after_state)
        
        # 生成系统建议
        system_recommendations = generate_system_recommendations(plan_id, adjustment_type, impact_assessment)
        
        # 创建调整记录
        adjustment = PlanAdjustment(
            plan_id=plan_id,
            adjustment_type=adjustment_type,
            adjustment_reason=adjustment_reason,
            before_state=before_state,
            after_state=after_state,
            impact_assessment=impact_assessment,
            system_recommendations=system_recommendations,
            adjusted_by=current_user.id
        )
        db.session.add(adjustment)
        
        # 更新方案最后修改时间
        plan.last_updated = datetime.utcnow()
        
        # 记录方案历史
        history = PlanHistory(
            plan_id=plan.id,
            change_type='方案调整',
            change_details=json.dumps({
                'adjustment_type': adjustment_type,
                'adjustment_id': adjustment.id
            }),
            changed_by=current_user.id
        )
        db.session.add(history)
        
        db.session.commit()
        flash('方案调整已完成')
        return redirect(url_for('plan_detail', plan_id=plan_id))
    
    # 获取相关资源信息
    resources = Resource.query.filter_by(status='可用').all()
    resource_types = set([r.resource_type for r in resources])
    
    return render_template('plan_adjustment/adjust.html', 
                          plan=plan, 
                          task=task, 
                          steps=steps, 
                          traffic_measures=traffic_measures,
                          resources=resources,
                          resource_types=resource_types)

@app.route('/plan/<int:plan_id>/adjustment/<int:adjustment_id>')
@login_required
def view_adjustment(plan_id, adjustment_id):
    plan = ConstructionPlan.query.get_or_404(plan_id)
    adjustment = PlanAdjustment.query.get_or_404(adjustment_id)
    
    if adjustment.plan_id != plan_id:
        flash('无效的方案调整记录')
        return redirect(url_for('plan_detail', plan_id=plan_id))
    
    # 获取任务和用户信息
    task = Task.query.get(plan.task_id)
    user = User.query.get(adjustment.adjusted_by)
    
    return render_template('plan_adjustment/view.html', 
                          plan=plan, 
                          task=task, 
                          adjustment=adjustment,
                          user=user)

@app.route('/plan/<int:plan_id>/optimize', methods=['GET', 'POST'])
@login_required
def optimize_plan(plan_id):
    plan = ConstructionPlan.query.get_or_404(plan_id)
    task = Task.query.get(plan.task_id)
    steps = PlanStep.query.filter_by(plan_id=plan_id).order_by(PlanStep.step_number).all()
    
    if request.method == 'POST':
        optimization_type = request.form.get('optimization_type')
        optimization_criteria = request.form.get('optimization_criteria')
        
        # 获取原始方案状态
        original_plan_state = {}
        original_plan_state['plan'] = plan.to_dict()
        original_plan_state['steps'] = [step.to_dict() for step in steps]
        
        # 执行优化算法
        if optimization_type == '任务顺序优化':
            # 根据优化标准重新排序步骤
            optimized_steps = optimize_step_sequence(steps, optimization_criteria)
            
            # 更新步骤顺序
            for i, step_data in enumerate(optimized_steps):
                step = PlanStep.query.get(step_data['id'])
                if step:
                    step.step_number = i + 1
            
            # 计算优化后的工期
            estimated_duration = sum(step['duration'] for step in optimized_steps)
            plan.estimated_duration = estimated_duration
            
        elif optimization_type == '资源分配优化':
            # 优化资源分配
            optimized_resources = optimize_resource_allocation(plan_id, optimization_criteria)
            
            # 更新资源需求
            for step_id, resources in optimized_resources.items():
                step = PlanStep.query.get(int(step_id))
                if step:
                    step.resource_requirements = json.dumps(resources)
        
        # 获取优化后的方案状态
        optimized_plan_state = {}
        optimized_plan_state['plan'] = plan.to_dict()
        optimized_plan_state['steps'] = [step.to_dict() for step in PlanStep.query.filter_by(plan_id=plan_id).order_by(PlanStep.step_number).all()]
        
        # 计算改进指标
        improvement_metrics = calculate_improvement_metrics(original_plan_state, optimized_plan_state, optimization_criteria)
        
        # 创建优化记录
        optimization = PlanOptimization(
            plan_id=plan_id,
            optimization_type=optimization_type,
            optimization_criteria=optimization_criteria,
            original_plan_state=json.dumps(original_plan_state),
            optimized_plan_state=json.dumps(optimized_plan_state),
            improvement_metrics=json.dumps(improvement_metrics),
            created_at=datetime.utcnow(),
            is_applied=True,  # 直接应用优化结果
            applied_at=datetime.utcnow(),
            applied_by=current_user.id
        )
        db.session.add(optimization)
        
        # 更新方案最后修改时间
        plan.last_updated = datetime.utcnow()
        
        # 记录方案历史
        history = PlanHistory(
            plan_id=plan.id,
            change_type='方案优化',
            change_details=json.dumps({
                'optimization_type': optimization_type,
                'optimization_id': optimization.id
            }),
            changed_by=current_user.id
        )
        db.session.add(history)
        
        db.session.commit()
        flash('方案优化已完成并应用')
        return redirect(url_for('plan_detail', plan_id=plan_id))
    
    return render_template('plan_optimization/optimize.html', 
                          plan=plan, 
                          task=task, 
                          steps=steps)

@app.route('/plan_optimizations')
@login_required
def plan_optimization_list():
    # 获取所有方案优化记录
    optimizations = PlanOptimization.query.order_by(PlanOptimization.created_at.desc()).all()
    
    # 获取方案和用户信息
    optimizations_with_details = []
    for optimization in optimizations:
        plan = ConstructionPlan.query.get(optimization.plan_id)
        task = Task.query.get(plan.task_id) if plan else None
        user = User.query.get(optimization.applied_by) if optimization.applied_by else None
        
        optimization_dict = optimization.to_dict()
        optimization_dict['plan_name'] = plan.name if plan else '未知方案'
        optimization_dict['task_name'] = task.name if task else '未知任务'
        optimization_dict['task_id'] = task.id if task else None
        optimization_dict['applied_by_name'] = user.username if user else '未知用户'
        
        # 获取改进指标的关键数据
        if optimization.improvement_metrics:
            metrics = json.loads(optimization.improvement_metrics)
            optimization_dict['duration_change'] = metrics.get('duration_change', 0)
            optimization_dict['resource_efficiency'] = metrics.get('resource_efficiency', 0)
            optimization_dict['traffic_impact_improvement'] = metrics.get('traffic_impact_improvement', 0)
        
        optimizations_with_details.append(optimization_dict)
    
    return render_template('plan_optimization/list.html', optimizations=optimizations_with_details)

@app.route('/plan/<int:plan_id>/optimization/<int:optimization_id>')
@login_required
def view_optimization(plan_id, optimization_id):
    plan = ConstructionPlan.query.get_or_404(plan_id)
    optimization = PlanOptimization.query.get_or_404(optimization_id)
    
    if optimization.plan_id != plan_id:
        flash('无效的方案优化记录')
        return redirect(url_for('plan_detail', plan_id=plan_id))
    
    # 获取任务和用户信息
    task = Task.query.get(plan.task_id)
    user = User.query.get(optimization.applied_by) if optimization.applied_by else None
    
    # 解析原始和优化后的方案状态
    original_state = json.loads(optimization.original_plan_state) if optimization.original_plan_state else {}
    optimized_state = json.loads(optimization.optimized_plan_state) if optimization.optimized_plan_state else {}
    
    # 解析改进指标
    improvement_metrics = json.loads(optimization.improvement_metrics) if optimization.improvement_metrics else {}
    
    return render_template('plan_optimization/view.html', 
                          plan=plan, 
                          task=task, 
                          optimization=optimization,
                          user=user,
                          original_state=original_state,
                          optimized_state=optimized_state,
                          improvement_metrics=improvement_metrics)

# 辅助函数
def calculate_adjustment_impact(plan_id, adjustment_type, before_state, after_state):
    """计算方案调整的影响"""
    impact = {}
    
    # 解析调整前后的状态
    before = json.loads(before_state)
    after = json.loads(after_state)
    
    if adjustment_type == '步骤调整':
        # 计算工期变化
        before_duration = sum(step.get('duration', 0) for step in before)
        after_duration = sum(step.get('duration', 0) for step in after)
        impact['duration_change'] = after_duration - before_duration
        
        # 计算步骤数量变化
        impact['steps_count_change'] = len(after) - len(before)
        
        # 计算前置依赖关系变化
        before_deps = {step.get('id'): step.get('prerequisites', '').split(',') for step in before if step.get('prerequisites')}
        after_deps = {step.get('id'): step.get('prerequisites', '').split(',') for step in after if step.get('prerequisites')}
        impact['dependencies_changed'] = before_deps != after_deps
        
    elif adjustment_type == '交通措施调整':
        # 计算交通影响变化
        before_impact = [m.get('impact_level', '低') for m in before]
        after_impact = [m.get('impact_level', '低') for m in after]
        
        # 转换影响级别为数值
        impact_values = {'低': 1, '中': 2, '高': 3}
        before_value = sum(impact_values.get(i, 1) for i in before_impact) / len(before_impact) if before_impact else 0
        after_value = sum(impact_values.get(i, 1) for i in after_impact) / len(after_impact) if after_impact else 0
        
        impact['traffic_impact_change'] = after_value - before_value
        impact['measures_count_change'] = len(after) - len(before)
        
    else:  # 资源或时间调整
        # 计算工期变化
        impact['duration_change'] = after.get('estimated_duration', 0) - before.get('estimated_duration', 0)
        
        # 计算交通影响变化
        impact_values = {'低': 1, '中': 2, '高': 3}
        before_value = impact_values.get(before.get('traffic_impact', '低'), 1)
        after_value = impact_values.get(after.get('traffic_impact', '低'), 1)
        impact['traffic_impact_change'] = after_value - before_value
    
    # 获取方案相关联的资源分配情况
    plan = ConstructionPlan.query.get(plan_id)
    task = Task.query.get(plan.task_id)
    resource_allocations = ResourceAllocation.query.filter_by(task_id=task.id).all()
    
    # 计算资源使用变化
    if adjustment_type in ['步骤调整', '资源调整']:
        impact['resource_change'] = estimate_resource_change(before, after, resource_allocations)
    
    return json.dumps(impact)

def generate_system_recommendations(plan_id, adjustment_type, impact_assessment):
    """根据调整影响生成系统建议"""
    recommendations = {
        'resource_recommendations': [],
        'schedule_recommendations': [],
        'traffic_recommendations': []
    }
    
    impact = json.loads(impact_assessment)
    
    # 工期相关建议
    if adjustment_type in ['步骤调整', '时间调整']:
        if impact.get('duration_change', 0) > 0:
            recommendations['schedule_recommendations'].append('方案工期增加，建议检查是否可以压缩某些非关键路径的步骤工期')
        elif impact.get('duration_change', 0) < 0:
            recommendations['schedule_recommendations'].append('方案工期缩短，请确保调整后的工期能保证施工质量和安全')
    
    # 交通影响相关建议
    if adjustment_type in ['交通措施调整', '时间调整']:
        if impact.get('traffic_impact_change', 0) > 0:
            recommendations['traffic_recommendations'].append('交通影响程度增加，建议考虑在高峰期增加交通疏导措施')
            recommendations['traffic_recommendations'].append('可考虑将部分影响较大的施工安排在夜间或假期进行')
        elif impact.get('traffic_impact_change', 0) < 0:
            recommendations['traffic_recommendations'].append('交通影响程度降低，可以适当减少交通管制资源投入')
    
    # 资源相关建议
    if 'resource_change' in impact:
        resource_change = impact['resource_change']
        for resource_type, change in resource_change.items():
            if change > 0:
                recommendations['resource_recommendations'].append(f'{resource_type}类资源需求增加，建议提前准备')
            elif change < 0:
                recommendations['resource_recommendations'].append(f'{resource_type}类资源需求减少，可以调整分配到其他任务')
    
    return json.dumps(recommendations)

def estimate_resource_change(before_state, after_state, resource_allocations):
    """估算资源需求变化"""
    resource_change = {}
    
    # 处理步骤调整的情况
    if isinstance(before_state, list) and isinstance(after_state, list):
        # 提取步骤中的资源需求
        before_resources = {}
        after_resources = {}
        
        for step in before_state:
            if 'resource_requirements' in step:
                for req in step['resource_requirements']:
                    resource_type = req.get('type', '未知')
                    quantity = req.get('quantity', 0)
                    before_resources[resource_type] = before_resources.get(resource_type, 0) + quantity
        
        for step in after_state:
            if 'resource_requirements' in step:
                for req in step['resource_requirements']:
                    resource_type = req.get('type', '未知')
                    quantity = req.get('quantity', 0)
                    after_resources[resource_type] = after_resources.get(resource_type, 0) + quantity
        
        # 计算变化
        for resource_type in set(list(before_resources.keys()) + list(after_resources.keys())):
            resource_change[resource_type] = after_resources.get(resource_type, 0) - before_resources.get(resource_type, 0)
    
    return resource_change

def optimize_step_sequence(steps, criteria):
    """优化步骤顺序"""
    steps_data = [step.to_dict() for step in steps]
    
    # 构建步骤依赖图
    dependencies = {}
    for step in steps_data:
        step_id = step['id']
        prerequisites = step.get('prerequisites', '')
        if prerequisites:
            dependencies[step_id] = [int(p.strip()) for p in prerequisites.split(',') if p.strip()]
        else:
            dependencies[step_id] = []
    
    # 按照优化标准进行排序
    if criteria == '工期最短':
        # 使用关键路径算法，将较长工期的步骤尽早安排
        steps_data.sort(key=lambda s: s.get('duration', 0), reverse=True)
    elif criteria == '资源均衡':
        # 尝试均衡资源使用，避免资源使用峰值
        # 简化实现：将资源需求较大的步骤分散安排
        steps_data.sort(key=lambda s: len(s.get('resource_requirements', [])))
    elif criteria == '交通影响最小':
        # 将交通影响较大的步骤集中安排
        # 简化实现：先安排不受交通影响的步骤
        steps_data.sort(key=lambda s: 'traffic' in s.get('description', '').lower())
    
    # 尊重依赖关系，重新排序
    final_sequence = []
    scheduled = set()
    
    # 持续安排步骤直到所有步骤都被安排
    while len(final_sequence) < len(steps_data):
        for step in steps_data:
            if step['id'] in scheduled:
                continue
                
            # 检查所有前置条件是否都已安排
            if all(dep in scheduled for dep in dependencies.get(step['id'], [])):
                final_sequence.append(step)
                scheduled.add(step['id'])
    
    return final_sequence

def optimize_resource_allocation(plan_id, criteria):
    """优化资源分配"""
    steps = PlanStep.query.filter_by(plan_id=plan_id).all()
    plan = ConstructionPlan.query.get(plan_id)
    task = Task.query.get(plan.task_id)
    
    # 获取可用资源
    resources = Resource.query.filter_by(status='可用').all()
    resources_by_type = {}
    for resource in resources:
        if resource.resource_type not in resources_by_type:
            resources_by_type[resource.resource_type] = []
        resources_by_type[resource.resource_type].append(resource)
    
    # 获取已分配资源
    allocated_resources = {}
    resource_allocations = ResourceAllocation.query.filter_by(task_id=task.id).all()
    for allocation in resource_allocations:
        resource = Resource.query.get(allocation.resource_id)
        if resource:
            allocated_resources[resource.id] = allocation.quantity
    
    # 优化每个步骤的资源需求
    optimized_resources = {}
    
    for step in steps:
        step_id = step.id
        step_resources = json.loads(step.resource_requirements) if step.resource_requirements else []
        
        # 根据优化标准调整资源分配
        if criteria == '资源最少':
            # 尝试减少资源使用量，但保持最低需求
            for i, req in enumerate(step_resources):
                if req.get('quantity', 0) > 1:
                    step_resources[i]['quantity'] = max(1, int(req.get('quantity', 0) * 0.8))
                    
        elif criteria == '成本最低':
            # 尝试使用低成本资源（简化:人员>设备>材料）
            resource_priority = {'人员': 3, '设备': 2, '材料': 1}
            step_resources.sort(key=lambda r: resource_priority.get(r.get('type', ''), 0))
            
        elif criteria == '效率最高':
            # 增加关键步骤的资源分配
            if step.duration > 4:  # 假设较长工期的步骤为关键步骤
                for i, req in enumerate(step_resources):
                    step_resources[i]['quantity'] = int(req.get('quantity', 0) * 1.2)
        
        optimized_resources[step_id] = step_resources
    
    return optimized_resources

def calculate_improvement_metrics(original_state, optimized_state, criteria):
    """计算优化改进指标"""
    metrics = {}
    
    # 提取原始和优化后的方案信息
    original_plan = original_state.get('plan', {})
    optimized_plan = optimized_state.get('plan', {})
    original_steps = original_state.get('steps', [])
    optimized_steps = optimized_state.get('steps', [])
    
    # 计算工期变化
    original_duration = original_plan.get('estimated_duration', 0)
    optimized_duration = optimized_plan.get('estimated_duration', 0)
    metrics['duration_change'] = optimized_duration - original_duration
    if original_duration > 0:
        metrics['duration_change_percent'] = (metrics['duration_change'] / original_duration) * 100
    
    # 计算资源效率
    original_resources = {}
    optimized_resources = {}
    
    for step in original_steps:
        for req in step.get('resource_requirements', []):
            resource_type = req.get('type', '未知')
            quantity = req.get('quantity', 0)
            original_resources[resource_type] = original_resources.get(resource_type, 0) + quantity
    
    for step in optimized_steps:
        for req in step.get('resource_requirements', []):
            resource_type = req.get('type', '未知')
            quantity = req.get('quantity', 0)
            optimized_resources[resource_type] = optimized_resources.get(resource_type, 0) + quantity
    
    # 计算总资源数量变化
    original_total = sum(original_resources.values())
    optimized_total = sum(optimized_resources.values())
    
    if original_total > 0:
        metrics['resource_efficiency'] = ((original_total - optimized_total) / original_total) * 100
    
    # 根据优化标准设置关键指标
    if criteria == '工期最短':
        metrics['key_improvement'] = -metrics['duration_change']
    elif criteria == '资源最少':
        metrics['key_improvement'] = metrics['resource_efficiency']
    elif criteria == '交通影响最小':
        # 计算交通影响改进，简化为使用交通影响级别变化
        impact_values = {'低': 1, '中': 2, '高': 3}
        original_impact = impact_values.get(original_plan.get('traffic_impact', '低'), 1)
        optimized_impact = impact_values.get(optimized_plan.get('traffic_impact', '低'), 1)
        metrics['traffic_impact_improvement'] = original_impact - optimized_impact
        metrics['key_improvement'] = metrics['traffic_impact_improvement']
    
    return metrics

# 可视化模块路由
@app.route('/visualization')
@login_required
def visualization_dashboard():
    return render_template('visualization/dashboard.html')

@app.route('/visualization/map')
@login_required
def visualization_map():
    # 获取所有活跃任务
    active_tasks = Task.query.filter(Task.status.in_(['待处理', '进行中'])).all()
    # 获取所有资源位置
    resources = Resource.query.all()
    return render_template('visualization/map.html', tasks=active_tasks, resources=resources)

@app.route('/visualization/statistics')
@login_required
def visualization_statistics():
    # 统计数据
    task_count_by_type = db.session.query(Task.task_type, db.func.count(Task.id)).group_by(Task.task_type).all()
    resource_usage = db.session.query(Resource.resource_type, db.func.count(Resource.id)).group_by(Resource.resource_type).all()
    
    # 获取任务状态统计
    task_status_counts = db.session.query(Task.status, db.func.count(Task.id)).group_by(Task.status).all()
    
    return render_template('visualization/statistics.html', 
                           task_count_by_type=task_count_by_type,
                           resource_usage=resource_usage,
                           task_status_counts=task_status_counts)

@app.route('/visualization/3d')
@login_required
def visualization_3d():
    # 获取特定任务的详细信息用于3D可视化
    task_id = request.args.get('task_id')
    if task_id:
        task = Task.query.get_or_404(int(task_id))
        plans = ConstructionPlan.query.filter_by(task_id=task.id).all()
        selected_plan = next((p for p in plans if p.is_selected), None)
        steps = []
        if selected_plan:
            steps = PlanStep.query.filter_by(plan_id=selected_plan.id).order_by(PlanStep.step_number).all()
        return render_template('visualization/3d.html', task=task, plan=selected_plan, steps=steps)
    
    # 如果没有指定任务ID，则显示所有可以进行3D可视化的任务列表
    tasks = Task.query.filter(Task.status.in_(['待处理', '进行中'])).all()
    return render_template('visualization/3d_selection.html', tasks=tasks)

@app.route('/api/map_data')
@login_required
def api_map_data():
    """提供地图数据的API端点"""
    # 获取所有任务数据，与任务管理界面保持一致
    tasks = Task.query.all()
    resources = Resource.query.all()
    
    task_data = []
    for task in tasks:
        # 使用任务的实际经纬度数据，如果没有则使用默认值
        latitude = task.latitude if task.latitude is not None else 22.5 + (task.id * 0.01) % 0.5
        longitude = task.longitude if task.longitude is not None else 113.9 + (task.id * 0.015) % 0.6
        
        # 获取最新的施工方案信息
        plans = ConstructionPlan.query.filter_by(task_id=task.id).all()
        selected_plan = next((p for p in plans if p.is_selected), None)
        
        # 使用任务自身的交通影响信息，如果没有则使用选定方案的交通影响信息
        traffic_impact = task.traffic_impact
        if not traffic_impact and selected_plan:
            traffic_impact = selected_plan.traffic_impact
        
        task_data.append({
            'id': task.id,
            'name': task.name,
            'type': task.task_type,
            'status': task.status,
            'location': task.location,
            'latitude': latitude,
            'longitude': longitude,
            'traffic_impact': traffic_impact or '未知',
            'start_time': task.start_time.strftime('%Y-%m-%d %H:%M') if task.start_time else None,
            'end_time': task.end_time.strftime('%Y-%m-%d %H:%M') if task.end_time else None,
            'priority': task.priority
        })
    
    resource_data = []
    for resource in resources:
        # 获取资源的最新分配状态
        allocations = ResourceAllocation.query.filter_by(resource_id=resource.id).all()
        is_allocated = len(allocations) > 0
        
        # 资源的虚拟坐标
        base_lat = 22.52 + (resource.id * 0.008) % 0.3
        base_lng = 114.0 + (resource.id * 0.012) % 0.4
        
        resource_data.append({
            'id': resource.id,
            'name': resource.name,
            'type': resource.resource_type,
            'status': resource.status,
            'location': resource.location,
            'latitude': base_lat,
            'longitude': base_lng,
            'is_allocated': is_allocated
        })
    
    # 使用Flask的jsonify函数确保返回最新数据
    response = jsonify({
        'tasks': task_data,
        'resources': resource_data,
        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    # 设置不缓存的响应头
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route('/api/traffic_data')
@login_required
def api_traffic_data():
    """提供交通数据的API端点，用于图表显示"""
    try:
        # 尝试从数据库获取真实数据
        traffic_records = TrafficData.query.order_by(TrafficData.timestamp).limit(24).all()
        
        if traffic_records and len(traffic_records) > 0:
            # 使用数据库中的真实数据
            data_points = []
            for record in traffic_records:
                data_points.append({
                    'location': record.location,
                    'timestamp': record.timestamp.strftime('%Y-%m-%d %H:%M'),
                    'traffic_volume': record.traffic_volume,
                    'avg_speed': record.avg_speed,
                    'road_status': record.road_status
                })
            return jsonify(data_points)
    except Exception as e:
        print(f"获取交通数据出错: {e}")
    
    # 如果没有数据或出错，返回示例数据
    data_points = []
    now = datetime.utcnow()
    location = '莞深高速K15+300段'
    
    for hour in range(24):
        timestamp = now - timedelta(hours=24-hour)
        
        # 模拟交通流量数据（早晚高峰）
        if 7 <= hour <= 9:  # 早高峰
            traffic_volume = random.randint(150, 200)
            avg_speed = random.randint(30, 40)
        elif 17 <= hour <= 19:  # 晚高峰
            traffic_volume = random.randint(160, 210)
            avg_speed = random.randint(25, 35)
        elif 22 <= hour or hour <= 5:  # 夜间
            traffic_volume = random.randint(40, 80)
            avg_speed = random.randint(60, 75)
        else:  # 其他时段
            traffic_volume = random.randint(90, 130)
            avg_speed = random.randint(45, 60)
        
        data_points.append({
            'location': location,
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M'),
            'traffic_volume': traffic_volume,
            'avg_speed': avg_speed
        })
    
    return jsonify(data_points)

@app.route('/api/resource_usage')
@login_required
def api_resource_usage():
    """提供资源使用情况的API端点"""
    resource_types = ['人员', '设备', '材料']
    usage_data = {}
    
    for r_type in resource_types:
        # 获取该类型的所有资源
        resources = Resource.query.filter_by(resource_type=r_type).all()
        
        # 计算已分配和未分配资源
        allocated = 0
        for resource in resources:
            if ResourceAllocation.query.filter_by(resource_id=resource.id).count() > 0:
                allocated += 1
        
        usage_data[r_type] = {
            'total': len(resources),
            'allocated': allocated,
            'available': len(resources) - allocated
        }
    
    return jsonify(usage_data)

@app.route('/api/map_config')
@login_required
def api_map_config():
    """提供地图配置的API端点"""
    config = {
        'provider': app.config['MAP_PROVIDER'],
        'tianditu_key': app.config['TIANDITU_KEY'],
        'center': [22.54, 114.05],  # 默认中心位置
        'zoom': 9  # 默认缩放级别
    }
    return jsonify(config)

@app.route('/api/recent_activities')
@login_required
def api_recent_activities():
    """提供最近施工活动数据的API端点"""
    try:
        # 获取最近更新的施工方案（按last_updated降序排序，取前10个）
        print("开始查询最近施工方案...")
        recent_plans = ConstructionPlan.query.order_by(ConstructionPlan.last_updated.desc()).limit(10).all()
        print(f"查询到 {len(recent_plans)} 个施工方案")
        
        activities = []
        
        for plan in recent_plans:
            # 获取方案对应的任务
            task = Task.query.get(plan.task_id)
            if not task:
                print(f"未找到方案 {plan.id} 对应的任务 {plan.task_id}")
                continue
                
            # 添加方案信息到活动列表，重点包含方案名称、任务类型和状态
            activity = {
                'plan_id': plan.id,
                'plan_name': plan.name,
                'task_type': task.task_type,
                'status': plan.status,
                'last_updated': plan.last_updated.strftime('%Y-%m-%d %H:%M')
            }
            activities.append(activity)
            print(f"添加活动: {activity}")
        
        if activities:
            print(f"返回 {len(activities)} 个活动")
            return jsonify(activities)
        else:
            print("未找到活动数据，将返回示例数据")
    except Exception as e:
        import traceback
        print(f"获取施工活动数据出错: {e}")
        print(traceback.format_exc())
    
    # 如果没有数据或出错，返回示例数据
    activities = [
        {
            'plan_id': 1,
            'plan_name': '莞深高速K15+300段路面修补方案',
            'task_type': '道路养护',
            'status': '已提交',
            'last_updated': '2024-05-21 02:54'
        },
        {
            'plan_id': 2,
            'plan_name': '莞深高速K15+300段路面修补方案(夜间版)',
            'task_type': '道路养护',
            'status': '草稿',
            'last_updated': '2024-05-21 02:57'
        },
        {
            'plan_id': 3,
            'plan_name': '龙林高速S22桥梁钢架检修标准方案',
            'task_type': '桥梁维护',
            'status': '执行中',
            'last_updated': '2024-05-21 02:59'
        }
    ]
    
    print("返回示例活动数据")
    return jsonify(activities)

@app.route('/api/test_db')
@login_required
def api_test_db():
    """测试数据库连接和查询的API端点"""
    try:
        # 测试用户表
        users_count = User.query.count()
        # 测试任务表
        tasks_count = Task.query.count()
        # 测试施工方案表
        plans_count = ConstructionPlan.query.count()
        
        # 获取最近的5个施工方案
        recent_plans = []
        if plans_count > 0:
            plans = ConstructionPlan.query.order_by(ConstructionPlan.last_updated.desc()).limit(5).all()
            for plan in plans:
                recent_plans.append({
                    'id': plan.id,
                    'name': plan.name,
                    'status': plan.status,
                    'last_updated': plan.last_updated.strftime('%Y-%m-%d %H:%M:%S')
                })
        
        return jsonify({
            'success': True,
            'database_status': 'connected',
            'counts': {
                'users': users_count,
                'tasks': tasks_count,
                'plans': plans_count
            },
            'recent_plans': recent_plans
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'error_details': error_details
        })

# 初始化数据库
with app.app_context():
    db.create_all()
    # 确保有一个管理员用户
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', department='管理部', role='管理员')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
    
    # 添加示例资源数据
    if Resource.query.count() == 0:
        # 人员资源
        resources = [
            Resource(name='养护队伍A', resource_type='人员', specialty='道路养护', status='可用', location='东部基地'),
            Resource(name='养护队伍B', resource_type='人员', specialty='桥梁维护', status='可用', location='西部基地'),
            Resource(name='养护队伍C', resource_type='人员', specialty='隧道维护', status='可用', location='南部基地'),
            Resource(name='绿化养护队', resource_type='人员', specialty='绿化养护', status='可用', location='中心基地'),
            Resource(name='设施维护团队', resource_type='人员', specialty='设施维护', status='可用', location='北部基地'),
            # 设备资源
            Resource(name='路面修补车', resource_type='设备', specialty='道路养护', status='可用', location='设备仓库'),
            Resource(name='钢架检测车', resource_type='设备', specialty='桥梁维护', status='可用', location='设备仓库'),
            Resource(name='隧道清洗机', resource_type='设备', specialty='隧道维护', status='可用', location='设备仓库'),
            Resource(name='绿化剪枝车', resource_type='设备', specialty='绿化养护', status='可用', location='设备仓库'),
            Resource(name='电子设备检测仪', resource_type='设备', specialty='设施维护', status='可用', location='设备仓库'),
            # 材料资源
            Resource(name='沥青混凝土', resource_type='材料', specialty='道路养护', status='可用', location='材料仓库'),
            Resource(name='钢筋材料', resource_type='材料', specialty='桥梁维护', status='可用', location='材料仓库'),
            Resource(name='防水材料', resource_type='材料', specialty='隧道维护', status='可用', location='材料仓库'),
            Resource(name='植物肥料', resource_type='材料', specialty='绿化养护', status='可用', location='材料仓库'),
            Resource(name='电缆线材', resource_type='材料', specialty='设施维护', status='可用', location='材料仓库'),
        ]
        for resource in resources:
            db.session.add(resource)
        db.session.commit()
    
    # 添加示例任务数据
    if Task.query.count() == 0:
        admin_user = User.query.filter_by(username='admin').first()
        now = datetime.utcnow()
        
        tasks = [
            Task(
                name='莞深高速K15+300沥青路面修补',
                task_type='道路养护',
                location='莞深高速K15+300段',
                latitude=22.940131,
                longitude=113.874493,
                description='路面出现裂缝和坑洼，需要进行沥青路面修补，确保行车安全。',
                start_time=now,
                end_time=now + timedelta(days=1),
                priority=1,
                status='进行中',  # 改为进行中
                created_by=admin_user.id,
                created_at=now
            ),
            Task(
                name='龙林高速S22桥梁钢架检修',
                task_type='桥梁维护',
                location='龙林高速S22桥梁',
                latitude=22.674600,
                longitude=114.034805,
                description='桥梁钢架需要定期检修，更换老化螺栓，加固钢架结构。',
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=3),
                priority=2,
                status='待处理',
                created_by=admin_user.id,
                created_at=now
            ),
            Task(
                name='常虎高速虎门港支线隧道清洗',
                task_type='隧道维护',
                location='常虎高速虎门港支线隧道',
                latitude=22.826285,
                longitude=113.616410,
                description='隧道内壁积累灰尘和污垢，需要进行全面清洗，并检查防水系统。',
                start_time=now + timedelta(days=2),
                end_time=now + timedelta(days=4),
                priority=3,
                status='待处理',
                created_by=admin_user.id,
                created_at=now
            ),
            Task(
                name='深外环高速中央分隔带绿化修剪',
                task_type='绿化养护',
                location='深外环高速东莞段中央分隔带',
                latitude=22.746679,
                longitude=113.751376,
                description='中央分隔带植被生长过于茂盛，需要进行修剪整理，确保行车视线。',
                start_time=now + timedelta(days=3),
                end_time=now + timedelta(days=5),
                priority=2,
                status='待处理',
                created_by=admin_user.id,
                created_at=now
            ),
            Task(
                name='惠常高速甬莞段路灯设施检修',
                task_type='设施维护',
                location='惠常高速甬莞段',
                latitude=22.803556,
                longitude=113.928452,
                description='路灯设施出现故障，部分路段夜间照明不足，需要检修更换损坏元件。',
                start_time=now,
                end_time=now + timedelta(hours=12),
                priority=1,
                status='进行中',
                created_by=admin_user.id,
                created_at=now - timedelta(hours=24)
            ),
            Task(
                name='莞番高速广龙段标识牌维护',
                task_type='设施维护',
                location='莞番高速广龙段',
                latitude=22.712345,
                longitude=113.845678,
                description='标识牌字迹模糊，部分标识牌歪斜，需要进行维护更换。',
                start_time=now - timedelta(days=1),
                end_time=now,
                priority=2,
                status='已完成',
                created_by=admin_user.id,
                created_at=now - timedelta(days=3)
            ),
        ]
        
        for task in tasks:
            db.session.add(task)
        db.session.commit()
        
        # 创建一个基本的方案模板
        if PlanTemplate.query.count() == 0:
            road_maintenance_steps = [
                {
                    "name": "现场勘察",
                    "description": "对损坏路面进行勘察评估",
                    "duration": 2,
                    "resource_requirements": [
                        {"type": "人员", "quantity": 2, "unit": "人"}
                    ],
                    "prerequisites": ""
                },
                {
                    "name": "交通管制",
                    "description": "设置安全区域和交通导流措施",
                    "duration": 1,
                    "resource_requirements": [
                        {"type": "人员", "quantity": 4, "unit": "人"},
                        {"type": "设备", "quantity": 1, "unit": "套"}
                    ],
                    "prerequisites": "1"
                },
                {
                    "name": "路面清理",
                    "description": "清理破损路面及周边区域",
                    "duration": 2,
                    "resource_requirements": [
                        {"type": "人员", "quantity": 3, "unit": "人"},
                        {"type": "设备", "quantity": 1, "unit": "台"}
                    ],
                    "prerequisites": "2"
                },
                {
                    "name": "材料准备与混合",
                    "description": "准备沥青混凝土并按比例混合",
                    "duration": 2,
                    "resource_requirements": [
                        {"type": "人员", "quantity": 2, "unit": "人"},
                        {"type": "材料", "quantity": 500, "unit": "kg"}
                    ],
                    "prerequisites": "2"
                },
                {
                    "name": "路面铺设修补",
                    "description": "将混合好的材料铺设到损坏区域",
                    "duration": 4,
                    "resource_requirements": [
                        {"type": "人员", "quantity": 5, "unit": "人"},
                        {"type": "设备", "quantity": 2, "unit": "台"},
                        {"type": "材料", "quantity": 500, "unit": "kg"}
                    ],
                    "prerequisites": "3,4"
                },
                {
                    "name": "压实与养护",
                    "description": "使用压路机压实修补区域并养护",
                    "duration": 3,
                    "resource_requirements": [
                        {"type": "人员", "quantity": 3, "unit": "人"},
                        {"type": "设备", "quantity": 1, "unit": "台"}
                    ],
                    "prerequisites": "5"
                },
                {
                    "name": "质量检查",
                    "description": "检查修补质量是否符合要求",
                    "duration": 1,
                    "resource_requirements": [
                        {"type": "人员", "quantity": 2, "unit": "人"}
                    ],
                    "prerequisites": "6"
                },
                {
                    "name": "撤除交通管制",
                    "description": "撤除安全区域和交通导流措施",
                    "duration": 1,
                    "resource_requirements": [
                        {"type": "人员", "quantity": 4, "unit": "人"}
                    ],
                    "prerequisites": "7"
                }
            ]
            
            template = PlanTemplate(
                name='道路养护标准流程',
                task_type='道路养护',
                description='标准道路养护流程，适用于沥青路面修补作业',
                steps_template=json.dumps(road_maintenance_steps),
                created_by=admin_user.id
            )
            db.session.add(template)
            
            # 添加桥梁维护模板
            bridge_maintenance_steps = [
                {
                    "name": "桥梁结构检查",
                    "description": "对桥梁结构进行全面检查，识别问题区域",
                    "duration": 4,
                    "resource_requirements": [
                        {"type": "人员", "quantity": 3, "unit": "人"},
                        {"type": "设备", "quantity": 1, "unit": "套"}
                    ],
                    "prerequisites": ""
                },
                {
                    "name": "交通管制设置",
                    "description": "设置安全区域和交通导流措施",
                    "duration": 2,
                    "resource_requirements": [
                        {"type": "人员", "quantity": 6, "unit": "人"},
                        {"type": "设备", "quantity": 2, "unit": "套"}
                    ],
                    "prerequisites": "1"
                },
                {
                    "name": "钢架除锈处理",
                    "description": "清理钢架表面锈蚀部分",
                    "duration": 5,
                    "resource_requirements": [
                        {"type": "人员", "quantity": 4, "unit": "人"},
                        {"type": "设备", "quantity": 2, "unit": "台"}
                    ],
                    "prerequisites": "2"
                },
                {
                    "name": "结构加固材料准备",
                    "description": "准备钢筋、混凝土等加固材料",
                    "duration": 3,
                    "resource_requirements": [
                        {"type": "人员", "quantity": 3, "unit": "人"},
                        {"type": "材料", "quantity": 800, "unit": "kg"}
                    ],
                    "prerequisites": "2"
                },
                {
                    "name": "结构加固施工",
                    "description": "对桥梁薄弱部位进行加固",
                    "duration": 8,
                    "resource_requirements": [
                        {"type": "人员", "quantity": 8, "unit": "人"},
                        {"type": "设备", "quantity": 3, "unit": "台"},
                        {"type": "材料", "quantity": 800, "unit": "kg"}
                    ],
                    "prerequisites": "3,4"
                },
                {
                    "name": "防腐处理",
                    "description": "对钢架结构进行防腐处理",
                    "duration": 6,
                    "resource_requirements": [
                        {"type": "人员", "quantity": 5, "unit": "人"},
                        {"type": "材料", "quantity": 200, "unit": "L"}
                    ],
                    "prerequisites": "5"
                },
                {
                    "name": "质量验收",
                    "description": "对加固维护工作进行质量验收",
                    "duration": 2,
                    "resource_requirements": [
                        {"type": "人员", "quantity": 3, "unit": "人"},
                        {"type": "设备", "quantity": 1, "unit": "台"}
                    ],
                    "prerequisites": "6"
                },
                {
                    "name": "撤除管制",
                    "description": "撤除交通管制措施，恢复正常通行",
                    "duration": 2,
                    "resource_requirements": [
                        {"type": "人员", "quantity": 6, "unit": "人"}
                    ],
                    "prerequisites": "7"
                }
            ]
            
            bridge_template = PlanTemplate(
                name='桥梁维护标准流程',
                task_type='桥梁维护',
                description='桥梁钢架检修和加固标准流程',
                steps_template=json.dumps(bridge_maintenance_steps),
                created_by=admin_user.id
            )
            db.session.add(bridge_template)
            
            db.session.commit()
        
        # 为道路养护任务创建一个施工方案示例
        if ConstructionPlan.query.count() == 0:
            # 获取道路养护任务和模板
            road_task = Task.query.filter_by(task_type='道路养护').first()
            road_template = PlanTemplate.query.filter_by(task_type='道路养护').first()
            
            if road_task and road_template:
                # 创建方案
                road_plan = ConstructionPlan(
                    name='莞深高速K15+300段路面修补方案',
                    task_id=road_task.id,
                    template_id=road_template.id,
                    description='针对莞深高速K15+300段路面裂缝和坑洼的修补方案，采用标准沥青路面修补流程。',
                    traffic_impact='中',
                    estimated_duration=16,  # 总工时
                    status='已提交',
                    created_by=admin_user.id
                )
                db.session.add(road_plan)
                db.session.flush()  # 获取plan_id
                
                # 添加施工步骤
                steps_data = json.loads(road_template.steps_template)
                for idx, step_data in enumerate(steps_data):
                    step = PlanStep(
                        plan_id=road_plan.id,
                        step_number=idx + 1,
                        name=step_data.get('name'),
                        description=step_data.get('description', ''),
                        duration=step_data.get('duration', 0),
                        resource_requirements=json.dumps(step_data.get('resource_requirements', [])),
                        prerequisites=step_data.get('prerequisites', '')
                    )
                    db.session.add(step)
                
                # 记录方案创建历史
                history = PlanHistory(
                    plan_id=road_plan.id,
                    change_type='创建',
                    change_details=json.dumps({'action': '创建新方案', 'template_used': road_template.name}),
                    changed_by=admin_user.id
                )
                db.session.add(history)
                
                # 将方案标记为已选中
                road_plan.is_selected = True
                
                # 创建一个替代方案进行比较
                alt_road_plan = ConstructionPlan(
                    name='莞深高速K15+300段路面修补方案(夜间版)',
                    task_id=road_task.id,
                    template_id=road_template.id,
                    description='针对莞深高速K15+300段路面的夜间修补方案，减少对日间交通的影响。',
                    traffic_impact='低',
                    estimated_duration=20,  # 夜间工作，总工时略长
                    status='草稿',
                    created_by=admin_user.id
                )
                db.session.add(alt_road_plan)
                db.session.flush()
                
                # 添加施工步骤（夜间版有所调整）
                for idx, step_data in enumerate(steps_data):
                    # 夜间版的步骤有些微调整
                    duration_modifier = 1.2 if idx in [2, 4, 5] else 1  # 某些步骤在夜间需要更长时间
                    step = PlanStep(
                        plan_id=alt_road_plan.id,
                        step_number=idx + 1,
                        name=step_data.get('name') + "(夜间)" if idx in [1, 2, 4, 5, 7] else step_data.get('name'),
                        description=step_data.get('description', '') + (
                            "，夜间施工需增加照明设备。" if idx in [2, 4, 5] else ""
                        ),
                        duration=int(step_data.get('duration', 0) * duration_modifier),
                        resource_requirements=json.dumps(step_data.get('resource_requirements', [])),
                        prerequisites=step_data.get('prerequisites', '')
                    )
                    db.session.add(step)
                
                # 记录方案创建历史
                history = PlanHistory(
                    plan_id=alt_road_plan.id,
                    change_type='创建',
                    change_details=json.dumps({'action': '创建新方案', 'template_used': road_template.name, 'note': '夜间施工版本'}),
                    changed_by=admin_user.id
                )
                db.session.add(history)
                
                db.session.commit()

@app.route('/plan_detail/<int:plan_id>', methods=['GET'])
@login_required
def plan_detail_redirect(plan_id):
    return redirect(url_for('plan_detail', plan_id=plan_id))

# 考核监管模块路由
@app.route('/inspection')
@login_required
def inspection_list():
    # 获取筛选参数
    task_id = request.args.get('task_id', type=int)
    inspection_type = request.args.get('type')
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # 构建基础查询
    query = Inspection.query
    
    # 应用筛选条件
    if task_id:
        query = query.filter(Inspection.task_id == task_id)
    if inspection_type:
        query = query.filter(Inspection.inspection_type == inspection_type)
    if status:
        query = query.filter(Inspection.status == status)
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Inspection.inspection_date >= start_date)
        except ValueError:
            flash('开始日期格式无效', 'error')
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            end_date = end_date + timedelta(days=1)  # 包含当天
            query = query.filter(Inspection.inspection_date < end_date)
        except ValueError:
            flash('结束日期格式无效', 'error')
    
    # 按日期降序排序，最新检查排在前面
    inspections = query.order_by(Inspection.inspection_date.desc()).all()
    
    # 获取任务列表供筛选使用
    tasks = Task.query.all()
    
    return render_template('inspection/inspection_list.html', 
                           inspections=inspections, 
                           tasks=tasks,
                           current_filters={
                               'task_id': task_id,
                               'type': inspection_type,
                               'status': status,
                               'start_date': start_date,
                               'end_date': end_date
                           })

@app.route('/inspection/new', methods=['GET', 'POST'])
@login_required
def new_inspection():
    if request.method == 'POST':
        # 获取基本信息
        title = request.form.get('title')
        inspection_type = request.form.get('inspection_type')
        task_id = request.form.get('task_id', type=int)
        location = request.form.get('location')
        inspection_date_str = request.form.get('inspection_date')
        content = request.form.get('content')
        
        # 获取多条问题数据
        issues_data = []
        issue_descriptions = request.form.getlist('issue_description')
        issue_severities = request.form.getlist('issue_severity')
        
        for i in range(len(issue_descriptions)):
            if issue_descriptions[i].strip():  # 只添加非空问题
                issues_data.append({
                    'description': issue_descriptions[i],
                    'severity': issue_severities[i] if i < len(issue_severities) else '一般',
                    'status': '未处理'
                })
        
        # 创建新的检查记录
        try:
            inspection_date = datetime.strptime(inspection_date_str, '%Y-%m-%d %H:%M')
            
            inspection = Inspection(
                title=title,
                inspection_type=inspection_type,
                task_id=task_id,
                location=location,
                inspection_date=inspection_date,
                inspector_id=current_user.id,
                inspector_name=current_user.username,
                inspector_organization=current_user.department,
                content=content,
                issues=json.dumps(issues_data),
                status='已提交'
            )
            
            db.session.add(inspection)
            db.session.commit()
            
            # 记录操作日志
            log_operation(
                operation_type='创建检查记录',
                operation_details=json.dumps({
                    'inspection_id': inspection.id,
                    'title': inspection.title,
                    'task_id': inspection.task_id
                }),
                user_id=current_user.id
            )
            
            flash('检查记录创建成功！', 'success')
            return redirect(url_for('inspection_detail', inspection_id=inspection.id))
        except Exception as e:
            db.session.rollback()
            flash(f'创建检查记录失败: {str(e)}', 'error')
    
    # GET 请求处理
    tasks = Task.query.all()
    return render_template('inspection/new_inspection.html', tasks=tasks)

@app.route('/inspection/<int:inspection_id>')
@login_required
def inspection_detail(inspection_id):
    inspection = Inspection.query.get_or_404(inspection_id)
    task = Task.query.get(inspection.task_id)
    
    # 获取相关的评分信息（如果已评分）
    scores = EvaluationScore.query.filter_by(inspection_id=inspection_id).all()
    criteria_dict = {}
    
    if scores:
        # 查询所有相关的评分标准
        criteria_ids = [score.criteria_id for score in scores]
        criteria_list = EvaluationCriteria.query.filter(EvaluationCriteria.id.in_(criteria_ids)).all()
        criteria_dict = {c.id: c for c in criteria_list}
    
    return render_template('inspection/inspection_detail.html', 
                          inspection=inspection, 
                          task=task, 
                          scores=scores,
                          criteria=criteria_dict)

@app.route('/inspection/<int:inspection_id>/evaluate', methods=['GET', 'POST'])
@login_required
def evaluate_inspection(inspection_id):
    inspection = Inspection.query.get_or_404(inspection_id)
    
    if request.method == 'POST':
        # 获取所有评分数据
        criteria_ids = request.form.getlist('criteria_id', type=int)
        scores = request.form.getlist('score', type=float)
        comments = request.form.getlist('comment')
        
        try:
            # 删除之前的评分（如果有）
            EvaluationScore.query.filter_by(inspection_id=inspection_id).delete()
            
            # 添加新的评分
            for i in range(len(criteria_ids)):
                if i < len(scores):  # 确保索引有效
                    score = EvaluationScore(
                        inspection_id=inspection_id,
                        criteria_id=criteria_ids[i],
                        score=scores[i],
                        comment=comments[i] if i < len(comments) else '',
                        evaluator_id=current_user.id
                    )
                    db.session.add(score)
            
            # 更新检查记录状态
            inspection.status = '已评分'
            db.session.commit()
            
            # 记录操作日志
            log_operation(
                operation_type='评分检查记录',
                operation_details=json.dumps({
                    'inspection_id': inspection.id,
                    'title': inspection.title,
                    'criteria_count': len(criteria_ids)
                }),
                user_id=current_user.id
            )
            
            flash('评分已保存！', 'success')
            return redirect(url_for('inspection_detail', inspection_id=inspection_id))
        except Exception as e:
            db.session.rollback()
            flash(f'保存评分失败: {str(e)}', 'error')
    
    # GET 请求处理
    # 获取所有活跃的评分标准
    criteria = EvaluationCriteria.query.filter_by(is_active=True).order_by(EvaluationCriteria.category).all()
    
    # 获取现有评分（如果有）
    existing_scores = EvaluationScore.query.filter_by(inspection_id=inspection_id).all()
    scores_dict = {score.criteria_id: score for score in existing_scores}
    
    return render_template('inspection/evaluate_inspection.html', 
                          inspection=inspection, 
                          criteria=criteria,
                          scores=scores_dict)

@app.route('/criteria')
@login_required
def criteria_list():
    criteria = EvaluationCriteria.query.order_by(EvaluationCriteria.category, EvaluationCriteria.name).all()
    
    # 按类别分组
    criteria_by_category = {}
    for c in criteria:
        if c.category not in criteria_by_category:
            criteria_by_category[c.category] = []
        criteria_by_category[c.category].append(c)
    
    return render_template('inspection/criteria_list.html', 
                          criteria_by_category=criteria_by_category)

@app.route('/criteria/new', methods=['GET', 'POST'])
@login_required
def new_criteria():
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        description = request.form.get('description')
        max_score = request.form.get('max_score', type=float, default=10.0)
        weight = request.form.get('weight', type=float, default=1.0)
        
        try:
            criteria = EvaluationCriteria(
                name=name,
                category=category,
                description=description,
                max_score=max_score,
                weight=weight,
                created_by=current_user.id
            )
            
            db.session.add(criteria)
            db.session.commit()
            
            flash('评分标准创建成功！', 'success')
            return redirect(url_for('criteria_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'创建评分标准失败: {str(e)}', 'error')
    
    return render_template('inspection/new_criteria.html')

@app.route('/criteria/<int:criteria_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_criteria(criteria_id):
    criteria = EvaluationCriteria.query.get_or_404(criteria_id)
    
    if request.method == 'POST':
        criteria.name = request.form.get('name')
        criteria.category = request.form.get('category')
        criteria.description = request.form.get('description')
        criteria.max_score = request.form.get('max_score', type=float, default=10.0)
        criteria.weight = request.form.get('weight', type=float, default=1.0)
        criteria.is_active = 'is_active' in request.form
        
        try:
            db.session.commit()
            flash('评分标准已更新！', 'success')
            return redirect(url_for('criteria_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'更新评分标准失败: {str(e)}', 'error')
    
    return render_template('inspection/edit_criteria.html', criteria=criteria)

@app.route('/reports')
@login_required
def report_list():
    # 获取筛选参数
    task_id = request.args.get('task_id', type=int)
    grade = request.args.get('grade')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # 构建查询
    query = EvaluationReport.query
    
    if task_id:
        query = query.filter(EvaluationReport.task_id == task_id)
    if grade:
        query = query.filter(EvaluationReport.grade == grade)
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(EvaluationReport.end_date >= start_date)
        except ValueError:
            flash('开始日期格式无效', 'error')
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            end_date = end_date + timedelta(days=1)  # 包含当天
            query = query.filter(EvaluationReport.start_date < end_date)
        except ValueError:
            flash('结束日期格式无效', 'error')
    
    # 按生成日期降序排序
    reports = query.order_by(EvaluationReport.generated_at.desc()).all()
    
    # 获取任务列表供筛选使用
    tasks = Task.query.all()
    
    return render_template('inspection/report_list.html', 
                          reports=reports, 
                          tasks=tasks,
                          current_filters={
                              'task_id': task_id,
                              'grade': grade,
                              'start_date': start_date,
                              'end_date': end_date
                          })

@app.route('/reports/new', methods=['GET', 'POST'])
@login_required
def new_report():
    if request.method == 'POST':
        task_id = request.form.get('task_id', type=int)
        title = request.form.get('title')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            
            # 获取该任务在指定时间范围内的所有已评分检查
            inspections = Inspection.query.filter(
                Inspection.task_id == task_id,
                Inspection.inspection_date >= start_date,
                Inspection.inspection_date <= end_date + timedelta(days=1),
                Inspection.status == '已评分'
            ).all()
            
            if not inspections:
                flash('所选时间范围内没有已评分的检查记录', 'error')
                tasks = Task.query.all()
                return render_template('inspection/new_report.html', tasks=tasks)
            
            # 收集所有检查ID
            inspection_ids = [insp.id for insp in inspections]
            
            # 获取所有评分
            all_scores = EvaluationScore.query.filter(EvaluationScore.inspection_id.in_(inspection_ids)).all()
            
            # 获取所有标准
            criteria_ids = set(score.criteria_id for score in all_scores)
            all_criteria = EvaluationCriteria.query.filter(EvaluationCriteria.id.in_(criteria_ids)).all()
            criteria_dict = {c.id: c for c in all_criteria}
            
            # 按类别计算得分
            category_scores = {}
            total_weighted_score = 0
            total_weight = 0
            
            for category in set(c.category for c in all_criteria):
                category_criteria = [c for c in all_criteria if c.category == category]
                category_total = 0
                category_max = 0
                
                for criteria in category_criteria:
                    criteria_scores = [s.score for s in all_scores if s.criteria_id == criteria.id]
                    if criteria_scores:
                        avg_score = sum(criteria_scores) / len(criteria_scores)
                        category_total += avg_score * criteria.weight
                        category_max += criteria.max_score * criteria.weight
                        total_weighted_score += avg_score * criteria.weight
                        total_weight += criteria.weight
                
                if category_max > 0:
                    category_percentage = (category_total / category_max) * 100
                    category_scores[category] = {
                        'score': round(category_total, 2),
                        'max': round(category_max, 2),
                        'percentage': round(category_percentage, 2)
                    }
            
            # 计算总分（百分比）
            if total_weight > 0:
                total_score = (total_weighted_score / total_weight) * 10  # 转换为10分制
            else:
                total_score = 0
            
            # 确定等级
            if total_score >= 9:
                grade = '优秀'
            elif total_score >= 8:
                grade = '良好'
            elif total_score >= 6:
                grade = '合格'
            else:
                grade = '不合格'
            
            # 生成优点和改进建议
            strengths = []
            improvements = []
            
            # 找出得分高的方面作为优点
            for category, data in category_scores.items():
                if data['percentage'] >= 85:
                    strengths.append(f"{category}表现优异，得分率{data['percentage']}%")
            
            # 找出得分低的方面作为改进建议
            for category, data in category_scores.items():
                if data['percentage'] < 70:
                    improvements.append(f"需加强{category}方面的工作，当前得分率仅{data['percentage']}%")
            
            # 创建报告
            report = EvaluationReport(
                title=title,
                task_id=task_id,
                start_date=start_date,
                end_date=end_date,
                total_score=round(total_score, 2),
                grade=grade,
                summary=f"基于{len(inspections)}次检查的综合评估，总体评级为{grade}。",
                strength_points=json.dumps(strengths),
                improvement_points=json.dumps(improvements),
                inspection_ids=json.dumps(inspection_ids),
                category_scores=json.dumps(category_scores),
                generated_by=current_user.id
            )
            
            # 确定排名 (与其他同类任务比较)
            task = Task.query.get(task_id)
            similar_reports = EvaluationReport.query.join(Task).filter(
                Task.task_type == task.task_type,
                EvaluationReport.id != report.id  # 排除当前报告
            ).all()
            
            better_reports = sum(1 for r in similar_reports if r.total_score > total_score)
            report.rank = better_reports + 1  # 排名是比它好的数量+1
            
            db.session.add(report)
            db.session.commit()
            
            flash('考核报告生成成功！', 'success')
            return redirect(url_for('report_detail', report_id=report.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'生成报告失败: {str(e)}', 'error')
    
    # GET 请求处理
    tasks = Task.query.all()
    return render_template('inspection/new_report.html', tasks=tasks)

@app.route('/reports/<int:report_id>')
@login_required
def report_detail(report_id):
    report = EvaluationReport.query.get_or_404(report_id)
    task = Task.query.get(report.task_id)
    
    # 获取报告中包含的检查记录
    inspection_ids = json.loads(report.inspection_ids) if report.inspection_ids else []
    inspections = Inspection.query.filter(Inspection.id.in_(inspection_ids)).all() if inspection_ids else []
    
    # 获取类别得分数据
    category_scores = json.loads(report.category_scores) if report.category_scores else {}
    
    # 处理每个类别的分数，添加百分比属性
    processed_category_scores = {}
    for category, score in category_scores.items():
        # 将简单的分数转换为包含更多信息的对象
        if isinstance(score, (int, float)):
            # 如果是简单数值，设置最大分为100，并计算百分比
            processed_category_scores[category] = {
                'score': score,
                'max': 100,
                'percentage': score
            }
        else:
            # 如果已经是字典，添加百分比属性
            if isinstance(score, dict) and 'score' in score and 'max' in score:
                score['percentage'] = round((score['score'] / score['max']) * 100)
                processed_category_scores[category] = score
            else:
                # 否则处理为简单数值
                processed_category_scores[category] = {
                    'score': score,
                    'max': 100,
                    'percentage': score
                }
    
    # 处理优点和改进建议
    strengths = json.loads(report.strength_points) if report.strength_points else []
    improvements = json.loads(report.improvement_points) if report.improvement_points else []
    
    return render_template('inspection/report_detail.html',
                          report=report,
                          task=task,
                          inspections=inspections,
                          category_scores=processed_category_scores,
                          strengths=strengths,
                          improvements=improvements)

@app.route('/reports/statistics')
@login_required
def report_statistics():
    # 获取筛选参数
    task_type = request.args.get('task_type')
    period = request.args.get('period', 'monthly')
    year = request.args.get('year', datetime.now().year, type=int)
    
    # 构建基础查询
    reports_query = EvaluationReport.query
    
    if task_type:
        reports_query = reports_query.join(Task).filter(Task.task_type == task_type)
    
    # 根据年份筛选
    start_date = datetime(year, 1, 1)
    end_date = datetime(year + 1, 1, 1)
    reports_query = reports_query.filter(
        EvaluationReport.generated_at >= start_date,
        EvaluationReport.generated_at < end_date
    )
    
    reports = reports_query.all()
    
    # 处理统计数据
    stats_data = process_report_statistics(reports, period)
    
    # 获取任务类型列表供筛选
    task_types = db.session.query(Task.task_type).distinct().all()
    task_types = [t[0] for t in task_types]
    
    # 生成可用年份列表
    current_year = datetime.now().year
    years = list(range(current_year - 5, current_year + 1))
    
    return render_template('inspection/report_statistics.html',
                          task_types=task_types,
                          years=years,
                          current_filters={
                              'task_type': task_type,
                              'period': period,
                              'year': year
                          },
                          stats_data=stats_data)

def process_report_statistics(reports, period):
    """处理报告统计数据"""
    if not reports:
        return {
            'labels': [],
            'scores': [],
            'counts': [],
            'grade_distribution': {},
            'category_averages': {}
        }
    
    # 初始化数据容器
    time_periods = {}
    grade_counts = {'优秀': 0, '良好': 0, '合格': 0, '不合格': 0}
    all_category_scores = {}
    
    for report in reports:
        # 根据周期确定时间标签
        if period == 'monthly':
            period_key = report.generated_at.strftime('%Y-%m')
            period_label = report.generated_at.strftime('%Y年%m月')
        elif period == 'quarterly':
            quarter = (report.generated_at.month - 1) // 3 + 1
            period_key = f"{report.generated_at.year}-Q{quarter}"
            period_label = f"{report.generated_at.year}年Q{quarter}"
        else:  # yearly
            period_key = str(report.generated_at.year)
            period_label = f"{report.generated_at.year}年"
        
        # 初始化时间周期数据
        if period_key not in time_periods:
            time_periods[period_key] = {
                'label': period_label,
                'total_score': 0,
                'count': 0,
                'categories': {}
            }
        
        # 累加分数和计数
        time_periods[period_key]['total_score'] += report.total_score
        time_periods[period_key]['count'] += 1
        
        # 统计等级分布
        grade_counts[report.grade] = grade_counts.get(report.grade, 0) + 1
        
        # 处理类别得分
        category_scores = json.loads(report.category_scores) if report.category_scores else {}
        for category, data in category_scores.items():
            # 更新时间周期的类别数据
            if category not in time_periods[period_key]['categories']:
                time_periods[period_key]['categories'][category] = {
                    'total': 0,
                    'count': 0
                }
            time_periods[period_key]['categories'][category]['total'] += data['percentage']
            time_periods[period_key]['categories'][category]['count'] += 1
            
            # 更新全局类别数据
            if category not in all_category_scores:
                all_category_scores[category] = {
                    'total': 0,
                    'count': 0
                }
            all_category_scores[category]['total'] += data['percentage']
            all_category_scores[category]['count'] += 1
    
    # 计算平均分
    labels = []
    scores = []
    counts = []
    
    for key in sorted(time_periods.keys()):
        period_data = time_periods[key]
        labels.append(period_data['label'])
        
        if period_data['count'] > 0:
            scores.append(round(period_data['total_score'] / period_data['count'], 2))
        else:
            scores.append(0)
            
        counts.append(period_data['count'])
    
    # 计算类别平均分
    category_averages = {}
    for category, data in all_category_scores.items():
        if data['count'] > 0:
            category_averages[category] = round(data['total'] / data['count'], 2)
    
    # 计算等级分布百分比
    total_reports = len(reports)
    grade_distribution = {}
    for grade, count in grade_counts.items():
        grade_distribution[grade] = {
            'count': count,
            'percentage': round((count / total_reports) * 100, 2) if total_reports > 0 else 0
        }
    
    return {
        'labels': labels,
        'scores': scores,
        'counts': counts,
        'grade_distribution': grade_distribution,
        'category_averages': category_averages
    }

@app.context_processor
def inject_nav_links():
    return {
        'nav_links': [
            {'name': '控制面板', 'url': url_for('dashboard')},
            {'name': '任务管理', 'url': url_for('tasks')},
            {'name': '资源管理', 'url': url_for('resources')},
            {'name': '施工方案', 'url': url_for('plans')},
            {'name': '方案调整', 'url': url_for('plan_adjustment_list')},
            {'name': '方案优化', 'url': url_for('plan_optimization_list')},
            {'name': '考核监管', 'url': url_for('inspection_list')},
            {'name': '评分标准', 'url': url_for('criteria_list')},
            {'name': '考核报告', 'url': url_for('report_list')},
            {'name': '系统日志', 'url': url_for('system_logs')},
            {'name': '审计报告', 'url': url_for('audit_reports')}
        ]
    }

# 系统日志模型
class SystemLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    log_id = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True)
    operation_type = db.Column(db.String(50), nullable=False)  # 登录、资源调度、任务分配等
    operation_details = db.Column(db.Text)  # JSON格式存储操作详情
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user_name = db.Column(db.String(80))  # 冗余存储用户名，避免每次都联结查询
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    resource_id = db.Column(db.Integer, nullable=True)  # 相关资源ID（如适用）
    task_id = db.Column(db.Integer, nullable=True)  # 相关任务ID（如适用）
    plan_id = db.Column(db.Integer, nullable=True)  # 相关方案ID（如适用）
    result = db.Column(db.String(20), default='成功')  # 操作结果：成功、失败

    def to_dict(self):
        return {
            'id': self.id,
            'log_id': self.log_id,
            'operation_type': self.operation_type,
            'operation_details': json.loads(self.operation_details) if self.operation_details else {},
            'user_id': self.user_id,
            'user_name': self.user_name,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'resource_id': self.resource_id,
            'task_id': self.task_id,
            'plan_id': self.plan_id,
            'result': self.result
        }

# 审计报告模型
class AuditReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True)
    report_type = db.Column(db.String(50), nullable=False)  # 资源合规、任务分配、方案调整等
    report_name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    generated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    report_data = db.Column(db.Text)  # JSON格式存储报告数据
    findings = db.Column(db.Text)  # 发现的问题或异常
    recommendations = db.Column(db.Text)  # 建议措施
    
    def to_dict(self):
        return {
            'id': self.id,
            'report_id': self.report_id,
            'report_type': self.report_type,
            'report_name': self.report_name,
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'end_date': self.end_date.strftime('%Y-%m-%d'),
            'generated_by': self.generated_by,
            'generated_at': self.generated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'report_data': json.loads(self.report_data) if self.report_data else {},
            'findings': self.findings,
            'recommendations': self.recommendations
        }

# 日志记录函数
def log_operation(operation_type, operation_details=None, user_id=None, resource_id=None, task_id=None, plan_id=None, result='成功'):
    """
    记录系统操作日志
    :param operation_type: 操作类型
    :param operation_details: 操作详情（字典）
    :param user_id: 用户ID
    :param resource_id: 资源ID
    :param task_id: 任务ID
    :param plan_id: 方案ID
    :param result: 操作结果
    :return: None
    """
    if not user_id and current_user.is_authenticated:
        user_id = current_user.id
        user_name = current_user.username
    else:
        user = User.query.get(user_id) if user_id else None
        user_name = user.username if user else '未知用户'
    
    # 获取客户端IP
    ip_address = request.remote_addr if request else '0.0.0.0'
    
    # 将操作详情转换为JSON字符串
    if operation_details is None:
        operation_details = {}
    operation_details_json = json.dumps(operation_details)
    
    # 创建日志记录
    log = SystemLog(
        operation_type=operation_type,
        operation_details=operation_details_json,
        user_id=user_id,
        user_name=user_name,
        ip_address=ip_address,
        resource_id=resource_id,
        task_id=task_id,
        plan_id=plan_id,
        result=result
    )
    
    db.session.add(log)
    db.session.commit()
    return log

# 系统日志相关路由
@app.route('/system_logs')
@login_required
def system_logs():
    # 获取筛选参数
    operation_type = request.args.get('operation_type')
    user_id = request.args.get('user_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    result = request.args.get('result')
    
    # 构建查询
    query = SystemLog.query
    
    if operation_type:
        query = query.filter(SystemLog.operation_type == operation_type)
    if user_id:
        query = query.filter(SystemLog.user_id == int(user_id))
    if start_date:
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(SystemLog.timestamp >= start_datetime)
    if end_date:
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        query = query.filter(SystemLog.timestamp < end_datetime)
    if result:
        query = query.filter(SystemLog.result == result)
    
    # 分页
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = query.order_by(SystemLog.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items
    
    # 获取统计数据
    stats = {}
    stats['total_logs'] = SystemLog.query.count()
    stats['login_count'] = SystemLog.query.filter(SystemLog.operation_type == '用户登录').count()
    stats['resource_allocation_count'] = SystemLog.query.filter(SystemLog.operation_type == '资源分配').count()
    stats['task_creation_count'] = SystemLog.query.filter(SystemLog.operation_type == '创建任务').count()
    stats['success_rate'] = round(SystemLog.query.filter(SystemLog.result == '成功').count() / stats['total_logs'] * 100 if stats['total_logs'] > 0 else 0, 2)
    
    # 获取操作类型和用户列表（用于筛选）
    operation_types = db.session.query(SystemLog.operation_type).distinct().all()
    users = User.query.all()
    
    return render_template(
        'system_logs/list.html',
        logs=logs,
        pagination=pagination,
        stats=stats,
        operation_types=operation_types,
        users=users,
        filters={
            'operation_type': operation_type,
            'user_id': user_id,
            'start_date': start_date,
            'end_date': end_date,
            'result': result
        }
    )

@app.route('/system_logs/<string:log_id>')
@login_required
def log_detail(log_id):
    log = SystemLog.query.filter_by(log_id=log_id).first_or_404()
    
    # 获取相关对象信息
    related_user = User.query.get(log.user_id) if log.user_id else None
    related_task = Task.query.get(log.task_id) if log.task_id else None
    related_resource = Resource.query.get(log.resource_id) if log.resource_id else None
    related_plan = ConstructionPlan.query.get(log.plan_id) if log.plan_id else None
    
    return render_template(
        'system_logs/detail.html',
        log=log,
        related_user=related_user,
        related_task=related_task,
        related_resource=related_resource,
        related_plan=related_plan
    )

@app.route('/audit_reports')
@login_required
def audit_reports():
    # 获取筛选参数
    report_type = request.args.get('report_type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # 构建查询
    query = AuditReport.query
    
    if report_type:
        query = query.filter(AuditReport.report_type == report_type)
    if start_date:
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(AuditReport.generated_at >= start_datetime)
    if end_date:
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        query = query.filter(AuditReport.generated_at < end_datetime)
    
    # 分页
    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = query.order_by(AuditReport.generated_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    reports = pagination.items
    
    # 获取报告类型列表（用于筛选）
    report_types = db.session.query(AuditReport.report_type).distinct().all()
    
    return render_template(
        'audit_reports/list.html',
        reports=reports,
        pagination=pagination,
        report_types=report_types,
        filters={
            'report_type': report_type,
            'start_date': start_date,
            'end_date': end_date
        }
    )

@app.route('/audit_reports/<string:report_id>')
@login_required
def audit_report_detail(report_id):
    report = AuditReport.query.filter_by(report_id=report_id).first_or_404()
    generated_by_user = User.query.get(report.generated_by)
    
    return render_template(
        'audit_reports/detail.html',
        report=report,
        generated_by_user=generated_by_user
    )

@app.route('/generate_audit_report', methods=['GET', 'POST'])
@login_required
def generate_audit_report():
    if request.method == 'POST':
        report_type = request.form.get('report_type')
        report_name = request.form.get('report_name')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        # 验证输入
        if not all([report_type, report_name, start_date, end_date]):
            flash('请填写所有必填字段')
            return redirect(url_for('generate_audit_report'))
        
        # 转换日期
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        
        # 根据报告类型生成报告数据
        report_data = {}
        findings = []
        recommendations = []
        
        if report_type == '资源调度合规':
            # 获取时间范围内的资源分配记录
            resource_logs = SystemLog.query.filter(
                SystemLog.operation_type == '资源分配',
                SystemLog.timestamp >= start_datetime,
                SystemLog.timestamp < end_datetime
            ).all()
            
            # 统计资源分配数据
            resource_allocations = {}
            for log in resource_logs:
                details = json.loads(log.operation_details)
                for allocation in details.get('allocations', []):
                    resource_id = allocation.get('resource_id')
                    if resource_id not in resource_allocations:
                        resource_allocations[resource_id] = {
                            'resource_id': resource_id,
                            'resource_name': allocation.get('resource_name', '未知资源'),
                            'allocation_count': 0,
                            'total_quantity': 0
                        }
                    resource_allocations[resource_id]['allocation_count'] += 1
                    resource_allocations[resource_id]['total_quantity'] += allocation.get('quantity', 0)
            
            # 检查是否有资源利用率不平衡的情况
            all_resources = Resource.query.all()
            unused_resources = [r for r in all_resources if r.id not in resource_allocations]
            heavily_used_resources = [r for r_id, r in resource_allocations.items() if r['allocation_count'] > 5]
            
            report_data = {
                'total_allocations': len(resource_logs),
                'resource_allocations': list(resource_allocations.values()),
                'unused_resources': [{'id': r.id, 'name': r.name, 'type': r.resource_type} for r in unused_resources],
                'heavily_used_resources': heavily_used_resources
            }
            
            # 添加审计发现和建议
            if unused_resources:
                findings.append(f'有{len(unused_resources)}个资源在该时间段内未被使用')
                recommendations.append('建议检查未使用资源的状态，考虑调整资源分配策略')
            
            if heavily_used_resources:
                findings.append(f'有{len(heavily_used_resources)}个资源使用频率过高')
                recommendations.append('建议增加高频使用资源的数量或寻找替代资源')
        
        elif report_type == '任务分配透明度':
            # 获取时间范围内的任务创建记录
            task_logs = SystemLog.query.filter(
                SystemLog.operation_type == '创建任务',
                SystemLog.timestamp >= start_datetime,
                SystemLog.timestamp < end_datetime
            ).all()
            
            # 获取对应的任务资源分配情况
            task_ids = [log.task_id for log in task_logs if log.task_id]
            tasks = Task.query.filter(Task.id.in_(task_ids)).all()
            
            task_allocation_data = []
            for task in tasks:
                allocations = ResourceAllocation.query.filter_by(task_id=task.id).all()
                allocation_details = []
                
                for allocation in allocations:
                    resource = Resource.query.get(allocation.resource_id)
                    allocation_details.append({
                        'resource_id': allocation.resource_id,
                        'resource_name': resource.name if resource else '未知资源',
                        'resource_type': resource.resource_type if resource else '未知',
                        'quantity': allocation.quantity
                    })
                
                task_allocation_data.append({
                    'task_id': task.id,
                    'task_name': task.name,
                    'task_type': task.task_type,
                    'created_by': task.created_by,
                    'created_by_name': User.query.get(task.created_by).username if User.query.get(task.created_by) else '未知用户',
                    'allocations': allocation_details
                })
            
            # 检查是否有资源分配不均的情况
            tasks_without_resources = [t for t in task_allocation_data if not t['allocations']]
            
            report_data = {
                'total_tasks': len(tasks),
                'task_allocation_data': task_allocation_data,
                'tasks_without_resources': tasks_without_resources
            }
            
            # 添加审计发现和建议
            if tasks_without_resources:
                findings.append(f'有{len(tasks_without_resources)}个任务没有分配资源')
                recommendations.append('建议确保每个创建的任务都有适当的资源分配')
        
        # 创建审计报告
        report = AuditReport(
            report_type=report_type,
            report_name=report_name,
            start_date=start_datetime,
            end_date=end_datetime - timedelta(days=1),
            generated_by=current_user.id,
            report_data=json.dumps(report_data),
            findings='\n'.join(findings),
            recommendations='\n'.join(recommendations)
        )
        
        db.session.add(report)
        db.session.commit()
        
        # 记录生成审计报告的操作
        log_operation(
            operation_type='生成审计报告',
            operation_details={
                'report_id': report.report_id,
                'report_type': report_type,
                'report_name': report_name
            }
        )
        
        flash('审计报告已生成')
        return redirect(url_for('audit_report_detail', report_id=report.report_id))
    
    # 获取报告类型选项
    report_types = [
        ('资源调度合规', '资源调度合规审计'),
        ('任务分配透明度', '任务分配透明度审计'),
        ('方案调整合规', '方案调整合规审计')
    ]
    
    return render_template(
        'audit_reports/generate.html',
        report_types=report_types
    )

# 将系统日志和审计报告链接添加到导航栏
@app.context_processor
def inject_nav_links():
    return {
        'nav_links': [
            {'name': '控制面板', 'url': url_for('dashboard')},
            {'name': '任务管理', 'url': url_for('tasks')},
            {'name': '资源管理', 'url': url_for('resources')},
            {'name': '施工方案', 'url': url_for('plans')},
            {'name': '方案调整', 'url': url_for('plan_adjustment_list')},
            {'name': '方案优化', 'url': url_for('plan_optimization_list')},
            {'name': '考核监管', 'url': url_for('inspection_list')},
            {'name': '评分标准', 'url': url_for('criteria_list')},
            {'name': '考核报告', 'url': url_for('report_list')},
            {'name': '系统日志', 'url': url_for('system_logs')},
            {'name': '审计报告', 'url': url_for('audit_reports')}
        ]
    }

# 确保创建所有表，包括新添加的系统日志和审计报告表