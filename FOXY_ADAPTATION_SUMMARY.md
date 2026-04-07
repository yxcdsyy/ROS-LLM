# Auromix/ROS-LLM 在 Ubuntu 20.04 + ROS2 Foxy 的适配与排障技术总结

## 1. 项目目标

本次工作的目标是：在不升级系统、不影响现有 ROS1 环境、不使用 Docker 的前提下，使 `Auromix/ROS-LLM` 先跑通“纯文本输入 -> LLM 推理 -> turtlesim 控制/反馈”的最小闭环。

开展该项目的主要原因如下：

- 需要验证自然语言驱动机器人控制的落地可行性，并形成可复用的工程基线。
- 当前机器承载 ROS1 任务，不能通过升级 Ubuntu 版本和 ROS 发行版破坏现网环境。
- 上游项目主线偏向 Humble，直接按官方 README 在 Foxy 环境执行存在明显兼容风险。

优先选择“无语音、纯文本”最小链路，是为了降低排障维度。语音链路涉及 ASR/TTS、音频设备、云端 SDK 和系统依赖，变量更多。先打通文本主链路，可以尽快证明核心闭环可运行，再分阶段恢复语音能力。

## 2. 初始环境与约束

- 宿主机：Ubuntu 20.04
- 既有环境：ROS1 仍需保留
- ROS2 运行环境：Foxy
- 项目：Auromix/ROS-LLM
- 上游实现方向：更偏 ros2-humble（通常配套 Ubuntu 22.04）

由此带来的兼容性风险主要包括：

- Python 打包依赖声明与 ROS 包依赖声明混用，导致运行期 `pkg_resources` 错误。
- 不同机器人数据模型复用同名 topic，触发 DDS 反序列化错误。
- 模型调用层仍是旧版 OpenAI SDK 风格，与 OpenAI-compatible 接口改造目标不一致。

## 3. 遇到的关键问题

### 3.1 `llm_interfaces distribution not found` 导致 `chatgpt` 节点无法启动

现象：

- `ros2 run llm_model chatgpt` 失败，报错：
- `pkg_resources.DistributionNotFound: The 'llm_interfaces' distribution was not found and is required by llm-model`

原因：

- `setup.py` 的 `install_requires` 中包含了 ROS 包依赖，`pkg_resources` 将其按 Python distribution 解析。
- `llm_interfaces` 是 ROS 接口包，不应作为 pip distribution 依赖被强制解析。

定位过程：

- 检查 `llm_model/setup.py`、`llm_input/setup.py`、`llm_output/setup.py` 的 `install_requires`。
- 检查 `egg-info/requires.txt`，确认运行脚本确实在通过 `pkg_resources` 解析这些依赖。

修复方案：

- 将 ROS 依赖从 `install_requires` 中移除，仅保留 `setuptools`。
- 把 ROS 运行依赖改为在 `package.xml` 中声明 `exec_depend`。

修复结果：

- `ros2 run llm_model chatgpt` 不再出现 `DistributionNotFound`。

### 3.2 `boto3` 缺失导致音频节点无法启动

现象：

- 语音节点启动时报缺包（如 `boto3`）。

原因：

- 音频链路依赖较重，涉及 AWS、音频库、本地设备和系统包，Foxy 环境下成本较高。

定位过程：

- 分离启动路径后确认：核心问题并非机器人动作链路，而是语音链路依赖。

修复方案：

- 本阶段不优先修复语音，新增 text-only 启动方式，先跑通主闭环。

修复结果：

- 成功绕开语音依赖阻塞，文本链路可独立验证。

### 3.3 `/turtle1/pose` topic 双类型发布导致 Fast DDS 报错

现象：

- 日志出现：
- `Deserialization of data failed -> Function deserialize_change`

原因：

- 同一 topic `/turtle1/pose` 被同时以两种类型发布：
- `geometry_msgs/msg/Pose`
- `turtlesim/msg/Pose`

定位过程：

- 通过 `ros2 topic list -t` 和 `ros2 topic info -v` 检查 topic 类型与发布者，定位到 `multi_robot.py`。

修复方案：

- 在 `llm_robot/llm_robot/multi_robot.py` 中区分 `GeometryPose` 与 `TurtlePose`。
- 新增 `get_pose_type_for_robot()`，对 turtlesim 机器人名（如 `turtle1`、`turtle2`）使用 `turtlesim/msg/Pose`，其他机器人使用 `geometry_msgs/msg/Pose`。

修复结果：

- 消除 `/turtle1/pose` 双类型冲突，DDS 反序列化错误不再出现。

### 3.4 `/llm_feedback_to_user` 初期无响应

现象：

- 文本测试早期看不到反馈。

原因：

- 根因是 `chatgpt` 节点未成功启动，导致反馈 topic 实际不可用。

定位过程：

- 先验证节点进程和 topic 发布者，再验证订阅回调日志。

修复方案：

- 优先修复 `chatgpt` 启动问题。
- 将 `chatgpt.py` 关键 pub/sub QoS 深度调整为 `10`，提升 Foxy 下稳定性。

修复结果：

- 文本输入后能在 `/llm_feedback_to_user` 获取回复。

