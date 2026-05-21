## 启动（先看这里）

```bash
cp .env.example .env
# 按需填写 .env（至少要填：DockerPostgreSQLUser/DockerPostgreSQLPassword/DockerPostgreSQLDatabase、FLASK_SECRET_KEY、ADMIN_PASSWORD、MedicalInsuranceBaseURL）

uv sync
uv run webapp/app.py
```

浏览器访问：

- http://127.0.0.1:5000/

---

## 项目简介

personal-toolkit 是一个用于“药品更新数据”的抓取、入库、查询与导出的工具集，包含：

- 后台管理站点（Flask + SQLAlchemy + Semantic UI）
- 抓取客户端（调用 `api/medical_info.py` 对应的医保接口）
- Excel 导出（openpyxl）

## 主要功能

- 登录认证（flask-login）
- 抓取入库
  - 按版本号分页抓取
  - 入库前会先清空该版本号历史数据（DELETE + INSERT）
  - 接口调用自动做 6 秒节流兜底（避免调用间隔过短）
  - 前端轮询展示实时进度（页数、写入行数、耗时、滚动日志）
- 数据查询
  - 版本号必选
  - 支持按药品代码/商品名/本位码/批准文号筛选
  - 分页查询（数据库层面 limit/offset），并提供总数统计
- Excel 导出
  - “标准/新版”两种导出模板

## 环境变量（.env）

项目会在启动时自动加载根目录 `.env`（可参考 `.env.example`）。首次启动前请先配置以下变量：

```ini
DockerPostgreSQLUser=
DockerPostgreSQLPassword=
DockerPostgreSQLHost=
DockerPostgreSQLDatabase=

MedicalInsuranceBaseURL=
MedicalInsuranceTimeOut=30

FLASK_SECRET_KEY=
ADMIN_USERNAME=
ADMIN_PASSWORD=
```

说明：

- `ADMIN_PASSWORD` 必填：首次启动会自动初始化管理员账号；未设置会直接报错并退出（避免生成无密码账号）。
- `DockerPostgreSQLHost` 支持 `host:port` 写法。
- `MedicalInsuranceBaseURL` / `MedicalInsuranceTimeOut` 为抓取接口所需配置。

## 初始化行为（启动时自动完成）

- 自动创建数据表：`users`、`drug_update_info`
- 自动创建唯一索引：`drug_update_info(version, goodscode)`（避免重复写入）
- 自动初始化管理员账号：`ADMIN_USERNAME` / `ADMIN_PASSWORD`

## 页面入口

- `/`：根据登录状态跳转
- `/login`：登录页
- `/ingest`：抓取入库 + 实时进度
- `/medical-info`：查询分页
- `/export?style=standard&version=...`：导出标准
- `/export?style=new&version=...`：导出新版

## 目录结构

```text
webapp/                 Flask 管理站点
  app.py                create_app 工厂 & 启动时初始化逻辑
  db.py                 SQLAlchemy Engine/Session 管理
  models.py             User / DrugUpdateInfo 模型
  routes/               路由：auth、ingest、medical_info
  services/             业务服务：ingest、export、bootstrap
  repositories/         数据访问：drug_update_repo
  templates/            页面模板（Semantic UI）

api/medical_info.py     原始医保接口调用封装（抓取依赖）
dotenv/                 自带的 dotenv 兼容实现（用于 Python 3.14）
note/                   SQL/脚本备忘与导出 SQL
```

## 开发约定

- Python 依赖与运行统一使用 uv
- 导出使用 openpyxl（避免 pandas 在 Python 3.14 上的兼容问题）
- 抓取接口调用需满足最小 6 秒间隔（系统会自动兜底）
