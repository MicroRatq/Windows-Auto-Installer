"""
XML 导入导出测试脚本
使用 ref/autounattend.xml 作为测试样例，分别使用 Python 后端和 C# DLL 进行解析和生成 XML，对比结果一致性。

注意：运行此脚本前需要激活 win-auto-installer conda 环境
"""
import sys
import json
import logging
import os
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

def compare_xml(python_xml: bytes, csharp_xml: bytes, test_name: str) -> bool:
    """对比两个 XML，返回是否一致"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Comparing XML for: {test_name}")
    logger.info(f"{'='*60}")
    
    try:
        # 解析 XML
        python_root = ET.fromstring(python_xml)
        csharp_root = ET.fromstring(csharp_xml)
        
        # 对比关键节点
        ns_uri = 'urn:schemas-microsoft-com:unattend'
        differences = []
        
        # 对比语言设置组件
        python_pe = python_root.find(f".//{{{ns_uri}}}component[@name='Microsoft-Windows-International-Core-WinPE']")
        csharp_pe = csharp_root.find(f".//{{{ns_uri}}}component[@name='Microsoft-Windows-International-Core-WinPE']")
        
        if (python_pe is None) != (csharp_pe is None):
            differences.append("WinPE component existence mismatch")
        elif python_pe is not None:
            python_ui = python_pe.find(f"{{{ns_uri}}}UILanguage")
            csharp_ui = csharp_pe.find(f"{{{ns_uri}}}UILanguage")
            if (python_ui is None) != (csharp_ui is None):
                differences.append("UILanguage in WinPE mismatch")
            elif python_ui is not None and python_ui.text != csharp_ui.text:
                differences.append(f"UILanguage in WinPE: Python='{python_ui.text}', C#='{csharp_ui.text}'")
        
        python_oobe = python_root.find(f".//{{{ns_uri}}}component[@name='Microsoft-Windows-International-Core']")
        csharp_oobe = csharp_root.find(f".//{{{ns_uri}}}component[@name='Microsoft-Windows-International-Core']")
        
        if (python_oobe is None) != (csharp_oobe is None):
            differences.append("OOBE component existence mismatch")
        elif python_oobe is not None:
            for elem_name in ['InputLocale', 'SystemLocale', 'UserLocale', 'UILanguage']:
                python_elem = python_oobe.find(f"{{{ns_uri}}}{elem_name}")
                csharp_elem = csharp_oobe.find(f"{{{ns_uri}}}{elem_name}")
                if (python_elem is None) != (csharp_elem is None):
                    differences.append(f"{elem_name} existence mismatch")
                elif python_elem is not None and python_elem.text != csharp_elem.text:
                    differences.append(f"{elem_name}: Python='{python_elem.text}', C#='{csharp_elem.text}'")
        
        # 对比时区设置
        python_tz = python_root.find(f".//{{{ns_uri}}}component[@name='Microsoft-Windows-Shell-Setup']/{{{ns_uri}}}TimeZone")
        csharp_tz = csharp_root.find(f".//{{{ns_uri}}}component[@name='Microsoft-Windows-Shell-Setup']/{{{ns_uri}}}TimeZone")
        
        if (python_tz is None) != (csharp_tz is None):
            differences.append("TimeZone existence mismatch")
        elif python_tz is not None and python_tz.text != csharp_tz.text:
            differences.append(f"TimeZone: Python='{python_tz.text}', C#='{csharp_tz.text}'")
        
        if differences:
            logger.error("✗ Differences found:")
            for diff in differences:
                logger.error(f"  - {diff}")
            
            # 保存 XML 文件用于调试
            output_dir = project_root / 'test' / 'output'
            output_dir.mkdir(parents=True, exist_ok=True)
            
            python_file = output_dir / f'{test_name}_python.xml'
            csharp_file = output_dir / f'{test_name}_csharp.xml'
            
            with open(python_file, 'wb') as f:
                f.write(python_xml)
            with open(csharp_file, 'wb') as f:
                f.write(csharp_xml)
            
            logger.info(f"\n  XML files saved to:")
            logger.info(f"    Python: {python_file}")
            logger.info(f"    C#:     {csharp_file}")
            return False
        else:
            logger.info("✓ XML structures match!")
            return True
            
    except Exception as e:
        logger.error(f"✗ Comparison failed: {e}")
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
    
    # 读取测试 XML 文件
    xml_file = project_root / 'ref' / 'autounattend.xml'
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
    
    # C# DLL 解析
    logger.info("\n1.2 C# DLL parsing...")
    csharp_wrapper = CSharpDLLWrapper()
    csharp_config_dict = None
    
    if csharp_wrapper.dll_loaded:
        csharp_config_dict = csharp_wrapper.parse_xml(xml_content)
        if csharp_config_dict is not None:
            logger.info(f"✓ C# DLL parsed XML successfully")
            logger.info(f"  Parsed {len(csharp_config_dict)} top-level keys")
            
            # 保存解析结果
            csharp_parse_file = output_dir / 'csharp_parse_result.json'
            with open(csharp_parse_file, 'w', encoding='utf-8') as f:
                json.dump(csharp_config_dict, f, indent=2, ensure_ascii=False)
            logger.info(f"  Saved parse result to: {csharp_parse_file}")
        else:
            logger.warning("⚠ C# DLL parsing not available or returned None")
    else:
        logger.info("  (C# DLL parsing skipped - DLL not loaded)")
    
    # 对比解析结果
    if csharp_config_dict is not None:
        logger.info("\n1.3 Comparing parse results...")
        python_normalized = normalize_dict_for_comparison(python_config_dict)
        csharp_normalized = normalize_dict_for_comparison(csharp_config_dict)
        
        differences = compare_dicts(python_normalized, csharp_normalized)
        if differences:
            logger.error(f"✗ Found {len(differences)} differences in parse results:")
            for diff in differences[:20]:  # 只显示前20个差异
                logger.error(f"  - {diff}")
            if len(differences) > 20:
                logger.error(f"  ... and {len(differences) - 20} more differences")
            
            # 保存差异报告
            diff_file = output_dir / 'parse_differences.txt'
            with open(diff_file, 'w', encoding='utf-8') as f:
                f.write("Parse Result Differences\n")
                f.write("="*60 + "\n\n")
                for diff in differences:
                    f.write(f"{diff}\n")
            logger.info(f"  Saved differences to: {diff_file}")
        else:
            logger.info("✓ Parse results match!")
    else:
        logger.info("  (Parse result comparison skipped - C# parsing not available)")
    
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
    logger.info("\n2.2 C# DLL generation (from Python parsed config)...")
    csharp_generated_xml = None
    
    if csharp_wrapper.dll_loaded:
        # 使用 Python 解析的配置字典来生成 C# XML
        csharp_generated_xml = csharp_wrapper.generate_xml_from_config_dict(python_config_dict)
        if csharp_generated_xml is not None:
            logger.info(f"✓ C# DLL generated XML ({len(csharp_generated_xml)} bytes)")
            
            # 保存生成的 XML
            csharp_gen_file = output_dir / 'csharp_generated.xml'
            with open(csharp_gen_file, 'wb') as f:
                f.write(csharp_generated_xml)
            logger.info(f"  Saved generated XML to: {csharp_gen_file}")
        else:
            logger.warning("⚠ C# DLL generation not available or returned None")
    else:
        logger.info("  (C# DLL generation skipped - DLL not loaded)")
    
    # 对比生成的 XML
    if csharp_generated_xml is not None:
        logger.info("\n2.3 Comparing generated XML...")
        if compare_xml(python_generated_xml, csharp_generated_xml, "generated_xml"):
            logger.info("✓ Generated XML structures match!")
        else:
            logger.error("✗ Generated XML structures differ!")
    else:
        logger.info("  (Generated XML comparison skipped - C# generation not available)")
    
    # ========================================
    # 步骤 3: 往返测试（Parse -> Generate -> Parse）
    # ========================================
    logger.info("\n" + "-"*60)
    logger.info("Step 3: Round-trip test (Parse -> Generate -> Parse)")
    logger.info("-"*60)
    
    logger.info("\n3.1 Re-parsing Python generated XML...")
    try:
        python_roundtrip_dict = generator.parse_xml(python_generated_xml)
        logger.info(f"✓ Re-parsed Python generated XML successfully")
        
        # 对比原始解析结果和往返解析结果
        python_original_normalized = normalize_dict_for_comparison(python_config_dict)
        python_roundtrip_normalized = normalize_dict_for_comparison(python_roundtrip_dict)
        
        roundtrip_differences = compare_dicts(python_original_normalized, python_roundtrip_normalized)
        if roundtrip_differences:
            logger.warning(f"⚠ Found {len(roundtrip_differences)} differences in round-trip:")
            for diff in roundtrip_differences[:10]:  # 只显示前10个差异
                logger.warning(f"  - {diff}")
            if len(roundtrip_differences) > 10:
                logger.warning(f"  ... and {len(roundtrip_differences) - 10} more differences")
        else:
            logger.info("✓ Round-trip test passed! (Parse -> Generate -> Parse)")
    except Exception as e:
        logger.error(f"✗ Round-trip test failed: {e}")
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

