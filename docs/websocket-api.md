# WebSocket API 使用文档

## 快速开始

### 1. 启动服务

```bash
# 安装依赖
pip install -r requirements.txt

# 模拟模式启动（开发调试用，不需要连接真实硬件）
python run_server.py --simulation

# 连接真实硬件启动
python run_server.py

# 自定义端口
python run_server.py --port 9000
```

启动成功后终端输出：

```
==================================================
机器人 WebSocket 控制服务
地址: ws://0.0.0.0:8765
模式: 模拟
==================================================
WebSocket 服务已启动: ws://0.0.0.0:8765
等待前端连接...
```

### 2. 前端连接

```javascript
const ws = new WebSocket("ws://localhost:8765");

ws.onopen = () => {
  console.log("已连接到机器人服务");
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("收到:", data);
};

ws.onclose = () => {
  console.log("连接已断开");
};
```

### 3. 通信协议

所有通信都是 JSON 格式。

- **前端 → 服务端**：发送指令，必须包含 `action` 字段
- **服务端 → 前端**：返回结果或推送事件，包含 `event` 字段

---

## 动作类型说明

系统支持 5 种动作类型，前端传参时 `type` 字段使用以下值：

| type 值 | 中文名 | 说明 |
|---------|-------|------|
| `MOVE_TO_POINT` | 移动类 | 机械臂移动 / 升降平台移动 |
| `ARM_ACTION` | 执行类 | 快换手、继电器、夹爪、吸液枪 |
| `INSPECT_AND_OUTPUT` | 检测类 | 传感器读取 |
| `CHANGE_GUN` | 换枪类 | 取/放工具头 |
| `VISION_CAPTURE` | 视觉类 | 视觉识别 + 抓取 |

### 各类型参数详解

#### MOVE_TO_POINT — 机械臂移动

```json
{
  "name": "移动到A点",
  "type": "MOVE_TO_POINT",
  "parameters": {
    "目标": "机械臂",
    "臂": "左",
    "模式": "move_j",
    "点位": "[-0.048, -0.269, -0.101, 3.109, -0.094, -1.592]"
  }
}
```

| 参数 | 可选值 | 说明 |
|-----|-------|------|
| 目标 | `"机械臂"` / `"身体"` | 控制机械臂还是升降平台 |
| 臂 | `"左"` / `"右"` | 左臂=Robot1，右臂=Robot2（目标为机械臂时） |
| 模式 | `"move_j"` / `"move_l"` | 关节运动 / 直线运动（目标为机械臂时） |
| 点位 | JSON 数组字符串 | 6维位姿（目标为机械臂时） |
| 位置 | 整数 | 脉冲值 0~500000（目标为身体时） |

#### MOVE_TO_POINT — 升降平台移动

```json
{
  "name": "升降到200mm",
  "type": "MOVE_TO_POINT",
  "parameters": {
    "目标": "身体",
    "位置": 100000
  }
}
```

#### ARM_ACTION — 快换手

```json
{
  "name": "快换手打开",
  "type": "ARM_ACTION",
  "parameters": {
    "执行器": "快换手",
    "操作": "开"
  }
}
```

#### ARM_ACTION — 夹爪

```json
{
  "name": "夹爪关闭",
  "type": "ARM_ACTION",
  "parameters": {
    "执行器": "夹爪",
    "操作": "关"
  }
}
```

| 参数 | 可选值 |
|-----|-------|
| 操作 | `"开"` / `"关"` |

#### ARM_ACTION — 继电器

```json
{
  "name": "继电器1打开",
  "type": "ARM_ACTION",
  "parameters": {
    "执行器": "继电器",
    "编号": 1,
    "操作": "开"
  }
}
```

| 参数 | 可选值 |
|-----|-------|
| 编号 | `1` / `2` |
| 操作 | `"开"` / `"关"` |

#### ARM_ACTION — 吸液枪

```json
{
  "name": "吸液500ul",
  "type": "ARM_ACTION",
  "parameters": {
    "执行器": "吸液枪",
    "操作": "吸",
    "容量": 500
  }
}
```

