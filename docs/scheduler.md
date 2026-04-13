# Scheduler 模块

Scheduler 模块提供强大的计划任务调度功能，支持基于真实时间、sprite 世界时间或主观 tick 的定时任务。

## Schedule 类

### 创建定时任务

```python
from sprited.scheduler import Schedule

async def my_job(schedule: Schedule):
    print("任务执行！")

schedule = Schedule(
    sprite_id="sprite_1",
    schedule_provider="my_plugin",
    schedule_type="reminder",
    job=my_job,
    job_args=(),
    job_kwargs={},
    interval_fixed=3600,  # 固定间隔（秒）
    max_triggers=10,      # 最大触发次数，0表示无限
    time_reference='real_world',  # 时间参考类型
)
await schedule.add_to_db()
```

### 时间参考类型

| 类型 | 说明 |
|------|------|
| `real_world` | 真实世界时间 |
| `sprite_world` | sprite 世界时间（受时间膨胀影响） |
| `sprite_subjective` | sprite 主观 tick（整数） |

### 触发规则

**固定间隔触发：**

```python
schedule = Schedule(
    ...
    interval_fixed=7200,  # 每2小时触发
    time_reference='sprite_world',
)
```

**随机间隔触发：**

```python
schedule = Schedule(
    ...
    interval_random_min=3600,   # 最小1小时
    interval_random_max=7200,    # 最大2小时
)
```

**定时触发：**

```python
from datetime import time

schedule = Schedule(
    ...
    scheduled_time_of_day=3600 * 10,  # 每天10:00:00触发（秒数）
    scheduled_every_day=True,         # 每天触发
    # 或者指定周几
    scheduled_weekdays={1, 3, 5},      # 周一、三、五
    scheduled_monthdays={1, 15},       # 每月1号、15号
)
```

### 完整示例：提醒事项

```python
from sprited.scheduler import Schedule
from sprited.times import TimestampUs

async def reminder_job(schedule: Schedule, sprite_id: str, title: str):
    # 发送提醒
    ...

schedule = Schedule(
    sprite_id=sprite_id,
    schedule_provider="reminder",
    schedule_type="reminder",
    job=reminder_job,
    job_kwargs={
        'sprite_id': sprite_id,
        'title': title,
    },
    scheduled_time_of_day=9 * 3600,  # 每天9点
    scheduled_every_day=True,
    time_reference='sprite_world',
    max_triggers=0,  # 无限触发
)
await schedule.add_to_db()
```

## 查询任务

```python
from sprited.scheduler import get_schedules

# 查询某个 sprite 的所有任务
schedules = await get_schedules([
    Schedule.Condition(key='sprite_id', value=sprite_id),
])

# 条件查询
schedules = await get_schedules([
    Schedule.Condition(key='schedule_provider', value='reminder'),
    Schedule.Condition(key='time_reference', op='!=', value='real_world'),
])

# 排序
schedules = await get_schedules(
    order_by='trigger_time',
    order='ASC',
    limit=10,
)
```

### Condition 操作符

| 操作符 | 说明 |
|--------|------|
| `=` | 等于 |
| `!=` | 不等于 |
| `<`, `<=`, `>`, `>=` | 比较 |
| `IN`, `NOT IN` | 在集合中 |
| `LIKE`, `NOT LIKE` | 模糊匹配 |

## 管理任务

```python
# 更新任务
new_values = {'max_triggers': 100}
await schedule.update_to_db(new_values)

# 删除任务
await schedule.delete_from_db()

# 格式化任务信息
print(schedule.format_schedule(
    prefix='计划',
    include_id=True,
    include_type=True
))
```

## tick_schedules

系统通过 `tick_schedules` 函数驱动所有定时任务：

```python
from sprited.scheduler import tick_schedules

# 在主循环中调用
await tick_schedules()
```

## Schedule 生命周期

1. **创建** → 设置 `trigger_time` 和触发规则
2. **添加** → 调用 `await schedule.add_to_db()`
3. **触发** → `tick_schedules` 检测到满足条件
4. **更新** → 计算并更新下次触发时间
5. **删除** → 满足删除条件（如一次性任务、超次）