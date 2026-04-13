# Plugin 插件

Plugin 是 Sprited 的核心扩展机制，通过 Hooks 系统与 sprite 的生命周期和执行流程交互。

## 基础结构

### 定义插件

```python
from sprited.plugin import BasePlugin, PluginPriority, PluginPrompts, PluginPrompt

class MyPlugin(BasePlugin):
    name = 'my_plugin'           # 唯一名称（必须）
    version = Version('1.0.0')    # 版本号（必须）
    priority = PluginPriority()   # 优先级（可选）
    prompts = PluginPrompts()     # 提示词（可选）

    async def on_manager_init(self):
        """Manager 初始化时调用"""
        pass

    async def on_sprite_init(self, sprite_id: str):
        """每个 sprite 初始化时调用"""
        pass
```

### 必需属性

| 属性     | 类型  | 说明     |
| ------ | --- | ------ |
| `name` | str | 插件唯一名称 |

### 可选属性

| 属性             | 类型                                            | 说明     |
| -------------- | --------------------------------------------- | ------ |
| `version`      | Version                                       | 版本号    |
| `priority`     | PluginPriority                                | 执行优先级  |
| `dependencies` | list\[PluginRelation]                         | 依赖插件   |
| `conflicts`    | list\[PluginRelation]                         | 冲突插件   |
| `tools`        | list\[Union\[Callable, BaseTool, SpriteTool]] | 提供的工具  |
| `config`       | type\[StoreModel]                             | 配置存储模型 |
| `data`         | type\[StoreModel]                             | 数据存储模型 |
| `prompts`      | PluginPrompts                                 | 提示词    |

## 生命周期 Hooks

### Manager 级别

```python
class MyPlugin(BasePlugin):
    async def on_manager_init(self):
        """Manager 初始化时调用一次"""
        pass

    async def on_manager_close(self):
        """Manager 关闭时调用一次"""
        pass
```

### Sprite 级别

```python
class MyPlugin(BasePlugin):
    async def on_sprite_init(self, sprite_id: str):
        """每个 sprite 创建时调用"""
        pass

    async def on_sprite_close(self, sprite_id: str):
        """每个 sprite 关闭时调用"""
        pass

    async def on_sprite_reset(self, sprite_id: str):
        """Sprite 重置时调用（关闭后、删除前）"""
        pass
```

## 执行流程 Hooks

### 1. before\_call\_sprite

在调用 sprite 之前执行，可取消或修改请求：

```python
from sprited.plugin import BeforeCallSpriteControl

class MyPlugin(BasePlugin):
    async def before_call_sprite(
        self,
        request: CallSpriteRequest,
        info: BeforeCallSpriteInfo,
    ) -> Optional[BeforeCallSpriteControl]:
        # 可选：取消调用
        # 可选：修改双重短信策略
        return BeforeCallSpriteControl(cancel=True)
```

### 2. on\_call\_sprite

在进入 ReAct 循环前执行，可修改输入消息：

```python
from sprited.plugin import OnCallSpriteControl

class MyPlugin(BasePlugin):
    async def on_call_sprite(
        self,
        request: CallSpriteRequest,
        info: OnCallSpriteInfo,
    ) -> Optional[OnCallSpriteControl]:
        # 可选：添加消息补丁
        return OnCallSpriteControl(
            input_messages_patch=[HumanMessage(content="追加消息")]
        )
```

### 3. after\_call\_sprite

在 sprite 执行完成后执行：

```python
class MyPlugin(BasePlugin):
    async def after_call_sprite(
        self,
        request: CallSpriteRequest,
        info: AfterCallSpriteInfo,
    ) -> None:
        if info.cancelled:
            print(f"调用被取消: {info.cancelled_reason}")
```

### 4. 模型调用 Hooks

```python
class MyPlugin(BasePlugin):
    async def before_call_model(
        self,
        request: CallSpriteRequest,
        info: BeforeCallModelInfo,
    ) -> None:
        """模型调用前"""
        pass

    async def after_call_model(
        self,
        request: CallSpriteRequest,
        info: AfterCallModelInfo,
    ) -> Optional[AfterCallModelControl]:
        """模型调用后，可修改响应"""
        return AfterCallModelControl(response=modified_response)
```

