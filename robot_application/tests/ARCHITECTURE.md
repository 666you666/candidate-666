# 架构设计说明

## 模块图

```mermaid
graph TD
    A[外部事件源] -->|Event| B[RobotApplication]
    B -->|Effect| C[执行器/机器人动作]
    B --> D[内部状态]
    D -->|快照| E[外部监控]
模块职责
models.py

    定义不可变数据类 Event 和 Effect。
    不包含任何业务逻辑。

application.py

    包含 RobotApplication 类，是系统的核心控制器。
    负责：

        维护所有人员状态（_persons）和交互状态（_interaction_count）。
        根据输入事件和业务规则更新状态，并生成对应的效果。
        提供状态快照（snapshot）供外部调试或监控。

    不负责：

        事件感知（如相机、传感器）。
        动作执行（如挥手、语音合成）。
        与硬件或 ROS 2 的直接交互。

状态所有权
状态	所属模块
人员在场/离开/等待计时状态	RobotApplication
对话/会议进行中标志	RobotApplication
送客超时阈值	RobotApplication

所有状态变更均在 handle_event 中原子化完成，并遵循业务规则。
未来扩展性
VIP 支持

    扩展 Event 或 PersonState，添加 is_vip 字段。
    在迎宾逻辑中根据 VIP 状态生成不同欢迎词或动作。
RAG 个性化

    将欢迎语生成抽离为独立服务，通过依赖注入传入 RobotApplication。
    handle_event 在需要输出 say 效果时调用该服务生成内容。
ROS 2 导航

    RobotApplication 保持纯业务逻辑，不引入 ROS 依赖。
    外部 ROS 节点将传感器数据转换为 Event，并接收 Effect 后转换为机器人指令。
    扩展时只需增加新的事件类型和对应的效果，不影响核心逻辑。
避免“大泥球”

    当前 RobotApplication 承担了状态机和规则引擎，但逻辑清晰（事件 → 状态迁移 → 效果）。
    当规则增多时，可进一步拆分为独立的 状态机处理器（如 GreetingHandler、FarewellHandler、
    InteractionHandler），由 RobotApplication 协调。
