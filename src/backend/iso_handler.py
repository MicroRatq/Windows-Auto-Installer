"""
ISO image processing module
Supports parsing image lists from multiple sources, scanning local cache, and identifying version information
"""
import os
import re
import subprocess
import tempfile
import json
import uuid
import hashlib
import shutil
import threading
import time
import sys
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from downloader import Downloader
from iso_inspector import ISOInspector


logger = logging.getLogger('ISOHandler')


class ISOHandler:
    """ISO镜像处理器"""
    
    def __init__(self, cache_dir: str = "./data/isos"):
        """
        初始化ISO处理器
        
        Args:
            cache_dir: 本地缓存目录
        """
        self.cache_dir: Path = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.downloader: Downloader = Downloader()
        self.product_edition_ids: dict[str, Any] = self._load_product_edition_ids()
        # 测试任务管理
        self.test_tasks: dict[str, dict[str, Any]] = {}
        self._test_lock: threading.Lock = threading.Lock()
    
    def _load_product_edition_ids(self) -> dict[str, Any]:
        """
        从配置文件加载产品版本ID映射
        
        Returns:
            产品版本ID字典
        
        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置文件格式错误
        """
        config_path = Path(__file__).parent.parent.parent / "data" / "product_edition_ids.json"
        
        if not config_path.exists():
            raise FileNotFoundError(
                f"Product ID config file not found: {config_path}\nPlease ensure data/product_edition_ids.json file exists"
            )
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 移除注释字段
                data.pop('_note', None)
                data.pop('_how_to_add_more', None)
                data.pop('_source', None)
                return data
        except json.JSONDecodeError as e:
            raise ValueError(f"Product ID config file format error: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load product ID config file: {e}")
    
    def _get_product_edition_ids_from_config(
        self,
        os_type: str,
        version: str
    ) -> list[int]:
        """
        从配置文件中获取产品版本ID（仅支持 Multi Editions）
        
        Args:
            os_type: 操作系统类型 ("windows11" | "windows10")
            version: 版本号（如 "25H2", "24H2", "22H2"），不区分大小写
        
        Returns:
            产品版本ID列表
        
        Raises:
            ValueError: 如果找不到对应的产品ID
        """
        if not self.product_edition_ids:
            raise ValueError("Product ID config not loaded, unable to get product edition IDs")
        
        # 确定操作系统键
        if "windows11" in os_type or "win11" in os_type or "w11" in os_type:
            os_key = "Windows 11"
        elif "windows10" in os_type or "win10" in os_type or "w10" in os_type:
            os_key = "Windows 10"
        else:
            raise ValueError(f"Unsupported OS type: {os_type}")
        
        # 检查操作系统是否存在
        if os_key not in self.product_edition_ids:
            raise ValueError(
                f"Configuration for {os_key} not found in config file. Available OS: {list(self.product_edition_ids.keys())}"
            )
        
        os_config = self.product_edition_ids[os_key]
        
        # 查找版本（不区分大小写）
        version_key = None
        version_lower = version.upper() if version else ""
        
        # 如果没有指定版本，使用第一个可用版本（通常是最新的）
        if not version:
            if os_config:
                version_key = list(os_config.keys())[0]
                logger.info(f"No version specified, using default version: {version_key}")
        else:
            # 尝试精确匹配
            for key in os_config.keys():
                if key.upper() == version_lower:
                    version_key = key
                    break
            
            # 如果精确匹配失败，尝试部分匹配
            if not version_key:
                for key in os_config.keys():
                    if version_lower in key.upper() or key.upper() in version_lower:
                        version_key = key
                        break
        
        if not version_key:
            available_versions = list(os_config.keys())
            raise ValueError(
                f"Version '{version}' for {os_key} not found in config file. Available versions: {available_versions}"
            )
        
        version_config = os_config[version_key]
        
        # 只支持 Multi Editions
        if "Multi Editions" not in version_config:
            raise ValueError(
                f"Multi Editions configuration for {os_key} {version_key} not found in config file."
            )
        
        multi_editions = version_config["Multi Editions"]
        if "ids" not in multi_editions:
            raise ValueError(
                f"Multi Editions for {os_key} {version_key} is missing 'ids' field in config file."
            )
        
        product_ids = multi_editions["ids"]
        
        # 确保返回的是列表
        if isinstance(product_ids, list):
            return product_ids
        elif isinstance(product_ids, int):
            return [product_ids]
        else:
            raise ValueError(
                f"Product ID format error in config file: {os_key}/{version_key}/Multi Editions/ids = {product_ids}"
            )
    
    def list_sources(self) -> list[str]:
        """获取可用的镜像源列表"""
        return ["microsoft", "msdn", "local"]
    
    def list_available_versions(self, os_type: str | None = None) -> dict[str, Any]:
        """
        从配置文件中获取可用版本列表（包含description字段用于前端过滤）
        
        Args:
            os_type: 操作系统类型（可选），如果提供则只返回该OS的版本列表
        
        Returns:
            字典，格式为 {
                "Windows 11": {
                    "25H2": {"description": "Windows 11 25H2", "build": "26200.6584"},
                    "24H2": {"description": "Windows 11 24H2", "build": "26100.1742"},
                    ...
                },
                "Windows 10": {
                    "22H2": {"description": "Windows 10 22H2", "build": "19045.2965"},
                    ...
                }
            }
            如果指定了 os_type，则只返回该OS的版本列表
        """
        if not self.product_edition_ids:
            return {}
        
        result = {}
        
        for os_key, os_config in self.product_edition_ids.items():
            # 如果指定了 os_type，只处理匹配的OS
            if os_type:
                os_key_lower = os_key.lower().replace(" ", "")
                os_type_lower = os_type.lower().replace(" ", "")
                if os_key_lower not in os_type_lower and os_type_lower not in os_key_lower:
                    continue
            
            # 提取所有版本信息（包含description和build）
            versions = {}
            for version_key, version_config in os_config.items():
                # 跳过注释字段
                if version_key.startswith('_'):
                    continue
                
                # 获取description字段
                description = version_config.get("description", version_key)
                
                # 过滤掉description中包含[已失效]的版本
                if description and '[已失效]' in description:
                    continue
                
                # 提取description和build字段
                versions[version_key] = {
                    "description": description,
                    "build": version_config.get("build", "")
                }
            
            if versions:
                # 按版本号降序排列（保持字典顺序，但前端会重新排序）
                result[os_key] = versions
        
        return result
    
    def list_images(
        self,
        source: str,
        filter_options: dict[str, str] | None = None
    ) -> list[dict[str, Any]]:
        """
        获取镜像列表
        
        Args:
            source: 镜像源 ("microsoft" | "msdn" | "local")
            filter_options: 过滤选项 {"os": "Windows10|Windows11|Server", "arch": "x64|x86|ARM64"}
        
        Returns:
            镜像列表
        """
        if source == "microsoft":
            return self._list_microsoft_images(filter_options)
        elif source == "msdn":
            return self._list_msdn_images(filter_options)
        elif source == "local":
            return self._list_local_images(filter_options)
        else:
            raise ValueError(f"Unknown image source: {source}")
    
    def _list_microsoft_images(self, filter_options: dict[str, str] | None) -> list[dict[str, Any]]:
        """
        从微软官网获取镜像列表（基于Fido方案）
        
        参考Fido.ps1的实现：
        1. 使用微软的API端点获取下载链接
        2. 需要先白名单sessionId
        3. 通过productEditionId获取SKU信息
        4. 通过SKU ID获取下载链接
        
        Args:
            filter_options: 过滤选项，支持：
                - os: Windows10/Windows11
                - arch: x64/x86/ARM64
                - language: 语言代码（如zh-CN, en-US），默认为zh-CN
                - version: 版本号（如25H2, 22H2）
                - edition: 版本类型（如Home/Pro/Edu）
        """
        images = []
        
        # 根据过滤选项确定要访问的页面
        os_type = filter_options.get("os", "").lower() if filter_options else ""
        # 默认简体中文，但需要检查是否可用（如果不可用，API会返回其他语言）
        language = filter_options.get("language", "zh-CN") if filter_options else "zh-CN"
        # 保存原始语言用于后续API调用
        query_locale = language
        version = filter_options.get("version", "").lower() if filter_options else ""
        edition = filter_options.get("edition", "").lower() if filter_options else ""
        
        # 如果没有指定OS类型，直接抛异常
        if not os_type or ("windows10" not in os_type and "win10" not in os_type and "w10" not in os_type and 
                          "windows11" not in os_type and "win11" not in os_type and "w11" not in os_type):
            raise ValueError("OS type (Windows10 or Windows11) must be specified to get image list from Microsoft website")
        
        try:
            # 确定下载页面URL
            if "windows11" in os_type or "win11" in os_type or "w11" in os_type:
                download_page_url = "https://www.microsoft.com/software-download/windows11"
                referer_url = "https://www.microsoft.com/software-download/windows11"
            elif "windows10" in os_type or "win10" in os_type or "w10" in os_type:
                download_page_url = "https://www.microsoft.com/software-download/windows10"
                referer_url = "https://www.microsoft.com/software-download/windows10"
            else:
                raise ValueError(f"Unsupported OS type: {os_type}")
            
            # 从配置文件获取产品版本ID（仅支持 Multi Editions）
            product_edition_ids = self._get_product_edition_ids_from_config(os_type, version)
            
            # 微软API配置（基于Fido）
            org_id = "y6jn8c31"
            profile_id = "606624d44113"
            timeout = 30
            
            # 为每个productEditionId生成sessionId并获取SKU信息
            session_ids = []
            sku_data = {}  # {language: {DisplayName: str, Data: [{SessionIndex: int, SkuId: str}]}}
            
            for idx, edition_id in enumerate(product_edition_ids):
                # 生成sessionId
                session_id = str(uuid.uuid4())
                session_ids.append(session_id)
                
                # 步骤1: 白名单sessionId
                tags_url = f"https://vlscppe.microsoft.com/tags?org_id={org_id}&session_id={session_id}"
                try:
                    response = requests.get(tags_url, timeout=timeout, allow_redirects=False)
                    # 不检查状态码，因为可能返回重定向
                except Exception as e:
                    logger.error(f"Failed to whitelist sessionId: {e}")
                    continue
                
                # 步骤2: 获取SKU信息（语言列表）
                sku_url = (
                    f"https://www.microsoft.com/software-download-connector/api/getskuinformationbyproductedition"
                    f"?profile={profile_id}"
                    f"&productEditionId={edition_id}"
                    f"&SKU=undefined"
                    f"&friendlyFileName=undefined"
                    f"&Locale={language}"
                    f"&sessionID={session_id}"
                )
                
                try:
                    # 使用Session保持cookie，并添加必要的请求头
                    session = requests.Session()
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "application/json, text/plain, */*",
                        "Accept-Language": f"{language},en-US;q=0.9",
                        "Referer": referer_url,
                        "Origin": "https://www.microsoft.com"
                    }
                    response = session.get(sku_url, headers=headers, timeout=timeout)
                    response.raise_for_status()
                    
                    # 尝试解析JSON（即使Content-Type不是application/json）
                    try:
                        sku_info = response.json()
                    except ValueError:
                        # 如果解析失败，检查是否是HTML响应
                        content_type = response.headers.get('Content-Type', '').lower()
                        if 'html' in content_type:
                            logger.warning(f"API returned HTML format (Content-Type: {content_type}, Status: {response.status_code})")
                            logger.debug(f"Response content first 500 chars: {response.text[:500]}")
                            raise Exception(f"API returned HTML format: {content_type}")
                        else:
                            # 尝试解析为JSON（可能是text/plain但内容是JSON）
                            logger.warning(f"Content-Type is {content_type}, attempting to parse as JSON")
                            try:
                                sku_info = response.json()
                            except ValueError as e:
                                logger.error(f"JSON parsing failed: {e}")
                                logger.debug(f"Response content first 500 chars: {response.text[:500]}")
                                raise Exception(f"Failed to parse JSON response: {e}")
                    
                    if sku_info.get("Errors"):
                        error_msg = sku_info["Errors"][0].get("Value", "Unknown error")
                        raise Exception(f"Failed to get SKU information: {error_msg}")
                    
                    # 解析SKU信息
                    for sku in sku_info.get("Skus", []):
                        lang = sku.get("Language", "")
                        sku_id = sku.get("Id", "")
                        if not sku_id:
                            continue
                        if lang not in sku_data:
                            sku_data[lang] = {
                                "DisplayName": sku.get("LocalizedLanguage", lang),
                                "Data": []
                            }
                        sku_data[lang]["Data"].append({
                            "SessionIndex": idx,
                            "SkuId": sku_id
                        })
                    
                    # 调试信息：打印获取到的语言和SKU数量
                    if sku_info.get("Skus"):
                        logger.info(f"Successfully retrieved {len(sku_info.get('Skus', []))} SKUs")
                        for sku in sku_info.get("Skus", [])[:3]:  # 只打印前3个
                            logger.debug(f"  - Language: {sku.get('Language', 'N/A')}, SKU ID: {sku.get('Id', 'N/A')}")
                
                except Exception as e:
                    logger.error(f"Failed to get SKU info (edition_id={edition_id}): {e}")
                    continue
            
            # 如果没有获取到SKU信息，抛出异常
            if not sku_data:
                raise ValueError("Failed to get SKU information, please check network connection or try again later")
            
            # 步骤3: 获取下载链接
            # 打印所有可用的语言
            logger.info(f"Available languages: {list(sku_data.keys())}")
            
            # 语言代码映射（API返回的语言名称 -> 标准语言代码）
            api_name_to_code = {
                "chinese (simplified)": "zh-CN",
                "chinese (traditional)": "zh-TW",
                "english": "en-US",
                "english international": "en-US",
                "french": "fr-FR",
                "french canadian": "fr-CA",
                "german": "de-DE",
                "japanese": "ja-JP",
                "korean": "ko-KR",
                "spanish": "es-ES",
                "spanish (mexico)": "es-MX",
                "portuguese": "pt-PT",
                "brazilian portuguese": "pt-BR",
                "russian": "ru-RU",
                "italian": "it-IT",
                "dutch": "nl-NL",
                "polish": "pl-PL",
                "turkish": "tr-TR",
                "arabic": "ar-SA",
                "danish": "da-DK",
                "swedish": "sv-SE",
                "norwegian": "nb-NO",
                "finnish": "fi-FI",
                "czech": "cs-CZ",
                "hungarian": "hu-HU",
                "romanian": "ro-RO",
                "greek": "el-GR",
                "hebrew": "he-IL",
                "thai": "th-TH",
                "ukrainian": "uk-UA",
                "bulgarian": "bg-BG",
                "croatian": "hr-HR",
                "serbian latin": "sr-Latn-RS",
                "slovak": "sk-SK",
                "slovenian": "sl-SI",
                "estonian": "et-EE",
                "latvian": "lv-LV",
                "lithuanian": "lt-LT"
            }
            
            # 创建反向映射（标准语言代码 -> API返回的语言名称）
            code_to_api_name = {}
            for api_name, code in api_name_to_code.items():
                if code not in code_to_api_name:
                    code_to_api_name[code] = []
                code_to_api_name[code].append(api_name)
            
            # 优先使用指定的语言，如果没有则使用第一个可用语言
            target_language = None
            language_lower = language.lower()
            
            # 首先尝试直接匹配（用户输入的语言代码或名称与API返回的名称完全匹配）
            for lang in sku_data.keys():
                if lang.lower() == language_lower:
                    target_language = lang
                    break
            
            # 如果直接匹配失败，尝试通过语言代码映射匹配
            if not target_language:
                # 如果用户输入的是标准语言代码（如zh-CN），查找对应的API语言名称
                if language_lower in code_to_api_name:
                    for api_name in code_to_api_name[language_lower]:
                        for lang in sku_data.keys():
                            if lang.lower() == api_name.lower():
                                target_language = lang
                                break
                        if target_language:
                            break
                else:
                    # 如果用户输入的是语言名称，查找对应的标准代码，然后查找API语言名称
                    target_code = api_name_to_code.get(language_lower)
                    if target_code and target_code in code_to_api_name:
                        for api_name in code_to_api_name[target_code]:
                            for lang in sku_data.keys():
                                if lang.lower() == api_name.lower():
                                    target_language = lang
                                    break
                            if target_language:
                                break
            
            # 如果仍然找不到，尝试模糊匹配（包含关系）
            if not target_language:
                for lang in sku_data.keys():
                    lang_lower = lang.lower()
                    # 检查用户输入是否包含在API语言名称中，或API语言名称是否包含在用户输入中
                    if language_lower in lang_lower or lang_lower in language_lower:
                        target_language = lang
                        break
                    # 检查API语言名称映射后的代码是否匹配
                    mapped_code = api_name_to_code.get(lang_lower)
                    if mapped_code and mapped_code.lower() == language_lower:
                        target_language = lang
                        break
            
            if not target_language:
                target_language = list(sku_data.keys())[0]
                logger.info(f"Language {language} not available, using {target_language}")
            else:
                logger.info(f"Matched language: {target_language} (requested: {language})")
            
            language_info = sku_data[target_language]
            logger.info(f"Using language: {target_language}, SKU count: {len(language_info['Data'])}")
            
            for entry in language_info["Data"]:
                session_idx = entry["SessionIndex"]
                sku_id = entry["SkuId"]
                session_id = session_ids[session_idx]
                
                # 获取下载链接
                # 注意：Locale应该使用用户指定的语言（query_locale），而不是从SKU返回的语言
                download_url = (
                    f"https://www.microsoft.com/software-download-connector/api/GetProductDownloadLinksBySku"
                    f"?profile={profile_id}"
                    f"&productEditionId=undefined"
                    f"&SKU={sku_id}"
                    f"&friendlyFileName=undefined"
                    f"&Locale={query_locale}"
                    f"&sessionID={session_id}"
                )
                
                try:
                    # 必须添加Referer头，否则微软服务器可能拒绝请求
                    # 使用Session保持cookie
                    session = requests.Session()
                    headers = {
                        "Referer": referer_url,
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "application/json, text/plain, */*",
                        "Accept-Language": f"{query_locale},en-US;q=0.9",
                        "Origin": "https://www.microsoft.com"
                    }
                    response = session.get(download_url, headers=headers, timeout=timeout)
                    response.raise_for_status()
                    download_info = response.json()
                    
                    if download_info.get("Errors"):
                        error = download_info["Errors"][0]
                        if error.get("Type") == 9:
                            # Error type 9 indicates IP banned or region restricted
                            error_msg = (
                                f"Your IP address has been banned by Microsoft or is in a sanctioned region. "
                                f"Session ID: {session_id}"
                            )
                            raise Exception(error_msg)
                        else:
                            error_msg = error.get("Value", "Unknown error")
                            raise Exception(f"Failed to get download link: {error_msg}")
                    
                    # 解析下载选项
                    for option in download_info.get("ProductDownloadOptions", []):
                        download_type = option.get("DownloadType", 1)  # 0=x86, 1=x64, 2=ARM64
                        download_url_uri = option.get("Uri", "")
                        
                        if not download_url_uri:
                            continue
                        
                        # 转换架构类型
                        arch_map = {0: "x86", 1: "x64", 2: "ARM64"}
                        arch = arch_map.get(download_type, "x64")
                        
                        # 从URL提取镜像信息
                        # 从下载URL中提取文件名信息（可能不符合标准格式，这里仅用于显示）
                        # 实际下载后的文件会使用标准格式重命名
                        image_info = {}
                        
                        # Extract filename from URL, removing query parameters
                        url_path = download_url_uri.split('?')[0]  # Remove query parameters
                        filename = os.path.basename(url_path) or f"Windows_ISO_{arch}.iso"
                        
                        images.append({
                            "id": f"microsoft_{len(images)}",
                            "name": filename,
                            "version": version.upper() if version else "",
                            "architecture": arch,
                            "source_type": "me",  # microsoft 官网标记为 Multi Editions
                            "size": 0,  # 需要从HEAD请求获取
                            "url": download_url_uri,
                            "url_type": "http",
                            "source": "microsoft",
                            "checksum": "",
                            "language": target_language
                        })
                
                except Exception as e:
                    logger.error(f"Failed to get download link (sku_id={sku_id}): {e}")
                    continue
            
            # 如果仍然没有找到，抛出异常
            if not images:
                raise ValueError(
                    f"Failed to get image list from Microsoft official website. Possible reasons: 1) Network connection issue 2) Specified language/version/edition not available 3) IP restricted"
                )
        
        except Exception as e:
            logger.error(f"Microsoft official website parsing failed: {e}")
            raise
        
        return self._filter_images(images, filter_options)
    
    def fetch_download_url(self, source: str, config: dict[str, str]) -> dict[str, Any]:
        """
        根据配置精确获取下载URL/magnet（不返回列表，只返回第一个匹配的结果）
        
        Args:
            source: 镜像源 ("microsoft" | "msdn")
            config: 配置参数 {
                "os": "Windows10" | "Windows11",
                "version": "25H2" | "24H2" | ...,
                "language": "zh-CN" | "en-US" | ...,
                "arch": "x64" | "x86" | "ARM64"
            }
        
        Returns:
            包含URL信息的字典: {
                "url": str,
                "url_type": "http" | "magnet",
                "name": str,
                "architecture": str,
                "language": str,
                "source_type": str,
                ...
            }
        
        Raises:
            ValueError: 如果找不到匹配的URL
        """
        if source == "microsoft":
            return self._fetch_microsoft_url(config)
        elif source == "msdn":
            return self._fetch_msdn_url(config)
        else:
            raise ValueError(f"Unsupported image source: {source}")
    
    def _fetch_microsoft_url(self, config: dict[str, str]) -> dict[str, Any]:
        """
        从微软官网精确获取下载URL（复用_list_microsoft_images的核心逻辑）
        """
        os_type = config.get("os", "").lower()
        language = config.get("language", "zh-CN")
        version = config.get("version", "").lower()
        arch = config.get("arch", "x64").lower()
        
        # 确定下载页面URL
        if "windows11" in os_type or "win11" in os_type or "w11" in os_type:
            download_page_url = "https://www.microsoft.com/software-download/windows11"
            referer_url = "https://www.microsoft.com/software-download/windows11"
        elif "windows10" in os_type or "win10" in os_type or "w10" in os_type:
            download_page_url = "https://www.microsoft.com/software-download/windows10"
            referer_url = "https://www.microsoft.com/software-download/windows10"
        else:
            raise ValueError(f"Unsupported OS type: {os_type}")
        
        # 从配置文件获取产品版本ID
        product_edition_ids = self._get_product_edition_ids_from_config(os_type, version)
        
        # 微软API配置
        org_id = "y6jn8c31"
        profile_id = "606624d44113"
        timeout = 30
        
        # 为每个productEditionId生成sessionId并获取SKU信息
        session_ids = []
        sku_data = {}
        
        for idx, edition_id in enumerate(product_edition_ids):
            session_id = str(uuid.uuid4())
            session_ids.append(session_id)
            
            # 步骤1: 白名单sessionId
            tags_url = f"https://vlscppe.microsoft.com/tags?org_id={org_id}&session_id={session_id}"
            try:
                response = requests.get(tags_url, timeout=timeout, allow_redirects=False)
            except Exception as e:
                logger.error(f"Failed to whitelist sessionId: {e}")
                continue
            
            # 步骤2: 获取SKU信息
            sku_url = (
                f"https://www.microsoft.com/software-download-connector/api/getskuinformationbyproductedition"
                f"?profile={profile_id}"
                f"&productEditionId={edition_id}"
                f"&SKU=undefined"
                f"&friendlyFileName=undefined"
                f"&Locale={language}"
                f"&sessionID={session_id}"
            )
            
            try:
                session = requests.Session()
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": f"{language},en-US;q=0.9",
                    "Referer": referer_url,
                    "Origin": "https://www.microsoft.com"
                }
                response = session.get(sku_url, headers=headers, timeout=timeout)
                response.raise_for_status()
                
                try:
                    sku_info = response.json()
                except ValueError:
                    content_type = response.headers.get('Content-Type', '').lower()
                    if 'html' in content_type:
                        raise Exception(f"API returned HTML format: {content_type}")
                    try:
                        sku_info = response.json()
                    except ValueError as e:
                        raise Exception(f"Failed to parse JSON response: {e}")
                
                if sku_info.get("Errors"):
                    error_msg = sku_info["Errors"][0].get("Value", "Unknown error")
                    raise Exception(f"Failed to get SKU information: {error_msg}")
                
                # 解析SKU信息
                for sku in sku_info.get("Skus", []):
                    lang = sku.get("Language", "")
                    sku_id = sku.get("Id", "")
                    if not sku_id:
                        continue
                    if lang not in sku_data:
                        sku_data[lang] = {
                            "DisplayName": sku.get("LocalizedLanguage", lang),
                            "Data": []
                        }
                    sku_data[lang]["Data"].append({
                        "SessionIndex": idx,
                        "SkuId": sku_id
                    })
            
            except Exception as e:
                logger.error(f"Failed to get SKU info (edition_id={edition_id}): {e}")
                continue
        
        if not sku_data:
            raise ValueError("Failed to get SKU information, please check network connection or try again later")
        
        # 语言代码映射
        api_name_to_code = {
            "chinese (simplified)": "zh-CN",
            "chinese (traditional)": "zh-TW",
            "english": "en-US",
            "english international": "en-US",
        }
        
        code_to_api_name = {}
        for api_name, code in api_name_to_code.items():
            if code not in code_to_api_name:
                code_to_api_name[code] = []
            code_to_api_name[code].append(api_name)
        
        # 匹配语言
        target_language = None
        language_lower = language.lower()
        
        for lang in sku_data.keys():
            if lang.lower() == language_lower:
                target_language = lang
                break
        
        if not target_language:
            if language_lower in code_to_api_name:
                for api_name in code_to_api_name[language_lower]:
                    for lang in sku_data.keys():
                        if lang.lower() == api_name.lower():
                            target_language = lang
                            break
                    if target_language:
                        break
        
        if not target_language:
            target_language = list(sku_data.keys())[0]
            logger.info(f"Language {language} not available, using {target_language}")
        
        language_info = sku_data[target_language]
        
        # 架构映射
        arch_map = {"x86": 0, "x64": 1, "arm64": 2}
        target_arch_type = arch_map.get(arch, 1)
        
        # 获取下载链接（只返回匹配架构的第一个）
        for entry in language_info["Data"]:
            session_idx = entry["SessionIndex"]
            sku_id = entry["SkuId"]
            session_id = session_ids[session_idx]
            
            download_url = (
                f"https://www.microsoft.com/software-download-connector/api/GetProductDownloadLinksBySku"
                f"?profile={profile_id}"
                f"&productEditionId=undefined"
                f"&SKU={sku_id}"
                f"&friendlyFileName=undefined"
                f"&Locale={language}"
                f"&sessionID={session_id}"
            )
            
            try:
                session = requests.Session()
                headers = {
                    "Referer": referer_url,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": f"{language},en-US;q=0.9",
                    "Origin": "https://www.microsoft.com"
                }
                response = session.get(download_url, headers=headers, timeout=timeout)
                response.raise_for_status()
                download_info = response.json()
                
                if download_info.get("Errors"):
                    error = download_info["Errors"][0]
                    if error.get("Type") == 9:
                        raise Exception("Your IP address has been banned by Microsoft or is in a sanctioned region.")
                    else:
                        error_msg = error.get("Value", "Unknown error")
                        raise Exception(f"Failed to get download link: {error_msg}")
                
                # 查找匹配架构的下载选项
                for option in download_info.get("ProductDownloadOptions", []):
                    download_type = option.get("DownloadType", 1)
                    download_url_uri = option.get("Uri", "")
                    
                    if not download_url_uri:
                        continue
                    
                    # 只返回匹配架构的URL
                    if download_type == target_arch_type:
                        arch_map_reverse = {0: "x86", 1: "x64", 2: "ARM64"}
                        arch_name = arch_map_reverse.get(download_type, "x64")
                        url_path = download_url_uri.split('?')[0]
                        filename = os.path.basename(url_path) or f"Windows_ISO_{arch_name}.iso"
                        
                        return {
                            "url": download_url_uri,
                            "url_type": "http",
                            "name": filename,
                            "architecture": arch_name,
                            "language": target_language,
                            "source_type": "me",
                            "source": "microsoft",
                            "version": version.upper() if version else ""
                        }
            
            except Exception as e:
                logger.error(f"Failed to get download link (sku_id={sku_id}): {e}")
                continue
        
        raise ValueError(
            f"Failed to get download URL from Microsoft. Possible reasons: 1) Network connection issue 2) Specified language/version/arch not available 3) IP restricted"
        )
    
    def _fetch_msdn_url(self, config: dict[str, str]) -> dict[str, Any]:
        """
        从MSDN镜像站精确获取magnet链接（复用_list_msdn_images的核心逻辑）
        """
        os_type = config.get("os", "").lower()
        version = config.get("version", "").lower()
        language = config.get("language", "zh-cn")
        arch = config.get("arch", "x64").lower()
        
        # 构建要尝试的URL列表
        urls_to_try = []
        
        if "windows10" in os_type or "win10" in os_type or "w10" in os_type:
            urls_to_try = [
                "https://msdn.sjjzm.com/win10.html",
                "https://msdn.sjjzm.com/windows10.html",
            ]
            version_pages = ["22h2", "21h2", "21h1", "20h2", "2004", "1909", "1903"]
            for v in version_pages:
                urls_to_try.append(f"https://msdn.sjjzm.com/win10/{v}.html")
        elif "windows11" in os_type or "win11" in os_type or "w11" in os_type:
            urls_to_try = [
                "https://msdn.sjjzm.com/win11.html",
                "https://msdn.sjjzm.com/windows11.html",
            ]
            version_pages = ["25h2", "24h2", "23h2", "22h2", "21h2"]
            for v in version_pages:
                urls_to_try.append(f"https://msdn.sjjzm.com/win11/{v}.html")
        else:
            raise ValueError(f"Unsupported OS type: {os_type}")
        
        # 访问页面并解析magnet链接
        for url in urls_to_try:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'lxml')
                    
                    # 查找所有magnet链接
                    for link in soup.find_all('a', href=True):
                        href = str(link.get('href', '')).strip()
                        if href.startswith('magnet:'):
                            filename = link.get_text(strip=True) or self._parse_magnet_filename(href)
                            try:
                                image_info = self._parse_iso_filename(filename)
                                # 检查是否匹配配置
                                if self._matches_config(image_info, config):
                                    return {
                                        "url": href,
                                        "url_type": "magnet",
                                        "name": filename,
                                        "architecture": image_info.get("arch", "x64"),
                                        "language": image_info.get("language", ""),
                                        "source_type": "ce",
                                        "source": "msdn",
                                        "version": image_info.get("version", ""),
                                        "build": image_info.get("build", ""),
                                        "checksum": self._parse_magnet_hash(href),
                                        "size": self._parse_magnet_size(href)
                                    }
                            except ValueError:
                                continue
                    
                    # 从表格中提取镜像信息
                    import re
                    for table in soup.find_all('table'):
                        current_image = {}
                        for row in table.find_all('tr'):
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 2:
                                key = cells[0].get_text(strip=True)
                                value = cells[1].get_text(strip=True)
                                
                                if '文件名' in key or 'file' in key.lower():
                                    current_image['name'] = value
                                    try:
                                        image_info = self._parse_iso_filename(value)
                                        current_image.update(image_info)
                                    except ValueError:
                                        current_image = {}
                                        continue
                                
                                elif '大小' in key or 'size' in key.lower():
                                    size_str = value.replace('GB', '').replace('MB', '').strip()
                                    try:
                                        size_val = float(size_str)
                                        if 'GB' in value:
                                            current_image['size'] = int(size_val * 1024 * 1024 * 1024)
                                        elif 'MB' in value:
                                            current_image['size'] = int(size_val * 1024 * 1024)
                                    except:
                                        pass
                                
                                elif 'sha-256' in key.lower() or 'sha256' in key.lower():
                                    current_image['checksum'] = value
                            
                            # 查找magnet链接
                            for cell in cells:
                                for link in cell.find_all('a', href=True):
                                    href = str(link.get('href', '')).strip()
                                    if href.startswith('magnet:'):
                                        if current_image.get('name'):
                                            if self._matches_config(current_image, config):
                                                return {
                                                    "url": href,
                                                    "url_type": "magnet",
                                                    "name": current_image.get('name', ''),
                                                    "architecture": current_image.get('arch', 'x64'),
                                                    "language": current_image.get('language', ''),
                                                    "source_type": "ce",
                                                    "source": "msdn",
                                                    "version": current_image.get('version', ''),
                                                    "build": current_image.get('build', ''),
                                                    "checksum": current_image.get('checksum', self._parse_magnet_hash(href)),
                                                    "size": current_image.get('size', self._parse_magnet_size(href))
                                                }
                                
                                cell_text = cell.get_text()
                                magnet_match = re.search(r'magnet:[^\s\)]+', cell_text)
                                if magnet_match:
                                    magnet_url = magnet_match.group()
                                    if current_image.get('name') and self._matches_config(current_image, config):
                                        return {
                                            "url": magnet_url,
                                            "url_type": "magnet",
                                            "name": current_image.get('name', ''),
                                            "architecture": current_image.get('arch', 'x64'),
                                            "language": current_image.get('language', ''),
                                            "source_type": "ce",
                                            "source": "msdn",
                                            "version": current_image.get('version', ''),
                                            "build": current_image.get('build', ''),
                                            "checksum": current_image.get('checksum', self._parse_magnet_hash(magnet_url)),
                                            "size": current_image.get('size', self._parse_magnet_size(magnet_url))
                                        }
                                    current_image = {}
            except Exception as e:
                logger.error(f"Failed to parse MSDN page {url}: {e}")
                continue
        
        raise ValueError(f"Unable to get matching image link from MSDN mirror site")
    
    def _matches_config(self, image_info: dict[str, Any], config: dict[str, str]) -> bool:
        """
        检查镜像信息是否匹配配置
        
        Args:
            image_info: 镜像信息字典
            config: 配置参数
        
        Returns:
            是否匹配
        """
        # 检查架构
        arch = config.get("arch", "x64").lower()
        image_arch = image_info.get("arch", "").lower()
        if arch and image_arch and arch != image_arch:
            return False
        
        # 检查语言
        language = config.get("language", "").lower()
        image_lang = image_info.get("language", "").lower()
        if language and image_lang:
            # 支持部分匹配（如zh-cn匹配zh-CN）
            if language.replace("-", "") not in image_lang.replace("-", "") and image_lang.replace("-", "") not in language.replace("-", ""):
                return False
        
        # 检查版本（如果配置中指定了版本）
        version = config.get("version", "").lower()
        if version:
            image_version = image_info.get("version", "").lower()
            if image_version and version not in image_version and image_version not in version:
                return False
        
        return True
    
    def _list_msdn_images(self, filter_options: dict[str, str] | None) -> list[dict[str, Any]]:
        """
        从 msdn.sjjzm.com 获取镜像列表（HTML解析，仅支持magnet/BT链接）
        """
        images = []
        
        # 根据过滤选项确定要访问的页面
        os_type = filter_options.get("os", "").lower() if filter_options else ""
        
        # 如果没有指定OS类型，直接抛异常
        if not os_type or ("windows10" not in os_type and "win10" not in os_type and "w10" not in os_type and 
                          "windows11" not in os_type and "win11" not in os_type and "w11" not in os_type):
            raise ValueError("OS type (Windows10 or Windows11) must be specified to get image list from MSDN mirror site")
        
        try:
            # 构建要尝试的URL列表
            urls_to_try = []
            
            if "windows10" in os_type or "win10" in os_type or "w10" in os_type:
                # Windows 10页面
                urls_to_try = [
                    "https://msdn.sjjzm.com/win10.html",
                    "https://msdn.sjjzm.com/windows10.html",
                    "https://msdn.sjjzm.com/windows-10.html",
                ]
                # 尝试访问Windows 10的各个版本页面
                version_pages = ["22h2", "21h2", "21h1", "20h2", "2004", "1909", "1903"]
                for version in version_pages:
                    urls_to_try.append(f"https://msdn.sjjzm.com/win10/{version}.html")
            elif "windows11" in os_type or "win11" in os_type or "w11" in os_type:
                # Windows 11页面
                urls_to_try = [
                    "https://msdn.sjjzm.com/win11.html",
                    "https://msdn.sjjzm.com/windows11.html",
                    "https://msdn.sjjzm.com/windows-11.html",
                ]
                # 尝试访问Windows 11的各个版本页面
                version_pages = ["25h2", "24h2", "23h2", "22h2", "21h2"]
                for version in version_pages:
                    urls_to_try.append(f"https://msdn.sjjzm.com/win11/{version}.html")
            
            # 访问页面并解析magnet链接
            for url in urls_to_try:
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'lxml')
                        
                        # 查找所有magnet链接
                        for link in soup.find_all('a', href=True):
                            href = str(link.get('href', '')).strip()
                            text = link.get_text(strip=True)
                            
                            # 仅检查magnet链接
                            if href.startswith('magnet:'):
                                # 尝试解析文件名（可能不符合标准格式）
                                            filename = text or self._parse_magnet_filename(href)
                                            try:
                                                image_info = self._parse_iso_filename(filename)
                                            except ValueError:
                                                # 如果不符合标准格式，跳过
                                                continue
                                            
                                            images.append({
                                                "id": f"msdn_magnet_{len(images)}",
                                                "name": filename,
                                                "version": image_info.get("version", ""),
                                                "build": image_info.get("build", ""),
                                                "build_major": image_info.get("build_major", ""),
                                                "build_minor": image_info.get("build_minor", ""),
                                                "architecture": image_info.get("arch", "x64"),
                                                "language": image_info.get("language", ""),
                                                "source_type": "ce",  # msdn 镜像站标记为 Consumer Editions
                                                "os_type": image_info.get("os_type", ""),
                                                "size": self._parse_magnet_size(href),
                                                "url": href,
                                                "url_type": "magnet",
                                                "source": "msdn",
                                                "checksum": self._parse_magnet_hash(href)
                                            })
                        
                        # 从表格中提取镜像信息并查找magnet链接
                        import re
                        for table in soup.find_all('table'):
                            current_image = {}
                            for row in table.find_all('tr'):
                                cells = row.find_all(['td', 'th'])
                                if len(cells) >= 2:
                                    key = cells[0].get_text(strip=True)
                                    value = cells[1].get_text(strip=True)
                                    
                                    if '文件名' in key or 'file' in key.lower():
                                        current_image['name'] = value
                                        # 尝试解析文件名（可能不符合标准格式）
                                        try:
                                            image_info = self._parse_iso_filename(value)
                                            current_image.update(image_info)
                                        except ValueError:
                                            # 如果不符合标准格式，跳过
                                            current_image = {}
                                            continue
                                    
                                    elif '大小' in key or 'size' in key.lower():
                                        size_str = value.replace('GB', '').replace('MB', '').strip()
                                        try:
                                            size_val = float(size_str)
                                            if 'GB' in value:
                                                current_image['size'] = int(size_val * 1024 * 1024 * 1024)
                                            elif 'MB' in value:
                                                current_image['size'] = int(size_val * 1024 * 1024)
                                        except:
                                            pass
                                    
                                    elif 'sha-256' in key.lower() or 'sha256' in key.lower():
                                        current_image['checksum'] = value
                                
                                # 在单元格中查找magnet链接（可能在文本中或链接标签中）
                                for cell in cells:
                                    # 方法1: 检查链接标签
                                    for link in cell.find_all('a', href=True):
                                        href = str(link.get('href', '')).strip()
                                        text = link.get_text(strip=True)
                                        
                                        # 仅检查magnet链接
                                        if href.startswith('magnet:'):
                                            # 尝试解析文件名（可能不符合标准格式）
                                            filename = text or self._parse_magnet_filename(href)
                                            try:
                                                image_info = self._parse_iso_filename(filename)
                                            except ValueError:
                                                # 如果不符合标准格式，跳过
                                                continue
                                            
                                            images.append({
                                                "id": f"msdn_magnet_{len(images)}",
                                                "name": filename,
                                                "version": image_info.get("version", ""),
                                                "build": image_info.get("build", ""),
                                                "build_major": image_info.get("build_major", ""),
                                                "build_minor": image_info.get("build_minor", ""),
                                                "architecture": image_info.get("arch", "x64"),
                                                "language": image_info.get("language", ""),
                                                "source_type": "ce",  # msdn 镜像站标记为 Consumer Editions
                                                "os_type": image_info.get("os_type", ""),
                                                "size": self._parse_magnet_size(href),
                                                "url": href,
                                                "url_type": "magnet",
                                                "source": "msdn",
                                                "checksum": self._parse_magnet_hash(href)
                                            })
                                    
                                    # 方法2: 在文本中查找magnet链接（正则表达式）
                                    cell_text = cell.get_text()
                                    magnet_match = re.search(r'magnet:[^\s\)]+', cell_text)
                                    if magnet_match:
                                        magnet_url = magnet_match.group()
                                        if current_image.get('name'):
                                            images.append({
                                                "id": f"msdn_magnet_{len(images)}",
                                                "name": current_image.get('name', ''),
                                                "version": current_image.get('version', ''),
                                                "edition": current_image.get('edition', ''),
                                                "architecture": current_image.get('arch', 'x64'),
                                                "size": current_image.get('size', self._parse_magnet_size(magnet_url)),
                                                "url": magnet_url,
                                                "url_type": "magnet",
                                                "source": "msdn",
                                                "checksum": current_image.get('checksum', self._parse_magnet_hash(magnet_url))
                                            })
                                            current_image = {}  # 重置当前镜像信息
                        
                        # 如果找到了镜像，跳出循环
                        if images:
                            break
                except Exception as e:
                    continue
            
            # 如果仍然没有找到，抛出异常
            if not images:
                raise ValueError(f"Unable to get image list from MSDN mirror site, please check network connection or if website structure has changed")
        
        except Exception as e:
            logger.error(f"MSDN mirror site parsing failed: {e}")
        
        return self._filter_images(images, filter_options)
    
    def _parse_magnet_filename(self, magnet_link: str) -> str:
        """从magnet链接解析文件名"""
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(magnet_link)
            params = urllib.parse.parse_qs(parsed.query)
            return params.get('dn', [''])[0]
        except:
            pass
        return ""
    
    def _parse_magnet_size(self, magnet_link: str) -> int:
        """从magnet链接解析文件大小"""
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(magnet_link)
            params = urllib.parse.parse_qs(parsed.query)
            return int(params.get('xl', ['0'])[0])
        except:
            pass
        return 0
    
    def _parse_magnet_hash(self, magnet_link: str) -> str:
        """从magnet链接解析BT哈希"""
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(magnet_link)
            params = urllib.parse.parse_qs(parsed.query)
            btih = params.get('xt', [''])[0].replace('urn:btih:', '')
            return btih
        except:
            pass
        return ""
    
    def _list_local_images(self, filter_options: dict[str, str] | None) -> list[dict[str, Any]]:
        """扫描本地缓存目录"""
        images = []
        
        logger.info(f"Scanning local cache directory: {self.cache_dir.resolve()}")
        
        if not self.cache_dir.exists():
            logger.warning(f"Cache directory does not exist: {self.cache_dir}")
            return images
        
        # 删除非ISO格式文件
        self._cleanup_non_iso_files()
        
        iso_files = list(self.cache_dir.glob("*.iso"))
        logger.info(f"Found {len(iso_files)} ISO file(s) in cache directory")
        
        for iso_file in iso_files:
            try:
                logger.info(f"Processing ISO file: {iso_file.name}")
                
                # 首先尝试从文件名解析（如果符合标准格式）
                filename_info = None
                try:
                    filename_info = self._parse_iso_filename(iso_file.name)
                    logger.info(f"Filename parsed successfully: {filename_info}")
                except ValueError as e:
                    # 文件名不符合标准格式
                    logger.debug(f"Filename does not match standard format: {e}")
                    pass
                
                # 如果文件名符合标准格式，直接使用文件名信息，不进行版本识别
                if filename_info:
                    image_info = filename_info.copy()
                    image_info["checksum"] = ""  # 标准格式文件不计算校验和
                    logger.info(f"Using filename info directly (standard format): {image_info}")
                else:
                    # 文件名不符合标准格式，只显示文件名，不进行版本识别
                    image_info = {
                        "version": "",
                        "build": "",
                        "build_major": "",
                        "build_minor": "",
                        "arch": "x64",
                        "language": "",
                        "source_type": "",
                        "os_type": "",
                        "checksum": "",
                        "needs_identification": True  # 标记需要手动识别
                    }
                    logger.info(f"Non-standard filename, skipping identification: {iso_file.name}")
                
                image_data = {
                    "id": f"local_{iso_file.stem}",
                    "name": iso_file.name,
                    "version": image_info.get("version", ""),
                    "build": image_info.get("build", ""),
                    "build_major": image_info.get("build_major", ""),
                    "build_minor": image_info.get("build_minor", ""),
                    "architecture": image_info.get("arch", "x64"),
                    "language": image_info.get("language", ""),
                    "source_type": image_info.get("source_type", ""),
                    "os_type": image_info.get("os_type", ""),
                    "size": iso_file.stat().st_size,
                    "url": str(iso_file),
                    "url_type": "local",
                    "source": "local",
                    "checksum": image_info.get("checksum", ""),
                    "needs_identification": image_info.get("needs_identification", False)
                }
                
                logger.info(f"Adding image to list: {image_data['name']}")
                images.append(image_data)
                
            except Exception as e:
                logger.error(f"Failed to process ISO file {iso_file.name}: {e}")
                import traceback
                traceback.print_exc()
        
        logger.info(f"Total images before filtering: {len(images)}")
        filtered_images = self._filter_images(images, filter_options)
        logger.info(f"Total images after filtering: {len(filtered_images)}")
        
        return filtered_images
    
    def _cleanup_non_iso_files(self):
        """删除缓存目录中的非ISO格式文件"""
        if not self.cache_dir.exists():
            return
        
        deleted_count = 0
        for file_path in self.cache_dir.iterdir():
            if file_path.is_file() and not file_path.name.lower().endswith('.iso'):
                try:
                    logger.info(f"Deleting non-ISO file: {file_path.name}")
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete non-ISO file {file_path.name}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} non-ISO file(s) from cache directory")
    
    def identify_iso(self, iso_path: str) -> dict[str, Any]:
        """
        手动识别ISO文件版本信息
        
        Args:
            iso_path: ISO文件路径
        
        Returns:
            包含版本信息的字典
        """
        try:
            logger.info(f"Manually identifying ISO file: {iso_path}")
            # 使用新创建的 ISOInspector 服务进行识别
            inspector = ISOInspector(iso_path)
            image_info = inspector.get_summary()
            
            if not image_info or not image_info.get("version"):
                return {
                    "success": False,
                    "message": "Failed to identify ISO version information"
                }
            
            # 如果识别成功，尝试生成标准文件名并重命名
            # 这里的 image_info 包含 version, build_major, build_minor 等字段
            if image_info.get("version") and image_info.get("build_major") and image_info.get("build_minor"):
                try:
                    new_filename = self._generate_iso_filename(
                        os_type=image_info.get("os_type", ""),
                        version=image_info.get("version", ""),
                        build_major=image_info.get("build_major", ""),
                        build_minor=image_info.get("build_minor", ""),
                        language=image_info.get("language", "zh-cn"),
                        arch=image_info.get("arch", "x64"),
                        source_type=image_info.get("source_type", "ce")
                    )
                    
                    iso_path_obj = Path(iso_path)
                    new_path = iso_path_obj.parent / new_filename
                    
                    # 如果新文件名与当前文件名不同，重命名
                    if new_path != iso_path_obj:
                        if new_path.exists():
                            return {
                                "success": False,
                                "message": f"Target file already exists: {new_filename}"
                            }
                        iso_path_obj.rename(new_path)
                        logger.info(f"Renamed ISO file: {iso_path_obj.name} -> {new_filename}")
                        iso_path = str(new_path)
                except Exception as e:
                    logger.error(f"Failed to rename ISO file: {e}")
                    # 重命名失败不影响识别结果
            
            return {
                "success": True,
                "message": "ISO version identified successfully",
                "image_info": image_info,
                "file_path": iso_path
            }
        except Exception as e:
            logger.error(f"Failed to identify ISO file {iso_path}: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Failed to identify ISO: {str(e)}"
            }
    
    def import_iso(self, iso_path: str, overwrite: bool = False) -> dict[str, Any]:
        """
        导入ISO文件到 cache_dir (data/isos) 并按照标准格式重命名
        
        Args:
            iso_path: 源ISO文件路径
            overwrite: 如果目标文件已存在，是否覆盖（默认False）
        
        Returns:
            包含导入结果的字典:
            - success: 是否成功
            - message: 结果消息
            - source_path: 源文件路径
            - target_path: 目标文件路径（如果成功）
            - image_info: 识别到的版本信息（如果成功）
        
        Raises:
            FileNotFoundError: 如果源文件不存在
            ValueError: 如果无法识别版本信息或缺少必要字段
        """
        source_path = Path(iso_path)
        
        # 检查源文件是否存在
        if not source_path.exists():
            raise FileNotFoundError(f"Source ISO file does not exist: {iso_path}")
        
        if not source_path.is_file():
            raise ValueError(f"Path is not a file: {iso_path}")
        
        # 识别ISO版本信息
        logger.info(f"Starting ISO file version identification: {iso_path}")
        image_info = ISOInspector(str(source_path)).get_summary()
        
        # 检查是否识别成功，并验证必要字段
        required_fields = ["version", "build_major", "build_minor", "os_type", "arch", "language", "source_type"]
        missing_fields = [field for field in required_fields if not image_info.get(field)]
        
        if missing_fields:
            raise ValueError(
                f"Failed to identify complete version information of ISO file. Missing fields: {', '.join(missing_fields)}\n"
                f"识别到的信息: {image_info}"
            )
        
        # 生成标准文件名
        new_filename = self._generate_iso_filename(
            os_type=image_info["os_type"],
            version=image_info["version"],
            build_major=image_info["build_major"],
            build_minor=image_info["build_minor"],
            language=image_info["language"],
            arch=image_info["arch"],
            source_type=image_info["source_type"]
        )
        
        # 目标文件路径
        target_path = self.cache_dir / new_filename
        
        # 检查目标文件是否已存在
        if target_path.exists() and not overwrite:
            return {
                "success": False,
                "message": f"Target file already exists: {new_filename}. Set overwrite=True to overwrite",
                "source_path": str(source_path),
                "target_path": str(target_path),
                "image_info": image_info
            }
        
        # 复制文件到目标目录
        try:
            source_size = source_path.stat().st_size
            logger.info(f"Copying file: {source_path} -> {target_path}")
            logger.info(f"Source file size: {source_size / (1024**3):.2f} GB ({source_size:,} bytes)")
            
            # 使用 copy2 复制文件（保留元数据）
            shutil.copy2(source_path, target_path)
            
            # 验证复制结果
            if not target_path.exists():
                raise FileNotFoundError(f"Target file does not exist: {target_path}")
            
            target_size = target_path.stat().st_size
            logger.info(f"Target file size: {target_size / (1024**3):.2f} GB ({target_size:,} bytes)")
            
            if target_size != source_size:
                raise ValueError(
                    f"文件大小不匹配！源文件: {source_size:,} 字节, 目标文件: {target_size:,} 字节, "
                    f"差异: {abs(target_size - source_size):,} 字节"
                )
            
            logger.info(f"File imported successfully: {new_filename}")
            
            return {
                "success": True,
                "message": f"ISO file successfully imported and renamed to: {new_filename}",
                "source_path": str(source_path),
                "target_path": str(target_path),
                "image_info": image_info
            }
        except Exception as e:
            logger.error(f"File copy failed: {e}")
            import traceback
            traceback.print_exc()
            # 如果复制失败，尝试删除不完整的目标文件
            if target_path.exists():
                try:
                    target_path.unlink()
                    logger.info("Deleted incomplete target file")
                except Exception as cleanup_error:
                    logger.error(f"Failed to delete incomplete file: {cleanup_error}")
            
            return {
                "success": False,
                "message": f"File copy failed: {e}",
                "source_path": str(source_path),
                "target_path": str(target_path),
                "image_info": image_info
            }
    
    def _parse_iso_filename(self, filename: str) -> dict[str, str]:
        """
        解析标准格式的ISO文件名
        
        格式: {大版本}{me/ce}_{版本号}_{主构建号}_{次构建号}_{语言}_{架构}.iso
        示例: win11me_25h2_26200_6584_zh-cn_x64.iso
        
        Args:
            filename: ISO文件名
        
        Returns:
            包含解析信息的字典:
            - os_type: "Windows11" 或 "Windows10"
            - source_type: "me" (Multi Editions) 或 "ce" (Consumer Editions)
            - version: 版本号 (如 "25H2")
            - build_major: 主构建号 (如 "26200")
            - build_minor: 次构建号 (如 "6584")
            - build: 完整构建号 (如 "26200.6584")
            - language: 语言代码 (如 "zh-cn")
            - arch: 架构 (如 "x64")
        
        Raises:
            ValueError: 如果文件名不符合标准格式
        """
        # 移除路径，只保留文件名
        filename = os.path.basename(filename)
        
        # 移除 .iso 扩展名
        if filename.lower().endswith('.iso'):
            filename = filename[:-4]
        
        # 正则表达式匹配格式: win11me_25h2_26200_6584_zh-cn_x64
        pattern = r'^(win11|win10)(me|ce)_(\d{2}h\d)_(\d+)_(\d+)_([a-z]{2}(?:-[a-z]{2})?)_(x64|x86|arm64)$'
        match = re.match(pattern, filename.lower())
        
        if not match:
            raise ValueError(
                f"文件名不符合标准格式: {filename}\n"
                f"期望格式: {{大版本}}{{me/ce}}_{{版本号}}_{{主构建号}}_{{次构建号}}_{{语言}}_{{架构}}.iso\n"
                f"示例: win11me_25h2_26200_6584_zh-cn_x64.iso"
            )
        
        os_prefix = match.group(1)
        source_type = match.group(2)
        version = match.group(3).upper()
        build_major = match.group(4)
        build_minor = match.group(5)
        language = match.group(6).lower()
        arch = match.group(7).lower()
        
        # 确定操作系统类型
        if os_prefix == "win11":
            os_type = "Windows11"
        elif os_prefix == "win10":
            os_type = "Windows10"
        else:
            raise ValueError(f"Unsupported OS prefix: {os_prefix}")
        
        return {
            "os_type": os_type,
            "source_type": source_type,
            "version": version,
            "build_major": build_major,
            "build_minor": build_minor,
            "build": f"{build_major}.{build_minor}",
            "language": language,
            "arch": arch
        }
    
    def _generate_iso_filename(
        self,
        os_type: str,
        version: str,
        build_major: str,
        build_minor: str,
        language: str,
        arch: str,
        source_type: str
    ) -> str:
        """
        生成标准格式的ISO文件名
        
        Args:
            os_type: 操作系统类型 ("Windows11" 或 "Windows10")
            version: 版本号 (如 "25H2")
            build_major: 主构建号 (如 "26200")
            build_minor: 次构建号 (如 "6584")
            language: 语言代码 (如 "zh-cn")
            arch: 架构 (如 "x64")
            source_type: 来源类型 ("me" 或 "ce")
        
        Returns:
            标准格式的文件名 (不含路径)
        """
        # 确定操作系统前缀
        if "windows11" in os_type.lower() or "win11" in os_type.lower() or "w11" in os_type.lower():
            os_prefix = "win11"
        elif "windows10" in os_type.lower() or "win10" in os_type.lower() or "w10" in os_type.lower():
            os_prefix = "win10"
        else:
            raise ValueError(f"Unsupported OS type: {os_type}")
        
        # 验证 source_type
        if source_type not in ["me", "ce"]:
            raise ValueError(f"source_type must be 'me' or 'ce', current value: {source_type}")
        
        # 转换为小写并格式化
        version_lower = version.lower()
        language_lower = language.lower()
        arch_lower = arch.lower()
        
        # 生成文件名
        filename = f"{os_prefix}{source_type}_{version_lower}_{build_major}_{build_minor}_{language_lower}_{arch_lower}.iso"
        
        return filename
    
    def _filter_images(self, images: list[dict[str, Any]], filter_options: dict[str, str] | None = None) -> list[dict[str, Any]]:
        """过滤镜像列表"""
        if not filter_options:
            return images
        
        filtered = []
        for image in images:
            # 过滤操作系统类型
            if "os" in filter_options:
                # 优先使用 os_type 字段
                image_os = image.get("os_type", "")
                if not image_os:
                    # 如果没有 os_type，尝试从文件名解析
                    image_name = image.get("name", "")
                    if image_name:
                        try:
                            filename_info = self._parse_iso_filename(image_name)
                            image_os = filename_info.get("os_type", "")
                        except ValueError:
                            pass
                
                if image_os and filter_options["os"].lower() not in image_os.lower():
                    continue
            
            # 过滤架构
            if "arch" in filter_options:
                if image.get("architecture", "").lower() != filter_options["arch"].lower():
                    continue
            
            filtered.append(image)
        
        return filtered
    
    def start_test_mirror(self, source: str, test_url: str | None = None) -> str:
        """
        开始测试镜像站网络（异步）
        
        Args:
            source: 镜像源 ("microsoft" | "msdn")
            test_url: 可选的测试URL（对于MSDN，应该是magnet链接）
        
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        start_time = time.time()
        
        with self._test_lock:
            self.test_tasks[task_id] = {
                "source": source,
                "test_url": test_url,
                "status": "running",
                "start_time": start_time,
                "cancelled": False,
                "result": None,
                "error": None
            }
        
        # 在后台线程中执行测试
        def _test():
            try:
                with self._test_lock:
                    if self.test_tasks[task_id]["cancelled"]:
                        self.test_tasks[task_id]["status"] = "cancelled"
                        return
                
                # 设置超时时间（仅后端）
                timeout = 300  # 5分钟超时
                
                if source == "msdn":
                    # MSDN 镜像站：使用 BT/magnet 链接进行测速
                    magnet_link = test_url or "magnet:?xt=urn:btih:f869fc05b4a9c2c7b6d2dd4de9e56ad98b0b117d&dn=zh-cn_windows_11_consumer_editions_version_25h2_updated_nov_2025_x64_dvd_4ace2901.iso&xl=7863162880"
                    test_size = 10 * 1024 * 1024  # 10MB
                    logger.info(f"Starting MSDN mirror speed test (BT), magnet: {magnet_link[:50]}...")
                    
                    # 创建取消检查函数
                    def check_cancelled():
                        with self._test_lock:
                            return self.test_tasks.get(task_id, {}).get("cancelled", False)
                    
                    speed_result = self.downloader.test_bt_download_speed(
                        magnet_link, 
                        test_size=test_size,
                        timeout=timeout,
                        cancel_check=check_cancelled
                    )
                    
                    # 检查是否被取消（取消时会返回 speed=-1, latency=-1）
                    with self._test_lock:
                        if self.test_tasks[task_id]["cancelled"]:
                            self.test_tasks[task_id]["status"] = "cancelled"
                            return
                        # 如果返回的结果都是 -1，可能是被取消或失败，再次检查取消标志
                        if speed_result.get("speed") == -1 and speed_result.get("latency") == -1:
                            if self.test_tasks[task_id]["cancelled"]:
                                self.test_tasks[task_id]["status"] = "cancelled"
                                return
                    
                    if not isinstance(speed_result, dict):
                        speed_result = {}
                    
                    latency = speed_result.get("latency", -1)
                    download_speed = speed_result.get("speed", -1)
                    
                    # 再次检查取消标志（在设置完成状态之前）
                    with self._test_lock:
                        if self.test_tasks[task_id]["cancelled"]:
                            self.test_tasks[task_id]["status"] = "cancelled"
                            return
                        self.test_tasks[task_id]["status"] = "completed"
                        self.test_tasks[task_id]["result"] = {
                            "latency": latency if latency is not None and latency > 0 else -1,
                            "download_speed": download_speed if download_speed is not None and download_speed > 0 else -1
                        }
                        
                elif source == "microsoft":
                    # Microsoft 官方源：使用 HTTP 测试
                    url = test_url or "https://download.microsoft.com/download/0a8b07d9-a3bf-47b9-b71b-8e13354cec88/MediaCreationTool.exe"
                    logger.info(f"Starting Microsoft mirror speed test, URL: {url}")
                    
                    # 测试延迟
                    latency = self.downloader.test_latency(url, timeout=timeout)
                    logger.info(f"Latency test result: {latency} ms")
                    
                    with self._test_lock:
                        if self.test_tasks[task_id]["cancelled"]:
                            self.test_tasks[task_id]["status"] = "cancelled"
                            return
                    
                    # 测试下载速度（下载前10MB用于测速）
                    speed_result = self.downloader.test_download_speed(url, test_size=10 * 1024 * 1024, timeout=timeout)
                    logger.info(f"Speed test result: {speed_result}")
                    
                    with self._test_lock:
                        if self.test_tasks[task_id]["cancelled"]:
                            self.test_tasks[task_id]["status"] = "cancelled"
                            return
                    
                    if not isinstance(speed_result, dict):
                        speed_result = {}
                    
                    download_speed = speed_result.get("speed", -1)
                    if "latency" in speed_result and speed_result["latency"] > 0:
                        latency = speed_result["latency"]
                    
                    final_latency = latency if latency is not None and latency > 0 else -1
                    final_download_speed = download_speed if download_speed is not None and download_speed > 0 else -1
                    
                    logger.info(f"Final result: latency={final_latency}, download_speed={final_download_speed}")
                    
                    with self._test_lock:
                        self.test_tasks[task_id]["status"] = "completed"
                        self.test_tasks[task_id]["result"] = {
                            "latency": float(final_latency),
                            "download_speed": float(final_download_speed)
                        }
                else:
                    with self._test_lock:
                        self.test_tasks[task_id]["status"] = "completed"
                        self.test_tasks[task_id]["result"] = {"latency": -1, "download_speed": -1}
                        
            except Exception as e:
                logger.error(f"test_mirror failed: {e}")
                import traceback
                traceback.print_exc()
                with self._test_lock:
                    self.test_tasks[task_id]["status"] = "failed"
                    self.test_tasks[task_id]["error"] = str(e)
        
        thread = threading.Thread(target=_test, daemon=True)
        thread.start()
        
        return task_id
    
    def get_test_status(self, task_id: str) -> dict[str, Any]:
        """
        获取测试任务状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务状态信息
        """
        with self._test_lock:
            if task_id not in self.test_tasks:
                return {"status": "not_found"}
            
            task = self.test_tasks[task_id]
            elapsed = time.time() - task["start_time"]
            
            return {
                "status": task["status"],
                "elapsed": int(elapsed),
                "result": task.get("result"),
                "error": task.get("error")
            }
    
    def cancel_test(self, task_id: str) -> bool:
        """
        中止测试任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            是否成功中止
        """
        with self._test_lock:
            if task_id not in self.test_tasks:
                return False
            
            task = self.test_tasks[task_id]
            if task["status"] != "running":
                return False
            
            task["cancelled"] = True
            task["status"] = "cancelling"
            return True
    
    def test_mirror(self, source: str, test_url: str | None = None) -> dict[str, float]:
        """
        测试镜像站网络（同步版本，保持向后兼容）
        
        Args:
            source: 镜像源 ("microsoft" | "msdn")
            test_url: 可选的测试URL（对于MSDN，应该是magnet链接）
        
        Returns:
            {"latency": 延迟(ms), "download_speed": 速度(字节/秒)}
        """
        # 使用新的异步方法，但等待完成
        task_id = self.start_test_mirror(source, test_url)
        
        # 等待任务完成（最多等待5分钟）
        timeout = 300
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_test_status(task_id)
            if status["status"] in ["completed", "failed", "cancelled"]:
                if status["status"] == "completed":
                    return status.get("result", {"latency": -1, "download_speed": -1})
                elif status["status"] == "cancelled":
                    return {"latency": -1, "download_speed": -1}
                else:
                    return {"latency": -1, "download_speed": -1}
            time.sleep(0.5)
        
        # 超时
        self.cancel_test(task_id)
        return {"latency": -1, "download_speed": -1}
    
    def verify_iso(self, file_path: str, expected_sha256: str | None = None) -> dict[str, Any]:
        """校验ISO文件"""
        return self.downloader.verify_file(file_path, expected_sha256)
    
    def delete_iso(self, file_path: str) -> dict[str, bool | str]:
        """删除ISO文件"""
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                path.unlink()
                return {"success": True}
            else:
                return {"success": False, "error": "File does not exist"}
        except Exception as e:
            return {"success": False, "error": str(e)}
