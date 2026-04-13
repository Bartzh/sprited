# SpriteManager

SpriteManager以及其单例`sprite_manager` 是 Sprited 的核心管理器，可以说这就是sprited的整个程序。

## 启动程序

### run\_standalone

以独立模式启动管理器，处理信号关闭：

```python
from sprited import sprite_manager

sprite_manager.run_standalone([
    InstructionPlugin,
    ReminderPlugin,
    MyPlugin,
], heartbeat_interval=5.0)
# 如果想通过代码关闭独立模式运行的事件循环
# 一般来说你只能通过其他线程做到这点
# sprite_manager.close_standalone()
```

**参数：**

- `plugins` - 要加载的插件列表
- `heartbeat_interval` - 心跳间隔（秒），默认 5.0

### init\_manager

手动初始化管理器（通常通过 `run_standalone` 自动调用）：

```python
await sprite_manager.init_manager(plugins, heartbeat_interval)
```

### close\_manager

关闭管理器（独立模式下自动调用）：

```python
await sprite_manager.close_manager()
```

停止心跳、等待所有任务完成、调用插件的 `on_manager_close`，并清理资源。

## Sprite 生命周期

### init\_sprite

初始化一个 sprite：

```python
await sprite_manager.init_sprite(sprite_id)
```

会初始化 store、创建触发事件，并调用所有插件的 `on_sprite_init`。

### close\_sprite

关闭一个 sprite：

```python
await sprite_manager.close_sprite(sprite_id)
```

会等待触发完成、调用所有插件的 `on_sprite_close`，并清理 store。

## 调用 Sprite

### call\_sprite\_for\_user

用户消息触发 sprite：

```python
await sprite_manager.call_sprite_for_user(
    sprite_id=sprite_id,
    user_input="你好",
    user_name="小明",
)
```

**参数：**

- `sprite_id` - Sprite ID
- `user_input` - 用户输入（str 或 ContentBlock 列表）
- `user_name` - 用户名称（可选）

消息会自动添加时间戳前缀。

### call\_sprite\_for\_user\_nowait

用户消息触发 sprite（非阻塞）：

```python
task = sprite_manager.call_sprite_for_user_nowait(
    sprite_id=sprite_id,
    user_input="你好",
)
```

返回 `asyncio.Task`。

### call\_sprite\_for\_system

系统消息触发 sprite：

```python
await sprite_manager.call_sprite_for_system(
    sprite_id=sprite_id,
    content="系统通知内容",
    times=current_times,  # 可选，指定时间
)
```

系统消息使用 `enqueue` 策略，不会打断正在运行的 sprite。

### call\_sprite\_for\_system\_nowait

系统消息触发 sprite（非阻塞）。

### call\_sprite

通用 sprite 调用，你可以通过调用该方法来实现自己的调用逻辑（for\_user与for\_system本质也是如此，也并不是必须使用的）：

```python
await sprite_manager.call_sprite(
    sprite_id=sprite_id,
    input_messages=[HumanMessage(content="...")],
    double_texting_strategy='merge',  # merge/interrupt/reject/enqueue
    random_wait=True,  # 随机等待 1-4 秒
)
```

**双重短信策略：**

- `merge` - 合并到当前运行的消息中
- `interrupt` - 打断当前运行
- `reject` - 丢弃新消息
- `enqueue` - 排队等待

### call\_sprite\_nowait

通用 sprite 调用（非阻塞）。

### call\_sprite\_for\_user\_with\_command

用户消息触发 sprite，支持命令处理：

```python
await sprite_manager.call_sprite_for_user_with_command(
    sprite_id=sprite_id,
    user_input="/help",  # 以 / 开头的输入被视为命令
    is_admin=True,       # 管理员可执行命令
)
```

可用命令包括 `/help`, `/get_state`, `/delete_last_messages`, `/set_role_prompt`, `/load_config`, `/messages`, `/tokens`, `/reset`, `/skip_sprite_time`, `/list_reminders` 等。

