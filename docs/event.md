# Event 模块

Event 模块提供事件总线系统，支持 sprite 内部的松耦合通信。

## EventBus

事件总线是发布-订阅模式的核心：

```python
from sprited.event import event_bus

# 注册事件
event_bus.register('my_event')

# 或者注册为同步事件（只支持同步订阅者）
event_bus.register('sync_event', sync_only=True)
```

## 订阅事件

### subscribe 方法

```python
async def my_handler(data: str):
    print(f"收到: {data}")

event_bus.subscribe('my_event', my_handler)
```

### 装饰器方式

```python
@event_bus.on('my_event')
def sync_handler(data: str):
    print(f"同步收到: {data}")
```

### 异步与同步

- 普通事件：支持异步处理器
- 同步事件 (`sync_only=True`)：只支持同步处理器

## 发布事件

### publish（异步）

```python
await event_bus.publish('my_event', data="hello")
```

### publish_sync（同步）

```python
event_bus.publish_sync('sync_event', data="sync hello")
```

## 取消订阅

```python
event_bus.unsubscribe('my_event', my_handler)
```

## 查询事件

```python
# 检查事件是否已注册
event_bus.is_registered('my_event')  # True/False

# 检查是否为同步事件
event_bus.is_sync_event('my_event')  # True/False

# 获取所有订阅者
subscribers = event_bus.get_subscribers('my_event')

# 检查是否有订阅者
event_bus.has_subscribers('my_event')  # True/False
```

## 使用示例

### 在 Plugin 中使用

```python
from sprited.event import event_bus

class MyPlugin(BasePlugin):

    async def on_manager_init(self):
        # 初始化时注册事件
        event_bus.register('my_event')

    @event_bus.on('my_event')
    async def on_event(self, data: str):
        print(f"收到: {data}")
```

### 参数过滤

事件发布时会自动过滤关键字参数，只传递处理器需要的关键字参数：

```python
async def handler(particular_arg, **kwargs):
    # 只会收到 particular_arg
    pass

event_bus.publish('my_event', particular_arg="value", extra_arg="ignored")
```