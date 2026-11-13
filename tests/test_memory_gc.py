import pytest
import shutil
import os
from pathlib import Path
from agent.memory.manager import MemoryManager


@pytest.mark.asyncio
async def test_memory_gc_and_merge():
    # 1. 模拟一个临时记忆存储文件夹
    temp_memory_dir = "/tmp/test_agent_memory_gc"
    if os.path.exists(temp_memory_dir):
        shutil.rmtree(temp_memory_dir)
    os.makedirs(temp_memory_dir)

    try:
        manager = MemoryManager(base_dir=temp_memory_dir)
        
        # 2. 构造一些碎片反思小文件
        ref_proj_file = "reflect_project_20260520-000000.md"
        ref_user_file = "reflect_user_20260520-000000.md"
        
        p_proj = Path(temp_memory_dir) / ref_proj_file
        p_user = Path(temp_memory_dir) / ref_user_file
        
        p_proj.write_text("会话反思发现: 这是我项目中的重要教训", encoding="utf-8")
        p_user.write_text("会话反思发现: 亮哥喜欢极简中文语气", encoding="utf-8")
        
        # 3. 构造 MEMORY.md 索引，填入这两个碎片
        manager.index_file.write_text(
            f"# Memory Index\n\n"
            f"- [[project] 反思一]({ref_proj_file}) `2026-05-20T00:00:00Z`\n"
            f"- [[user] 偏好反思]({ref_user_file}) `2026-05-20T00:00:00Z`\n",
            encoding="utf-8"
        )
        
        # 4. 执行垃圾回收 (GC)
        cleaned_count = await manager.gc_and_merge_fragmented_memories()
        
        # 5. 断言验证
        # 校验：碎片小文件应该已经被物理删除
        assert cleaned_count == 2
        assert not p_proj.exists()
        assert not p_user.exists()
        
        # Core memories are stored in SQLite; no new Markdown copies are created.
        rows = manager._get_db().execute("SELECT title, content FROM knowledge_items").fetchall()
        assert any(title == "xl_code_review" and "这是我项目中的重要教训" in content for title, content in rows)
        assert any(title == "user_profile" and "亮哥喜欢极简中文语气" in content for title, content in rows)
        assert ref_proj_file not in manager.index_file.read_text()
        assert ref_user_file not in manager.index_file.read_text()

    finally:
        if os.path.exists(temp_memory_dir):
            shutil.rmtree(temp_memory_dir)
