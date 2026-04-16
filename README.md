# Flask 个人博客系统

一个基于 Flask + SQLite 开发的个人博客系统，支持用户注册登录、文章发布、评论互动、点赞收藏、关注、私信和通知等基础社交功能。

## 功能特点

- 用户注册、登录、退出
- 文章发布、编辑、删除
- 文章支持上传图片
- 文章标签管理
- 点赞、收藏、转发文章
- 关注 / 取消关注用户
- 评论、评论回复、评论点赞
- 评论支持上传图片
- 消息通知中心
- 用户私信聊天
- 头像上传与修改
- 管理员文章 / 用户管理

## 技术栈

- Python 3
- Flask
- SQLite3
- Jinja2 模板
- Werkzeug 密码加密
- HTML / CSS / Bootstrap / JavaScript

## 运行环境

建议先安装依赖：

```bash
pip install flask werkzeug
```

## 快速启动

1. 初始化数据库：

```bash
python init_db.py
```

2. 启动应用：

```bash
python blog.py
```

3. 打开浏览器访问：

```text
http://127.0.0.1:5000
```

## 默认账号

数据库初始化后会创建示例账号：

- 管理员：`admin` / `arimakanaa`
- 普通用户：`user1` / `123456`

## 目录说明

```text
FlaskProject/
├── blog.py            # 主程序入口
├── init_db.py         # 初始化数据库脚本
├── db.sql             # 数据库表结构
├── templates/         # Jinja 模板
├── static/            # 静态资源、头像和上传图片
├── README.md          # 项目说明文档
└── .gitignore         # Git 忽略配置
```

## 数据库说明

- `database.db`：主数据库文件
- `users.db`：旧数据库文件或历史数据文件
- `static/uploads/`：图片上传目录

## 注意事项

- `static/uploads/` 建议不要直接提交到仓库，避免上传大量图片文件。
- 如果修改了数据库结构，建议重新执行 `init_db.py` 生成最新表结构。
- 当前项目使用本地 SQLite，适合演示和学习；如果后续部署到线上，可以再考虑迁移到 MySQL 或 PostgreSQL。

## 说明

本项目适合作为 Flask 入门练习、课程设计或简历项目展示。