| 参数 | 可选值 | 说明 |
|-----|-------|------|
| 操作 | `"吸"` / `"吐"` | 吸液 / 吐液 |
| 容量 | 整数 | 单位: 微升(ul)，吐液时忽略 |

#### INSPECT_AND_OUTPUT — 传感器检测

```json
{
  "name": "检测温度",
  "type": "INSPECT_AND_OUTPUT",
  "parameters": {
    "Sensor_ID": "temp_01",
    "Threshold": 25.0,
    "Timeout": 5
  }
}
```

#### CHANGE_GUN — 换枪

```json
{
  "name": "取枪1",
  "type": "CHANGE_GUN",
  "parameters": {
    "Gun_Position": 1,
    "Operation": "取"
  }
}
```

| 参数 | 可选值 |
|-----|-------|
| Gun_Position | `1` / `2` |
| Operation | `"取"` / `"放"` |

#### VISION_CAPTURE — 视觉抓取

```json
{
  "name": "视觉抓取",
  "type": "VISION_CAPTURE",
  "parameters": {
    "目标机械臂": "robot1",
    "工作流": "vertical",
    "置信度": 0.7,
    "调试图片": true,
    "移动速度": 15,
    "夹爪长度": 100.0
  }
}
```

---

## API 详细说明

### 一、设备管理

#### 查询状态

```javascript
ws.send(JSON.stringify({ action: "status" }));
```

响应：

```json
{
  "event": "status",
  "devices": {
    "robot1": true,
    "robot2": true,
    "body": false
  },
  "executor": {
    "running": false,
    "paused": false
  },
  "sequence_length": 3,
  "ai_processing": false
}
```

#### 初始化机械臂

```javascript
ws.send(JSON.stringify({ action: "init_robots" }));
```

响应（异步推送，可能有多条）：

```json
{"event": "log", "message": "正在初始化机械臂..."}
{"event": "log", "message": "Robot1 初始化成功"}
{"event": "log", "message": "Robot2 初始化成功"}
{"event": "device_status_changed", "devices": {"robot1": true, "robot2": true, "body": false}}
```

#### 初始化升降平台

```javascript
ws.send(JSON.stringify({ action: "init_body" }));
```

#### 断开所有硬件

```javascript
ws.send(JSON.stringify({ action: "disconnect" }));
```

#### 测试相机

```javascript
ws.send(JSON.stringify({ action: "test_camera" }));
```

响应：

```json
{
  "event": "camera_test_result",
  "success": true,
  "message": "相机测试成功: color=640x480 depth=0.523m (SN=153122077516)"
}
```

---

### 二、动作库管理

动作库是预定义的动作模板，相当于 GUI 左侧的动作列表。

#### 获取动作类型参数结构（Schema）

前端可通过此接口获取所有动作类型的参数定义，动态生成新建/编辑动作的表单，无需硬编码。

```javascript
ws.send(JSON.stringify({ action: "get_action_schema" }));
```

响应：

