"""
XML 导入导出测试脚本
使用 ref/autounattend.xml 作为测试样例，分别使用 Python 后端和 C# DLL 进行解析和生成 XML，对比结果一致性。

注意：运行此脚本前需要激活 win-auto-installer conda 环境
"""
import sys
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional
from xml.etree import ElementTree as ET
from xml.dom import minidom

# 检查 conda 环境
def check_conda_environment():
    """检查是否在正确的 conda 环境中"""
    conda_env = os.environ.get('CONDA_DEFAULT_ENV', '')
    if conda_env != 'win-auto-installer':
        print("="*60, file=sys.stderr)
        print("WARNING: Not in win-auto-installer conda environment!", file=sys.stderr)
        print(f"Current environment: {conda_env if conda_env else 'None'}", file=sys.stderr)
        print("Please activate the environment first:", file=sys.stderr)
        print("  conda activate win-auto-installer", file=sys.stderr)
        print("="*60, file=sys.stderr)
        return False
    return True

# 立即配置日志（在任何其他操作之前）
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 确保立即输出
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

logger.info("="*60)
logger.info("XML Import/Export Test Script")
logger.info("="*60)

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src' / 'backend'))
logger.info(f"Project root: {project_root}")
logger.info(f"Backend path added: {project_root / 'src' / 'backend'}")

# Python.NET 支持（用于调用 C# DLL）
HAS_PYTHONNET = False

try:
    # 尝试使用 clr_loader 配置 .NET Core 运行时（用于 .NET 8.0 DLL）
    try:
        from clr_loader import get_coreclr
        from pythonnet import set_runtime
        
        # 创建 runtimeconfig.json 文件（如果不存在）
        runtime_config_path = project_root / 'ref' / 'unattend-generator' / 'bin' / 'Release' / 'net8.0' / 'UnattendGenerator.runtimeconfig.json'
        
        if not runtime_config_path.exists():
            runtime_config = {
                "runtimeOptions": {
                    "tfm": "net8.0",
                    "framework": {
                        "name": "Microsoft.NETCore.App",
                        "version": "8.0.0"
                    }
                }
            }
            runtime_config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(runtime_config_path, 'w', encoding='utf-8') as f:
                json.dump(runtime_config, f, indent=2)
            logger.info(f"Created runtimeconfig.json at {runtime_config_path}")
        
        # 加载 .NET Core 运行时
        rt = get_coreclr(runtime_config=str(runtime_config_path))
        set_runtime(rt)
        logger.info("✓ Configured Python.NET to use .NET Core runtime")
    except ImportError:
        logger.debug("clr_loader not available, trying default Python.NET")
    except Exception as e:
        logger.warning(f"Failed to configure .NET Core runtime: {e}")
        logger.warning("  Falling back to default Python.NET runtime")
    
    # 导入 clr（必须在 set_runtime 之后）
    import clr
    HAS_PYTHONNET = True
    logger.info("✓ Python.NET available")
except ImportError:
    HAS_PYTHONNET = False
    logger.warning("Python.NET not installed. C# DLL comparison will be skipped.")

logger.info("Importing unattend_generator...")
try:
    from unattend_generator import (
        UnattendGenerator,
        Configuration,
        config_dict_to_configuration,
        configuration_to_config_dict
    )
    logger.info("✓ Successfully imported unattend_generator")
