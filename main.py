"""
光纤FP超声成像系统 - 程序入口
"""

import sys
import os

# 项目自身模块必须优先于外部硬件脚本，避免同名旧文件覆盖新版逻辑。
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR in sys.path:
    sys.path.remove(APP_DIR)
sys.path.insert(0, APP_DIR)

# 配置matplotlib中文字体和Qt后端
import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'KaiTi', 'FangSong']
plt.rcParams['axes.unicode_minus'] = False

import PyQt5
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from main_window import MainWindow
from ui_theme import THEME_QSS
from hardware_paths import configure_hardware_paths


def _fix_qt_plugin_path():
    """避免中文路径/环境变量导致找不到 windows 平台插件。"""
    plugins = os.path.join(os.path.dirname(PyQt5.__file__), "Qt5", "plugins")
    platforms = os.path.join(plugins, "platforms")
    if os.path.isdir(platforms):
        os.environ["QT_PLUGIN_PATH"] = plugins
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = platforms


def main():
    _fix_qt_plugin_path()
    configure_hardware_paths()

    # 设置高DPI支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei UI", 10))

    app.setStyleSheet(THEME_QSS)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