```json
{
  "event": "action_schema",
  "types": {
    "MOVE_TO_POINT": {
      "label": "移动类",
      "description": "机械臂移动 / 升降平台移动",
      "variant_key": "目标",
      "variants": {
        "机械臂": {
          "description": "控制机械臂移动到指定点位",
          "fields": {
            "目标": {"type": "select", "options": ["机械臂"], "default": "机械臂", "label": "目标"},
            "臂":   {"type": "select", "options": ["左", "右"], "default": "左", "label": "臂"},
            "模式": {"type": "select", "options": [
              {"value": "move_j", "label": "关节运动 (move_j)"},
              {"value": "move_l", "label": "直线运动 (move_l)"}
            ], "default": "move_j", "label": "运动模式"},
            "点位": {"type": "text", "placeholder": "例如: [-0.048, ...]", "label": "点位", "required": true}
          }
        },
        "身体": {
          "description": "控制升降平台移动到指定位置",
          "fields": {
            "目标": {"type": "select", "options": ["身体"], "default": "身体", "label": "目标"},
            "位置": {"type": "number", "min": 0, "max": 500000, "default": 0, "unit": "脉冲", "label": "目标位置"}
          }
        }
      }
    },
    "ARM_ACTION": {
      "label": "执行类",
      "description": "快换手、继电器、夹爪、吸液枪等执行器操作",
      "variant_key": "执行器",
      "variants": {
        "快换手": { "fields": {"执行器": {...}, "编号": {...}, "操作": {...}} },
        "继电器": { "fields": {"执行器": {...}, "编号": {...}, "操作": {...}} },
        "夹爪":   { "fields": {"执行器": {...}, "编号": {...}, "操作": {...}} },
        "吸液枪": { "fields": {"执行器": {...}, "操作": {...}, "容量": {...}} }
      }
    },
    "INSPECT_AND_OUTPUT": {
      "label": "检测类",
      "fields": {"Sensor_ID": {...}, "Threshold": {...}, "Timeout": {...}}
    },
    "CHANGE_GUN": {
      "label": "换枪类",
      "fields": {"Gun_Position": {...}, "Operation": {...}}
    },
    "VISION_CAPTURE": {
      "label": "视觉类",
      "note": "视觉抓取参数已固定，前端仅需填写动作名称即可",
      "fields": {"目标机械臂": {...}, "工作流": {...}, ...}
    }
  }
}
```

**Schema 结构说明：**

| 字段 | 说明 |
|------|------|
| `label` | 动作类型的中文名，用于 Tab/下拉显示 |
| `description` | 类型描述 |
| `variant_key` | 有子类型时，表示根据哪个参数字段区分子类型（如 `"目标"` 或 `"执行器"`） |
| `variants` | 子类型字典，每个 key 对应 `variant_key` 的一个取值，包含该子类型的 `fields` |
| `fields` | 参数字段定义（无 variant 时直接在类型下，有 variant 时在各子类型下） |

**字段定义（fields 中每个条目）：**

| 属性 | 说明 |
|------|------|
| `type` | 字段类型：`"select"` / `"text"` / `"number"` / `"boolean"` |
| `options` | `select` 类型的可选值列表（可以是字符串/数字，也可以是 `{value, label}` 对象） |
| `default` | 默认值 |
| `label` | 显示标签 |
| `required` | 是否必填（默认 false） |
| `readonly` | 是否只读（如视觉抓取的固定参数） |
| `placeholder` | 输入提示文本 |
| `min` / `max` | 数值范围 |
| `unit` | 单位（如 `"ul"`, `"s"`, `"脉冲"`） |

**前端使用建议：**

1. 页面加载时调用一次 `get_action_schema`，缓存 schema
2. 新建动作时，根据用户选择的动作类型渲染对应的表单
3. 有 `variant_key` 的类型，先让用户选择子类型，再渲染对应子类型的 fields
4. `readonly` 字段直接使用 `default` 值，无需用户编辑

#### 获取动作库

```javascript
ws.send(JSON.stringify({ action: "list_actions" }));
```

响应：

```json
{
  "event": "actions_list",
  "actions": {
    "MOVE_TO_POINT": [
      {"id": "xxx", "name": "移动到A点", "type": "MOVE_TO_POINT", "parameters": {...}}
    ],
    "ARM_ACTION": [...],
    "INSPECT_AND_OUTPUT": [...],
    "CHANGE_GUN": [...],
    "VISION_CAPTURE": [...]
  },
  "total": 12
}
```

#### 新建动作

```javascript
ws.send(JSON.stringify({
  action: "create_action",
  name: "移动到安全位置",
  type: "MOVE_TO_POINT",
  parameters: {
    "目标": "机械臂",
    "臂": "左",
    "模式": "move_j",
    "点位": "[0.1, -0.2, 0.3, 1.57, 0, 0]"
  }
}));
```

响应：

```json
{
  "event": "action_created",
  "action": {
    "id": "生成的uuid",
    "name": "移动到安全位置",
    "type": "MOVE_TO_POINT",
    "parameters": {...}
  }
}
```