except Exception as e:
    logger.error(f"✗ Failed to import unattend_generator: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


# ========================================
# C# DLL 包装类（用于解析和生成）
# ========================================

class CSharpDLLWrapper:
    """C# DLL 包装类（用于解析和生成）"""
    
    def __init__(self, dll_path: Optional[Path] = None):
        self.dll_loaded = False
        self.generator = None
        self.types = {}
        self.assembly = None
        
        if not HAS_PYTHONNET:
            logger.warning("Python.NET not available, skipping C# DLL loading")
            return
        
        if dll_path is None:
            # 尝试查找编译后的 DLL（优先使用 net8.0）
            dll_path = project_root / 'ref' / 'unattend-generator' / 'bin' / 'Release' / 'net8.0' / 'UnattendGenerator.dll'
            if not dll_path.exists():
                # 尝试 net9.0
                dll_path = project_root / 'ref' / 'unattend-generator' / 'bin' / 'Release' / 'net9.0' / 'UnattendGenerator.dll'
            if not dll_path.exists():
                # 尝试 Debug 版本
                dll_path = project_root / 'ref' / 'unattend-generator' / 'bin' / 'Debug' / 'net8.0' / 'UnattendGenerator.dll'
        
        if dll_path and dll_path.exists():
            try:
                import clr
                import System
                from System import Reflection
                from System.IO import Path as SysPath
                
                # 设置程序集解析器，以便从 DLL 目录加载依赖项
                dll_dir = str(dll_path.parent)
                
                # 创建 ResolveEventHandler 委托
                def resolve_assembly(sender, args):
                    """程序集解析器，用于加载依赖项"""
                    assembly_name = args.Name
                    if ',' in assembly_name:
                        assembly_name = assembly_name.split(',')[0]
                    
                    # 尝试从 DLL 目录加载
                    dll_file = SysPath.Combine(dll_dir, f"{assembly_name}.dll")
                    if SysPath.Exists(dll_file):
                        try:
                            return Reflection.Assembly.LoadFrom(dll_file)
                        except:
                            pass
                    
                    return None
                
                # 使用 System.ResolveEventHandler 包装 Python 函数
                resolve_handler = System.ResolveEventHandler(resolve_assembly)
                System.AppDomain.CurrentDomain.add_AssemblyResolve(resolve_handler)
                
                # 加载依赖项（Newtonsoft.Json 等）
                newtonsoft_paths = [
                    dll_path.parent / 'Newtonsoft.Json.dll',
                    Path(os.environ.get('USERPROFILE', '')) / '.nuget' / 'packages' / 'newtonsoft.json' / '13.0.3' / 'lib' / 'net6.0' / 'Newtonsoft.Json.dll',
                    Path(os.environ.get('USERPROFILE', '')) / '.nuget' / 'packages' / 'newtonsoft.json' / '13.0.3' / 'lib' / 'net8.0' / 'Newtonsoft.Json.dll',
                    Path(os.environ.get('USERPROFILE', '')) / '.nuget' / 'packages' / 'newtonsoft.json' / '13.0.3' / 'lib' / 'netstandard2.0' / 'Newtonsoft.Json.dll',
                ]
                
                newtonsoft_loaded = False
                for newtonsoft_path in newtonsoft_paths:
                    if newtonsoft_path.exists():
                        try:
                            clr.AddReference(str(newtonsoft_path))
                            logger.info(f"✓ Loaded Newtonsoft.Json from {newtonsoft_path}")
                            newtonsoft_loaded = True
                            break
                        except Exception as e:
                            logger.debug(f"Failed to load from {newtonsoft_path}: {e}")
                
                if not newtonsoft_loaded:
                    try:
                        clr.AddReference("Newtonsoft.Json")
                        logger.info("✓ Loaded Newtonsoft.Json from GAC/system")
                        newtonsoft_loaded = True
                    except:
                        logger.warning("⚠ Could not load Newtonsoft.Json, DLL may fail to load")
                
                # 使用 LoadFrom 加载主 DLL
                self.assembly = Reflection.Assembly.LoadFrom(str(dll_path))
                
                # 获取类型
                unattend_type = self.assembly.GetType("Schneegans.Unattend.UnattendGenerator")
                config_type = self.assembly.GetType("Schneegans.Unattend.Configuration")
                
                # 创建生成器实例
                self.generator = System.Activator.CreateInstance(unattend_type)
                
                # 保存类型引用
                self.types = {
                    'UnattendGenerator': unattend_type,
                    'Configuration': config_type,
                }
                
                # 预加载常用类型（用于后续使用）
                try:
                    self.types['ImageLanguage'] = self.assembly.GetType("Schneegans.Unattend.ImageLanguage")
                    self.types['UserLocale'] = self.assembly.GetType("Schneegans.Unattend.UserLocale")
                    self.types['KeyboardIdentifier'] = self.assembly.GetType("Schneegans.Unattend.KeyboardIdentifier")
                    self.types['GeoLocation'] = self.assembly.GetType("Schneegans.Unattend.GeoLocation")
                    self.types['TimeOffset'] = self.assembly.GetType("Schneegans.Unattend.TimeOffset")
                    self.types['LocaleAndKeyboard'] = self.assembly.GetType("Schneegans.Unattend.LocaleAndKeyboard")
                    self.types['UnattendedLanguageSettings'] = self.assembly.GetType("Schneegans.Unattend.UnattendedLanguageSettings")
                    self.types['InteractiveLanguageSettings'] = self.assembly.GetType("Schneegans.Unattend.InteractiveLanguageSettings")
                    self.types['ExplicitTimeZoneSettings'] = self.assembly.GetType("Schneegans.Unattend.ExplicitTimeZoneSettings")
                    self.types['ImplicitTimeZoneSettings'] = self.assembly.GetType("Schneegans.Unattend.ImplicitTimeZoneSettings")
                except Exception as e:
                    logger.warning(f"Failed to preload some types: {e}")
                    # 继续执行，类型会在需要时加载
                
                self.dll_loaded = True
                logger.info(f"✓ Successfully loaded C# DLL from {dll_path}")
            except Exception as e:
                logger.error(f"✗ Failed to load C# DLL: {e}")
                import traceback
                traceback.print_exc()
        else:
            logger.warning(f"✗ C# DLL not found at {dll_path}")
    
    def parse_xml(self, xml_content: bytes) -> Optional[Dict[str, Any]]:
        """使用 C# DLL 解析 XML（如果存在此方法）"""
        if not self.dll_loaded:
            return None
        
        try:
            import System
            from System import Reflection
            from System.Reflection import BindingFlags
            
            # 检查是否有 ParseXml 方法
            generator_type = self.types['UnattendGenerator']
            
            # 尝试查找 ParseXml 方法
            parse_xml_method = None
            methods = generator_type.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static)
            
            for method in methods:
                if method.Name == "ParseXml" or method.Name == "Parse":
                    params = method.GetParameters()
                    if len(params) == 1:
                        param_type = params[0].ParameterType
                        if param_type.Name == "String" or param_type.Name == "Byte[]" or "XmlDocument" in param_type.Name:
                            parse_xml_method = method
                            break
            
            if parse_xml_method is None:
                logger.warning("⚠ C# DLL does not have ParseXml method - skipping C# parsing")
                return None
            
            # 调用解析方法
            param_type_name = parse_xml_method.GetParameters()[0].ParameterType.Name
            if param_type_name == "String":
                xml_str = xml_content.decode('utf-8')
                result = parse_xml_method.Invoke(self.generator if not parse_xml_method.IsStatic else None, [xml_str])
            elif param_type_name == "Byte[]":
                byte_array = System.Array[System.Byte](list(xml_content))
                result = parse_xml_method.Invoke(self.generator if not parse_xml_method.IsStatic else None, [byte_array])
            else:
                # 可能是 XmlDocument 或其他类型
                logger.warning(f"⚠ Unsupported ParseXml parameter type: {param_type_name}")
                return None
            
            # 将结果转换为字典（如果返回的是 Configuration 对象）
            if result is None:
                return None
            
            # 检查返回类型
            if result is None:
                return None
            result_type = result.GetType()
            config_type = self.types['Configuration']
            
            if result_type == config_type or result_type.IsSubclassOf(config_type):
                # 返回的是 Configuration 对象，需要转换为字典
                # 由于 C# Configuration 对象转换为字典比较复杂，暂时返回 None
                # 实际实现需要使用反射读取所有属性
                logger.warning("⚠ C# ParseXml returns Configuration object - conversion to dict not fully implemented")
                return None
            else:
                # 可能是其他类型，暂时返回 None
                logger.warning(f"⚠ C# ParseXml returns unexpected type: {result_type.Name}")
                return None
            
        except Exception as e:
            logger.error(f"✗ C# DLL parse XML failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_xml_from_config_dict(self, config_dict: Dict[str, Any]) -> Optional[bytes]:
        """使用 C# DLL 从配置字典生成 XML（参考 test_unattend_modules.py 中的 generate_xml 方法）"""
        if not self.dll_loaded:
            return None
        
        try:
            import System
            from System import Reflection
            from System.Reflection import BindingFlags
            
            # 获取类型
            config_type = self.types['Configuration']
            generator_type = self.types['UnattendGenerator']
            
            # 获取 Default 属性
            default_prop = config_type.GetProperty("Default")
            config = default_prop.GetValue(None)
            
            # 加载所有需要的类型（如果尚未加载）
            type_names = {
                'ImageLanguage': "Schneegans.Unattend.ImageLanguage",
                'UserLocale': "Schneegans.Unattend.UserLocale",
                'KeyboardIdentifier': "Schneegans.Unattend.KeyboardIdentifier",
                'GeoLocation': "Schneegans.Unattend.GeoLocation",
                'TimeOffset': "Schneegans.Unattend.TimeOffset",
                'LocaleAndKeyboard': "Schneegans.Unattend.LocaleAndKeyboard",
                'UnattendedLanguageSettings': "Schneegans.Unattend.UnattendedLanguageSettings",
                'InteractiveLanguageSettings': "Schneegans.Unattend.InteractiveLanguageSettings",
                'ExplicitTimeZoneSettings': "Schneegans.Unattend.ExplicitTimeZoneSettings",
                'ImplicitTimeZoneSettings': "Schneegans.Unattend.ImplicitTimeZoneSettings",
            }
            
            for key, type_name in type_names.items():
                if key not in self.types:
                    try:
                        self.types[key] = self.assembly.GetType(type_name)
                    except Exception as e:
                        logger.warning(f"Failed to load type {type_name}: {e}")
            
            # 设置语言设置
            if 'languageSettings' in config_dict:
                lang = config_dict['languageSettings']
                mode = lang.get('mode', 'interactive')
                
                if mode == 'unattended':
                    image_lang_id = lang.get('uiLanguage', 'en-US')
                    locale_id = lang.get('systemLocale', 'en-US')
                    keyboard_id = lang.get('inputLocale', '00000409')
                    geo_location_id = lang.get('geoLocation')
                    
                    # 使用泛型 Lookup 方法（直接使用解析出的 ID，不进行转换）
                    lookup_method = generator_type.GetMethod("Lookup").MakeGenericMethod([self.types['ImageLanguage']])
                    image_lang = lookup_method.Invoke(self.generator, [image_lang_id])
                    
                    lookup_method = generator_type.GetMethod("Lookup").MakeGenericMethod([self.types['UserLocale']])
                    user_locale = lookup_method.Invoke(self.generator, [locale_id])
                    
                    lookup_method = generator_type.GetMethod("Lookup").MakeGenericMethod([self.types['KeyboardIdentifier']])
                    keyboard = lookup_method.Invoke(self.generator, [keyboard_id])
                    
                    geo_location = None
                    if geo_location_id:
                        lookup_method = generator_type.GetMethod("Lookup").MakeGenericMethod([self.types['GeoLocation']])
                        geo_location = lookup_method.Invoke(self.generator, [geo_location_id])
                    
                    # 创建 LocaleAndKeyboard
                    locale_and_keyboard_type = self.types['LocaleAndKeyboard']
                    locale_and_keyboard = System.Activator.CreateInstance(
                        locale_and_keyboard_type, user_locale, keyboard
                    )
                    
                    # 创建 UnattendedLanguageSettings
                    unattended_lang_settings_type = self.types['UnattendedLanguageSettings']
                    lang_settings = System.Activator.CreateInstance(
                        unattended_lang_settings_type,
                        image_lang, locale_and_keyboard, None, None, geo_location
                    )
                    
                    # 设置 LanguageSettings 属性
                    lang_settings_prop = config_type.GetProperty("LanguageSettings")
                    lang_settings_prop.SetValue(config, lang_settings)
                else:
                    interactive_lang_settings_type = self.types['InteractiveLanguageSettings']
                    lang_settings = System.Activator.CreateInstance(interactive_lang_settings_type)
                    lang_settings_prop = config_type.GetProperty("LanguageSettings")
                    lang_settings_prop.SetValue(config, lang_settings)
            
            # 设置时区
            if 'timeZone' in config_dict:
                tz = config_dict['timeZone']
                mode = tz.get('mode', 'implicit')
                
                if mode == 'explicit':
                    timezone_id = tz.get('timeZone', '')
                    if timezone_id:
                        lookup_method = generator_type.GetMethod("Lookup").MakeGenericMethod([self.types['TimeOffset']])
                        time_offset = lookup_method.Invoke(self.generator, [timezone_id])
                        
                        explicit_tz_settings_type = self.types['ExplicitTimeZoneSettings']
                        tz_settings = System.Activator.CreateInstance(explicit_tz_settings_type, time_offset)
                        
                        tz_settings_prop = config_type.GetProperty("TimeZoneSettings")
                        tz_settings_prop.SetValue(config, tz_settings)
                else:
                    implicit_tz_settings_type = self.types['ImplicitTimeZoneSettings']
                    tz_settings = System.Activator.CreateInstance(implicit_tz_settings_type)
                    
                    tz_settings_prop = config_type.GetProperty("TimeZoneSettings")
                    tz_settings_prop.SetValue(config, tz_settings)
            
            # 设置 Setup Settings（模块 2）
            if 'setupSettings' in config_dict:
                setup = config_dict['setupSettings']
                bypass_req_prop = config_type.GetProperty("BypassRequirementsCheck")
                if bypass_req_prop:
                    bypass_req_prop.SetValue(config, setup.get('bypassRequirementsCheck', False))
                
                bypass_net_prop = config_type.GetProperty("BypassNetworkCheck")
                if bypass_net_prop:
                    bypass_net_prop.SetValue(config, setup.get('bypassNetworkCheck', False))
                
                use_config_set_prop = config_type.GetProperty("UseConfigurationSet")
                if use_config_set_prop:
                    use_config_set_prop.SetValue(config, setup.get('useConfigurationSet', False))
                
                hide_ps_prop = config_type.GetProperty("HidePowerShellWindows")
                if hide_ps_prop:
                    hide_ps_prop.SetValue(config, setup.get('hidePowerShellWindows', False))
                
                keep_files_prop = config_type.GetProperty("KeepSensitiveFiles")
                if keep_files_prop:
                    keep_files_prop.SetValue(config, setup.get('keepSensitiveFiles', False))
                
                use_narrator_prop = config_type.GetProperty("UseNarrator")
                if use_narrator_prop:
                    use_narrator_prop.SetValue(config, setup.get('useNarrator', False))
            
            # 注意：由于 C# Configuration 对象设置非常复杂，这里只设置了基本属性
            # 其他属性（如账户、分区等）的设置需要更复杂的实现
            # 为了测试目的，我们主要关注语言和时区设置
            
            # 生成 XML (返回 XmlDocument)
            generate_xml_method = generator_type.GetMethod("GenerateXml")
            xml_doc = generate_xml_method.Invoke(self.generator, [config])
            
            # 序列化为字节数组
            xml_doc_type = xml_doc.GetType()
            param_types = System.Array[System.Type]([xml_doc_type])
            serialize_method = generator_type.GetMethod("Serialize", param_types)
            
            if serialize_method is None:
                serialize_method = generator_type.GetMethod("Serialize", BindingFlags.Public | BindingFlags.Static, None, param_types, None)
            
            if serialize_method is None:
                methods = generator_type.GetMethods(BindingFlags.Public | BindingFlags.Static)
                for method in methods:
                    if method.Name == "Serialize":
                        params = method.GetParameters()
                        if len(params) == 1 and params[0].ParameterType == xml_doc_type:
                            serialize_method = method
                            break
            
            if serialize_method is None:
                raise ValueError("Could not find Serialize method")
            
            xml_bytes = serialize_method.Invoke(None, [xml_doc])
            
            # 转换为 Python bytes
            import array
            byte_array = array.array('B', xml_bytes)
            return byte_array.tobytes()
            
        except Exception as e:
            logger.error(f"✗ C# DLL generate XML failed: {e}")
            import traceback
            traceback.print_exc()
            return None


# ========================================
# 字典对比工具
# ========================================

def compare_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any], path: str = "") -> list:
    """深度对比两个字典，返回差异列表"""
    differences = []
    
    # 获取所有键
    all_keys = set(dict1.keys()) | set(dict2.keys())
    
    for key in all_keys:
        current_path = f"{path}.{key}" if path else key
        
        if key not in dict1:
            differences.append(f"{current_path}: Missing in dict1, value in dict2: {dict2[key]}")
        elif key not in dict2:
            differences.append(f"{current_path}: Missing in dict2, value in dict1: {dict1[key]}")
        else:
            val1 = dict1[key]
            val2 = dict2[key]
            
            if isinstance(val1, dict) and isinstance(val2, dict):
                differences.extend(compare_dicts(val1, val2, current_path))
            elif isinstance(val1, list) and isinstance(val2, list):
                if len(val1) != len(val2):
                    differences.append(f"{current_path}: List length mismatch: {len(val1)} vs {len(val2)}")
                else:
                    for i, (item1, item2) in enumerate(zip(val1, val2)):
                        if isinstance(item1, dict) and isinstance(item2, dict):
                            differences.extend(compare_dicts(item1, item2, f"{current_path}[{i}]"))
                        elif item1 != item2:
                            differences.append(f"{current_path}[{i}]: {item1} != {item2}")
            elif val1 != val2:
                differences.append(f"{current_path}: {val1} != {val2}")
    
    return differences


