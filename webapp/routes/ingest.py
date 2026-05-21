from __future__ import annotations

from threading import Thread

from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required

from webapp.services.ingest import IngestCancelled, IngestResult, ingest_drug_update
from webapp.services.ingest_tasks import append_job_log, create_job, get_job, update_job
from webapp.services.version_retention import cleanup_old_versions


bp = Blueprint("ingest", __name__, url_prefix="/ingest")


def _format_duration(seconds: float) -> str:
    total_seconds = max(0, int(round(seconds)))
    minutes, sec = divmod(total_seconds, 60)
    if minutes > 0:
        return f"{minutes}分{sec:02d}秒"
    return f"{sec}秒"


@bp.get("")
@login_required
def ingest_page():
    """
    渲染抓取入库页面。

    Returns:
        str: 渲染后的 HTML。
    """
    return render_template(
        "ingest.html",
        defaults={
            "rows": 1000,
            "start_page": 1,
            "end_page": "",
            "waiting_time": 7,
            "max_retries": 3,
            "retry_delay_seconds": 2.0,
        },
    )


def _int_value(form, name: str, default: int) -> int:
    """
    从表单读取整数参数。

    Args:
        form: request.form 或兼容的映射对象。
        name (str): 参数名。
        default (int): 默认值（当参数为空时使用）。

    Returns:
        int: 解析后的整数值。
    """
    v = (form.get(name) or "").strip()
    if not v:
        return default
    return int(v)


def _float_value(form, name: str, default: float) -> float:
    """
    从表单读取浮点数参数。

    Args:
        form: request.form 或兼容的映射对象。
        name (str): 参数名。
        default (float): 默认值（当参数为空时使用）。

    Returns:
        float: 解析后的浮点数值。
    """
    v = (form.get(name) or "").strip()
    if not v:
        return default
    return float(v)


def _run_ingest_job(job_id: str, payload: dict) -> None:
    """
    后台线程执行抓取任务。

    通过 progress_callback 将抓取过程的元信息/分页进度写入内存任务存储，供前端轮询展示。

    Args:
        job_id (str): 任务 ID。
        payload (dict): 抓取参数（version、rows、start_page、end_page、waiting_time 等）。

    Returns:
        None: 无返回值。
    """
    try:
        update_job(job_id, {"status": "running"})
        base_inserted_rows = int(payload.get("base_inserted_rows") or 0)
        base_processed_pages = int(payload.get("base_processed_pages") or 0)
        base_elapsed_seconds = float(payload.get("base_elapsed_seconds") or 0.0)

        def should_cancel() -> bool:
            job = get_job(job_id) or {}
            return bool(job.get("cancel_requested"))

        def on_progress(event: dict) -> None:
            """
            抓取过程回调，用于将实时进度同步到任务存储。

            Args:
                event (dict): 进度事件数据（包含 event 类型、页码、耗时、日志等）。

            Returns:
                None: 无返回值。
            """
            event_type = event.get("event")
            if event_type == "meta":
                start_page = int(event.get("start_page") or 1)
                total_pages = int(event.get("total_pages") or 0)
                end_page = event.get("end_page")
                target_pages = total_pages
                if end_page is not None and int(end_page) > 0:
                    target_pages = max(0, int(end_page) - start_page + 1)
                update_job(
                    job_id,
                    {
                        "total_records": event["total_records"],
                        "total_pages": event["total_pages"],
                        "target_pages": target_pages,
                        "rows_per_page": event["rows_per_page"],
                        "start_page": event["start_page"],
                        "end_page": event["end_page"],
                        "deleted_rows": event["deleted_rows"],
                    },
                )
            elif event_type == "page_started":
                update_job(
                    job_id,
                    {
                        "current_page": event["page"],
                        "processed_pages": base_processed_pages + event["processed_pages"],
                        "inserted_rows": base_inserted_rows + event["inserted_rows"],
                    },
                )
            elif event_type == "page_finished":
                elapsed_seconds = base_elapsed_seconds + float(
                    event.get("cumulative_elapsed_seconds") or 0.0
                )
                update_job(
                    job_id,
                    {
                        "current_page": event["page"],
                        "processed_pages": base_processed_pages + event["processed_pages"],
                        "inserted_rows": base_inserted_rows + event["inserted_rows_total"],
                        "last_page_elapsed_text": event["page_elapsed_text"],
                        "last_page_elapsed_seconds": float(
                            event.get("page_elapsed_seconds") or 0.0
                        ),
                        "elapsed_seconds": elapsed_seconds,
                        "elapsed_text": _format_duration(elapsed_seconds),
                    },
                )
            elif event_type == "finished":
                elapsed_seconds = base_elapsed_seconds + float(
                    event.get("total_elapsed_seconds") or 0.0
                )
                update_job(
                    job_id,
                    {
                        "elapsed_seconds": elapsed_seconds,
                        "elapsed_text": _format_duration(elapsed_seconds),
                    },
                )

            message = event.get("message")
            if message:
                append_job_log(job_id, message)

        result: IngestResult = ingest_drug_update(
            version=payload["version"],
            rows=payload["rows"],
            start_page=payload["start_page"],
            end_page=payload["end_page"],
            clear_existing=payload.get("clear_existing", True),
            waiting_time=payload["waiting_time"],
            max_retries=payload["max_retries"],
            retry_delay_seconds=payload["retry_delay_seconds"],
            progress_callback=on_progress,
            should_cancel=should_cancel,
        )
        try:
            cleanup_result = cleanup_old_versions()
            if cleanup_result.deleted_versions:
                deleted_versions_text = "、".join(reversed(cleanup_result.deleted_versions))
                append_job_log(
                    job_id,
                    f"清理旧版本：保留最近{cleanup_result.keep}个版本，删除版本：{deleted_versions_text}，共删除{cleanup_result.deleted_rows}行",
                )
            else:
                append_job_log(
                    job_id,
                    f"清理旧版本：当前共有{cleanup_result.total_versions}个版本，未超过保留上限{cleanup_result.keep}，无需删除",
                )
        except BaseException as exc:
            append_job_log(job_id, f"清理旧版本失败：{exc}")
        total_elapsed_seconds = base_elapsed_seconds + float(result.total_elapsed_seconds)
        update_job(
            job_id,
            {
                "status": "success",
                "version": result.version,
                "deleted_rows": result.deleted_rows,
                "inserted_rows": base_inserted_rows + result.inserted_rows,
                "total_records": result.total_records,
                "rows_per_page": result.rows_per_page,
                "total_pages": result.total_pages,
                "start_page": result.start_page,
                "end_page": result.end_page,
                "processed_pages": base_processed_pages + len(result.page_details),
                "elapsed_seconds": total_elapsed_seconds,
                "elapsed_text": _format_duration(total_elapsed_seconds),
                "last_page_elapsed_text": (
                    result.page_details[-1].page_elapsed_text if result.page_details else "-"
                ),
                "last_page_elapsed_seconds": (
                    result.page_details[-1].page_elapsed_seconds if result.page_details else 0.0
                ),
                "message": "抓取任务已完成",
            },
        )
    except IngestCancelled as exc:
        update_job(job_id, {"status": "cancelled", "message": str(exc) or "抓取已终止"})
        append_job_log(job_id, str(exc) or "抓取已终止")
    except BaseException as exc:
        update_job(job_id, {"status": "error", "message": str(exc)})
        append_job_log(job_id, f"抓取失败：{exc}")


