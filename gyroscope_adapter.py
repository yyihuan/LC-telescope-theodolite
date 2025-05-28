from abc import ABC, abstractmethod
import time
import numpy as np
from typing import Tuple, Optional
from gyroscope import Gyroscope

class GyroscopeBase(ABC):
    """陀螺仪基类，定义统一接口"""
    
    @abstractmethod
    def get_current_attitude(self) -> Tuple[float, float]:
        """获取当前姿态
        Returns:
            Tuple[float, float]: (方位角, 高度角) 单位：度
        """
        pass
        
    @abstractmethod
    def process_command(self, cmd: str) -> None:
        """处理控制命令（仅在仿真模式下需要实现）
        Args:
            cmd: 控制命令字符串
        """
        pass

class VirtualGyroscope(GyroscopeBase):
    """虚拟陀螺仪实现"""
    def __init__(self):
        self.current_az = 0.0
        self.current_alt = 20.0
        self.last_update = time.time()
        
    def get_current_attitude(self) -> Tuple[float, float]:
        return self.current_az, self.current_alt
        
    def process_command(self, cmd: str) -> None:
        """处理控制命令，更新虚拟陀螺仪状态"""
        current_time = time.time()
        dt = current_time - self.last_update
        self.last_update = current_time
        
        # 模拟运动速度（度/秒）
        speed = 10.0
        
        if "AZ1" in cmd:  # 顺时针
            self.current_az = (self.current_az + speed * dt) % 360
        elif "AZ2" in cmd:  # 逆时针
            self.current_az = (self.current_az - speed * dt) % 360
            
        if "EL1" in cmd:  # 升高
            self.current_alt = min(90.0, self.current_alt + speed * dt)
        elif "EL2" in cmd:  # 降低
            self.current_alt = max(20.0, self.current_alt - speed * dt)

class RealGyroscope(GyroscopeBase):
    """真实陀螺仪适配器"""
    def __init__(self, port: str):
        self.gyro = Gyroscope(port=port)
        
    def get_current_attitude(self) -> Tuple[float, float]:
        """获取真实陀螺仪数据
        Returns:
            Tuple[float, float]: (方位角, 高度角) 单位：度
        """
        x, y, z = self.gyro.read_angles()
        # 根据实际陀螺仪的安装方式，可能需要调整角度的映射关系
        azimuth = z % 360  # 假设z轴对应方位角
        altitude = y       # 假设y轴对应高度角
        return azimuth, altitude
        
    def process_command(self, cmd: str) -> None:
        """真实陀螺仪不需要处理命令"""
        pass 