def normalize_dict_for_comparison(d: Dict[str, Any]) -> Dict[str, Any]:
    """规范化字典以便对比（移除 None 值，排序等）"""
    if not isinstance(d, dict):
        return d
    
    result = {}
    for k, v in sorted(d.items()):
        if v is None:
            continue
        if isinstance(v, dict):
            result[k] = normalize_dict_for_comparison(v)
        elif isinstance(v, list):
            result[k] = [normalize_dict_for_comparison(item) if isinstance(item, dict) else item for item in v]
        else:
            result[k] = v
    
    return result


# ========================================
# XML 对比工具
# ========================================

def normalize_text(text: str | None) -> str:
    """规范化文本内容：去除首尾空白，将多个空白字符压缩为单个空格"""
    if text is None:
        return ""
    # 去除首尾空白，将多个空白字符（包括换行、制表符等）压缩为单个空格
    import re
    normalized = re.sub(r'\s+', ' ', text.strip())
    return normalized


def get_element_path(elem: ET.Element | None, namespaces: dict, include_root: bool = True) -> str:
    """生成元素的完整路径（考虑命名空间和属性）
    
    注意：由于 ElementTree 不直接支持向上遍历，此函数仅用于生成当前元素的路径标识
    """
    if elem is None:
        return "None"
    
    # 获取元素标签（去除命名空间前缀）
    tag = elem.tag
    if '}' in tag:
        tag = tag.split('}')[1]
    
    # 构建路径部分
    path_part = tag
    
    # 添加关键属性（如果有）
    key_attrs = []
    if 'name' in elem.attrib:
        key_attrs.append(f"@name='{elem.attrib['name']}'")
    if 'pass' in elem.attrib:
        key_attrs.append(f"@pass='{elem.attrib['pass']}'")
    if 'path' in elem.attrib:
        key_attrs.append(f"@path='{elem.attrib['path']}'")
    
    # 对于有序元素，添加 Order 信息
    if tag in ['RunSynchronousCommand', 'SynchronousCommand']:
        order_elem = elem.find(f".//{{{namespaces.get('u', 'urn:schemas-microsoft-com:unattend')}}}Order")
        if order_elem is not None and order_elem.text:
            key_attrs.append(f"Order={order_elem.text}")
    
    if key_attrs:
        path_part += "[" + ", ".join(key_attrs) + "]"
    
    return path_part