### 3.5 Foxy 与 Humble 导向项目的兼容性问题

现象：

- 编译可通过，但运行层频繁出现依赖、配置和行为差异问题。

原因：

- 项目原始主线偏 Humble，Foxy 下 Python 依赖解析、CLI 行为和默认配置存在差异。

定位过程：

- 采用分层排障：构建层 -> 启动层 -> topic 层 -> 模型调用层。

修复方案：

- 明确区分 Python distribution 依赖与 ROS 包依赖。
- 补全 `llm_interfaces` 导出依赖声明。
- 改造模型调用层为新版 OpenAI SDK 并统一环境变量。

修复结果：

- 在 Ubuntu 20.04 + ROS2 Foxy 下实现最小闭环可运行。

## 4. 关键修复点

### 4.1 `multi_robot.py` 中 `/turtle1/pose` 冲突修复思路

- turtlesim 机器人的姿态 topic 语义应使用 `turtlesim/msg/Pose`。
- 普通 geometry 机器人应使用 `geometry_msgs/msg/Pose`。
- 同名 topic 必须保持单一类型，否则 DDS 层会产生反序列化失败。
- 通过 `GeometryPose` + `TurtlePose` 的显式区分，按机器人类型选择消息定义，根治类型冲突。

### 4.2 text-only 思路绕开语音链路问题

新增 text-only launch，仅启动：

- `turtlesim_node`
- `turtle_robot`
- `chatgpt`

不启动：

- `llm_audio_input`
- `llm_audio_output`

该策略将复杂系统拆成最小主链路，先验证核心功能，再逐步恢复外围能力。

### 4.3 千问 OpenAI-compatible 接口适配

模型调用层改造为新版 OpenAI Python SDK 风格：

- `from openai import OpenAI`
- `client = OpenAI(api_key=..., base_url=...)`
- `client.chat.completions.create(...)`

环境变量统一为：

- `OPENAI_API_KEY`
- `OPENAI_API_BASE`
- `OPENAI_MODEL`

统一配置入口可以减少脚本分叉、提升可移植性，并且与 OpenAI-compatible 服务（如千问兼容接口）对齐。

### 4.4 工具调用能力保留

- 原代码使用旧式 `functions/function_call`。
- 改造后采用 `tools/tool_calls`，并保留对 `/ChatGPT_function_call_service` 的调用。
- 在文本链路中仍可触发 `turtle_robot` 动作接口，维持单机器人控制能力。

## 5. 测试与验证流程

### 5.1 组件级启动验证

- 单独启动 `turtlesim_node`
- 单独启动 `turtle_robot`
- 单独启动 `chatgpt`

用于确认基础节点可独立运行、互不阻塞。

### 5.2 文本链路验证

- 监听输出 topic：`/llm_feedback_to_user`
- 手动发布输入 topic：`/llm_input_audio_to_text`

示例文本：

- “你好，请回复：模型已接通”
- “请让乌龟向前走一点”
- “请控制乌龟画一个正方形”

验证重点：

- `chatgpt` 节点是否收到输入并产生响应。
- `/llm_feedback_to_user` 是否有输出。
- 涉及动作时 `turtle_robot` 服务是否被调用。

### 5.3 最小闭环构建验证

采用全量重建保证环境干净：

```bash
cd ~/ros_llm_ws
rm -rf build install log
source /opt/ros/foxy/setup.bash
colcon build --symlink-install
source install/setup.bash
export ROS_DOMAIN_ID=77
```

## 6. 最终结果

已跑通：

- Foxy 环境下“纯文本 -> LLM -> 反馈 topic”主链路
- turtlesim 单机器人动作能力（通过函数工具调用链路）
- 千问 OpenAI-compatible 接口接入路径

暂时绕开：

- 语音输入输出链路（ASR/TTS）
- 多机器人高级流程的完整回归验证

当前方案优点：

- 不破坏 ROS1 现网环境
- 无需系统升级
- 快速建立最小可运行闭环

当前方案限制：

- 语音链路尚未恢复
- 与 Humble 主线仍存在维护差异

在当前约束下，这是风险最低且可交付的现实方案。

## 7. 经验与教训

- 运行开源 ROS 项目时，分支与 ROS 发行版匹配极其关键。
- topic 类型冲突会触发隐蔽的 DDS 反序列化错误，应优先用 `ros2 topic list -t`、`ros2 topic info -v` 排查。
- “最小可运行链路”是复杂系统排障的高效策略，能快速缩小问题空间。
- 需要保留旧环境时，兼容改造通常比直接升级更现实。
- 引入新模型接口时，应优先统一配置方式和调用封装，降低后续迁移成本。

## 8. 后续优化建议

- 恢复语音链路：
- 完整补齐 `boto3`、音频设备与依赖项，并做脚本化自检。

- 完善 Foxy 兼容性：
- 增加 Foxy CI，固化依赖版本，补充运行矩阵文档。

- 增加 Humble 独立运行方案：
- 在不影响现网的前提下提供 Docker/Humble 快速体验路径。

- 引入 ROS1/ROS2 bridge：
- 在保留 ROS1 系统的同时，让 ROS2 LLM 能力平滑接入旧系统。