@bp.post("")
@login_required
def ingest_post():
    """
    提交抓取入库任务（异步）。

    校验参数后创建任务并启动后台线程执行；接口立即返回 job_id，前端通过轮询查询状态。

    Returns:
        Response: JSON 响应，包含 ok 与 job_id 或 error 信息。
    """
    version = (request.form.get("version") or "").strip()
    if not version:
        return jsonify({"ok": False, "error": "版本号不能为空"}), 400

    payload = {
        "version": version,
        "rows": _int_value(request.form, "rows", 1000),
        "start_page": _int_value(request.form, "start_page", 1),
        "end_page": _int_value(request.form, "end_page", 0) or None,
        "clear_existing": True,
        "waiting_time": _int_value(request.form, "waiting_time", 7),
        "max_retries": _int_value(request.form, "max_retries", 3),
        "retry_delay_seconds": _float_value(request.form, "retry_delay_seconds", 2.0),
        "base_inserted_rows": 0,
        "base_processed_pages": 0,
        "base_elapsed_seconds": 0.0,
    }

    try:
        job_id = create_job(
            {
                "status": "queued",
                "version": version,
                "rows": payload["rows"],
                "waiting_time": payload["waiting_time"],
                "max_retries": payload["max_retries"],
                "retry_delay_seconds": payload["retry_delay_seconds"],
                "clear_existing": True,
                "cancel_requested": False,
                "base_inserted_rows": 0,
                "base_processed_pages": 0,
                "base_elapsed_seconds": 0.0,
                "deleted_rows": 0,
                "inserted_rows": 0,
                "total_records": None,
                "rows_per_page": payload["rows"],
                "total_pages": None,
                "target_pages": None,
                "start_page": payload["start_page"],
                "end_page": payload["end_page"],
                "current_page": None,
                "processed_pages": 0,
                "elapsed_text": "0秒",
                "elapsed_seconds": 0.0,
                "last_page_elapsed_text": "-",
                "last_page_elapsed_seconds": 0.0,
                "message": "任务已创建，等待开始",
                "logs": ["任务已创建，等待开始"],
            }
        )
        Thread(target=_run_ingest_job, args=(job_id, payload), daemon=True).start()
    except BaseException as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify({"ok": True, "job_id": job_id})


