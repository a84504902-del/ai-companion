"""数据库操作模块"""
import sqlite3
from datetime import datetime
from config import DB_PATH


def connect():
    """统一数据库连接入口"""
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = connect()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        tags TEXT DEFAULT '',
        session_id TEXT DEFAULT ''
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_mem_ts ON memories(timestamp)")

    c.execute("""CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        title TEXT,
        system_prompt TEXT DEFAULT '',
        created TEXT,
        updated TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS people (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER DEFAULT 0,
        description TEXT DEFAULT '',
        session_id TEXT DEFAULT ''
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS relations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_a_id INTEGER NOT NULL,
        relation_type TEXT NOT NULL,
        person_b_id INTEGER NOT NULL,
        session_id TEXT DEFAULT ''
    )""")

    # 迁移：添加 system_prompt 列（如果不存在）
    try:
        conn.execute("SELECT system_prompt FROM sessions LIMIT 1")
    except Exception:
        conn.execute("ALTER TABLE sessions ADD COLUMN system_prompt TEXT DEFAULT ''")

    # 迁移：添加 title_locked 列（如果不存在）
    try:
        conn.execute("SELECT title_locked FROM sessions LIMIT 1")
    except Exception:
        conn.execute("ALTER TABLE sessions ADD COLUMN title_locked INTEGER DEFAULT 0")

    conn.commit()
    conn.close()


def new_session_id():
    """生成新的会话ID"""
    return f"session_{int(datetime.now().timestamp() * 1000)}"


def create_message_table(session_id):
    """创建会话消息表"""
    table_name = f"messages_{session_id}"
    conn = connect()
    conn.execute(f"""CREATE TABLE IF NOT EXISTS [{table_name}] (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )""")
    conn.commit()
    conn.close()


def drop_message_table(session_id):
    """删除会话消息表"""
    table_name = f"messages_{session_id}"
    conn = connect()
    conn.execute(f"DROP TABLE IF EXISTS [{table_name}]")
    conn.commit()
    conn.close()


def save_message(session_id, role, content):
    """保存消息"""
    table_name = f"messages_{session_id}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = connect()
    conn.execute(f"INSERT INTO [{table_name}] (role, content, timestamp) VALUES (?, ?, ?)",
                 (role, content, timestamp))
    conn.commit()
    conn.close()


