from typing import Final, Self, Any

from pydantic_core import core_schema

# ？！难难！？
PROJECT_NAME: Final = 'sprited'

class UnsetType:
    """表示未设置值的类型，请使用全局单例UNSET，不要另外再实例化此类"""
    __slots__ = ()

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "<UNSET>"

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self) -> Self:
        return self

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any):
        return core_schema.is_instance_schema(cls
            #serialization=core_schema.plain_serializer_function_ser_schema(lambda x: None)
        )

    def is_unset(self, value: Any) -> bool:
        return value is self

UNSET: Final = UnsetType()
