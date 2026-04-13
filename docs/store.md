# Store 模块

Store 模块提供基于 SQLite 的持久化存储，支持为每个 sprite 独立管理配置和数据。

## 核心概念

### StoreModel

`StoreModel` 是存储模型的基础类，类似于 Pydantic 的 `BaseModel`，但数据会自动持久化到数据库。

```python
from sprited.store.base import StoreModel, StoreField

class MyConfig(StoreModel):
    _namespace = ('my_plugin',)  # 存储路径
    _is_config = True  # True 表示配置（会出现在配置文件），False 表示数据

    name: str = StoreField(default="unnamed", title="名称")
    count: int = StoreField(default=0, title="计数")
```

### StoreField

`StoreField` 用于定义存储字段的属性：

```python
class MyModel(StoreModel):
    _namespace = ('my_plugin',)

    name: str = StoreField(
        default="default",
        title="显示名称",
        description="这是字段描述",
    )
    counter: int = StoreField(
        default_factory=lambda: 0,  # 默认值工厂
        title="计数器",
    )
    frozen_field: str = StoreField(
        default="locked",
        frozen=True,  # 冻结后不可修改
    )
```

### StoreField 参数

| 参数                | 类型       | 说明         |
| ----------------- | -------- | ---------- |
| `default`         | Any      | 默认值        |
| `default_factory` | Callable | 默认值工厂函数    |
| `title`           | str      | 显示名称       |
| `description`     | str      | 字段描述       |
| `reducer`         | Callable | 值变更时的合并函数  |
| `frozen`          | bool     | 是否冻结（不可修改） |

### reducer 函数

`reducer` 用于定义如何合并新值和当前值：

```python
def append_reducer(current: list, new_value: Any, sprite_id: str = None) -> list:
    if isinstance(current, list):
        return current + [new_value]
    return [new_value]

class MyModel(StoreModel):
    _namespace = ('my_plugin',)
    items: list = StoreField(default_factory=list, reducer=append_reducer)
```

## 使用示例

### 作为插件的config或data

```python
from sprited.store.base import StoreModel, StoreField
from sprited.plugin import *

class MyConfig(StoreModel):
    # 在作为插件的config时，_namespace和_is_config可以省略，默认值分别为('my_plugin',)和True
    # _namespace = ('my_plugin',)
    # _is_config = True

    name: Optional[str] = StoreField(default=None, title="名称")
    count: int = StoreField(default=0, title="计数")

class MyData(StoreModel):
    # 在作为插件的data时，_namespace和_is_config可以省略，默认值分别为('my_plugin',)和False
    # _namespace = ('my_plugin',)
    # _is_config = False

    name: Optional[str] = StoreField(default=None, title="名称")
    count: int = StoreField(default=0, title="计数")

class MyPlugin(BasePlugin):
    name = 'my_plugin'
    config = MyConfig
    data = MyData

    # 自动注册模型，无需手动操作
```

### 手动注册模型

```python
from sprited.store.manager import store_manager

# 在 sprite 初始化时注册
store_manager.register_model(MyConfig)
```

### 获取和修改数据

```python
# 获取模型实例
config = store_manager.get_model(sprite_id, MyConfig)

# 读取字段（自动从数据库加载）
print(config.name)

# 修改字段（自动持久化）
config.name = "new name"
config.counter += 1
```

### 从数据库加载

```python
# 异步从 store 加载
model = await MyModel.from_store(sprite_id)

# 从全局配置创建（冻结实例）
model = MyModel.from_global_config(plugin_name)
```

## 内置模型

Sprited 提供两个内置模型：

### SpritedSettings

存储 sprite 的基本设置：

```python
class SpritedSettings(StoreModel):
    _namespace = ('sprited',)
    _is_config = True

    role_prompt: str = StoreField(default="...")
    role_description: str = StoreField(default="...")
    time_settings: SpriteTimeSettings = StoreField(...)
```

### SpritedStates

存储 sprite 的运行时状态：

```python
class SpritedStates(StoreModel):
    _namespace = ('sprited',)

    born_at: TimestampUs = StoreField(default_factory=TimestampUs.now, frozen=True)
    last_updated_times: Times = StoreField(default_factory=Times.from_time_settings)
```

## 存储路径

数据按以下路径结构存储：

```
sprites/
└── {sprite_id}/
    ├── configs/     # _is_config=True 的数据
    │   └── {namespace}/
    │       └── {field_name}/
    └── datas/       # _is_config=False 的数据
        └── {namespace}/
            └── {field_name}/
```

## 异步操作

Store 模块使用队列机制实现异步写入：

```python
from sprited.store.base import store_setup, store_queue

# 初始化存储
await store_setup()

# 队列会自动处理写入
config.name = "new name"  # 自动加入队列异步写入
```

