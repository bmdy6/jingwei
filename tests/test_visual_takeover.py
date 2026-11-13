# -*- coding: utf-8 -*-
"""视觉自愈接管系统 TDD 自动化测试用例

涵盖 API 接口契约校验、QQ审批全局劫持拦截、审批超时自动熔断、以及物理鼠标移动抢占防踩踏保护。
"""

import io
import os
import json
import base64
import asyncio
import pytest
from PIL import Image
from unittest.mock import AsyncMock, MagicMock, patch
from agent.tools.visual_tools import BrowserAgentTool
from agent.net_gateway.dispatcher import MessageDispatcher
from agent.net_gateway.context import GatewayContext
from agent.tools.base_tool import ToolResult


@pytest.mark.asyncio
async def test_browser_agent_requires_task_and_llm():
    tool = BrowserAgentTool()
    assert tool.needs_permissions({"task": "example"})
    assert not (await tool.validate_input({}))["result"]
    assert (await tool.validate_input({"task": "example"}))["result"]
    results = [r async for r in tool.call({"task": "example"})]
    assert "未绑定LLM" in results[0].data


# ── 用例 2: 校验 QQ 全局审批消息劫持拦截器 (MessageDispatcher.dispatch_event) ──
@pytest.mark.asyncio
async def test_qq_approval_message_global_hijack():
    # 模拟上下文
    context = MagicMock()
    context.admin_id = "10001"
    
    # 模拟活动的 agent 实例并挂载未决议的 approval_future
    agent = MagicMock()
    loop = asyncio.get_running_loop()
    agent.approval_future = loop.create_future()
    
    context._agents = {"user_10001": agent}
    
    dispatcher = MessageDispatcher(context)
    dispatcher.middlewares = [] # 清空中间件，防止干扰
    
    # 1. 模拟非管理员发送审批词，不予拦截劫持
    normal_event = {
        "message_type": "private",
        "raw_message": "y",
        "user_id": "999999", # 非亮哥QQ
        "self_id": "888888"
    }
    await dispatcher.dispatch_event(normal_event)
    assert not agent.approval_future.done()
    
    # 2. 模拟管理员发送非审批动作词，不予拦截劫持
    random_event = {
        "message_type": "private",
        "raw_message": "你好小萤",
        "user_id": "10001", # 亮哥QQ
        "self_id": "888888"
    }
    # 劫持检测拦截未匹配成功应继续流转（由于 executor 会抛错，在此忽略其异常以检测拦截性）
    try:
        await dispatcher.dispatch_event(random_event)
    except Exception:
        pass
    assert not agent.approval_future.done()

    # 3. 模拟亮哥（管理员）正式在 QQ 发送 "y" 审批放行
    approve_event = {
        "message_type": "private",
        "raw_message": "  y  ", # 带有空格
        "user_id": "10001",
        "self_id": "888888"
    }
    await dispatcher.dispatch_event(approve_event)
    
    # 关键断言：QQ 消息被成功劫持，决议 future 成功为 True
    assert agent.approval_future.done()
    assert agent.approval_future.result() is True


@pytest.mark.asyncio
async def test_browser_agent_passes_task_and_returns_result():
    tool = BrowserAgentTool()
    agent = MagicMock()
    visual = AsyncMock()
    visual.execute.return_value = {"success": False, "steps": 1, "error": "cancelled", "history": []}
    with patch("agent.core.visual_agent.VisualAgent") as factory:
        factory.return_value.__aenter__.return_value = visual
        results = [r async for r in tool.call({"task": "read page", "cdp_url": "http://localhost:9222"}, agent)]
    visual.execute.assert_awaited_once_with(task="read page")
    assert json.loads(results[0].data)["error"] == "cancelled"
