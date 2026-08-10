import sys
import time
import threading
from collections import deque
from enum import Enum

import numpy as np
import serial

import config

sys.path.append(r"C:\Program Files (x86)\ART Technology\ART-DAQ\Samples\Python\LIB")
import artdaq


class State(Enum):
    IDLE = "idle"
    INIT = "init"
    SWEEP = "sweep"
    SET = "set"
    LOCK = "lock"


class TLB8800:
    def __init__(self, port="COM3", baudrate=config.LASER_BAUDRATE):
        self.ser = serial.Serial(port, baudrate, timeout=2)
        time.sleep(0.5)
        self.ser.read_all()

    def send(self, cmd: str) -> str:
        self.ser.write((cmd + "\n").encode())
        time.sleep(0.05)
        return self.ser.read_all().decode(errors="ignore").strip()

    def query(self, cmd: str) -> str:
        self.ser.write((cmd + "\n").encode())
        time.sleep(0.1)
        return self.ser.read_all().decode(errors="ignore").strip()

    def init(self):
        self.send("int 0")
        time.sleep(0.5)
        self.send("pwr 10.00")
        time.sleep(0.3)
        self.send("laz 1")
        time.sleep(3)

    def get_wavelength(self):
        try:
            return float(self.query("wav?"))
        except Exception:
            return None

    def set_wavelength(self, wl_nm: float):
        self.send("wav {:.3f}".format(float(wl_nm)))

    def setup_sweep(self, start_nm: float, stop_nm: float, speed_nm_s: float):
        self.send("str {:.3f}".format(float(start_nm)))
        self.send("stop {:.3f}".format(float(stop_nm)))
        self.send("spd {}".format(int(speed_nm_s)))
        self.send("mode 2")
        self.send("num 1")

    def start_sweep(self):
        self.send("scan")

    def close(self):
        try:
            self.send("laz 0")
        except Exception:
            pass
        try:
            self.ser.close()
        except Exception:
            pass


class DAQReader:
    def __init__(self, device="Dev1", channel="ai7", sample_rate=config.ITF_SAMPLE_RATE):
        self.channel_str = "{}/{}".format(device, channel)
        self.sample_rate = float(sample_rate)

    def read_finite(self, num_samples: int, timeout: float = 10.0) -> np.ndarray:
        num_samples = int(num_samples)
        if num_samples <= 0:
            return np.array([], dtype=float)

        with artdaq.Task() as task:
            task.ai_channels.add_ai_voltage_chan(
                self.channel_str,
                terminal_config=artdaq.constants.TerminalConfiguration.RSE,
            )
            task.timing.cfg_samp_clk_timing(
                rate=float(self.sample_rate),
                sample_mode=artdaq.constants.AcquisitionType.FINITE,
                samps_per_chan=num_samples,
            )
            data = task.read(
                number_of_samples_per_channel=num_samples,
                timeout=float(timeout),
            )
        return np.asarray(data, dtype=float)


class PID:
    def __init__(
        self,
        kp=config.PID_KP,
        ki=config.PID_KI,
        kd=config.PID_KD,
        output_limit=config.PID_OUTPUT_LIMIT,
    ):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.output_limit = float(output_limit)
        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_time = None
        self._integral_limit = 1.0

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_time = None

    def update(self, error: float, slope_v_per_nm: float) -> float:
        now = time.time()
        dt = 0.1 if self._prev_time is None else max(now - self._prev_time, 0.01)

        self._integral += float(error) * dt
        self._integral = float(np.clip(self._integral, -self._integral_limit, self._integral_limit))
        derivative = (float(error) - self._prev_error) / dt
        output_v = self.kp * float(error) + self.ki * self._integral + self.kd * derivative

        slope = float(slope_v_per_nm)
        wl_adjust = output_v / slope if abs(slope) > 1e-12 else 0.0
        wl_adjust = float(np.clip(wl_adjust, -self.output_limit, self.output_limit))

        self._prev_error = float(error)
        self._prev_time = now
        return wl_adjust


