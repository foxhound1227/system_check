import requests
from PIL import Image
import io

def download_and_create_icon():
    # 从 flaticon 获取一个系统监控相关的图标
    url = "https://cdn-icons-png.flaticon.com/512/1802/1802979.png"
    try:
        response = requests.get(url)
        img = Image.open(io.BytesIO(response.content))
        
        # 调整图片大小并保存为ico格式
        img = img.resize((256, 256))
        img.save("system_check.ico", format='ICO')
        print("图标已成功创建：system_check.ico")
    except Exception as e:
        print(f"创建图标时出错：{e}")
        return False
    return True

if __name__ == "__main__":
    download_and_create_icon()