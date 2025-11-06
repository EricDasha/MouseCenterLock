import os
import sys
import requests
from concurrent.futures import ThreadPoolExecutor

def download_wallpaper(wallpaper_url, wallpaper_path):
    """
    下载单张壁纸。

    :param wallpaper_url: 壁纸的 URL。
    :param wallpaper_path: 保存路径。
    """
    try:
        response = requests.get(wallpaper_url)
        response.raise_for_status()  # 检查请求是否成功
        img_data = response.content
        with open(wallpaper_path, "wb") as f:
            f.write(img_data)
        print(f"壁纸已保存到: {wallpaper_path}")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err}")  # 更详细的错误信息
    except Exception as e:
        print(f"下载壁纸失败: {e}")

def get_real_path():
    """
    获取实际运行时的文件所在路径（包括 pyinstaller 打包后的情况）。
    """
    if getattr(sys, 'frozen', False):  # 被 pyinstaller 打包时
        return os.path.dirname(sys.executable)  # 可执行文件所在目录
    return os.path.dirname(os.path.abspath(__file__))  # 脚本所在目录

def get_bing_wallpapers(count=8):
    """
    爬取必应最近几天的壁纸并保存到指定文件夹。

    :param count: 要爬取的壁纸数量，最多 8 张。
    """
    # 必应的国际版首页 URL
    bing_url = "https://www.bing.com"
    wallpaper_api = f"{bing_url}/HPImageArchive.aspx?format=js&idx=0&n={count}&mkt=en-US"

    try:
        # 获取壁纸信息
        response = requests.get(wallpaper_api)
        response.raise_for_status()
        data = response.json()

        # 创建保存壁纸的文件夹
        real_path = get_real_path()
        save_dir = os.path.join(real_path, "Bing_Wallpapers")
        if not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)  # 避免重复创建文件夹时抛出异常

        # 准备下载任务
        tasks = []
        with ThreadPoolExecutor() as executor:
            for image in data["images"]:
                wallpaper_url = bing_url + image["url"]
                wallpaper_name = image.get("title", "bing_wallpaper") + ".jpg"
                wallpaper_path = os.path.join(save_dir, wallpaper_name)
                tasks.append(executor.submit(download_wallpaper, wallpaper_url, wallpaper_path))

            # 等待所有任务完成
            for task in tasks:
                task.result()
        print("所有壁纸下载完成。")  # 下载任务完成后的日志信息

    except Exception as e:
        print(f"获取必应壁纸失败: {e}")

if __name__ == "__main__":
    get_bing_wallpapers()
