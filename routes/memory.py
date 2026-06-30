"""记忆管理路由"""
from aiohttp import web
import db


async def list_memories(request):
    """获取记忆列表"""
    tag = request.query.get("tag")
    session_id = request.query.get("session_id")
    memories = db.load_memories(tag=tag, session_id=session_id)
    return web.json_response({"memories": memories})


async def save_memory(request):
    """保存记忆"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "无效的JSON"}, status=400)

    content = data.get("content", "").strip()
    tags = data.get("tags", "")
    session_id = data.get("session_id", "")

    if not content:
        return web.json_response({"error": "内容不能为空"}, status=400)

    db.save_memory(content, tags, session_id)
    return web.json_response({"ok": True})


async def delete_memory(request):
    """删除记忆"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "无效的JSON"}, status=400)

    memory_id = data.get("id")
    if not memory_id:
        return web.json_response({"error": "缺少 id"}, status=400)

    db.delete_memory(memory_id)
    return web.json_response({"ok": True})
