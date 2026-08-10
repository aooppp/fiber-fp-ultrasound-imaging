"""
浅色精密仪器主题（Light Precision Instrument）。
旧版备份见 ui_theme_legacy.py。
"""

THEME_QSS = """
* {
    font-family: "Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif;
    font-size: 13px;
    color: #1A1D21;
}

QWidget {
    background: #F4F6F8;
}

QMainWindow, QWidget#AppRoot {
    background: #F4F6F8;
}

QMenuBar {
    background: #FFFFFF;
    color: #1A1D21;
    border-bottom: 1px solid #E2E6EB;
    padding: 4px 12px;
}

QMenuBar::item {
    padding: 6px 12px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background: #E8EEF0;
    color: #0F7A72;
}

QMenu {
    background: #FFFFFF;
    border: 1px solid #E2E6EB;
    padding: 4px;
}

QMenu::item {
    padding: 7px 22px 7px 12px;
    border-radius: 4px;
}

QMenu::item:selected {
    background: #E8F3F1;
    color: #0F7A72;
}

/* —— 顶栏 —— */
QFrame#TopBar {
    background: #FFFFFF;
    border: 1px solid #E2E6EB;
    border-radius: 6px;
}

QLabel#AppTitle {
    color: #1A1D21;
    font-size: 18px;
    font-weight: 650;
    letter-spacing: -0.3px;
}

QLabel#AppSubtitle {
    color: #5C6570;
    font-size: 12px;
    letter-spacing: 0.2px;
}

QLabel#BrandMark {
    color: #0F7A72;
    background: #E8F3F1;
    border: 1px solid #C5DED9;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.2px;
    padding: 0 8px;
}

QFrame#MetaStrip {
    background: transparent;
    border: none;
}

QLabel[class="MetaItem"] {
    color: #5C6570;
    background: #F4F6F8;
    border: 1px solid #E2E6EB;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.3px;
}

QLabel[class="MetaItemReady"] {
    color: #0F7A72;
    background: #E8F3F1;
    border: 1px solid #C5DED9;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
}

/* —— 工作区 —— */
QFrame#WorkspaceFrame {
    background: #F4F6F8;
    border: none;
    border-radius: 0;
}

QFrame#ColumnPanel {
    background: #FFFFFF;
    border: 1px solid #E2E6EB;
    border-radius: 6px;
}

QFrame#ColumnHeader {
    background: #FAFBFC;
    border: none;
    border-bottom: 1px solid #E2E6EB;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QLabel#ColumnIndex {
    color: #0F7A72;
    font-family: "Cascadia Mono", "Consolas", "SF Mono", monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
}

QLabel#ColumnTitle {
    color: #1A1D21;
    font-size: 14px;
    font-weight: 650;
}

QLabel#ColumnHint {
    color: #8A939E;
    font-size: 11px;
}

QScrollArea {
    background: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background: #FFFFFF;
}

QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px 1px;
}

QScrollBar::handle:vertical {
    background: #C8CDD4;
    border-radius: 4px;
    min-height: 28px;
}

QScrollBar::handle:vertical:hover {
    background: #A8B0BA;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QSplitter::handle {
    background: #E2E6EB;
    margin: 8px 6px;
    border-radius: 2px;
}

QSplitter::handle:hover {
    background: #0F7A72;
}

/* —— 分组与表单 —— */
QGroupBox {
    background: #FFFFFF;
    border: 1px solid #E2E6EB;
    border-radius: 5px;
    margin-top: 12px;
    padding: 14px 10px 10px 10px;
    font-weight: 600;
    color: #1A1D21;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: 1px;
    padding: 0 5px;
    color: #5C6570;
    background: #FFFFFF;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.3px;
}

QLabel {
    color: #5C6570;
    background: transparent;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {
    background: #F4F6F8;
    color: #1A1D21;
    border: 1px solid #E2E6EB;
    border-radius: 4px;
    padding: 5px 10px;
    min-height: 28px;
    min-width: 72px;
    selection-background-color: #0F7A72;
    selection-color: #ffffff;
}

QTextEdit {
    font-family: "Cascadia Mono", "Consolas", "SF Mono", monospace;
    font-size: 12px;
    line-height: 1.45;
}

QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover, QTextEdit:hover {
    border-color: #C5CDD6;
    background: #EEF1F4;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus {
    background: #FFFFFF;
    border: 1px solid #0F7A72;
}

QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
    color: #A0A8B0;
    background: #EEF0F2;
    border-color: #E8EBEE;
}

QComboBox::drop-down {
    border: none;
    width: 26px;
}

QComboBox::down-arrow {
    image: none;
}

QSpinBox::up-button,
QSpinBox::down-button,
QDoubleSpinBox::up-button,
QDoubleSpinBox::down-button {
    width: 0px;
    border: none;
}

QPushButton {
    background: #F4F6F8;
    color: #1A1D21;
    border: 1px solid #E2E6EB;
    border-radius: 4px;
    padding: 5px 12px;
    min-height: 28px;
    min-width: 56px;
    font-weight: 600;
}

QPushButton:hover {
    background: #E8EEF0;
    border-color: #C5CDD6;
}

QPushButton:pressed {
    background: #DEE4E8;
    padding-top: 8px;
    padding-bottom: 6px;
}

QPushButton:focus {
    border: 1px solid #0F7A72;
}

QPushButton:disabled {
    color: #A0A8B0;
    background: #EEF0F2;
    border-color: #E8EBEE;
}

QPushButton[role="primary"] {
    background: #0F7A72;
    color: #ffffff;
    border-color: #0F7A72;
}

QPushButton[role="primary"]:hover {
    background: #128A81;
    border-color: #128A81;
}

QPushButton[role="primary"]:pressed {
    background: #0C655E;
}

QPushButton[role="danger"] {
    background: #FDF2F2;
    color: #B4232A;
    border-color: #F0D0D2;
}

QPushButton[role="danger"]:hover {
    background: #FAE5E6;
}

QProgressBar {
    background: #EEF1F4;
    border: 1px solid #E2E6EB;
    border-radius: 4px;
    text-align: center;
    color: #5C6570;
    min-height: 16px;
}

QProgressBar::chunk {
    background: #0F7A72;
    border-radius: 3px;
}
"""


def style_figure(fig, ax):
    try:
        import matplotlib.pyplot as plt

        plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Microsoft YaHei UI", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False
    except Exception:
        pass

    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FAFBFC")
    ax.tick_params(colors="#8A939E", labelsize=9)
    ax.xaxis.label.set_color("#5C6570")
    ax.yaxis.label.set_color("#5C6570")
    ax.title.set_color("#1A1D21")
    for spine in ax.spines.values():
        spine.set_color("#E2E6EB")
        spine.set_linewidth(0.8)
    ax.grid(True, color="#E2E6EB", alpha=0.7, linewidth=0.6)
