"""提示词模板管理路由"""
import json
import os
import time
from aiohttp import web

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompt_templates.json")


def load_templates():
    """加载模板"""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"templates": []}


def save_templates(data):
    """保存模板"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


async def list_templates(request):
    """获取模板列表"""
    data = load_templates()
    return web.json_response(data)


async def add_template(request):
    """添加模板"""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "无效的JSON"}, status=400)

    name = body.get("name", "").strip()
    prompt = body.get("prompt", "").strip()

    if not name or not prompt:
        return web.json_response({"error": "名称和提示词不能为空"}, status=400)

    data = load_templates()
    template_id = f"tpl_{int(time.time() * 1000)}"

    data["templates"].append({
        "id": template_id,
        "name": name,
        "prompt": prompt
    })
    save_templates(data)

    return web.json_response({"ok": True, "id": template_id})


async def update_template(request):
    """更新模板"""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "无效的JSON"}, status=400)

    template_id = body.get("id")
    if not template_id:
        return web.json_response({"error": "缺少 id"}, status=400)

    data = load_templates()
    for t in data["templates"]:
        if t.get("id") == template_id:
            if "name" in body:
                t["name"] = body["name"]
            if "prompt" in body:
                t["prompt"] = body["prompt"]
            break
    else:
        return web.json_response({"error": "未找到该模板"}, status=404)

    save_templates(data)
    return web.json_response({"ok": True})


async def delete_template(request):
    """删除模板"""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "无效的JSON"}, status=400)

    template_id = body.get("id")
    if not template_id:
        return web.json_response({"error": "缺少 id"}, status=400)

    data = load_templates()
    data["templates"] = [t for t in data["templates"] if t.get("id") != template_id]
    save_templates(data)

    return web.json_response({"ok": True})
