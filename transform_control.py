import time
import serial
from datetime import datetime
import logging
import sys
import numpy as np
from astropy import units as u
from astropy.coordinates import EarthLocation, SkyCoord, AltAz
from astropy.time import Time


class TelescopeController:
    def __init__(self, port='/dev/tty.usbmodem1201', baudrate=115200, gyro=None, simulation=False, hybrid_sim=False):
        """
        初始化望远镜控制器
        
        :param port: 串口设备名
        :param baudrate: 波特率
        :param gyro: 陀螺仪对象，提供姿态数据
        :param simulation: 完全仿真模式（不连接真实串口，使用虚拟陀螺仪）
        :param hybrid_sim: 半实物仿真模式（连接真实串口，使用虚拟陀螺仪）
        """
        self.gyro = gyro if gyro is not None else None
        self.simulation = simulation
        self.hybrid_sim = hybrid_sim
        
        # 完全仿真模式：不连接串口
        # 半实物仿真模式：连接串口但使用虚拟陀螺仪
        # 正常模式：连接串口并使用真实陀螺仪
        
        if not simulation or hybrid_sim:
            try:
                self.ser = serial.Serial(port, baudrate, timeout=0.1)
                logging.info(f"成功连接到串口 {port}")
                if hybrid_sim:
                    logging.info("运行在半实物仿真模式：虚拟陀螺仪 + 真实硬件控制")
            except Exception as e:
                logging.error(f"无法连接串口 {port}: {e}")
                if not hybrid_sim:
                    logging.warning("自动切换到仿真模式")
                    self.simulation = True  # 连接失败时自动切换到仿真模式（非半实物仿真模式下）
                else:
                    logging.error("半实物仿真模式下串口连接失败，无法继续")
                    raise
                
        self.target_azimuth = 0.0
        self.target_altitude = 20.0
        
        # 记录运行模式
        mode = "完全仿真" if simulation else ("半实物仿真" if hybrid_sim else "正常")
        logging.info(f"望远镜控制器初始化完成，运行模式：{mode}")

    def equatorial_to_horizontal(self, ra, dec, lat, lon, time):
        """
        使用astropy将赤道坐标系转换为地平坐标系。

        :param ra: 赤经 (小时)
        :param dec: 赤纬 (度)
        :param lat: 观测点纬度 (度)
        :param lon: 观测点经度 (度)
        :param time: 观测时间 (datetime对象)
        :return: 方位角 (度), 高度角 (度)
        """
        # 定义观测地点
        location = EarthLocation(lat=lat*u.deg, lon=lon*u.deg)
        # 定义观测时间
        astropy_time = Time(time)
        # 定义赤道坐标
        equatorial_coord = SkyCoord(ra=ra*15*u.deg, dec=dec*u.deg)
        # 定义地平坐标系
        altaz_frame = AltAz(obstime=astropy_time, location=location)
        # 转换为地平坐标
        altaz_coord = equatorial_coord.transform_to(altaz_frame)

        return altaz_coord.az.deg, altaz_coord.alt.deg

    def set_target(self, *args, **kwargs):
        """
        设置目标坐标。可以接受两种格式的参数：
        1. 赤道坐标：set_target(ra, dec, lat, lon, time)
           - ra: 赤经 (小时)
           - dec: 赤纬 (度)
           - lat: 观测点纬度 (度)
           - lon: 观测点经度 (度)
           - time: 观测时间 (datetime对象)
        
        2. 地平坐标：set_target(azimuth, altitude, coordinate_type='horizontal')
           - azimuth: 方位角 (度)
           - altitude: 高度角 (度)
           - coordinate_type: 必须设为'horizontal'
        """
        # 检查参数来确定是哪种坐标系
        if 'coordinate_type' in kwargs and kwargs['coordinate_type'] == 'horizontal':
            # 地平坐标系输入
            if len(args) >= 2:
                azimuth, altitude = args[0], args[1]
            else:
                raise ValueError("使用地平坐标系时，必须提供方位角和高度角")
        else:
            # 赤道坐标系输入
            if len(args) >= 5:
                ra, dec, lat, lon, time = args
                azimuth, altitude = self.equatorial_to_horizontal(ra, dec, lat, lon, time)
            else:
                raise ValueError("使用赤道坐标系时，必须提供赤经、赤纬、纬度、经度和时间")
        
        # 设置目标坐标
        self.target_azimuth = azimuth % 360
        self.target_altitude = max(20.0, min(90.0, altitude))
        logging.info(f"设置目标: 方位角={self.target_azimuth:.2f}°, 高度角={self.target_altitude:.2f}°")
        
    def send_command(self, cmd):
        """发送命令，根据模式选择发送到串口或模拟"""
        # 在完全仿真模式下不发送串口命令，在半实物仿真和正常模式下发送
        if not self.simulation or self.hybrid_sim:
            try:
                self.ser.write(cmd.encode())
                logging.debug(f"串口命令已发送: {cmd.strip()}")
            except Exception as e:
                logging.error(f"串口命令发送失败: {e}")
        
        # 在仿真和半实物仿真模式下使用虚拟陀螺仪，在正常模式下不使用
        if self.gyro and (self.simulation or self.hybrid_sim):
            self.gyro.process_command(cmd)
            
        print(cmd, end="")
        
    def control_loop(self):
        """控制循环，驱动望远镜移动到目标位置"""
        while True:
            # 获取当前姿态
            if not self.gyro and (self.simulation or self.hybrid_sim):
                logging.error("仿真或半实物仿真模式下未设置虚拟陀螺仪")
                return 1
                
            current_az, current_alt = self.gyro.get_current_attitude()
            
            # 计算方位角和高度角的控制信号
            az_cw, az_ccw = self._calculate_azimuth_control(current_az)
            alt_up, alt_down = self._calculate_altitude_control(current_alt)

            # 打印当前状态
            print(f"当前角度: ({current_az:.2f}°, {current_alt:.2f}°)")
            print(f"目标角度: ({self.target_azimuth:.2f}°, {self.target_altitude:.2f}°)")
            
            # 检查是否到达目标
            if self._reached_target(az_cw, az_ccw, alt_up, alt_down):
                logging.info("到达目标位置，停止所有运动")
                for i in range(10):
                    self.send_command("AZ0EL0\n")  # 停止所有运动 
                    time.sleep(0.005)
                return 0  # 退出循环
                
            # 生成控制命令
            cmd = self._generate_control_command(az_cw, az_ccw, alt_up, alt_down)
            self.send_command(cmd)
            
            # 等待下一个控制周期
            time.sleep(0.005)  # 10ms控制周期
    
    def _reached_target(self, az_cw, az_ccw, alt_up, alt_down):
        """检查是否到达目标位置"""
        return az_cw and az_ccw and alt_up and alt_down
    
    def _generate_control_command(self, az_cw, az_ccw, alt_up, alt_down):
        """根据控制信号生成控制命令"""
        # 方位角控制
        if az_cw and not az_ccw:
            az_cmd = "1"  # 顺时针
        elif not az_cw and az_ccw:
            az_cmd = "2"  # 逆时针
        else:
            az_cmd = "0"  # 停止
        
        # 高度角控制
        if alt_up and not alt_down:
            el_cmd = "1"  # 升高
        elif not alt_up and alt_down:
            el_cmd = "2"  # 降低
        else:
            el_cmd = "0"  # 停止
        
        return f"AZ{az_cmd}EL{el_cmd}\n"
            
    def _calculate_azimuth_control(self, current_az):
        error = (self.target_azimuth - current_az) % 360
        if abs(error) < 1:  # 使用绝对值函数简化判断逻辑，当误差绝对值小于0.5时认为到达目标
            return 1, 1  # 停止信号
                
        # 不使用最短旋转方向，根据误差正负判断旋转方向
        if error > 1:
            return 1, 0  # 顺时针旋转
        else:
            return 0, 1  # 逆时针旋转
                    
    def _calculate_altitude_control(self, current_alt):
        # 检查目标高度角是否在20-90度范围内
        if self.target_altitude < 20 or self.target_altitude > 90:
            logging.error(f"目标高度角 {self.target_altitude} 不在20-90度的有效范围内，请检查输入。")
            sys.exit(1)
        
        error = self.target_altitude - current_alt
        if abs(error) < 1:  # 到达目标
            return 1, 1  # 停止信号
            
        if error > 1:
            return 1, 0  # 升高
        else:
            return 0, 1  # 降低

    def close(self):
        """关闭控制器，释放资源"""
        if hasattr(self, 'ser') and self.ser:
            try:
                self.send_command("AZ0EL0\n")  # 确保停止所有运动
                self.ser.close()
                logging.info("串口已关闭")
            except Exception as e:
                logging.error(f"关闭串口时出错: {e}")
        
# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    
    controller = TelescopeController(simulation=True)
    current_time = datetime.now()
    
    # 使用赤道坐标设置目标
    controller.set_target(90, 45, 40.011, 116.392, current_time)  
    
    # 使用地平坐标设置目标
    # controller.set_target(180, 45, coordinate_type='horizontal')
    
    try:
        controller.control_loop()
    finally:
        controller.close()  # 确保在退出时关闭资源