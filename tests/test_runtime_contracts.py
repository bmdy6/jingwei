import asyncio
import json
import sqlite3
import sys
from unittest.mock import AsyncMock

import pytest

from agent.memory.manager import MemoryManager
from agent.tools.mcp.protocol import MCPClient, StdioTransport


@pytest.mark.asyncio
async def test_new_memory_store_can_save_and_recall(tmp_path):
    memory = MemoryManager(tmp_path / "memory")
    await memory.save("example.md", "example memory", "remember test phrase")
    assert memory.search_memories("test phrase")


class NoFtsConnection(sqlite3.Connection):
    def execute(self, sql, parameters=()):
        if "CREATE VIRTUAL TABLE" in sql.upper():
            raise sqlite3.OperationalError("no such module: fts5")
        return super().execute(sql, parameters)


def test_memory_without_fts5_can_save_and_recall(tmp_path, monkeypatch):
    original_connect = sqlite3.connect
    monkeypatch.setattr(sqlite3, "connect", lambda *a, **kw: original_connect(*a, **kw, factory=NoFtsConnection))
    memory = MemoryManager(tmp_path / "memory")
    memory.save_ki({"id": "fallback", "title": "检索测试", "category": "learn",
                    "keywords": ["检索"], "summary": "没有FTS时的检索", "content": "检索仍可运行"})
    assert memory.get_ki("fallback")["content"] == "检索仍可运行"
    assert memory.search_memories("检索")[0]["filename"] == "ki_fallback.md"


@pytest.mark.asyncio
async def test_mcp_stdio_notifications_have_no_response(tmp_path):
    server = tmp_path / "mcp fixture.py"
    server.write_text('''import sys,json
for line in sys.stdin:
    req=json.loads(line)
    if "id" not in req: continue
    method=req["method"]
    if method=="initialize": result={"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"fixture","version":"1"}}
    elif method=="tools/list": result={"tools":[{"name":"echo","inputSchema":{"type":"object"}}]}
    else: result={"content":[{"type":"text","text":req["params"]["arguments"]["text"]}]}
    print(json.dumps({"jsonrpc":"2.0","id":req["id"],"result":result}),flush=True)
''')
    transport = StdioTransport([sys.executable, str(server)])
    client = MCPClient(transport)
    try:
        await asyncio.wait_for(client.initialize(), timeout=2)
        assert (await client.list_tools())[0]["name"] == "echo"
        response = await client.call_tool("echo", {"text": "hello"})
        assert response["result"]["content"][0]["text"] == "hello"
    finally:
        await transport.close()


@pytest.mark.asyncio
async def test_learned_rules_are_injected_from_sqlite_feedback(tmp_path):
    from types import SimpleNamespace
    from agent.evolution.rules import evolve_rules
    from agent.core.prompt_builder import build_system_prompt
    memory = MemoryManager(tmp_path / "memory")
    await memory.save("feedback1", "[feedback] response preference", "回答请简短")
    await memory.save("feedback2", "[feedback] response preference", "请用短句回复")
    llm = SimpleNamespace(chat=AsyncMock(return_value={"content": '{"new_rules":["用户偏好: 简短回复"]}'}))
    agent = SimpleNamespace(memory=memory, llm=llm, _persona_cache={"name": "XL", "user_address": "用户"}, role="admin")
    assert await evolve_rules(agent) == ["用户偏好: 简短回复"]
    assert "用户偏好: 简短回复" in await build_system_prompt(agent)


@pytest.mark.asyncio
async def test_registry_runtime_registration_and_dispatch():
    from agent.tools.registry import ToolRegistry
    from agent.tools.filesystem.read import ReadFileTool
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    assert registry.get_definitions()[0]["function"]["name"] == "read_file"
    assert "Invalid input" in await registry.dispatch("read_file", {})
    registry.deregister("read_file")
    assert registry.get_definitions() == []
    assert "Unknown tool" in await registry.dispatch("read_file", {})


@pytest.mark.asyncio
async def test_react_tool_loop_stops_at_configured_limit(tmp_path, monkeypatch):
    from agent.core.agent import Agent
    from agent.tools.registry import ToolRegistry
    from agent.tools.filesystem.read import ReadFileTool
    from types import SimpleNamespace
    target = tmp_path / "readme.txt"
    target.write_text("local tool result")
    llm = SimpleNamespace(model="mock", chat=AsyncMock(return_value={
        "content": "", "tool_calls": [{"id": "r1", "type": "function", "function": {
            "name": "read_file", "arguments": json.dumps({"file_path": str(target)})}}]}))
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    agent = Agent(llm=llm, registry=registry, memory=MemoryManager(tmp_path / "memory"), max_turns=1)
    monkeypatch.setattr("agent.core.react_loop.audit_tool_call", AsyncMock())
    events = [e async for e in agent.run("read file", stream=False)]
    assert llm.chat.await_count == 1
    assert any(e["type"] == "tool_call" for e in events)
    assert any("local tool result" in str(e) for e in events if e["type"] == "tool_result")
    await agent.close()


@pytest.mark.asyncio
async def test_session_end_runs_rule_extraction(tmp_path, monkeypatch):
    from agent.core.agent import Agent
    from agent.evolution.base import on_session_end
    from types import SimpleNamespace
    llm = SimpleNamespace(model="mock", chat=AsyncMock(return_value={"content": '{"has_learnings":false}'}))
    agent = Agent(llm=llm, registry=None, memory=MemoryManager(tmp_path / "memory"))
    agent.messages = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}] * 2
    rules = AsyncMock(return_value=[])
    monkeypatch.setattr("agent.evolution.base.evolve_rules", rules)
    monkeypatch.setattr("agent.evolution.base.detect_task_pattern", AsyncMock(return_value={}))
    await on_session_end(agent)
    await asyncio.gather(*agent._active_tasks)
    rules.assert_awaited_once_with(agent)
    await agent.close()