其本质是多加了一层判断，如果输入以/开头就调用sprite_manager.command_processing处理命令，你也可以做一个你自己的版本。

## Sprite 状态查询

### is\_sprite\_running

检查 sprite 是否正在运行：

```python
if sprite_manager.is_sprite_running(sprite_id):
    print("Sprite 正在运行")
```

### is\_current\_run

检查是否为当前运行：

```python
if sprite_manager.is_current_run(sprite_id, sprite_run_id):
    print("是当前运行")
```

### get\_current\_run\_id

获取当前运行的 ID：

```python
run_id = sprite_manager.get_current_run_id(sprite_id)
```

## 消息管理

### get\_messages

获取 sprite 的消息列表：

```python
messages = await sprite_manager.get_messages(sprite_id)
```

### update\_messages

更新 sprite 的消息列表：

```python
await sprite_manager.update_messages(
    sprite_id,
    messages,
    skip_hooks=False,  # 是否跳过插件 hooks
)
```

## 插件管理

### get\_plugins

获取所有已启用的插件：

```python
plugins = sprite_manager.get_plugins(sprite_id)
```

### get\_plugins\_with\_name

获取插件字典（name → plugin）：

```python
plugins = sprite_manager.get_plugins_with_name(sprite_id)
```

### get\_plugin

获取指定插件：

```python
plugin = sprite_manager.get_plugin("reminder")
```

### get\_plugin\_names

获取插件名称列表：

```python
names = sprite_manager.get_plugin_names(sprite_id)
```

### is\_plugin\_loaded

检查插件是否已加载：

```python
if sprite_manager.is_plugin_loaded("reminder"):
    print("Reminder 插件已加载")
```

### is\_plugin\_enabled

检查插件是否已启用（对于指定 sprite）：

```python
if sprite_manager.is_plugin_enabled("reminder", sprite_id):
    print("Reminder 插件已启用")
```

## 时间设置

### set\_time\_settings

设置 sprite 的时间设置：

```python
from sprited.times import SpriteTimeSettings

new_settings = SpriteTimeSettings(
    world_scale=10.0,  # 10 倍速
)
await sprite_manager.set_time_settings(sprite_id, new_settings)
```

如果设置导致世界时间倒退，会自动重新计算相关 schedule。

## 事件发布

### subscribe\_sprite\_output

订阅 sprite 输出事件：

```python
async def on_output(sprite_id, method, params, **kwargs):
    print(f"Sprite {sprite_id} 调用了 {method}")

sprite_manager.subscribe_sprite_output(on_output)
```

### on\_sprite\_output

订阅装饰器：

```python
@sprite_manager.on_sprite_output
async def on_output(sprite_id, method, params, **kwargs):
    print(f"Sprite {sprite_id} 调用了 {method}")
```

### publish\_sprite\_output

手动发布 sprite 输出事件：

```python
await sprite_manager.publish_sprite_output(
    sprite_id=sprite_id,
    method="send_message",
    params={"content": "Hello"},
)
```

### publish\_sprite\_log

发布 sprite 日志：

```python
await sprite_manager.publish_sprite_log(
    sprite_id=sprite_id,
    log="操作完成",
)
```

## 模型配置

SpriteManager 提供多个模型配置：

```python
sprite_manager.sprite_model           # 主模型
sprite_manager.sprite_model_thinking  # 带思考的模型

sprite_manager.max_model               # 最大模型
sprite_manager.max_model_thinking      # 最大模型带思考的
sprite_manager.plus_model             # Plus 模型
sprite_manager.plus_model_thinking      # Plus 模型带思考的
sprite_manager.flash_model            # 快速模型
sprite_manager.flash_model_thinking   # 快速模型带思考的
```

## 属性

| 属性                          | 说明             |
| --------------------------- | -------------- |
| `plugins_with_name`         | 所有已加载的插件字典     |
| `activated_sprite_id_datas` | 已激活的 sprite 数据 |
| `main_graph`                | 主图实例           |

