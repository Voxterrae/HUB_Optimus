> 🇬🇧 English source: [docs/05_control_plane.md](../05_control_plane.md)

# 控制平面 —— 技术介绍 (ZH)

## 目的

HUB_Optimus 的控制平面是一个新的子系统，它将高级治理与模拟框架与现实世界的工具和自动化连接起来。它旨在实施策略、调节工具访问、记录遥测数据，并确保互动保持非强制性且可验证。

## 组成部分

### 策略引擎 (PolicyEngine)

`PolicyEngine` 保持一组授权规则，定义哪些参与者可以调用哪些工具。最简单情况下，它是一个内存字典，但未来计划用正式的策略引擎（如 Open Policy Agent）替代。

### 控制平面 (ControlPlane)

`ControlPlane` 协调工具调用。它接受参与者的请求，查询 `PolicyEngine` 决定调用是否允许，记录结果并返回。工具注册为 Python 可调用对象，可以是简单的算术函数或完整的 MCP 服务器。

## 使用方法

1. 导入控制平面：

   ```python
   from hub_optimus import ControlPlane, PolicyEngine
   ```

2. 定义一个策略字典，将参与者映射到允许的工具，并实例化 `PolicyEngine`。

3. 使用 `register_tool(name, func)` 在控制平面注册工具。

4. 通过 `invoke(actor, tool_name, **params)` 调用工具。控制平面返回一个四元组 `(call_id, timestamp, result, error)` 并在日志中记录调用。

具体示例请参见 `hub_optimus/test_hub_optimus_control.py` 单元测试。

## 当前状态及下一步

该控制平面是一个原型，需要扩展集成：

- 正式的策略评估（如 OPA/Rego）。
- 通过 SPIFFE/SPIRE 和 OpenFGA 实现身份和授权。
- 使用 OpenTelemetry 实现可观察性。
- 隔离工具执行（例如容器或微虚拟机）。
- 面向外部服务的 MCP 连接器。

欢迎对本文档的贡献和翻译。
