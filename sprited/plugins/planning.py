from typing import Optional, Annotated
from langchain.tools import tool, ToolRuntime
from sprited.types.manager import CallSpriteRequest
from sprited.store.base import StoreModel, StoreField
from sprited.store.manager import store_manager
from sprited.plugin import *
from sprited.message import SpritedMsgMetaOptionalTimes

NAME = "planning"


class PlanningData(StoreModel):
    steps: list[tuple[str, bool]] = StoreField(default_factory=list)

@tool
async def add_steps(runtime: ToolRuntime[CallSpriteRequest], steps: Annotated[list[str], '计划步骤描述列表，按执行顺序排序']) -> str:
    """添加计划步骤"""
    if not steps:
        raise ValueError("计划步骤不能为空！")
    elif any(not step.strip() for step in steps):
        raise ValueError("计划步骤不能包含空字符串！")
    data = store_manager.get_model(runtime.context.sprite_id, PlanningData)
    data_steps = data.steps.copy()
    data_steps.extend([(step, False) for step in steps])
    data.steps = data_steps
    return f"添加计划步骤成功"

@tool(response_format='content_and_artifact')
async def finish_step(runtime: ToolRuntime[CallSpriteRequest], index: Annotated[int, '计划步骤索引']) -> str:
    """「纯执行工具」将计划步骤标记为已完成"""
    data = store_manager.get_model(runtime.context.sprite_id, PlanningData)
    if index < 0 or index >= len(data.steps):
        raise ValueError(f"计划步骤索引 {index} 无效！")
    data_steps = data.steps.copy()
    data_steps[index] = (data_steps[index][0], True)
    data.steps = data_steps
    return f"已将计划步骤 {index+1} 标记为已完成", SpritedMsgMetaOptionalTimes(is_action_only_tool=True)


class PlanningPlugin(BasePlugin):
    name = NAME
    data = PlanningData
    tools = [add_steps, finish_step]

    async def before_call_model(self, request: CallSpriteRequest, info: BeforeCallModelInfo, /) -> None:
        data = store_manager.get_model(request.sprite_id, PlanningData)
        if not data.steps:
            plan = '无已计划步骤'
        else:
            plan = '\n'.join(f'[{"✓" if done else " "}] {i+1}. {step}' for i, (step, done) in enumerate(data.steps))

        # 构建完整的提示信息，包括功能说明、工具说明和执行规则
        full_content = f"""此功能用于遇到的长任务拆分或细化，使复杂任务能够被分解为多个可执行的小步骤，并按顺序逐步完成。
这只是为了方便你自己进行思考，以及在所有步骤被标记为完成前阻止系统退出ReAct循环，除此以外没有其他任何作用。
如果你觉得当前任务足够简单两下就能搞定，那么也自然不用把简单事情复杂化，无需使用此功能。

### 如何使用？
通过两个简单的工具来添加和完成计划步骤。
- `add_steps`: 添加新的计划步骤，参数为步骤描述列表
- `finish_step`: 将指定索引的步骤标记为完成状态（索引会在下面展示的每条步骤前注明）

### 执行规则：
- 在仍有未完成步骤时，系统将持续循环执行，不会结束响应
- 只有当使用`finish_step`工具将所有计划步骤都标记为完成后，此时系统才能够退出ReAct循环。

### 当前所有计划步骤：
{plan}"""
        self.prompts = PluginPrompts(
            secondary=PluginPrompt(
                title='计划执行功能',
                content=full_content,
            )
        )

    async def after_call_tools(self, request: CallSpriteRequest, info: AfterCallToolsInfo, /) -> Optional[AfterCallToolsControl]:
        data = store_manager.get_model(request.sprite_id, PlanningData)
        all_done = all(done for _, done in data.steps)
        if not all_done:
            return AfterCallToolsControl(
                exit_loop=False,
            )
        elif data.steps:
            data.steps = []
