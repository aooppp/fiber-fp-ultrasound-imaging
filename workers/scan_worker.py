"""
扫描工作线程 - 二维蛇形扫描
"""

from PyQt5.QtCore import QThread, pyqtSignal
import numpy as np
import time
import os
import json
from datetime import datetime
import config


def _driver_data_to_volts(data):
    if data is None:
        return None
    return np.asarray(data, dtype=np.float64) * float(config.DAQ_DRIVER_SCALE_TO_V)


class ScanWorker(QThread):
    """二维扫描工作线程"""

    progress = pyqtSignal(int, int)  # current, total
    waveform = pyqtSignal(object)  # 单次采集波形
    finished = pyqtSignal(object, object)  # data, positions

    def __init__(self, mc600, daq,
                 x_start, x_stop, x_step,
                 y_start, y_stop, y_step,
                 speed=config.SCAN_SPEED, settle_time=config.SCAN_SETTLE_TIME,
                 save_path=None,
                 avg_count=1, sample_length=1024,
                 sample_rate=10000000,
                 steps_rev=config.STAGE_STEPS_REV):
        super().__init__()
        self.mc600 = mc600
        self.daq = daq

        # 扫描参数
        self.x_start = x_start
        self.x_stop = x_stop
        self.x_step = x_step
        self.y_start = y_start
        self.y_stop = y_stop
        self.y_step = y_step
        self.speed = speed
        self.settle_time = settle_time
        self.save_path = save_path
        self.avg_count = avg_count
        self.sample_length = sample_length
        self.sample_rate = sample_rate
        self.steps_rev = steps_rev

        self._running = True

    def run(self):
        try:
            # 生成扫描网格
            x_positions = np.arange(self.x_start, self.x_stop + self.x_step / 2, self.x_step)
            y_positions = np.arange(self.y_start, self.y_stop + self.y_step / 2, self.y_step)
            num_x = len(x_positions)
            num_y = len(y_positions)
            total_positions = num_x * num_y

            # 初始化数据数组
            scan_data = np.zeros((num_x, num_y, self.sample_length))
            scan_positions = np.zeros((num_x, num_y, 2))

            # 配置位移台参数
            self.mc600.setup_axis(
                axis='X',
                pitch=config.STAGE_PITCH_X,
                speed=self.speed,
                init_speed=config.SCAN_INIT_SPEED,
                acc=config.SCAN_ACC,
                unit='m',
                steps_rev=self.steps_rev,
                stage_style='T'
            )
            self.mc600.setup_axis(
                axis='Y',
                pitch=config.STAGE_PITCH_Y,
                speed=self.speed,
                init_speed=config.SCAN_INIT_SPEED,
                acc=config.SCAN_ACC,
                unit='m',
                steps_rev=self.steps_rev,
                stage_style='T'
            )

            # 设置采集卡参数
            self.daq.sample_rate = self.sample_rate
            self.daq.sample_length = self.sample_length

            # 打开采集卡
            if not self.daq.open():
                self.finished.emit(None, None)
                return

            # 生成蛇形路径
            path = []
            for y_idx in range(num_y):
                if y_idx % 2 == 0:
                    x_indices = range(num_x)
                else:
                    x_indices = range(num_x - 1, -1, -1)
                for x_idx in x_indices:
                    path.append((y_idx, x_idx))

            # 开始扫描
            completed = 0
            start_time = time.time()

            for y_idx, x_idx in path:
                if not self._running:
                    break

                x_target = x_positions[x_idx]
                y_target = y_positions[y_idx]

                # 移动到位
                self.mc600.move_absolute('X', x_target)
                self.mc600.wait_for_stop('X', timeout=30)
                self.mc600.move_absolute('Y', y_target)
                self.mc600.wait_for_stop('Y', timeout=30)

                # 等待稳定
                time.sleep(self.settle_time)

                # 采集数据
                data = _driver_data_to_volts(
                    self.daq.read_averaged(avg_count=self.avg_count, timeout=10.0)
                )
                if data is not None:
                    actual_len = min(len(data), self.sample_length)
                    scan_data[x_idx, y_idx, :actual_len] = data[:actual_len]

                    # 发送波形信号（用于实时显示）
                    self.waveform.emit(data)

                # 记录位置
                x_actual = self.mc600.get_position('X')
                y_actual = self.mc600.get_position('Y')
                scan_positions[x_idx, y_idx, 0] = x_actual if x_actual is not None else x_target
                scan_positions[x_idx, y_idx, 1] = y_actual if y_actual is not None else y_target

                completed += 1
                self.progress.emit(completed, total_positions)

            # 关闭采集卡
            if self.daq.is_open:
                self.daq.close()

            # 保存数据
            self._save_data(scan_data, scan_positions)

            self.finished.emit(scan_data, scan_positions)

        except Exception as e:
            print(f"扫描异常: {e}")
            import traceback
            traceback.print_exc()
            self.finished.emit(None, None)

    def stop(self):
        self._running = False

    def _save_data(self, scan_data, scan_positions):
        """保存扫描数据"""
        if self.save_path:
            save_dir = self.save_path
        else:
            save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scan_data')

        os.makedirs(save_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 保存数据
        np.save(os.path.join(save_dir, f'scan_data_{timestamp}.npy'), scan_data)
        np.save(os.path.join(save_dir, f'scan_positions_{timestamp}.npy'), scan_positions)

        # 保存元数据
        meta = {
            'timestamp': timestamp,
            'x_start': self.x_start,
            'x_stop': self.x_stop,
            'x_step': self.x_step,
            'y_start': self.y_start,
            'y_stop': self.y_stop,
            'y_step': self.y_step,
            'speed': self.speed,
            'settle_time': self.settle_time,
            'trigger_source': self.daq.trigger_source,
            'trigger_slope': int(self.daq.trigger_slope),
            'trigger_sensitivity': int(self.daq.trigger_sensitivity),
            'input_range_index': int(self.daq.range_idx),
            'input_range_v': 1.0 if int(self.daq.range_idx) == 1 else 5.0,
            'voltage_unit': 'V',
            'driver_scale_to_v': float(config.DAQ_DRIVER_SCALE_TO_V),
        }
        with open(os.path.join(save_dir, f'scan_meta_{timestamp}.json'), 'w') as f:
            json.dump(meta, f, indent=2)


class TriggerWorker(QThread):
    """纯触发采集工作线程（类似trigger_ch_save_dma.py）"""

    progress = pyqtSignal(int, int)  # current, total
    waveform = pyqtSignal(object)  # 单次采集波形
    finished = pyqtSignal(object, object)  # data, positions

    def __init__(self, daq, groups=500, sample_rate=100000000,
                 sample_length=1024, save_path=None):
        super().__init__()
        self.daq = daq
        self.groups = groups
        self.sample_rate = sample_rate
        self.sample_length = sample_length
        self.save_path = save_path
        self._running = True

    def run(self):
        try:
            # 设置采集卡参数
            self.daq.sample_rate = self.sample_rate
            self.daq.sample_length = self.sample_length
            self.daq.trigger_count = 0  # 重复触发直到停止

            # 打开采集卡
            if not self.daq.open():
                self.finished.emit(None, None)
                return

            actual_len = self.daq.actual_record_length
            num_waveforms = max(1, int(self.daq.num_waveforms))
            total_len = actual_len * num_waveforms

            # 采集阶段保存驱动原始值，结束后一次性换算为伏特。
            all_data = np.empty((self.groups, total_len), dtype=np.float64)
            ok = 0
            t0 = time.time()
            last_ui_update = 0.0
            ui_interval_s = 0.1

            # 开始采集（单次Start，循环Fetch）
            if not self.daq.arm():
                self.daq.close()
                self.finished.emit(None, None)
                return

            fetch_into = getattr(self.daq, "fetch_voltage_into", None)
            try:
                for i in range(self.groups):
                    if not self._running:
                        break

                    if callable(fetch_into):
                        fetched = bool(fetch_into(all_data[ok], timeout=10.0))
                    else:
                        raw = self.daq.fetch_voltage(timeout=10.0)
                        fetched = raw is not None
                        if fetched:
                            raw = np.asarray(raw, dtype=np.float64).reshape(-1)
                            if raw.size < total_len:
                                raise RuntimeError(
                                    f"Fetch返回 {raw.size} 点，少于所需 {total_len} 点"
                                )
                            all_data[ok] = raw[:total_len]

                    if not fetched:
                        print(f"  [{i+1}/{self.groups}] Fetch失败/超时，停止")
                        break

                    ok += 1
                    now = time.perf_counter()
                    update_ui = (
                        ok == 1
                        or ok == self.groups
                        or now - last_ui_update >= ui_interval_s
                    )
                    if update_ui:
                        preview = (
                            all_data[ok - 1, :actual_len].copy()
                            * float(config.DAQ_DRIVER_SCALE_TO_V)
                        )
                        self.waveform.emit(preview)
                        self.progress.emit(ok, self.groups)
                        last_ui_update = now

                    if (i + 1) % max(1, self.groups // 20) == 0 or i == 0:
                        print(f"  [{i+1}/{self.groups}] ok")
            finally:
                self.daq.close()

            t1 = time.time()

            if ok == 0:
                self.finished.emit(None, None)
                return

            # 裁剪有效数据并在采集结束后统一换算为伏特。
            all_data = all_data[:ok]
            np.multiply(
                all_data,
                float(config.DAQ_DRIVER_SCALE_TO_V),
                out=all_data,
            )

            # 确保不足一个UI刷新周期的短采集也显示最终进度与波形。
            self.progress.emit(ok, self.groups)
            self.waveform.emit(all_data[-1, :actual_len].copy())

            # 保存数据
            self._save_data(all_data, ok, t1 - t0)

            self.finished.emit(all_data, None)

        except Exception as e:
            print(f"触发采集异常: {e}")
            import traceback
            traceback.print_exc()
            self.finished.emit(None, None)

    def stop(self):
        self._running = False

    def _save_data(self, data, groups_acquired, elapsed):
        """保存触发采集数据 - 每次触发存一个dat文件（只存电压值）"""
        if self.save_path:
            save_dir = self.save_path
        else:
            save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'trigger_data')

        os.makedirs(save_dir, exist_ok=True)

        # 每次触发存一个dat文件，只存电压值
        for i in range(groups_acquired):
            dat_path = os.path.join(save_dir, f'shot_{i+1:06d}.dat')
            np.savetxt(dat_path, data[i], fmt="%.10e")

        # 保存元数据
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        meta = {
            'timestamp': timestamp,
            'mode': 'trigger_only',
            'groups_requested': self.groups,
            'groups_acquired': groups_acquired,
            'sample_rate': self.sample_rate,
            'sample_length': self.sample_length,
            'actual_record_length': data.shape[1] if len(data.shape) > 1 else 0,
            'elapsed_s': elapsed,
            'groups_per_s': groups_acquired / max(1e-12, elapsed),
            'trigger_source': self.daq.trigger_source,
            'trigger_slope': int(self.daq.trigger_slope),
            'trigger_sensitivity': int(self.daq.trigger_sensitivity),
            'input_range_index': int(self.daq.range_idx),
            'input_range_v': 1.0 if int(self.daq.range_idx) == 1 else 5.0,
            'acquisition_mode': 'FINITE_retrigger_single_start',
            'ui_update_rate_limit_hz': 10.0,
            'voltage_unit': 'V',
            'driver_scale_to_v': float(config.DAQ_DRIVER_SCALE_TO_V),
        }
        with open(os.path.join(save_dir, f'trigger_meta_{timestamp}.json'), 'w') as f:
            json.dump(meta, f, indent=2)

        print(f"已保存 {groups_acquired} 个dat文件到: {save_dir}")