#### 更新动作

```javascript
ws.send(JSON.stringify({
  action: "update_action",
  id: "动作的id",
  name: "新名称",
  parameters: { "目标": "身体", "位置": 200000 }
}));
```

只需传入要修改的字段，未传的字段不变。

#### 删除动作

```javascript
ws.send(JSON.stringify({
  action: "delete_action",
  id: "动作的id"
}));
```

---

### 三、序列编排

序列是待执行的动作队列，相当于 GUI 右侧的序列列表。

#### 获取当前序列

```javascript
ws.send(JSON.stringify({ action: "get_sequence" }));
```

#### 添加动作到序列

方式1 — 从动作库引用（传 id）：

```javascript
ws.send(JSON.stringify({
  action: "add_to_sequence",
  action_ids: ["动作id1", "动作id2"]
}));
```

方式2 — 直接传入动作数据：

```javascript
ws.send(JSON.stringify({
  action: "add_to_sequence",
  items: [
    { name: "移动到A点", type: "MOVE_TO_POINT", parameters: { "目标": "机械臂", "臂": "左", "模式": "move_j", "点位": "[0,0,0,0,0,0]" } },
    { name: "夹爪打开", type: "ARM_ACTION", parameters: { "执行器": "夹爪", "操作": "开" } }
  ]
}));
```

响应（所有序列操作都返回完整序列）：

```json
{
  "event": "sequence_updated",
  "sequence": [...]
}
```

#### 移动顺序

```javascript
// 把第0项移到第2项的位置
ws.send(JSON.stringify({
  action: "move_in_sequence",
  from: 0,
  to: 2
}));
```

#### 删除某项

```javascript
ws.send(JSON.stringify({
  action: "remove_from_sequence",
  index: 1
}));
```

#### 清空序列

```javascript
ws.send(JSON.stringify({ action: "clear_sequence" }));
```

---

### 四、执行控制

#### 执行当前序列

```javascript
// 执行已编排好的序列
ws.send(JSON.stringify({ action: "execute" }));
```

#### 直接传入序列执行

```javascript
ws.send(JSON.stringify({
  action: "execute",
  sequence: [
    { name: "夹爪打开", type: "ARM_ACTION", parameters: { "执行器": "夹爪", "操作": "开" } },
    { name: "移动到A点", type: "MOVE_TO_POINT", parameters: { "目标": "机械臂", "臂": "左", "模式": "move_j", "点位": "[0.1,-0.2,0.3,1.57,0,0]" } },
    { name: "夹爪关闭", type: "ARM_ACTION", parameters: { "执行器": "夹爪", "操作": "关" } }
  ]
}));
```

#### 执行过程中的事件流

执行开始后，服务端会持续推送事件：

```
← {"event": "accepted", "message": "开始执行", "steps": 3}
← {"event": "step_started", "index": 0, "name": "夹爪打开", "status": "RUNNING"}
← {"event": "log", "message": "正在执行: 夹爪打开"}
← {"event": "log", "message": "参数: {执行器: 夹爪, 操作: 开}"}
← {"event": "log", "message": "夹爪开执行完成"}
← {"event": "step_completed", "index": 0, "name": "夹爪打开"}
← {"event": "step_started", "index": 1, "name": "移动到A点", "status": "RUNNING"}
← ...
← {"event": "step_completed", "index": 2, "name": "夹爪关闭"}
← {"event": "execution_finished"}
```

如果某步失败：

```
← {"event": "step_failed", "index": 1, "name": "移动到A点", "error": "机械臂控制器未初始化"}
← {"event": "execution_finished"}
```

#### 暂停 / 继续 / 停止

```javascript
ws.send(JSON.stringify({ action: "pause" }));   // ← {"event": "paused", ...}
ws.send(JSON.stringify({ action: "resume" }));   // ← {"event": "resumed", ...}
ws.send(JSON.stringify({ action: "stop" }));     // ← {"event": "stopped", ...}
```

---

### 五、任务持久化

