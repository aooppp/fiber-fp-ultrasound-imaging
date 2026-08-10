"""
光纤超声成像系统 - 配置管理
"""

# 激光器配置
LASER_PORT = 'COM3'
LASER_BAUDRATE = 115200

# ITF扫描参数
ITF_SCAN_START = 1540.0       # nm
ITF_SCAN_STOP = 1560.0        # nm
ITF_SCAN_SPEED = 10.0         # nm/s
ITF_SAMPLE_RATE = 10000.0     # S/s
ITF_TRIGGER_SPACING = 0.1    # nm
ITF_SAMPLES_PER_TRIGGER = 1000

# PID参数
PID_KP = 2.0
PID_KI = 0.5
PID_KD = 0.1
PID_OUTPUT_LIMIT = 0.002     # nm

# 位移台配置
STAGE_PORT = 'COM4'
STAGE_BAUDRATE = 19200
STAGE_PITCH_X = 2.0           # X轴丝杠导程 (mm)
STAGE_PITCH_Y = 2.0           # Y轴丝杠导程 (mm)
STAGE_STEPS_REV = 1600        # 每转脉冲数（与原始扫描程序一致）

# 扫描参数
SCAN_X_START = 0.0           # mm
SCAN_X_STOP = 50.0           # mm
SCAN_X_STEP = 0.5            # mm
SCAN_Y_START = 0.0           # mm
SCAN_Y_STOP = 50.0           # mm
SCAN_Y_STEP = 0.5            # mm
SCAN_SPEED = 5.0             # mm/s
SCAN_INIT_SPEED = 2.0        # mm/s
SCAN_ACC = 10.0              # mm/s²
SCAN_SETTLE_TIME = 0.1       # s

# 采集卡配置
DAQ_DEVICE = 'DEV2'
DAQ_CHANNEL = '0'
DAQ_SAMPLE_RATE = 100000000.0  # PCIe8526常用100 MS/s
DAQ_MAX_SAMPLE_RATE = 125000000.0  # PCIe8526每通道最高125 MS/s
DAQ_SAMPLE_LENGTH = 1024
DAQ_RANGE = 1                 # ±1V
DAQ_COUPLING = 0              # DC
DAQ_IMPEDANCE = 1             # 50Ω
DAQ_TRIGGER_SOURCE = 'DTR'
DAQ_TRIGGER_LEVEL = 1.0       # V，仅 ATR/CHx 模拟边沿触发有效
DAQ_TRIGGER_SLOPE = 1         # 0=下降沿，1=上升沿
DAQ_TRIGGER_COUPLING = 0      # DC
DAQ_TRIGGER_SENSITIVITY = 50  # DTR灵敏度，按ART-SCOPE驱动原值传递
DAQ_TIMEOUT = 10.0            # s
DAQ_AVG_COUNT = 1
# 当前ART-SCOPE Python封装返回mV；程序显示和保存统一使用V。
DAQ_DRIVER_SCALE_TO_V = 0.001

# 数据保存
SAVE_DIR = 'scan_data'
AUTO_SAVE_INTERVAL = 10
