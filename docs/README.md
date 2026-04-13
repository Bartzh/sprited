# Sprited 文档

Sprited 是一个基于 LangChain/LangGraph 的插件驱动型 Agent 系统，其中 Agent 被称为 "sprite"。

## 核心特性

- 对double-texting的处理，包括merge、interrupt、enqueue、reject四种模式
- 自定义模型的持久化存储
- 计划任务调度
- 消息元数据管理
- 事件总线
- 多层级 Hooks，控制整个流程
- 灵活的配置系统
- 多维度时间定义（真实世界时间、Agent 世界时间、Agent 主观 tick）
- 运行时可修改工具 Schema

## 快速开始

```python
from sprited.plugins import *
from sprited import sprite_manager

if __name__ == "__main__":
    sprite_manager.run_standalone([
        InstructionPlugin,
        ReminderPlugin,
        TimeIncrementerPlugin,
        NotePlugin,
        PlanningPlugin,
        SimpleCLI,
    ])
```

或手动管理事件循环

```python
import asyncio
from sprited.plugins import *
from sprited import sprite_manager

async def main():
    await sprite_manager.init_manager([
        InstructionPlugin,
        ReminderPlugin,
        TimeIncrementerPlugin,
        NotePlugin,
        PlanningPlugin,
        # SimpleCLI,
    ])
    # 你自己的程序
    ...

if __name__ == "__main__":
    asyncio.run(main())
```


## 文档目录

- [Manager](manager.md) - SpriteManager 管理器
- [Store 模块](store.md) - 数据持久化存储
- [Scheduler 模块](scheduler.md) - 计划任务调度
- [Times 模块](times.md) - 时间管理
- [Message 模块](message.md) - 消息与元数据
- [Event 模块](event.md) - 事件总线
- [Tool 模块](tool.md) - 工具定义
- [Plugin 插件](plugin.md) - 如何编写插件
