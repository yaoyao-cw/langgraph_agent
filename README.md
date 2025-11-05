# LangGraph Agent

本项目提供一个可扩展的 LangGraph 测试用例生成代理，已经根据业务建议完成模块化拆分，方便后续扩展与集成。核心目录结构如下：

```
langgraph_agent/
├── agents/         # 入口层（CLI 等）
├── config.py       # 全局配置与环境变量支持
├── graph/          # LangGraph 节点与装配逻辑
├── models/         # Pydantic 数据模型（Todo、状态等）
├── prompts/        # 系统提示词与工作流模板
├── tools/          # LangChain 工具封装（系统、Todo、测试生成）
├── utils/          # 通用工具（控制台渲染、文件路径等）
└── workflow/       # 共享上下文（Todo 看板等）
```

## 快速开始

```bash
pip install -r requirements.txt  # 安装依赖（示例）
python -m langgraph_agent.agents.cli
```

CLI 启动后会展示当前工作区路径，并允许与代理交互。

## 主要模块说明

- **agents**：提供 `run_cli` 和 `main`，负责组装 LLM、工具集并启动 LangGraph 流程。
- **config**：通过 `pydantic.BaseSettings` 提供统一配置入口，可用环境变量覆盖默认值。
- **graph**：包含 `nodes.py`（节点定义）与 `builder.py`（状态机装配）。
- **models**：定义 Todo 项、Agent 状态等结构，提供类型校验与渲染逻辑。
- **prompts**：集中存放系统提示词，包含 Todo 步骤模板与详细操作规范。
- **tools**：分离系统级工具、Todo 管理工具以及测试生成工作流相关工具。
- **utils**：提供终端渲染、文本截断、工作区路径校验等通用方法。
- **workflow**：维护 Todo 看板等跨模块共享状态。

## 环境配置

| 变量名 | 说明 |
| --- | --- |
| `LANGGRAPH_AGENT_ANTHROPIC_BASE_URL` | 自定义模型 API 基址 |
| `LANGGRAPH_AGENT_ANTHROPIC_API_KEY` | 模型调用所需的 API Key |
| `LANGGRAPH_AGENT_AGENT_MODEL` | 使用的模型名称 |

所有配置也可通过 `.env` 文件进行设置。

## 开发建议

- 如需新增工具，可在 `tools/` 目录创建模块，并在 `graph.builder.build_toolkit` 中注册。
- 如需扩展提示词，可在 `prompts/` 中维护模板，避免直接修改业务逻辑。
- 推荐为关键模块编写单元测试，保障 Todo 工作流和测试生成流程的稳定性。

欢迎根据业务需求进一步拓展模块与功能。
