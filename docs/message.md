# Message 模块

Message 模块管理 sprite 的消息系统，包括消息格式化和元数据管理。

## 消息类型

Sprited 使用 LangChain 的消息类型：

```python
from langchain_core.messages import (
    HumanMessage,   # 用户消息
    AIMessage,      # AI 消息
    ToolMessage,    # 工具调用结果
)
```

## 消息元数据

### SpritedMsgMeta

基础消息元数据，每条消息都会自动添加，包含创建时间和消息类型：

```python
from sprited.message import SpritedMsgMeta

meta = SpritedMsgMeta(
    creation_times=current_times,
    message_type='custom:type',
)
```

### BaseMsgMeta

创建自定义消息元数据类：

```python
from sprited.message import BaseMsgMeta
from pydantic import Field

class MyMsgMeta(BaseMsgMeta):
    KEY = 'my_plugin'  # 必须定义唯一 KEY

    custom_field: str = Field(default="default")
    created_at: str = Field(default_factory=lambda: "timestamp")
```

### DictMsgMeta

`DictMsgMeta` 用于在无法引用目标元数据类时，忽略类型检查直接使用，这在需要使用其他插件的元数据类时非常有用。

```python
from sprited.message import DictMsgMeta

DictMsgMeta(
    KEY='my_plugin',
    value={
        'custom_field': 'value',
        'created_at': 'timestamp',
    }
)
# 拥有与 BaseMsgMeta 相同的方法，如 parse, set_to, fill_to, update_to 等
```


### 使用元数据

```python
# 解析
meta = MyMsgMeta.parse(message)

# 解析的异常处理（不存在时）
try:
    meta = MyMsgMeta.parse(message)
except KeyError:
    meta = MyMsgMeta()

# 解析但拥有默认值
meta = MyMsgMeta().parse_with_default(message)

# 设置到消息
meta.set_to(message)

# 填充（合并，不覆盖已存在值）
meta.fill_to(message)

# 更新（合并，覆盖已存在值）
meta.update_to(message)
```

## 工具函数

### format_messages

将消息列表格式化为可读字符串：

```python
from sprited.message import format_messages, HumanMessage, AIMessage

messages = [human_msg, ai_msg]
formatted = format_messages(messages)
```

### construct_system_message

创建系统消息：

```python
from sprited.message import construct_system_message
from sprited.times import Times

system_msg = construct_system_message(
    content="这是一条系统消息",
    times=current_times,
    message_type='sprited:system',
)
```

## 添加工具消息

### InitalAIMessage

用于创建包含工具调用的 AI 消息：

```python
from sprited.message import InitalAIMessage, InitalToolCall

ai_msg = InitalAIMessage(
    content="我来帮你搜索",
    tool_calls=[
        InitalToolCall(
            name="web_search",
            args={"query": "天气"},
        )
    ]
)

# 构建消息
messages = ai_msg.construct_messages(current_times)
# 返回 [AIMessage, ToolMessage]
```

