/* AI Companion - 主应用逻辑 */

// 状态
let currentSession = null;
let sessions = [];
let ttsEnabled = true;

// 切换 TTS
function toggleTTS() {
    ttsEnabled = !ttsEnabled;
    const btn = document.getElementById('ttsBtn');
    btn.classList.toggle('active', ttsEnabled);
    btn.textContent = ttsEnabled ? '🔊' : '🔇';
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadSessions();
    loadCustomLLMs();
    setupTextarea();
});

// 设置文本框
function setupTextarea() {
    const input = document.getElementById('messageInput');
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

// 加载自定义 LLM
async function loadCustomLLMs() {
    try {
        const resp = await fetch('/api/llms');
        const data = await resp.json();
        const select = document.getElementById('llmSelect');

        // 清空现有选项
        select.innerHTML = '';

        if (data.llms && data.llms.length > 0) {
            data.llms.forEach(llm => {
                const option = document.createElement('option');
                option.value = llm.id;
                option.textContent = llm.name;
                select.appendChild(option);
            });

            // 恢复上次选择
            const saved = localStorage.getItem('selected_llm');
            if (saved && data.llms.some(l => l.id === saved)) {
                select.value = saved;
            }
        }

        // 保存选择
        select.addEventListener('change', () => {
            localStorage.setItem('selected_llm', select.value);
        });
    } catch (e) {
        console.error('加载 LLM 列表失败:', e);
    }
}

// 加载会话列表
async function loadSessions() {
    try {
        const resp = await fetch('/chat_sessions');
        const data = await resp.json();
        sessions = data.sessions;
        currentSession = data.current;
        renderSessions();
        if (currentSession) {
            loadHistory();
        }
    } catch (e) {
        console.error('加载会话失败:', e);
    }
}

// 渲染会话列表
function renderSessions() {
    const list = document.getElementById('sessionList');
    list.innerHTML = sessions.map(s => `
        <div class="session-item ${s.id === currentSession ? 'active' : ''}" onclick="switchSession('${s.id}')">
            <span class="session-title">${escapeHtml(s.title || '新对话')}</span>
            <button class="session-delete" onclick="event.stopPropagation(); deleteSession('${s.id}')">&times;</button>
        </div>
    `).join('');
}

// 加载聊天历史
async function loadHistory() {
    try {
        const resp = await fetch('/history');
        const data = await resp.json();
        renderMessages(data.history);
    } catch (e) {
        console.error('加载历史失败:', e);
    }
}

// 渲染消息
function renderMessages(history) {
    const container = document.getElementById('chatMessages');
    container.innerHTML = history.map(msg => `
        <div class="message ${msg.role}">
            <div class="message-content">${escapeHtml(msg.content)}</div>
        </div>
    `).join('');
    container.scrollTop = container.scrollHeight;
}

// 发送消息
async function sendMessage() {
    const input = document.getElementById('messageInput');
    const text = input.value.trim();
    if (!text) return;

    const mode = document.getElementById('llmSelect').value;
    input.value = '';

    // 先显示用户消息
    appendMessage('user', text);

    try {
        const resp = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, mode })
        });
        const data = await resp.json();

        if (data.error) {
            appendMessage('assistant', '错误: ' + data.error);
        } else {
            appendMessage('assistant', data.response, data.audio_url);

            // 自动播放 TTS
            if (data.audio_url && ttsEnabled) {
                playAudio(data.audio_url);
            }
        }
    } catch (e) {
        appendMessage('assistant', '发送失败: ' + e.message);
    }
}

