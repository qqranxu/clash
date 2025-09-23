import requests
import yaml
import base64
import re
from urllib.parse import unquote

def get_subscription_data():
    """获取订阅数据"""
    url = "https://huaikhwang.central-world.org/api/v1/trails/bolster?token=c57e6b17821b3bf7a20c46605b6fdcb5"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # 解码base64
        decoded = base64.b64decode(response.text).decode('utf-8')
        print(f"✅ 获取订阅成功，共 {len(decoded.split())} 行")
        return decoded
    except Exception as e:
        print(f"❌ 获取订阅失败: {e}")
        return None

def parse_ss_links_fixed(content):
    """修复的SS链接解析"""
    proxies = []
    lines = content.strip().split('\n')
    
    for line_num, line in enumerate(lines, 1):
        if not line.startswith('ss://'):
            continue
            
        try:
            # 移除ss://前缀
            ss_data = line[5:]
            
            # 分离配置和名称
            if '#' in ss_data:
                config_part, name_part = ss_data.split('#', 1)
                proxy_name = unquote(name_part)
            else:
                config_part = ss_data
                proxy_name = f"节点-{line_num}"
            
            # 解析配置部分
            if '@' in config_part:
                auth_part, server_part = config_part.split('@', 1)
                
                # 解码认证信息
                try:
                    # 处理base64填充
                    auth_part_padded = auth_part + '=' * (4 - len(auth_part) % 4)
                    auth_decoded = base64.b64decode(auth_part_padded).decode('utf-8')
                    
                    if ':' in auth_decoded:
                        cipher, password = auth_decoded.split(':', 1)
                    else:
                        print(f"跳过行 {line_num}: 认证格式错误")
                        continue
                except Exception as e:
                    print(f"跳过行 {line_num}: 认证解码失败 - {e}")
                    continue
                
                # 修复端口解析 - 关键修复！
                # 先移除所有URL参数
                if '?' in server_part:
                    server_port_clean = server_part.split('?')[0]
                elif '/' in server_part:
                    server_port_clean = server_part.split('/')[0]
                else:
                    server_port_clean = server_part
                
                # 解析服务器和端口
                if ':' in server_port_clean:
                    parts = server_port_clean.rsplit(':', 1)
                    server = parts[0]
                    port_str = parts[1]
                    
                    # 确保端口是纯数字
                    port_clean = re.sub(r'[^0-9]', '', port_str)
                    if port_clean:
                        port = int(port_clean)
                    else:
                        print(f"跳过行 {line_num}: 端口解析失败 - {port_str}")
                        continue
                else:
                    print(f"跳过行 {line_num}: 服务器格式错误")
                    continue
                
                # 构建代理配置
                proxy = {
                    'name': proxy_name,
                    'type': 'ss',
                    'server': server,
                    'port': port,
                    'cipher': cipher,
                    'password': password,
                    'udp': True
                }
                
                # 检查obfs插件
                if 'plugin=' in server_part and 'obfs' in server_part:
                    proxy['plugin'] = 'obfs'
                    proxy['plugin-opts'] = {
                        'mode': 'http',
                        'host': '2195a4c365c3.microsoft.com'
                    }
                
                proxies.append(proxy)
                print(f"✅ 解析成功 {line_num}: {proxy_name} -> {server}:{port}")
                
        except Exception as e:
            print(f"跳过行 {line_num}: 解析失败 - {e}")
            continue
    
    return proxies

def create_complete_config():
    """创建完整配置"""
    
    # 获取订阅数据
    subscription_data = get_subscription_data()
    if not subscription_data:
        return None
    
    # 解析代理
    proxies = parse_ss_links_fixed(subscription_data)
    if not proxies:
        print("❌ 没有解析到有效的代理")
        return None
    
    print(f"🎉 成功解析 {len(proxies)} 个代理节点")
    
    # 基础配置（使用您的工作配置）
    config = {
        'mixed-port': 7890,
        'allow-lan': False,
        'mode': 'rule',
        'log-level': 'warning',
        'external-controller': '127.0.0.1:9090',
        'clash-for-android': {
            'append-system-dns': False
        },
        'cfw-bypass': [
            'localhost', '127.*', '10.*', '172.16.*', '172.17.*', 
            '172.18.*', '172.19.*', '172.20.*', '172.21.*', '172.22.*',
            '172.23.*', '172.24.*', '172.25.*', '172.26.*', '172.27.*',
            '172.28.*', '172.29.*', '172.30.*', '172.31.*', '192.168.*', '<local>'
        ],
        'hosts': {
            'mtalk.google.com': '108.177.125.188',
            'tagss.pro': '104.26.4.238'
        },
        'dns': {
            'enable': True,
            'listen': '127.0.0.1:9053',
            'default-nameserver': ['223.5.5.5', '223.6.6.6', '119.29.29.29'],
            'enhanced-mode': 'fake-ip',
            'nameserver': [
                'https://223.5.5.5/dns-query',
                'https://223.6.6.6/dns-query', 
                'https://doh.pub/dns-query'
            ]
        }
    }
    
    # 添加代理
    config['proxies'] = proxies
    
    # 生成listeners
    listeners = []
    for i, proxy in enumerate(proxies):
        listener = {
            'name': f'mixed{i}',
            'type': 'mixed',
            'port': 42000 + i,
            'proxy': proxy['name']
        }
        listeners.append(listener)
    
    config['listeners'] = listeners
    
    # 添加基础规则
    config['proxy-groups'] = [
        {
            'name': '🚀 节点选择',
            'type': 'select',
            'proxies': ['♻️ 自动选择', 'DIRECT'] + [p['name'] for p in proxies[:10]]
        },
        {
            'name': '♻️ 自动选择',
            'type': 'url-test',
            'proxies': [p['name'] for p in proxies],
            'url': 'http://www.gstatic.com/generate_204',
            'interval': 300
        }
    ]
    
    config['rules'] = ['MATCH,🚀 节点选择']
    
    return config, len(proxies)

def main():
    print("🚀 开始从订阅链接生成配置...")
    
    result = create_complete_config()
    if not result:
        print("❌ 生成失败")
        return
    
    config, proxy_count = result
    
    # 保存配置
    output_file = 'clash_auto_config.yaml'
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"\n🎉 自动配置生成完成！")
    print(f"📁 文件: {output_file}")
    print(f"🔌 端口范围: 42000-{42000 + proxy_count - 1}")
    print(f"📊 总计: {proxy_count} 个独立IP端口")
    
    print(f"\n📋 GitHub部署步骤:")
    print(f"1. 将 {output_file} 上传到GitHub仓库")
    print(f"2. 在Clash中使用链接:")
    print(f"   https://raw.githubusercontent.com/你的用户名/仓库名/main/{output_file}")

if __name__ == "__main__":
    main()
