"""
扫描控制面板 - 位移台控制、采集卡、二维扫描
主界面只保留连接与启停；详细参数在「高级设置」。
"""

import os
import config
import numpy as np

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QFormLayout, QDialog,
    QMessageBox, QDoubleSpinBox, QSpinBox, QProgressBar,
    QFileDialog, QSizePolicy, QDialogButtonBox, QStackedWidget,
)
from PyQt5.QtCore import pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from ui_controls import (
    SafeComboBox as QComboBox,
    SafeDoubleSpinBox as QDoubleSpinBox,
    SafeSpinBox as QSpinBox,
)
from ui_theme import style_figure


class ScanAdvancedDialog(QDialog):
    def __init__(self, parent, values, mode_index):
        super().__init__(parent)
        self.setWindowTitle("扫描 · 高级设置")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("当前模式参数"))
        self.mode_hint = QLabel(
            "位移台联动" if mode_index == 0 else "纯触发采集"
        )
        mode_row.addWidget(self.mode_hint, 1)
        layout.addLayout(mode_row)

        self.stack = QStackedWidget()

        stage_page = QWidget()
        stage_form = QFormLayout(stage_page)
        stage_form.setSpacing(8)

        self.x_distance_edit = QDoubleSpinBox()
        self.x_distance_edit.setRange(0.1, 200)
        self.x_distance_edit.setSuffix(" mm")
        self.x_distance_edit.setValue(values["x_distance"])
        self.x_step_edit = QDoubleSpinBox()
        self.x_step_edit.setRange(0.01, 10)
        self.x_step_edit.setSuffix(" mm")
        self.x_step_edit.setValue(values["x_step"])
        x_row = QHBoxLayout()
        x_row.addWidget(self.x_distance_edit)
        x_row.addWidget(QLabel("步进"))
        x_row.addWidget(self.x_step_edit)
        stage_form.addRow("X 扫描", x_row)

        self.y_distance_edit = QDoubleSpinBox()
        self.y_distance_edit.setRange(0.1, 200)
        self.y_distance_edit.setSuffix(" mm")
        self.y_distance_edit.setValue(values["y_distance"])
        self.y_step_edit = QDoubleSpinBox()
        self.y_step_edit.setRange(0.01, 10)
        self.y_step_edit.setSuffix(" mm")
        self.y_step_edit.setValue(values["y_step"])
        y_row = QHBoxLayout()
        y_row.addWidget(self.y_distance_edit)
        y_row.addWidget(QLabel("步进"))
        y_row.addWidget(self.y_step_edit)
        stage_form.addRow("Y 扫描", y_row)

        self.speed_edit = QDoubleSpinBox()
        self.speed_edit.setRange(0.1, 50)
        self.speed_edit.setSuffix(" mm/s")
        self.speed_edit.setValue(values["speed"])
        self.settle_edit = QDoubleSpinBox()
        self.settle_edit.setRange(0, 5)
        self.settle_edit.setDecimals(2)
        self.settle_edit.setSuffix(" s")
        self.settle_edit.setValue(values["settle"])
        motion_row = QHBoxLayout()
        motion_row.addWidget(self.speed_edit)
        motion_row.addWidget(QLabel("等待"))
        motion_row.addWidget(self.settle_edit)
        stage_form.addRow("运动", motion_row)

        self.steps_rev_edit = QSpinBox()
        self.steps_rev_edit.setRange(100, 10000)
        self.steps_rev_edit.setSingleStep(100)
        self.steps_rev_edit.setValue(values["steps_rev"])
        stage_form.addRow("每转脉冲数", self.steps_rev_edit)

        self.sample_rate_edit = QDoubleSpinBox()
        self.sample_rate_edit.setRange(1000, config.DAQ_MAX_SAMPLE_RATE)
        self.sample_rate_edit.setDecimals(0)
        self.sample_rate_edit.setSuffix(" Hz")
        self.sample_rate_edit.setValue(values["sample_rate"])
        stage_form.addRow("采样率", self.sample_rate_edit)

        self.sample_length_edit = QSpinBox()
        self.sample_length_edit.setRange(100, 100000)
        self.sample_length_edit.setSingleStep(100)
        self.sample_length_edit.setValue(values["sample_length"])
        stage_form.addRow("采集点数", self.sample_length_edit)

        self.avg_count_edit = QSpinBox()
        self.avg_count_edit.setRange(1, 100)
        self.avg_count_edit.setValue(values["avg_count"])
        stage_form.addRow("平均次数", self.avg_count_edit)

        self.stack.addWidget(stage_page)

        trigger_page = QWidget()
        trigger_form = QFormLayout(trigger_page)
        trigger_form.setSpacing(8)
        self.trigger_groups_edit = QSpinBox()
        self.trigger_groups_edit.setRange(1, 100000)
        self.trigger_groups_edit.setValue(values["trigger_groups"])
        trigger_form.addRow("触发组数", self.trigger_groups_edit)

        self.trigger_sample_rate_edit = QDoubleSpinBox()
        self.trigger_sample_rate_edit.setRange(1000, config.DAQ_MAX_SAMPLE_RATE)
        self.trigger_sample_rate_edit.setDecimals(0)
        self.trigger_sample_rate_edit.setSuffix(" Hz")
        self.trigger_sample_rate_edit.setValue(values["trigger_sample_rate"])
        trigger_form.addRow("采样率", self.trigger_sample_rate_edit)

        self.trigger_sample_length_edit = QSpinBox()
        self.trigger_sample_length_edit.setRange(512, 100000)
        self.trigger_sample_length_edit.setSingleStep(512)
        self.trigger_sample_length_edit.setValue(values["trigger_sample_length"])
        trigger_form.addRow("采样点数", self.trigger_sample_length_edit)
        self.stack.addWidget(trigger_page)

        self.stack.setCurrentIndex(0 if mode_index == 0 else 1)
        layout.addWidget(self.stack)

        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("保存目录"))
        self.save_path_edit = QLineEdit(values["save_path"])
        path_row.addWidget(self.save_path_edit, 1)
        browse_btn = QPushButton("选择…")
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "选择保存目录", self.save_path_edit.text())
        if path:
            self.save_path_edit.setText(path)

    def values(self):
        return {
            "x_distance": self.x_distance_edit.value(),
            "x_step": self.x_step_edit.value(),
            "y_distance": self.y_distance_edit.value(),
            "y_step": self.y_step_edit.value(),
            "speed": self.speed_edit.value(),
            "settle": self.settle_edit.value(),
            "steps_rev": self.steps_rev_edit.value(),
            "sample_rate": self.sample_rate_edit.value(),
            "sample_length": self.sample_length_edit.value(),
            "avg_count": self.avg_count_edit.value(),
            "trigger_groups": self.trigger_groups_edit.value(),
            "trigger_sample_rate": self.trigger_sample_rate_edit.value(),
            "trigger_sample_length": self.trigger_sample_length_edit.value(),
            "save_path": self.save_path_edit.text(),
        }


