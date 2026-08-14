# Cross-platform AI State Hub

## 1. 项目目标

新建一个可安装、可自启动、可通过浏览器管理的跨平台本地服务：

```text
http://127.0.0.1:7800/
```

它不是单一的 Flipper 状态切换工具，而是多 AI 编程工具的统一接入中心：

- 检测本机已安装或已配置的 AI 工具。
- 为不同 AI 安装、修复和卸载 hook。
- 将各家不同的生命周期事件归一化。
- 在本地控制台实时显示事件、会话、来源和设备状态。
- 通过 BLE 将统一状态发送给 Flipper Zero。
- 支持 macOS、Windows 和 Linux。
- 后续可以扩展到其他提示灯或硬件，不把业务逻辑绑定到 Flipper。

## 2. 已确认的参考能力

本机 PromLight `http://127.0.0.1:7800/` 已实现了值得参考的产品模型：

- `GET /api/agents` 返回 AI 工具列表及 hook 安装状态。
- 页面中的“AI 接入”弹窗可以逐个安装或重新安装 hook。
- 支持全局、项目级和本地生成三种配置范围。
- 安装采用合并策略，不应直接覆盖用户已有配置。
- 通过 SSE 展示实时事件流。
- 支持多设备、设备选择、手动命令、参数读写和开机启动。

当前参考实现覆盖：

| ID | 工具 |
| --- | --- |
| `claude` | Claude Code |
| `codex` | Codex |
| `cursor` | Cursor |
| `copilot` | GitHub Copilot |
| `qoder` | Qoder |
| `codebuddy` | CodeBuddy |
| `antigravity` | Antigravity |

新项目可以借鉴行为和交互，但应独立实现代码、协议层和安装器。

## 3. 总体架构

```text
Claude / Codex / Cursor / Copilot / Qoder / CodeBuddy / Antigravity
                              |
                     Agent Adapter Layer
                              |
                      Normalized Event Bus
                              |
              +---------------+----------------+
              |                                |
       Web Console + REST/SSE             State Router
       127.0.0.1:7800                          |
                                      Device Adapter Layer
                                               |
                                        Flipper BLE
```

建议采用单个本地后台进程：

- Python 3.11+。
- FastAPI 或 Starlette 提供 REST、静态页面和 SSE/WebSocket。
- Bleak 负责跨平台 BLE。
- 前端使用轻量 HTML/CSS/TypeScript，构建后静态资源嵌入安装包。
- SQLite 保存配置、设备别名、事件记录和版本迁移信息；简单配置也可以使用 JSON，但写入必须原子化。

不要为三个平台分别维护三套桌面 UI。浏览器控制台应共用同一套前后端。

## 4. 模块边界

```text
src/ai_state_hub/
├── app.py                    # 进程入口与生命周期
├── config.py                 # 跨平台路径、配置读取和迁移
├── server/
│   ├── api.py                # REST API
│   ├── events.py             # SSE/WebSocket
│   └── static/               # 构建后的 Web 控制台
├── agents/
│   ├── base.py               # AgentAdapter 接口
│   ├── registry.py           # 适配器注册表
│   ├── claude.py
│   ├── codex.py
│   ├── cursor.py
│   ├── copilot.py
│   ├── qoder.py
│   ├── codebuddy.py
│   └── antigravity.py
├── hooks/
│   ├── receiver.py           # hook stdin/argv 解析
│   ├── normalizer.py         # 原始事件归一化
│   └── installer.py          # 配置合并、备份、修复、卸载
├── devices/
│   ├── base.py               # DeviceAdapter 接口
│   └── flipper_ble.py        # 扫描、连接、重连、发送状态
├── domain/
│   ├── events.py             # 统一事件模型
│   └── states.py             # 状态机与优先级
└── platform/
    ├── macos.py              # LaunchAgent、路径、蓝牙提示
    ├── windows.py            # Windows Service/任务计划、WinRT
    └── linux.py              # systemd user、BlueZ、权限检查
```

