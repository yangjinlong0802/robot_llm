# Robot LLM Vision Grasp Skill

## 简介

本 Skill 为大模型（LLM）提供调用机械臂视觉抓取能力的接口规范。
通过自然语言描述，LLM 可以驱动机械臂完成「目标检测 → SAM 分割 → 三维定位 → 抓取」的全流程。

## 核心文件

| 文件 | 用途 |
|------|------|
| `action_vision_capture.py` | 视觉抓取动作核心实现 |
| `action_vision_capture_gui.py` | GUI 封装层（GUI 专用，LLM 不直接调用） |
| `Robot.py` | RobotController 机械臂总控制器 |

## 依赖环境

- Python 3.9+
- `ultralytics` (YOLO + SAM 模型推理)
- `opencv-python` (cv2)
- `numpy`
- `scikit-learn` (GaussianMixture)
- 深度相机服务（Intel Realsense 或类似，需监听 `localhost:12345`）
- 机械臂 SDK：`Robotic_Arm/rm_robot_interface.py`
- 抓取位姿计算：`vertical_grab/interface.py`
- 模型文件：
  - YOLO：`best.pt`（目标检测）
  - SAM：`sam2.1_l.pt`（图像分割）
- 配置文件：`config.py`

## 架构说明

```
LLM / Agent
    │
    ▼
action_vision_capture.VisionCaptureAction
    │
    ├─ get_frames_from_socket()       ← 从深度相机服务获取 RGBD 帧
    ├─ detect_and_segment()           ← YOLO 检测 + SAM 分割 + GMM 优化
    ├─ vertical_catch()               ← 三维坐标变换，计算目标位姿
    └─ rm_movej_p / rm_movel /       ← 机械臂运动 + 夹爪控制
      rm_set_gripper_pick_on /
      rm_set_gripper_release
```

### 核心算法流程

1. **打开夹爪** → 记录初始位姿
2. **首次检测**：YOLO 检测目标 bounding-box → SAM 分割 → GMM 优化掩码 → `vertical_catch` 计算三维坐标
3. **移动到预备位置**：相机对准物体正上方
4. **二次精确检测**：重复第 2 步，提高定位精度
5. **XY 平面移动**：对准目标水平位置
6. **Z 轴下降**：垂直下降到抓取高度
7. **夹取**（最多重试 5 次）
8. **返回初始位姿**
9. **释放**（放置物体）

## 调用方式

### 方式一：复用 RobotController（推荐）

```python
from Robot import RobotController
from action_vision_capture import VisionCaptureAction

# RobotController 已在别处初始化并连接双机械臂
controller = RobotController()
action = VisionCaptureAction(
    controller           = controller,
    target_robot         = "robot1",      # "robot1" | "robot2"
    confidence_threshold = 0.7,
    save_debug_images    = True,
    move_velocity         = 15,
)

try:
    result = action.execute()
    if result:
        print("抓取成功")
    else:
        print("抓取失败:", action.last_error)
finally:
    action.shutdown()
```

### 方式二：独立调用（无 RobotController 时）

```python
from action_vision_capture import VisionCaptureAction

action = VisionCaptureAction(
    frame_provider       = "gui",         # 从 GUI socket 获取帧
    frame_socket_host     = "localhost",
    frame_socket_port     = 12345,
    yolo_model_path       = "/home/maic/10-robotgui/src/best.pt",
    sam_model_path        = "/home/maic/10-robotgui/src/sam2.1_l.pt",
    target_robot          = "robot1",
    confidence_threshold  = 0.7,
    save_debug_images     = True,
)

try:
    success = action.execute()
finally:
    action.shutdown()
```

### 方式三：通过 GUI 动作封装（GUI 编排器）

```python
from action_vision_capture_gui import VisionCaptureGUIAction

action = VisionCaptureGUIAction(
    controller     = robot_controller_instance,
    target_robot   = "robot1",
    confidence     = 0.75,
    debug_images   = True,
)
result = action.execute()
# result = {"success": bool, "error": str|None, "detail": str}
```

