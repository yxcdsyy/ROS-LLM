[![Official](https://img.shields.io/badge/Official%20-Auromix-blue?style=flat&logo=world&logoColor=white)](https://github.com/Auromix) &nbsp;
[![ROS2 VERSION](https://img.shields.io/badge/ROS-ROS%202%20Humble-brightgreen)](http://docs.ros.org/en/humble/index.html) &nbsp;
[![Ubuntu VERSION](https://img.shields.io/badge/Ubuntu-22.04-green)](https://ubuntu.com/) &nbsp; [![LICENSE](https://img.shields.io/badge/license-Apache--2.0-informational)](https://github.com/Auromix/ROS-LLM/blob/ros2-humble/LICENSE) &nbsp;
[![GitHub Repo stars](https://img.shields.io/github/stars/Auromix/ROS-LLM?style=social)](https://github.com/Auromix/ROS-LLM/stargazers) &nbsp;
[![Twitter Follow](https://img.shields.io/twitter/follow/Hermanye233?style=social)](https://twitter.com/Hermanye233) &nbsp;

# ROS-LLM

ROS-LLM 是一个面向具身智能应用的 ROS 框架，核心目标是把自然语言大模型能力接入机器人控制流程。

你可以通过语音或文本与机器人交互，并通过函数调用机制将大模型输出映射为 ROS 中的真实动作控制（例如运动、导航或自定义技能）。

项目强调易扩展性。按照示例实现机器人功能接口后，可以较快完成接入。

![Related Schematics](llm_imgs/flow_diagram.png)

## 功能特性

- ROS 深度集成：基于 ROS 2 话题、服务和节点通信机制组织交互流程。
- 大模型驱动：支持基于 ChatGPT/OpenAI 兼容接口的语言理解与决策。
- 自然语言交互：支持“语音输入 -> 文本理解 -> 动作执行 -> 语音反馈”链路。
- 多机器人扩展：可在配置中维护多机器人名称并统一调度。
- 快速二次开发：通过 `llm_robot` + `llm_config` 自定义函数描述与执行逻辑。
- 聊天历史记录：会话数据可写入本地 JSON，便于回溯调试。

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/Auromix/ROS-LLM.git
```

### 2. 安装依赖

```bash
cd ROS-LLM/llm_install
bash dependencies_install.sh
```

### 3. 配置 OpenAI 兼容接口

脚本会写入 `~/.bashrc` 中的环境变量（`OPENAI_API_KEY`、`OPENAI_API_BASE`、`OPENAI_MODEL`）。

```bash
cd ROS-LLM/llm_install
bash config_openai_api_key.sh
source ~/.bashrc
```

### 4. 配置 AWS（可选）

如果你想使用云端 ASR/TTS，可执行：

```bash
cd ROS-LLM/llm_install
bash config_aws.sh
```

### 5. 配置本地 Whisper（可选）

如果你希望本地语音识别，可安装：

```bash
pip install -U openai-whisper
pip install setuptools-rust
```

### 6. 编译工作空间

```bash
cd <your_ws>
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

## 运行示例

### 示例 A：Turtlesim（云端语音输入）

```bash
ros2 launch llm_bringup chatgpt_with_turtle_robot.launch.py
```

启动监听：

```bash
ros2 topic pub /llm_state std_msgs/msg/String "data: 'listening'" -1
```

### 示例 B：多机器人（本地语音输入）

```bash
ros2 launch llm_bringup local_chatgpt_with_multi_robot.launch.py
```

### 示例 C：直接调用服务测试

```bash
ros2 service call /ChatGPT_service llm_interfaces/srv/ChatGPT "{request_text: '让小乌龟以较大角速度逆时针旋转并向前移动'}"
```

## 自定义你的机器人

若要接入你自己的机器人，重点修改以下两个包：

- `llm_robot`：实现真实动作函数（例如发布速度、调用服务等）。
- `llm_config`：定义函数描述、参数约束、模型行为提示词和机器人配置。

建议同时检查：

- `llm_config/llm_config/robot_behavior.py`
- `llm_config/llm_config/user_config.py`

## 项目结构

- `llm_bringup`：启动文件（单机器人、多机器人、演示场景）。
- `llm_model`：大模型调用节点与函数调用流程。
- `llm_input`：语音输入与状态管理。
- `llm_output`：语音播报与反馈输出。
- `llm_robot`：机器人动作接口实现。
- `llm_interfaces`：自定义 ROS 接口定义。
- `llm_install`：依赖与环境配置脚本。

## 未来计划

- Agent 任务机制
- 外部函数反馈通道
- 导航接口
- 更多传感器输入接口
- 视觉模型能力融合
- 持续性能与可扩展性优化

## 贡献

欢迎贡献代码与文档。提交 PR 前请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

本项目基于 Apache License 2.0，详见 [LICENSE](LICENSE)。