## 5. AgentAdapter 契约

每个 AI 工具使用独立适配器，至少实现：

```python
class AgentAdapter(Protocol):
    id: str
    display_name: str

    def detect(self) -> AgentDetection: ...
    def inspect(self, scope: InstallScope) -> HookStatus: ...
    def install(self, scope: InstallScope) -> InstallResult: ...
    def repair(self, scope: InstallScope) -> InstallResult: ...
    def uninstall(self, scope: InstallScope) -> InstallResult: ...
    def normalize(self, event_name: str, payload: dict) -> NormalizedEvent: ...
```

实现要求：

- 全局路径、项目路径和配置格式由适配器负责，不散落在 API 层。
- 修改前创建带时间戳的备份。
- 使用 JSON/TOML 等结构化解析与合并，禁止字符串拼接替换配置文件。
- 只删除本项目安装的 hook，不删除用户其他 hook。
- 重复安装必须幂等，等价于检查和修复。
- 检测结果区分：未发现工具、未安装 hook、部分安装、已安装、配置损坏。
- Windows 命令行引用、macOS/Linux shell 引用分别处理。

## 6. 统一事件模型

不同 AI 的事件名称不同，但进入系统后统一为：

```python
class EventPhase(str, Enum):
    SESSION_START = "session_start"
    USER_PROMPT = "user_prompt"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    APPROVAL_REQUIRED = "approval_required"
    TASK_SUCCESS = "task_success"
    TASK_ERROR = "task_error"
    TASK_CANCELLED = "task_cancelled"
    SESSION_END = "session_end"
```

事件对象建议包含：

```json
{
  "id": "uuid",
  "timestamp": "2026-08-13T15:00:00+08:00",
  "agent": "codex",
  "raw_event": "PermissionRequest",
  "phase": "approval_required",
  "session_id": "optional",
  "project_path": "optional",
  "tool_name": "optional",
  "summary": "optional redacted text",
  "payload": {},
  "target_devices": []
}
```

默认不要保存完整 prompt、密钥、文件内容或原始工具参数。事件日志应脱敏，并支持关闭持久化。

## 7. 统一设备状态

新项目的标准状态定义：

| 状态 | 语义 | Flipper 表现 |
| --- | --- | --- |
| `idle` | 无活动或会话取消/结束 | 待机动画，RGB 关闭 |
| `thinking` | AI 分析或等待模型结果 | 思考动画，蓝灯 |
| `running` | 工具执行或子任务运行 | 执行动画，黄灯 |
| `approval` | 等待用户批准或选择 | 待确认文字、独立铃声、紫色呼吸灯 |
| `success` | 本轮成功完成 | 成功动画、绿灯、成功提示音 |
| `error` | 失败或不可恢复错误 | 异常动画、红灯、错误提示音 |

当前 Flipper BLE 文本协议：

```text
state idle\n
state thinking\n
state running\n
state approval\n
state success\n
state error\n
```

设备端既定行为：

- 每次收到有效状态命令都唤醒一次屏幕背光。
- `approval` 使用独立三音提示和紫色呼吸灯。
- 取消/中断映射到 `idle`。
- 正常完成映射到 `success`。

## 8. 状态路由与并发

多个 AI 或多个会话可能同时运行，不能简单地让最后一条事件永久覆盖状态。

建议按会话维护状态，再根据优先级计算设备展示状态：

```text
error > approval > running > thinking > success > idle
```

规则建议：

- `approval` 必须保持，直到对应会话收到继续、取消或结束事件。
- `success` 和 `error` 可以设置展示超时，之后根据其他活动会话重新计算。
- 某一会话取消只移除该会话状态；没有其他活动会话时才进入 `idle`。
- 支持设备路由：全部设备、默认设备、按 AI 指定设备、按项目指定设备。
- 对同一状态的高频重复事件做去重，避免重复响铃和反复点亮屏幕。
- `approval` 只在首次进入时响铃；保持期间的相同事件不重复响。

