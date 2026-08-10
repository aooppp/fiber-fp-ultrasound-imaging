"""
结果面板 - 成像显示、进度、导出与日志
主界面精简；配置读写放进「更多」。
"""

import os
import json
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QSizePolicy, QDialog,
    QDialogButtonBox, QFormLayout,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from ui_theme import style_figure


class ResultMoreDialog(QDialog):
    def __init__(self, parent, export_path):
        super().__init__(parent)
        self.setWindowTitle("结果 · 更多")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.export_path_edit = QLineEdit(export_path)
        browse = QPushButton("选择…")
        browse.clicked.connect(self._browse)
        path_row = QHBoxLayout()
        path_row.addWidget(self.export_path_edit, 1)
        path_row.addWidget(browse)
        form.addRow("导出目录", path_row)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        self.save_config_btn = QPushButton("保存配置")
        self.load_config_btn = QPushButton("加载配置")
        btn_row.addWidget(self.save_config_btn)
        btn_row.addWidget(self.load_config_btn)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "选择导出目录", self.export_path_edit.text())
        if path:
            self.export_path_edit.setText(path)


class ResultPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._scan_data = None
        self._scan_positions = None
        self._start_time = None
        self._export_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "export")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        image_group = QGroupBox("成像结果")
        image_layout = QVBoxLayout(image_group)
        image_layout.setContentsMargins(8, 8, 8, 8)
        self.image_figure = Figure(figsize=(5.5, 3.8), dpi=100)
        self.image_figure.subplots_adjust(left=0.12, right=0.97, bottom=0.12, top=0.90)
        self.image_canvas = FigureCanvas(self.image_figure)
        self.image_canvas.setMinimumHeight(280)
        self.image_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_ax = self.image_figure.add_subplot(111)
        self.image_ax.set_title("等待扫描数据...")
        self.image_ax.set_xlabel("X (mm)")
        self.image_ax.set_ylabel("Z (mm)")
        style_figure(self.image_figure, self.image_ax)
        image_layout.addWidget(self.image_canvas)
        layout.addWidget(image_group, 1)

        bottom = QGroupBox("进度与数据")
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(10, 10, 10, 10)
        bottom_layout.setSpacing(8)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        bottom_layout.addWidget(self.progress_bar)
        self.progress_detail_label = QLabel("位置: 0/0    耗时: 0s    剩余: --")
        bottom_layout.addWidget(self.progress_detail_label)

        btn_row = QHBoxLayout()
        export_btn = QPushButton("导出扫描数据")
        export_btn.setProperty("role", "primary")
        export_btn.clicked.connect(self._export_data)
        btn_row.addWidget(export_btn)
        more_btn = QPushButton("更多…")
        more_btn.clicked.connect(self._open_more)
        btn_row.addWidget(more_btn)
        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(lambda: self.log_text.clear())
        btn_row.addWidget(clear_btn)
        bottom_layout.addLayout(btn_row)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(110)
        bottom_layout.addWidget(self.log_text)
        layout.addWidget(bottom)

    def _open_more(self):
        dlg = ResultMoreDialog(self, self._export_path)
        dlg.save_config_btn.clicked.connect(lambda: self._save_config(dlg.export_path_edit.text()))
        dlg.load_config_btn.clicked.connect(self._load_config)
        if dlg.exec_() == QDialog.Accepted:
            self._export_path = dlg.export_path_edit.text()

    def update_itf_plot(self, wl, v):
        pass

    def update_lock_display(self, data):
        pass

    def update_scan_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        if self._start_time is None:
            self._start_time = datetime.now()
        elapsed = (datetime.now() - self._start_time).total_seconds()
        if current > 0:
            avg_time = elapsed / current
            remaining = avg_time * (total - current)
            remaining_str = f"{remaining:.0f}s"
        else:
            remaining_str = "--"
        self.progress_detail_label.setText(
            f"位置: {current}/{total}    耗时: {elapsed:.0f}s    剩余: {remaining_str}"
        )

    def update_scan_data(self, data, positions):
        self._scan_data = data
        self._scan_positions = positions
        self._start_time = None
        if data is not None and len(data.shape) >= 3:
            self._show_bscan_preview(data)
        self.add_log(f"扫描数据已接收: {data.shape}")

    def _show_bscan_preview(self, data):
        self.image_ax.clear()
        mid_y = data.shape[1] // 2
        bscan = data[:, mid_y, :]
        self.image_ax.imshow(
            bscan.T,
            aspect="auto",
            cmap="magma",
            extent=[0, bscan.shape[0], bscan.shape[1], 0],
        )
        self.image_ax.set_title(f"B-scan 预览 (Y={mid_y})")
        self.image_ax.set_xlabel("X 位置")
        self.image_ax.set_ylabel("采样点")
        style_figure(self.image_figure, self.image_ax)
        self.image_canvas.draw()

    def add_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def _save_config(self, export_path=None):
        try:
            import config
            base = export_path or self._export_path
            config_path = os.path.join(base, "config.json")
            os.makedirs(os.path.dirname(config_path) or ".", exist_ok=True)
            config_data = {
                "laser_port": config.LASER_PORT,
                "stage_port": config.STAGE_PORT,
                "daq_device": config.DAQ_DEVICE,
                "voltage_unit": "V",
                "daq_driver_scale_to_v": config.DAQ_DRIVER_SCALE_TO_V,
                "scan_params": {
                    "x_start": config.SCAN_X_START,
                    "x_stop": config.SCAN_X_STOP,
                    "x_step": config.SCAN_X_STEP,
                    "y_start": config.SCAN_Y_START,
                    "y_stop": config.SCAN_Y_STOP,
                    "y_step": config.SCAN_Y_STEP,
                    "speed": config.SCAN_SPEED,
                },
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            self.add_log(f"配置已保存: {config_path}")
            QMessageBox.information(self, "成功", "配置已保存")
        except Exception as e:
            self.add_log(f"保存配置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存配置失败: {e}")

    def _load_config(self):
        try:
            path, _ = QFileDialog.getOpenFileName(
                self, "加载配置文件", "", "JSON文件 (*.json)"
            )
            if not path:
                return
            with open(path, "r", encoding="utf-8") as f:
                json.load(f)
            self.add_log(f"配置已加载: {path}")
            QMessageBox.information(self, "成功", "配置已加载")
        except Exception as e:
            self.add_log(f"加载配置失败: {e}")
            QMessageBox.critical(self, "错误", f"加载配置失败: {e}")

    def _export_data(self):
        if self._scan_data is None:
            QMessageBox.warning(self, "警告", "没有可导出的扫描数据")
            return
        try:
            export_dir = self._export_path
            os.makedirs(export_dir, exist_ok=True)
            if len(self._scan_data.shape) == 3:
                nx, ny, ns = self._scan_data.shape
                count = 0
                for ix in range(nx):
                    for iy in range(ny):
                        dat_path = os.path.join(export_dir, f"x{ix:04d}_y{iy:04d}.dat")
                        np.savetxt(dat_path, self._scan_data[ix, iy, :], fmt="%.10e")
                        count += 1
                self.add_log(f"已导出 {count} 个dat文件到: {export_dir}")
            else:
                count = 0
                for i in range(self._scan_data.shape[0]):
                    dat_path = os.path.join(export_dir, f"shot_{i+1:06d}.dat")
                    np.savetxt(dat_path, self._scan_data[i], fmt="%.10e")
                    count += 1
                self.add_log(f"已导出 {count} 个dat文件到: {export_dir}")
            QMessageBox.information(self, "成功", f"数据已导出到:\n{export_dir}")
        except Exception as e:
            self.add_log(f"导出数据失败: {e}")
            QMessageBox.critical(self, "错误", f"导出数据失败: {e}")