def load_messages(session_id):
    """加载会话消息"""
    table_name = f"messages_{session_id}"
    conn = connect()
    try:
        rows = conn.execute(f"SELECT role, content, timestamp FROM [{table_name}] ORDER BY id").fetchall()
        return [{"role": r["role"], "content": r["content"], "timestamp": r["timestamp"]} for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def get_message_count(session_id):
    """获取消息数量"""
    table_name = f"messages_{session_id}"
    conn = connect()
    try:
        count = conn.execute(f"SELECT COUNT(*) FROM [{table_name}]").fetchone()[0]
        return count
    except Exception:
        return 0
    finally:
        conn.close()


# 记忆操作
def save_memory(content, tags="", session_id=""):
    """保存记忆"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = connect()
    conn.execute("INSERT INTO memories (content, timestamp, tags, session_id) VALUES (?, ?, ?, ?)",
                 (content, timestamp, tags, session_id))
    conn.commit()
    conn.close()


def load_memories(tag=None, session_id=None):
    """加载记忆列表"""
    conn = connect()
    query = "SELECT id, content, timestamp, tags, session_id FROM memories"
    conditions = []
    params = []

    if tag:
        conditions.append("tags LIKE ?")
        params.append(f"%{tag}%")
    if session_id:
        conditions.append("session_id = ?")
        params.append(session_id)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY timestamp DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_memory(memory_id):
    """删除记忆"""
    conn = connect()
    conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    conn.commit()
    conn.close()


# 会话操作
def get_all_sessions():
    """获取所有会话"""
    conn = connect()
    rows = conn.execute("SELECT id, title, system_prompt, created, updated FROM sessions ORDER BY updated DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session(session_id):
    """获取单个会话"""
    conn = connect()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_session(session_id, title=None, system_prompt=None):
    """创建会话"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not title:
        title = f"新对话 {datetime.now().strftime('%H:%M')}"
    if not system_prompt:
        system_prompt = ""
    conn = connect()
    conn.execute("INSERT INTO sessions (id, title, system_prompt, created, updated) VALUES (?, ?, ?, ?, ?)",
                 (session_id, title, system_prompt, timestamp, timestamp))
    conn.commit()
    conn.close()


def update_session(session_id, title=None, system_prompt=None):
    """更新会话"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = connect()
    if title is not None and system_prompt is not None:
        conn.execute("UPDATE sessions SET title = ?, system_prompt = ?, updated = ? WHERE id = ?",
                     (title, system_prompt, timestamp, session_id))
    elif title is not None:
        conn.execute("UPDATE sessions SET title = ?, updated = ? WHERE id = ?",
                     (title, timestamp, session_id))
    elif system_prompt is not None:
        conn.execute("UPDATE sessions SET system_prompt = ?, updated = ? WHERE id = ?",
                     (system_prompt, timestamp, session_id))
    else:
        conn.execute("UPDATE sessions SET updated = ? WHERE id = ?", (timestamp, session_id))
    conn.commit()
    conn.close()


def update_system_prompt(session_id, system_prompt):
    """更新系统提示词"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = connect()
    conn.execute("UPDATE sessions SET system_prompt = ?, updated = ? WHERE id = ?",
                 (system_prompt, timestamp, session_id))
    conn.commit()
    conn.close()


def rename_session(session_id, new_title):
    """重命名会话并锁定标题"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = connect()
    conn.execute("UPDATE sessions SET title = ?, title_locked = 1, updated = ? WHERE id = ?",
                 (new_title, timestamp, session_id))
    conn.commit()
    conn.close()


def is_title_locked(session_id):
    """检查标题是否已锁定"""
    conn = connect()
    row = conn.execute("SELECT title_locked FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return row["title_locked"] if row else False


def delete_session(session_id):
    """删除会话"""
    conn = connect()
    conn.execute("DELETE FROM memories WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM people WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM relations WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    drop_message_table(session_id)


# 人物操作
def get_people(session_id):
    """获取人物列表"""
    conn = connect()
    rows = conn.execute("SELECT id, name, age, description FROM people WHERE session_id = ?",
                        (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_person(name, age=0, description="", session_id=""):
    """添加人物"""
    conn = connect()
    cursor = conn.execute("INSERT INTO people (name, age, description, session_id) VALUES (?, ?, ?, ?)",
                          (name, age, description, session_id))
    person_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return person_id


def update_person(person_id, name=None, age=None, description=None):
    """更新人物"""
    conn = connect()
    if name is not None:
        conn.execute("UPDATE people SET name = ? WHERE id = ?", (name, person_id))
    if age is not None:
        conn.execute("UPDATE people SET age = ? WHERE id = ?", (age, person_id))
    if description is not None:
        conn.execute("UPDATE people SET description = ? WHERE id = ?", (description, person_id))
    conn.commit()
    conn.close()


def delete_person(person_id):
    """删除人物"""
    conn = connect()
    conn.execute("DELETE FROM people WHERE id = ?", (person_id,))
    conn.execute("DELETE FROM relations WHERE person_a_id = ? OR person_b_id = ?",
                 (person_id, person_id))
    conn.commit()
    conn.close()


# 关系操作
def get_relations(session_id):
    """获取关系列表"""
    conn = connect()
    rows = conn.execute("""
        SELECT r.id, r.relation_type, r.person_a_id, r.person_b_id,
               pa.name as person_a_name, pb.name as person_b_name
        FROM relations r
        LEFT JOIN people pa ON r.person_a_id = pa.id
        LEFT JOIN people pb ON r.person_b_id = pb.id
        WHERE r.session_id = ?
    """, (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_relation(person_a_id, relation_type, person_b_id, session_id=""):
    """添加关系"""
    conn = connect()
    cursor = conn.execute(
        "INSERT INTO relations (person_a_id, relation_type, person_b_id, session_id) VALUES (?, ?, ?, ?)",
        (person_a_id, relation_type, person_b_id, session_id))
    relation_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return relation_id


def update_relation(relation_id, relation_type):
    """更新关系"""
    conn = connect()
    conn.execute("UPDATE relations SET relation_type = ? WHERE id = ?",
                 (relation_type, relation_id))
    conn.commit()
    conn.close()


def delete_relation(relation_id):
    """删除关系"""
    conn = connect()
    conn.execute("DELETE FROM relations WHERE id = ?", (relation_id,))
    conn.commit()
    conn.close()


def search_messages(query):
    """搜索所有会话的消息"""
    conn = connect()
    results = []

    # 获取所有消息表
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'messages_%'"
    ).fetchall()

    for table in tables:
        table_name = table["name"]
        session_id = table_name.replace("messages_", "")

        try:
            rows = conn.execute(
                f"SELECT role, content, timestamp FROM [{table_name}] WHERE content LIKE ? ORDER BY timestamp DESC LIMIT 10",
                (f"%{query}%",)
            ).fetchall()

            for row in rows:
                # 获取会话标题
                session = conn.execute(
                    "SELECT title FROM sessions WHERE id = ?", (session_id,)
                ).fetchone()
                title = session["title"] if session else "未知会话"

                results.append({
                    "session_id": session_id,
                    "session_title": title,
                    "role": row["role"],
                    "content": row["content"],
                    "timestamp": row["timestamp"]
                })
        except Exception:
            continue

    conn.close()

    # 按时间倒序排列
    results.sort(key=lambda x: x["timestamp"], reverse=True)
    return results


def get_stats():
    """获取统计数据"""
    conn = connect()
    stats = {}

    # 会话数
    stats["session_count"] = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]

    # 消息总数
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'messages_%'").fetchall()
    total_messages = 0
    for t in tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM [{t['name']}]").fetchone()[0]
            total_messages += count
        except Exception:
            pass
    stats["message_count"] = total_messages

    # 记忆数
    stats["memory_count"] = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

    # 人物数
    stats["people_count"] = conn.execute("SELECT COUNT(*) FROM people").fetchone()[0]

    conn.close()
    return stats
