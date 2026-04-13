# Times 模块

Times 模块处理 sprite 的多维度时间系统，包括真实世界时间、sprite 世界时间和主观 tick。

## TimestampUs

微秒级时间戳，解决 timestamp 的范围和精度问题，支持 1\~9999 年：

```python
from sprited.times import TimestampUs

# 从 datetime 创建
ts = TimestampUs(datetime(2024, 1, 1, 12, 0, 0))

# 从微秒创建
ts = TimestampUs(1704067200_000_000)

# 从字符串创建
ts = TimestampUs("2024-01-01 12:00:00")

# 获取当前时间
ts = TimestampUs.now()

# 转换为 datetime
dt = ts.to_datetime()
```

## SpriteTimeSettings

定义 sprite 的时间行为：

```python
from sprited.times import SpriteTimeSettings, SerializableTimeZone

settings = SpriteTimeSettings(
    # 世界时间锚点
    world_real_anchor=TimestampUs(0),
    world_sprite_anchor=TimestampUs(0),
    world_scale=1,  # 时间膨胀倍率

    # 主观时间锚点
    subjective_real_anchor=TimestampUs.now(),
    subjective_sprite_anchor=0,
    subjective_scale=1,  # 设为0则放弃时间驱动

    # 时区
    time_zone=SerializableTimeZone.from_local(),
)
```

### 时间膨胀

时间可以加速、静止甚至倒退：

```python
# 设置 10 倍速（每真实 1 秒 = sprite 世界 10 秒）
new_settings = settings.set_scale_from_now(10, 'world')

# 时间倒退 1 小时
new_settings = settings.add_offset_from_now(-3600 * 1000000, 'world')
```

## Times

包含所有时间信息的不可变结构：

```python
from sprited.times import Times

# 创建 Times 实例
times = Times.from_time_settings(time_settings)

# 访问各种时间
real_time = times.real_world_datetime      # 真实世界时间
real_time_us = times.real_world_timestampus  # 真实世界时间（微秒）
sprite_time = times.sprite_world_datetime  # Sprite 世界时间
sprite_time_us = times.sprite_world_timestampus  # Sprite 世界时间（微秒）
subjective = times.sprite_subjective_tick  # 主观 tick（整数）
real_world_time_zone = times.real_world_time_zone  # 真实世界时区
sprite_time_settings = times.sprite_time_settings  # Sprite 时间设置
```

## 工具函数

### 时间格式化

```python
from sprited.times import format_time, format_duration

# 格式化时间点
formatted = format_time(datetime.now())
# "2024-01-01 12:00:00 Week01 Monday"

# 格式化时长
duration_str = format_duration(3600000000)  # 微秒
# "1小时"

duration_str = format_duration(timedelta(days=1))
# "1天"
```

### 解析时长字符串

```python
from sprited.times import parse_timedelta

delta = parse_timedelta("2h30m")      # 2小时30分钟
delta = parse_timedelta("1d2h3m4s")   # 1天2小时3分钟4秒
delta = parse_timedelta("1w")         # 1周
```

### 时区

```python
from sprited.times import SerializableTimeZone

# 直接创建
tz = SerializableTimeZone(name="Asia/Shanghai")
tz = SerializableTimeZone(name="custom", offset=28800) # 单位为秒

# 从时区创建
tz = SerializableTimeZone.from_timezone(get_localzone())

# 从 datetime 获取
tz = SerializableTimeZone.from_datetime(datetime.now())

# 获取本地时区
tz = SerializableTimeZone.from_local()
```

## 使用示例

### 获取指定sprite当前时间

```python
from sprited.store.manager import store_manager
from sprited.times import Times

time_settings = store_manager.get_settings(sprite_id).time_settings
current_times = Times.from_time_settings(time_settings)
# 或
current_times = Times.from_sprite_id(sprite_id)


print(f"真实时间: {current_times.real_world_datetime}")
print(f"Sprite时间: {current_times.sprite_world_datetime}")
print(f"主观Tick: {current_times.sprite_subjective_tick}")
```

### 创建带时间戳的消息

```python
from sprited.times import format_time

time_settings = store_manager.get_settings(sprite_id).time_settings
current_times = Times.from_time_settings(time_settings)

message = f"当前 sprite 世界时间是：{format_time(current_times.sprite_world_datetime)}"
```

