# MySQL数据库设置指南

本文档说明如何将高速公路集中养护智能管理系统配置为使用MySQL数据库。

## 前提条件

1. 已安装MySQL服务器
2. Python 3.7+
3. 已安装项目依赖（见requirements.txt）

## 配置步骤

### 1. 安装MySQL

如果尚未安装MySQL，请按照以下步骤安装：

- **Windows**: 下载并安装[MySQL Installer](https://dev.mysql.com/downloads/installer/)
- **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt update
  sudo apt install mysql-server
  sudo mysql_secure_installation
  ```
- **macOS**:
  ```bash
  brew install mysql
  brew services start mysql
  ```

### 2. 创建数据库用户和密码

登录到MySQL并创建一个新用户（或使用root用户）：

```sql
CREATE USER 'highway_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON highway_maintenance.* TO 'highway_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3. 配置项目连接参数

创建一个`.env`文件在项目根目录，包含以下内容：

```
SECRET_KEY=your_secret_key
DB_USER=highway_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_NAME=highway_maintenance
MAP_PROVIDER=gaode
TIANDITU_KEY=
```

请根据您的MySQL设置修改上述参数。

### 4. 初始化数据库

运行初始化脚本创建数据库和表结构：

```bash
python init_db.py
```

这将：
1. 创建`highway_maintenance`数据库（如果不存在）
2. 创建所有必要的表
3. 创建默认管理员账户（用户名：admin，密码：admin123）

### 5. 运行应用

初始化完成后，您可以启动应用：

```bash
python app.py
```

## 故障排除

### 连接错误

如果遇到"Can't connect to MySQL server"错误：
- 确认MySQL服务正在运行
- 验证用户名和密码正确
- 检查主机名是否正确（通常是'localhost'或'127.0.0.1'）

### 权限错误

如果遇到"Access denied"错误：
- 确认用户有正确的数据库权限
- 重新检查`.env`文件中的凭据

### 字符集问题

如果遇到中文或特殊字符显示问题：
- 确认数据库使用`utf8mb4`字符集
- 检查表的字符集设置

## 数据库备份

定期备份数据库是个好习惯：

```bash
mysqldump -u highway_user -p highway_maintenance > backup_$(date +%Y%m%d).sql
```

## 从SQLite迁移数据

如果您之前使用SQLite并希望迁移数据，可以使用项目中的迁移工具：

```bash
python migrate_sqlite_to_mysql.py
```

注意：迁移前请确保已备份两个数据库。 