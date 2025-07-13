import urllib.request
import re
GITHUB_REPO = "Hum1Tab/Hum1Tab_proxy_scraper"
CURRENT_VERSION = "1.0"

def check_github_update():
    """GitHubの最新リリースバージョンをチェックし、更新があれば通知"""
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    try:
        with urllib.request.urlopen(api_url, timeout=5) as res:
            import json
            data = json.load(res)
            tag = data.get("tag_name")
            if tag:
                # v1.0.1 → 1.0.1 などに正規化
                tag_version = re.sub(r"^v", "", tag)
                if tag_version != CURRENT_VERSION:
                    print(f"{Fore.YELLOW}[UPDATE] 新バージョン {tag_version} が公開されています → https://github.com/{GITHUB_REPO}/releases/latest")
    except Exception as e:
        pass  # 通信失敗時は何もしない
import asyncio
import aiohttp
import aiofiles
import time
import json
import socket
import logging
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import colorama
from colorama import Fore, init
import os
import sys

init(convert=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ProxySource:
    """プロキシソース情報"""
    name: str
    url: str
    enabled: bool = True
    parse_format: str = "ip_port_per_line"
    headers: Dict[str, str] = None
    json_path: str = None
    timeout: int = 15
    description: str = ""
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}

@dataclass
class AsyncSettings:
    """非同期設定情報"""
    validate_proxies: bool = True
    max_concurrent_requests: int = 100
    max_concurrent_validations: int = 200
    request_timeout: int = 10
    proxy_timeout: int = 5
    save_raw_proxies: bool = True
    retry_count: int = 3
    delay_between_requests: float = 0.1
    auto_save_settings: bool = True
    
    def save_to_file(self, filename: str = "settings.json"):
        """設定をファイルに保存"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(asdict(self), f, indent=2, ensure_ascii=False)
            logger.info(f"Settings saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to save settings: {str(e)}")
            return False
    
    def load_from_file(self, filename: str = "settings.json"):
        """ファイルから設定を読み込み"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        if hasattr(self, key):
                            # 型を明示的に変換
                            attr_type = type(getattr(self, key))
                            if attr_type is bool:
                                setattr(self, key, bool(value))
                            else:
                                setattr(self, key, value)
                logger.info(f"Settings loaded from {filename}")
                return True
            else:
                logger.info(f"Settings file {filename} not found, creating default settings")
                self.save_to_file(filename)
                return True
        except Exception as e:
            logger.error(f"Failed to load settings: {str(e)}")
            return False