## 9. 本地 Web 控制台

第一版页面建议包含以下区域。

### 9.1 总览

- 后台服务版本与运行状态。
- 蓝牙可用性。
- 已连接设备数。
- 当前统一状态。
- 开机启动开关。
- 最近错误和更新提示。

### 9.2 AI 接入

每个 AI 一行，显示：

- 图标、名称、是否检测到客户端。
- hook 状态和安装范围。
- 安装、修复、卸载按钮。
- 全局/项目范围选择。
- 查看将要修改的文件。
- 查看备份和恢复操作。

批量操作：

- 安装全部已检测工具。
- 修复全部。
- 检查配置冲突。

### 9.3 设备

- BLE 扫描、连接、断开、自动重连。
- 设备名称、地址/ID、固件协议版本、信号强度。
- 设备别名和默认设备。
- 六种状态手动测试。
- 铃声、呼吸灯、背光测试。
- 多设备路由规则。

### 9.4 事件流

- SSE 或 WebSocket 实时更新。
- 显示时间、AI 来源、事件、会话缩写、目标设备和结果。
- 按 AI、会话、级别筛选。
- 默认只展示脱敏摘要。
- 支持清屏，不默认提供无限期原始日志存储。

### 9.5 设置与诊断

- 服务端口，默认 `7800`。
- 开机启动。
- 日志级别和保留天数。
- hook 配置检查。
- BLE 权限与依赖检查。
- 导出诊断包，导出前预览并排除敏感内容。

## 10. API 草案

```text
GET    /api/status
GET    /api/agents
GET    /api/agents/{id}
POST   /api/agents/{id}/install
POST   /api/agents/{id}/repair
DELETE /api/agents/{id}/install

GET    /api/devices
POST   /api/devices/scan
POST   /api/devices/{id}/connect
POST   /api/devices/{id}/disconnect
POST   /api/devices/{id}/state

GET    /api/events                 # SSE
GET    /api/events/history
POST   /api/autostart
POST   /api/restart
GET    /api/diagnostics
```

Hook 接收建议优先走本地 IPC，而不是开放网络端口：

- macOS/Linux：Unix domain socket。
- Windows：Named Pipe。
- HTTP 仅作为兼容后备，并使用随机本地 token。

## 11. 安全边界

- Web 服务只绑定 `127.0.0.1` 和 `::1`，绝不默认监听 `0.0.0.0`。
- 所有写操作使用 CSRF 防护或本地会话 token。
- `/api/setup` 不接受任意 shell 命令，只接受结构化 agent、scope、project path。
- 项目路径必须规范化，并拒绝越权目录。
- hook 安装、卸载、服务重启等操作记录审计摘要。
- 配置更新采用临时文件 + fsync + 原子替换。
- 不记录 API key、环境变量、完整 prompt 和文件内容。
- 页面中的设备命令使用白名单协议，不暴露通用 shell。

## 12. 跨平台服务与安装包

### macOS

- 应用包或 `.pkg/.dmg`。
- 后台使用 LaunchAgent，运行在当前用户会话。
- 首次运行引导蓝牙权限。
- 浏览器入口可由菜单栏应用或快捷方式打开。

### Windows

- `.msi` 或签名 `.exe` 安装器。
- 用户级后台进程优先；必要时使用 Windows Service。
- BLE 使用 Bleak 的 WinRT 后端。
- hook 命令使用安装目录下固定可执行文件，避免依赖用户 Python。

### Linux

- 首选 `.deb`，后续增加 `.rpm` 和 AppImage。
- 后台使用 `systemd --user`。
- 检查 BlueZ、D-Bus 和蓝牙用户权限。
- 无桌面环境时仍能用 CLI 管理。

### 打包