### 5. 工具调用 Hooks

```python
class MyPlugin(BasePlugin):
    async def after_call_tools(
        self,
        request: CallSpriteRequest,
        info: AfterCallToolsInfo,
    ) -> Optional[AfterCallToolsControl]:
        """工具调用后，可修改结果或退出循环"""
        return AfterCallToolsControl(
            tool_responses_patch=[ToolMessage(...)]
        )
```

### 6. 消息更新 Hooks

```python
class MyPlugin(BasePlugin):
    async def on_update_messages(
        self,
        sprite_id: str,
        info: OnUpdateMessagesInfo,
    ) -> Optional[OnUpdateMessagesControl]:
        """当某一方调用sprite_manager.update_messages更新消息时调用"""
        return OnUpdateMessagesControl(
            messages_patch=[...]
        )
```

## 插件优先级

```python
from sprited.plugin import PluginPriority

class EarlyPlugin(BasePlugin):
    priority = PluginPriority(phase='earliest')  # 最先执行

class NormalPlugin(BasePlugin):
    priority = PluginPriority()  # 默认，可省略

class LatePlugin(BasePlugin):
    priority = PluginPriority(phase='late')  # 靠后执行
```

### Phase 映射

| Phase      | 值    |
| ---------- | ---- |
| `earliest` | -600 |
| `early`    | -300 |
| `normal`   | 0    |
| `late`     | +300 |
| `last`     | +600 |

## 插件依赖/冲突

```python
from sprited.plugin import PluginRelation

class MyPlugin(BasePlugin):
    dependencies = [
        PluginRelation(name='other_plugin', specifiers='>=1.0.0'),
    ]
    conflicts = [
        PluginRelation(name='conflicting_plugin', specifiers='>=2.0.0'),
    ]
```

## 插件提示词

```python
from sprited.plugin import PluginPrompts, PluginPrompt

class MyPlugin(BasePlugin):
    prompts = PluginPrompts(
        core=PluginPrompt(
            title="核心功能",
            content="你是一个有用的助手..."
        ),
        role=PluginPrompt(
            title="角色设定",
            content="你扮演一个医生..."
        )
    )
    
    # 如果要动态修改，推荐使用这个钩子
    async def before_call_model(self, request: CallSpriteRequest, info: BeforeCallModelInfo, /) -> None:
        """模型调用前"""
        self.prompts = PluginPrompts(
            ...
        )
```

## 简单示例，具体可参考内置的一些插件

```python
from sprited.plugin import (
    BasePlugin, PluginPriority, PluginPrompts, PluginPrompt,
    BeforeCallSpriteControl, AfterCallModelControl
)
from sprited.store.base import StoreModel, StoreField
from sprited.times import Times
from packaging.version import Version

NAME = 'my_plugin'

class MyConfig(StoreModel):
    _namespace = NAME
    enabled: bool = StoreField(default=True)

class MyPlugin(BasePlugin):
    name = NAME
    version = Version('1.0.0')
    config = MyConfig
    priority = PluginPriority(phase='normal')
    prompts = PluginPrompts(
        core=PluginPrompt(
            title="我的插件",
            content="提供额外的搜索功能..."
        )
    )

    async def on_sprite_init(self, sprite_id: str):
        config = store_manager.get_model(sprite_id, MyConfig)
        if config.enabled:
            print(f"MyPlugin 已为 {sprite_id} 启用")

    async def after_call_model(
        self,
        request,
        info: AfterCallModelInfo,
    ) -> Optional[AfterCallModelControl]:
        # 检查或修改模型响应
        pass
```

## 加载插件

```python
from sprited import sprite_manager

sprite_manager.run_standalone([
    InstructionPlugin,
    ReminderPlugin,
    MyPlugin,  # 添加你的插件
])
```

