"""
激光器工作线程 - ITF扫描和PID锁定
"""

from PyQt5.QtCore import QThread, pyqtSignal
import numpy as np
import time


class LaserScanWorker(QThread):
    """ITF扫描工作线程"""

    finished = pyqtSignal(bool)  # success

    def __init__(self, system):
        super().__init__()
        self.system = system

    def run(self):
        try:
            print(f"[LaserScanWorker] 开始扫描: {self.system.scan_start} -> {self.system.scan_stop} nm")
            print(f"[LaserScanWorker] 扫描速度: {self.system.scan_speed} nm/s")

            self.system.do_sweep()

            # 检查结果
            if self.system._scan_wl is not None and self.system._scan_v is not None:
                print(f"[LaserScanWorker] 扫描成功: {len(self.system._scan_wl)} 点")
                print(f"[LaserScanWorker] 电压范围: {self.system._scan_v.min():.6f} ~ {self.system._scan_v.max():.6f} V")
                if hasattr(self.system, "get_scan_info"):
                    info = self.system.get_scan_info()
                    print(
                        "[LaserScanWorker] PFI触发: "
                        f"{info['received_triggers']}/{info['expected_triggers']} 次, "
                        f"每次 {info['samples_per_trigger']} 点"
                    )
                self.finished.emit(True)
            else:
                print("[LaserScanWorker] 扫描失败: 无数据")
                self.finished.emit(False)
        except Exception as e:
            print(f"[LaserScanWorker] 扫描异常: {e}")
            import traceback
            traceback.print_exc()
            self.finished.emit(False)


class LockWorker(QThread):
    """PID锁定状态更新线程

    根据误差大小动态调整更新频率：
    - 误差 > 0.1V：快速更新（0.5s一次）
    - 误差 ≤ 0.1V：慢速更新（5s一次）
    """

    data_update = pyqtSignal(dict)

    def __init__(self, system):
        super().__init__()
        self.system = system
        self._running = True
        self.error_threshold = 0.1  # V
        self.fast_interval = 0.5    # s
        self.slow_interval = 5.0    # s

    def run(self):
        while self._running:
            try:
                status = self.system.get_status()
                if status:
                    self.data_update.emit(status)

                    # 根据误差大小调整更新频率
                    raw_error = status.get('error')
                    try:
                        error = abs(float(raw_error))
                    except Exception:
                        error = None
                    message = status.get("message") or ""
                    acquiring = any(
                        text in message
                        for text in ("正在", "捕获", "对准", "检查", "确认")
                    )

                    if not status.get("running", True):
                        self._running = False
                    elif not acquiring and error is not None and np.isfinite(error) and error <= self.error_threshold:
                        # 误差小，慢速更新
                        time.sleep(self.slow_interval)
                    else:
                        # 误差大，快速更新
                        time.sleep(self.fast_interval)
                else:
                    time.sleep(self.fast_interval)
            except Exception as e:
                print(f"[LockWorker] 状态更新异常: {e}")
                time.sleep(self.fast_interval)

    def stop(self):
        self._running = False