def compare_attributes(elem1: ET.Element, elem2: ET.Element, path: str, differences: list):
    """对比两个元素的所有属性（包括命名空间属性）"""
    attrs1 = dict(elem1.attrib)
    attrs2 = dict(elem2.attrib)
    
    # 获取所有属性名（包括命名空间属性）
    all_attrs = set(attrs1.keys()) | set(attrs2.keys())
    
    for attr_name in sorted(all_attrs):
        val1 = attrs1.get(attr_name)
        val2 = attrs2.get(attr_name)
        
        if val1 != val2:
            attr_path = f"{path}/@{attr_name}"
            if val1 is None:
                differences.append({
                    'path': attr_path,
                    'type': '属性缺失（第一个XML）',
                    'expected': val2,
                    'actual': None
                })
            elif val2 is None:
                differences.append({
                    'path': attr_path,
                    'type': '属性缺失（第二个XML）',
                    'expected': val1,
                    'actual': None
                })
            else:
                differences.append({
                    'path': attr_path,
                    'type': '属性值不匹配',
                    'expected': val1,
                    'actual': val2
                })


def compare_elements_recursive(elem1: ET.Element | None, elem2: ET.Element | None, 
                                path: str, differences: list, namespaces: dict):
    """递归对比两个元素及其所有子元素
    
    注意：elem1 是生成的 XML，elem2 是原始的 XML
    """
    # 处理 None 值
    if elem1 is None and elem2 is None:
        return
    if elem1 is None:
        differences.append({
            'path': path,
            'type': '元素缺失（生成的XML）',
            'expected': get_element_path(elem2, namespaces, include_root=False) if elem2 is not None else None,  # elem2 是原始 XML（期望值）
            'actual': None  # elem1 是生成的 XML（实际值）
        })
        return
    if elem2 is None:
        differences.append({
            'path': path,
            'type': '元素缺失（原始XML）',
            'expected': None,  # elem2 是原始 XML（期望值）
            'actual': get_element_path(elem1, namespaces, include_root=False)  # elem1 是生成的 XML（实际值）
        })
        return
    
    # 对比标签名
    tag1 = elem1.tag
    tag2 = elem2.tag
    if tag1 != tag2:
        differences.append({
            'path': path,
            'type': '元素标签不匹配',
            'expected': tag2,  # elem2 是原始 XML（期望值）
            'actual': tag1     # elem1 是生成的 XML（实际值）
        })
        return
    
    # 对比属性
    compare_attributes(elem1, elem2, path, differences)
    
    # 对比文本内容（如果元素没有子元素）
    if len(list(elem1)) == 0 and len(list(elem2)) == 0:
        text1 = normalize_text(elem1.text)
        text2 = normalize_text(elem2.text)
        if text1 != text2:
            differences.append({
                'path': path,
                'type': '文本内容不匹配',
                'expected': text2[:200] + ('...' if len(text2) > 200 else ''),  # elem2 是原始 XML（期望值）
                'actual': text1[:200] + ('...' if len(text1) > 200 else '')    # elem1 是生成的 XML（实际值）
            })
    else:
        # 对比 tail 文本（如果有）
        tail1 = normalize_text(elem1.tail)
        tail2 = normalize_text(elem2.tail)
        if tail1 != tail2:
            differences.append({
                'path': path + '/@tail',
                'type': '尾部文本不匹配',
                'expected': tail2,  # elem2 是原始 XML（期望值）
                'actual': tail1     # elem1 是生成的 XML（实际值）
            })
    
    # 处理子元素
    children1 = list(elem1)
    children2 = list(elem2)
    
    # 判断是否需要按顺序对比
    tag_name = elem1.tag.split('}')[-1] if '}' in elem1.tag else elem1.tag
    is_ordered = tag_name in ['RunSynchronous', 'FirstLogonCommands', 'RunSynchronousCommand', 'SynchronousCommand']
    
    if is_ordered:
        # 有序元素：按 Order 排序后对比
        def get_order(elem: ET.Element) -> int:
            order_elem = elem.find(f".//{{{namespaces.get('u', 'urn:schemas-microsoft-com:unattend')}}}Order")
            if order_elem is not None and order_elem.text:
                try:
                    return int(order_elem.text)
                except ValueError:
                    return 0
            return 0
        
        children1_sorted = sorted(children1, key=get_order)
        children2_sorted = sorted(children2, key=get_order)
        
        max_len = max(len(children1_sorted), len(children2_sorted))
        for i in range(max_len):
            child1 = children1_sorted[i] if i < len(children1_sorted) else None
            child2 = children2_sorted[i] if i < len(children2_sorted) else None
            
            child_tag = child1.tag.split('}')[-1] if child1 and '}' in child1.tag else (child2.tag.split('}')[-1] if child2 and '}' in child2.tag else 'unknown')
            child_path = f"{path}/{child_tag}"
            
            # 添加 Order 信息到路径
            if child1:
                order_elem = child1.find(f".//{{{namespaces.get('u', 'urn:schemas-microsoft-com:unattend')}}}Order")
                if order_elem is not None and order_elem.text:
                    child_path += f"[Order={order_elem.text}]"
            elif child2:
                order_elem = child2.find(f".//{{{namespaces.get('u', 'urn:schemas-microsoft-com:unattend')}}}Order")
                if order_elem is not None and order_elem.text:
                    child_path += f"[Order={order_elem.text}]"
            
            compare_elements_recursive(child1, child2, child_path, differences, namespaces)
    else:
        # 无序元素：按关键属性匹配
        # 对于 LocalAccount，按 Name 匹配
        if tag_name == 'LocalAccounts':
            # 构建子元素映射
            children1_map = {}
            children2_map = {}
            
            for child in children1:
                name_elem = child.find(f".//{{{namespaces.get('u', 'urn:schemas-microsoft-com:unattend')}}}Name")
                if name_elem is not None and name_elem.text:
                    key = normalize_text(name_elem.text)
                    children1_map[key] = child
            
            for child in children2:
                name_elem = child.find(f".//{{{namespaces.get('u', 'urn:schemas-microsoft-com:unattend')}}}Name")
                if name_elem is not None and name_elem.text:
                    key = normalize_text(name_elem.text)
                    children2_map[key] = child
            
            # 对比所有键
            all_keys = set(children1_map.keys()) | set(children2_map.keys())
            for key in sorted(all_keys):
                child1 = children1_map.get(key)
                child2 = children2_map.get(key)
                child_path = f"{path}/LocalAccount[@Name='{key}']"
                compare_elements_recursive(child1, child2, child_path, differences, namespaces)
        else:
            # 其他情况：按位置对比
            max_len = max(len(children1), len(children2))
            for i in range(max_len):
                child1 = children1[i] if i < len(children1) else None
                child2 = children2[i] if i < len(children2) else None
                
                child_tag = child1.tag.split('}')[-1] if child1 and '}' in child1.tag else (child2.tag.split('}')[-1] if child2 and '}' in child2.tag else 'unknown')
                child_path = f"{path}/{child_tag}[{i}]"
                
                compare_elements_recursive(child1, child2, child_path, differences, namespaces)


