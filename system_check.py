#!/usr/bin/env python
# -*- coding: utf-8 -*-

import psutil
import subprocess
import time
from datetime import datetime
import csv
import socket
import os
import re
import tkinter as tk
from tkinter import ttk, filedialog
import webbrowser
from html_generator import HTMLGenerator

# 配置告警阈值
MEMORY_THRESHOLD = 80  # 内存使用率告警阈值（%）
DISK_THRESHOLD = 80    # 磁盘使用率告警阈值（%）

# 需要检查的服务列表
SERVICES = [
    "updpi.service",
    "upp.service",
    "upload.service",
    "logtar.service",
    "tnlinfo_proxy.service"
]

# 纯 HTML 模板，无 CSS
HTML_TEMPLATE = '''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>系统巡检报告</title>
</head>
<body>
<h1>系统巡检报告汇总</h1>
<hr>
<div>{device_links}</div>
<hr>
<div>{device_details}</div>
<script>
function showDevice(ip) {{
    var details = document.getElementsByClassName('device-details');
    for(var i = 0; i < details.length; i++) {{
        details[i].style.display = 'none';
    }}
    document.getElementById('device-' + ip).style.display = 'block';
}}
document.addEventListener('DOMContentLoaded', function() {{
    var headers = document.getElementsByClassName('section-header');
    for(var i = 0; i < headers.length; i++) {{
        headers[i].addEventListener('click', function() {{
            var content = this.nextElementSibling;
            if(content.style.display === 'none' || content.style.display === '') {{
                content.style.display = 'block';
            }} else {{
                content.style.display = 'none';
            }}
        }});
    }}
    var firstDevice = document.getElementsByClassName('device-details')[0];
    if(firstDevice) {{
        firstDevice.style.display = 'block';
    }}
}});
</script>
</body>
</html>'''

def get_hostname():
    """获取主机名"""
    return socket.gethostname()

# 在文件顶部导入部分添加
import sys

def get_system_version():
    """获取系统版本"""
    try:
        # 在Windows系统上，使用不同的方法获取系统版本
        if os.name == 'nt':
            import platform
            return platform.platform()
        else:
            with open('/etc/redhat-release', 'r') as f:
                return f.read().strip()
    except:
        return "Unknown"

def get_uptime():
    """获取系统运行时间"""
    try:
        # 在Windows系统上，使用不同的方法获取系统运行时间
        if os.name == 'nt':
            import time
            import ctypes
            
            lib = ctypes.windll.kernel32
            t = lib.GetTickCount64()
            t = int(t / 1000)
            
            return time.strftime('%d天%H小时%M分钟', time.gmtime(t))
        else:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                return time.strftime('%d天%H小时%M分钟', time.gmtime(uptime_seconds))
    except:
        return "Unknown"

def check_service_status(service_name):
    """检查服务状态和运行时间"""
    try:
        # 在Windows系统上，使用不同的方法检查服务状态
        if os.name == 'nt':
            import subprocess
            import re
            from datetime import datetime, timedelta
            
            # 使用sc查询服务状态
            status_cmd = f"sc query {service_name}"
            status_output = subprocess.check_output(status_cmd, shell=True).decode()
            
            # 解析状态
            if "RUNNING" in status_output:
                status = "active"
                return status, "运行中"
            else:
                status = "inactive"
                return status, "未运行"
        else:
            status_cmd = "systemctl is-active {}".format(service_name)
            status = subprocess.check_output(status_cmd, shell=True).decode().strip()
          
            if status == "active":
                time_cmd = "systemctl show {} --property=ActiveEnterTimestamp".format(service_name)
                time_output = subprocess.check_output(time_cmd, shell=True).decode().strip()
                start_time = time_output.split('=')[1]
                start_datetime = datetime.strptime(start_time, '%a %Y-%m-%d %H:%M:%S %Z')
                running_time = datetime.now() - start_datetime
                return status, str(running_time).split('.')[0]
            return status, "未运行"
    except:
        return "unknown", "未知"

def get_memory_usage():
    """获取内存使用率"""
    memory = psutil.virtual_memory()
    return memory.percent

def get_disk_usage():
    """获取根分区磁盘使用率"""
    disk = psutil.disk_usage('/')
    return disk.percent

