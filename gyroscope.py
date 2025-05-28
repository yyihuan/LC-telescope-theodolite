import time
from pymodbus.client import ModbusSerialClient
from typing import Tuple, Optional

class Gyroscope:
    def __init__(self, 
                 port: str ,
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
            print(self.client.connect())
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
            # 假设寄存器中的值为16位有符号整数，数值被放大了10倍。
            # 大于32767的值被视为负数（按二进制补码表示）。
            
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

    def __del__(self):
        """析构函数，确保关闭串口连接"""
        if hasattr(self, 'client'):
            self.client.close()

# 测试代码
if __name__ == "__main__":
    try:
        # 创建陀螺仪实例（使用默认参数）
        gyro = Gyroscope(port='/dev/tty.usbserial-1120')
        
        # 执行校准
        # print("开始XY轴校准...")
        # if gyro.calibrate_xy():
        #     print("XY轴校准成功")
        # else:
        #     print("XY轴校准失败")
            
        # print("开始Z轴校准...")
        # if gyro.calibrate_z():
        #     print("Z轴校准成功")
        # else:
        #     print("Z轴校准失败")
            
        # 读取角度值
        print("\n开始读取角度值...")
        for i in range(100):
            x, y, z = gyro.read_angles()
            print(f"当前角度 - X: {x:.2f}°  Y: {y:.2f}°  Z: {z:.2f}°")
            time.sleep(1)
            
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}") 