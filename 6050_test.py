import serial
import time
import sys
import struct

# --- 配置 ---
# !! 请根据实际情况修改下面的串口名称 !!
# 例如: '/dev/tty.usbserial-1130', '/dev/tty.usbmodem14101', 等
SERIAL_PORT = '/dev/tty.usbserial-1201' # <--- 请务必确认并修改这里！
BAUD_RATE = 115200
TIMEOUT = 1  # 读取超时时间（秒）

# --- 指令 (十六进制) ---
CMD_START_SAMPLING = bytes([0x01])  # 0x01 表示开始采样
CMD_STOP_SAMPLING = bytes([0x00])   # 0x00 表示停止采样

def list_serial_ports():
    """列出可用的串口 (macOS/Linux)"""
    if sys.platform.startswith('darwin') or sys.platform.startswith('linux'):
        import glob
        ports = glob.glob('/dev/tty.*') + glob.glob('/dev/cu.*')
        if not ports:
            print("未找到可用的串口。请确保设备已连接。")
        else:
            print("检测到的可用串口:")
            for port in ports:
                print(f"  {port}")
    else:
        print("此功能目前主要支持 macOS 和 Linux。对于 Windows，请检查设备管理器。")


def parse_sensor_data(data):
    """解析传感器数据(十六进制字符串列表)"""
    if len(data) != 22:
        raise ValueError(f"数据长度应为22字节，实际收到{len(data)}字节")
    
    # 检查帧头和帧尾
    if data[0].lower() != '5a' or data[1].lower() != '4a' or data[-2].lower() != 'aa' or data[-1].lower() != '55':
        raise ValueError("帧头或帧尾不匹配")
    
    # 提取数据部分 (索引7-18)
    data_part = data[7:19]
    
    # 解析加速度 (前6字节)
    def hex_to_signed_int(hex_str):
        # 分割输入字符串并确保每个部分是2位十六进制
        parts = hex_str.split()
        # 补足到2位十六进制
        fixed_parts = [f"{int(part,16):02x}" for part in parts]
        fixed_hex = " ".join(fixed_parts)
        
        #print(f"正在解析(修正后): {fixed_hex}")
        byte_data = bytes.fromhex(fixed_hex)
        
        # 使用 struct.unpack 将字节串解码为有符号 16 位整数
        # 'h' 表示短整数(2字节，带符号整数)
        parsed_value = struct.unpack('>h', byte_data)[0]
        #print(f"解析结果: {parsed_value}")
        return parsed_value
    
    # 解析加速度 (前12字节)
    acx = hex_to_signed_int(data_part[0]+" "+data_part[1]) 
    acy = hex_to_signed_int(data_part[2]+" "+data_part[3]) 
    acz = hex_to_signed_int(data_part[4]+" "+data_part[5]) 

    # 解析角速度 (后12字节)      
    gyx = hex_to_signed_int(data_part[6]+" "+data_part[7]) / 1000.0
    gyy = hex_to_signed_int(data_part[8]+" "+data_part[9]) / 1000.0
    gyz = hex_to_signed_int(data_part[10]+" "+data_part[11]) / 1000.0
    
    return {
        'acceleration': {'x': acx, 'y': acy, 'z': acz},
        'gyroscope': {'x': gyx, 'y': gyy, 'z': gyz}
    }

def main():
    ser = None
    print(f"尝试连接到串口: {SERIAL_PORT}，波特率: {BAUD_RATE}")
    
    # 新增变量用于角度计算
    last_time = None
    last_gyro = None
    current_angles = {'x': 0.0, 'y': 0.0, 'z': 0.0}

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
        print("串口连接成功！")
        
        # 先发送停止采样命令
        ser.write(CMD_STOP_SAMPLING)
        print(f"已发送停止采样指令: {CMD_STOP_SAMPLING.hex()}")
        time.sleep(1)
        
        # 再发送开始采样命令
        ser.write(CMD_START_SAMPLING)
        print(f"已发送开始采样指令: {CMD_START_SAMPLING.hex()}")
        time.sleep(1)
        
        # 读取并解析3次数据
        data_buffer = []  # 改为列表存储分割后的数据
        frames_received = 0
        
        while frames_received < 1000:
            if ser.in_waiting > 0:
                # 读取并分割数据
                raw_data = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
                new_items = raw_data.split()
                data_buffer.extend(new_items)
                
                # 逐个检查帧头
                while len(data_buffer) >= 22:
                    if data_buffer[0] == '5a' and data_buffer[1] == '4a':
                        # print("找到帧头 5a 4a")
                        frame_hex = data_buffer[:22]
                        try:
                            parsed = parse_sensor_raw_data(frame_hex)
                            frames_received += 1
                            
                            # 计算角度变化
                            current_time = time.time()
                            if last_time is not None and last_gyro is not None:
                                time_diff = current_time - last_time
                                # 角度变化 = 角速度 * 时间差
                                # 在文件顶部添加
                                import math
                                RAD_TO_DEG = 180 / math.pi
                                current_angles['x'] += parsed['gyroscope']['x'] * time_diff * RAD_TO_DEG
                                current_angles['y'] += parsed['gyroscope']['y'] * time_diff * RAD_TO_DEG
                                current_angles['z'] += parsed['gyroscope']['z'] * time_diff * RAD_TO_DEG
                            
                            last_time = current_time
                            last_gyro = parsed['gyroscope']
                            
                            print(f"\n=== 第 {frames_received} 次读取数据 ===")
                            print(f"原始数据 (HEX): {' '.join(frame_hex)}")
                            print("解析结果:")
                            # print(f"  加速度 (g): X={parsed['acceleration']['x']:.3f}, Y={parsed['acceleration']['y']:.3f}, Z={parsed['acceleration']['z']:.3f}")
                            print(f"  加速度 (g): X={parsed['acceleration']['x']}, Y={parsed['acceleration']['y']}, Z={parsed['acceleration']['z']}")
                            print(f"  角速度 (°/s): X={parsed['gyroscope']['x']:.3f}, Y={parsed['gyroscope']['y']:.3f}, Z={parsed['gyroscope']['z']:.3f}")
                            print(f"  当前角度 (°): X={current_angles['x']:.3f}, Y={current_angles['y']:.3f}, Z={current_angles['z']:.3f}")
                            
                            # 移除已处理的数据
                            data_buffer = data_buffer[22:]
                            break
                            
                        except ValueError as e:
                            print(f"数据解析错误: {e}")
                            data_buffer.pop(0)

                    else:
                        # print(f"未找到帧头，当前头: {data_buffer[0]} {data_buffer[1]}")
                        data_buffer.pop(0)
            time.sleep(0.01)
            
    except serial.SerialException as e:
        print(f"串口错误: {e}")
        list_serial_ports()
    except Exception as e:
        print(f"发生未知错误: {e}")
    finally:
        if ser and ser.is_open:
            ser.close()
            print("串口已关闭。")

if __name__ == "__main__":
    main()