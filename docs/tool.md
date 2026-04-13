# Tool 模块

Tool 模块提供一种新的工具类来使得工具schema可被动态修改。

## SpriteTool

`SpriteTool` 包装 LangChain 工具，支持为不同 sprite 设置不同的 schema：

```python
from sprited.tool import SpriteTool
from langchain_core.tools import tool

@tool
def my_tool(input: str) -> str:
    """我的工具"""
    return f"处理: {input}"

sprite_tool = SpriteTool(my_tool)
```

## 运行时修改 Schema

### 为单个 sprite 设置 schema

```python
# 设置自定义 schema
custom_schema = {
    "title": "my_tool",
    "description": "自定义描述",
    "parameters": {...}
}
sprite_tool.set_schema(sprite_id, custom_schema)

# 隐藏工具（设为 None）
sprite_tool.set_schema(sprite_id, None)
```

### 获取 schema

```python
schema = sprite_tool.get_schema(sprite_id)
```

### 重置为默认

```python
sprite_tool.reset_schema(sprite_id)
```

## hide\_by\_default

创建工具时设置默认隐藏：

```python
sprite_tool = SpriteTool(
    my_tool,
    hide_by_default=True  # 默认隐藏，需要手动启用
)

# 某个 sprite 需要时启用
sprite_tool.set_schema(sprite_id, {...})
```