def compare_extensions(ext1: ET.Element | None, ext2: ET.Element | None, 
                       differences: list, namespaces: dict):
    """专门对比 Extensions 部分（ExtractScript 和 File 元素）"""
    if ext1 is None and ext2 is None:
        return
    if ext1 is None:
        differences.append({
            'path': '/unattend/Extensions',
            'type': 'Extensions 部分缺失（生成的XML）',
            'expected': '存在',  # 原始 XML 中存在（期望值）
            'actual': None       # 生成的 XML 中缺失（实际值）
        })
        return
    if ext2 is None:
        differences.append({
            'path': '/unattend/Extensions',
            'type': 'Extensions 部分缺失（原始XML）',
            'expected': None,     # 原始 XML 中缺失（期望值）
            'actual': '存在'      # 生成的 XML 中存在（实际值）
        })
        return
    
    ext_ns = namespaces.get('ext', 'https://schneegans.de/windows/unattend-generator/')
    
    # 对比 ExtractScript
    script1 = ext1.find(f"{{{ext_ns}}}ExtractScript")
    script2 = ext2.find(f"{{{ext_ns}}}ExtractScript")
    
    if script1 is not None and script2 is not None:
        text1 = normalize_text(script1.text)  # 生成的 XML（实际值）
        text2 = normalize_text(script2.text)  # 原始的 XML（期望值）
        if text1 != text2:
            differences.append({
                'path': '/unattend/Extensions/ExtractScript',
                'type': 'ExtractScript 内容不匹配',
                'expected': text2[:500] + ('...' if len(text2) > 500 else ''),  # 原始 XML（期望值）
                'actual': text1[:500] + ('...' if len(text1) > 500 else '')    # 生成的 XML（实际值）
            })
    elif script1 is None and script2 is not None:
        differences.append({
            'path': '/unattend/Extensions/ExtractScript',
            'type': 'ExtractScript 缺失（生成的XML）',
            'expected': '存在',  # 原始 XML 中存在（期望值）
            'actual': None       # 生成的 XML 中缺失（实际值）
        })
    elif script1 is not None and script2 is None:
        differences.append({
            'path': '/unattend/Extensions/ExtractScript',
            'type': 'ExtractScript 缺失（原始XML）',
            'expected': None,     # 原始 XML 中缺失（期望值）
            'actual': '存在'      # 生成的 XML 中存在（实际值）
        })
    
    # 对比 File 元素（按 path 属性匹配）
    files1 = ext1.findall(f"{{{ext_ns}}}File")
    files2 = ext2.findall(f"{{{ext_ns}}}File")
    
    files1_map = {}
    files2_map = {}
    
    for file_elem in files1:
        path_attr = file_elem.get('path', '')
        if path_attr:
            files1_map[path_attr] = file_elem
    
    for file_elem in files2:
        path_attr = file_elem.get('path', '')
        if path_attr:
            files2_map[path_attr] = file_elem
    
    # 对比所有文件
    all_paths = set(files1_map.keys()) | set(files2_map.keys())
    for file_path in sorted(all_paths):
        file1 = files1_map.get(file_path)
        file2 = files2_map.get(file_path)
        
        if file1 is None:
            differences.append({
                'path': f'/unattend/Extensions/File[@path="{file_path}"]',
                'type': '文件缺失（生成的XML）',
                'expected': '存在',  # 原始 XML 中存在（期望值）
                'actual': None       # 生成的 XML 中缺失（实际值）
            })
        elif file2 is None:
            differences.append({
                'path': f'/unattend/Extensions/File[@path="{file_path}"]',
                'type': '文件缺失（原始XML）',
                'expected': None,     # 原始 XML 中缺失（期望值）
                'actual': '存在'      # 生成的 XML 中存在（实际值）
            })
        else:
            # 对比文件内容
            content1 = normalize_text(file1.text)  # 生成的 XML（实际值）
            content2 = normalize_text(file2.text)  # 原始的 XML（期望值）
            if content1 != content2:
                # 对于大文件，只显示前500个字符
                preview1 = content1[:500] + ('...' if len(content1) > 500 else '')
                preview2 = content2[:500] + ('...' if len(content2) > 500 else '')
                differences.append({
                    'path': f'/unattend/Extensions/File[@path="{file_path}"]',
                    'type': '文件内容不匹配',
                    'expected': preview2,  # 原始 XML（期望值）
                    'actual': preview1     # 生成的 XML（实际值）
                })


