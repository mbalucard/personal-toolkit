# Flask 药品更新：抓取入库 / 查询 / 导出（SQLAlchemy）计划

## 目标与成功标准

目标：在现有项目 `/Users/lucifer/code/Python/TRAE/personal-toolkit` 基础上，新增一个 Flask 网站，用于：

- 按页面参数调用既有接口函数 `api/medical_info.py:get_drug_update_info` 抓取药品更新数据并写入 PostgreSQL。
- 基于数据库数据提供查询页面（必选 `version`，支持基础筛选 + 服务端分页）。
- 提供两种 Excel 导出样式（对应 `note/select_table.sql` 与 `note/select_new.sql` 的字段顺序与列名）。
- 提供简单登录（仅用户名/密码），不做复杂权限体系；所有业务页面需登录后可访问。

成功标准（可验收）：

- 能在页面触发一次拉取入库，入库后在查询页按 `version` 查询到数据。
- 同一 `version` 重跑入库会先清空数据库中该 `version` 的数据，再重新拉取写入；最终库中该 `version` 的数据以本次拉取为准。
- 查询页分页默认 100 行，可选 200/500。
- 导出能下载 xlsx 文件，列名与 `note/export.py` 中定义一致，数据列顺序与 `note/select_*.sql` 一致。
- 不修改 `api/medical_info.py`。

## 现状分析（基于仓库实际内容）

### 现有代码与约束

- 已有 API 文件：`api/medical_info.py`（含 `get_drug_update_info(batchNumber, ...)` 异步函数），用户要求不改动。
- 已有数据库连接配置：`config/server.py` 通过 dotenv 读取环境变量：
  - `DockerPostgreSQLUser / DockerPostgreSQLPassword / DockerPostgreSQLHost / DockerPostgreSQLDatabase`
  - `DockerPostgreSQLHost` 值已包含端口，例如 `www.dawn13.cn:1081`
- 已有 SQL 与参考脚本（均位于 `note/`，仅供参考）：
  - 建表：`note/create_update_table.sql`（表名 `drug_update_info`）
  - 拉取入库参考：`note/new_get_drug_update.py`（分页、重试、清空批次等）
  - 导出参考：`note/export.py`（两种样式列名定义 + select SQL 文件选择）
  - 导出 SQL：`note/select_table.sql`（标准版）、`note/select_new.sql`（新版）
- 当前项目依赖：`pyproject.toml` 中已有 `sqlalchemy>=2.0.49`、`httpx`、`dotenv` 等，但未包含 Flask / Postgres 驱动 / Excel 导出依赖。

### 数据表（药品更新）

依据 `note/create_update_table.sql`：

- 表名：`drug_update_info`
- 字段：见 SQL（包含 `goodscode`、`version`、`traceCodeFlag`、`goodsCodeHistory`、`oldApprovalCode` 等）
- SQL 文件本身未定义主键/唯一约束；本项目将按需求采用 `goodscode + version` 作为同 version 去重键。

## 关键决策与约束（已确认）

- 目标表固定：`drug_update_info`。
- 去重/upsert 唯一键：`(version, goodscode)`。
- “抓取入库”页面需包含分页控制参数（行为参考 `note/new_get_drug_update.py`）。
- 同一 `version` 重跑时，必须先清空该 `version` 的历史数据再重新拉取入库（不做“直接 upsert 覆盖”作为主要策略）。
- 查询字段：`version` 必填，另支持筛选 `goodscode / goodsname / goodsstandardcode / approvalcode`。
- 查询分页：默认每页 100 行，可选 200/500。
- 登录：需要简单登录；用户提到账号 admin 与密码，但出于安全原因不在代码库中写死明文密码，改为从环境变量初始化 admin 账号。

## 方案概述（端到端数据流）

1) 用户登录后进入“抓取入库”页，填写 `version(batchNumber)` 等参数并提交。
2) 服务端按分页循环调用 `get_drug_update_info`，拿到每页 `rows` 列表。
3) 将每页数据批量 upsert 写入 `drug_update_info`，冲突目标为 `(version, goodscode)`。
4) 用户进入“查询”页，先选 `version`，再按条件筛选，服务端分页返回结果表格。
5) 用户在查询页点击导出（标准/新版），下载对应样式的 Excel（xlsx）。

## 拟新增/修改的文件与内容

