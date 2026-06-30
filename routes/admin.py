"""后台管理路由"""
import os
import sqlite3
from aiohttp import web
import db
import config


async def stats_handler(request):
    """获取系统统计"""
    stats = db.get_stats()
    return web.json_response(stats)


async def llm_status_handler(request):
    """获取 LLM 配置状态"""
    from config import (
        DEEPSEEK_API_KEY, ZHIPU_API_KEY, DASHSCOPE_API_KEY,
        BAIDU_API_KEY, AGNES_API_KEY
    )

    status = {
        "deepseek": bool(DEEPSEEK_API_KEY),
        "zhipu": bool(ZHIPU_API_KEY),
        "qwen": bool(DASHSCOPE_API_KEY),
        "baidu": bool(BAIDU_API_KEY),
        "agnes": bool(AGNES_API_KEY),
        "ollama": True  # 本地服务默认可用
    }
    return web.json_response(status)


async def sessions_handler(request):
    """获取所有会话"""
    sessions = db.get_all_sessions()
    result = []
    for s in sessions:
        msg_count = db.get_message_count(s["id"])
        result.append({
            "id": s["id"],
            "title": s["title"],
            "created": s["created"],
            "msg_count": msg_count
        })
    return web.json_response({"sessions": result})


async def database_info_handler(request):
    """获取数据库信息"""
    db_path = config.DB_PATH
    info = {"path": db_path, "size": "-", "tables": "-"}

    if os.path.exists(db_path):
        size = os.path.getsize(db_path)
        if size < 1024:
            info["size"] = f"{size} B"
        elif size < 1024 * 1024:
            info["size"] = f"{size / 1024:.1f} KB"
        else:
            info["size"] = f"{size / (1024 * 1024):.1f} MB"

        try:
            conn = sqlite3.connect(db_path)
            count = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
            info["tables"] = str(count)
            conn.close()
        except Exception:
            pass

    return web.json_response(info)


async def database_vacuum_handler(request):
    """压缩数据库"""
    try:
        conn = sqlite3.connect(config.DB_PATH)
        conn.execute("VACUUM")
        conn.close()
        return web.json_response({"ok": True})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
