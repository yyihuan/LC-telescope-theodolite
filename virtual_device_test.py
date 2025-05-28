import time
import logging
from datetime import datetime
from transform_control import TelescopeController

class VirtualGyro:
    def __init__(self):
        self.azimuth = 0.0  # 方位角(0-360度)
        self.altitude = 90.0  # 高度角(20-90度)
        self.last_update = datetime.now()
        self.az_direction = 0  # 0:停止, 1:顺时针, 2:逆时针
        self.alt_direction = 0  # 0:停止, 1:升高, 2:降低
        self.last_cmd_time = datetime.now()
        self.az_speed = 30  # 方位角每秒旋转角度
        self.alt_speed = 50  # 高度角每秒旋转角度
        
    def get_current_attitude(self):
        """仅获取当前角度，不做任何计算"""
        return self.azimuth, self.altitude
        
    def update_attitude(self):
        """更新虚拟陀螺仪的角度"""
        now = datetime.now()
        delta = (now - self.last_update).total_seconds()
        self.last_update = now
        
        # 更新方位角
        if self.az_direction == 1:  # 顺时针
            self.azimuth = (self.azimuth + delta * self.az_speed) % 360
        elif self.az_direction == 2:  # 逆时针
            self.azimuth = (self.azimuth - delta * self.az_speed) % 360
            
        # 更新高度角
        if self.alt_direction == 1:  # 升高
            self.altitude = min(90.0, self.altitude + delta * self.alt_speed)
        elif self.alt_direction == 2:  # 降低
            self.altitude = max(20.0, self.altitude - delta * self.alt_speed)
        
    def parse_command(self, cmd):
        """解析控制命令"""
        # 解析方位角控制部分
        if "AZ1" in cmd:  # 顺时针
            self.az_direction = 1
        elif "AZ2" in cmd:  # 逆时针
            self.az_direction = 2
        elif "AZ0" in cmd:  # 停止
            self.az_direction = 0
            
        # 解析高度角控制部分
        if "EL1" in cmd:  # 升高
            self.alt_direction = 1
        elif "EL2" in cmd:  # 降低
            self.alt_direction = 2
        elif "EL0" in cmd:  # 停止
            self.alt_direction = 0
            
    def process_command(self, cmd):
        """处理控制命令并更新状态"""
        self.last_cmd_time = datetime.now()
        self.parse_command(cmd)
        self.update_attitude()

def test_virtual_gyro():
    """测试虚拟陀螺仪单独工作"""
    gyro = VirtualGyro()
    
    print("初始状态:", gyro.get_current_attitude())
    
    # 测试方位角
    print("\n测试方位角顺时针旋转...")
    gyro.process_command("AZ1EL0\n")
    time.sleep(1)
    print("1秒后角度:", gyro.get_current_attitude())
    
    print("\n测试停止方位角...")
    gyro.process_command("AZ0EL0\n")
    time.sleep(1)
    print("1秒后角度:", gyro.get_current_attitude())
    
    # 测试高度角
    print("\n测试高度角降低...")
    gyro.process_command("AZ0EL2\n")
    time.sleep(1)
    print("1秒后角度:", gyro.get_current_attitude())
    
    print("\n测试高度角升高...")
    gyro.process_command("AZ0EL1\n")
    time.sleep(1)
    print("1秒后角度:", gyro.get_current_attitude())

def test_telescope_control_equatorial():
    """测试望远镜控制系统 - 使用赤道坐标"""
    # 创建虚拟陀螺仪
    gyro = VirtualGyro()
    
    # 创建望远镜控制器并传入虚拟陀螺仪，使用仿真模式
    controller = TelescopeController(gyro=gyro, simulation=True)
    
    # 设置目标位置 (使用赤道坐标)
    current_time = datetime.now()
    controller.set_target(90, 45, 40.011, 116.392, current_time)
    
    print("\n开始望远镜控制测试 (赤道坐标)...")
    print(f"初始角度: {gyro.get_current_attitude()}")
    print(f"目标角度: ({controller.target_azimuth:.2f}°, {controller.target_altitude:.2f}°)")
    
    # 运行控制循环一次，然后退出
    controller.control_loop()
    
    # 模拟望远镜移动5秒钟
    start_time = time.time()
    while time.time() - start_time < 5:
        # 更新虚拟陀螺仪状态
        gyro.update_attitude()
        
        # 打印当前状态
        current_az, current_alt = gyro.get_current_attitude()
        print(f"当前角度: ({current_az:.2f}°, {current_alt:.2f}°)", end='\r')
        time.sleep(0.1)
    
    print("\n5秒后角度:", gyro.get_current_attitude())