@bp.get("/status/<job_id>")
@login_required
def ingest_status(job_id: str):
    """
    获取抓取任务状态。

    Args:
        job_id (str): 任务 ID。

    Returns:
        Response: JSON 响应，包含 ok 与 job 数据或 error 信息。
    """
    job = get_job(job_id)
    if job is None:
        return jsonify({"ok": False, "error": "任务不存在"}), 404
    return jsonify({"ok": True, "job": job})


@bp.post("/cancel/<job_id>")
@login_required
def ingest_cancel(job_id: str):
    job = get_job(job_id)
    if job is None:
        return jsonify({"ok": False, "error": "任务不存在"}), 404
    status = job.get("status")
    if status in {"success", "error", "cancelled"}:
        return jsonify({"ok": False, "error": "任务已结束，无法终止"}), 400
    update_job(job_id, {"cancel_requested": True, "message": "已收到终止请求，正在停止..."})
    append_job_log(job_id, "已收到终止请求，正在停止...")
    return jsonify({"ok": True})


@bp.post("/resume/<job_id>")
@login_required
def ingest_resume(job_id: str):
    job = get_job(job_id)
    if job is None:
        return jsonify({"ok": False, "error": "任务不存在"}), 404
    if job.get("status") != "error":
        return jsonify({"ok": False, "error": "仅失败任务支持继续"}), 400

    version = (job.get("version") or "").strip()
    if not version:
        return jsonify({"ok": False, "error": "任务缺少版本号，无法继续"}), 400

    rows = job.get("rows") or job.get("rows_per_page")
    waiting_time = job.get("waiting_time")
    max_retries = job.get("max_retries")
    retry_delay_seconds = job.get("retry_delay_seconds")
    if rows is None or waiting_time is None or max_retries is None or retry_delay_seconds is None:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "任务缺少必要参数（rows/waiting_time/max_retries/retry_delay_seconds），无法继续",
                }
            ),
            400,
        )

    base_inserted_rows = int(job.get("inserted_rows") or 0)
    base_processed_pages = int(job.get("processed_pages") or 0)
    base_elapsed_seconds = float(job.get("elapsed_seconds") or 0.0)

    resume_start_page = base_processed_pages + 1
    effective_end = job.get("end_page") or job.get("total_pages")
    if effective_end is not None and resume_start_page > int(effective_end):
        return jsonify({"ok": False, "error": "已无待处理页，无需继续"}), 400

    payload = {
        "version": version,
        "rows": int(rows),
        "start_page": resume_start_page,
        "end_page": job.get("end_page"),
        "clear_existing": False,
        "waiting_time": int(waiting_time),
        "max_retries": int(max_retries),
        "retry_delay_seconds": float(retry_delay_seconds),
        "base_inserted_rows": base_inserted_rows,
        "base_processed_pages": base_processed_pages,
        "base_elapsed_seconds": base_elapsed_seconds,
    }

    new_job_id = create_job(
        {
            "status": "queued",
            "version": version,
            "rows": int(rows),
            "waiting_time": int(waiting_time),
            "max_retries": int(max_retries),
            "retry_delay_seconds": float(retry_delay_seconds),
            "clear_existing": False,
            "base_inserted_rows": base_inserted_rows,
            "base_processed_pages": base_processed_pages,
            "base_elapsed_seconds": base_elapsed_seconds,
            "source_job_id": job_id,
            "deleted_rows": 0,
            "inserted_rows": base_inserted_rows,
            "total_records": job.get("total_records"),
            "rows_per_page": int(rows),
            "total_pages": job.get("total_pages"),
            "start_page": resume_start_page,
            "end_page": job.get("end_page"),
            "current_page": None,
            "processed_pages": base_processed_pages,
            "elapsed_seconds": base_elapsed_seconds,
            "elapsed_text": _format_duration(base_elapsed_seconds),
            "last_page_elapsed_text": job.get("last_page_elapsed_text") or "-",
            "last_page_elapsed_seconds": float(job.get("last_page_elapsed_seconds") or 0.0),
            "message": f"续跑任务已创建，等待开始（从第 {resume_start_page} 页继续）",
            "logs": [f"续跑任务已创建，等待开始（从第 {resume_start_page} 页继续）"],
        }
    )
    Thread(target=_run_ingest_job, args=(new_job_id, payload), daemon=True).start()
    append_job_log(job_id, f"已创建续跑任务：{new_job_id}")
    return jsonify({"ok": True, "job_id": new_job_id})