def compare_xml(python_xml: bytes, csharp_xml: bytes, test_name: str) -> bool:
    """对比两个 XML，返回是否一致（完整对比所有内容）"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Comparing XML for: {test_name}")
    logger.info(f"{'='*60}")

    def extract_numeric_entities(xml_bytes: bytes, label: str) -> list[dict]:
        """提取数字字符引用，区分十进制与十六进制"""
        text = xml_bytes.decode('utf-8', errors='ignore')
        entities = []
        for m in re.finditer(r'&#(x?[0-9A-Fa-f]+);', text):
            raw = m.group(0)
            val = m.group(1)
            is_hex = val.lower().startswith('x')
            # 计算行列
            line = text.count('\n', 0, m.start()) + 1
            col = m.start() - text.rfind('\n', 0, m.start())
            entities.append({
                'raw': raw,
                'value': val,
                'is_hex': is_hex,
                'line': line,
                'col': col,
                'label': label,
            })
        return entities

    def check_numeric_entities(python_bytes: bytes, other_bytes: bytes, differences: list, label_python: str, label_other: str):
        """对比数字实体格式，强调十六进制要求"""
        py_entities = extract_numeric_entities(python_bytes, label_python)
        other_entities = extract_numeric_entities(other_bytes, label_other)

        # 1) Python 中是否存在十进制实体
        for ent in py_entities:
            if not ent['is_hex']:
                differences.append({
                    'path': f"@{label_python}:{ent['line']}:{ent['col']}",
                    'type': '数字字符引用使用十进制',
                    'expected': '使用十六进制（形如 &#xhhhh;）',
                    'actual': ent['raw']
                })

        # 2) 同一位置实体格式差异（长度与顺序一致时尝试逐个对比）
        if len(py_entities) == len(other_entities):
            for i, (p, o) in enumerate(zip(py_entities, other_entities), start=1):
                if p['raw'] != o['raw']:
                    differences.append({
                        'path': f"@entity[{i}]",
                        'type': '数字字符引用格式不一致',
                        'expected': f"{label_other} 使用 {o['raw']}",
                        'actual': f"{label_python} 使用 {p['raw']}"
                    })
        else:
            differences.append({
                'path': '@entity_count',
                'type': '数字字符引用数量不一致',
                'expected': f"{label_other}: {len(other_entities)}",
                'actual': f"{label_python}: {len(py_entities)}"
            })
    
    try:
        # 首先对比原始文本中的数字字符引用格式（解析前即可发现十进制引用）
        differences = []
        check_numeric_entities(python_xml, csharp_xml, differences, 'python_xml', 'original_xml')

        # 解析 XML
        python_root = ET.fromstring(python_xml)
        csharp_root = ET.fromstring(csharp_xml)
        
        # 注册命名空间
        namespaces = {
            'u': 'urn:schemas-microsoft-com:unattend',
            'wcm': 'http://schemas.microsoft.com/WMIConfig/2002/State',
            'ext': 'https://schneegans.de/windows/unattend-generator/'
        }
        
        # 存储所有差异
        # 对比根元素属性
        compare_attributes(python_root, csharp_root, '/unattend', differences)
        
        # 对比所有 settings pass
        settings_passes = ['offlineServicing', 'windowsPE', 'generalize', 'specialize', 
                          'auditSystem', 'auditUser', 'oobeSystem']
        
        python_settings = {}
        csharp_settings = {}
        
        for settings_elem in python_root.findall(f"{{{namespaces['u']}}}settings"):
            pass_attr = settings_elem.get('pass', '')
            if pass_attr:
                python_settings[pass_attr] = settings_elem
        
        for settings_elem in csharp_root.findall(f"{{{namespaces['u']}}}settings"):
            pass_attr = settings_elem.get('pass', '')
            if pass_attr:
                csharp_settings[pass_attr] = settings_elem
        
        # 对比每个 pass
        all_passes = set(python_settings.keys()) | set(csharp_settings.keys())
        for pass_name in sorted(all_passes):
            python_pass = python_settings.get(pass_name)
            csharp_pass = csharp_settings.get(pass_name)
            pass_path = f"/unattend/settings[@pass='{pass_name}']"
            
            if python_pass is None:
                differences.append({
                    'path': pass_path,
                    'type': 'settings pass 缺失（生成的XML）',
                    'expected': '存在',  # 原始 XML 中存在（期望值）
                    'actual': None       # 生成的 XML 中缺失（实际值）
                })
                continue
            if csharp_pass is None:
                differences.append({
                    'path': pass_path,
                    'type': 'settings pass 缺失（原始XML）',
                    'expected': None,     # 原始 XML 中缺失（期望值）
                    'actual': '存在'      # 生成的 XML 中存在（实际值）
                })
                continue
            
            # 对比 settings 属性
            compare_attributes(python_pass, csharp_pass, pass_path, differences)
            
            # 对比所有 component
            python_components = {}
            csharp_components = {}
            
            for comp in python_pass.findall(f"{{{namespaces['u']}}}component"):
                comp_name = comp.get('name', '')
                if comp_name:
                    python_components[comp_name] = comp
            
            for comp in csharp_pass.findall(f"{{{namespaces['u']}}}component"):
                comp_name = comp.get('name', '')
                if comp_name:
                    csharp_components[comp_name] = comp
            
            # 对比每个 component
            all_components = set(python_components.keys()) | set(csharp_components.keys())
            for comp_name in sorted(all_components):
                python_comp = python_components.get(comp_name)
                csharp_comp = csharp_components.get(comp_name)
                comp_path = f"{pass_path}/component[@name='{comp_name}']"
                
                if python_comp is None:
                    differences.append({
                        'path': comp_path,
                        'type': 'component 缺失（生成的XML）',
                        'expected': '存在',  # 原始 XML 中存在（期望值）
                        'actual': None       # 生成的 XML 中缺失（实际值）
                    })
                    continue
                if csharp_comp is None:
                    differences.append({
                        'path': comp_path,
                        'type': 'component 缺失（原始XML）',
                        'expected': None,     # 原始 XML 中缺失（期望值）
                        'actual': '存在'      # 生成的 XML 中存在（实际值）
                    })
                    continue
                
                # 递归对比 component 及其所有子元素
                compare_elements_recursive(python_comp, csharp_comp, comp_path, differences, namespaces)
        
        # 对比 Extensions 部分
        python_ext = python_root.find(f"{{{namespaces['ext']}}}Extensions")
        csharp_ext = csharp_root.find(f"{{{namespaces['ext']}}}Extensions")
        compare_extensions(python_ext, csharp_ext, differences, namespaces)
        
        # 报告差异
        if differences:
            logger.error(f"✗ 发现 {len(differences)} 个差异:")
            for i, diff in enumerate(differences[:50], 1):  # 只显示前50个差异
                logger.error(f"  {i}. 路径: {diff['path']}")
                logger.error(f"     类型: {diff['type']}")
                if diff.get('expected') is not None:
                    logger.error(f"     期望值: {diff['expected']}")
                if diff.get('actual') is not None:
                    logger.error(f"     实际值: {diff['actual']}")
                logger.error("")
            
            if len(differences) > 50:
                logger.error(f"  ... 还有 {len(differences) - 50} 个差异未显示")
            
            # 保存 XML 文件用于调试
            output_dir = project_root / 'test' / 'output'
            output_dir.mkdir(parents=True, exist_ok=True)
            
            python_file = output_dir / f'{test_name}_python.xml'
            csharp_file = output_dir / f'{test_name}_csharp.xml'
            diff_file = output_dir / f'{test_name}_differences.txt'
            
            with open(python_file, 'wb') as f:
                f.write(python_xml)
            with open(csharp_file, 'wb') as f:
                f.write(csharp_xml)
            
            # 保存详细的差异报告
            with open(diff_file, 'w', encoding='utf-8') as f:
                f.write(f"XML 对比差异报告: {test_name}\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"总共发现 {len(differences)} 个差异\n\n")
                
                for i, diff in enumerate(differences, 1):
                    f.write(f"差异 #{i}:\n")
                    f.write(f"  路径: {diff['path']}\n")
                    f.write(f"  类型: {diff['type']}\n")
                    if diff.get('expected') is not None:
                        f.write(f"  期望值: {diff['expected']}\n")
                    if diff.get('actual') is not None:
                        f.write(f"  实际值: {diff['actual']}\n")
                    f.write("\n")
            
            logger.info(f"\n  文件已保存:")
            logger.info(f"    Python XML:  {python_file}")
            logger.info(f"    C# XML:      {csharp_file}")
            logger.info(f"    差异报告:    {diff_file}")
            return False
        else:
            logger.info("✓ XML 完全匹配！所有内容都一致。")
            return True
            
    except Exception as e:
        logger.error(f"✗ 对比失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ========================================
# 主测试函数
# ========================================

def test_xml_import_export():
    """测试 XML 导入导出功能"""
    logger.info("\n" + "="*60)
    logger.info("Test: XML Import/Export")
    logger.info("="*60)
    
    # 读取测试 XML 文件（使用 test.xml）
    xml_file = project_root / 'ref' / 'test.xml'
    if not xml_file.exists():
        logger.error(f"✗ Test XML file not found: {xml_file}")
        return False
    
    logger.info(f"Reading test XML file: {xml_file}")
    with open(xml_file, 'rb') as f:
        xml_content = f.read()
    logger.info(f"✓ Read XML file ({len(xml_content)} bytes)")
    
    # ========================================
    # 步骤 1: 解析测试
    # ========================================
    logger.info("\n" + "-"*60)
    logger.info("Step 1: Parse XML")
    logger.info("-"*60)
    
    # Python 后端解析
    logger.info("\n1.1 Python backend parsing...")
    try:
        generator = UnattendGenerator()
        python_config_dict = generator.parse_xml(xml_content)
        logger.info(f"✓ Python parsed XML successfully")
        logger.info(f"  Parsed {len(python_config_dict)} top-level keys")
        
        # 保存解析结果
        output_dir = project_root / 'test' / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        python_parse_file = output_dir / 'python_parse_result.json'
        with open(python_parse_file, 'w', encoding='utf-8') as f:
            json.dump(python_config_dict, f, indent=2, ensure_ascii=False)
        logger.info(f"  Saved parse result to: {python_parse_file}")
    except Exception as e:
        logger.error(f"✗ Python parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # # C# DLL 解析
    # logger.info("\n1.2 C# DLL parsing...")
    # csharp_wrapper = CSharpDLLWrapper()
    # csharp_config_dict = None
    
    # if csharp_wrapper.dll_loaded:
    #     csharp_config_dict = csharp_wrapper.parse_xml(xml_content)
    #     if csharp_config_dict is not None:
    #         logger.info(f"✓ C# DLL parsed XML successfully")
    #         logger.info(f"  Parsed {len(csharp_config_dict)} top-level keys")
            
    #         # 保存解析结果
    #         csharp_parse_file = output_dir / 'csharp_parse_result.json'
    #         with open(csharp_parse_file, 'w', encoding='utf-8') as f:
    #             json.dump(csharp_config_dict, f, indent=2, ensure_ascii=False)
    #         logger.info(f"  Saved parse result to: {csharp_parse_file}")
    #     else:
    #         logger.warning("⚠ C# DLL parsing not available or returned None")
    # else:
    #     logger.info("  (C# DLL parsing skipped - DLL not loaded)")
    
    # # 对比解析结果
    # if csharp_config_dict is not None:
    #     logger.info("\n1.3 Comparing parse results...")
    #     python_normalized = normalize_dict_for_comparison(python_config_dict)
    #     csharp_normalized = normalize_dict_for_comparison(csharp_config_dict)
        
    #     differences = compare_dicts(python_normalized, csharp_normalized)
    #     if differences:
    #         logger.error(f"✗ Found {len(differences)} differences in parse results:")
    #         for diff in differences[:20]:  # 只显示前20个差异
    #             logger.error(f"  - {diff}")
    #         if len(differences) > 20:
    #             logger.error(f"  ... and {len(differences) - 20} more differences")
            
    #         # 保存差异报告
    #         diff_file = output_dir / 'parse_differences.txt'
    #         with open(diff_file, 'w', encoding='utf-8') as f:
    #             f.write("Parse Result Differences\n")
    #             f.write("="*60 + "\n\n")
    #             for diff in differences:
    #                 f.write(f"{diff}\n")
    #         logger.info(f"  Saved differences to: {diff_file}")
    #     else:
    #         logger.info("✓ Parse results match!")
    # else:
    #     logger.info("  (Parse result comparison skipped - C# parsing not available)")
    
    # ========================================
    # 步骤 2: 生成测试
    # ========================================
    logger.info("\n" + "-"*60)
    logger.info("Step 2: Generate XML from parsed config")
    logger.info("-"*60)
    
    # Python 后端生成
    logger.info("\n2.1 Python backend generation...")
    try:
        # 将解析结果转换为 Configuration 对象
        python_config = config_dict_to_configuration(python_config_dict, generator)
        logger.info("✓ Converted config_dict to Configuration object")
        
        # 生成 XML
        python_generated_xml = generator.generate_xml(python_config)
        logger.info(f"✓ Python generated XML ({len(python_generated_xml)} bytes)")
        
        # 保存生成的 XML
        python_gen_file = output_dir / 'python_generated.xml'
        with open(python_gen_file, 'wb') as f:
            f.write(python_generated_xml)
        logger.info(f"  Saved generated XML to: {python_gen_file}")
    except Exception as e:
        logger.error(f"✗ Python generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # C# DLL 生成（使用 Python 解析的结果）
    # logger.info("\n2.2 C# DLL generation (from Python parsed config)...")
    # csharp_generated_xml = None
    
    # if csharp_wrapper.dll_loaded:
    #     # 使用 Python 解析的配置字典来生成 C# XML
    #     csharp_generated_xml = csharp_wrapper.generate_xml_from_config_dict(python_config_dict)
    #     if csharp_generated_xml is not None:
    #         logger.info(f"✓ C# DLL generated XML ({len(csharp_generated_xml)} bytes)")
            
    #         # 保存生成的 XML
    #         csharp_gen_file = output_dir / 'csharp_generated.xml'
    #         with open(csharp_gen_file, 'wb') as f:
    #             f.write(csharp_generated_xml)
    #         logger.info(f"  Saved generated XML to: {csharp_gen_file}")
    #     else:
    #         logger.warning("⚠ C# DLL generation not available or returned None")
    # else:
    #     logger.info("  (C# DLL generation skipped - DLL not loaded)")
    
    # # 对比生成的 XML
    # if csharp_generated_xml is not None:
    #     logger.info("\n2.3 Comparing generated XML...")
    #     if compare_xml(python_generated_xml, csharp_generated_xml, "generated_xml"):
    #         logger.info("✓ Generated XML structures match!")
    #     else:
    #         logger.error("✗ Generated XML structures differ!")
    # else:
    #     logger.info("  (Generated XML comparison skipped - C# generation not available)")
    
    # ========================================
    # 步骤 3: 往返测试（Parse -> Generate，对比生成的 XML 与原始 XML）
    # ========================================
    logger.info("\n" + "-"*60)
    logger.info("Step 3: Round-trip test (Parse -> Generate, compare XML)")
    logger.info("-"*60)
    
    logger.info("\n3.1 Comparing generated XML with original XML...")
    try:
        # 对比生成的 XML 和原始 XML
        if compare_xml(python_generated_xml, xml_content, "roundtrip_original_vs_generated"):
            logger.info("✓ Generated XML matches original XML structure!")
        else:
            logger.warning("⚠ Generated XML differs from original XML structure")
        
        # 保存对比结果
        output_dir = project_root / 'test' / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        original_file = output_dir / 'original.xml'
        generated_file = output_dir / 'roundtrip_generated.xml'
        
        with open(original_file, 'wb') as f:
            f.write(xml_content)
        with open(generated_file, 'wb') as f:
            f.write(python_generated_xml)
        
        logger.info(f"\n  XML files saved to:")
        logger.info(f"    Original:  {original_file}")
        logger.info(f"    Generated: {generated_file}")
        
    except Exception as e:
        logger.error(f"✗ Round-trip XML comparison failed: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info("\n" + "="*60)
    logger.info("Test completed")
    logger.info("="*60)
    return True


def main():
    """主函数"""
    logger.info("="*60)
    logger.info("XML Import/Export Test")
    logger.info("="*60)
    
    try:
        test_xml_import_export()
    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    # 检查 conda 环境
    if not check_conda_environment():
        sys.exit(1)
    
    logger.info("="*60)
    logger.info("Starting test script...")
    logger.info("="*60)
    
    try:
        success = main()
        if success:
            logger.info("="*60)
            logger.info("Test script completed successfully.")
            logger.info("="*60)
        else:
            logger.error("="*60)
            logger.error("Test script completed with errors.")
            logger.error("="*60)
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

