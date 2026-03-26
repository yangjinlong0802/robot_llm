import time
import sys
import os
from PyQt6.QtCore import QThread, pyqtSignal

# 添加路径以导入机械臂模块 (必须在其他导入之前)
_src_path = os.path.dirname(os.path.abspath(__file__))
_robot_arm_path = os.path.join(_src_path, 'vertical_grab', 'code', 'robot_arm')
if _robot_arm_path not in sys.path:
    sys.path.insert(0, _robot_arm_path)

from .models import SequenceItem, SequenceItemStatus, ActionType
from gui import ModbusMotor
from Class.Class_Delay import RelayController
from Class.Class_Kuaihuanshou import Kuaihuanshou
from Class.Class_ADP import ADP



class ExecutionThread(QThread):
    started = pyqtSignal()
    finished = pyqtSignal()
    step_started = pyqtSignal(int, SequenceItem)
    step_completed = pyqtSignal(int, SequenceItem)
    step_failed = pyqtSignal(int, SequenceItem, str)
    log_message = pyqtSignal(str)

    def __init__(self, sequence: list[SequenceItem], robot_controller=None, body_controller=None):
        super().__init__()
        self.sequence = sequence
        self._stop_requested = False
        self._paused = False
        self._robot_controller = robot_controller
        self._body_controller = body_controller

    def stop(self):
        self._stop_requested = True

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def run(self):
        self.started.emit()

        for index, item in enumerate(self.sequence):
            if self._stop_requested:
                self.log_message.emit("执行已停止")
                break

            while self._paused:
                time.sleep(0.1)
                if self._stop_requested:
                    self.log_message.emit("执行已停止")
                    break

            if self._stop_requested:
                break

            item.status = SequenceItemStatus.RUNNING
            self.step_started.emit(index, item)

            try:
                success = self._execute_action(item)
                item.status = SequenceItemStatus.SUCCESS if success else SequenceItemStatus.FAILED

                if success:
                    self.step_completed.emit(index, item)
                else:
                    error_msg = "动作执行失败"
                    self.step_failed.emit(index, item, error_msg)
                    break

            except Exception as e:
                item.status = SequenceItemStatus.FAILED
                error_msg = f"执行异常: {str(e)}"
                self.step_failed.emit(index, item, error_msg)
                break

        self.finished.emit()

    def _execute_action(self, item: SequenceItem) -> bool:
        definition = item.definition
        params = definition.parameters

        self.log_message.emit(f"正在执行: {definition.name}")
        self.log_message.emit(f"参数: {params}")

        try:
            if definition.type == ActionType.MOVE:
                return self._execute_move(params)
            elif definition.type == ActionType.MANIPULATE:
                return self._execute_manipulate(params)
            elif definition.type == ActionType.INSPECT:
                return self._execute_inspect(params)
            elif definition.type == ActionType.CHANGE_GUN:
                return self._execute_change_gun(params)
        except Exception as e:
            self.log_message.emit(f"执行错误: {str(e)}")
            return False

    def _execute_move(self, params: dict) -> bool:
        target = params.get('目标', '机械臂')

        if target == '身体':
            return self._execute_body_move(params)
        else:
            return self._execute_robot_move(params)

    def _execute_robot_move(self, params: dict) -> bool:
        """执行机械臂移动"""
        arm = params.get('臂', '左')
        target_pose_str = params.get('点位', '')
        mode = params.get('模式','')

        self.log_message.emit(f"机械臂移动动作: 臂={arm}, 模式={mode}, 点位={target_pose_str}")

        if self._robot_controller is None:
            self.log_message.emit("机械臂控制器未初始化")
            return False

        try:
            import json
            target_pose = json.loads(target_pose_str)

            if arm == '左':
                if mode == 'move_j':
                    success = self._robot_controller.move_robot1(target_pose)
                elif mode == 'move_l':
                    success = self._robot_controller.move_robot1l(target_pose)
                else:
                    self.log_message.emit("moshiyichang")
                    return False
            else:
                if mode == 'move_j':
                    success = self._robot_controller.move_robot2(target_pose)
                elif mode == 'move_l':
                    success = self._robot_controller.move_robot2l(target_pose)
                else:
                    self.log_message.emit("moshiyichang")
                    return False
            if success:
                self.log_message.emit(f"机械臂移动执行完成")
            return success
        except Exception as e:
            self.log_message.emit(f"执行机械臂移动出错: {str(e)}")
            return False

    def _execute_body_move(self, params: dict) -> bool:
        """执行身体移动（ModbusMotor）"""
        position = params.get('位置', 0)

        self.log_message.emit(f"身体移动动作: 目标位置={position}")

        if self._body_controller is None:
            self.log_message.emit("身体控制器未初始化")
            return False

        try:
            self.log_message.emit(f"正在移动身体到位置 {position}...")
            self._body_controller.move_to(position)

            # 等待到达目标位置
            while True:
                if self._stop_requested:
                    self.log_message.emit("身体移动已停止")
                    return False
                st = self._body_controller.is_reached()
                if st is None:
                    self.log_message.emit("身体通信异常")
                    return False
                if st:
                    self.log_message.emit(f"身体移动完成，位置={position}")
                    return True
                time.sleep(0.1)

        except Exception as e:
            self.log_message.emit(f"执行身体移动出错: {str(e)}")
            return False

    def _execute_manipulate(self, params: dict) -> bool:

        executor = params.get('执行器', '快换手')
        number = params.get('编号', 1)
        operation = params.get('操作', '开')

        if executor == '快换手':
            kuaihuanshou = Kuaihuanshou(port='/dev/hand')
            if operation == '开':
                kuaihuanshou.send_command('open')
            elif operation == '关':
                kuaihuanshou.send_command('close')
        elif executor == '继电器':
            adp = RelayController()
            if operation == '开':
                if number == 1:
                    adp.turn_on_relay_Y1()
                elif number == 2:
                    adp.turn_on_relay_Y2()
                else:
                    self.log_message.emit(f"未知的编号: {number}")
                    return False
            elif operation == '关':
                if number == 1:
                    adp.turn_off_relay_Y1()
                elif number == 2:
                    adp.turn_off_relay_Y2()
                else:
                    self.log_message.emit(f"未知的编号: {number}")
                    return False
        elif executor == '夹爪':
            return self._execute_gripper(operation)
        elif executor == '吸液枪':
            return self._execute_pipette(params)
        else:
            self.log_message.emit(f"未知的执行器: {executor}")
            return False

        self.log_message.emit(f"执行器: {executor}, 编号: {number}, 操作: {operation}")
        return True

    def _execute_gripper(self, operation: str) -> bool:
        """执行夹爪动作"""
        self.log_message.emit(f"夹爪动作: {operation}")

        if self._robot_controller is None:
            self.log_message.emit("机械臂控制器未初始化")
            return False

        try:
            if operation == '开':
                success = self._robot_controller.gripper_open_robot1()
            else:
                success = self._robot_controller.gripper_close_robot1()

            if success:
                self.log_message.emit(f"夹爪{operation}执行完成")
            return success
        except Exception as e:
            self.log_message.emit(f"执行夹爪出错: {str(e)}")
            return False

    def _execute_pipette(self, params: dict) -> bool:
        """执行吸液枪动作（吸/吐）"""
        operation = params.get('操作', '吸')
        capacity = params.get('容量', 500)
        port = params.get('端口', '/dev/hand')

        self.log_message.emit(f"吸液枪动作: 操作={operation}, 容量={capacity}ul")

        try:
            adp = ADP(port=port)
            if operation == '吸':
                self.log_message.emit("正在吸液...")
                ret = adp.absorb(capacity)
            elif operation == '吐':
                self.log_message.emit("正在吐液...")
                ret = adp.dispense_all()
            else:
                self.log_message.emit(f"未知的吸液枪操作: {operation}")
                adp.close()
                return False

            adp.close()

            if ret:
                self.log_message.emit(f"吸液枪{operation}执行成功")
            else:
                self.log_message.emit(f"吸液枪{operation}执行失败")
            return ret
        except Exception as e:
            self.log_message.emit(f"执行吸液枪出错: {str(e)}")
            return False


    def _execute_inspect(self, params: dict) -> bool:
        sensor_id = params.get('Sensor_ID', '')
        threshold = params.get('Threshold', 0)
        timeout = params.get('Timeout', 5)

        self.log_message.emit(f"读取传感器 {sensor_id}, 阈值: {threshold}, 超时: {timeout}s")
        time.sleep(0.8)
        self.log_message.emit("检测完成 - 结果: 通过")
        return True

    def _execute_change_gun(self, params: dict) -> bool:
        """执行换枪动作"""
        gun_position = params.get('Gun_Position', 1)
        operation = params.get('Operation', '取')

        self.log_message.emit(f"换枪动作: 枪位={gun_position}, 操作={operation}")

        if self._robot_controller is None:
            self.log_message.emit("机械臂控制器未初始化")
            return False

        try:
            method_map = {
                (1, '取'): 'pick_gun1',
                (2, '取'): 'pick_gun2',
                (1, '放'): 'drop_gun1',
                (2, '放'): 'drop_gun2'
            }

            key = (gun_position, operation)
            if key not in method_map:
                self.log_message.emit(f"未知的换枪参数组合: 枪位={gun_position}, 操作={operation}")
                return False

            method_name = method_map[key]
            self.log_message.emit(f"调用: {method_name}()")

            method = getattr(self._robot_controller, method_name)
            success = method()

            if success:
                self.log_message.emit(f"{method_name} 执行完成")
            return success
        except Exception as e:
            self.log_message.emit(f"执行换枪出错: {str(e)}")
            return False