> 说明：以下是批准后进入实现阶段将要创建/修改的文件清单；实现阶段严格不改动 `api/medical_info.py`。

### 1) 依赖与运行方式

- 修改 `pyproject.toml`：新增依赖
  - `flask`（Web 框架）
  - `flask-login`（登录会话管理）
  - `psycopg[binary]`（PostgreSQL 驱动，配合 SQLAlchemy）
  - `pandas` + `openpyxl`（Excel 导出）
- 新增 `.env.example`（示例，不含真实密码）
  - `ADMIN_USERNAME=admin`
  - `ADMIN_PASSWORD=...`
  - 以及现有 DB 与 MedicalInsurance 相关环境变量说明

### 2) Web 应用包（新增）

新增目录（建议）：

**核心原则：登录 / 抓取入库 / 查询导出 全部解耦，业务逻辑不放在 app.py（或启动入口）里。启动文件只负责“创建 app + 注册蓝图/扩展 + 配置加载”。**

- `webapp/`（Flask 应用包）
  - `webapp/app.py`：仅包含 `create_app()`、加载配置、注册蓝图、初始化扩展（不写任何业务逻辑）
  - `webapp/config.py`：读取环境变量（Flask Secret Key、admin 初始化、分页默认值等）
  - `webapp/extensions.py`：集中初始化扩展对象（LoginManager、数据库会话工厂等），供 app.py 调用
  - `webapp/db.py`：SQLAlchemy engine/session 管理（同步），提供 `get_session()` 之类的最小接口
  - `webapp/models.py`：ORM 模型（User、DrugUpdateInfo）
  - `webapp/clients/medical_api.py`：对 `api.medical_info.get_drug_update_info` 做轻量封装（便于在 service 层调用与未来替换/mock）
  - `webapp/repositories/drug_update_repo.py`：纯 DB 读写（delete by version、insert batch、distinct version、query with filters+pagination）
  - `webapp/services/ingest.py`：抓取与入库编排（分页循环、重试、sleep、调用 repo 写入）
  - `webapp/services/export.py`：导出编排（读取 SQL、调用 repo 执行查询、生成 xlsx bytes）
  - `webapp/routes/auth.py`：登录/登出 Blueprint（只做参数接收/调用 service/返回模板）
  - `webapp/routes/ingest.py`：抓取入库 Blueprint
  - `webapp/routes/medical_info.py`：查询页 + 导出入口 Blueprint
  - `webapp/templates/*.html`：Jinja2 模板（login、ingest、list）
  - `webapp/static/`：可选（基础样式）

### 3) ORM 设计细节（SQLAlchemy 2.0）

#### User 表

- 表名：`users`
- 字段：
  - `id`（自增主键）
  - `username`（唯一，非空）
  - `password_hash`（非空）
  - `created_at`
- 初始化：admin 用户仅在库为空时创建（或 admin 不存在时创建），用户名/密码来自环境变量：
  - `ADMIN_USERNAME`（默认 admin）
  - `ADMIN_PASSWORD`（必须由用户自行设置到环境变量；代码不包含明文）

#### drug_update_info 表

- 表名：`drug_update_info`
- 主键/唯一键：
  - 使用**复合主键**：`(version, goodscode)`（与需求一致，并天然支持 on-conflict upsert）
- 其余字段按 `note/create_update_table.sql` 定义映射：
  - 需要注意 SQL 中大量字段使用双引号（大小写敏感，如 `goodsCodeHistory`、`oldApprovalCode`、`traceCodeFlag`），ORM Column 需使用原始列名字符串。

### 4) 抓取入库（服务层）

入口：`POST /ingest`

页面参数（包含分页控制，参考 `note/new_get_drug_update.py`）：

- `version`（必填，对应 API 的 `batchNumber`）
- `rows`（默认 1000；单页拉取条数）
- `start_page`（默认 1）
- `end_page`（默认空，表示拉到最后一页）
- `waiting_time`（默认 5 秒；每页处理后 sleep，防止接口限流）
- `clear_table_flag`（默认 true；实际逻辑固定为“先清空再重拉”，该参数仅用于页面显示与未来扩展）
- `max_retries`（默认 3；单页拉取与单页写入分别重试）
- `retry_delay_seconds`（默认 2 秒）

实现策略：

