class HTMLGenerator:
    @staticmethod
    def generate_device_card(device):
        """生成设备卡片HTML"""
        summary_items = device['summary'].split(', ')
        summary_links = []
      
        section_mapping = {
            '内存': '内存使用',
            '磁盘': '磁盘使用',
            '服务状态': '服务状态',
            '硬件状态': '硬件错误检查',
            'Core文件': 'Core文件检查',
            '内存池': 'Updpi内存池检查',
            '回填率': '回填率',
            '流量情况': '流量情况',
            '策略加载': '策略加载信息',
            '策略下发': '策略下发检查'
        }
      
        for item in summary_items:
            if ': ' in item:
                name, status = item.split(': ')
                section_name = section_mapping.get(name, name)
                if '告警' in status:
                    color = '#FF4444'  # 红色
                elif 'OK' in status.upper():
                    color = '#4CAF50'  # 绿色
                else:
                    color = '#000000'  # 黑色
              
                summary_links.append(
                    f'<span style="margin-right: 15px;"><a href="device_{device["ip"]}.html?section={section_name}" '
                    f'style="color: {color};">{name}: {status}</a></span>'
                )
      
        return f'''
            <div class="device-card">
                <h3>IP: {device['ip']}</h3>
                <p>主机名: {device['hostname']}</p>
                <p style="display: flex; flex-wrap: wrap;">{"".join(summary_links)}</p>
                <p><a href="device_{device['ip']}.html?show=all" class="view-report">查看完整报告</a></p>
                <hr>
            </div>
        '''

    @staticmethod
    def generate_index_page(check_results):
        """生成索引页面"""
        devices_html = ''.join(HTMLGenerator.generate_device_card(device) for device in check_results)
        
        # 获取当前日期
        from datetime import datetime
        current_date = datetime.now().strftime('%Y-%m-%d')
      
        return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>系统巡检报告 - {current_date}</title>
<style>
body {{
    font-family: Arial, sans-serif;
    margin: 20px;
    background-color: #f5f5f5;
}}
h1 {{
    color: #333;
    text-align: center;
    margin-bottom: 30px;
}}
.device-list {{
    max-width: 1200px;
    margin: 0 auto;
    background-color: white;
    padding: 20px;
    border-radius: 5px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}}
