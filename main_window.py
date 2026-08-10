"""
光纤超声成像系统 - 主窗口
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QAction, QMessageBox, QFrame, QLabel
)
from PyQt5.QtCore import Qt

from widgets.demod_panel import DemodPanel
from widgets.scan_panel import ScanPanel
from widgets.result_panel import ResultPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("光纤FP超声成像系统")
        self.setMinimumSize(1500, 820)

        central_widget = QWidget()
        central_widget.setObjectName("AppRoot")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 10, 12, 12)
        main_layout.setSpacing(10)

        main_layout.addWidget(self._build_top_bar())

        workspace = QFrame()
        workspace.setObjectName("WorkspaceFrame")
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        workspace_layout.addWidget(splitter)
        main_layout.addWidget(workspace, 1)

        self.demod_panel = DemodPanel()
        self.scan_panel = ScanPanel()
        self.result_panel = ResultPanel()

        splitter.addWidget(self._build_column(
            "01", "解调锁定", "激光器 · ITF · 工作点",
            self.demod_panel,
        ))
        splitter.addWidget(self._build_column(
            "02", "扫描采集", "位移台 · 高速 DAQ",
            self.scan_panel,
        ))
        splitter.addWidget(self._build_column(
            "03", "成像结果", "B-scan · 导出 · 日志",
            self.result_panel,
        ))

        splitter.setSizes([480, 500, 560])
        splitter.setChildrenCollapsible(False)

        self._create_menu_bar()
        self._connect_signals()

    def _build_top_bar(self):
        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_bar.setFixedHeight(58)

        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)

        brand = QLabel("FP")
        brand.setObjectName("BrandMark")
        brand.setAlignment(Qt.AlignCenter)
        brand.setFixedSize(34, 34)
        layout.addWidget(brand)

        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        title = QLabel("光纤 FP 超声成像实验室")
        title.setObjectName("AppTitle")
        subtitle = QLabel("工作点锁定 · RF 口采集 · 二维 B-scan 成像")
        subtitle.setObjectName("AppSubtitle")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        layout.addLayout(title_block, 1)

        meta = QFrame()
        meta.setObjectName("MetaStrip")
        meta_layout = QHBoxLayout(meta)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(8)

        version = QLabel("v1.0.0")
        version.setProperty("class", "MetaItem")
        version.setFixedHeight(28)
        meta_layout.addWidget(version)

        ready = QLabel("系统就绪")
        ready.setProperty("class", "MetaItemReady")
        ready.setFixedHeight(28)
        meta_layout.addWidget(ready)

        layout.addWidget(meta)
        return top_bar

    def _build_column(self, index, title, hint, panel):
        column = QFrame()
        column.setObjectName("ColumnPanel")
        col_layout = QVBoxLayout(column)
        col_layout.setContentsMargins(0, 0, 0, 0)
        col_layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("ColumnHeader")
        header.setFixedHeight(40)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 4, 12, 4)
        header_layout.setSpacing(8)

        idx = QLabel(index)
        idx.setObjectName("ColumnIndex")
        header_layout.addWidget(idx)

        text_block = QVBoxLayout()
        text_block.setSpacing(0)
        title_label = QLabel(title)
        title_label.setObjectName("ColumnTitle")
        hint_label = QLabel(hint)
        hint_label.setObjectName("ColumnHint")
        text_block.addWidget(title_label)
        text_block.addWidget(hint_label)
        header_layout.addLayout(text_block, 1)

        col_layout.addWidget(header)
        # 直接放入面板，不用 ScrollArea，波形区才能纵向拉伸占满剩余高度
        col_layout.addWidget(panel, 1)

        return column

    def _create_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件")

        save_action = QAction("保存配置", self)
        save_action.triggered.connect(self._save_config)
        file_menu.addAction(save_action)

        load_action = QAction("加载配置", self)
        load_action.triggered.connect(self._load_config)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _connect_signals(self):
        self.demod_panel.scan_complete.connect(self.result_panel.update_itf_plot)
        self.demod_panel.status_update.connect(self.result_panel.add_log)
        self.demod_panel.lock_data.connect(self.result_panel.update_lock_display)

        self.scan_panel.scan_progress.connect(self.result_panel.update_scan_progress)
        self.scan_panel.scan_data.connect(self.result_panel.update_scan_data)
        self.scan_panel.status_update.connect(self.result_panel.add_log)
        self.scan_panel.waveform_data.connect(self.scan_panel.update_waveform_plot)

    def _save_config(self):
        QMessageBox.information(self, "提示", "配置保存功能待实现")

    def _load_config(self):
        QMessageBox.information(self, "提示", "配置加载功能待实现")

    def _show_about(self):
        QMessageBox.about(
            self,
            "关于",
            "光纤FP超声成像系统 v1.0\n\n"
            "集成FP解调和二维扫描采集功能"
        )

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "确认退出",
            "确定要退出程序吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.demod_panel.cleanup()
            self.scan_panel.cleanup()
            event.accept()
        else:
            event.ignore()
