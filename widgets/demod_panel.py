"""
解调控制面板 - 激光器控制、ITF扫描、工作点锁定
主界面只保留常用操作；详细参数在「高级设置」。
"""

import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QLabel,
    QPushButton, QHBoxLayout, QFormLayout, QDialog,
    QMessageBox, QDoubleSpinBox, QSizePolicy, QFileDialog,
    QDialogButtonBox,
)
from PyQt5.QtCore import pyqtSignal
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from ui_controls import SafeComboBox as QComboBox, SafeDoubleSpinBox as QDoubleSpinBox
from ui_theme import style_figure


class DemodAdvancedDialog(QDialog):
    """解调高级参数"""

    def __init__(self, parent, values):
        super().__init__(parent)
        self.setWindowTitle("解调 · 高级设置")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(8)

        self.power_edit = QDoubleSpinBox()
        self.power_edit.setRange(-20, 30)
        self.power_edit.setDecimals(1)
        self.power_edit.setSuffix(" dBm")
        self.power_edit.setValue(values["power_dbm"])
        form.addRow("激光功率", self.power_edit)

        self.start_wl_edit = QDoubleSpinBox()
        self.start_wl_edit.setRange(1500, 1600)
        self.start_wl_edit.setDecimals(3)
        self.start_wl_edit.setSuffix(" nm")
        self.start_wl_edit.setValue(values["start_wl"])
        form.addRow("ITF 起始波长", self.start_wl_edit)

        self.stop_wl_edit = QDoubleSpinBox()
        self.stop_wl_edit.setRange(1500, 1600)
        self.stop_wl_edit.setDecimals(3)
        self.stop_wl_edit.setSuffix(" nm")
        self.stop_wl_edit.setValue(values["stop_wl"])
        form.addRow("ITF 终止波长", self.stop_wl_edit)

        self.speed_edit = QDoubleSpinBox()
        self.speed_edit.setRange(0.1, 100)
        self.speed_edit.setDecimals(2)
        self.speed_edit.setSuffix(" nm/s")
        self.speed_edit.setValue(values["speed"])
        form.addRow("ITF 扫描速度", self.speed_edit)

        self.target_v_edit = QDoubleSpinBox()
        self.target_v_edit.setRange(-10, 10)
        self.target_v_edit.setDecimals(4)
        self.target_v_edit.setSuffix(" V")
        self.target_v_edit.setValue(values["target_v"])
        form.addRow("手动目标电压", self.target_v_edit)

        self.target_wl_edit = QDoubleSpinBox()
        self.target_wl_edit.setRange(1500, 1600)
        self.target_wl_edit.setDecimals(4)
        self.target_wl_edit.setSingleStep(0.001)
        self.target_wl_edit.setSuffix(" nm")
        self.target_wl_edit.setValue(values["target_wl"])
        form.addRow("手动目标波长", self.target_wl_edit)

        self.pid_limit_edit = QDoubleSpinBox()
        self.pid_limit_edit.setRange(0.0001, 0.1)
        self.pid_limit_edit.setDecimals(4)
        self.pid_limit_edit.setSingleStep(0.0005)
        self.pid_limit_edit.setSuffix(" nm")
        self.pid_limit_edit.setValue(values["pid_limit"])
        form.addRow("PID 单步上限", self.pid_limit_edit)

        layout.addLayout(form)

        action_row = QHBoxLayout()
        self.apply_power_btn = QPushButton("应用功率")
        self.set_v_btn = QPushButton("按电压设工作点")
        self.set_wl_btn = QPushButton("按波长设工作点")
        action_row.addWidget(self.apply_power_btn)
        action_row.addWidget(self.set_v_btn)
        action_row.addWidget(self.set_wl_btn)
        layout.addLayout(action_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        return {
            "power_dbm": self.power_edit.value(),
            "start_wl": self.start_wl_edit.value(),
            "stop_wl": self.stop_wl_edit.value(),
            "speed": self.speed_edit.value(),
            "target_v": self.target_v_edit.value(),
            "target_wl": self.target_wl_edit.value(),
            "pid_limit": self.pid_limit_edit.value(),
        }


class DemodPanel(QWidget):
    scan_complete = pyqtSignal(object, object)
    status_update = pyqtSignal(str)
    lock_data = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.system = None
        self._lock_running = False
        self._lock_thread = None
        self._itf_wl = None
        self._itf_v = None
        self._last_lock_message = ""

        self._adv = {
            "power_dbm": 10.0,
            "start_wl": 1540.0,
            "stop_wl": 1560.0,
            "speed": 10.0,
            "target_v": 0.0,
            "target_wl": 1550.0,
            "pid_limit": 0.0020,
        }

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        conn = QGroupBox("激光器")
        conn_layout = QHBoxLayout(conn)
        conn_layout.setContentsMargins(10, 10, 10, 10)
        conn_layout.setSpacing(8)
        conn_layout.addWidget(QLabel("串口"))
        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self.port_combo.addItems(["COM3", "COM4", "COM5", "COM6"])
        self.port_combo.setMinimumWidth(100)
        conn_layout.addWidget(self.port_combo, 1)
        self.connect_btn = QPushButton("连接")
        self.connect_btn.setMinimumWidth(72)
        self.connect_btn.clicked.connect(self._toggle_laser_connection)
        conn_layout.addWidget(self.connect_btn)
        layout.addWidget(conn)

        ops = QGroupBox("操作")
        ops_layout = QVBoxLayout(ops)
        ops_layout.setContentsMargins(10, 10, 10, 10)
        ops_layout.setSpacing(8)

        row1 = QHBoxLayout()
        self.scan_btn = QPushButton("ITF 扫描")
        self.scan_btn.setProperty("role", "primary")
        self.scan_btn.setEnabled(False)
        self.scan_btn.clicked.connect(self._start_scan)
        row1.addWidget(self.scan_btn)

        self.auto_wp_btn = QPushButton("自动工作点")
        self.auto_wp_btn.setEnabled(False)
        self.auto_wp_btn.clicked.connect(self._auto_set_workpoint)
        row1.addWidget(self.auto_wp_btn)

        self.lock_btn = QPushButton("开始锁定")
        self.lock_btn.setProperty("role", "primary")
        self.lock_btn.setEnabled(False)
        self.lock_btn.clicked.connect(self._toggle_lock)
        row1.addWidget(self.lock_btn)

        self.stop_btn = QPushButton("停止锁定")
        self.stop_btn.setProperty("role", "danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_lock)
        row1.addWidget(self.stop_btn)
        ops_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.export_itf_btn = QPushButton("导出 ITF (.dat)")
        self.export_itf_btn.setEnabled(False)
        self.export_itf_btn.clicked.connect(self._export_itf_dat)
        row2.addWidget(self.export_itf_btn)

        advanced_btn = QPushButton("高级设置…")
        advanced_btn.clicked.connect(self._open_advanced)
        row2.addWidget(advanced_btn)
        ops_layout.addLayout(row2)

        self.status_label = QLabel("工作点: 未设定  |  锁定: --")
        self.status_label.setWordWrap(True)
        ops_layout.addWidget(self.status_label)
        layout.addWidget(ops)

        plot_group = QGroupBox("ITF 波形")
        plot_layout = QVBoxLayout(plot_group)
        plot_layout.setContentsMargins(8, 8, 8, 8)
        self.figure = Figure(figsize=(5, 3.6), dpi=100)
        self.figure.subplots_adjust(left=0.12, right=0.97, bottom=0.14, top=0.90)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(260)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel("波长 (nm)")
        self.ax.set_ylabel("电压 (V)")
        self.ax.set_title("ITF扫描波形")
        style_figure(self.figure, self.ax)
        plot_layout.addWidget(self.canvas)
        layout.addWidget(plot_group, 1)

    def _open_advanced(self):
        dlg = DemodAdvancedDialog(self, self._adv)
        dlg.apply_power_btn.clicked.connect(lambda: self._apply_power_from_dialog(dlg))
        dlg.set_v_btn.clicked.connect(lambda: self._manual_set_workpoint_from_dialog(dlg))
        dlg.set_wl_btn.clicked.connect(lambda: self._manual_set_wl_from_dialog(dlg))
        if dlg.exec_() == QDialog.Accepted:
            self._adv.update(dlg.values())
            if self.system is not None:
                self.system.pid.output_limit = float(self._adv["pid_limit"])
            self.status_update.emit("解调高级参数已更新")

    def _apply_power_from_dialog(self, dlg):
        self._adv["power_dbm"] = dlg.power_edit.value()
        self._set_laser_power()

    def _manual_set_workpoint_from_dialog(self, dlg):
        self._adv.update(dlg.values())
        self._manual_set_workpoint()

    def _manual_set_wl_from_dialog(self, dlg):
        self._adv.update(dlg.values())
        self._manual_set_workpoint_wavelength()

    def _toggle_laser_connection(self):
        if self.system is None:
            port = self.port_combo.currentText()
            try:
                from fp_lock_pfi_trigger import FPWorkPointStabilizerPFI
                self.system = FPWorkPointStabilizerPFI(laser_port=port)
                self._adv["pid_limit"] = float(self.system.pid.output_limit)
                self.system.do_init()
                self.connect_btn.setText("断开")
                self.scan_btn.setEnabled(True)
                self.status_update.emit(f"激光器已连接并初始化: {port}")
            except Exception as e:
                QMessageBox.critical(self, "连接失败", f"无法连接激光器: {e}")
                self.system = None
        else:
            self._stop_lock()
            try:
                self.system.shutdown()
            except Exception:
                pass
            self.system = None
            self.connect_btn.setText("连接")
            self.scan_btn.setEnabled(False)
            self.auto_wp_btn.setEnabled(False)
            self.lock_btn.setEnabled(False)
            self.status_update.emit("激光器已断开")

    def _set_laser_power(self):
        if self.system is None:
            QMessageBox.warning(self, "提示", "请先连接激光器")
            return
        power_dbm = self._adv["power_dbm"]
        power_mw = 10 ** (power_dbm / 10)
        try:
            self.system.set_laser_power(power_mw)
            self.status_update.emit(f"激光器功率已设置: {power_dbm:.1f} dBm ({power_mw:.2f} mW)")
        except Exception as e:
            QMessageBox.warning(self, "设置失败", f"设置激光器功率失败: {e}")

    def _start_scan(self):
        if self.system is None:
            return
        self.system.scan_start = self._adv["start_wl"]
        self.system.scan_stop = self._adv["stop_wl"]
        self.system.scan_speed = self._adv["speed"]
        self.status_update.emit(
            f"开始ITF扫描: {self.system.scan_start} - {self.system.scan_stop} nm"
        )
        from workers.laser_worker import LaserScanWorker
        self._scan_thread = LaserScanWorker(self.system)
        self._scan_thread.finished.connect(self._on_scan_finished)
        self._scan_thread.start()
        self.scan_btn.setEnabled(False)

    def _on_scan_finished(self, success):
        if success and self.system._scan_wl is not None:
            self._itf_wl = np.asarray(self.system._scan_wl, dtype=float)
            self._itf_v = np.asarray(self.system._scan_v, dtype=float)
            self.scan_complete.emit(self._itf_wl, self._itf_v)
            self.lock_btn.setEnabled(True)
            self.auto_wp_btn.setEnabled(True)
            self.export_itf_btn.setEnabled(True)
            if hasattr(self.system, "get_scan_info"):
                info = self.system.get_scan_info()
                self.status_update.emit(
                    f"扫描完成: {info['sample_points']} 个样本，"
                    f"PFI触发 {info['received_triggers']}/{info['expected_triggers']} 次，"
                    f"每次保留 {info['samples_per_trigger']} 点"
                )
                if info["received_triggers"] < info["expected_triggers"] - 1:
                    self.status_update.emit("警告: PFI触发数量不足，本次谱线可能不完整")
            else:
                self.status_update.emit(f"扫描完成: {len(self._itf_wl)} 点")
            self._update_itf_plot(self._itf_wl, self._itf_v)
        else:
            self.status_update.emit("扫描失败")
        self.scan_btn.setEnabled(self.system is not None)

    def _export_itf_dat(self):
        if self._itf_wl is None or self._itf_v is None:
            QMessageBox.warning(self, "提示", "没有可导出的 ITF 数据，请先完成扫描")
            return

        default_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "export")
        os.makedirs(default_dir, exist_ok=True)
        default_name = os.path.join(
            default_dir, f"itf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dat"
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 ITF 数据", default_name, "DAT 文件 (*.dat);;所有文件 (*.*)"
        )
        if not path:
            return
        if not path.lower().endswith(".dat"):
            path += ".dat"

        try:
            data = np.column_stack([self._itf_wl, self._itf_v])
            header = "wavelength_nm\tvoltage_V"
            np.savetxt(path, data, fmt="%.10e", delimiter="\t", header=header, comments="")
            self.status_update.emit(f"ITF 已导出: {path}")
            QMessageBox.information(self, "导出成功", f"ITF 数据已保存为:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def _update_itf_plot(self, wl, v):
        self.ax.clear()
        self.ax.plot(wl, v, "b-", linewidth=0.8)
        self.ax.set_xlabel("波长 (nm)")
        self.ax.set_ylabel("电压 (V)")
        self.ax.set_title("ITF扫描波形")
        style_figure(self.figure, self.ax)
        if self.system and self.system.workpoint_wl > 0:
            self.ax.plot(self.system.workpoint_wl, self.system.workpoint_v, "ro", markersize=8)
            self.ax.axhline(y=self.system.workpoint_v, color="r", linestyle="--", alpha=0.5)
            self.ax.axvline(x=self.system.workpoint_wl, color="r", linestyle="--", alpha=0.5)
        self.canvas.draw()

    def _refresh_wp_status(self):
        if self.system is None or self.system.workpoint_wl <= 0:
            self.status_label.setText("工作点: 未设定  |  锁定: --")
            return
        self.status_label.setText(
            f"工作点: {self.system.workpoint_wl:.4f} nm, {self.system.workpoint_v:.4f} V  |  "
            f"斜率: {self.system.workpoint_slope:.6f} V/nm"
        )

    def _auto_set_workpoint(self):
        if self.system is None:
            return
        self.system.set_workpoint_auto()
        self.lock_btn.setEnabled(True)
        self._refresh_wp_status()
        self.status_update.emit("自动设定工作点完成")
        if self.system._scan_wl is not None:
            self._update_itf_plot(self.system._scan_wl, self.system._scan_v)

    def _manual_set_workpoint(self):
        if self.system is None:
            return
        target_v = self._adv["target_v"]
        self.system.set_workpoint_manual(target_v)
        self.lock_btn.setEnabled(True)
        self._refresh_wp_status()
        self.status_update.emit(f"手动设定工作点: {target_v} V")
        if self.system._scan_wl is not None:
            self._update_itf_plot(self.system._scan_wl, self.system._scan_v)

    def _manual_set_workpoint_wavelength(self):
        if self.system is None:
            return
        target_wl = self._adv["target_wl"]
        self.system.set_workpoint_manual_wavelength(target_wl)
        self.lock_btn.setEnabled(True)
        self._refresh_wp_status()
        self.status_update.emit(f"按波长设定工作点: {self.system.workpoint_wl:.4f} nm")
        if self.system._scan_wl is not None:
            self._update_itf_plot(self.system._scan_wl, self.system._scan_v)

    def _toggle_lock(self):
        if self._lock_running:
            self._stop_lock()
        else:
            self._start_lock()

    def _start_lock(self):
        if self.system is None or self.system.workpoint_wl == 0:
            QMessageBox.warning(self, "警告", "请先设定工作点")
            return
        self._lock_running = True
        self.lock_btn.setText("锁定中...")
        self.stop_btn.setEnabled(True)
        self.system.pid.output_limit = float(self._adv["pid_limit"])
        try:
            started = self.system.start_lock()
        except Exception as exc:
            self._lock_running = False
            self.lock_btn.setText("开始锁定")
            self.stop_btn.setEnabled(False)
            QMessageBox.critical(self, "锁定启动失败", f"无法启动锁定:\n{exc}")
            return
        # Older working wrappers returned None after successfully starting.
        if started is False:
            self._lock_running = False
            self.lock_btn.setText("开始锁定")
            self.stop_btn.setEnabled(False)
            QMessageBox.warning(self, "警告", "锁定启动失败，请检查工作点")
            return
        from workers.laser_worker import LockWorker
        self._lock_thread = LockWorker(self.system)
        self._lock_thread.data_update.connect(self._on_lock_data_update)
        self._lock_thread.start()
        self.status_update.emit("工作点自动捕获与PID锁定已启动")

    def _on_lock_data_update(self, data):
        self.lock_data.emit(data)
        if data:
            def fmt(value, fmt_spec, empty="--"):
                try:
                    if value is None or not np.isfinite(float(value)):
                        return empty
                    return format(float(value), fmt_spec)
                except Exception:
                    return empty

            message = data.get("message") or ""
            self.status_label.setText(
                f"锁定  V={fmt(data.get('voltage'), '.5f')} V  "
                f"λ={fmt(data.get('wavelength'), '.4f')} nm  "
                f"e={fmt(data.get('error'), '.6f')} V"
                + (f"  |  {message}" if message else "")
            )
            if message and message != self._last_lock_message:
                self._last_lock_message = message
                self.status_update.emit(message)
                if "捕获成功" in message and self.system._scan_wl is not None:
                    self._update_itf_plot(self.system._scan_wl, self.system._scan_v)
            if self._lock_running and not data.get("running", True):
                self._lock_running = False
                self.lock_btn.setText("开始锁定")
                self.stop_btn.setEnabled(False)

    def _stop_lock(self):
        self._lock_running = False
        if self._lock_thread:
            self._lock_thread.stop()
            self._lock_thread = None
        if self.system:
            self.system.stop_lock()
        self.lock_btn.setText("开始锁定")
        self.stop_btn.setEnabled(False)
        self._refresh_wp_status()
        self.status_update.emit("PID锁定已停止")

    def cleanup(self):
        self._stop_lock()
        if self.system:
            try:
                self.system.shutdown()
            except Exception:
                pass
