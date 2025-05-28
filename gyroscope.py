from abc import ABC, abstractmethod
import time
from pymodbus.client import ModbusSerialClient
from typing import Tuple, Optional
import numpy as np

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
    """真实陀螺仪实现"""
    def __init__(self, 
                 port: str,
                 baudrate: int = 4800,
                 parity: str = 'N',
                 stopbits: int = 1,
                 bytesize: int = 8,
                 timeout: int = 1):
        """
        初始化陀螺仪
        Args:
            port: 串口设备地址
            baudrate: 波特率
            parity: 校验位 ('N' - 无校验, 'E' - 偶校验, 'O' - 奇校验)
            stopbits: 停止位
            bytesize: 数据位
            timeout: 超时时间(秒)
        """
        self.client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            parity=parity,
            stopbits=stopbits,
            bytesize=bytesize,
            timeout=timeout
        )
        
        if not self.client.connect():
            raise ConnectionError("无法连接到陀螺仪设备")

    def read_angles(self) -> Tuple[float, float, float]:
        """
        读取三轴角度值
        Returns:
            tuple: (x角度, y角度, z角度) 单位：度
        """
        try:
            # 根据说明书，读取寄存器地址为0x0000-0x0005
            response = self.client.read_holding_registers(
                address=3,
                count=3,
                slave=1
            )
            
            if response.isError():
                raise Exception("读取角度数据失败")
                
            # 将数据转换为实际角度值（除以10，因为数据被放大了10倍）
            raw_x = response.registers[0]
            signed_x = raw_x - 65536 if raw_x > 32767 else raw_x
            x_angle = signed_x / 10.0
            
            raw_y = response.registers[1]
            signed_y = raw_y - 65536 if raw_y > 32767 else raw_y
            y_angle = signed_y / 10.0
            
            raw_z = response.registers[2]
            signed_z = raw_z - 65536 if raw_z > 32767 else raw_z
            z_angle = signed_z / 10.0
            
            return x_angle, y_angle, z_angle
            
        except Exception as e:
            print(f"读取角度时发生错误: {str(e)}")
            return 0.0, 0.0, 0.0

    def calibrate_xy(self) -> bool:
        """
        校准XY轴
        Returns:
            bool: 校准是否成功
        """
        try:
            # 根据说明书，写入特定值到校准寄存器
            result = self.client.write_register(
                address=0x0006,
                value=1,
                slave=1
            )
            
            if result.isError():
                raise Exception("XY轴校准失败")
                
            # 等待校准完成
            time.sleep(2)
            return True
            
        except Exception as e:
            print(f"XY轴校准时发生错误: {str(e)}")
            return False

    def calibrate_z(self) -> bool:
        """
        校准Z轴
        Returns:
            bool: 校准是否成功
        """
        try:
            # 根据说明书，写入特定值到校准寄存器
            result = self.client.write_register(
                address=0x0007,
                value=1,
                slave=1
            )
            
            if result.isError():
                raise Exception("Z轴校准失败")
                
            # 等待校准完成
            time.sleep(2)
            return True
            
        except Exception as e:
            print(f"Z轴校准时发生错误: {str(e)}")
            return False
            
    def get_current_attitude(self) -> Tuple[float, float]:
        """获取真实陀螺仪数据
        Returns:
            Tuple[float, float]: (方位角, 高度角) 单位：度
        """
        x, y, z = self.read_angles()
        # 根据实际陀螺仪的安装方式，可能需要调整角度的映射关系
        azimuth = z % 360  # 假设z轴对应方位角
        altitude = y       # 假设y轴对应高度角
        return azimuth, altitude
        
    def process_command(self, cmd: str) -> None:
        """真实陀螺仪不需要处理命令"""
        pass

    def __del__(self):
        """析构函数，确保关闭串口连接"""
        if hasattr(self, 'client'):
            self.client.close()

# 测试代码
if __name__ == "__main__":
    try:
        # 创建陀螺仪实例（使用默认参数）
        gyro = RealGyroscope(port='/dev/tty.usbserial-1120')
        
        # 读取角度值
        print("\n开始读取角度值...")
        for i in range(100):
            azimuth, altitude = gyro.get_current_attitude()
            print(f"当前角度 - 方位角: {azimuth:.2f}° 高度角: {altitude:.2f}°")
            time.sleep(1)
            
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}") 