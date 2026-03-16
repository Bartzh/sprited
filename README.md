# sprited

这是一个基于[langchain](https://github.com/langchain-ai/langchain)&[langgraph](https://github.com/langchain-ai/langgraph)（类似其中的`create_agent`+ middleware）的功能几乎完全由插件驱动的agent系统，实现了：
- 创建自定义模型实现持久化
- 调度计划任务
- 消息元数据
- 事件总线
- 多个hooks，提供对整个流程尽可能强的控制
- 配置
- 对agent的时间的定义，分为真实世界时间、agent世界时间、agent主观tick（可以用来实现如异世界、时间旅行等）
- 运行时可修改工具schema（或直接隐藏）

在这个系统中，agent被称为sprite。

这是[become-human](https://github.com/Bartzh/become-human)的底座（become-human现在是在此之上的一些插件），其中会有更详细的说明。

## 使用

需要安装uv

简单来说，克隆仓库，运行`uv sync`安装依赖，然后运行`uv run main.py或app.py`（非常简单的两个示例，你可以做你自己的）

复制`.env.example`为`.env`并进行一些设置

检查config以了解并使用配置
