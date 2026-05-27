from __future__ import annotations

import os
import sys
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from flask import Flask

from webapp.config import Settings
from webapp.db import get_engine, init_db
from webapp.extensions import login_manager
from webapp.models import Base
from webapp.services.bootstrap import (
    ensure_admin_user,
    ensure_drug_update_unique_index,
    ensure_user_login_log_indexes,
    ensure_user_columns,
)


def create_app() -> Flask:
    """
    创建并初始化 Flask 应用实例。

    启动时会加载 .env 配置，初始化数据库连接与表结构，并注册各业务蓝图与登录管理器。

    Returns:
        Flask: 已完成初始化的 Flask 应用实例。
    """
    load_dotenv()
    settings = Settings()

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = settings.secret_key

    @app.context_processor
    def inject_global_config() -> dict[str, str]:
        return {"icp_number": (os.getenv("ICP_NUMBER") or "").strip()}

    init_db()
    Base.metadata.create_all(bind=get_engine())
    ensure_user_columns()
    ensure_drug_update_unique_index()
    ensure_user_login_log_indexes()

    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    ensure_admin_user(settings)

    from webapp.routes.auth import bp as auth_bp
    from webapp.routes.ingest import bp as ingest_bp
    from webapp.routes.medical_info import bp as medical_info_bp
    from webapp.routes.user_mgmt import bp as user_mgmt_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(ingest_bp)
    app.register_blueprint(medical_info_bp)
    app.register_blueprint(user_mgmt_bp)

    return app


if __name__ == "__main__":
    import os

    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", "5001"))
    debug = (os.getenv("FLASK_DEBUG", "1") or "").strip().lower() not in {"0", "false"}
    create_app().run(host=host, port=port, debug=debug)

# uv run webapp/app.py
