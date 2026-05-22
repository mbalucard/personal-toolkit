from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user
from werkzeug.security import check_password_hash

from webapp.db import session_scope
from webapp.extensions import login_manager
from webapp.models import User, UserLoginLog
from webapp.services.redis_client import RedisUnavailableError, ping_or_raise


bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    """
    根据用户 ID 加载用户对象（flask-login 回调）。

    Args:
        user_id (str): 用户 ID（字符串形式，通常来自 session）。

    Returns:
        User | None: 查询到的用户对象；不存在则返回 None。
    """
    with session_scope() as session:
        return session.query(User).filter(User.id == int(user_id)).first()


@bp.get("/login")
def login() -> str:
    """
    渲染登录页面。

    Returns:
        str: 渲染后的 HTML。
    """
    return render_template("login.html")


@bp.post("/login")
def login_post():
    """
    处理登录提交。

    从表单中读取用户名与密码，校验通过后写入登录态并跳转到查询页。

    Returns:
        Response | str: 登录成功时重定向；失败时返回带错误信息的登录页面。
    """
    try:
        ping_or_raise()
    except RedisUnavailableError as exc:
        return render_template("login.html", error=str(exc), redis_popup=True)

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    with session_scope() as session:
        user = session.query(User).filter(User.username == username).first()
        if user is None:
            return render_template("login.html", error="用户名或密码错误")

        if user.is_active == 0:
            return render_template("login.html", error="账号已停用")

        now = datetime.now(timezone.utc)
        locked_until = user.locked_until
        if locked_until is not None and locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)

        if locked_until is not None and locked_until > now:
            return render_template("login.html", error="账号已锁定，请 2 小时后再试")

        if not check_password_hash(user.password_hash, password):
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= 5:
                user.locked_until = now + timedelta(hours=2)
                return render_template(
                    "login.html", error="密码错误次数过多，账号已锁定 2 小时"
                )
            remaining = 5 - user.failed_login_attempts
            return render_template(
                "login.html", error=f"密码错误，还剩 {remaining} 次重试机会"
            )

        user.failed_login_attempts = 0
        user.locked_until = None

        session.add(
            UserLoginLog(
                user_id=user.id,
                username=user.username,
                ip=request.remote_addr,
            )
        )
        login_user(user)
        return redirect(url_for("medical_info.list_page"))


@bp.get("/logout")
@login_required
def logout():
    """
    退出登录并跳转回登录页。

    Returns:
        Response: 重定向响应。
    """
    logout_user()
    return redirect(url_for("auth.login"))
