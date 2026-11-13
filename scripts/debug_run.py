import asyncio
import os
import sys

sys.path.insert(0, os.getcwd())

from main import build_agent

async def main():
    agent = build_agent("user_10001")
    print("--- 正在以真实会话 user_10001 初始化小肖 Agent ---")
    
    user_input = "好，以后你叫精卫"
    print(f"亮哥发送: {user_input}")
    
    print("--- 开始运行小肖推理流 ---")
    async for evt in agent.run(user_input, stream=True):
        print(f"\n[EVENT] {evt}")
        
        # 模拟真实网关自动审批行为
        if evt["type"] == "permission_request":
            print(f"\n⚡ [模拟网关操作]: 检测到敏感权限请求 {evt.get('tool_name')}，正在调用 approve_permission()...")
            agent.approve_permission()

    print("\n✅ 测试运行成功结束！没有发生死锁挂起！")

if __name__ == "__main__":
    asyncio.run(main())
