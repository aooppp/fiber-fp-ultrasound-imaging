"""
阿尔泰 PCIe8526/PCIe8536C 兼容采集卡控制类
基于 ART_SCOPE_Lib SDK
触发方式: 数字/模拟触发（默认DTR外部数字触发）
采集模式: 默认有限采集 (FINITE)；可选连续模式 (CONTINUOUS) 用于「单次 Start、多次 Fetch」的高重频触发序列。
"""

import sys
import ctypes
import numpy as np
import time
import logging

# 添加 ART_SCOPE_Lib 路径
sys.path.append(r'C:\Program Files (x86)\ART Technology\ART-SCOPE\Samples\Python')

from ART_SCOPE_Lib.functions import Functions
from ART_SCOPE_Lib.constants import (
    SampleMode, CouplingType, InputImpedance, BandWidth,
    InputRange, TriggerSource, TriggerSlope, TriggerCoupling,
    ArtScope_wfmInfo, ARTSCOPE_STATUS_AD
)
from ART_SCOPE_Lib.lib import lib_importer
from ART_SCOPE_Lib.errors import check_for_error, ArtScopeError

logger = logging.getLogger(__name__)

# 量程映射表
# PCIe8526 的 AI 模拟输入量程为 ±5V、±1V（对应 10Vpp、2Vpp）。
# 为避免配置到设备不支持的档位，这里仅保留这两档。
RANGE_MAP = {
    0: InputRange.RANGE_10VPP,  # ±5V
    1: InputRange.RANGE_2VPP,   # ±1V
}

COUPLING_MAP = {
    0: CouplingType.DC,
    1: CouplingType.AC,
}

IMPEDANCE_MAP = {
    0: InputImpedance.AI_IMPEND_1M,
    1: InputImpedance.AI_IMPEND_50,
}

# 触发源映射表
TRIGGER_SOURCE_MAP = {
    'ATR': TriggerSource.TRIGSRC_ATR,     # 外部模拟触发(TRIG_IN口)
    'DTR': TriggerSource.TRIGSRC_DTR,     # 外部数字触发
    'CH0': TriggerSource.TRIGSRC_CH0,     # CH0通道触发
    'CH1': TriggerSource.TRIGSRC_CH1,
    'CH2': TriggerSource.TRIGSRC_CH2,
    'CH3': TriggerSource.TRIGSRC_CH3,
    'CH4': TriggerSource.TRIGSRC_CH4,
    'CH5': TriggerSource.TRIGSRC_CH5,
    'CH6': TriggerSource.TRIGSRC_CH6,
    'CH7': TriggerSource.TRIGSRC_CH7,
    'PFI': TriggerSource.TRIGSRC_PFI,     # PFI数字触发
}

# 触发耦合映射
TRIGGER_COUPLING_MAP = {
    0: TriggerCoupling.TRIGCOUP_DC,   # DC
    1: TriggerCoupling.TRIGCOUP_AC,   # AC
    2: TriggerCoupling.TRIGCOUP_HIG,  # HF reject
    3: TriggerCoupling.TRIGCOUP_LOW,  # LF reject
}