## 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `controller` | RobotController | `None` | 机械臂控制器实例，传入则复用其连接 |
| `target_robot` | str | `"robot1"` | 执行目标：`"robot1"` 或 `"robot2"` |
| `confidence_threshold` | float | `0.7` | YOLO 检测置信度阈值，范围 0.1~1.0 |
| `frame_provider` | str | `"gui"` | 帧来源：`"gui"` 或 `"standalone"` |
| `frame_socket_host` | str | `"localhost"` | 深度相机服务地址 |
| `frame_socket_port` | int | `12345` | 深度相机服务端口 |
| `yolo_model_path` | str | `"/home/maic/10-robotgui/src/best.pt"` | YOLO 模型路径 |
| `sam_model_path` | str | `"/home/maic/10-robotgui/src/sam2.1_l.pt"` | SAM 模型路径 |
| `gripper_offset` | list | `[3.146, 0, 3.128]` | 夹爪末端姿态偏移 |
| `rotation_matrix` | list | 3×3 矩阵 | 手眼标定旋转矩阵 |
| `translation_vector` | list | 三维向量 | 手眼标定平移向量 |
| `gripper_length` | float | `100` | 夹爪长度（mm），用于计算下降距离 |
| `move_velocity` | int | `15` | 机械臂运动速度 |
| `image_width` | int | `640` | 相机图像宽度 |
| `image_height` | int | `480` | 相机图像高度 |
| `save_debug_images` | bool | `True` | 是否保存检测/分割调试图片 |
| `debug_save_root` | str | `".../pictures/"` | 调试图片保存根目录 |
| `raise_on_error` | bool | `True` | 出错时是否抛出异常 |

## 返回值

| 属性 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 全流程是否成功 |
| `last_error` | str \| None | 错误信息（失败时） |

## LLM 提示词模板

当 LLM 需要执行视觉抓取任务时，可使用以下提示词模板：

```
请执行视觉抓取任务：
1. 使用 YOLO + SAM 模型检测并分割目标物体
2. 通过深度相机获取三维坐标
3. 控制 {target_robot} 机械臂完成抓取并放回初始位姿
4. 检测置信度阈值：{confidence}
5. YOLO 模型路径：{yolo_model_path}
6. SAM 模型路径：{sam_model_path}
```

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| 无法连接深度相机服务 | socket 重试 3 次，仍失败抛出 `RuntimeError` |
| 首次/二次检测未发现目标 | 保存 `failed_detection.jpg`，抛出 `RuntimeError` |
| 机械臂移动失败 | 返回错误码，抛出 `RuntimeError` |
| 夹取失败 | 最多重试 5 次，仍失败抛出 `RuntimeError` |
| 模型加载失败 | 打印错误，抛出异常 |

## 调试输出

执行时会打印以下关键信息：

```
[VisionCapture] 初始位姿: [...]
[VisionCapture] 机械臂已连接: 192.168.3.xx
[VisionCapture] 夹爪已打开
[VisionCapture] 已移动到 预备位置: [...]
[VisionCapture] 已移动到 目标上方: [...]
[VisionCapture] 已移动到 抓取位姿: [...]
[VisionCapture] 夹取成功
[VisionCapture] 已移动到 初始位姿: [...]
[VisionCapture] === 抓取流程完成 ===
```

调试图片保存位置（`save_debug_images=True` 时）：
```
{pictures_dir}/
├── first/
│   ├── detection.jpg   # 首次检测标注图
│   └── mask.jpg        # 首次分割掩码
├── second/
│   ├── detection.jpg   # 二次检测标注图
│   └── mask.jpg        # 二次分割掩码
└── failed/
    └── failed_detection.jpg  # 检测失败时的原图
```

## 注意事项

1. **深度相机服务必须提前启动**，并监听 `localhost:12345`，返回格式：
   ```python
   {
       "color":       np.ndarray,  # RGB 图像 (H, W, 3)
       "depth":       np.ndarray,  # 深度图 (H, W)
       "intrinsics":  dict         # 相机内参
   }
   ```
2. 模型路径（`best.pt`、`sam2.1_l.pt`）需根据实际部署环境修改。
3. 夹爪速度/力度可通过 `config.py` 中的 `GRIPPER_CONFIG` 全局调整。
4. 若 `raise_on_error=False`，`execute()` 返回 `False` 而不抛异常，适合批量执行。