class FPWorkPointStabilizerPFI:
    def __init__(self, laser_port="COM3"):
        self.laser = TLB8800(laser_port)
        self.daq = DAQReader()
        self.pid = PID(kp=0.6, ki=0.08, kd=0.0, output_limit=config.PID_OUTPUT_LIMIT)

        self.scan_start = config.ITF_SCAN_START
        self.scan_stop = config.ITF_SCAN_STOP
        self.scan_speed = config.ITF_SCAN_SPEED
        self.sample_rate = config.ITF_SAMPLE_RATE
        self.daq.sample_rate = self.sample_rate

        self.trigger_source = None
        self.trigger_edge = "rising"
        self.trigger_spacing_nm = config.ITF_TRIGGER_SPACING
        self.samples_per_trigger = config.ITF_SAMPLES_PER_TRIGGER
        self.trigger_timeout_s = 1.5
        self.first_read_timeout_s = 5.0
        self.fallback_on_trigger_fail = True

        self.wp_savgol_window = 7
        self.wp_savgol_poly = 2
        self.wp_extrema_n = 2
        self.wp_refine_radius = 3
        self.wp_min_peak_distance = 5
        self.wp_min_contrast = 0.003
        self.wp_min_span_nm = 0.03
        self.wp_linearity_min = 0.75

        self.lock_sample_count = 1000
        self.lock_read_timeout_s = 2.0
        self.lock_interval_s = 3.0
        self.lock_use_median = True
        self.lock_max_error_v = 0.20
        self.lock_lost_limit = 5
        self.lock_range_nm = 0.30
        self.lock_min_abs_slope = 1e-4

        self.workpoint_wl = 0.0
        self.workpoint_v = 0.0
        self.workpoint_slope = 0.0
        self.workpoint_mode = "auto"

        self.state = State.IDLE
        self._running = False
        self._lock_thread = None
        self._scan_wl = None
        self._scan_v = None
        self._scan_expected_triggers = 0
        self._scan_received_triggers = 0
        self._scan_samples_per_trigger = 0
        self._scan_timeout_count = 0
        self._status_lock = threading.Lock()
        self._last_status = None

        self.log = {
            "time": deque(maxlen=10000),
            "voltage": deque(maxlen=10000),
            "wavelength": deque(maxlen=10000),
            "error": deque(maxlen=10000),
        }

    def _publish_status(self, voltage=None, wavelength=None, error=None, message=""):
        status = {
            "state": self.state.value,
            "voltage": voltage,
            "wavelength": wavelength,
            "error": error,
            "target_v": self.workpoint_v,
            "target_wl": self.workpoint_wl,
            "slope": self.workpoint_slope,
            "lock_range_nm": self.lock_range_nm,
            "message": message,
            "running": bool(self._running),
            "time": time.time(),
        }
        with self._status_lock:
            self._last_status = status
        return status

    def _append_lock_sample(self, voltage, wavelength, error):
        values = (voltage, wavelength, error)
        if not all(np.isfinite(float(value)) for value in values):
            return
        self.log["time"].append(time.time())
        self.log["voltage"].append(float(voltage))
        self.log["wavelength"].append(float(wavelength))
        self.log["error"].append(float(error))

    def do_init(self):
        self.state = State.INIT
        self.laser.init()
        self.state = State.IDLE

    def set_laser_power(self, power_mw: float):
        self.laser.send("pwr {:.2f}".format(float(power_mw)))
        time.sleep(0.1)

    def get_laser_power(self):
        try:
            resp = self.laser.query("pwr?")
            if not resp:
                return None
            for token in str(resp).replace(",", " ").replace("=", " ").split():
                try:
                    return float(token)
                except Exception:
                    continue
        except Exception:
            return None
        return None

    def _trigger_line(self):
        return self.trigger_source or "PFI0"

    def _edge_const(self):
        if str(self.trigger_edge).lower() in ("falling", "f", "neg"):
            return artdaq.constants.Edge.FALLING
        return artdaq.constants.Edge.RISING

    def _safe_samples_per_trigger(self):
        trig_period_s = abs(float(self.trigger_spacing_nm) / float(self.scan_speed))
        if trig_period_s <= 0:
            return int(self.samples_per_trigger)
        return max(10, int(float(self.sample_rate) * trig_period_s * 0.8))

    def _read_triggered_median_spectrum(self, trigger_count):
        medians = []
        timeout_count = 0
        with artdaq.Task() as task:
            task.ai_channels.add_ai_voltage_chan(
                self.daq.channel_str,
                terminal_config=artdaq.constants.TerminalConfiguration.RSE,
            )
            task.timing.cfg_samp_clk_timing(
                rate=float(self.sample_rate),
                sample_mode=artdaq.constants.AcquisitionType.FINITE,
                samps_per_chan=int(self.samples_per_trigger),
            )
            task.triggers.start_trigger.cfg_dig_edge_start_trig(
                self._trigger_line(),
                trigger_edge=self._edge_const(),
            )
            task.triggers.start_trigger.retriggerable = 1
            task.start()

            period_s = abs(float(self.trigger_spacing_nm) / float(self.scan_speed))
            timeout_each = max(1.0, 3.0 * period_s)
            self.laser.start_sweep()
            for i in range(int(trigger_count)):
                read_timeout = max(self.first_read_timeout_s, timeout_each) if i == 0 else max(self.trigger_timeout_s, timeout_each)
                try:
                    block = task.read(
                        number_of_samples_per_channel=int(self.samples_per_trigger),
                        timeout=float(read_timeout),
                    )
                    medians.append(float(np.median(np.asarray(block, dtype=float))))
                except Exception:
                    timeout_count += 1
                    if timeout_count >= 8:
                        break
        return np.asarray(medians, dtype=float), timeout_count

    def do_sweep(self):
        self.state = State.SWEEP
        sweep_range = float(self.scan_stop - self.scan_start)
        if sweep_range == 0:
            self.state = State.IDLE
            return

        self.daq.sample_rate = float(self.sample_rate)
        safe_n = self._safe_samples_per_trigger()
        if self.samples_per_trigger > safe_n:
            self.samples_per_trigger = safe_n
        self._scan_wl = None
        self._scan_v = None
        self._scan_samples_per_trigger = int(self.samples_per_trigger)
        self._scan_received_triggers = 0
        self._scan_timeout_count = 0

        self.laser.setup_sweep(self.scan_start, self.scan_stop, self.scan_speed)
        time.sleep(0.2)
        try:
            self.laser.send("trpol 1")
            self.laser.send("traen 1")
        except Exception:
            pass

        trigger_count = int(abs(sweep_range) / float(self.trigger_spacing_nm)) + 1
        self._scan_expected_triggers = int(trigger_count)
        v, timeout_count = self._read_triggered_median_spectrum(trigger_count)
        self._scan_received_triggers = int(v.size)
        self._scan_timeout_count = int(timeout_count)
        if v.size < 20:
            self.state = State.IDLE
            return

        self._scan_wl = np.linspace(float(self.scan_start), float(self.scan_stop), v.size)
        self._scan_v = v
        self.state = State.IDLE

    def get_scan_info(self):
        return {
            "expected_triggers": int(self._scan_expected_triggers),
            "received_triggers": int(self._scan_received_triggers),
            "samples_per_trigger": int(self._scan_samples_per_trigger),
            "timeout_count": int(self._scan_timeout_count),
            "sample_points": 0 if self._scan_v is None else int(self._scan_v.size),
        }

    def _find_extrema(self, y: np.ndarray, n: int, y_raw: np.ndarray = None):
        y = np.asarray(y, dtype=float)
        y_raw = y if y_raw is None else np.asarray(y_raw, dtype=float)
        n = max(1, int(n))
        dy = np.diff(y)
        peaks, valleys = [], []
        for i in range(n, y.size - n):
            if dy[i - 1] > 0 and dy[i] <= 0:
                peaks.append(i)
            if dy[i - 1] < 0 and dy[i] >= 0:
                valleys.append(i)

        def refine(indices, mode):
            refined = []
            radius = max(1, int(self.wp_refine_radius))
            for idx in indices:
                i1 = max(0, idx - radius)
                i2 = min(y_raw.size - 1, idx + radius)
                window = y_raw[i1 : i2 + 1]
                if window.size == 0:
                    continue
                refined.append(i1 + int(np.argmax(window) if mode == "peak" else np.argmin(window)))
            if not refined:
                return np.array([], dtype=int)
            refined = np.array(sorted(set(refined)), dtype=int)
            kept = []
            min_dist = max(1, int(self.wp_min_peak_distance))
            for idx in refined:
                if not kept or int(idx) - kept[-1] >= min_dist:
                    kept.append(int(idx))
            return np.asarray(kept, dtype=int)

        return refine(peaks, "peak"), refine(valleys, "valley")

    def _smooth_scan(self, v: np.ndarray):
        win = int(self.wp_savgol_window)
        if win % 2 == 0:
            win += 1
        win = min(win, v.size - (1 - v.size % 2))
        if win < 5:
            return v.copy()
        try:
            from scipy.signal import savgol_filter

            return np.asarray(
                savgol_filter(v, window_length=win, polyorder=min(int(self.wp_savgol_poly), win - 2), mode="interp"),
                dtype=float,
            )
        except Exception:
            kernel = np.ones(win, dtype=float) / float(win)
            return np.convolve(v, kernel, mode="same")

    def set_workpoint_auto(self):
        if self._scan_wl is None or self._scan_v is None:
            return

        wl0 = np.asarray(self._scan_wl, dtype=float)
        v0 = np.asarray(self._scan_v, dtype=float)
        valid = np.isfinite(wl0) & np.isfinite(v0)
        wl0 = wl0[valid]
        v0 = v0[valid]
        if wl0.size != v0.size or wl0.size < 20:
            return

        order = np.argsort(wl0)
        wl_u = wl0[order]
        v_u = v0[order]
        v_s = self._smooth_scan(v_u)

        peaks, valleys = self._find_extrema(v_s, self.wp_extrema_n, y_raw=v_u)
        extrema = [(int(i), "peak") for i in peaks] + [(int(i), "valley") for i in valleys]
        extrema.sort(key=lambda item: item[0])
        candidates = []

        for (i1, t1), (i2, t2) in zip(extrema[:-1], extrema[1:]):
            if t1 == t2:
                continue
            s, e = (i1, i2) if i1 < i2 else (i2, i1)
            if e - s < 3:
                continue
            seg_wl = wl_u[s : e + 1]
            seg_v = v_s[s : e + 1]
            span = abs(float(seg_wl[-1] - seg_wl[0]))
            contrast = abs(float(v_s[i2] - v_s[i1]))
            if span < float(self.wp_min_span_nm) or contrast < float(self.wp_min_contrast):
                continue
            try:
                slope, intercept = np.polyfit(seg_wl, seg_v, 1)
            except Exception:
                continue
            corr = np.corrcoef(seg_wl, seg_v)[0, 1]
            linearity = abs(float(corr)) if np.isfinite(corr) else 0.0
            if linearity < float(self.wp_linearity_min):
                continue

            work_v = 0.5 * float(min(v_s[i1], v_s[i2]) + max(v_s[i1], v_s[i2]))
            work_wl = float((work_v - intercept) / slope)
            work_wl = float(np.clip(work_wl, min(float(seg_wl[0]), float(seg_wl[-1])), max(float(seg_wl[0]), float(seg_wl[-1]))))
            candidates.append(
                {
                    "score": abs(float(slope)),
                    "slope": float(slope),
                    "work_v": work_v,
                    "work_wl": work_wl,
                    "span": span,
                    "contrast": contrast,
                    "linearity": linearity,
                }
            )

        if not candidates:
            return

        best = max(candidates, key=lambda c: (c["score"], c["contrast"], c["linearity"]))
        self.workpoint_wl = float(best["work_wl"])
        self.workpoint_v = float(best["work_v"])
        self.workpoint_slope = float(best["slope"])
        self.lock_range_nm = max(0.05, 0.45 * float(best["span"]))
        self.workpoint_mode = "auto"
        self.state = State.SET

    def set_workpoint_manual(self, target_v: float):
        if self._scan_wl is None or self._scan_v is None:
            return
        wl = np.asarray(self._scan_wl, dtype=float)
        v = np.asarray(self._scan_v, dtype=float)
        idx = int(np.argmin(np.abs(v - float(target_v))))
        i1 = max(0, idx - 5)
        i2 = min(v.size - 1, idx + 5)
        slope = 0.0 if i2 <= i1 else float((v[i2] - v[i1]) / (wl[i2] - wl[i1] + 1e-12))
        self.workpoint_wl = float(wl[idx])
        self.workpoint_v = float(target_v)
        self.workpoint_slope = slope
        self.lock_range_nm = 0.30
        self.workpoint_mode = "voltage"
        self.state = State.SET

    def set_workpoint_manual_wavelength(self, target_wl: float):
        if self._scan_wl is None or self._scan_v is None:
            return
        wl = np.asarray(self._scan_wl, dtype=float)
        v = np.asarray(self._scan_v, dtype=float)
        idx = int(np.argmin(np.abs(wl - float(target_wl))))
        i1 = max(0, idx - 5)
        i2 = min(v.size - 1, idx + 5)
        slope = 0.0 if i2 <= i1 else float(
            (v[i2] - v[i1]) / (wl[i2] - wl[i1] + 1e-12)
        )
        self.workpoint_wl = float(wl[idx])
        self.workpoint_v = float(v[idx])
        self.workpoint_slope = slope
        self.lock_range_nm = 0.30
        self.workpoint_mode = "wavelength"
        self.state = State.SET

    def _read_monitor_lock_voltage(self):
        data = self.daq.read_finite(int(self.lock_sample_count), timeout=float(self.lock_read_timeout_s))
        data = np.asarray(data, dtype=float)
        data = data[np.isfinite(data)]
        if data.size == 0:
            return float("nan")
        return float(np.median(data) if self.lock_use_median else np.mean(data))

    def start_lock(self):
        if self.workpoint_wl == 0:
            return False
        self.pid.reset()
        self._running = True
        self.state = State.LOCK
        self._publish_status(
            wavelength=self.workpoint_wl,
            message="正在移动到工作点，等待激光器稳定",
        )
        self._lock_thread = threading.Thread(target=self._lock_loop, daemon=True)
        self._lock_thread.start()
        return True

    def stop_lock(self):
        self._running = False
        if self._lock_thread:
            self._lock_thread.join(timeout=2)
            self._lock_thread = None
        self.state = State.IDLE
        self._publish_status(message="锁定已停止")

    def _lock_loop(self):
        lost_count = 0
        self.daq.sample_rate = float(self.sample_rate)
        if abs(float(self.workpoint_slope)) < float(self.lock_min_abs_slope):
            self._running = False
            self.state = State.IDLE
            self._publish_status(
                wavelength=self.workpoint_wl,
                message="工作点斜率太小，无法锁定",
            )
            return

        try:
            nominal_wl = round(float(self.workpoint_wl), 3)
            self.laser.set_wavelength(nominal_wl)
            self._publish_status(
                wavelength=nominal_wl,
                message="已发送工作点波长，等待稳定",
            )
            time.sleep(2.0)
            if not self._running:
                return

            initial_v = self._read_monitor_lock_voltage()
            current_wl = self.laser.get_wavelength()
            if current_wl is None or not np.isfinite(initial_v):
                raise RuntimeError("无法读取稳定后的Monitor电压或当前波长")

            scan_target_v = float(self.workpoint_v)
            initial_error = float(scan_target_v - initial_v)
            if self.workpoint_mode != "voltage":
                # 扫频时的电压会受触发/响应延迟影响；静态锁定应以同一波长
                # 稳定后的Monitor中位数为参考，避免启动时产生虚假的大误差。
                self.workpoint_v = float(initial_v)
                initial_error = 0.0
                message = (
                    "静态参考已校准，"
                    f"扫描与静态电压差 {scan_target_v - initial_v:+.6f} V"
                )
            else:
                message = "保留手动目标电压，开始PID锁定"

            self.pid.reset()
            self._append_lock_sample(initial_v, current_wl, initial_error)
            self._publish_status(
                voltage=float(initial_v),
                wavelength=float(current_wl),
                error=float(initial_error),
                message=message,
            )
        except Exception as exc:
            self._running = False
            self.state = State.IDLE
            self._publish_status(
                wavelength=self.workpoint_wl,
                message=f"锁定初始化失败: {exc}",
            )
            return

        while self._running:
            try:
                current_v = self._read_monitor_lock_voltage()
                current_wl = self.laser.get_wavelength()
                if current_wl is None or not np.isfinite(current_v):
                    lost_count += 1
                    self._publish_status(
                        voltage=None if not np.isfinite(current_v) else float(current_v),
                        wavelength=current_wl,
                        error=None,
                        message=f"锁定读数异常 {lost_count}/{int(self.lock_lost_limit)}",
                    )
                    if lost_count >= int(self.lock_lost_limit):
                        self._running = False
                        self.state = State.IDLE
                        self._publish_status(message="连续读数异常，已停止锁定")
                        break
                    time.sleep(float(self.lock_interval_s))
                    continue

                error = float(self.workpoint_v - current_v)
                error_is_large = abs(error) > float(self.lock_max_error_v)
                lost_count = 0

                if error_is_large:
                    # Large initial errors still need a bounded correction. Resetting the
                    # integral prevents windup while the wavelength moves back gradually.
                    self.pid.reset()
                wl_adj = self.pid.update(error, self.workpoint_slope)
                new_wl = float(np.clip(float(current_wl) + wl_adj, self.workpoint_wl - self.lock_range_nm, self.workpoint_wl + self.lock_range_nm))
                self.laser.set_wavelength(new_wl)

                self._append_lock_sample(current_v, new_wl, error)
                self._publish_status(
                    voltage=float(current_v),
                    wavelength=float(new_wl),
                    error=float(error),
                    message="误差偏大，正在限步拉回" if error_is_large else "锁定调节中",
                )
            except Exception as exc:
                lost_count += 1
                self._publish_status(message=f"锁定循环异常: {exc}")
                if lost_count >= int(self.lock_lost_limit):
                    self._running = False
                    self.state = State.IDLE
                    self._publish_status(message="锁定异常次数过多，已停止")
                    break
            time.sleep(float(self.lock_interval_s))

    def get_status(self):
        with self._status_lock:
            if self._last_status is not None:
                return dict(self._last_status)
        if len(self.log["voltage"]) == 0:
            return None
        return {
            "state": self.state.value,
            "voltage": self.log["voltage"][-1],
            "wavelength": self.log["wavelength"][-1],
            "error": self.log["error"][-1],
            "target_v": self.workpoint_v,
            "target_wl": self.workpoint_wl,
            "slope": self.workpoint_slope,
            "lock_range_nm": self.lock_range_nm,
            "message": "",
            "running": bool(self._running),
        }

    def shutdown(self):
        self.stop_lock()
        self.laser.close()
