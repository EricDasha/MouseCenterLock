import os
import subprocess
import logging

print("请确保使用管理员权限运行此脚本！")

# 设置日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def disable_system_proxy():
    try:
        subprocess.run(['reg', 'add', 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings', '/v', 'ProxyEnable', '/t', 'REG_DWORD', '/d', '0', '/f'], check=True)
        logging.info("系统代理已关闭。")
        
        # 检查 ProxyServer 项是否存在
        result = subprocess.run(['reg', 'query', 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings', '/v', 'ProxyServer'], capture_output=True, text=True)
        if result.returncode == 0:
            # ProxyServer 项存在，删除它
            subprocess.run(['reg', 'delete', 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings', '/v', 'ProxyServer', '/f'], check=True)
            logging.info("ProxyServer 项已删除。")
        else:
            logging.info("ProxyServer 项不存在，无需删除。")
    except subprocess.CalledProcessError as e:
        logging.error(f"修改注册表时发生错误: {e}")

def reset_hosts_file():
    try:
        hosts_path = r'C:\\Windows\\System32\\drivers\\etc\\hosts'
        default_hosts_content = """\
# Copyright (c) 1993-2009 Microsoft Corp.
#
# 这是一个示例的 HOSTS 文件，用来解析主机名到 IP 地址。
#
# localhost 名解析由 DNS 自身完成。
# 127.0.0.1       localhost
# ::1             localhost
"""
        with open(hosts_path, 'w', encoding='utf-8') as file:
            file.write(default_hosts_content)
        logging.info("hosts 文件已重置。")
    except PermissionError:
        logging.error("权限不足，无法修改 hosts 文件。请以管理员权限运行此脚本。")
    except Exception as e:
        logging.error(f"重置 hosts 文件时发生错误: {e}")

def modify_dns():
    dns_options = {
        '1': ('114.114.114.114', '114.114.115.115'),
        '2': ('1.1.1.1', '1.0.0.1'),
        '3': ('119.29.29.29', '1.2.4.8')
    }

    try:
        dns_input = input("是否修改 DNS 设置？输入 'yes' 进行修改，不输入则跳过: (请勿随意修改dns)").strip().lower()
        if dns_input != 'yes':
            logging.info("DNS 设置未修改。")
            return

        print("请选择使用的 DNS 地址 (推荐 114.114.114.114，1.1.1.1，8.8.8.8):")
        for i, option in dns_options.items():
            print(f"{i}. {option[0]} (主要) / {option[1]} (备用)")

        choice = input("请输入选项 (1/2/3): ").strip()
        if choice not in dns_options:
            logging.info("无效的选项，DNS 设置未修改。")
            return
        print("修改dns时间可能较长，请耐心等待……")
        preferred_dns, alternate_dns = dns_options[choice]

        result = subprocess.run(['netsh', 'interface', 'show', 'interface'], capture_output=True, text=True)
        interfaces = [line.split()[3] for line in result.stdout.splitlines() if '已连接' in line or '已启用' in line]

        logging.info(f"找到的网络接口: {interfaces}")

        for interface in interfaces:
            try:
                subprocess.run(['netsh', 'interface', 'ip', 'set', 'dns', f'name={interface}', 'source=static', f'addr={preferred_dns}'], check=True)
                subprocess.run(['netsh', 'interface', 'ip', 'add', 'dns', f'name={interface}', f'addr={alternate_dns}', 'index=2'], check=True)
                logging.info(f"DNS 设置已应用到接口: {interface}")
            except subprocess.CalledProcessError as e:
                logging.error(f"修改接口 {interface} 的 DNS 设置时发生错误: {e}")

    except subprocess.CalledProcessError as e:
        logging.error(f"修改 DNS 设置时发生错误: {e}")

if __name__ == "__main__":
    disable_system_proxy()
    reset_hosts_file()
    modify_dns()

input("按任意键退出...(如果有此脚本无法修复的问题，请使用杀毒软件中的强力修复电脑网络或重置电脑网络)")