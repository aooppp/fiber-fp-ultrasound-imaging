# Legacy theme backup (pre light-precision redesign).
# To restore: copy THEME_QSS and style_figure back into ui_theme.py,
# or point main.py to: from ui_theme_legacy import THEME_QSS

THEME_QSS = """
* {
    font-family: "Microsoft YaHei UI", "PingFang SC", "Segoe UI", sans-serif;
    font-size: 13px;
    color: #1d1d1f;
}

QWidget {
    background: #edf4f3;
}

QMainWindow, QWidget#AppRoot {
    background: #edf4f3;
}

QMenuBar {
    background: #f5faf9;
    color: #1d1d1f;
    border-bottom: 1px solid #e1e1e6;
    padding: 5px 10px;
}

QMenuBar::item {
    padding: 7px 12px;
    border-radius: 7px;
}

QMenuBar::item:selected {
    background: #dcefeb;
}

QMenu {
    background: #ffffff;
    border: 1px solid #d9dde5;
    padding: 6px;
}

QMenu::item {
    padding: 8px 26px 8px 12px;
    border-radius: 7px;
}

QMenu::item:selected {
    background: #e2f3ef;
    color: #0d9488;
}

QFrame#TopBar {
    background: #f8fbfa;
    border: 2px solid #1d1d1f;
    border-radius: 14px;
}

QLabel#AppTitle {
    color: #1d1d1f;
    font-size: 28px;
    font-weight: 750;
    letter-spacing: -1px;
}

QLabel#AppSubtitle {
    color: #6e6e73;
    font-size: 13px;
}

QLabel[class="StatusPill"] {
    color: #1d1d1f;
    background: #ffffff;
    border: 2px solid #1d1d1f;
    border-radius: 10px;
    padding: 6px 14px;
    font-weight: 700;
}

QLabel#MascotBadge {
    color: #0d9488;
    background: #ffffff;
    border: 2px solid #1d1d1f;
    border-radius: 22px;
    font-size: 22px;
    font-weight: 800;
}

QFrame#WorkspaceFrame {
    background: #fbfdfc;
    border: 3px solid #1d1d1f;
    border-radius: 14px;
}

QFrame#SideRail {
    background: #eef7f5;
    border-right: 1px solid #d3e4e0;
}

QLabel[class="RailItem"] {
    color: #0f766e;
    background: #ffffff;
    border: 1px solid #d5e3e0;
    border-radius: 10px;
    font-weight: 800;
}

QLabel[class="RailItem"]:hover {
    border-color: #0d9488;
}

QScrollArea {
    background: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background: #fbfdfc;
}

QScrollBar:vertical {
    background: transparent;
    width: 9px;
    margin: 3px 1px;
}

QScrollBar::handle:vertical {
    background: #c9ccd3;
    border-radius: 4px;
    min-height: 32px;
}

QScrollBar::handle:vertical:hover {
    background: #aeb4bd;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QSplitter::handle {
    background: #e4e7ec;
    margin: 10px 8px;
    border-radius: 4px;
}

QSplitter::handle:hover {
    background: #9bd4cc;
}

QGroupBox {
    background: #ffffff;
    border: 1px solid #cfdedb;
    border-radius: 12px;
    margin-top: 22px;
    padding: 22px 18px 18px 18px;
    font-weight: 700;
    color: #1d1d1f;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    top: 1px;
    padding: 0 8px;
    color: #1d1d1f;
    background: #fbfdfc;
}

QLabel {
    color: #424245;
    background: transparent;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {
    background: #f5f7f8;
    color: #1d1d1f;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 8px 11px;
    min-height: 32px;
    selection-background-color: #0071e3;
    selection-color: #ffffff;
}

QTextEdit {
    font-family: "SF Mono", "Cascadia Mono", "Consolas", monospace;
    font-size: 12px;
    line-height: 1.45;
}

QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover, QTextEdit:hover {
    background: #ececf1;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus {
    background: #ffffff;
    border: 1px solid #0d9488;
}

QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
    color: #a1a1a6;
    background: #eeeeef;
}

QComboBox::drop-down {
    border: none;
    width: 28px;
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
    background: #eef1f1;
    color: #1d1d1f;
    border: 1px solid #dddddf;
    border-radius: 8px;
    padding: 8px 15px;
    min-height: 34px;
    font-weight: 650;
}

QPushButton:hover {
    background: #dcdce2;
    border-color: #cfcfd6;
}

QPushButton:pressed {
    background: #d1d1d6;
    padding-top: 9px;
    padding-bottom: 7px;
}

QPushButton:focus {
    border: 1px solid #0d9488;
}

QPushButton:disabled {
    color: #a1a1a6;
    background: #eeeeef;
    border-color: transparent;
}

QPushButton[role="primary"] {
    background: #0d9488;
    color: #ffffff;
    border-color: #0d9488;
}

QPushButton[role="primary"]:hover {
    background: #0faaa0;
    border-color: #0faaa0;
}

QPushButton[role="primary"]:pressed {
    background: #0b7f76;
}

QPushButton[role="danger"] {
    background: #fff0f0;
    color: #b4232a;
    border-color: #ffd3d6;
}

QPushButton[role="danger"]:hover {
    background: #ffe3e5;
}

QProgressBar {
    background: #f2f2f7;
    border: none;
    border-radius: 8px;
    text-align: center;
    color: #424245;
    min-height: 17px;
}

QProgressBar::chunk {
    background: #0d9488;
    border-radius: 8px;
}
"""


def style_figure(fig, ax):
    try:
        import matplotlib.pyplot as plt

        plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Microsoft YaHei UI", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False
    except Exception:
        pass

    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#fbfdfc")
    ax.tick_params(colors="#5f6f6d", labelsize=9)
    ax.xaxis.label.set_color("#424245")
    ax.yaxis.label.set_color("#424245")
    ax.title.set_color("#1d1d1f")
    for spine in ax.spines.values():
        spine.set_color("#cfdedb")
    ax.grid(True, color="#cfdedb", alpha=0.55, linewidth=0.7)