任务是保存到磁盘的序列文件（`.task`），可以反复加载和执行。

#### 保存当前序列

```javascript
ws.send(JSON.stringify({
  action: "save_task",
  name: "抓瓶子流程.task"
}));
```

#### 查看已保存的任务

```javascript
ws.send(JSON.stringify({ action: "list_tasks" }));
```

响应：

```json
{
  "event": "tasks_list",
  "tasks": ["抓瓶子流程.task", "吸液流程.task"]
}
```

#### 加载任务到序列（不执行）

```javascript
ws.send(JSON.stringify({
  action: "load_task",
  name: "抓瓶子流程.task"
}));
```

响应：

```json
{
  "event": "task_loaded",
  "name": "抓瓶子流程.task",
  "sequence": [...]
}
```

#### 加载任务并立即执行

```javascript
ws.send(JSON.stringify({
  action: "execute_task",
  name: "抓瓶子流程.task"
}));
```

#### 删除任务

```javascript
ws.send(JSON.stringify({
  action: "delete_task",
  name: "抓瓶子流程.task"
}));
```

---

### 六、AI 自然语言助手

通过自然语言描述意图，AI 自动规划动作序列。

#### 完整流程

```
前端发送文字 → LLM分析意图 → 匹配技能 → 展开为动作序列 → 前端预览 → 确认执行
```

#### Step 1: 发送自然语言

```javascript
ws.send(JSON.stringify({
  action: "ai_chat",
  text: "帮我抓一个瓶子"
}));
```

#### Step 2: 监听 AI 事件

```
← {"event": "ai_status_changed", "status": "分析中..."}
← {"event": "ai_skill_matched", "skill_id": "grab_bottle", "skill_name": "抓取瓶子", "confidence": 0.95, "params": {...}, "reasoning": "用户想抓瓶子"}
← {"event": "ai_preview_ready", "sequence": [...], "skill_info": {"name": "抓取瓶子", "icon": "🤖", ...}}
← {"event": "ai_status_changed", "status": "预览就绪"}
```

#### Step 3: 确认或取消

```javascript
// 确认执行
ws.send(JSON.stringify({ action: "ai_confirm" }));

// 或者取消
ws.send(JSON.stringify({ action: "ai_cancel" }));
```

确认后会触发正常的执行事件流（`step_started` → `step_completed` → `execution_finished`）。

#### 查询 AI 状态

```javascript
ws.send(JSON.stringify({ action: "ai_status" }));
```

响应：

```json
{
  "event": "ai_status",
  "llm_available": true,
  "api_key_set": true,
  "model": "deepseek-reasoner",
  "provider": "DEEPSEEK",
  "processing": false,
  "has_preview": false
}
```

#### 查看可用技能

```javascript
ws.send(JSON.stringify({ action: "list_skills" }));
```

响应：

```json
{
  "event": "skills_list",
  "skills": [
    {"id": "grab_bottle", "name": "抓取瓶子", "icon": "🤖", "category": "GRAB", ...},
    {"id": "release_bottle", "name": "释放瓶子", ...},
    {"id": "absorb_liquid", "name": "吸液", ...}
  ]
}
```

---

## 前端集成示例

### React Hook 示例