- 使用 PyInstaller 或 Nuitka 生成独立二进制，用户不需要安装 Python。
- 前端资源随二进制或应用资源目录分发。
- 三个平台分别在原生 CI runner 构建，不能交叉假设 BLE 后端可用。
- 安装器必须提供干净卸载，但默认保留用户配置；卸载时可选择一并移除 hooks。

## 13. CLI 草案

Web 控制台之外保留完整 CLI，便于服务器和故障恢复：

```text
ai-state-hub serve
ai-state-hub status
ai-state-hub agents
ai-state-hub agent install codex --global
ai-state-hub agent install cursor --project /path/to/project
ai-state-hub agent repair all
ai-state-hub agent uninstall codex --global
ai-state-hub devices
ai-state-hub device connect <id>
ai-state-hub state approval
ai-state-hub diagnostics
```

## 14. 分阶段实施

### Phase 1：可用核心

- 创建新仓库与 Python 包结构。
- 实现配置、日志、Web 服务和统一事件模型。
- 迁移 Flipper BLE 连接与六状态协议。
- 实现 Codex adapter。
- 提供状态手动测试、事件流和 macOS LaunchAgent。

验收：Codex 的 prompt、工具执行、权限确认、成功、失败和取消均能正确驱动 Flipper。

### Phase 2：多 AI 接入

- 增加 Claude、Cursor、Copilot。
- 实现结构化配置合并、备份、修复和卸载。
- 完成“AI 接入”页面。
- 加入多会话状态聚合和重复事件抑制。

### Phase 3：跨平台

- Windows BLE、路径、hook 命令和安装器。
- Linux BlueZ、systemd user 和 `.deb`。
- 平台诊断页和首次运行引导。

### Phase 4：完整生态

- Qoder、CodeBuddy、Antigravity。
- 多设备路由。
- 固件协议版本协商。
- 自动更新、签名和发布流水线。

## 15. 测试矩阵

- 每个 AgentAdapter 的配置合并、幂等安装、修复、卸载和回滚。
- 带有用户既有 hooks 的配置不得丢失。
- Windows 路径带空格、Unicode 用户名、shell 引用。
- macOS/Linux 文件权限和符号链接。
- BLE 无权限、蓝牙关闭、设备未启动、连接中断和自动重连。
- 多 AI 并发时的状态优先级。
- `approval` 去重、解除和取消回 `idle`。
- Web 服务只监听 loopback。
- 非法项目路径、CSRF、任意命令注入和敏感日志检查。
- 安装、升级、降级和卸载后的 hook 恢复。

## 16. 新项目启动清单

1. 确定新仓库名称和目标许可证。
2. 固化统一事件与状态协议，先写测试。
3. 创建 `AgentAdapter` 和 `DeviceAdapter` 接口。
4. 迁移 Flipper BLE 客户端，不直接复制旧服务的全局路径。
5. 先完成 Codex adapter 和 macOS 开发闭环。
6. 再扩展其他 AI，不在核心层硬编码工具名称。
7. 每个平台使用原生 CI 构建并做真实蓝牙设备测试。

## 17. 可迁移的现有资产

从旧版本地 Flipper 原型工程可迁移：

- `ai_state_display.c`：Flipper 六状态、提示音、呼吸灯、背光行为。
- `ble_state_profile.c/.h`：BLE GATT Profile。
- `frames/`：五种已有动画素材；`approval` 当前使用文字回退，可后续补动画。
- `mac-client/src/flipper_state/`：Bleak 扫描、连接、daemon 和 socket 通信原型。
- `application.fam`：Flipper FAP 构建清单。

参考但不要直接耦合：

- `PromLight/agent_hook.py`：多 AI 事件解析和宏映射思路。
- `PromLight/events.json`：事件到语义分类的样例。
- `http://127.0.0.1:7800/`：AI 接入、设备管理和事件流的交互参考。

新项目开始时，应将此文档复制到新仓库的 `docs/architecture.md`，并以新仓库中的 ADR 和测试作为后续权威依据。
