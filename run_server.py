#!/usr/bin/env python3
"""
无 GUI 启动入口
初始化机器人硬件 → 启动 WebSocket 服务端

用法:
    python run_server.py                    # 默认端口 8765
    python run_server.py --port 9000        # 自定义端口
    python run_server.py --simulation       # 模拟模式（不连接硬件）
"""

import sys
import os
import argparse
import logging

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 机械臂模块路径
_src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
_robot_arm_path = os.path.join(_src_path, 'vertical_grab', 'code', 'robot_arm')
if _robot_arm_path not in sys.path:
    sys.path.insert(0, _robot_arm_path)


def setup_logging(level: str = "INFO") -> None:
    """配置日志"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def init_hardware(simulation: bool = False):
    """
    初始化机器人硬件，返回 (robot_controller, body_controller)
    模拟模式下返回 (None, None)
    """
    if simulation:
        print("== 模拟模式：跳过硬件初始化 ==")
        return None, None

    robot_controller = None
    body_controller = None

    # 初始化机械臂
    try:
        from Robot import RobotController
        print("正在初始化机械臂...")
        robot_controller = RobotController()

        robot1 = robot_controller.init_robot1()
        if robot1 is not None:
            print("  Robot1 初始化成功")
        else:
            print("  Robot1 初始化失败")

        robot2 = robot_controller.init_robot2()
        if robot2 is not None:
            print("  Robot2 初始化成功")
        else:
            print("  Robot2 初始化失败")

    except ImportError as e:
        print(f"机械臂模块导入失败: {e}")
    except Exception as e:
        print(f"机械臂初始化异常: {e}")

    # 初始化身体（ModbusMotor）
    try:
        from gui import ModbusMotor
        print("正在初始化身体控制器...")
        body_controller = ModbusMotor(port="/dev/body", baudrate=115200, slave_id=1, timeout=1)
        print("  身体控制器初始化成功")
    except ImportError as e:
        print(f"身体模块导入失败: {e}")
    except Exception as e:
        print(f"身体初始化异常: {e}")

    return robot_controller, body_controller


def main():
    parser = argparse.ArgumentParser(description="机器人 WebSocket 控制服务")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8765, help="监听端口 (默认: 8765)")
    parser.add_argument("--simulation", action="store_true", help="模拟模式，不连接硬件")
    parser.add_argument("--log-level", default="INFO", help="日志级别 (默认: INFO)")
    args = parser.parse_args()

    setup_logging(args.log_level)

    # 加载配置
    try:
        from src.config_loader import Config
        config = Config.load()
        if config.SIMULATION_MODE:
            args.simulation = True
            print("config.env 中 SIMULATION_MODE=True，启用模拟模式")
    except Exception:
        pass

    # 初始化硬件
    robot_controller, body_controller = init_hardware(args.simulation)

    # 启动 WebSocket 服务
    from src.ws_server import RobotWebSocketServer

    server = RobotWebSocketServer(
        robot_controller=robot_controller,
        body_controller=body_controller,
        host=args.host,
        port=args.port,
    )

    print("=" * 50)
    print(f"机器人 WebSocket 控制服务")
    print(f"地址: ws://{args.host}:{args.port}")
    print(f"模式: {'模拟' if args.simulation else '硬件'}")
    print("=" * 50)

    try:
        server.run()
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    main()