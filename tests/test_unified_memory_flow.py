import os
import re
import json
import sqlite3
import shutil
import pytest
from pathlib import Path
from datetime import datetime, timezone

from agent.memory.manager import MemoryManager
from agent.evolution.memory import extract_coworker_memory
from agent.tools.skill_usage_tool import RecordSkillUsageTool
from agent.core.prompt_builder import _search_experiences

@pytest.fixture(autouse=True)
def setup_test_sandbox(tmp_path):
    from agent.core import paths
    return {"isolated_dir": tmp_path, "exp_dir": paths.EXPERIENCES_DIR,
            "skills_dir": paths.SKILLS_DIR, "context_dir": paths.CONTEXT_DIR}

@pytest.mark.asyncio
async def test_coworker_context_memory_flow(setup_test_sandbox):
    """测试 Task 2.3 & 4.2: 社交经历 coworker 极简隔离记忆 json 在 agent_memory/context 中的正确存取"""
    class MockLLM:
        model = "mock-model"
        async def chat(self, messages, tools=None, model_override=None):
            return {"content": '{"memories": ["偏好使用 Python", "不喜废话"]}'}
            
    class MockAgent:
        current_user_id = "test_user_123"
        messages = [
            {"role": "user", "content": "你好小萤"},
            {"role": "assistant", "content": "你好！有什么我可以帮你的？"},
            {"role": "user", "content": "我写代码喜欢用 Python，比较追求极简"},
            {"role": "assistant", "content": "好哒，我记住啦！"}
        ]
        llm = MockLLM()
        
    # 模拟提取记忆
    await extract_coworker_memory(MockAgent())
    
    # 核验写入物理路径
    target_json = setup_test_sandbox["context_dir"] / "coworker_test_user_123.json"
    assert target_json.exists(), f"社交记忆 json 未成功写入目标路径: {target_json}"
    
    data = json.loads(target_json.read_text(encoding="utf-8"))
    assert "memories" in data
    assert "偏好使用 Python" in data["memories"]
    assert len(data["memories"]) <= 3

@pytest.mark.asyncio
async def test_experience_rag_search_flow(setup_test_sandbox):
    from types import SimpleNamespace
    memory = MemoryManager()
    memory.save_ki({"id": "test_git", "title": "git 冲突", "category": "experience", "keywords": ["git"],
                    "summary": "解决冲突", "content": "git fetch origin", "ki_type": "experience"})
    matched = await _search_experiences(SimpleNamespace(memory=memory), "git")
    assert "MEMORY BLOCK" in matched
    assert "git fetch origin" in matched

@pytest.mark.asyncio
async def test_experience_to_skills_promotion_flow(setup_test_sandbox):
    """测试 Task 3.1 & 3.2 & 4.4: 累加打分、SQLite 同步以及满 5 次 90% 成功率时 Experiences ➔ Skills 的物理搬家晋升"""
    exp_dir = setup_test_sandbox["exp_dir"]
    skills_dir = setup_test_sandbox["skills_dir"]
    
    # 建立一条临时测试经验
    skill_name = "test_case_hotkey_run"
    exp_file = exp_dir / f"{skill_name}.md"
    content = f"""---
name: {skill_name}
trigger: 快捷键/运行/调试
description: 模拟快捷键高效调试的经历
usage_count: 0
success_count: 0
category: verification
---

# 模拟调试
1. 按 Command+R 启动极速调试。
"""
    exp_file.write_text(content, encoding="utf-8")
    
    memory = MemoryManager()
    memory.save_ki({"id": "test_skill", "title": skill_name, "category": "experience", "keywords": [skill_name],
                    "summary": "调试经验", "content": content, "ki_type": "experience"})
    tool = RecordSkillUsageTool()
    
    # 1. 模拟 4 次成功打卡，此时 usage_count=4，应该依然保留在 experiences 目录下
    for _ in range(4):
        res_list = []
        async for res in tool.call({"skill_name": skill_name, "success": True}, context=None):
            res_list.append(res)
        assert "已记录" in res_list[0].data
        
    assert exp_file.exists()
    assert not (skills_dir / f"{skill_name}.md").exists()
    
    # 2. 模拟第 5 次打卡（success），达到 5 次且成功率 100% (>=90%) 门槛，触发自动物理搬家！
    res_list = []
    async for res in tool.call({"skill_name": skill_name, "success": True}, context=None):
        res_list.append(res)
        
    assert "技能晋级" in res_list[0].data
    
    # Promotion updates the SQLite KI; legacy files are not moved.
    assert memory._get_db().execute("SELECT ki_type FROM knowledge_items WHERE id='test_skill'").fetchone()[0] == "skill"

    # 4. 验证 SQLite 中的 is_skills 标记为 1
    mm = MemoryManager()
    db_path = mm.base_dir / "memories.db"
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute("SELECT usage_count, success_count, is_skills FROM skill_usage WHERE skill_name = ?", (skill_name,))
        row = cur.fetchone()
        assert row is not None
        db_usage, db_success, is_skills = row
        assert db_usage == 5
        assert db_success == 5
        assert is_skills == 1
    finally:
        conn.close()