// 追加消息
function appendMessage(role, content, audioUrl) {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = `message ${role}`;

    let audioBtn = '';
    if (role === 'assistant' && audioUrl) {
        audioBtn = `<button class="btn-audio" onclick="playAudio('${audioUrl}')">🔊 播放</button>`;
    }

    div.innerHTML = `
        <div class="message-content">${escapeHtml(content)}${audioBtn}</div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

// 播放音频
function playAudio(url) {
    const audio = new Audio(url);
    audio.play().catch(e => console.log('播放失败:', e));
}

// 新建对话
async function newChat() {
    try {
        const resp = await fetch('/new_chat', { method: 'POST' });
        const data = await resp.json();
        currentSession = data.session_id;
        document.getElementById('chatMessages').innerHTML = '';
        loadSessions();
    } catch (e) {
        console.error('新建对话失败:', e);
    }
}

// 切换对话
async function switchSession(sessionId) {
    try {
        const resp = await fetch('/switch_chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        const data = await resp.json();
        currentSession = sessionId;
        renderMessages(data.history);
        loadSessions();
    } catch (e) {
        console.error('切换对话失败:', e);
    }
}

// 删除对话
async function deleteSession(sessionId) {
    if (!confirm('确定删除这个对话？')) return;
    try {
        await fetch('/delete_session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        loadSessions();
    } catch (e) {
        console.error('删除失败:', e);
    }
}

// 清空对话
async function clearChat() {
    if (!confirm('确定清空当前对话？')) return;
    try {
        await fetch('/clear_chat', { method: 'POST' });
        document.getElementById('chatMessages').innerHTML = '';
    } catch (e) {
        console.error('清空失败:', e);
    }
}

// 导出对话
async function exportChat() {
    try {
        const resp = await fetch('/export_chat');
        const data = await resp.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `chat_${new Date().toISOString().slice(0,10)}.json`;
        a.click();
    } catch (e) {
        console.error('导出失败:', e);
    }
}

// 切换面板标签
function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));

    event.target.classList.add('active');
    document.getElementById(tab + 'Panel').classList.add('active');

    // 加载对应内容
    if (tab === 'memory') loadMemories();
    if (tab === 'people') loadPeople();
    if (tab === 'relations') loadRelations();
    if (tab === 'prompt') loadSystemPrompt();
}

// 加载系统提示词
async function loadSystemPrompt() {
    try {
        const resp = await fetch('/api/system_prompt');
        const data = await resp.json();
        document.getElementById('systemPromptInput').value = data.system_prompt || '';
    } catch (e) {
        console.error('加载系统提示词失败:', e);
    }
}

// 保存系统提示词
async function saveSystemPrompt() {
    const prompt = document.getElementById('systemPromptInput').value;
    try {
        await fetch('/api/system_prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ system_prompt: prompt })
        });
        alert('保存成功');
    } catch (e) {
        alert('保存失败: ' + e.message);
    }
}

// 加载记忆
async function loadMemories() {
    try {
        const resp = await fetch('/memories');
        const data = await resp.json();
        const panel = document.getElementById('memoryPanel');
        if (!data.memories || data.memories.length === 0) {
            panel.innerHTML = '<p style="color: #999;">暂无记忆</p>';
            return;
        }
        panel.innerHTML = data.memories.map(m => `
            <div class="memory-item">
                <div class="memory-content">${escapeHtml(m.content)}</div>
                <div class="memory-meta">
                    <span>${m.timestamp}</span>
                    <button class="btn btn-danger btn-sm" onclick="deleteMemory(${m.id})">删除</button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.error('加载记忆失败:', e);
    }
}

// 删除记忆
async function deleteMemory(id) {
    if (!confirm('确定删除这条记忆？')) return;
    try {
        await fetch('/delete_memory', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
        });
        loadMemories();
    } catch (e) {
        alert('删除失败: ' + e.message);
    }
}

