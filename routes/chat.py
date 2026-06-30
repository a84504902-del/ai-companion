"""聊天相关路由"""
import json
import hashlib
from aiohttp import web

import db
import llm
from tts import synthesize


# 内存中的会话状态
_chat_sessions = []
_current_session_id = None
_conversation_history = []


async def chat_handler(request):
    """处理聊天请求"""
    global _conversation_history, _current_session_id

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "无效的JSON"}, status=400)

    text = data.get("text", "").strip()
    mode = data.get("mode", "deepseek")

    if not text:
        return web.json_response({"error": "消息不能为空"}, status=400)

    # 处理保存记忆指令
    if text.startswith("保存记忆：") or text.startswith("保存记忆:"):
        memory_content = text.split("：", 1)[-1] if "：" in text else text.split(":", 1)[-1]
        db.save_memory(memory_content.strip(), session_id=_current_session_id)
        return web.json_response({"response": "已保存记忆", "audio_url": None})

    # 获取会话的系统提示词
    session = db.get_session(_current_session_id)
    system_prompt = session.get("system_prompt", "") if session else ""

    # 获取记忆和关系文本
    memory_text = ""
    relations = db.get_relations(_current_session_id)
    if relations:
        people = db.get_people(_current_session_id)
        people_map = {p["id"]: p["name"] for p in people}
        relation_lines = []
        for r in relations:
            name_a = people_map.get(r["person_a_id"], "未知")
            name_b = people_map.get(r["person_b_id"], "未知")
            relation_lines.append(f"{name_a} 是 {name_b} 的{r['relation_type']}")
        memory_text = "\n".join(relation_lines)

    # 调用 LLM
    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: llm.chat(text, mode, _conversation_history,
                                   system_prompt=system_prompt,
                                   memory_text=memory_text)
        )
    except Exception as e:
        return web.json_response({"error": f"LLM 调用失败: {e}"}, status=500)

    # 保存消息
    _conversation_history.append({"role": "user", "content": text})
    _conversation_history.append({"role": "assistant", "content": response})

    db.save_message(_current_session_id, "user", text)
    db.save_message(_current_session_id, "assistant", response)

    # 更新会话标题（取首条消息）
    if len(_conversation_history) == 2:
        title = text[:50] + ("..." if len(text) > 50 else "")
        db.update_session(_current_session_id, title)

    # 生成 TTS 音频
    audio_url = None
    try:
        from tts import synthesize as tts_synthesize
        text_hash = hashlib.md5(response.encode()).hexdigest()[:12]
        await tts_synthesize(response)
        audio_url = f"/audio/{text_hash}"
    except Exception:
        pass

    return web.json_response({
        "response": response,
        "audio_url": audio_url
    })


async def history_handler(request):
    """获取对话历史"""
    return web.json_response({"history": _conversation_history})


async def sessions_handler(request):
    """获取会话列表"""
    global _current_session_id

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

    return web.json_response({
        "sessions": result,
        "current": _current_session_id
    })


async def new_chat_handler(request):
    """新建会话"""
    global _current_session_id, _conversation_history, _chat_sessions

    # 保存当前会话
    if _current_session_id and _conversation_history:
        db.update_session(_current_session_id)

    # 创建新会话
    _current_session_id = db.new_session_id()
    _conversation_history = []
    db.create_session(_current_session_id)
    db.create_message_table(_current_session_id)

    _chat_sessions.append({
        "id": _current_session_id,
        "title": f"新对话",
        "history": []
    })

    return web.json_response({"session_id": _current_session_id})


async def switch_chat_handler(request):
    """切换会话"""
    global _current_session_id, _conversation_history

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "无效的JSON"}, status=400)

    session_id = data.get("session_id")
    if not session_id:
        return web.json_response({"error": "缺少 session_id"}, status=400)

    # 保存当前会话
    if _current_session_id and _conversation_history:
        db.update_session(_current_session_id)

    # 切换到目标会话
    _current_session_id = session_id
    messages = db.load_messages(session_id)
    _conversation_history = [{"role": m["role"], "content": m["content"]} for m in messages]

    return web.json_response({
        "session_id": session_id,
        "history": _conversation_history
    })


async def clear_chat_handler(request):
    """清空会话"""
    global _conversation_history

    if _current_session_id:
        db.drop_message_table(_current_session_id)
        db.create_message_table(_current_session_id)
        _conversation_history = []

    return web.json_response({"ok": True})


async def delete_session_handler(request):
    """删除会话"""
    global _current_session_id, _chat_sessions, _conversation_history

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "无效的JSON"}, status=400)

    session_id = data.get("session_id")
    if not session_id:
        return web.json_response({"error": "缺少 session_id"}, status=400)

    db.delete_session(session_id)

    # 从内存中移除
    _chat_sessions = [s for s in _chat_sessions if s["id"] != session_id]

    # 如果删除的是当前会话，切换到最后一个或新建
    if _current_session_id == session_id:
        if _chat_sessions:
            _current_session_id = _chat_sessions[-1]["id"]
            messages = db.load_messages(_current_session_id)
            _conversation_history = [{"role": m["role"], "content": m["content"]} for m in messages]
        else:
            _current_session_id = db.new_session_id()
            _conversation_history = []
            db.create_session(_current_session_id)
            db.create_message_table(_current_session_id)

    return web.json_response({"ok": True})


async def search_history_handler(request):
    """搜索历史消息"""
    query = request.query.get("q", "")
    if not query:
        return web.json_response({"results": []})

    results = db.search_messages(query)
    return web.json_response({"results": results[:50]})


async def export_chat_handler(request):
    """导出聊天记录"""
    return web.json_response({
        "session_id": _current_session_id,
        "messages": _conversation_history
    })


async def update_system_prompt_handler(request):
    """更新系统提示词"""
    global _current_session_id

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "无效的JSON"}, status=400)

    session_id = data.get("session_id", _current_session_id)
    system_prompt = data.get("system_prompt", "")

    db.update_system_prompt(session_id, system_prompt)
    return web.json_response({"ok": True})


async def get_system_prompt_handler(request):
    """获取系统提示词"""
    session_id = request.query.get("session_id", _current_session_id)
    session = db.get_session(session_id)
    if session:
        return web.json_response({"system_prompt": session.get("system_prompt", "")})
    return web.json_response({"system_prompt": ""})


# 导入 asyncio
import asyncio