class PCIe8536CDAQ:
    """ART-SCOPE 数据采集卡控制类（保留原始类名以兼容旧程序）。"""

    def __init__(self, device_name='DEV2', channel='0',
                 sample_rate=10000000.0, sample_length=1024,
                 range_idx=1, coupling=0, impedance=1,
                 trigger_source='DTR', trigger_level=1.0,
                 trigger_slope=1, trigger_coupling=0,
                 trigger_sensitivity=50,
                 trigger_count=1,
                 timeout=10.0,
                 acquisition_mode='FINITE'):
        """
        参数:
            device_name: 设备名（在阿尔泰DMC中查看）
            channel: 采集通道号，如 '0', '0,1'
            sample_rate: 采样率 (Hz)
            sample_length: 每次触发采集点数
            range_idx: 量程索引（见RANGE_MAP）
            coupling: 耦合 0=DC, 1=AC
            impedance: 阻抗 0=1MΩ, 1=50Ω
            trigger_source: 触发源 'ATR'/'DTR'/'CH0'~'CH7'/'PFI'
            trigger_level: 触发电平 (V)，用于模拟边沿触发
            trigger_slope: 触发边沿 0=下降沿, 1=上升沿
            trigger_coupling: 触发耦合 0=DC, 1=AC, 2=HF reject, 3=LF reject
            trigger_sensitivity: 触发去抖/毛刺过滤灵敏度，按驱动原值传递
            trigger_count: 触发次数。1=单次触发；0=重复触发直到停止（是否支持取决于具体板卡/驱动）
            timeout: 采集超时 (s)
            acquisition_mode: 'FINITE' 或 'CONTINUOUS'（对齐官方 ContinueAcq_* 连续模式）
        """
        self.device_name = device_name
        self.channel = channel
        self.sample_rate = sample_rate
        self.sample_length = sample_length
        self.range_idx = range_idx
        self.coupling = coupling
        self.impedance = impedance
        self.trigger_source = trigger_source
        self.trigger_level = trigger_level
        self.trigger_slope = trigger_slope
        self.trigger_coupling = trigger_coupling
        self.trigger_sensitivity = trigger_sensitivity
        self.trigger_count = int(trigger_count)
        self.timeout = timeout

        am = str(acquisition_mode).upper().strip()
        if am in ('FINITE', 'F', '0'):
            self._sample_mode = SampleMode.FINITE
        elif am in ('CONTINUOUS', 'C', 'CONT', '1'):
            self._sample_mode = SampleMode.CONTINUOUS
        else:
            raise ValueError("acquisition_mode 须为 'FINITE' 或 'CONTINUOUS'")

        self.task_handle = lib_importer.task_handle(0)
        self.is_open = False
        self._actual_record_length = 0
        self._num_wfms = 0

    def open(self):
        """创建采集任务，配置所有参数，返回是否成功"""
        try:
            # 创建任务
            err = Functions.ArtScope_init(self.device_name, self.task_handle)
            if err < 0:
                self._handle_error(err, 'init')
                return False

            # 采集模式：FINITE 或 CONTINUOUS（后者对齐官方 ContinueAcq_IntClk_Trig* 例程）
            err = Functions.ArtScope_ConfigureAcquisitionMode(
                self.task_handle, self._sample_mode
            )
            if err < 0:
                self._handle_error(err, 'acquisition mode')
                return False

            # 设置垂直参数（通道、量程、耦合）
            v_range = RANGE_MAP.get(self.range_idx, InputRange.RANGE_2VPP)
            v_coupling = COUPLING_MAP.get(self.coupling, CouplingType.DC)
            err = Functions.ArtScope_ConfigureVertical(
                self.task_handle, self.channel,
                v_range, 0, v_coupling, 1, 1
            )
            if err < 0:
                self._close_on_error(err, 'vertical')
                return False

            # 设置通道特性（阻抗、带宽）
            imp = IMPEDANCE_MAP.get(self.impedance, InputImpedance.AI_IMPEND_50)
            err = Functions.ArtScope_ConfigureChanCharacteristics(
                self.task_handle, self.channel, imp,
                BandWidth.BANDWIDTH_DEFAULT
            )
            if err < 0:
                self._close_on_error(err, 'channel characteristics')
                return False

            # 设置水平参数（采样率、采集长度）
            err = Functions.ArtScope_ConfigureHorizontalTiming(
                self.task_handle, self.sample_rate,
                self.sample_length, 0
            )
            if err < 0:
                self._close_on_error(err, 'horizontal timing')
                return False

            # 设置触发 — 根据触发源类型选择触发方式
            trig_src = TRIGGER_SOURCE_MAP.get(self.trigger_source, TriggerSource.TRIGSRC_DTR)
            slope = TriggerSlope.TRIGDIR_POSITIVE if self.trigger_slope else TriggerSlope.TRIGDIR_NEGATIVE

            if self.trigger_source == 'SW':
                # 软件触发（无需外部信号，用于测试采集链路）
                err = Functions.ArtScope_ConfigureTriggerSoftWare(self.task_handle)
                if err < 0:
                    self._close_on_error(err, 'trigger software')
                    return False
                logger.info("触发模式: 软件触发 (SW)")
            elif self.trigger_source == 'DTR' or self.trigger_source == 'PFI':
                # 数字触发
                err = Functions.ArtScope_ConfigureTriggerDigital(
                    self.task_handle,
                    trig_src,
                    slope,
                    int(self.trigger_count),
                    int(self.trigger_sensitivity)    # sensitivity（对齐官方示例常用 50）
                )
                if err < 0:
                    self._close_on_error(err, 'trigger digital')
                    return False
                logger.info(
                    f"触发模式: 数字触发 ({self.trigger_source}), "
                    f"{'上升' if self.trigger_slope else '下降'}沿, "
                    f"sensitivity={int(self.trigger_sensitivity)}"
                )
            else:
                # 模拟边沿触发 (ATR, CH0~CH7)
                trig_coup = TRIGGER_COUPLING_MAP.get(
                    self.trigger_coupling, TriggerCoupling.TRIGCOUP_DC
                )
                err = Functions.ArtScope_ConfigureTriggerEdge(
                    self.task_handle,
                    trig_src,
                    self.trigger_level,
                    slope,
                    trig_coup,
                    int(self.trigger_count),
                    int(self.trigger_sensitivity),
                )
                if err < 0:
                    self._close_on_error(err, 'trigger edge')
                    return False
                logger.info(f"触发模式: 模拟边沿触发 ({self.trigger_source}), "
                            f"电平={self.trigger_level}V, "
                            f"{'上升' if self.trigger_slope else '下降'}沿")

            # 获取实际通道数
            num_wfms = ctypes.c_uint32(0)
            err = Functions.ArtScope_ActualNumWfms(self.task_handle, num_wfms)
            if err < 0:
                self._close_on_error(err, 'num wfms')
                return False
            self._num_wfms = num_wfms.value

            # 初始化采集
            err = Functions.ArtScope_InitiateAcquisition(self.task_handle)
            if err < 0:
                self._close_on_error(err, 'initiate')
                return False

            # 获取实际采集长度
            actual_len = ctypes.c_uint32(0)
            err = Functions.ArtScope_ActualRecordLength(self.task_handle, actual_len)
            if err < 0:
                self._close_on_error(err, 'actual record length')
                return False
            self._actual_record_length = actual_len.value

            self.is_open = True
            logger.info(
                f"PCIe8536C 已配置: {self.device_name}, ch={self.channel}, "
                f"mode={'CONTINUOUS' if self._sample_mode == SampleMode.CONTINUOUS else 'FINITE'}, "
                f"rate={self.sample_rate/1e6:.0f}MS/s, "
                f"length={self._actual_record_length}, "
                f"channels={self._num_wfms}"
            )
            return True

        except Exception as e:
            logger.error(f"DAQ open 异常: {e}")
            self.close()
            return False

    def arm(self):
        """准备采集（开始等待触发）"""
        if not self.is_open:
            raise RuntimeError("DAQ未打开")

        err = Functions.ArtScope_StartAcquisition(self.task_handle)
        if err < 0:
            self._handle_error(err, 'start acquisition')
            return False
        return True

    @property
    def actual_record_length(self) -> int:
        """实际采样点数（由驱动返回，可能与请求值不同）。"""
        return int(self._actual_record_length)

    @property
    def num_waveforms(self) -> int:
        """实际波形路数（通道数）。"""
        return int(self._num_wfms)

    def fetch_voltage(self, timeout=None):
        """读取电压数据（等待触发后采集完成）

        返回:
            numpy数组，shape=(num_channels * sample_length,)
            如果单通道则直接是一维数组
        """
        if timeout is None:
            timeout = self.timeout

        total_length = self._actual_record_length * self._num_wfms
        waveform = np.zeros(total_length, dtype=np.double)

        wfm_info = ArtScope_wfmInfo()
        wfm_info.actualSamples = 0
        wfm_info.pAvailSampsPoints = 0

        read_length = ctypes.c_uint32(self._actual_record_length)

        err = Functions.ArtScope_FetchVoltage(
            self.task_handle, timeout,
            read_length, waveform, wfm_info
        )
        if err < 0:
            self._handle_error(err, 'fetch voltage')
            return None

        return waveform

    def fetch_voltage_into(self, destination, timeout=None):
        """将一次触发记录直接读取到预分配的 float64 缓冲区。"""
        if timeout is None:
            timeout = self.timeout

        total_length = self._actual_record_length * self._num_wfms
        waveform = np.asarray(destination)
        if waveform.dtype != np.float64:
            raise TypeError("destination 必须为 float64 数组")
        if not waveform.flags.c_contiguous:
            raise ValueError("destination 必须为连续内存")
        waveform = waveform.reshape(-1)
        if waveform.size < total_length:
            raise ValueError(
                f"destination 长度 {waveform.size} 小于所需长度 {total_length}"
            )

        wfm_info = ArtScope_wfmInfo()
        wfm_info.actualSamples = 0
        wfm_info.pAvailSampsPoints = 0
        read_length = ctypes.c_uint32(self._actual_record_length)

        err = Functions.ArtScope_FetchVoltage(
            self.task_handle,
            timeout,
            read_length,
            waveform,
            wfm_info,
        )
        if err < 0:
            self._handle_error(err, 'fetch voltage into')
            return False
        return True

    def wait_for_complete(self, timeout=None, poll_interval=0.01):
        """轮询采集状态，等待触发与采集完成。

        说明：
        - 手册中 DTR(数字触发) 需要外部 TTL 信号接入 TRIG_IN。
        - 这里用 SDK 的 AcquisitionStatus 明确区分“没触发/没完成/可读点数不足”等情况，
          避免仅凭 Fetch 的错误码猜测。
        """
        if timeout is None:
            timeout = self.timeout

        status = ARTSCOPE_STATUS_AD()
        deadline = time.time() + float(timeout)
        last = None

        while time.time() < deadline:
            err = Functions.ArtScope_AcquisitionStatus(self.task_handle, status)
            if err < 0:
                self._handle_error(err, 'acquisition status')
                return None

            snap = (status.bADEanble, status.bTrigger, status.bComplete, int(status.lCanReadPoint))
            if snap != last:
                logger.info(
                    f"采集状态: enable={status.bADEanble} trigger={status.bTrigger} "
                    f"complete={status.bComplete} canRead={int(status.lCanReadPoint)}"
                )
                last = snap

            # 有限采集：触发后直到完成才可稳定读取
            if status.bComplete == 1:
                return status

            time.sleep(poll_interval)

        logger.error("等待触发/采集完成超时（请重点检查：TRIG_IN 是否为 TTL 数字触发输入、边沿方向、脉宽>20ns）")
        return None

    def read_single(self, timeout=None):
        """单次完整采集流程: arm → 等待触发 → 读取数据
        流程对齐官方示例: StartAcquisition → FetchVoltage → StopAcquisition（便于再次 arm 等下一次触发）

        返回:
            单通道: shape (sample_length,) 的一维数组
            多通道: shape (num_channels * sample_length,) 的一维数组（与 FetchVoltage 缓冲一致）；
                    常见为按采样点交错 [ch0_t0, ch1_t0, ch0_t1, ch1_t1, ...]，可用 reshape(-1, num_channels) 解析

        注意: 仅用于 FINITE 模式。CONTINUOUS 请用 fetch_burst_retrigger。
        """
        if self._sample_mode == SampleMode.CONTINUOUS:
            logger.error("read_single 不用于 CONTINUOUS 模式，请改用 fetch_burst_retrigger")
            return None

        if not self.arm():
            return None

        # 软件触发：手动发送触发信号
        if self.trigger_source == 'SW':
            time.sleep(0.01)
            err = Functions.ArtScope_SendSoftwareTrigger(self.task_handle)
            if err < 0:
                self._handle_error(err, 'send software trigger')
                return None

        # 直接用FetchVoltage等待触发并读取（对齐官方示例）
        if timeout is None:
            timeout = self.timeout

        total_length = self._actual_record_length * self._num_wfms
        waveform = np.zeros(total_length, dtype=np.double)
        wfm_info = ArtScope_wfmInfo()
        wfm_info.actualSamples = 0
        wfm_info.pAvailSampsPoints = 0
        read_length = ctypes.c_uint32(self._actual_record_length)

        err = Functions.ArtScope_FetchVoltage(
            self.task_handle, timeout,
            read_length, waveform, wfm_info
        )
        if err < 0:
            self._handle_error(err, 'fetch voltage')
            return None

        out = waveform[:total_length].copy()

        # 官方有限采集示例在 Fetch 成功后调用 Stop，便于连续多次触发采集
        if self._sample_mode == SampleMode.FINITE:
            try:
                Functions.ArtScope_StopAcquisition(self.task_handle)
            except Exception as e:
                logger.warning(f"StopAcquisition: {e}")

        if self._num_wfms == 1:
            return out
        return out

    def fetch_burst_retrigger(self, n_shots: int, timeout=None, sw_trigger_each_shot: bool = False):
        """连续采集模式下一次 Start、多次 Fetch（对齐官方 ContinueAcq_IntClk_Trig*）。

        用于外部触发重复频率较高时，避免「每段 FINITE + Stop/Start」带来的毫秒级死区。

        前置: open() 时 acquisition_mode='CONTINUOUS'。

        参数:
            n_shots: 连续读取的触发次数（每次 Fetch 对应一次触发后的 record_length）
            timeout: 单次 Fetch 超时 (s)
            sw_trigger_each_shot: 若为 True 且 trigger_source=='SW'，每次 Fetch 前发送软件触发

        返回:
            list[np.ndarray]，长度 n_shots；每个元素 shape (num_channels * record_length,) 与 FetchVoltage 一致
        """
        if not self.is_open:
            raise RuntimeError("DAQ未打开")
        if self._sample_mode != SampleMode.CONTINUOUS:
            raise RuntimeError("fetch_burst_retrigger 仅适用于 acquisition_mode='CONTINUOUS'")
        if n_shots < 1:
            raise ValueError("n_shots 至少为 1")

        if timeout is None:
            timeout = self.timeout

        err = Functions.ArtScope_StartAcquisition(self.task_handle)
        if err < 0:
            self._handle_error(err, 'burst start acquisition')
            return None

        total_length = self._actual_record_length * self._num_wfms
        read_length = ctypes.c_uint32(self._actual_record_length)
        out_list: list[np.ndarray] = []

        for i in range(n_shots):
            if sw_trigger_each_shot and self.trigger_source == 'SW':
                time.sleep(0.005)
                err_sw = Functions.ArtScope_SendSoftwareTrigger(self.task_handle)
                if err_sw < 0:
                    self._handle_error(err_sw, f'software trigger burst shot {i+1}')
                    try:
                        Functions.ArtScope_StopAcquisition(self.task_handle)
                    except Exception:
                        pass
                    return None

            waveform = np.zeros(total_length, dtype=np.double)
            wfm_info = ArtScope_wfmInfo()
            wfm_info.actualSamples = 0
            wfm_info.pAvailSampsPoints = 0

            err = Functions.ArtScope_FetchVoltage(
                self.task_handle, timeout,
                read_length, waveform, wfm_info
            )
            if err < 0:
                self._handle_error(err, f'burst fetch shot {i+1}/{n_shots}')
                try:
                    Functions.ArtScope_StopAcquisition(self.task_handle)
                except Exception:
                    pass
                return None

            out_list.append(waveform[:total_length].copy())

        try:
            Functions.ArtScope_StopAcquisition(self.task_handle)
        except Exception as e:
            logger.warning(f"StopAcquisition after burst: {e}")

        return out_list

    def read_averaged(self, avg_count=1, timeout=None):
        """多次采集取平均

        参数:
            avg_count: 平均次数
            timeout: 单次采集超时

        返回:
            平均后的numpy数组
        """
        if avg_count <= 1:
            return self.read_single(timeout)

        result = None
        success_count = 0
        for i in range(avg_count):
            data = self.read_single(timeout)
            if data is not None:
                if result is None:
                    result = data.copy()
                else:
                    result += data
                success_count += 1
            else:
                logger.warning(f"第 {i+1} 次采集失败")

        if success_count > 0:
            result /= success_count
            return result
        return None

    def close(self):
        """停止、释放、关闭采集任务"""
        try:
            if self.is_open or self.task_handle:
                try:
                    Functions.ArtScope_StopAcquisition(self.task_handle)
                except Exception:
                    pass
                try:
                    Functions.ArtScope_ReleaseAcquisition(self.task_handle)
                except Exception:
                    pass
                try:
                    Functions.ArtScope_Close(self.task_handle)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"DAQ close 异常: {e}")
        finally:
            self.is_open = False
            self.task_handle = lib_importer.task_handle(0)
            logger.info("PCIe8536C 已关闭")

    def _handle_error(self, error_code, context=''):
        """处理错误"""
        try:
            check_for_error(error_code)
        except ArtScopeError as e:
            logger.error(f"DAQ 错误 [{context}]: {e}")
            # 额外读取扩展错误信息（便于区分超时/触发/读取等原因）
            try:
                buf = ctypes.create_string_buffer(2048)
                Functions.ArtScope_GetExtendedErrorInfo(buf, 2048)
                ext = buf.value.decode('utf-8', errors='ignore').strip()
                if ext:
                    logger.error(f"DAQ 扩展错误信息: {ext}")
            except Exception:
                pass

    def _close_on_error(self, error_code, context=''):
        """出错时关闭并报告"""
        self._handle_error(error_code, context)
        self.close()