class ConfigManager:
    """設定管理クラス"""
    
    def __init__(self):
        self.sources_file = "sources.json"
        self.settings_file = "settings.json"
    
    def create_default_sources(self):
        """デフォルトソース設定を作成"""
        default_sources = {
            "version": "1.0",
            "last_updated": time.strftime('%Y-%m-%d %H:%M:%S'),
            "sources": {
                "http": [
                    {
                        "name": "ProxyScrape HTTP",
                        "url": "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
                        "enabled": True,
                        "parse_format": "ip_port_per_line",
                        "headers": {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        },
                        "timeout": 15,
                        "description": "ProxyScrape HTTP proxies"
                    },
                    {
                        "name": "ProxyList HTTP",
                        "url": "https://www.proxy-list.download/api/v1/get?type=http",
                        "enabled": True,
                        "parse_format": "ip_port_per_line",
                        "headers": {},
                        "timeout": 15,
                        "description": "ProxyList HTTP proxies"
                    },
                    {
                        "name": "FreeProxyList",
                        "url": "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
                        "enabled": True,
                        "parse_format": "ip_port_per_line",
                        "headers": {},
                        "timeout": 15,
                        "description": "GitHub HTTP proxy list"
                    }
                ],
                "socks4": [
                    {
                        "name": "ProxyScrape SOCKS4",
                        "url": "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4&timeout=10000&country=all",
                        "enabled": True,
                        "parse_format": "ip_port_per_line",
                        "headers": {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        },
                        "timeout": 15,
                        "description": "ProxyScrape SOCKS4 proxies"
                    },
                    {
                        "name": "ProxyList SOCKS4",
                        "url": "https://www.proxy-list.download/api/v1/get?type=socks4",
                        "enabled": True,
                        "parse_format": "ip_port_per_line",
                        "headers": {},
                        "timeout": 15,
                        "description": "ProxyList SOCKS4 proxies"
                    },
                    {
                        "name": "GitHub SOCKS4",
                        "url": "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt",
                        "enabled": True,
                        "parse_format": "ip_port_per_line",
                        "headers": {},
                        "timeout": 15,
                        "description": "GitHub SOCKS4 proxy list"
                    }
                ],
                "socks5": [
                    {
                        "name": "ProxyScrape SOCKS5",
                        "url": "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all",
                        "enabled": True,
                        "parse_format": "ip_port_per_line",
                        "headers": {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        },
                        "timeout": 15,
                        "description": "ProxyScrape SOCKS5 proxies"
                    },
                    {
                        "name": "ProxyList SOCKS5",
                        "url": "https://www.proxy-list.download/api/v1/get?type=socks5",
                        "enabled": True,
                        "parse_format": "ip_port_per_line",
                        "headers": {},
                        "timeout": 15,
                        "description": "ProxyList SOCKS5 proxies"
                    },
                    {
                        "name": "GitHub SOCKS5",
                        "url": "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
                        "enabled": True,
                        "parse_format": "ip_port_per_line",
                        "headers": {},
                        "timeout": 15,
                        "description": "GitHub SOCKS5 proxy list"
                    }
                ]
            }
        }
        return default_sources
    
    def save_sources(self, sources_data: Dict):
        """ソース設定を保存"""
        try:
            with open(self.sources_file, 'w', encoding='utf-8') as f:
                json.dump(sources_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Sources saved to {self.sources_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save sources: {str(e)}")
            return False
    
    def load_sources(self):
        """ソース設定を読み込み"""
        try:
            if os.path.exists(self.sources_file):
                with open(self.sources_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"Sources loaded from {self.sources_file}")
                return data
            else:
                logger.info(f"Sources file {self.sources_file} not found, creating default")
                default_sources = self.create_default_sources()
                self.save_sources(default_sources)
                return default_sources
        except Exception as e:
            logger.error(f"Failed to load sources: {str(e)}")
            default_sources = self.create_default_sources()
            self.save_sources(default_sources)
            return default_sources
    
    def add_source(self, proxy_type: str, source_data: Dict):
        """新しいソースを追加"""
        sources_data = self.load_sources()
        
        if proxy_type not in sources_data['sources']:
            sources_data['sources'][proxy_type] = []
        
        # 必要なフィールドを補完
        required_fields = {
            'name': 'New Source',
            'url': '',
            'enabled': True,
            'parse_format': 'ip_port_per_line',
            'headers': {},
            'timeout': 15,
            'description': ''
        }
        
        for field, default_value in required_fields.items():
            if field not in source_data:
                source_data[field] = default_value
        
        sources_data['sources'][proxy_type].append(source_data)
        sources_data['last_updated'] = time.strftime('%Y-%m-%d %H:%M:%S')
        
        return self.save_sources(sources_data)
    
    def remove_source(self, proxy_type: str, source_name: str):
        """ソースを削除"""
        sources_data = self.load_sources()
        
        if proxy_type in sources_data['sources']:
            sources_data['sources'][proxy_type] = [
                source for source in sources_data['sources'][proxy_type]
                if source['name'] != source_name
            ]
            sources_data['last_updated'] = time.strftime('%Y-%m-%d %H:%M:%S')
            return self.save_sources(sources_data)
        
        return False
    
    def toggle_source(self, proxy_type: str, source_name: str):
        """ソースの有効/無効を切り替え"""
        sources_data = self.load_sources()
        
        if proxy_type in sources_data['sources']:
            for source in sources_data['sources'][proxy_type]:
                if source['name'] == source_name:
                    source['enabled'] = not source['enabled']
                    sources_data['last_updated'] = time.strftime('%Y-%m-%d %H:%M:%S')
                    return self.save_sources(sources_data)
        
        return False

class AsyncProxyValidator:
    """非同期プロキシ検証クラス"""
    
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.test_url = "http://httpbin.org/ip"
        self.backup_test_urls = [
            "http://ipinfo.io/ip",
            "http://icanhazip.com",
            "http://ident.me",
            "https://api.ipify.org"
        ]
        
    async def validate_proxy(self, session: aiohttp.ClientSession, proxy: str, proxy_type: str) -> bool:
        """プロキシの有効性を非同期で検証"""
        try:
            if proxy_type.lower() == 'http':
                proxy_url = f'http://{proxy}'
            elif proxy_type.lower() == 'socks4':
                proxy_url = f'socks4://{proxy}'
            elif proxy_type.lower() == 'socks5':
                proxy_url = f'socks5://{proxy}'
            else:
                return False
                
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            # メインテストURL
            try:
                async with session.get(
                    self.test_url,
                    proxy=proxy_url,
                    timeout=timeout
                ) as response:
                    return response.status == 200
            except:
                # バックアップURLで再試行
                for backup_url in self.backup_test_urls:
                    try:
                        async with session.get(
                            backup_url,
                            proxy=proxy_url,
                            timeout=timeout
                        ) as response:
                            return response.status == 200
                    except:
                        continue
                return False
                
        except Exception as e:
            return False

class AsyncProxyScraper:
    """非同期高性能プロキシスクレイパー"""
    
    def __init__(self, settings: AsyncSettings):
        self.settings = settings
        self.proxy_sources = {}
        self.validator = AsyncProxyValidator(self.settings.proxy_timeout)
        self.config_manager = ConfigManager()
        self.load_sources()
        
    def load_sources(self):
        """外部ファイルからソースを読み込み"""
        try:
            sources_data = self.config_manager.load_sources()
            
            for proxy_type, sources in sources_data.get('sources', {}).items():
                self.proxy_sources[proxy_type] = []
                for source_data in sources:
                    if source_data.get('enabled', True):
                        source = ProxySource(**source_data)
                        self.proxy_sources[proxy_type].append(source)
                        
        except Exception as e:
            logger.error(f"Failed to load sources: {str(e)}")
    
    async def fetch_from_source(self, session: aiohttp.ClientSession, source: ProxySource) -> List[str]:
        """単一ソースから非同期でプロキシを取得"""
        try:
            print(f"{Fore.CYAN}[INFO] Fetching from {source.name}...")
            
            timeout = aiohttp.ClientTimeout(total=source.timeout)
            headers = source.headers or {}
            
            for attempt in range(self.settings.retry_count):
                try:
                    async with session.get(source.url, headers=headers, timeout=timeout) as response:
                        if response.status != 200:
                            if attempt < self.settings.retry_count - 1:
                                await asyncio.sleep(1)
                                continue
                            raise aiohttp.ClientError(f"HTTP {response.status}")
                        
                        content = await response.text()
                        proxies = self.parse_proxy_content(content, source)
                        
                        print(f"{Fore.GREEN}[SUCCESS] Got {len(proxies)} proxies from {source.name}")
                        return proxies
                        
                except Exception as e:
                    if attempt < self.settings.retry_count - 1:
                        print(f"{Fore.YELLOW}[RETRY] Attempt {attempt + 1}/{self.settings.retry_count} failed for {source.name}: {str(e)}")
                        await asyncio.sleep(2)
                    else:
                        raise e
                        
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Failed to fetch from {source.name}: {str(e)}")
            return []
    
    def parse_proxy_content(self, content: str, source: ProxySource) -> List[str]:
        """プロキシコンテンツを解析"""
        proxies = []
        
        if source.parse_format == "ip_port_per_line":
            for line in content.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    parts = line.split(':')
                    if len(parts) >= 2:
                        try:
                            ip = parts[0].strip()
                            port = parts[1].strip()
                            
                            # IPアドレスとポート番号の検証
                            socket.inet_aton(ip)
                            port_num = int(port)
                            if 1 <= port_num <= 65535:
                                proxies.append(f"{ip}:{port}")
                        except:
                            continue
                            
        elif source.parse_format == "json":
            try:
                data = json.loads(content)
                if source.json_path:
                    # JSONパスに従ってデータを取得
                    proxy_list = data
                    for key in source.json_path.split('.'):
                        proxy_list = proxy_list.get(key, [])
                    
                    if isinstance(proxy_list, list):
                        for proxy_data in proxy_list:
                            if isinstance(proxy_data, dict):
                                ip = proxy_data.get('ip')
                                port = proxy_data.get('port')
                                if ip and port:
                                    proxies.append(f"{ip}:{port}")
                            elif isinstance(proxy_data, str) and ':' in proxy_data:
                                proxies.append(proxy_data)
                else:
                    # 直接リストの場合
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, str) and ':' in item:
                                proxies.append(item)
            except:
                pass
                
        return proxies
    
    async def fetch_proxies_parallel(self, proxy_type: str) -> List[str]:
        """並列でプロキシを取得"""
        if proxy_type not in self.proxy_sources:
            return []
            
        sources = self.proxy_sources[proxy_type]
        if not sources:
            return []
        
        timeout = aiohttp.ClientTimeout(total=self.settings.request_timeout)
        connector = aiohttp.TCPConnector(
            limit=self.settings.max_concurrent_requests,
            limit_per_host=10
        )
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            for source in sources:
                task = asyncio.create_task(self.fetch_from_source(session, source))
                tasks.append(task)
                
                # リクエスト間の遅延
                if self.settings.delay_between_requests > 0:
                    await asyncio.sleep(self.settings.delay_between_requests)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            all_proxies = []
            for result in results:
                if isinstance(result, list):
                    all_proxies.extend(result)
        
        # 重複を除去
        unique_proxies = list(set(all_proxies))
        print(f"{Fore.YELLOW}[INFO] Total unique proxies: {len(unique_proxies)}")
        return unique_proxies
    
    async def validate_proxies_parallel(self, proxies: List[str], proxy_type: str) -> List[str]:
        """並列でプロキシを検証"""
        if not proxies:
            return []
            
        print(f"{Fore.CYAN}[INFO] Validating {len(proxies)} proxies with {self.settings.max_concurrent_validations} concurrent connections...")
        
        valid_proxies = []
        semaphore = asyncio.Semaphore(self.settings.max_concurrent_validations)
        
        async def validate_single_proxy(session, proxy):
            async with semaphore:
                if await self.validator.validate_proxy(session, proxy, proxy_type):
                    valid_proxies.append(proxy)
                    print(f"{Fore.GREEN}[VALID] {proxy}")
                    return True
                return False
        
        timeout = aiohttp.ClientTimeout(total=self.settings.proxy_timeout)
        connector = aiohttp.TCPConnector(
            limit=self.settings.max_concurrent_validations,
            limit_per_host=50
        )
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            for proxy in proxies:
                task = asyncio.create_task(validate_single_proxy(session, proxy))
                tasks.append(task)
            
            # プログレス表示付きで実行
            completed = 0
            for task in asyncio.as_completed(tasks):
                await task
                completed += 1
                if completed % 10 == 0:
                    print(f"{Fore.YELLOW}[PROGRESS] Validated {completed}/{len(proxies)} proxies...")
        
        print(f"{Fore.GREEN}[SUCCESS] Found {len(valid_proxies)} valid proxies")
        return valid_proxies
    
    async def save_proxies_async(self, proxies: List[str], filename: str, include_stats: bool = True):
        """プロキシを非同期でファイルに保存"""
        try:
            async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
                for proxy in proxies:
                    await f.write(f"{proxy}\n")
            
            print(f"{Fore.GREEN}[SUCCESS] Saved {len(proxies)} proxies to {filename}")
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Failed to save proxies: {str(e)}")
    
    async def generate_proxies_async(self, proxy_type: str):
        """非同期プロキシ生成のメイン関数"""
        os.makedirs("proxy", exist_ok=True)
        filename = os.path.join("proxy", f"{proxy_type}_proxies.txt")
        # 既存ファイルを削除
        if os.path.exists(filename):
            os.remove(filename)
        
        print(f"{Fore.CYAN}[INFO] Generating {proxy_type.upper()} proxies asynchronously...")
        start_time = time.time()
        
        # プロキシを並列取得
        proxies = await self.fetch_proxies_parallel(proxy_type)
        
        if not proxies:
            print(f"{Fore.RED}[ERROR] No proxies found for {proxy_type}")
            return
        
        # 検証を行う場合
        if self.settings.validate_proxies:
            valid_proxies = await self.validate_proxies_parallel(proxies, proxy_type)
            await self.save_proxies_async(valid_proxies, filename)
            
            # 生のプロキシも保存する場合
            if self.settings.save_raw_proxies:
                raw_filename = os.path.join("proxy", f"{proxy_type}_raw_proxies.txt")
                await self.save_proxies_async(proxies, raw_filename)
                
        else:
            await self.save_proxies_async(proxies, filename)
        
        elapsed_time = time.time() - start_time
        print(f"{Fore.GREEN}[COMPLETE] Process completed in {elapsed_time:.2f} seconds")

def clear_screen():
    """画面をクリア"""
    os.system('cls' if os.name == 'nt' else 'clear')

def display_async_menu():
    """非同期版メニューを表示"""
    clear_screen()
    print(Fore.RED + """
██╗  ██╗██╗   ██╗███╗   ███╗ ██╗████████╗ █████╗ ██████╗ 
██║  ██║██║   ██║████╗ ████║███║╚══██╔══╝██╔══██╗██╔══██╗
███████║██║   ██║██╔████╔██║╚██║   ██║   ███████║██████╔╝
██╔══██║██║   ██║██║╚██╔╝██║ ██║   ██║   ██╔══██║██╔══██╗
██║  ██║╚██████╔╝██║ ╚═╝ ██║ ██║   ██║   ██║  ██║██████╔╝
╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝ ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═════╝ 

Hum1Tab Proxy Scraper v1.0
    """ + Fore.RESET)
    
    print(Fore.WHITE + "=" * 60)
    print(Fore.CYAN + " Simple & Fast Proxy Scraper")
    print(Fore.WHITE + "  - HTTP / SOCKS4 / SOCKS5 support")
    print(Fore.WHITE + "  - Easy menu operation")
    print(Fore.WHITE + "  - Output: *_proxies.txt")
    print(Fore.WHITE + "=" * 60)
    
    print(Fore.YELLOW + "\nProxy Operations:")
    print(Fore.WHITE + "[1] HTTP Proxies")
    print(Fore.WHITE + "[2] SOCKS4 Proxies") 
    print(Fore.WHITE + "[3] SOCKS5 Proxies")
    print(Fore.WHITE + "[4] All Types")
    print(Fore.WHITE + "[5] Source Management")
    print(Fore.WHITE + "[6] Check All Sources (Status)")
    print(Fore.WHITE + "[7] Settings")
    print(Fore.WHITE + "[8] Exit")
    print()

def display_source_menu():
    """ソース管理メニューを表示"""
    clear_screen()
    print(Fore.CYAN + """
╔══════════════════════════════════════════════════════════════════════════════╗
║                            SOURCE MANAGEMENT                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """ + Fore.RESET)
    
    print(Fore.YELLOW + "Source Management Options:")
    print(Fore.WHITE + "[1] View Current Sources")
    print(Fore.WHITE + "[2] Add New Source")
    print(Fore.WHITE + "[3] Remove Source")
    print(Fore.WHITE + "[4] Toggle Source Enable/Disable")
    print(Fore.WHITE + "[5] Reset to Default Sources")
    print(Fore.WHITE + "[6] Back to Main Menu")
    print()

def display_settings_menu(settings: AsyncSettings):
    """設定メニューを表示"""
    clear_screen()
    print(Fore.CYAN + """
╔══════════════════════════════════════════════════════════════════════════════╗
║                            SETTINGS CONFIGURATION                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """ + Fore.RESET)
    
    print(Fore.YELLOW + "Current Settings:")
    print(f"{Fore.WHITE}[1] Validate Proxies: {Fore.GREEN if settings.validate_proxies else Fore.RED}{settings.validate_proxies}")
    print(f"{Fore.WHITE}[2] Max Concurrent Requests: {Fore.CYAN}{settings.max_concurrent_requests}")
    print(f"{Fore.WHITE}[3] Max Concurrent Validations: {Fore.CYAN}{settings.max_concurrent_validations}")
    print(f"{Fore.WHITE}[4] Request Timeout: {Fore.CYAN}{settings.request_timeout}s")
    print(f"{Fore.WHITE}[5] Proxy Timeout: {Fore.CYAN}{settings.proxy_timeout}s")
    print(f"{Fore.WHITE}[6] Save Raw Proxies: {Fore.GREEN if settings.save_raw_proxies else Fore.RED}{settings.save_raw_proxies}")
    print(f"{Fore.WHITE}[7] Retry Count: {Fore.CYAN}{settings.retry_count}")
    print(f"{Fore.WHITE}[8] Delay Between Requests: {Fore.CYAN}{settings.delay_between_requests}s")
    print(f"{Fore.WHITE}[9] Auto Save Settings: {Fore.GREEN if settings.auto_save_settings else Fore.RED}{settings.auto_save_settings}")
    print(f"{Fore.WHITE}[10] Save Settings to File")
    print(f"{Fore.WHITE}[11] Back to Main Menu")
    print()

async def handle_source_management(config_manager: ConfigManager):
    """ソース管理を処理"""
    while True:
        display_source_menu()
        
        try:
            choice = input(f"{Fore.GREEN}[>] Select option: {Fore.RESET}")
            choice = int(choice)
            
            if choice == 1:
                # 現在のソースを表示
                sources_data = config_manager.load_sources()
                print(f"\n{Fore.CYAN}=== Current Sources ===")
                for proxy_type, sources in sources_data.get('sources', {}).items():
                    print(f"\n{Fore.YELLOW}{proxy_type.upper()} Sources:")
                    for i, source in enumerate(sources, 1):
                        status = f"{Fore.GREEN}[ENABLED]" if source.get('enabled', True) else f"{Fore.RED}[DISABLED]"
                        print(f"  {i}. {status} {source['name']}")
                        print(f"     URL: {source['url']}")
                        print(f"     Format: {source.get('parse_format', 'ip_port_per_line')}")
                        if source.get('description'):
                            print(f"     Description: {source['description']}")
                        print()
                
                input(f"{Fore.YELLOW}Press Enter to continue...")
                
            elif choice == 2:
                # 新しいソースを追加
                print(f"\n{Fore.CYAN}=== Add New Source ===")
                proxy_type = input(f"{Fore.WHITE}Proxy type (http/socks4/socks5): {Fore.RESET}").lower()
                
                if proxy_type not in ['http', 'socks4', 'socks5']:
                    print(f"{Fore.RED}[ERROR] Invalid proxy type!")
                    continue
                
                name = input(f"{Fore.WHITE}Source name: {Fore.RESET}")
                url = input(f"{Fore.WHITE}Source URL: {Fore.RESET}")
                description = input(f"{Fore.WHITE}Description (optional): {Fore.RESET}")
                
                print(f"\n{Fore.YELLOW}Parse formats:")
                print(f"{Fore.WHITE}1. ip_port_per_line (default)")
                print(f"{Fore.WHITE}2. json")
                
                format_choice = input(f"{Fore.WHITE}Parse format (1-2, default: 1): {Fore.RESET}")
                parse_format = "json" if format_choice == "2" else "ip_port_per_line"
                
                json_path = ""
                if parse_format == "json":
                    json_path = input(f"{Fore.WHITE}JSON path (e.g., 'data.proxies'): {Fore.RESET}")
                
                # ヘッダー設定
                headers = {}
                add_headers = input(f"{Fore.WHITE}Add custom headers? (y/n): {Fore.RESET}").lower()
                if add_headers == 'y':
                    while True:
                        header_name = input(f"{Fore.WHITE}Header name (or press Enter to finish): {Fore.RESET}")
                        if not header_name:
                            break
                        header_value = input(f"{Fore.WHITE}Header value: {Fore.RESET}")
                        headers[header_name] = header_value
                
                source_data = {
                    'name': name,
                    'url': url,
                    'enabled': True,
                    'parse_format': parse_format,
                    'headers': headers,
                    'timeout': 15,
                    'description': description
                }
                
                if json_path:
                    source_data['json_path'] = json_path
                
                if config_manager.add_source(proxy_type, source_data):
                    print(f"{Fore.GREEN}[SUCCESS] Source added successfully!")
                else:
                    print(f"{Fore.RED}[ERROR] Failed to add source!")
                
                input(f"{Fore.YELLOW}Press Enter to continue...")
                
            elif choice == 3:
                # ソースを削除
                print(f"\n{Fore.CYAN}=== Remove Source ===")
                proxy_type = input(f"{Fore.WHITE}Proxy type (http/socks4/socks5): {Fore.RESET}").lower()
                
                if proxy_type not in ['http', 'socks4', 'socks5']:
                    print(f"{Fore.RED}[ERROR] Invalid proxy type!")
                    continue
                
                sources_data = config_manager.load_sources()
                sources = sources_data.get('sources', {}).get(proxy_type, [])
                
                if not sources:
                    print(f"{Fore.RED}[ERROR] No sources found for {proxy_type}!")
                    continue
                
                print(f"\n{Fore.YELLOW}Available sources:")
                for i, source in enumerate(sources, 1):
                    print(f"  {i}. {source['name']}")
                
                source_name = input(f"{Fore.WHITE}Source name to remove: {Fore.RESET}")
                
                confirm = input(f"{Fore.RED}Are you sure you want to remove '{source_name}'? (y/n): {Fore.RESET}")
                if confirm.lower() == 'y':
                    if config_manager.remove_source(proxy_type, source_name):
                        print(f"{Fore.GREEN}[SUCCESS] Source removed successfully!")
                    else:
                        print(f"{Fore.RED}[ERROR] Failed to remove source!")
                
                input(f"{Fore.YELLOW}Press Enter to continue...")
                
            elif choice == 4:
                # ソースの有効/無効を切り替え
                print(f"\n{Fore.CYAN}=== Toggle Source Status ===")
                proxy_type = input(f"{Fore.WHITE}Proxy type (http/socks4/socks5): {Fore.RESET}").lower()
                
                if proxy_type not in ['http', 'socks4', 'socks5']:
                    print(f"{Fore.RED}[ERROR] Invalid proxy type!")
                    continue
                
                sources_data = config_manager.load_sources()
                sources = sources_data.get('sources', {}).get(proxy_type, [])
                
                if not sources:
                    print(f"{Fore.RED}[ERROR] No sources found for {proxy_type}!")
                    continue
                
                print(f"\n{Fore.YELLOW}Available sources:")
                for i, source in enumerate(sources, 1):
                    status = f"{Fore.GREEN}[ENABLED]" if source.get('enabled', True) else f"{Fore.RED}[DISABLED]"
                    print(f"  {i}. {status} {source['name']}")
                
                source_name = input(f"{Fore.WHITE}Source name to toggle: {Fore.RESET}")
                
                if config_manager.toggle_source(proxy_type, source_name):
                    print(f"{Fore.GREEN}[SUCCESS] Source status toggled successfully!")
                else:
                    print(f"{Fore.RED}[ERROR] Failed to toggle source status!")
                
                input(f"{Fore.YELLOW}Press Enter to continue...")
                
            elif choice == 5:
                # デフォルトソースにリセット
                print(f"\n{Fore.CYAN}=== Reset to Default Sources ===")
                confirm = input(f"{Fore.RED}This will overwrite all current sources. Are you sure? (y/n): {Fore.RESET}")
                
                if confirm.lower() == 'y':
                    default_sources = config_manager.create_default_sources()
                    if config_manager.save_sources(default_sources):
                        print(f"{Fore.GREEN}[SUCCESS] Sources reset to default!")
                    else:
                        print(f"{Fore.RED}[ERROR] Failed to reset sources!")
                
                input(f"{Fore.YELLOW}Press Enter to continue...")
                
            elif choice == 6:
                # メインメニューに戻る
                break
                
            else:
                print(f"{Fore.RED}[ERROR] Invalid choice. Please select 1-6.")
                time.sleep(2)
                
        except ValueError:
            print(f"{Fore.RED}[ERROR] Please enter a valid number.")
            time.sleep(2)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Unexpected error: {str(e)}")
            time.sleep(2)

def handle_settings_menu(settings: AsyncSettings):
    """設定メニューを処理"""
    while True:
        display_settings_menu(settings)
        
        try:
            choice = input(f"{Fore.GREEN}[>] Select option: {Fore.RESET}")
            choice = int(choice)
            
            if choice == 1:
                settings.validate_proxies = not settings.validate_proxies
                print(f"{Fore.GREEN}[SUCCESS] Proxy validation: {settings.validate_proxies}")
                
            elif choice == 2:
                new_value = int(input(f"{Fore.WHITE}New max concurrent requests (current: {settings.max_concurrent_requests}): {Fore.RESET}"))
                if 1 <= new_value <= 1000:
                    settings.max_concurrent_requests = new_value
                    print(f"{Fore.GREEN}[SUCCESS] Max concurrent requests updated to {new_value}")
                else:
                    print(f"{Fore.RED}[ERROR] Value must be between 1 and 1000")
                
            elif choice == 3:
                new_value = int(input(f"{Fore.WHITE}New max concurrent validations (current: {settings.max_concurrent_validations}): {Fore.RESET}"))
                if 1 <= new_value <= 1000:
                    settings.max_concurrent_validations = new_value
                    print(f"{Fore.GREEN}[SUCCESS] Max concurrent validations updated to {new_value}")
                else:
                    print(f"{Fore.RED}[ERROR] Value must be between 1 and 1000")
                
            elif choice == 4:
                new_value = int(input(f"{Fore.WHITE}New request timeout in seconds (current: {settings.request_timeout}): {Fore.RESET}"))
                if 1 <= new_value <= 300:
                    settings.request_timeout = new_value
                    print(f"{Fore.GREEN}[SUCCESS] Request timeout updated to {new_value}s")
                else:
                    print(f"{Fore.RED}[ERROR] Value must be between 1 and 300 seconds")
                
            elif choice == 5:
                new_value = int(input(f"{Fore.WHITE}New proxy timeout in seconds (current: {settings.proxy_timeout}): {Fore.RESET}"))
                if 1 <= new_value <= 60:
                    settings.proxy_timeout = new_value
                    print(f"{Fore.GREEN}[SUCCESS] Proxy timeout updated to {new_value}s")
                else:
                    print(f"{Fore.RED}[ERROR] Value must be between 1 and 60 seconds")
                
            elif choice == 6:
                settings.save_raw_proxies = not settings.save_raw_proxies
                print(f"{Fore.GREEN}[SUCCESS] Save raw proxies: {settings.save_raw_proxies}")
                
            elif choice == 7:
                new_value = int(input(f"{Fore.WHITE}New retry count (current: {settings.retry_count}): {Fore.RESET}"))
                if 1 <= new_value <= 10:
                    settings.retry_count = new_value
                    print(f"{Fore.GREEN}[SUCCESS] Retry count updated to {new_value}")
                else:
                    print(f"{Fore.RED}[ERROR] Value must be between 1 and 10")
                
            elif choice == 8:
                new_value = float(input(f"{Fore.WHITE}New delay between requests in seconds (current: {settings.delay_between_requests}): {Fore.RESET}"))
                if 0 <= new_value <= 10:
                    settings.delay_between_requests = new_value
                    print(f"{Fore.GREEN}[SUCCESS] Delay between requests updated to {new_value}s")
                else:
                    print(f"{Fore.RED}[ERROR] Value must be between 0 and 10 seconds")
                
            elif choice == 9:
                settings.auto_save_settings = not settings.auto_save_settings
                print(f"{Fore.GREEN}[SUCCESS] Auto save settings: {settings.auto_save_settings}")
                
            elif choice == 10:
                if settings.save_to_file():
                    print(f"{Fore.GREEN}[SUCCESS] Settings saved to file!")
                else:
                    print(f"{Fore.RED}[ERROR] Failed to save settings!")
                
            elif choice == 11:
                # メインメニューに戻る
                if settings.auto_save_settings:
                    settings.save_to_file()
                break
                
            else:
                print(f"{Fore.RED}[ERROR] Invalid choice. Please select 1-11.")
                time.sleep(2)
                continue
                
            time.sleep(1)
            
        except ValueError:
            print(f"{Fore.RED}[ERROR] Please enter a valid number.")
            time.sleep(2)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Unexpected error: {str(e)}")
            time.sleep(2)

async def main_async():
    """非同期メイン関数"""
    # 設定を読み込み（存在しない場合は自動作成）
    settings = AsyncSettings()
    settings.load_from_file()
    
    scraper = AsyncProxyScraper(settings)
    
    while True:
        display_async_menu()
        try:
            choice = input(f"{Fore.GREEN}[>] Select option: {Fore.RESET}")
            choice = int(choice)

            if choice == 1:
                await scraper.generate_proxies_async('http')
            elif choice == 2:
                await scraper.generate_proxies_async('socks4')
            elif choice == 3:
                await scraper.generate_proxies_async('socks5')
            elif choice == 4:
                # 全タイプを順次実行
                for proxy_type in ['http', 'socks4', 'socks5']:
                    await scraper.generate_proxies_async(proxy_type)
                    print(f"{Fore.YELLOW}[INFO] Waiting 2 seconds before next type...")
                    await asyncio.sleep(2)
            elif choice == 5:
                # ソース管理
                await handle_source_management(scraper.config_manager)
                # ソース管理後はソースを再読み込み
                scraper.load_sources()
            elif choice == 6:
                await check_all_sources(scraper)
            elif choice == 7:
                # 設定メニュー
                handle_settings_menu(settings)
                # 設定変更後はvalidatorのタイムアウトを更新
                scraper.validator.timeout = settings.proxy_timeout
            elif choice == 8:
                print(f"{Fore.GREEN}[INFO] Exiting...")
                if settings.auto_save_settings:
                    settings.save_to_file()
                break
            else:
                print(f"{Fore.RED}[ERROR] Invalid choice. Please select 1-8.")
                time.sleep(2)
                continue

            input(f"{Fore.YELLOW}Press Enter to continue...")
        except ValueError:
            print(f"{Fore.RED}[ERROR] Please enter a valid number.")
            time.sleep(2)
        except KeyboardInterrupt:
            print(f"\n{Fore.GREEN}[INFO] Exiting...")
            if settings.auto_save_settings:
                settings.save_to_file()
            break
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Unexpected error: {str(e)}")
            time.sleep(2)


# --- ソースチェック機能 ---
async def check_all_sources(scraper):
    """全ソースのURL応答をチェック"""
    print(f"{Fore.CYAN}[INFO] Checking all sources...")
    sources_data = scraper.config_manager.load_sources()
    all_sources = []
    for proxy_type, sources in sources_data.get('sources', {}).items():
        for source in sources:
            all_sources.append((proxy_type, source))

    results = []
    timeout = aiohttp.ClientTimeout(total=10)
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        for proxy_type, source in all_sources:
            url = source.get('url')
            name = source.get('name')
            try:
                start = time.time()
                async with session.get(url, headers=source.get('headers', {})) as resp:
                    elapsed = time.time() - start
                    status = resp.status
                    print(f"{Fore.GREEN}[OK] {proxy_type.upper()} | {name} | {url} | Status: {status} | {elapsed:.2f}s")
                    results.append((proxy_type, name, url, status, elapsed))
            except Exception as e:
                print(f"{Fore.RED}[FAIL] {proxy_type.upper()} | {name} | {url} | {str(e)}")
                results.append((proxy_type, name, url, 'ERROR', str(e)))
    print(f"{Fore.CYAN}[INFO] Source check finished.")

if __name__ == "__main__":
    try:
        print(f"{Fore.CYAN}[INFO] Initializing Enhanced Async Proxy Scraper v{CURRENT_VERSION}...")
        check_github_update()
        print(f"{Fore.CYAN}[INFO] Checking configuration files...")

        # 設定ファイルの存在確認
        if not os.path.exists("settings.json"):
            print(f"{Fore.YELLOW}[INFO] Creating default settings.json...")
            default_settings = AsyncSettings()
            default_settings.save_to_file()

        if not os.path.exists("sources.json"):
            print(f"{Fore.YELLOW}[INFO] Creating default sources.json...")
            config_manager = ConfigManager()
            config_manager.load_sources()  # これでデフォルトソースが作成される

        print(f"{Fore.GREEN}[INFO] Configuration ready!")
        time.sleep(1)

        asyncio.run(main_async())

    except KeyboardInterrupt:
        print(f"\n{Fore.GREEN}[INFO] Program interrupted by user")
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Fatal error: {str(e)}")
        input(f"{Fore.YELLOW}Press Enter to exit...")
    finally:
        print(f"{Fore.CYAN}[INFO] Thank you for using Enhanced Async Proxy Scraper!")