- 先请求第 1 页获取 `records` 总数，计算总页数（逻辑复用参考脚本中的 `get_total_page`）。
- 入库前固定执行：`DELETE FROM drug_update_info WHERE version=:version`（保证同 version 重跑为“清空后重拉”）。
- 分页循环：
  - 拉取：调用 `get_drug_update_info(batchNumber=version, page=page, rows=rows, ...)`
  - 转换：把 `data_json["rows"]` 作为待写入记录列表；确保每条记录包含 `version` 字段（若 API 未返回 version，则手动补充）
  - 写入：批量 INSERT；为防止接口返回重复行导致插入失败，插入策略采用 Postgres `ON CONFLICT DO NOTHING`（冲突目标 `(version, goodscode)`）
  - 提交：按页 commit（避免单事务过大）
- 错误处理：
  - 拉取失败与写入失败分别按 `max_retries` 重试，重试间隔 `retry_delay_seconds`
  - 失败时返回友好错误页（包含失败页码与异常信息）

### 5) 查询页面（基础筛选 + 分页）

入口：`GET /medical-info`

- `version`：必选；页面提供：
  - 下拉：从 DB `SELECT DISTINCT version ORDER BY version DESC`
  - 也支持手工输入（可选）
- 筛选字段（均为可选，模糊匹配/包含匹配）：
  - `goodscode`
  - `goodsname`
  - `goodsstandardcode`
  - `approvalcode`
- 分页：
  - `page`（默认 1）
  - `page_size`（默认 100；仅允许 100/200/500）
- 展示列：
  - 默认展示与 `note/select_table.sql` 同一组 20 列（与“标准导出”一致），减少页面横向溢出
  - 页面提供“导出标准/导出新版”两个按钮，导出不依赖页面当前显示列

### 6) Excel 导出（两种样式）

入口（建议）：

- `GET /export?style=standard&version=...`
- `GET /export?style=new&version=...`

规则（严格对齐 `note/export.py`）：

- style=standard：
  - SQL：`note/select_table.sql`
  - 列名（中文表头）：`note/export.py` 中 standard columns（20 列）
- style=new：
  - SQL：`note/select_new.sql`
  - 列名：`note/export.py` 中 new columns（28 列）

安全与实现方式：

- 不使用字符串 `.format()` 拼接用户输入，避免 SQL 注入。
- 读取 `note/select_*.sql` 后做“固定替换 + 参数化”：
  - `{table_name}` 固定替换为 `drug_update_info`
  - `where version = '{batch_number}'` 改造成 `where version = :version`
- 通过 SQLAlchemy 执行 text 查询，构造 DataFrame，再输出到 `BytesIO`：
  - `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
  - `Content-Disposition: attachment; filename=...`

## 安全与配置约定

- 不在仓库中写死任何真实密码/密钥。
- admin 初始化密码通过环境变量提供：
  - `ADMIN_PASSWORD` 由用户自行在本机 `.env` 设置（`.env` 已在 `.gitignore` 中时保持不提交）
- Flask `SECRET_KEY` 也从环境变量读取（如 `FLASK_SECRET_KEY`）。
- 页面参数校验：
  - `version` 必填且仅允许数字日期格式（`YYYYMMDD`）或你实际使用的版本格式
  - `page_size` 仅允许 100/200/500
  - 其它字符串筛选字段做长度限制

## 验证与自测步骤（实现阶段执行）

1) 安装依赖（uv）并设置环境变量：
   - DB：`DockerPostgreSQLUser/Password/Host/Database`
   - API：`MedicalInsuranceBaseURL/MedicalInsuranceTimeOut`
   - Web：`FLASK_SECRET_KEY`、`ADMIN_USERNAME`、`ADMIN_PASSWORD`
2) 启动 Flask 开发服务器（uv）。
3) 访问 `/login`，使用 admin 登录。
4) 访问 `/ingest`：
   - 输入 `version` 与分页参数，执行一次拉取入库
   - 重复执行同一 version，确认数据行数不增加（upsert 生效）
5) 访问 `/medical-info`：
   - 选择 version，检查列表能分页展示（100/200/500）
   - 测试 4 个筛选字段的查询行为
6) 点击导出：
   - 标准版与新版均可下载 xlsx
   - 打开 xlsx 校验列名与顺序正确（与参考文件一致）
