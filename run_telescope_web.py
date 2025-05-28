#!/usr/bin/env python3
"""
望远镜控制Web界面启动脚本
"""
import subprocess
import webbrowser
import time
import os
import sys

# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))

def check_dependencies():
    """检查依赖项"""
    try:
        import flask
        import serial
    except ImportError:
        print("正在安装必要的依赖项...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "pyserial"])
        print("依赖项安装完成")

def main():
    """主函数"""
    print("检查依赖项...")
    check_dependencies()
    
    print("启动望远镜控制Web界面...")
    # 启动Flask应用
    web_process = subprocess.Popen([sys.executable, "telescope_web.py"])
    
    # 等待Flask启动
    print("等待服务启动...")
    time.sleep(2)
    
    # 打开浏览器
    print("在浏览器中打开控制界面...")
    webbrowser.open('http://127.0.0.1:5001')
    
    try:
        print("按 Ctrl+C 停止服务...")
        web_process.wait()
    except KeyboardInterrupt:
        print("正在停止服务...")
        web_process.terminate()
        web_process.wait()
    
    print("服务已停止")

if __name__ == "__main__":
    main() 