// 加载人物
async function loadPeople() {
    try {
        const resp = await fetch(`/api/people/list?session_id=${currentSession}`);
        const data = await resp.json();
        const panel = document.getElementById('peoplePanel');

        let html = '<div class="add-section">';
        html += '<input type="text" id="newPersonName" placeholder="名字" class="input-sm">';
        html += '<input type="text" id="newPersonDesc" placeholder="描述（如：妈妈、朋友）" class="input-sm">';
        html += '<button class="btn btn-primary btn-sm" onclick="addPerson()">添加</button>';
        html += '</div>';

        if (!data.people || data.people.length === 0) {
            html += '<p style="color: #999; margin-top: 12px;">暂无人物</p>';
        } else {
            html += data.people.map(p => `
                <div class="person-item">
                    <div class="person-name">${escapeHtml(p.name)}</div>
                    <div class="person-desc">${escapeHtml(p.description || '无描述')}</div>
                    <button class="btn btn-danger btn-sm" onclick="deletePerson(${p.id})">删除</button>
                </div>
            `).join('');
        }

        panel.innerHTML = html;
    } catch (e) {
        console.error('加载人物失败:', e);
    }
}

// 添加人物
async function addPerson() {
    const name = document.getElementById('newPersonName').value.trim();
    const desc = document.getElementById('newPersonDesc').value.trim();
    if (!name) { alert('请输入名字'); return; }

    try {
        await fetch('/api/people/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description: desc, session_id: currentSession })
        });
        loadPeople();
    } catch (e) {
        alert('添加失败: ' + e.message);
    }
}

// 删除人物
async function deletePerson(id) {
    if (!confirm('确定删除？相关关系也会被删除')) return;
    try {
        await fetch('/api/people/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
        });
        loadPeople();
        loadRelations();
    } catch (e) {
        alert('删除失败: ' + e.message);
    }
}

// 加载关系
async function loadRelations() {
    try {
        const resp = await fetch(`/api/relations/list?session_id=${currentSession}`);
        const data = await resp.json();
        const panel = document.getElementById('relationsPanel');

        // 获取当前会话的人物列表
        const peopleResp = await fetch(`/api/people/list?session_id=${currentSession}`);
        const peopleData = await peopleResp.json();
        const people = peopleData.people || [];

        let html = '<div class="add-section">';
        html += '<select id="relPersonA" class="input-sm"><option value="">选择人物A</option>';
        people.forEach(p => { html += `<option value="${p.id}">${escapeHtml(p.name)}</option>`; });
        html += '</select>';
        html += '<input type="text" id="relType" placeholder="关系（如：妈妈、朋友）" class="input-sm">';
        html += '<select id="relPersonB" class="input-sm"><option value="">选择人物B</option>';
        people.forEach(p => { html += `<option value="${p.id}">${escapeHtml(p.name)}</option>`; });
        html += '</select>';
        html += '<button class="btn btn-primary btn-sm" onclick="addRelation()">添加</button>';
        html += '</div>';

        if (!data.relations || data.relations.length === 0) {
            html += '<p style="color: #999; margin-top: 12px;">暂无关系</p>';
        } else {
            html += data.relations.map(r => `
                <div class="relation-item">
                    <span>${escapeHtml(r.person_a_name)} → ${escapeHtml(r.relation_type)} → ${escapeHtml(r.person_b_name)}</span>
                    <button class="btn btn-danger btn-sm" onclick="deleteRelation(${r.id})">删除</button>
                </div>
            `).join('');
        }

        panel.innerHTML = html;
    } catch (e) {
        console.error('加载关系失败:', e);
    }
}

// 添加关系
async function addRelation() {
    const personA = document.getElementById('relPersonA').value;
    const type = document.getElementById('relType').value.trim();
    const personB = document.getElementById('relPersonB').value;
    if (!personA || !type || !personB) { alert('请填写完整'); return; }

    try {
        await fetch('/api/relations/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                person_a_id: parseInt(personA),
                relation_type: type,
                person_b_id: parseInt(personB),
                session_id: currentSession
            })
        });
        loadRelations();
    } catch (e) {
        alert('添加失败: ' + e.message);
    }
}

// 删除关系
async function deleteRelation(id) {
    if (!confirm('确定删除？')) return;
    try {
        await fetch('/api/relations/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
        });
        loadRelations();
    } catch (e) {
        alert('删除失败: ' + e.message);
    }
}

// HTML 转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
