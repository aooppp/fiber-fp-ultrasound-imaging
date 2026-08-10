"""
MC600 运动控制器 (卓立汉光) 串口控制类
通信协议: RS232, 19200bps, N,8,1
指令格式: ASCII, 以回车符(0x0D)结尾
"""

import serial
import time
import logging

logger = logging.getLogger(__name__)


class MC600Controller:
    """MC600系列运动控制器控制类"""

    # 轴号定义
    AXES = ['X', 'Y', 'Z', 'T']

    # 单位定义
    UNIT_MM = 'm'      # 毫米
    UNIT_UM = 'u'      # 微米
    UNIT_PP = 's'      # 脉冲数
    UNIT_DEG = 'd'     # 度

    # 台子类型
    STAGE_TRANSLATION = 'T'   # 平移台
    STAGE_ROTATION = 'R'      # 旋转台

    def __init__(self, port='COM4', baudrate=19200, timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

    def connect(self):
        """连接控制器，返回是否成功"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            time.sleep(0.5)
            self.ser.reset_input_buffer()

            # 联络测试
            if self.hello():
                logger.info(f"MC600 连接成功: {self.port}")
                return True
            else:
                logger.error("MC600 联络测试失败")
                self.ser.close()
                self.ser = None
                return False
        except serial.SerialException as e:
            logger.error(f"MC600 串口打开失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.ser = None
            logger.info("MC600 已断开")

    def _send_command(self, cmd):
        """发送指令，返回响应字符串

        MC600协议: 指令以0x0D(回车符)结尾，不是CR+LF
        """
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("串口未连接")

        self.ser.reset_input_buffer()
        self.ser.write((cmd + '\r').encode('ascii'))
        time.sleep(0.05)

        response = b''
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            if self.ser.in_waiting > 0:
                chunk = self.ser.read(self.ser.in_waiting)
                response += chunk
                # MC600响应以OK或E0x结尾
                if b'OK' in response or b'E0' in response:
                    break
            else:
                time.sleep(0.01)

        return response.decode('ascii', errors='ignore').strip()

    def hello(self):
        """联络测试"""
        try:
            resp = self._send_command('Hello')
            return 'OK' in resp
        except Exception:
            return False

    # ============================================================
    # 参数设置命令
    # ============================================================

    def set_unit(self, axis, unit='m'):
        """设置单位
        unit: 'm'=mm, 'u'=μm, 's'=PP(脉冲数), 'd'=deg(度)
        """
        cmd = f'SetUnit {axis},{unit}'
        return self._check_ok(cmd)

    def set_speed(self, axis, speed):
        """设置常速度"""
        cmd = f'SetSpeed {axis},{speed}'
        return self._check_ok(cmd)

    def set_init_speed(self, axis, speed):
        """设置初速度"""
        cmd = f'SetInitSpeed {axis},{speed}'
        return self._check_ok(cmd)

    def set_acc_speed(self, axis, acc):
        """设置加速度"""
        cmd = f'SetAccSpeed {axis},{acc}'
        return self._check_ok(cmd)

    def set_home_speed(self, axis, speed):
        """设置回原点速度"""
        cmd = f'SetHomeSpeed {axis},{speed}'
        return self._check_ok(cmd)

    def set_stage_style(self, axis, style='T'):
        """设置台子类型 T=平移台, R=旋转台"""
        cmd = f'SetStageStyle {axis},{style}'
        return self._check_ok(cmd)

    def set_pitch(self, axis, pitch):
        """设置丝杠导程 (mm)"""
        cmd = f'SetStagePitch {axis},{pitch}'
        return self._check_ok(cmd)

    def set_steps_rev(self, axis, steps):
        """设置每转脉冲数（细分）"""
        cmd = f'SetStageStepsRev {axis},{steps}'
        return self._check_ok(cmd)

    def set_origin(self, axis):
        """将当前位置设为工作原点"""
        cmd = f'SetUserOrigin {axis},0'
        return self._check_ok(cmd)

    def set_soft_limit_enable(self, axis, enable=True):
        """设置软限位使能 E=开启, D=关闭"""
        flag = 'E' if enable else 'D'
        cmd = f'SetUserLimitAble {axis},{flag}'
        return self._check_ok(cmd)

    def set_positive_limit(self, axis, limit):
        """设置正向软限位"""
        cmd = f'SetUserPositiveLimit {axis},{limit}'
        return self._check_ok(cmd)

    def set_negative_limit(self, axis, limit):
        """设置负向软限位"""
        cmd = f'SetUserNegativeLimit {axis},{limit}'
        return self._check_ok(cmd)

    # ============================================================
    # 运动控制命令
    # ============================================================

    def move_absolute(self, axis, position, workstate='O'):
        """绝对位置移动
        workstate: 'O'=开环, 'C'=闭环
        移动到绝对坐标 position（由当前单位决定）
        """
        cmd = f'GoPosition {axis},{workstate},A,P,{position}'
        resp = self._send_command(cmd)
        if 'READY' in resp:
            return True
        elif 'OK' in resp:
            return True
        elif 'E0' in resp:
            logger.error(f"移动失败: {resp}")
            return False
        return True

    def move_relative(self, axis, distance, workstate='O'):
        """相对位置移动
        distance: 相对移动距离，正值正向，负值负向
        """
        if distance >= 0:
            direction = 'P'
            dist = abs(distance)
        else:
            direction = 'N'
            dist = abs(distance)

        cmd = f'GoPosition {axis},{workstate},R,{direction},{dist}'
        resp = self._send_command(cmd)
        if 'READY' in resp:
            return True
        elif 'OK' in resp:
            return True
        elif 'E0' in resp:
            logger.error(f"移动失败: {resp}")
            return False
        return True

    def go_home(self, axis):
        """回机械原点"""
        cmd = f'GoHome {axis}'
        resp = self._send_command(cmd)
        if 'READY' in resp or 'OK' in resp:
            return True
        logger.error(f"归零失败: {resp}")
        return False

    def go_origin(self, axis):
        """回工作原点"""
        cmd = f'GoOrigion {axis}'
        resp = self._send_command(cmd)
        if 'READY' in resp or 'OK' in resp:
            return True
        logger.error(f"回原点失败: {resp}")
        return False

    def stop(self, axis):
        """停止某轴运动"""
        cmd = f'STOP {axis}'
        resp = self._send_command(cmd)
        return 'READY' in resp or 'OK' in resp

    # ============================================================
    # 参数查询命令
    # ============================================================

    def get_position(self, axis):
        """查询当前坐标位置，返回float值"""
        cmd = f'Position? {axis}'
        resp = self._send_command(cmd)
        try:
            # 响应格式: "Position? X,12.345,OK"
            parts = resp.split(',')
            for part in parts:
                part = part.strip()
                # 跳过 "Position?" 和 "OK"
                if part in ('OK', '') or part.startswith('Position'):
                    continue
                try:
                    return float(part)
                except ValueError:
                    continue
            logger.error(f"位置解析失败: {resp}")
            return None
        except Exception as e:
            logger.error(f"位置查询异常: {e}, 响应: {resp}")
            return None

    def get_speed(self, axis):
        """查询常速度"""
        cmd = f'SetSpeed? {axis}'
        resp = self._send_command(cmd)
        return self._parse_query_float(resp)

    def get_unit(self, axis):
        """查询当前单位"""
        cmd = f'SetUnit? {axis}'
        resp = self._send_command(cmd)
        try:
            parts = resp.split(',')
            for part in parts:
                part = part.strip()
                if part in ('OK', '') or part.startswith('SetUnit'):
                    continue
                return part
        except Exception:
            return None

    # ============================================================
    # 辅助方法
    # ============================================================

    def wait_for_stop(self, axis, timeout=60, poll_interval=0.05):
        """等待轴运动完成（通过轮询位置变化判断）"""
        last_pos = self.get_position(axis)
        stable_count = 0
        required_stable = 3  # 连续3次位置不变认为稳定

        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(poll_interval)
            current_pos = self.get_position(axis)

            if current_pos is None:
                continue

            if abs(current_pos - last_pos) < 1e-4:
                stable_count += 1
                if stable_count >= required_stable:
                    return True
            else:
                stable_count = 0
                last_pos = current_pos

        logger.warning(f"轴 {axis} 等待超时")
        return False

    def setup_axis(self, axis, pitch, speed, init_speed, acc, unit='m',
                   steps_rev=1600, stage_style='T'):
        """一次性设置轴的所有运动参数"""
        ok = True
        ok &= self.set_stage_style(axis, stage_style)
        ok &= self.set_pitch(axis, pitch)
        ok &= self.set_steps_rev(axis, steps_rev)
        ok &= self.set_unit(axis, unit)
        ok &= self.set_speed(axis, speed)
        ok &= self.set_init_speed(axis, init_speed)
        ok &= self.set_acc_speed(axis, acc)
        ok &= self.set_home_speed(axis, init_speed)

        if ok:
            logger.info(f"轴 {axis} 参数设置完成: pitch={pitch}, speed={speed}, "
                        f"init={init_speed}, acc={acc}, unit={unit}")
        else:
            logger.error(f"轴 {axis} 参数设置有误")
        return ok

    def _check_ok(self, cmd):
        """发送命令并检查是否返回OK"""
        resp = self._send_command(cmd)
        return 'OK' in resp

    def _parse_query_float(self, resp):
        """从查询响应中解析float值"""
        try:
            parts = resp.split(',')
            for part in parts:
                part = part.strip()
                if part in ('OK', '') or part.startswith('Set'):
                    continue
                try:
                    return float(part)
                except ValueError:
                    continue
        except Exception:
            pass
        return None


# ============================================================
# 独立测试
# ============================================================
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')

    mc = MC600Controller(port='COM4')

    if mc.connect():
        print("连接成功，开始测试...")

        # 查询当前位置
        for axis in ['X', 'Y']:
            pos = mc.get_position(axis)
            print(f"  轴{axis} 当前位置: {pos}")

        # 设置参数
        mc.setup_axis('X', pitch=2.0, speed=5.0, init_speed=2.0, acc=10.0)
        mc.setup_axis('Y', pitch=2.0, speed=5.0, init_speed=2.0, acc=10.0)

        # 归零
        print("\nX轴归零...")
        mc.go_home('X')
        mc.wait_for_stop('X')
        print(f"  X轴位置: {mc.get_position('X')}")

        # 相对移动测试
        print("\nX轴移动 +5mm...")
        mc.move_relative('X', 5.0)
        mc.wait_for_stop('X')
        print(f"  X轴位置: {mc.get_position('X')}")

        # 回原点
        print("\nX轴回原点...")
        mc.go_origin('X')
        mc.wait_for_stop('X')
        print(f"  X轴位置: {mc.get_position('X')}")

        mc.disconnect()
    else:
        print("连接失败，请检查串口号和接线")