def generate_csv_data():
    """生成CSV格式数据"""
    data = {}
  
    # 基本信息
    data['检查时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data['主机名'] = get_hostname()
    data['系统版本'] = get_system_version()
  
    # 资源使用情况
    memory_usage = get_memory_usage()
    data['内存使用率'] = "{:.1f}%".format(memory_usage)
    data['内存状态'] = "告警" if memory_usage > MEMORY_THRESHOLD else "正常"
  
    disk_usage = get_disk_usage()
    data['磁盘使用率'] = "{:.1f}%".format(disk_usage)
    data['磁盘状态'] = "告警" if disk_usage > DISK_THRESHOLD else "正常"
  
    data['系统运行时间'] = get_uptime()
  
    # 服务状态
    for service in SERVICES:
        status, running_time = check_service_status(service)
        data[service + '_状态'] = status
        data[service + '_运行时间'] = running_time
        data[service + '_告警'] = "告警" if status != "active" else "正常"
  
    return data

def main():
    """主函数"""
    csv_file = 'system_check_report.csv'
    data = generate_csv_data()
  
    # 检查文件是否存在
    file_exists = os.path.isfile(csv_file)
  
    # 使用 GBK 编码，并使用逗号作为分隔符
    with open(csv_file, 'a', newline='', encoding='gbk') as f:
        writer = csv.DictWriter(f, fieldnames=data.keys(), delimiter=',', quoting=csv.QUOTE_ALL)
      
        # 如果文件不存在，写入表头
        if not file_exists:
            writer.writeheader()
      
        writer.writerow(data)
  
    # 创建用于打开 CSV 的 bat 文件
    bat_content = '''@echo off
    start excel.exe "%~dp0system_check_report.csv"'''
  
    with open('open_report.bat', 'w') as f:
        f.write(bat_content)
  
    print("报告已保存到: {}".format(csv_file))
    print("请使用 open_report.bat 打开报告文件")

def parse_check_log(file_path):
    """解析日志文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
  
    # 解析基本信息
    ip = os.path.basename(file_path).split('_')[0]
    hostname = re.search(r'主机名: (.*)', content).group(1)
    check_time = re.search(r'系统巡检报告 \| (.*) =====', content).group(1)
  
    # 直接提取两个 ---- 之间的内容
    sections = {}
    current_section = None
    section_content = []
  
    for line in content.split('\n'):
        if line.startswith('---- ') and line.endswith(' ----'):
            if current_section and section_content:
                sections[current_section] = '\n'.join(section_content)
                section_content = []
            current_section = line[5:-5]  # 去掉前后的 ---- 和空格
        elif current_section:
            section_content.append(line)
  
    # 处理最后一个部分
    if current_section and section_content:
        sections[current_section] = '\n'.join(section_content)
  
    summary = re.search(r'巡检总结: (.*)', content).group(1)
  
    return {
        'ip': ip,
        'hostname': hostname,
        'check_time': check_time,
        'sections': sections,
        'summary': summary
    }

class SystemCheckGUI:
    def __init__(self, root):
        """初始化GUI界面"""
        self.root = root
        self.root.title("系统巡检报告生成器")
      
        # 设置窗口大小和位置
        window_width = 600
        window_height = 500
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
      
        # 设置整体样式
        self.root.configure(bg='#f0f0f0')
        style = ttk.Style()
        style.configure('TButton', padding=6)
        style.configure('TLabel', background='#f0f0f0')
        style.configure('TFrame', background='#f0f0f0')
      
        # 创建主框架，使用固定的padding
        main_frame = ttk.Frame(root, padding="20 20 20 20")
        main_frame.pack(fill=tk.BOTH, expand=True)
      
        # 标题
        title_label = ttk.Label(
            main_frame, 
            text="系统巡检报告生成器", 
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 20))
      
        # 创建输入区域框架，使用Grid布局
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(0, 20))
        input_frame.grid_columnconfigure(1, weight=1)  # 让输入框列可以扩展
      
        # 日志目录选择（使用Grid布局）
        dir_label = ttk.Label(
            input_frame, 
            text="日志目录:",
            width=10,
            anchor='e'  # 右对齐
        )
        dir_label.grid(row=0, column=0, padx=(0, 10), pady=5, sticky='e')
      
        self.dir_entry = ttk.Entry(input_frame)
        self.dir_entry.grid(row=0, column=1, padx=(0, 10), pady=5, sticky='ew')
      
        browse_btn = ttk.Button(
            input_frame,
            text="浏览",
            command=self.browse_directory,
            width=10
        )
        browse_btn.grid(row=0, column=2, pady=5)
      
        # 创建文件列表框架，减小高度占比
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
      
        # 添加标签
        list_label = ttk.Label(
            list_frame,
            text="发现的日志文件:",
            anchor='w'
        )
        list_label.pack(fill=tk.X, padx=5, pady=(0, 5))
      
        # 创建文件列表框和滚动条，设置合适的高度
        list_scroll = ttk.Scrollbar(list_frame)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
      
        self.file_listbox = tk.Listbox(
            list_frame,
            height=8,  # 调整显示行数
            yscrollcommand=list_scroll.set,
            selectmode=tk.EXTENDED,
            font=('Courier', 9)
        )
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        list_scroll.config(command=self.file_listbox.yview)
      
        # 创建按钮区域框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 20))  # 增加上边距
      
        # 按钮水平布局框架
        buttons_horizontal = ttk.Frame(button_frame)
        buttons_horizontal.pack()
      
        # 生成报告按钮
        generate_btn = ttk.Button(
            buttons_horizontal,
            text="生成报告",
            command=self.generate_report,
            width=20
        )
        generate_btn.pack(side=tk.LEFT, padx=5)
      
        # 查看报告按钮
        self.view_btn = ttk.Button(
            buttons_horizontal,
            text="查看报告",
            command=self.view_report,
            width=20,
            state='disabled'  # 初始状态为禁用
        )
        self.view_btn.pack(side=tk.LEFT, padx=5)
      
        # 状态显示区域
        self.status_label = ttk.Label(
            main_frame,
            text="请选择日志文件目录",
            wraplength=500,
            justify=tk.CENTER,
            font=('Arial', 10)
        )
        self.status_label.pack(fill=tk.X, pady=10)
      
        # 版权信息
        copyright_label = ttk.Label(
            main_frame,
            text="© 2024 系统巡检报告生成器",
            font=('Arial', 8),
            foreground='gray'
        )
        copyright_label.pack(side=tk.BOTTOM, pady=10)
      
        # 存储日志目录路径
        self.log_dir = ""

    def browse_directory(self):
        """选择目录对话框"""
        directory = filedialog.askdirectory(
            title="选择日志文件目录",
            initialdir="."
        )
        if directory:
            self.log_dir = directory
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
          
            # 检查日志文件
            self.check_log_files()
          
            # 检查是否存在报告文件
            if os.path.exists(os.path.join(directory, 'index.html')):
                self.view_btn.config(state='normal')
            else:
                self.view_btn.config(state='disabled')

    def check_log_files(self):
        """检查并显示日志文件"""
        if not self.log_dir:
            return
          
        self.file_listbox.delete(0, tk.END)  # 清空列表
      
        try:
            # 同时支持 .log 和 .log.txt 结尾的文件
            log_files = [f for f in os.listdir(self.log_dir) 
                        if f.endswith(('.log', '.log.txt'))]
          
            if not log_files:
                self.file_listbox.insert(tk.END, "未找到日志文件")
                self.status_label.config(text="未找到日志文件")
                return
          
            for file in sorted(log_files):
                self.file_listbox.insert(tk.END, file)
          
            self.status_label.config(text=f"找到 {len(log_files)} 个日志文件")
        except Exception as e:
            self.status_label.config(text=f"读取目录出错: {str(e)}")

    def format_service_status(self, content):
        """格式化服务状态内容"""
        # 移除所有的 '---' 和 '|'
        lines = content.split('\n')
        formatted_lines = []
      
        for line in lines:
            # 跳过空行和只包含分隔符的行
            if not line.strip() or line.strip().replace('-', '') == '':
                continue
          
            # 移除 '|' 并分割字段
            fields = [field.strip() for field in line.replace('|', '').split('  ') if field.strip()]
          
            # 确保至少有4个字段（服务名称、状态、版本、运行时长）
            if len(fields) >= 4:
                # 使用固定宽度格式化每个字段
                formatted_line = f"{fields[0]:<20} {fields[1]:<10} {fields[2]:<20} {fields[3]:<15}"
                formatted_lines.append(formatted_line)
      
        return '\n'.join(formatted_lines)

    def parse_check_log(self, file_path):
        """解析日志文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
      
        # 解析基本信息
        ip = os.path.basename(file_path).split('_')[0]
        hostname = re.search(r'主机名: (.*)', content).group(1)
        check_time = re.search(r'系统巡检报告 \| (.*) =====', content).group(1)
      
        # 直接提取两个 ---- 之间的内容
        sections = {}
        current_section = None
        section_content = []
      
        for line in content.split('\n'):
            if line.startswith('---- ') and line.endswith(' ----'):
                if current_section and section_content:
                    sections[current_section] = '\n'.join(section_content)
                    section_content = []
                current_section = line[5:-5]  # 去掉前后的 ---- 和空格
            elif current_section:
                section_content.append(line)
      
        # 处理最后一个部分
        if current_section and section_content:
            sections[current_section] = '\n'.join(section_content)
      
        # 确保关键部分使用统一的名称
        section_mapping = {
            '内存使用': '内存使用',
            '磁盘使用': '磁盘使用',
            '服务状态': '服务状态'
        }
        
        # 重命名部分以确保一致性
        renamed_sections = {}
        for name, content in sections.items():
            if name in section_mapping:
                renamed_sections[section_mapping[name]] = content
            else:
                renamed_sections[name] = content
        
        summary = re.search(r'巡检总结: (.*)', content).group(1)
      
        return {
            'ip': ip,
            'hostname': hostname,
            'check_time': check_time,
            'sections': renamed_sections,
            'summary': summary
        }
    def generate_report(self):
        """生成报告"""
        if not self.log_dir:
            self.status_label.config(text="请先选择日志文件目录")
            return
          
        try:
            self.status_label.config(text="正在生成报告...")
            self.root.update()
          
            # 清理旧的HTML文件
            for file in os.listdir(self.log_dir):
                if file.endswith('.html'):
                    try:
                        os.remove(os.path.join(self.log_dir, file))
                    except Exception as e:
                        print(f"删除文件 {file} 时出错: {str(e)}")
          
            check_results = []
            # 同时支持 .log 和 .log.txt 结尾的文件
            log_files = [f for f in os.listdir(self.log_dir) 
                        if f.endswith(('.log', '.log.txt'))]
          
            if not log_files:
                self.status_label.config(text="未找到日志文件")
                return
          
            total_files = len(log_files)
            for i, file in enumerate(log_files, 1):
                self.status_label.config(text=f"正在处理: {file} ({i}/{total_files})")
                self.root.update()
              
                file_path = os.path.join(self.log_dir, file)
                result = self.parse_check_log(file_path)
                check_results.append(result)
          
            # 使用HTMLGenerator生成页面
            index_html = HTMLGenerator.generate_index_page(check_results)
            with open(os.path.join(self.log_dir, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(index_html)
          
            for i, device in enumerate(check_results, 1):
                self.status_label.config(text=f"正在生成设备报告: {device['ip']} ({i}/{len(check_results)})")
                self.root.update()
              
                detail_html = HTMLGenerator.generate_device_detail_page(device)
                with open(os.path.join(self.log_dir, f'device_{device["ip"]}.html'), 'w', encoding='utf-8') as f:
                    f.write(detail_html)
          
            self.status_label.config(text=f"成功生成报告！处理了 {len(check_results)} 个设备的数据")
            self.view_btn.config(state='normal')
          
        except Exception as e:
            self.status_label.config(text=f"错误: {str(e)}")
            print(f"生成报告时出错: {str(e)}")

    def view_report(self):
        """打开报告文件"""
        if not self.log_dir:
            self.status_label.config(text="未找到报告目录")
            return
            
        index_path = os.path.join(self.log_dir, 'index.html')
        if not os.path.exists(index_path):
            self.status_label.config(text="报告文件不存在")
            return
          
        try:
            webbrowser.open(f'file://{os.path.abspath(index_path)}')
            self.status_label.config(text="已打开报告")
        except Exception as e:
            self.status_label.config(text=f"打开报告失败: {str(e)}")

def main():
    root = tk.Tk()
    app = SystemCheckGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()