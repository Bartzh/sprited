from pydantic import BaseModel, Field
from typing import Optional, Type
from datetime import date

from sprited.times import SpriteTimeSettings, Times, TimestampUs
from sprited.store.base import StoreField, StoreModel
from sprited.constants import PROJECT_NAME


class SpritedSettings(StoreModel):
    _namespace = (PROJECT_NAME,)
    _title = "sprited设置"
    _description = "sprited内置的一些设置"
    _is_config = True
    role_prompt: str = StoreField(default="你是一个对陌生人也抱有基本尊重的普通人。你与他人是通过一个无聊天记录（阅后即焚）的即时通讯软件远程交流的。", title="角色提示词")
    role_description: str = StoreField(default="应该是一个有用的助手吧。", title="展示用角色描述", description="直接向用户显示的一段文本，描述这个角色")
    time_settings: SpriteTimeSettings = StoreField(default_factory=SpriteTimeSettings, title="时间设置")
