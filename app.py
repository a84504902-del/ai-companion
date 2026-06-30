"""AI Companion - 主应用入口"""
import os
import asyncio
from aiohttp import web

import db
import config
from routes import chat, memory, person, relation, admin, custom_llm


async def index_handler(request):
    """返回主页"""
    with open(os.path.join(config.BASE_DIR, "templates", "index.html"), "r", encoding="utf-8") as f:
        return web.Response(text=f.read(), content_type="text/html")


async def admin_page_handler(request):
    """返回后台管理页面"""
    with open(os.path.join(config.BASE_DIR, "templates", "admin.html"), "r", encoding="utf-8") as f:
        return web.Response(text=f.read(), content_type="text/html")


async def audio_handler(request):
    """返回音频文件"""
    filename = request.match_info["filename"]
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio", f"{filename}.mp3")

    if not os.path.exists(filepath):
        import tempfile
        filepath = os.path.join(tempfile.gettempdir(), f"tts_{filename}.mp3")

    if os.path.exists(filepath):
        with open(filepath, "rb") as f:
            data = f.read()
        return web.Response(body=data, content_type="audio/mpeg")
    else:
        return web.Response(status=404, text="音频不存在")


def create_app():
    """创建应用"""
    app = web.Application()

    # 主页
    app.router.add_get("/", index_handler)
    app.router.add_get("/index.html", index_handler)

    # 后台管理页面
    app.router.add_get("/admin", admin_page_handler)

    # 音频
    app.router.add_get("/audio/{filename}", audio_handler)

    # 聊天
    app.router.add_post("/chat", chat.chat_handler)
    app.router.add_get("/history", chat.history_handler)
    app.router.add_get("/chat_sessions", chat.sessions_handler)
    app.router.add_post("/new_chat", chat.new_chat_handler)
    app.router.add_post("/switch_chat", chat.switch_chat_handler)
    app.router.add_post("/clear_chat", chat.clear_chat_handler)
    app.router.add_post("/delete_session", chat.delete_session_handler)
    app.router.add_get("/search_history", chat.search_history_handler)
    app.router.add_get("/export_chat", chat.export_chat_handler)
    app.router.add_post("/api/system_prompt", chat.update_system_prompt_handler)
    app.router.add_get("/api/system_prompt", chat.get_system_prompt_handler)
    app.router.add_get("/api/summarize", chat.summarize_handler)

    # 记忆
    app.router.add_get("/memories", memory.list_memories)
    app.router.add_post("/api/save_memory", memory.save_memory)
    app.router.add_post("/delete_memory", memory.delete_memory)

    # 人物
    app.router.add_get("/api/people/list", person.list_people)
    app.router.add_post("/api/people/add", person.add_person)
    app.router.add_post("/api/people/update", person.update_person)
    app.router.add_post("/api/people/delete", person.delete_person)

    # 关系
    app.router.add_get("/api/relations/list", relation.list_relations)
    app.router.add_post("/api/relations/add", relation.add_relation)
    app.router.add_post("/api/relations/update", relation.update_relation)
    app.router.add_post("/api/relations/delete", relation.delete_relation)

    # 后台 API
    app.router.add_get("/api/stats", admin.stats_handler)
    app.router.add_get("/api/llm_status", admin.llm_status_handler)
    app.router.add_get("/api/sessions", admin.sessions_handler)
    app.router.add_get("/api/database/info", admin.database_info_handler)
    app.router.add_post("/api/database/vacuum", admin.database_vacuum_handler)

    # 自定义 LLM
    app.router.add_get("/api/llms", custom_llm.list_llms)
    app.router.add_post("/api/llms/add", custom_llm.add_llm)
    app.router.add_post("/api/llms/update", custom_llm.update_llm)
    app.router.add_post("/api/llms/delete", custom_llm.delete_llm)
    app.router.add_post("/api/llms/test", custom_llm.test_llm)

    # 静态文件
    app.router.add_static("/static", os.path.join(config.BASE_DIR, "static"))

    return app


def main():
    """启动应用"""
    # 初始化数据库
    db.init_db()

    # 创建默认会话
    sessions = db.get_all_sessions()
    if not sessions:
        session_id = db.new_session_id()
        db.create_session(session_id)
        db.create_message_table(session_id)
        chat._current_session_id = session_id
    else:
        chat._current_session_id = sessions[0]["id"]

    print(f"AI Companion 启动中...")
    print(f"访问地址: http://localhost:{config.PORT}")
    print(f"数据库: {config.DB_PATH}")

    app = create_app()
    web.run_app(app, host=config.HOST, port=config.PORT)


if __name__ == "__main__":
    main()