class ScanPanel(QWidget):
    scan_progress = pyqtSignal(int, int)
    scan_data = pyqtSignal(object, object)
    status_update = pyqtSignal(str)
    waveform_data = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.mc600 = None
        self.daq = None
        self._scanning = False
        self._scan_thread = None
        self._adv = {
            "x_distance": config.SCAN_X_STOP - config.SCAN_X_START,
            "x_step": config.SCAN_X_STEP,
            "y_distance": config.SCAN_Y_STOP - config.SCAN_Y_START,
            "y_step": config.SCAN_Y_STEP,
            "speed": config.SCAN_SPEED,
            "settle": config.SCAN_SETTLE_TIME,
            "steps_rev": config.STAGE_STEPS_REV,
            "sample_rate": 10000000.0,
            "sample_length": 1024,
            "avg_count": 1,
            "trigger_groups": 500,
            "trigger_sample_rate": config.DAQ_SAMPLE_RATE,
            "trigger_sample_length": 1024,
            "trigger_slope": config.DAQ_TRIGGER_SLOPE,
            "trigger_sensitivity": config.DAQ_TRIGGER_SENSITIVITY,
            "input_range": config.DAQ_RANGE,
            "input_impedance": config.DAQ_IMPEDANCE,
            "save_path": os.path.join(os.path.dirname(os.path.dirname(__file__)), "scan_data"),
        }
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        device = QGroupBox("设备连接")
        device_layout = QVBoxLayout(device)
        device_layout.setContentsMargins(10, 10, 10, 10)
        device_layout.setSpacing(8)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("位移台"))
        self.stage_port_combo = QComboBox()
        self.stage_port_combo.setEditable(True)
        stage_ports = [config.STAGE_PORT, "COM3", "COM4", "COM5", "COM6"]
        self.stage_port_combo.addItems(list(dict.fromkeys(stage_ports)))
        self.stage_port_combo.setMinimumWidth(100)
        row1.addWidget(self.stage_port_combo, 1)
        self.stage_connect_btn = QPushButton("连接")
        self.stage_connect_btn.setMinimumWidth(72)
        self.stage_connect_btn.clicked.connect(self._toggle_stage_connection)
        row1.addWidget(self.stage_connect_btn)
        device_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("采集卡"))
        self.daq_device_edit = QLineEdit(config.DAQ_DEVICE)
        self.daq_device_edit.setMinimumWidth(100)
        row2.addWidget(self.daq_device_edit, 1)
        self.daq_connect_btn = QPushButton("连接")
        self.daq_connect_btn.setMinimumWidth(72)
        self.daq_connect_btn.clicked.connect(self._toggle_daq_connection)
        row2.addWidget(self.daq_connect_btn)
        device_layout.addLayout(row2)
        layout.addWidget(device)

        ops = QGroupBox("扫描控制")
        ops_layout = QVBoxLayout(ops)
        ops_layout.setContentsMargins(10, 10, 10, 10)
        ops_layout.setSpacing(8)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("模式"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["位移台联动采集", "纯触发采集"])
        self.mode_combo.setMinimumWidth(160)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_combo, 1)
        ops_layout.addLayout(mode_row)

        range_row = QHBoxLayout()
        range_row.addWidget(QLabel("输入量程"))
        self.input_range_combo = QComboBox()
        self.input_range_combo.addItem("±1 V", 1)
        self.input_range_combo.addItem("±5 V", 0)
        range_index = self.input_range_combo.findData(self._adv["input_range"])
        self.input_range_combo.setCurrentIndex(max(0, range_index))
        self.input_range_combo.setToolTip("选择 PCIe8526 模拟输入量程")
        self.input_range_combo.currentIndexChanged.connect(self._on_input_range_changed)
        range_row.addWidget(self.input_range_combo, 1)

        range_row.addWidget(QLabel("输入阻抗"))
        self.input_impedance_combo = QComboBox()
        self.input_impedance_combo.addItem("50 Ω", 1)
        self.input_impedance_combo.addItem("1 MΩ", 0)
        impedance_index = self.input_impedance_combo.findData(self._adv["input_impedance"])
        self.input_impedance_combo.setCurrentIndex(max(0, impedance_index))
        self.input_impedance_combo.setToolTip(
            "必须与 LabVIEW 例程一致；阻抗不一致会直接改变测得幅值"
        )
        self.input_impedance_combo.currentIndexChanged.connect(
            self._on_input_impedance_changed
        )
        range_row.addWidget(self.input_impedance_combo, 1)
        ops_layout.addLayout(range_row)

        trigger_row = QHBoxLayout()
        trigger_row.addWidget(QLabel("DTR 触发"))

        self.trigger_slope_combo = QComboBox()
        self.trigger_slope_combo.addItem("上升沿", 1)
        self.trigger_slope_combo.addItem("下降沿", 0)
        slope_index = self.trigger_slope_combo.findData(self._adv["trigger_slope"])
        self.trigger_slope_combo.setCurrentIndex(max(0, slope_index))
        self.trigger_slope_combo.setToolTip("选择 DTR 数字信号的有效跳变方向")
        trigger_row.addWidget(self.trigger_slope_combo, 1)

        trigger_row.addWidget(QLabel("灵敏度"))
        self.trigger_sensitivity_edit = QSpinBox()
        self.trigger_sensitivity_edit.setRange(0, 1638)
        self.trigger_sensitivity_edit.setValue(self._adv["trigger_sensitivity"])
        self.trigger_sensitivity_edit.setToolTip(
            "直接传给 ART-SCOPE sensitivity 参数；数值越大，过滤的短毛刺越多"
        )
        trigger_row.addWidget(self.trigger_sensitivity_edit, 1)
        ops_layout.addLayout(trigger_row)

        btn_row = QHBoxLayout()
        self.scan_btn = QPushButton("开始扫描")
        self.scan_btn.setProperty("role", "primary")
        self.scan_btn.setEnabled(False)
        self.scan_btn.clicked.connect(self._toggle_scan)
        btn_row.addWidget(self.scan_btn)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setProperty("role", "danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_scan)
        btn_row.addWidget(self.stop_btn)
        advanced_btn = QPushButton("高级设置…")
        advanced_btn.clicked.connect(self._open_advanced)
        btn_row.addWidget(advanced_btn)
        ops_layout.addLayout(btn_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        ops_layout.addWidget(self.progress_bar)
        self.progress_label = QLabel("就绪")
        ops_layout.addWidget(self.progress_label)
        layout.addWidget(ops)

        plot_group = QGroupBox("采集波形")
        plot_layout = QVBoxLayout(plot_group)
        plot_layout.setContentsMargins(8, 8, 8, 8)
        self.figure = Figure(figsize=(5, 3.6), dpi=100)
        self.figure.subplots_adjust(left=0.12, right=0.97, bottom=0.14, top=0.90)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(260)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel("采样点")
        self.ax.set_ylabel("电压 (V)")
        self.ax.set_title("采集波形")
        style_figure(self.figure, self.ax)
        self.waveform_line, = self.ax.plot([], [], "b-", linewidth=0.7)
        plot_layout.addWidget(self.canvas)
        layout.addWidget(plot_group, 1)

    def _open_advanced(self):
        dlg = ScanAdvancedDialog(self, self._adv, self.mode_combo.currentIndex())
        if dlg.exec_() == QDialog.Accepted:
            self._adv.update(dlg.values())
            self.status_update.emit("扫描高级参数已更新")

    def _apply_trigger_settings(self):
        slope = int(self.trigger_slope_combo.currentData())
        sensitivity = int(self.trigger_sensitivity_edit.value())

        self._adv["trigger_slope"] = slope
        self._adv["trigger_sensitivity"] = sensitivity

        if self.daq is not None:
            self.daq.trigger_source = "DTR"
            self.daq.trigger_slope = slope
            self.daq.trigger_sensitivity = sensitivity

        return slope, sensitivity

    def _apply_input_range(self):
        range_idx = int(self.input_range_combo.currentData())
        self._adv["input_range"] = range_idx
        if self.daq is not None:
            self.daq.range_idx = range_idx
        return range_idx

    def _on_input_range_changed(self, _index=None):
        range_idx = self._apply_input_range()
        range_text = "±1 V" if range_idx == 1 else "±5 V"
        self.status_update.emit(f"输入量程已设置为 {range_text}")

    def _apply_input_impedance(self):
        impedance = int(self.input_impedance_combo.currentData())
        self._adv["input_impedance"] = impedance
        if self.daq is not None:
            self.daq.impedance = impedance
        return impedance

    def _on_input_impedance_changed(self, _index=None):
        impedance = self._apply_input_impedance()
        impedance_text = "50 Ω" if impedance == 1 else "1 MΩ"
        self.status_update.emit(f"输入阻抗已设置为 {impedance_text}")

    def _toggle_stage_connection(self):
        if self.mc600 is None:
            port = self.stage_port_combo.currentText()
            try:
                from mc600_controller import MC600Controller
                self.mc600 = MC600Controller(
                    port=port,
                    baudrate=config.STAGE_BAUDRATE,
                )
                if self.mc600.connect():
                    self.stage_connect_btn.setText("断开")
                    self._check_scan_ready()
                    self.status_update.emit(f"位移台已连接: {port}")
                else:
                    QMessageBox.critical(
                        self,
                        "连接失败",
                        f"无法连接MC600位移台 ({port})。\n"
                        "请检查控制器电源、USB/RS232接线和串口号。",
                    )
                    self.mc600 = None
            except Exception as e:
                QMessageBox.critical(self, "连接失败", f"无法连接位移台: {e}")
                self.mc600 = None
        else:
            if self._scanning:
                self._stop_scan()
            try:
                self.mc600.disconnect()
            except Exception:
                pass
            self.mc600 = None
            self.stage_connect_btn.setText("连接")
            self._check_scan_ready()
            self.status_update.emit("位移台已断开")

    def _toggle_daq_connection(self):
        if self.daq is None:
            device = self.daq_device_edit.text()
            try:
                import config
                from hardware_paths import configure_hardware_paths, hardware_import_help

                configure_hardware_paths()
                try:
                    import art_scope_daq
                except ModuleNotFoundError as import_error:
                    missing = import_error.name or "art_scope_daq"
                    if missing == "art_scope_daq" or missing.startswith("ART_SCOPE"):
                        raise RuntimeError(hardware_import_help(missing)) from import_error
                    raise
                daq_class = getattr(art_scope_daq, "PCIe8526DAQ", None)
                if daq_class is None:
                    # The working experiment-PC wrapper keeps this legacy class name.
                    daq_class = getattr(art_scope_daq, "PCIe8536CDAQ", None)
                if daq_class is None:
                    raise RuntimeError(
                        "art_scope_daq.py 中未找到 PCIe8526DAQ 或兼容的 PCIe8536CDAQ 类"
                    )
                self.daq = daq_class(
                    device_name=device,
                    channel=config.DAQ_CHANNEL,
                    sample_rate=config.DAQ_SAMPLE_RATE,
                    sample_length=config.DAQ_SAMPLE_LENGTH,
                    range_idx=self._apply_input_range(),
                    coupling=config.DAQ_COUPLING,
                    impedance=self._apply_input_impedance(),
                    trigger_source="DTR",
                    trigger_level=config.DAQ_TRIGGER_LEVEL,
                    trigger_slope=self.trigger_slope_combo.currentData(),
                    trigger_coupling=config.DAQ_TRIGGER_COUPLING,
                    trigger_sensitivity=self.trigger_sensitivity_edit.value(),
                    timeout=config.DAQ_TIMEOUT,
                )
                self.daq_connect_btn.setText("断开")
                self._check_scan_ready()
                self.status_update.emit(
                    f"采集卡已配置: {device}，输入量程 {self.input_range_combo.currentText()}，"
                    f"输入阻抗 {self.input_impedance_combo.currentText()}"
                )
            except Exception as e:
                QMessageBox.critical(self, "连接失败", f"无法连接采集卡: {e}")
                self.daq = None
        else:
            if self._scanning:
                self._stop_scan()
            try:
                if self.daq.is_open:
                    self.daq.close()
            except Exception:
                pass
            self.daq = None
            self.daq_connect_btn.setText("连接")
            self._check_scan_ready()
            self.status_update.emit("采集卡已断开")

    def _on_mode_changed(self, index):
        self._check_scan_ready()

    def _check_scan_ready(self):
        mode = self.mode_combo.currentIndex()
        if mode == 0:
            ready = self.mc600 is not None and self.daq is not None
        else:
            ready = self.daq is not None
        self.scan_btn.setEnabled(ready)

    def _toggle_scan(self):
        if self._scanning:
            self._stop_scan()
        else:
            self._start_scan()

    def _start_scan(self):
        if self.daq is None:
            return
        self._apply_input_range()
        self._apply_input_impedance()
        slope, sensitivity = self._apply_trigger_settings()
        edge_text = "上升沿" if slope else "下降沿"
        self.status_update.emit(
            f"采集设置: {self.input_range_combo.currentText()}，"
            f"{self.input_impedance_combo.currentText()}，DTR {edge_text}，灵敏度 {sensitivity}"
        )
        if self.mode_combo.currentIndex() == 0:
            self._start_stage_scan()
        else:
            self._start_trigger_scan()

    def _start_stage_scan(self):
        if self.mc600 is None:
            return
        x_current = self.mc600.get_position("X")
        y_current = self.mc600.get_position("Y")
        if x_current is None or y_current is None:
            QMessageBox.warning(self, "警告", "无法获取当前位置，请先归零位移台")
            return

        x_start = x_current
        x_stop = x_current + self._adv["x_distance"]
        y_start = y_current
        y_stop = y_current + self._adv["y_distance"]

        self.status_update.emit(f"当前位置: X={x_current:.2f}, Y={y_current:.2f} mm")
        self.status_update.emit(
            f"扫描范围: X=[{x_start:.2f}, {x_stop:.2f}], Y=[{y_start:.2f}, {y_stop:.2f}] mm"
        )

        self._scanning = True
        self.input_range_combo.setEnabled(False)
        self.input_impedance_combo.setEnabled(False)
        self.scan_btn.setText("扫描中...")
        self.stop_btn.setEnabled(True)

        from workers.scan_worker import ScanWorker
        self._scan_thread = ScanWorker(
            self.mc600, self.daq,
            x_start, x_stop, self._adv["x_step"],
            y_start, y_stop, self._adv["y_step"],
            self._adv["speed"], self._adv["settle"], self._adv["save_path"],
            self._adv["avg_count"], self._adv["sample_length"], self._adv["sample_rate"],
            self._adv["steps_rev"],
        )
        self._scan_thread.progress.connect(self._on_scan_progress)
        self._scan_thread.waveform.connect(self._on_waveform)
        self._scan_thread.finished.connect(self._on_scan_finished)
        self._scan_thread.start()
        self.status_update.emit("位移台联动扫描已启动")

    def _start_trigger_scan(self):
        self._scanning = True
        self.input_range_combo.setEnabled(False)
        self.input_impedance_combo.setEnabled(False)
        self.scan_btn.setText("采集中...")
        self.stop_btn.setEnabled(True)
        from workers.scan_worker import TriggerWorker
        self._scan_thread = TriggerWorker(
            self.daq,
            self._adv["trigger_groups"],
            self._adv["trigger_sample_rate"],
            self._adv["trigger_sample_length"],
            self._adv["save_path"],
        )
        self._scan_thread.progress.connect(self._on_scan_progress)
        self._scan_thread.waveform.connect(self._on_waveform)
        self._scan_thread.finished.connect(self._on_scan_finished)
        self._scan_thread.start()
        self.status_update.emit(f"纯触发采集已启动: {self._adv['trigger_groups']}组")

    def _stop_scan(self):
        self._scanning = False
        self.input_range_combo.setEnabled(True)
        self.input_impedance_combo.setEnabled(True)
        if self._scan_thread:
            self._scan_thread.stop()
            self._scan_thread = None
        self.scan_btn.setText("开始扫描")
        self.stop_btn.setEnabled(False)
        self.status_update.emit("扫描已停止")

    def _on_scan_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"进度: {current}/{total}")
        self.scan_progress.emit(current, total)

    def _on_waveform(self, data):
        self.waveform_data.emit(data)

    def update_waveform_plot(self, data):
        if data is not None:
            values = np.asarray(data, dtype=np.float64).reshape(-1)
            self.waveform_line.set_data(np.arange(values.size), values)
            self.ax.relim()
            self.ax.autoscale_view()
            self.canvas.draw_idle()

    def _on_scan_finished(self, data, positions):
        self._scanning = False
        self.input_range_combo.setEnabled(True)
        self.input_impedance_combo.setEnabled(True)
        self.scan_btn.setText("开始扫描")
        self.stop_btn.setEnabled(False)
        if data is not None:
            self.scan_data.emit(data, positions)
            self.status_update.emit(f"扫描完成: {data.shape}")
        else:
            self.status_update.emit("扫描失败")

    def cleanup(self):
        self._stop_scan()
        if self.mc600:
            try:
                self.mc600.disconnect()
            except Exception:
                pass
        if self.daq:
            try:
                if self.daq.is_open:
                    self.daq.close()
            except Exception:
                pass