# 实验电脑使用的是PCIe8526；原始可用封装沿用了PCIe8536CDAQ类名。
PCIe8526DAQ = PCIe8536CDAQ


# ============================================================
# 独立测试
# ============================================================
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')

    daq = PCIe8536CDAQ(
        device_name='DEV2',
        channel='0',
        sample_rate=1e7,            # 对齐官方示例：MinSampleRate = 1E+7
        sample_length=1024,
        range_idx=1,              # ±1V（手册支持的量程）
        impedance=1,              # 50Ω
        trigger_source='DTR',     # 外部数字触发（对齐官方LabVIEW示例）
        trigger_slope=0,          # 下降沿（对齐官方 Python TrigDigital 示例）
        trigger_sensitivity=50,   # 对齐官方示例：50
        timeout=10.0
    )

    print("打开采集卡...")
    print(f"  触发方式: 数字触发 (DTR), 下降沿")
    if daq.open():
        print("配置成功，等待外部触发采集...")
        print("（DTR 为外部数字触发：请确保触发信号接入与官方示例一致的数字触发输入端）")

        try:
            print("提示：如果不确定触发链路，可临时把 trigger_source 改成 'SW'（软件触发）验证采集链路是否正常。")
            data = daq.read_single(timeout=10.0)
            if data is not None:
                print(f"采集成功: {len(data)} 点")
                print(f"  范围: {data.min():.4f} ~ {data.max():.4f} V")
                print(f"  均值: {data.mean():.4f} V")
            else:
                print("采集失败（常见原因：未触发/触发接线或电平不对/超时过短，可先把timeout调大再试）")
        except KeyboardInterrupt:
            print("\n用户中断")
        finally:
            daq.close()
    else:
        print("采集卡打开失败")