.device-card {{
    padding: 15px;
    margin-bottom: 20px;
    border-radius: 5px;
}}
.device-card:hover {{
    background-color: #f8f8f8;
}}
.device-card h3 {{
    margin: 0 0 10px 0;
    color: #333;
}}
.device-card p {{
    margin: 5px 0;
}}
.view-report {{
    display: inline-block;
    margin-top: 10px;
    padding: 5px 15px;
    background-color: #4CAF50;
    color: white;
    text-decoration: none;
    border-radius: 3px;
}}
.view-report:hover {{
    background-color: #45a049;
}}
hr {{
    border: none;
    border-top: 1px solid #eee;
    margin: 15px 0;
}}
a {{
    text-decoration: none;
}}
</style>
</head>
<body>
<h1>系统巡检报告 - {current_date}</h1>
<div class="device-list">
{devices_html}
</div>
</body>
</html>'''

    @staticmethod
    def format_service_status(content):
        """保持原始格式显示服务状态"""
        # 将内容按行分割
        lines = content.strip().split('\n')
      
        # 创建一个带有等宽字体的预格式化文本块
        formatted_content = f'''
        <pre style="font-family: 'Courier New', Courier, monospace; 
                    white-space: pre; 
                    font-size: 14px;
                    line-height: 1.5;
                    padding: 15px;
                    background-color: white;
                    border-radius: 4px;
                    overflow-x: auto;">
{content}
</pre>
        '''
      
        return formatted_content

    @staticmethod
    def generate_device_detail_page(device):
        """生成单个设备的详细信息页面"""
        sections_html = ''
        summary_items = device['summary'].split(', ')
        formatted_summary = []
      
        # 统一的部分名称映射
        section_mapping = {
            '内存': '内存使用',
            '磁盘': '磁盘使用',
            '服务状态': '服务状态',
            '硬件状态': '硬件错误检查',
            'Core文件': 'Core文件检查',
            '内存池': 'Updpi内存池检查',
            '回填率': '回填率',
            '流量情况': '流量情况',
            '策略加载': '策略加载信息',
            '策略下发': '策略下发检查'
        }
      
        # 记录告警部分
        warning_sections = set()
        for item in summary_items:
            if ': ' in item:
                name, status = item.split(': ')
                section_name = section_mapping.get(name, name)
                if '告警' in status:
                    warning_sections.add(section_name)
                
                # 设置颜色
                if '告警' in status:
                    color = '#FF4444'  # 红色
                elif 'OK' in status.upper():
                    color = '#4CAF50'  # 绿色
                else:
                    color = '#000000'  # 黑色
                
                # 添加可点击的链接，直接使用section_name作为锚点
                formatted_summary.append(
                    f'<a href="javascript:void(0)" onclick="showSection(\'{section_name}\')" '
                    f'style="margin-right: 15px; text-decoration: none; color: {color};">{name}: {status}</a>'
                )
      
        # 生成每个部分的HTML
        for name, content in device['sections'].items():
            # 使用映射后的名称作为ID
            section_id = name
            display_name = name
            
            # 检查是否需要映射回原始名称
            for orig_name, mapped_name in section_mapping.items():
                if mapped_name == name:
                    section_id = mapped_name
                    display_name = orig_name
                    break
            
            has_warning = section_id in warning_sections or '[告警]' in content
          
            if has_warning:
                header_style = 'background-color: #FF4444; color: white;'
                content_style = 'background-color: #FFEBEE;'
            else:
                header_style = 'background-color: #f0f0f0;'
                content_style = ''
          
            formatted_content = content
            if '[告警]' in content:
                formatted_content = content.replace('[告警]', '<span style="color: #FF4444; font-weight: bold;">[告警]</span>')
          
            # 对服务状态部分进行特殊处理
            if name == '服务状态':
                formatted_content = HTMLGenerator.format_service_status(formatted_content)
            else:
                formatted_content = f'<pre style="margin: 10px; padding: 10px; font-family: monospace; white-space: pre-wrap;">{formatted_content}</pre>'
          
            sections_html += f'''
                <div class="section" id="section_{section_id}">
                    <h3 onclick="toggleSection('{section_id}')" style="cursor: pointer; padding: 10px; {header_style}">
                        ▶ {display_name}
                    </h3>
                    <div id="content_{section_id}" style="display: none; {content_style}">
                        {formatted_content}
                    </div>
                </div>
                <hr>
            '''
        
        # 获取当前日期
        from datetime import datetime
        current_date = datetime.now().strftime('%Y-%m-%d')
      
        return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>设备 {device['ip']} 巡检报告 - {current_date}</title>
<style>
body {{
    font-family: Arial, sans-serif;
    margin: 20px;
    background-color: #f5f5f5;
    padding-top: 150px; /* 增加顶部内边距，为固定头部留出更多空间 */
}}
.header-fixed {{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background-color: white;
    padding: 15px 20px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    z-index: 1000;
}}
.content-container {{
    margin-top: 20px; /* 为内容添加额外的顶部边距 */
}}
.summary-link {{
    display: inline-block;
    margin: 5px 10px;
    padding: 3px 8px;
    border-radius: 3px;
    cursor: pointer;
}}
.summary-link:hover {{
    background-color: #f0f0f0;
}}
.warning {{
    color: #FF4444;
}}
.ok {{
    color: #4CAF50;
}}
.back-link {{
    margin-right: 20px;
}}
.control-buttons {{
    margin-top: 10px;
}}
.control-button {{
    padding: 5px 10px;
    margin-right: 10px;
    border: none;
    border-radius: 3px;
    background-color: #4CAF50;
    color: white;
    cursor: pointer;
}}
.control-button:hover {{
    background-color: #45a049;
}}
</style>
<script>
function toggleSection(id) {{
    var content = document.getElementById('content_' + id);
    var header = document.querySelector('#section_' + id + ' h3');
    if (content.style.display === 'none') {{
        content.style.display = 'block';
        header.innerHTML = header.innerHTML.replace('▶', '▼');
    }} else {{
        content.style.display = 'none';
        header.innerHTML = header.innerHTML.replace('▼', '▶');
    }}
}}

function showSection(id) {{
    var allContents = document.querySelectorAll('[id^="content_"]');
    var allHeaders = document.querySelectorAll('.section h3');
    
    allContents.forEach(function(content) {{
        content.style.display = 'none';
    }});
    
    allHeaders.forEach(function(header) {{
        header.innerHTML = header.innerHTML.replace('▼', '▶');
    }});
    
    var content = document.getElementById('content_' + id);
    var header = document.querySelector('#section_' + id + ' h3');
    
    if (content && header) {{
        content.style.display = 'block';
        header.innerHTML = header.innerHTML.replace('▶', '▼');
        
        // 滚动到该部分，考虑固定头部的高度
        var headerHeight = document.querySelector('.header-fixed').offsetHeight;
        var sectionTop = document.getElementById('section_' + id).getBoundingClientRect().top;
        var scrollPosition = window.pageYOffset + sectionTop - headerHeight - 30; // 增加额外的偏移量
        var scrollPosition = window.pageYOffset + sectionTop - headerHeight - 20;
        
        window.scrollTo({{
            top: scrollPosition,
            behavior: 'smooth'
        }});
    }}
}}

function toggleAll(show) {{
    var allContents = document.querySelectorAll('[id^="content_"]');
    var allHeaders = document.querySelectorAll('.section h3');
    
    allContents.forEach(function(content) {{
        content.style.display = show ? 'block' : 'none';
    }});
    
    allHeaders.forEach(function(header) {{
        if (show) {{
            header.innerHTML = header.innerHTML.replace('▶', '▼');
        }} else {{
            header.innerHTML = header.innerHTML.replace('▼', '▶');
        }}
    }});
}}

window.onload = function() {{
    var urlParams = new URLSearchParams(window.location.search);
    var showAll = urlParams.get('show') === 'all';
    var targetSection = urlParams.get('section');
  
    if (showAll) {{
        toggleAll(true);
    }} else if (targetSection) {{
        showSection(targetSection);
    }}
}}
</script>
</head>
<body>
<div class="header-fixed">
    <a href="index.html" class="back-link">返回设备列表</a>
    <strong>IP: {device['ip']}</strong> | 
    主机名: {device['hostname']} | 
    检查时间: {device['check_time']}
    <div class="control-buttons">
        <button class="control-button" onclick="toggleAll(true)">全部展开</button>
        <button class="control-button" onclick="toggleAll(false)">全部折叠</button>
    </div>
</div>

<div class="content-container">
    <h1>设备巡检详细信息</h1>
    <hr>
    <h3>巡检总结:</h3>
    <p style="line-height: 2;">{''.join(formatted_summary)}</p>
    <hr>
    <div>{sections_html}</div>
</div>
</body>
</html>'''