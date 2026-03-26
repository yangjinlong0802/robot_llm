from PyQt6.QtWidgets import (QDialog, QFormLayout, QLineEdit, QComboBox,
                            QDoubleSpinBox, QDialogButtonBox, QVBoxLayout,
                            QHBoxLayout, QLabel, QSpinBox, QWidget, QStackedLayout)
from PyQt6.QtCore import Qt
from .models import ActionType, ActionDefinition


class ActionConfigDialog(QDialog):
    def __init__(self, action_type: ActionType, action_data: dict = None, parent=None):
        super().__init__(parent)
        self.action_type = action_type
        self.action_data = action_data or {}
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"配置 {self.get_type_display()} 动作")
        self.setMinimumWidth(400)

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setText(self.action_data.get('name', ''))
        form_layout.addRow("动作名称:", self.name_input)

        if self.action_type == ActionType.MOVE:
            # 目标选择：机械臂 或 身体
            self.target_combo = QComboBox()
            self.target_combo.addItem("机械臂", "机械臂")
            self.target_combo.addItem("身体", "身体")
            current_target = self.action_data.get('parameters', {}).get('目标', '机械臂')
            self.target_combo.setCurrentText(current_target)
            self.target_combo.currentIndexChanged.connect(self._on_target_changed)

            # 机械臂参数面板
            self.robot_widget = QWidget()
            robot_layout = QFormLayout()

            self.arm_combo = QComboBox()
            self.arm_combo.addItem("左", "左")
            self.arm_combo.addItem("右", "右")
            current_arm = self.action_data.get('parameters', {}).get('臂', '左')
            self.arm_combo.setCurrentText(current_arm)

            self.mode_combo = QComboBox()
            self.mode_combo.addItem("关节运动 (move_j)", "move_j")
            self.mode_combo.addItem("直线运动 (move_l)", "move_l")
            current_mode = self.action_data.get('parameters', {}).get('模式', 'move_j')
            self.mode_combo.setCurrentText(current_mode if current_mode in ['move_j', 'move_l'] else 'move_j')

            self.target_pose_input = QLineEdit()
            self.target_pose_input.setText(self.action_data.get('parameters', {}).get('点位', ''))
            self.target_pose_input.setPlaceholderText("例如: [-0.048, -0.269, -0.101, 3.109, -0.094, -1.592]")

            robot_layout.addRow("臂:", self.arm_combo)
            robot_layout.addRow("运动模式:", self.mode_combo)
            robot_layout.addRow("点位:", self.target_pose_input)
            self.robot_widget.setLayout(robot_layout)

            # 身体参数面板
            self.body_widget = QWidget()
            body_layout = QFormLayout()

            self.position_input = QSpinBox()
            self.position_input.setRange(0, 500000)
            self.position_input.setValue(self.action_data.get('parameters', {}).get('位置', 0))
            self.position_input.setSuffix(" (脉冲)")

            body_layout.addRow("目标位置:", self.position_input)
            self.body_widget.setLayout(body_layout)

            # 使用堆叠布局根据目标类型显示不同面板
            self.move_param_stack = QStackedLayout()
            self.move_param_stack.addWidget(self.robot_widget)
            self.move_param_stack.addWidget(self.body_widget)
            self.move_param_stack.setCurrentWidget(self.robot_widget)

            form_layout.addRow("目标:", self.target_combo)
            form_layout.addRow("参数:", self.move_param_stack)

            # 初始化显示状态
            self._on_target_changed()

        elif self.action_type == ActionType.MANIPULATE:
            self.executor_combo = QComboBox()
            self.executor_combo.addItem("快换手", "快换手")
            self.executor_combo.addItem("继电器", "继电器")
            self.executor_combo.addItem("夹爪", "夹爪")
            self.executor_combo.addItem("吸液枪", "吸液枪")
            current_executor = self.action_data.get('parameters', {}).get('执行器', '快换手')
            self.executor_combo.setCurrentText(current_executor)
            self.executor_combo.currentIndexChanged.connect(self._on_executor_changed)

            # 快换手/继电器/夹爪 时的参数面板
            self.normal_widget = QWidget()
            normal_layout = QFormLayout()

            self.number_combo = QComboBox()
            self.number_combo.addItem("1", 1)
            self.number_combo.addItem("2", 2)
            current_number = self.action_data.get('parameters', {}).get('编号', 1)
            self.number_combo.setCurrentText(str(current_number))

            self.operation_combo = QComboBox()
            self.operation_combo.addItem("开", "开")
            self.operation_combo.addItem("关", "关")
            current_operation = self.action_data.get('parameters', {}).get('操作', '开')
            self.operation_combo.setCurrentText(current_operation)

            normal_layout.addRow("编号:", self.number_combo)
            normal_layout.addRow("操作:", self.operation_combo)
            self.normal_widget.setLayout(normal_layout)

            # 吸液枪参数面板
            self.pipette_widget = QWidget()
            pipette_layout = QFormLayout()

            self.pipette_operation_combo = QComboBox()
            self.pipette_operation_combo.addItem("吸", "吸")
            self.pipette_operation_combo.addItem("吐", "吐")
            current_pipette_op = self.action_data.get('parameters', {}).get('操作', '吸')
            self.pipette_operation_combo.setCurrentText(current_pipette_op)

            self.capacity_input = QSpinBox()
            self.capacity_input.setRange(0, 10000)
            self.capacity_input.setSuffix(" ul")
            self.capacity_input.setValue(self.action_data.get('parameters', {}).get('容量', 500))

            pipette_layout.addRow("操作:", self.pipette_operation_combo)
            pipette_layout.addRow("容量:", self.capacity_input)
            self.pipette_widget.setLayout(pipette_layout)

            # 使用堆叠布局根据执行器类型显示不同面板
            self.param_stack = QStackedLayout()
            self.param_stack.addWidget(self.normal_widget)
            self.param_stack.addWidget(self.pipette_widget)
            self.param_stack.setCurrentWidget(self.normal_widget)

            form_layout.addRow("执行器:", self.executor_combo)
            form_layout.addRow("", self.param_stack)

            # 初始化显示状态
            self._on_executor_changed()

        elif self.action_type == ActionType.INSPECT:
            self.sensor_input = QLineEdit()
            self.sensor_input.setText(self.action_data.get('parameters', {}).get('Sensor_ID', ''))

            self.threshold_input = QDoubleSpinBox()
            self.threshold_input.setRange(-9999, 9999)
            self.threshold_input.setValue(self.action_data.get('parameters', {}).get('Threshold', 0))

            self.timeout_input = QDoubleSpinBox()
            self.timeout_input.setRange(0.1, 60)
            self.timeout_input.setValue(self.action_data.get('parameters', {}).get('Timeout', 5))
            self.timeout_input.setSuffix(" s")

            form_layout.addRow("传感器 ID:", self.sensor_input)
            form_layout.addRow("判定阈值:", self.threshold_input)
            form_layout.addRow("超时时间:", self.timeout_input)

        elif self.action_type == ActionType.CHANGE_GUN:
            self.gun_position_combo = QComboBox()
            self.gun_position_combo.addItem("1", 1)
            self.gun_position_combo.addItem("2", 2)
            current_pos = self.action_data.get('parameters', {}).get('Gun_Position', 1)
            self.gun_position_combo.setCurrentText(str(current_pos))

            self.operation_combo = QComboBox()
            self.operation_combo.addItem("取", "取")
            self.operation_combo.addItem("放", "放")
            current_op = self.action_data.get('parameters', {}).get('Operation', '取')
            self.operation_combo.setCurrentText(current_op)

            form_layout.addRow("枪位:", self.gun_position_combo)
            form_layout.addRow("取/放:", self.operation_combo)

        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_type_display(self) -> str:
        type_map = {
            ActionType.MOVE: "移动",
            ActionType.MANIPULATE: "机械臂",
            ActionType.INSPECT: "检测",
            ActionType.CHANGE_GUN: "换枪"
        }
        return type_map.get(self.action_type, "")

    def _on_executor_changed(self):
        """根据选择的执行器类型切换参数面板"""
        if hasattr(self, 'executor_combo') and hasattr(self, 'param_stack'):
            executor = self.executor_combo.currentData()
            if executor == '吸液枪':
                self.param_stack.setCurrentWidget(self.pipette_widget)
            else:
                self.param_stack.setCurrentWidget(self.normal_widget)

    def _on_target_changed(self):
        """根据选择的目标类型切换参数面板"""
        if hasattr(self, 'target_combo') and hasattr(self, 'move_param_stack'):
            target = self.target_combo.currentData()
            if target == '机械臂':
                self.move_param_stack.setCurrentWidget(self.robot_widget)
            else:
                self.move_param_stack.setCurrentWidget(self.body_widget)

    def validate_and_accept(self):
        name = self.name_input.text().strip()
        if not name:
            self.name_input.setFocus()
            return

        if self.action_type == ActionType.MOVE:
            # 根据目标类型验证不同参数
            if hasattr(self, 'target_combo'):
                target = self.target_combo.currentData()
                if target == '机械臂':
                    target_pose = self.target_pose_input.text().strip()
                    if not target_pose:
                        self.target_pose_input.setFocus()
                        return
                # 身体模式不需要额外验证
            else:
                target_pose = self.target_pose_input.text().strip()
                if not target_pose:
                    self.target_pose_input.setFocus()
                    return

        if self.action_type == ActionType.INSPECT:
            sensor_id = self.sensor_input.text().strip()
            if not sensor_id:
                self.sensor_input.setFocus()
                return

        self.accept()

    def get_action_definition(self) -> ActionDefinition:
        name = self.name_input.text().strip()
        parameters = {}

        if self.action_type == ActionType.MOVE:
            target = self.target_combo.currentData()
            if target == '机械臂':
                parameters = {
                    '目标': target,
                    '臂': self.arm_combo.currentText(),
                    '模式': self.mode_combo.currentData(),
                    '点位': self.target_pose_input.text().strip()
                }
            else:
                parameters = {
                    '目标': target,
                    '位置': self.position_input.value()
                }
        elif self.action_type == ActionType.MANIPULATE:
            executor = self.executor_combo.currentData()
            if executor == '吸液枪':
                parameters = {
                    '执行器': executor,
                    '操作': self.pipette_operation_combo.currentText(),
                    '容量': self.capacity_input.value()
                }
            else:
                parameters = {
                    '执行器': executor,
                    '编号': self.number_combo.currentData(),
                    '操作': self.operation_combo.currentText()
                }
        elif self.action_type == ActionType.INSPECT:
            parameters = {
                'Sensor_ID': self.sensor_input.text().strip(),
                'Threshold': self.threshold_input.value(),
                'Timeout': self.timeout_input.value()
            }
        elif self.action_type == ActionType.CHANGE_GUN:
            parameters = {
                'Gun_Position': self.gun_position_combo.currentData(),
                'Operation': self.operation_combo.currentText()
            }

        return ActionDefinition(
            id=self.action_data.get('id', ''),
            name=name,
            type=self.action_type,
            parameters=parameters
        )