def test_telescope_control_horizontal():
    """测试望远镜控制系统 - 使用地平坐标"""
    # 创建虚拟陀螺仪
    gyro = VirtualGyro()
    
    # 创建望远镜控制器并传入虚拟陀螺仪，使用仿真模式
    controller = TelescopeController(gyro=gyro, simulation=True)
    
    # 设置目标位置 (使用地平坐标)
    controller.set_target(180, 45, coordinate_type='horizontal')
    
    print("\n开始望远镜控制测试 (地平坐标)...")
    print(f"初始角度: {gyro.get_current_attitude()}")
    print(f"目标角度: ({controller.target_azimuth:.2f}°, {controller.target_altitude:.2f}°)")
    
    # 运行控制循环一次，然后退出
    controller.control_loop()
    
    # 模拟望远镜移动5秒钟
    start_time = time.time()
    while time.time() - start_time < 5:
        # 更新虚拟陀螺仪状态
        gyro.update_attitude()
        
        # 打印当前状态
        current_az, current_alt = gyro.get_current_attitude()
        print(f"当前角度: ({current_az:.2f}°, {current_alt:.2f}°)", end='\r')
        time.sleep(0.1)
    
    print("\n5秒后角度:", gyro.get_current_attitude())

def test_hybrid_simulation():
    """测试半实物仿真模式 - 虚拟陀螺仪 + 真实串口"""
    # 配置日志以显示更多信息
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 创建虚拟陀螺仪
    gyro = VirtualGyro()
    
    try:
        # 创建望远镜控制器 - 使用半实物仿真模式
        # 注意：这会尝试连接真实串口，如果连接失败会抛出异常
        port = '/dev/tty.usbmodem1201'  # 根据实际串口修改
        controller = TelescopeController(
            port=port, 
            baudrate=115200, 
            gyro=gyro, 
            simulation=False,  # 不是完全仿真
            hybrid_sim=True    # 启用半实物仿真
        )
        
        # 使用地平坐标设置目标
        controller.set_target(180, 45, coordinate_type='horizontal')
        
        print("\n开始半实物仿真测试...")
        print(f"初始角度: {gyro.get_current_attitude()}")
        print(f"目标角度: ({controller.target_azimuth:.2f}°, {controller.target_altitude:.2f}°)")
        
        print("\n注意：此模式下命令将发送到真实硬件，但使用虚拟陀螺仪反馈位置")
        input("按回车键继续，或按Ctrl+C取消...")
        
        # 模拟望远镜移动5秒钟或直到达到目标
        start_time = time.time()
        max_time = 30  # 最大运行30秒
        
        try:
            while time.time() - start_time < max_time:
                # 执行一步控制
                result = controller.control_loop()
                
                # 如果返回0，表示已到达目标
                if result == 0:
                    print("\n已到达目标位置!")
                    break
                
                # 打印当前状态
                current_az, current_alt = gyro.get_current_attitude()
                print(f"当前角度: ({current_az:.2f}°, {current_alt:.2f}°)")
                
                time.sleep(0.5)  # 半秒更新一次
            else:
                print("\n控制超时，未能到达目标位置")
                
        except KeyboardInterrupt:
            print("\n用户中断，停止控制")
        
        # 打印最终状态
        final_az, final_alt = gyro.get_current_attitude()
        print(f"最终角度: ({final_az:.2f}°, {final_alt:.2f}°)")
        
    except Exception as e:
        print(f"\n半实物仿真测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 确保关闭控制器
        if 'controller' in locals():
            controller.close()

def test_continuous_control():
    """测试望远镜连续控制"""
    # 创建虚拟陀螺仪
    gyro = VirtualGyro()
    
    # 创建望远镜控制器并传入虚拟陀螺仪，使用仿真模式
    controller = TelescopeController(gyro=gyro, simulation=True)
    
    # 设置目标位置
    controller.set_target(180, 45, coordinate_type='horizontal')
    
    print("\n开始连续控制测试...")
    print(f"初始角度: {gyro.get_current_attitude()}")
    print(f"目标角度: ({controller.target_azimuth:.2f}°, {controller.target_altitude:.2f}°)")
    
    # 运行控制循环直到到达目标或超时
    start_time = time.time()
    max_time = 30  # 最大运行30秒
    
    while time.time() - start_time < max_time:
        # 执行一步控制
        result = controller.control_loop()
        
        # 如果返回0，表示已到达目标
        if result == 0:
            print("\n已到达目标位置!")
            break
            
        # 打印当前状态
        current_az, current_alt = gyro.get_current_attitude()
        print(f"当前角度: ({current_az:.2f}°, {current_alt:.2f}°)", end='\r')
        time.sleep(0.1)
    else:
        print("\n控制超时，未能到达目标位置")
    
    # 打印最终状态
    final_az, final_alt = gyro.get_current_attitude()
    print(f"最终角度: ({final_az:.2f}°, {final_alt:.2f}°)")
    print(f"目标角度: ({controller.target_azimuth:.2f}°, {controller.target_altitude:.2f}°)")
    
    # 确保关闭控制器
    controller.close()

if __name__ == "__main__":
    print("===== 虚拟陀螺仪测试 =====")
    test_virtual_gyro()
    
    print("\n===== 望远镜控制系统测试（赤道坐标） =====")
    test_telescope_control_equatorial()
    
    print("\n===== 望远镜控制系统测试（地平坐标） =====")
    test_telescope_control_horizontal()
    
    print("\n===== 望远镜连续控制测试 =====")
    test_continuous_control()
    
    # 半实物仿真测试需要连接真实硬件，默认注释掉
    # 取消下面的注释来运行半实物仿真测试
    # print("\n===== 半实物仿真测试 =====")
    # test_hybrid_simulation()