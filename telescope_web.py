from flask import Flask, render_template, request, jsonify
import serial.tools.list_ports
import time
import threading
from datetime import datetime
import logging
import sys
import os

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# 导入望远镜控制器
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from transform_control import TelescopeController
    from virtual_device_test import VirtualGyro
    logging.info("成功导入望远镜控制模块")
except Exception as e:
    logging.error(f"导入望远镜控制模块失败: {e}")
    sys.exit(1)

app = Flask(__name__)

# 全局变量
telescope = None
control_thread = None
running = False
status = {
    "current_az": 0.0,
    "current_alt": 0.0,
    "target_az": 0.0,
    "target_alt": 0.0,
    "current_time": "",
    "status": "就绪"
}

def get_serial_ports():
    """获取所有可用的串口"""
    try:
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        logging.info(f"检测到可用串口: {port_list}")
        return port_list
    except Exception as e:
        logging.error(f"获取串口列表失败: {e}")
        return []

def update_status():
    """更新状态"""
    global status, telescope, running
    
    while running:
        try:
            if telescope and telescope.gyro:
                current_az, current_alt = telescope.gyro.get_current_attitude()
                status["current_az"] = round(current_az, 2)
                status["current_alt"] = round(current_alt, 2)
                status["target_az"] = round(telescope.target_azimuth, 2)
                status["target_alt"] = round(telescope.target_altitude, 2)
            
            status["current_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logging.error(f"更新状态时出错: {e}")
        
        time.sleep(0.5)

def telescope_control():
    """望远镜控制线程"""
    global telescope, running, status
    
    if telescope:
        status["status"] = "控制中..."
        try:
            result = telescope.control_loop()
            if result == 0:
                status["status"] = "已到达目标"
            else:
                status["status"] = "控制失败"
        except Exception as e:
            status["status"] = f"错误: {str(e)}"
            logging.error(f"控制异常: {e}")
        
        running = False

@app.route('/')
def index():
    """主页"""
    logging.info("访问主页")
    serial_ports = get_serial_ports()
    return render_template('telescope.html', serial_ports=serial_ports)

@app.route('/status')
def get_status():
    """获取当前状态"""
    return jsonify(status)

@app.route('/start', methods=['POST'])
def start_telescope():
    """启动望远镜"""
    global telescope, control_thread, running, status
    
    if running:
        return jsonify({"success": False, "message": "望远镜已在运行中"})
    
    # 获取表单数据
    try:
        mode = request.form.get('mode')
        port = request.form.get('port')
        coordinate_type = request.form.get('coordinate_type')
        
        logging.info(f"启动参数 - 模式: {mode}, 串口: {port}, 坐标类型: {coordinate_type}")
        
        # 创建虚拟陀螺仪（在模拟和半实物模式下使用）
        gyro = None
        if mode == 'simulation' or mode == 'hybrid':
            gyro = VirtualGyro()
            logging.info("已创建虚拟陀螺仪")
        
        # 创建望远镜控制器
        simulation = (mode == 'simulation')
        hybrid_sim = (mode == 'hybrid')
        
        if mode == 'real' or mode == 'hybrid':
            if not port:
                return jsonify({"success": False, "message": "请选择串口"})
            
            logging.info(f"创建望远镜控制器 - 串口: {port}, 模拟: {simulation}, 半实物: {hybrid_sim}")
            telescope = TelescopeController(
                port=port,
                baudrate=115200,
                gyro=gyro,
                simulation=simulation,
                hybrid_sim=hybrid_sim
            )
        else:  # 纯模拟模式
            logging.info("创建望远镜控制器 - 纯模拟模式")
            telescope = TelescopeController(
                gyro=gyro,
                simulation=True
            )
        
        # 设置目标
        if coordinate_type == 'equatorial':
            ra = float(request.form.get('ra'))
            dec = float(request.form.get('dec'))
            lat = float(request.form.get('lat'))
            lon = float(request.form.get('lon'))
            current_time = datetime.now()
            
            logging.info(f"设置赤道坐标 - 赤经: {ra}h, 赤纬: {dec}°, 纬度: {lat}°, 经度: {lon}°")
            telescope.set_target(ra, dec, lat, lon, current_time)
            
        else:  # 地平坐标
            az = float(request.form.get('az'))
            alt = float(request.form.get('alt'))
            
            logging.info(f"设置地平坐标 - 方位角: {az}°, 高度角: {alt}°")
            telescope.set_target(az, alt, coordinate_type='horizontal')
        
        # 启动状态更新线程
        running = True
        status_thread = threading.Thread(target=update_status)
        status_thread.daemon = True
        status_thread.start()
        logging.info("状态更新线程已启动")
        
        # 启动控制线程
        control_thread = threading.Thread(target=telescope_control)
        control_thread.daemon = True
        control_thread.start()
        logging.info("控制线程已启动")
        
        return jsonify({"success": True, "message": "望远镜已启动"})
        
    except Exception as e:
        logging.error(f"启动错误: {e}")
        return jsonify({"success": False, "message": f"错误: {str(e)}"})

@app.route('/stop', methods=['POST'])
def stop_telescope():
    """停止望远镜"""
    global telescope, running, status
    
    if not running:
        return jsonify({"success": False, "message": "望远镜未运行"})
    
    logging.info("停止望远镜")
    running = False
    status["status"] = "已停止"
    
    if telescope:
        try:
            telescope.close()
            logging.info("望远镜控制器已关闭")
        except Exception as e:
            logging.error(f"关闭错误: {e}")
    
    return jsonify({"success": True, "message": "望远镜已停止"})

if __name__ == '__main__':
    try:
        # 先尝试在localhost上启动
        logging.info("在127.0.0.1:5001上启动服务...")
        app.run(debug=True, host='127.0.0.1', port=5001)
    except Exception as e:
        logging.error(f"在127.0.0.1上启动失败: {e}")
        try:
            # 如果失败，尝试在所有接口上启动
            logging.info("在0.0.0.0:5001上启动服务...")
            app.run(debug=True, host='0.0.0.0', port=5001)
        except Exception as e:
            logging.error(f"在0.0.0.0上启动失败: {e}")
            # 如果两种方式都失败，尝试在5001端口上启动
            logging.info("尝试在127.0.0.1:5001上启动服务...")
            app.run(debug=True, host='127.0.0.1', port=5001) 