```javascript
import { useEffect, useRef, useState, useCallback } from 'react';

function useRobotWS(url = 'ws://localhost:8765') {
  const wsRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const [logs, setLogs] = useState([]);
  const [deviceStatus, setDeviceStatus] = useState({});
  const [executionState, setExecutionState] = useState({ running: false, paused: false });
  const [sequence, setSequence] = useState([]);

  useEffect(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);

      switch (data.event) {
        // 日志
        case 'log':
          setLogs(prev => [...prev, data.message]);
          break;

        // 执行进度
        case 'step_started':
          console.log(`步骤 ${data.index} 开始: ${data.name}`);
          break;
        case 'step_completed':
          console.log(`步骤 ${data.index} 完成: ${data.name}`);
          break;
        case 'step_failed':
          console.error(`步骤 ${data.index} 失败: ${data.name} - ${data.error}`);
          break;
        case 'execution_finished':
          setExecutionState({ running: false, paused: false });
          break;

        // 状态
        case 'status':
          setDeviceStatus(data.devices);
          setExecutionState(data.executor);
          break;

        // 序列更新
        case 'sequence_updated':
        case 'task_loaded':
          setSequence(data.sequence);
          break;

        // 设备状态变更
        case 'device_status_changed':
          setDeviceStatus(data.devices);
          break;

        // 错误
        case 'error':
          console.error('服务端错误:', data.message);
          break;
      }
    };

    return () => ws.close();
  }, [url]);

  const send = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { connected, logs, deviceStatus, executionState, sequence, send };
}

// 使用示例
function RobotControl() {
  const { connected, logs, send, sequence } = useRobotWS();

  const handleExecute = () => {
    send({
      action: 'execute',
      sequence: [
        { name: '夹爪打开', type: 'ARM_ACTION', parameters: { '执行器': '夹爪', '操作': '开' } },
      ]
    });
  };

  return (
    <div>
      <p>连接状态: {connected ? '已连接' : '未连接'}</p>
      <button onClick={handleExecute}>执行</button>
      <button onClick={() => send({ action: 'stop' })}>停止</button>
      <button onClick={() => send({ action: 'status' })}>刷新状态</button>
      <div>{logs.map((log, i) => <p key={i}>{log}</p>)}</div>
    </div>
  );
}
```

### Vue 3 Composable 示例

```javascript
import { ref, onMounted, onUnmounted } from 'vue';

export function useRobotWS(url = 'ws://localhost:8765') {
  const ws = ref(null);
  const connected = ref(false);
  const logs = ref([]);
  const events = ref([]);

  function send(data) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(data));
    }
  }

  onMounted(() => {
    ws.value = new WebSocket(url);
    ws.value.onopen = () => (connected.value = true);
    ws.value.onclose = () => (connected.value = false);
    ws.value.onmessage = (e) => {
      const data = JSON.parse(e.data);
      events.value.push(data);
      if (data.event === 'log') {
        logs.value.push(data.message);
      }
    };
  });

  onUnmounted(() => ws.value?.close());

  return { connected, logs, events, send };
}
```

---

## 错误处理

所有错误都通过 `event: "error"` 返回：

```json
{"event": "error", "message": "错误描述"}
```

常见错误：

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| 已有序列正在执行，请先停止 | 重复执行 | 先发 `stop`，再执行新序列 |
| 序列为空，请先添加动作 | 没有编排序列就执行 | 先 `add_to_sequence` 或传 `sequence` |
| 机械臂控制器未初始化 | 未连接硬件 | 发 `init_robots` 或用 `--simulation` 启动 |
| LLM 不可用 | API Key 未配置 | 检查 `config.env` 中的 `OPENAI_API_KEY` |
| 无效的动作类型 | type 值不在枚举中 | 使用: `MOVE_TO_POINT` / `ARM_ACTION` / `INSPECT_AND_OUTPUT` / `CHANGE_GUN` / `VISION_CAPTURE` |

---

## 典型工作流

### 流程1: 手动编排并执行

```
1. list_actions          → 获取可用动作
2. add_to_sequence       → 编排序列
3. get_sequence          → 确认序列
4. execute               → 开始执行
5. 监听 step_* 事件      → 跟踪进度
6. save_task             → 保存为任务，下次直接用
```

### 流程2: 加载已有任务执行

```
1. list_tasks            → 查看有哪些任务
2. execute_task          → 直接执行
```

### 流程3: AI 语音/文字控制

```
1. ai_chat               → 发送自然语言
2. 监听 ai_preview_ready  → 显示预览
3. ai_confirm             → 用户确认
4. 监听 step_* 事件       → 跟踪进度
```

### 流程4: 从零创建并保存

```
1. create_action × N     → 创建多个动作模板
2. add_to_sequence       → 用 action_ids 引用已创建的动作
3. save_task             → 保存
```