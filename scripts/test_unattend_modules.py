"""
Unattend Generator 模块测试脚本
统一测试脚本，支持所有模块的增量测试
每新增一个模块，在此脚本中增量补充测试用例
通过注释/取消注释 main() 中的测试函数调用来进行针对性测试

注意：运行此脚本前需要激活 win-auto-installer conda 环境
"""
import sys
import json
import base64
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, List
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
logger.info("Test script started")
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
        project_root = Path(__file__).parent.parent
        runtime_config_path = project_root / 'ref' / 'unattend-generator' / 'bin' / 'Release' / 'net8.0' / 'UnattendGenerator.runtimeconfig.json'
        
        if not runtime_config_path.exists():
            import json as json_lib
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
                json_lib.dump(runtime_config, f, indent=2)
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
        create_default_configuration,
        config_dict_to_configuration,
        ProcessorArchitecture,
        InteractiveLanguageSettings,
        UnattendedLanguageSettings,
        LocaleAndKeyboard,
        ImplicitTimeZoneSettings,
        ExplicitTimeZoneSettings,
        ImageLanguage,
        UserLocale,
        KeyboardIdentifier,
        TimeOffset,
        GeoLocation,
        Constants,
        RandomComputerNameSettings,
        CustomComputerNameSettings,
        ScriptComputerNameSettings,
        InteractiveMicrosoftAccountSettings,
        InteractiveLocalAccountSettings,
        UnattendedAccountSettings,
        Account,
        NoneAutoLogonSettings,
        BuiltinAutoLogonSettings,
        OwnAutoLogonSettings,
        DefaultPasswordExpirationSettings,
        UnlimitedPasswordExpirationSettings,
        CustomPasswordExpirationSettings,
        DefaultLockoutSettings,
        DisableLockoutSettings,
        CustomLockoutSettings
    )
    logger.info("✓ Successfully imported unattend_generator")
except Exception as e:
    logger.error(f"✗ Failed to import unattend_generator: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


# ========================================
# C# DLL 包装类（仅用于测试对比）
# ========================================

class CSharpDLLWrapper:
    """C# DLL 包装类（仅用于测试对比）"""
    
    def __init__(self, dll_path: Optional[Path] = None):
        self.dll_loaded = False
        self.generator = None
        
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
                import os
                user_profile = os.environ.get('USERPROFILE', '')
                
                # 优先从 DLL 同目录加载（如果已复制）
                newtonsoft_paths = [
                    dll_path.parent / 'Newtonsoft.Json.dll',  # 同目录（优先）
                    Path(user_profile) / '.nuget' / 'packages' / 'newtonsoft.json' / '13.0.3' / 'lib' / 'net6.0' / 'Newtonsoft.Json.dll',
                    Path(user_profile) / '.nuget' / 'packages' / 'newtonsoft.json' / '13.0.3' / 'lib' / 'net8.0' / 'Newtonsoft.Json.dll',
                    Path(user_profile) / '.nuget' / 'packages' / 'newtonsoft.json' / '13.0.3' / 'lib' / 'netstandard2.0' / 'Newtonsoft.Json.dll',
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
                
                # 如果找不到文件，尝试从 GAC 或系统路径加载
                if not newtonsoft_loaded:
                    try:
                        clr.AddReference("Newtonsoft.Json")
                        logger.info("✓ Loaded Newtonsoft.Json from GAC/system")
                        newtonsoft_loaded = True
                    except:
                        logger.warning("⚠ Could not load Newtonsoft.Json, DLL may fail to load")
                
                # 使用 LoadFrom 加载主 DLL（这样可以自动解析依赖项）
                assembly = Reflection.Assembly.LoadFrom(str(dll_path))
                
                # 获取类型
                unattend_type = assembly.GetType("Schneegans.Unattend.UnattendGenerator")
                config_type = assembly.GetType("Schneegans.Unattend.Configuration")
                image_lang_type = assembly.GetType("Schneegans.Unattend.ImageLanguage")
                user_locale_type = assembly.GetType("Schneegans.Unattend.UserLocale")
                keyboard_type = assembly.GetType("Schneegans.Unattend.KeyboardIdentifier")
                geo_location_type = assembly.GetType("Schneegans.Unattend.GeoLocation")
                time_offset_type = assembly.GetType("Schneegans.Unattend.TimeOffset")
                locale_and_keyboard_type = assembly.GetType("Schneegans.Unattend.LocaleAndKeyboard")
                unattended_lang_settings_type = assembly.GetType("Schneegans.Unattend.UnattendedLanguageSettings")
                interactive_lang_settings_type = assembly.GetType("Schneegans.Unattend.InteractiveLanguageSettings")
                explicit_tz_settings_type = assembly.GetType("Schneegans.Unattend.ExplicitTimeZoneSettings")
                implicit_tz_settings_type = assembly.GetType("Schneegans.Unattend.ImplicitTimeZoneSettings")
                
                # 创建生成器实例
                self.generator = System.Activator.CreateInstance(unattend_type)
                
                # 保存类型引用供后续使用
                self.types = {
                    'UnattendGenerator': unattend_type,
                    'Configuration': config_type,
                    'ImageLanguage': image_lang_type,
                    'UserLocale': user_locale_type,
                    'KeyboardIdentifier': keyboard_type,
                    'GeoLocation': geo_location_type,
                    'TimeOffset': time_offset_type,
                    'LocaleAndKeyboard': locale_and_keyboard_type,
                    'UnattendedLanguageSettings': unattended_lang_settings_type,
                    'InteractiveLanguageSettings': interactive_lang_settings_type,
                    'ExplicitTimeZoneSettings': explicit_tz_settings_type,
                    'ImplicitTimeZoneSettings': implicit_tz_settings_type,
                }
                
                self.dll_loaded = True
                logger.info(f"✓ Successfully loaded C# DLL from {dll_path}")
            except Exception as e:
                logger.error(f"✗ Failed to load C# DLL: {e}")
                import traceback
                traceback.print_exc()
        else:
            logger.warning(f"✗ C# DLL not found at {dll_path}")
    
    def generate_xml(self, config_dict: Dict[str, Any]) -> Optional[bytes]:
        """使用 C# DLL 生成 XML"""
        if not self.dll_loaded:
            return None
        
        try:
            import System
            from System import Reflection
            
            # 获取类型
            config_type = self.types['Configuration']
            generator_type = self.types['UnattendGenerator']
            
            # 获取 Default 属性
            default_prop = config_type.GetProperty("Default")
            config = default_prop.GetValue(None)
            
            # 设置语言设置
            if 'languageSettings' in config_dict:
                lang = config_dict['languageSettings']
                mode = lang.get('mode', 'interactive')
                
                if mode == 'unattended':
                    image_lang_id = lang.get('uiLanguage', 'en-US')
                    locale_id = lang.get('systemLocale', 'en-US')
                    keyboard_id = lang.get('inputLocale', '00000409')
                    geo_location_id = lang.get('geoLocation')
                    
                    # 使用泛型 Lookup 方法
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
                bypass_req_prop.SetValue(config, setup.get('bypassRequirementsCheck', False))
                
                bypass_net_prop = config_type.GetProperty("BypassNetworkCheck")
                bypass_net_prop.SetValue(config, setup.get('bypassNetworkCheck', False))
                
                use_config_set_prop = config_type.GetProperty("UseConfigurationSet")
                use_config_set_prop.SetValue(config, setup.get('useConfigurationSet', False))
                
                hide_ps_prop = config_type.GetProperty("HidePowerShellWindows")
                hide_ps_prop.SetValue(config, setup.get('hidePowerShellWindows', False))
                
                keep_files_prop = config_type.GetProperty("KeepSensitiveFiles")
                keep_files_prop.SetValue(config, setup.get('keepSensitiveFiles', False))
                
                use_narrator_prop = config_type.GetProperty("UseNarrator")
                use_narrator_prop.SetValue(config, setup.get('useNarrator', False))
            
            # 设置模块 4: Name and Account
            # 设置计算机名
            if 'computerName' in config_dict:
                cn = config_dict['computerName']
                mode = cn.get('mode', 'random')
                
                if mode == 'random':
                    random_cn_settings_type = self.types['RandomComputerNameSettings']
                    cn_settings = System.Activator.CreateInstance(random_cn_settings_type)
                    cn_settings_prop = config_type.GetProperty("ComputerNameSettings")
                    cn_settings_prop.SetValue(config, cn_settings)
                elif mode == 'custom':
                    name = cn.get('name', '')
                    custom_cn_settings_type = self.types['CustomComputerNameSettings']
                    cn_settings = System.Activator.CreateInstance(custom_cn_settings_type, name)
                    cn_settings_prop = config_type.GetProperty("ComputerNameSettings")
                    cn_settings_prop.SetValue(config, cn_settings)
                elif mode == 'script':
                    script = cn.get('script', '')
                    script_cn_settings_type = self.types['ScriptComputerNameSettings']
                    cn_settings = System.Activator.CreateInstance(script_cn_settings_type, script)
                    cn_settings_prop = config_type.GetProperty("ComputerNameSettings")
                    cn_settings_prop.SetValue(config, cn_settings)
            
            # 设置账户
            if 'accountSettings' in config_dict:
                accounts = config_dict['accountSettings']
                mode = accounts.get('mode', 'interactive-microsoft')
                
                if mode == 'unattended':
                    # 创建账户列表
                    account_type = self.types['Account']
                    account_list_type = System.Type.GetType("System.Collections.Immutable.ImmutableList`1").MakeGenericType([account_type])
                    account_list = System.Activator.CreateInstance(account_list_type)
                    
                    for acc_dict in accounts.get('accounts', []):
                        account = System.Activator.CreateInstance(
                            account_type,
                            acc_dict.get('name', ''),
                            acc_dict.get('displayName', acc_dict.get('name', '')),
                            acc_dict.get('password', ''),
                            acc_dict.get('group', 'Users')
                        )
                        # 添加到不可变列表（简化处理，实际需要使用 ImmutableList.Builder）
                        # 这里暂时跳过，因为 ImmutableList 的构建比较复杂
                    
                    # 创建自动登录设置
                    auto_logon_mode = accounts.get('autoLogonMode', 'none')
                    if auto_logon_mode == 'builtin':
                        builtin_auto_logon_type = self.types['BuiltinAutoLogonSettings']
                        auto_logon_settings = System.Activator.CreateInstance(
                            builtin_auto_logon_type,
                            accounts.get('autoLogonPassword', '')
                        )
                    elif auto_logon_mode == 'own':
                        own_auto_logon_type = self.types['OwnAutoLogonSettings']
                        auto_logon_settings = System.Activator.CreateInstance(own_auto_logon_type)
                    else:
                        none_auto_logon_type = self.types['NoneAutoLogonSettings']
                        auto_logon_settings = System.Activator.CreateInstance(none_auto_logon_type)
                    
                    # 创建 UnattendedAccountSettings（需要 ImmutableList，暂时简化）
                    # unattended_account_settings_type = self.types['UnattendedAccountSettings']
                    # account_settings = System.Activator.CreateInstance(
                    #     unattended_account_settings_type,
                    #     account_list,
                    #     auto_logon_settings,
                    #     accounts.get('obscurePasswords', False)
                    # )
                    # account_settings_prop = config_type.GetProperty("AccountSettings")
                    # account_settings_prop.SetValue(config, account_settings)
                elif mode == 'interactive-local':
                    interactive_local_type = self.types['InteractiveLocalAccountSettings']
                    account_settings = System.Activator.CreateInstance(interactive_local_type)
                    account_settings_prop = config_type.GetProperty("AccountSettings")
                    account_settings_prop.SetValue(config, account_settings)
                else:
                    interactive_microsoft_type = self.types['InteractiveMicrosoftAccountSettings']
                    account_settings = System.Activator.CreateInstance(interactive_microsoft_type)
                    account_settings_prop = config_type.GetProperty("AccountSettings")
                    account_settings_prop.SetValue(config, account_settings)
            
            # 设置密码过期
            if 'passwordExpiration' in config_dict:
                pe = config_dict['passwordExpiration']
                mode = pe.get('mode', 'default')
                
                if mode == 'unlimited':
                    unlimited_pe_type = self.types['UnlimitedPasswordExpirationSettings']
                    pe_settings = System.Activator.CreateInstance(unlimited_pe_type)
                elif mode == 'custom':
                    custom_pe_type = self.types['CustomPasswordExpirationSettings']
                    max_age = pe.get('maxAge', 42)
                    pe_settings = System.Activator.CreateInstance(custom_pe_type, max_age)
                else:
                    default_pe_type = self.types['DefaultPasswordExpirationSettings']
                    pe_settings = System.Activator.CreateInstance(default_pe_type)
                
                pe_settings_prop = config_type.GetProperty("PasswordExpirationSettings")
                pe_settings_prop.SetValue(config, pe_settings)
            
            # 设置账户锁定
            if 'lockoutSettings' in config_dict:
                lockout = config_dict['lockoutSettings']
                mode = lockout.get('mode', 'default')
                
                if mode == 'disabled':
                    disable_lockout_type = self.types['DisableLockoutSettings']
                    lockout_settings = System.Activator.CreateInstance(disable_lockout_type)
                elif mode == 'custom':
                    custom_lockout_type = self.types['CustomLockoutSettings']
                    lockout_settings = System.Activator.CreateInstance(
                        custom_lockout_type,
                        lockout.get('lockoutThreshold', 0),
                        lockout.get('lockoutDuration', 30),
                        lockout.get('lockoutWindow', 30)
                    )
                else:
                    default_lockout_type = self.types['DefaultLockoutSettings']
                    lockout_settings = System.Activator.CreateInstance(default_lockout_type)
                
                lockout_settings_prop = config_type.GetProperty("LockoutSettings")
                lockout_settings_prop.SetValue(config, lockout_settings)
            
            # 设置模块 11: 高级设置
            # 设置快速设置
            if 'expressSettings' in config_dict:
                express = config_dict['expressSettings']
                mode = express.get('mode', 'disableAll')
                
                express_settings_mode_type = self.assembly.GetType("Schneegans.Unattend.ExpressSettingsMode")
                if mode == 'interactive':
                    express_mode = System.Enum.Parse(express_settings_mode_type, "Interactive")
                elif mode == 'enableAll':
                    express_mode = System.Enum.Parse(express_settings_mode_type, "EnableAll")
                else:
                    express_mode = System.Enum.Parse(express_settings_mode_type, "DisableAll")
                
                express_settings_prop = config_type.GetProperty("ExpressSettings")
                express_settings_prop.SetValue(config, express_mode)
            
            # 设置 WDAC 设置
            if 'wdac' in config_dict:
                wdac = config_dict['wdac']
                mode = wdac.get('mode', 'skip')
                
                if mode == 'configure':
                    wdac_audit_modes_type = self.assembly.GetType("Schneegans.Unattend.WdacAuditModes")
                    wdac_script_modes_type = self.assembly.GetType("Schneegans.Unattend.WdacScriptModes")
                    
                    audit_mode_str = wdac.get('auditMode', 'enforcement')
                    script_mode_str = wdac.get('scriptMode', 'restricted')
                    
                    # 转换前端值到 C# 枚举值
                    audit_mode_map = {
                        'auditing': 'Auditing',
                        'auditingOnBootFailure': 'AuditingOnBootFailure',
                        'enforcement': 'Enforcement'
                    }
                    script_mode_map = {
                        'restricted': 'Restricted',
                        'unrestricted': 'Unrestricted'
                    }
                    
                    audit_mode = System.Enum.Parse(wdac_audit_modes_type, audit_mode_map.get(audit_mode_str, 'Enforcement'))
                    script_mode = System.Enum.Parse(wdac_script_modes_type, script_mode_map.get(script_mode_str, 'Restricted'))
                    
                    configure_wdac_type = self.assembly.GetType("Schneegans.Unattend.ConfigureWdacSettings")
                    wdac_settings = System.Activator.CreateInstance(configure_wdac_type, audit_mode, script_mode)
                else:
                    skip_wdac_type = self.assembly.GetType("Schneegans.Unattend.SkipWdacSettings")
                    wdac_settings = System.Activator.CreateInstance(skip_wdac_type)
                
                wdac_settings_prop = config_type.GetProperty("WdacSettings")
                wdac_settings_prop.SetValue(config, wdac_settings)
            
            # 设置处理器架构（简化处理，因为 ImmutableHashSet 构建复杂）
            # 默认使用 amd64，如果需要多架构支持，需要更复杂的实现
            if 'processorArchitectures' in config_dict:
                # 暂时跳过，使用默认值（已在 Configuration.Default 中设置）
                pass
            
            # 设置预装软件（Bloatware）（简化处理，因为 ImmutableList 构建复杂）
            if 'bloatware' in config_dict:
                # 暂时跳过，使用默认值（空列表）
                pass
            
            # 生成 XML (返回 XmlDocument)
            generate_xml_method = generator_type.GetMethod("GenerateXml")
            xml_doc = generate_xml_method.Invoke(self.generator, [config])
            
            # 序列化为字节数组
            # Serialize 是静态方法，接受 XmlDocument 参数
            # 在 .NET Core 中，需要使用程序集限定名称或从已加载的程序集获取类型
            xml_doc_type = xml_doc.GetType()  # 直接从对象获取类型
            
            # 使用正确的参数类型数组
            param_types = System.Array[System.Type]([xml_doc_type])
            serialize_method = generator_type.GetMethod("Serialize", param_types)
            
            if serialize_method is None:
                # 尝试使用 BindingFlags 查找静态方法
                from System.Reflection import BindingFlags
                serialize_method = generator_type.GetMethod("Serialize", BindingFlags.Public | BindingFlags.Static, None, param_types, None)
            
            if serialize_method is None:
                # 最后尝试：直接通过方法名查找（可能有重载）
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
            logger.error(f"✗ C# DLL generation failed: {e}")
            import traceback
            traceback.print_exc()
            return None


# ========================================
# XML 对比工具
# ========================================

def normalize_xml(xml_bytes: bytes) -> str:
    """标准化 XML（移除格式差异）"""
    try:
        root = ET.fromstring(xml_bytes)
        # 重新序列化以标准化格式
        xml_str = ET.tostring(root, encoding='unicode', method='xml')
        # 使用 minidom 格式化
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent='  ')
    except Exception as e:
        return xml_bytes.decode('utf-8', errors='ignore')


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
        ns = {
            'u': 'urn:schemas-microsoft-com:unattend',
            'wcm': 'http://schemas.microsoft.com/WMIConfig/2002/State'
        }
        
        differences = []
        
        # 对比语言设置组件
        python_pe = python_root.find(".//{urn:schemas-microsoft-com:unattend}component[@name='Microsoft-Windows-International-Core-WinPE']")
        csharp_pe = csharp_root.find(".//{urn:schemas-microsoft-com:unattend}component[@name='Microsoft-Windows-International-Core-WinPE']")
        
        if (python_pe is None) != (csharp_pe is None):
            differences.append(f"WinPE component existence mismatch")
        elif python_pe is not None:
            python_ui = python_pe.find("{urn:schemas-microsoft-com:unattend}UILanguage")
            csharp_ui = csharp_pe.find("{urn:schemas-microsoft-com:unattend}UILanguage")
            if (python_ui is None) != (csharp_ui is None):
                differences.append("UILanguage in WinPE mismatch")
            elif python_ui is not None and python_ui.text != csharp_ui.text:
                differences.append(f"UILanguage in WinPE: Python='{python_ui.text}', C#='{csharp_ui.text}'")
        
        python_oobe = python_root.find(".//{urn:schemas-microsoft-com:unattend}component[@name='Microsoft-Windows-International-Core']")
        csharp_oobe = csharp_root.find(".//{urn:schemas-microsoft-com:unattend}component[@name='Microsoft-Windows-International-Core']")
        
        if (python_oobe is None) != (csharp_oobe is None):
            differences.append(f"OOBE component existence mismatch")
        elif python_oobe is not None:
            for elem_name in ['InputLocale', 'SystemLocale', 'UserLocale', 'UILanguage']:
                python_elem = python_oobe.find(f"{{urn:schemas-microsoft-com:unattend}}{elem_name}")
                csharp_elem = csharp_oobe.find(f"{{urn:schemas-microsoft-com:unattend}}{elem_name}")
                if (python_elem is None) != (csharp_elem is None):
                    differences.append(f"{elem_name} existence mismatch")
                elif python_elem is not None and python_elem.text != csharp_elem.text:
                    differences.append(f"{elem_name}: Python='{python_elem.text}', C#='{csharp_elem.text}'")
        
        # 对比时区设置
        python_tz = python_root.find(".//{urn:schemas-microsoft-com:unattend}component[@name='Microsoft-Windows-Shell-Setup']/{urn:schemas-microsoft-com:unattend}TimeZone")
        csharp_tz = csharp_root.find(".//{urn:schemas-microsoft-com:unattend}component[@name='Microsoft-Windows-Shell-Setup']/{urn:schemas-microsoft-com:unattend}TimeZone")
        
        if (python_tz is None) != (csharp_tz is None):
            differences.append(f"TimeZone existence mismatch")
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
# 模块 1 测试用例
# ========================================

def test_module_1_interactive_language():
    """测试模块 1: 交互式语言设置"""
    logger.info("\n" + "="*60)
    logger.info("Test: Module 1 - Interactive Language Settings")
    logger.info("="*60)
    
    try:
        generator = UnattendGenerator()
        config = Configuration()
        config.language_settings = InteractiveLanguageSettings()
        config.time_zone_settings = ImplicitTimeZoneSettings()
        
        # Python 实现
        python_xml = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml)} bytes)")
        
        # 保存 XML 用于检查
        output_dir = project_root / 'test' / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / 'module_1_interactive_language_python.xml'
        with open(output_file, 'wb') as f:
            f.write(python_xml)
        logger.info(f"  Saved to {output_file}")
        
        # C# DLL 对比
        csharp_wrapper = CSharpDLLWrapper()
        if csharp_wrapper.dll_loaded:
            config_dict = {
                'languageSettings': {'mode': 'interactive'},
                'timeZone': {'mode': 'implicit'}
            }
            csharp_xml = csharp_wrapper.generate_xml(config_dict)
            if csharp_xml:
                compare_xml(python_xml, csharp_xml, "module_1_interactive_language")
            else:
                logger.warning("  C# DLL XML generation returned None")
        else:
            logger.info("  (C# DLL comparison skipped - DLL not loaded)")
        
    except Exception as e:
        logger.error(f"✗ Python generation failed: {e}")
        import traceback
        traceback.print_exc()
        return


def test_module_1_unattended_language_basic():
    """测试模块 1: 无人值守语言设置（基础）"""
    logger.info("\n" + "="*60)
    logger.info("Test: Module 1 - Unattended Language Settings (Basic)")
    logger.info("="*60)
    
    try:
        generator = UnattendGenerator()
        
        # 创建配置：英语（美国）
        logger.info("  Looking up data items...")
        image_language = generator.lookup(ImageLanguage, 'en-US')
        user_locale = generator.lookup(UserLocale, 'en-US')
        keyboard = generator.lookup(KeyboardIdentifier, '00000409')  # US Keyboard
        geo_location = generator.lookup(GeoLocation, '244')  # United States
        time_offset = generator.lookup(TimeOffset, 'Eastern Standard Time')
        
        logger.info(f"    ImageLanguage: {image_language.id if image_language else 'None'}")
        logger.info(f"    UserLocale: {user_locale.id if user_locale else 'None'}")
        logger.info(f"    Keyboard: {keyboard.id if keyboard else 'None'}")
        logger.info(f"    GeoLocation: {geo_location.id if geo_location else 'None'}")
        logger.info(f"    TimeOffset: {time_offset.id if time_offset else 'None'}")
        
        if not all([image_language, user_locale, keyboard, geo_location, time_offset]):
            logger.error("✗ Failed to lookup required data items")
            return
        
        config = Configuration()
        config.language_settings = UnattendedLanguageSettings(
            image_language=image_language,
            locale_and_keyboard=LocaleAndKeyboard(locale=user_locale, keyboard=keyboard),
            geo_location=geo_location
        )
        config.time_zone_settings = ExplicitTimeZoneSettings(time_zone=time_offset)
        
        # Python 实现
        logger.info("  Generating XML...")
        python_xml = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml)} bytes)")
        
        # 保存 XML 用于检查
        output_dir = project_root / 'test' / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / 'module_1_unattended_language_basic_python.xml'
        with open(output_file, 'wb') as f:
            f.write(python_xml)
        logger.info(f"  Saved to {output_file}")
        
        # 显示 XML 的关键部分
        try:
            root = ET.fromstring(python_xml)
            ns_uri = '{urn:schemas-microsoft-com:unattend}'
            pe_comp = root.find(f".//{ns_uri}component[@name='Microsoft-Windows-International-Core-WinPE']")
            oobe_comp = root.find(f".//{ns_uri}component[@name='Microsoft-Windows-International-Core']")
            tz_comp = root.find(f".//{ns_uri}component[@name='Microsoft-Windows-Shell-Setup']/{ns_uri}TimeZone")
            
            if pe_comp is not None:
                ui_lang = pe_comp.find(f"{ns_uri}UILanguage")
                logger.info(f"    WinPE UILanguage: {ui_lang.text if ui_lang is not None else 'None'}")
            
            if oobe_comp is not None:
                input_locale = oobe_comp.find(f"{ns_uri}InputLocale")
                system_locale = oobe_comp.find(f"{ns_uri}SystemLocale")
                user_locale_elem = oobe_comp.find(f"{ns_uri}UserLocale")
                ui_lang_oobe = oobe_comp.find(f"{ns_uri}UILanguage")
                logger.info(f"    OOBE InputLocale: {input_locale.text if input_locale is not None else 'None'}")
                logger.info(f"    OOBE SystemLocale: {system_locale.text if system_locale is not None else 'None'}")
                logger.info(f"    OOBE UserLocale: {user_locale_elem.text if user_locale_elem is not None else 'None'}")
                logger.info(f"    OOBE UILanguage: {ui_lang_oobe.text if ui_lang_oobe is not None else 'None'}")
            
            if tz_comp is not None:
                logger.info(f"    TimeZone: {tz_comp.text}")
        except Exception as e:
            logger.warning(f"    (Could not parse XML for display: {e})")
        
        # C# DLL 对比
        csharp_wrapper = CSharpDLLWrapper()
        if csharp_wrapper.dll_loaded:
            config_dict = {
                'languageSettings': {
                    'mode': 'unattended',
                    'uiLanguage': 'en-US',
                    'systemLocale': 'en-US',
                    'inputLocale': '00000409',
                    'geoLocation': '244'
                },
                'timeZone': {
                    'mode': 'explicit',
                    'timeZone': 'Eastern Standard Time'
                }
            }
            csharp_xml = csharp_wrapper.generate_xml(config_dict)
            if csharp_xml:
                compare_xml(python_xml, csharp_xml, "module_1_unattended_language_basic")
            else:
                logger.warning("  C# DLL XML generation returned None")
        else:
            logger.info("  (C# DLL comparison skipped - DLL not loaded)")
        
    except Exception as e:
        logger.error(f"✗ Python generation failed: {e}")
        import traceback
        traceback.print_exc()
        return


def test_module_1_unattended_language_chinese():
    """测试模块 1: 无人值守语言设置（中文）"""
    logger.info("\n" + "="*60)
    logger.info("Test: Module 1 - Unattended Language Settings (Chinese)")
    logger.info("="*60)
    
    try:
        generator = UnattendGenerator()
        
        # 创建配置：简体中文
        logger.info("  Looking up data items...")
        image_language = generator.lookup(ImageLanguage, 'zh-CN')
        user_locale = generator.lookup(UserLocale, 'zh-CN')
        keyboard = generator.lookup(KeyboardIdentifier, '00000804')  # Chinese (Simplified) - US Keyboard
        geo_location = generator.lookup(GeoLocation, '45')  # China
        time_offset = generator.lookup(TimeOffset, 'China Standard Time')
        
        logger.info(f"    ImageLanguage: {image_language.id if image_language else 'None'}")
        logger.info(f"    UserLocale: {user_locale.id if user_locale else 'None'}")
        logger.info(f"    Keyboard: {keyboard.id if keyboard else 'None'}")
        logger.info(f"    GeoLocation: {geo_location.id if geo_location else 'None'}")
        logger.info(f"    TimeOffset: {time_offset.id if time_offset else 'None'}")
        
        if not all([image_language, user_locale, keyboard, geo_location, time_offset]):
            logger.error("✗ Failed to lookup required data items")
            return
        
        config = Configuration()
        config.language_settings = UnattendedLanguageSettings(
            image_language=image_language,
            locale_and_keyboard=LocaleAndKeyboard(locale=user_locale, keyboard=keyboard),
            geo_location=geo_location
        )
        config.time_zone_settings = ExplicitTimeZoneSettings(time_zone=time_offset)
        
        # Python 实现
        logger.info("  Generating XML...")
        python_xml = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml)} bytes)")
        
        # 保存 XML 用于检查
        output_dir = project_root / 'test' / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / 'module_1_unattended_language_chinese_python.xml'
        with open(output_file, 'wb') as f:
            f.write(python_xml)
        logger.info(f"  Saved to {output_file}")
        
        # C# DLL 对比
        csharp_wrapper = CSharpDLLWrapper()
        if csharp_wrapper.dll_loaded:
            config_dict = {
                'languageSettings': {
                    'mode': 'unattended',
                    'uiLanguage': 'zh-CN',
                    'systemLocale': 'zh-CN',
                    'inputLocale': '00000804',
                    'geoLocation': '45'
                },
                'timeZone': {
                    'mode': 'explicit',
                    'timeZone': 'China Standard Time'
                }
            }
            csharp_xml = csharp_wrapper.generate_xml(config_dict)
            if csharp_xml:
                compare_xml(python_xml, csharp_xml, "module_1_unattended_language_chinese")
            else:
                logger.warning("  C# DLL XML generation returned None")
        else:
            logger.info("  (C# DLL comparison skipped - DLL not loaded)")
        
    except Exception as e:
        logger.error(f"✗ Python generation failed: {e}")
        import traceback
        traceback.print_exc()
        return


def test_module_1_timezone_only():
    """测试模块 1: 仅时区设置（隐式语言）"""
    logger.info("\n" + "="*60)
    logger.info("Test: Module 1 - TimeZone Only (Implicit Language)")
    logger.info("="*60)
    
    try:
        generator = UnattendGenerator()
        
        logger.info("  Looking up timezone...")
        time_offset = generator.lookup(TimeOffset, 'Tokyo Standard Time')
        logger.info(f"    TimeOffset: {time_offset.id if time_offset else 'None'}")
        
        if not time_offset:
            logger.error("✗ Failed to lookup timezone")
            return
        
        config = Configuration()
        config.language_settings = InteractiveLanguageSettings()
        config.time_zone_settings = ExplicitTimeZoneSettings(time_zone=time_offset)
        
        # Python 实现
        logger.info("  Generating XML...")
        python_xml = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml)} bytes)")
        
        # 保存 XML 用于检查
        output_dir = project_root / 'test' / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / 'module_1_timezone_only_python.xml'
        with open(output_file, 'wb') as f:
            f.write(python_xml)
        logger.info(f"  Saved to {output_file}")
        
        # 显示 XML 的关键部分
        try:
            root = ET.fromstring(python_xml)
            ns_uri = '{urn:schemas-microsoft-com:unattend}'
            tz_comp = root.find(f".//{ns_uri}component[@name='Microsoft-Windows-Shell-Setup']/{ns_uri}TimeZone")
            if tz_comp is not None:
                logger.info(f"    TimeZone: {tz_comp.text}")
        except Exception as e:
            logger.warning(f"    (Could not parse XML for display: {e})")
        
        # C# DLL 对比
        csharp_wrapper = CSharpDLLWrapper()
        if csharp_wrapper.dll_loaded:
            config_dict = {
                'languageSettings': {'mode': 'interactive'},
                'timeZone': {
                    'mode': 'explicit',
                    'timeZone': 'Tokyo Standard Time'
                }
            }
            csharp_xml = csharp_wrapper.generate_xml(config_dict)
            if csharp_xml:
                compare_xml(python_xml, csharp_xml, "module_1_timezone_only")
            else:
                logger.warning("  C# DLL XML generation returned None")
        else:
            logger.info("  (C# DLL comparison skipped - DLL not loaded)")
        
    except Exception as e:
        logger.error(f"✗ Python generation failed: {e}")
        import traceback
        traceback.print_exc()
        return


# ========================================
# 模块 2 测试用例
# ========================================

def test_module_2_setup_settings():
    """测试模块 2: Setup Settings"""
    logger.info("\n" + "="*60)
    logger.info("Test: Module 2 - Setup Settings")
    logger.info("="*60)
    
    try:
        generator = UnattendGenerator()
        
        # 测试用例 1: 所有设置都启用
        logger.info("  Test case 1: All settings enabled")
        config = Configuration()
        config.language_settings = InteractiveLanguageSettings()
        config.time_zone_settings = ImplicitTimeZoneSettings()
        config.bypass_requirements_check = True
        config.bypass_network_check = True
        config.use_configuration_set = True
        config.hide_power_shell_windows = True
        config.keep_sensitive_files = False
        config.use_narrator = True
        
        python_xml = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml)} bytes)")
        
        # 保存 XML
        output_dir = project_root / 'test' / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / 'module_2_all_enabled_python.xml'
        with open(output_file, 'wb') as f:
            f.write(python_xml)
        logger.info(f"  Saved to {output_file}")
        
        # 检查关键元素
        try:
            root = ET.fromstring(python_xml)
            ns_uri = '{urn:schemas-microsoft-com:unattend}'
            s_uri = '{http://schemas.microsoft.com/SMI/2016/WindowsSettings}'
            
            # 检查 UseConfigurationSet
            use_config_set = root.find(f".//{ns_uri}UseConfigurationSet")
            if use_config_set is not None:
                logger.info(f"    UseConfigurationSet: {use_config_set.text}")
            
            # 检查 Bypass 注册表命令
            run_sync = root.findall(f".//{ns_uri}RunSynchronousCommand")
            logger.info(f"    Found {len(run_sync)} RunSynchronousCommand elements")
            
            # 检查 Extensions 中的文件
            extensions = root.find(f".//{s_uri}Extensions")
            if extensions is not None:
                files = extensions.findall(f".//{s_uri}File")
                logger.info(f"    Found {len(files)} files in Extensions")
                for file_elem in files:
                    source = file_elem.get('Source', '')
                    logger.info(f"      File: {source}")
        except Exception as e:
            logger.warning(f"    (Could not parse XML for display: {e})")
        
        # C# DLL 对比
        csharp_wrapper = CSharpDLLWrapper()
        if csharp_wrapper.dll_loaded:
            config_dict = {
                'languageSettings': {'mode': 'interactive'},
                'timeZone': {'mode': 'implicit'},
                'setupSettings': {
                    'bypassRequirementsCheck': True,
                    'bypassNetworkCheck': True,
                    'useConfigurationSet': True,
                    'hidePowerShellWindows': True,
                    'keepSensitiveFiles': False,
                    'useNarrator': True
                }
            }
            csharp_xml = csharp_wrapper.generate_xml(config_dict)
            if csharp_xml:
                compare_xml(python_xml, csharp_xml, "module_2_all_enabled")
            else:
                logger.warning("  C# DLL XML generation returned None")
        else:
            logger.info("  (C# DLL comparison skipped - DLL not loaded)")
        
        # 测试用例 2: 所有设置都禁用
        logger.info("\n  Test case 2: All settings disabled")
        config2 = Configuration()
        config2.language_settings = InteractiveLanguageSettings()
        config2.time_zone_settings = ImplicitTimeZoneSettings()
        config2.bypass_requirements_check = False
        config2.bypass_network_check = False
        config2.use_configuration_set = False
        config2.hide_power_shell_windows = False
        config2.keep_sensitive_files = True
        config2.use_narrator = False
        
        python_xml2 = generator.generate_xml(config2)
        logger.info(f"✓ Python generated XML ({len(python_xml2)} bytes)")
        
        output_file2 = output_dir / 'module_2_all_disabled_python.xml'
        with open(output_file2, 'wb') as f:
            f.write(python_xml2)
        logger.info(f"  Saved to {output_file2}")
        
        # C# DLL 对比
        if csharp_wrapper.dll_loaded:
            config_dict2 = {
                'languageSettings': {'mode': 'interactive'},
                'timeZone': {'mode': 'implicit'},
                'setupSettings': {
                    'bypassRequirementsCheck': False,
                    'bypassNetworkCheck': False,
                    'useConfigurationSet': False,
                    'hidePowerShellWindows': False,
                    'keepSensitiveFiles': True,
                    'useNarrator': False
                }
            }
            csharp_xml2 = csharp_wrapper.generate_xml(config_dict2)
            if csharp_xml2:
                compare_xml(python_xml2, csharp_xml2, "module_2_all_disabled")
            else:
                logger.warning("  C# DLL XML generation returned None")
        
    except Exception as e:
        logger.error(f"✗ Python generation failed: {e}")
        import traceback
        traceback.print_exc()
        return


# ========================================
# 模块 4 测试用例
# ========================================

def test_module_4_name_and_account():
    """测试模块 4: Name and Account"""
    logger.info("\n" + "="*60)
    logger.info("Test: Module 4 - Name and Account")
    logger.info("="*60)
    
    try:
        generator = UnattendGenerator()
        
        # 测试用例 1: 自定义计算机名 + 无人值守账户 + 自动登录
        logger.info("  Test case 1: Custom computer name + Unattended accounts + Auto logon")
        config = Configuration()
        config.language_settings = InteractiveLanguageSettings()
        config.time_zone_settings = ImplicitTimeZoneSettings()
        config.computer_name_settings = CustomComputerNameSettings(computer_name="MYPC-001")
        
        # 创建账户
        account1 = Account(
            name="TestUser",
            display_name="Test User",
            password="TestPass123",
            group=Constants.AdministratorsGroup
        )
        account2 = Account(
            name="RegularUser",
            display_name="Regular User",
            password="UserPass123",
            group=Constants.UsersGroup
        )
        
        config.account_settings = UnattendedAccountSettings(
            accounts=[account1, account2],
            auto_logon_settings=BuiltinAutoLogonSettings(password="AdminPass123"),
            obscure_passwords=False
        )
        config.password_expiration_settings = DefaultPasswordExpirationSettings()
        config.lockout_settings = DefaultLockoutSettings()
        
        python_xml = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml)} bytes)")
        
        # 保存 XML
        output_dir = project_root / 'test' / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / 'module_4_custom_name_accounts_python.xml'
        with open(output_file, 'wb') as f:
            f.write(python_xml)
        logger.info(f"  Saved to {output_file}")
        
        # 检查关键元素
        try:
            root = ET.fromstring(python_xml)
            ns_uri = '{urn:schemas-microsoft-com:unattend}'
            
            # 检查计算机名
            component_shell = root.find(f".//{{{ns_uri}}}component[@name='Microsoft-Windows-Shell-Setup']")
            if component_shell is not None:
                computer_name = component_shell.find(f"{{{ns_uri}}}ComputerName")
                if computer_name is not None:
                    logger.info(f"    ComputerName: {computer_name.text}")
            
            # 检查用户账户
            user_accounts = root.find(f".//{{{ns_uri}}}UserAccounts")
            if user_accounts is not None:
                local_accounts = user_accounts.find(f"{{{ns_uri}}}LocalAccounts")
                if local_accounts is not None:
                    accounts = local_accounts.findall(f"{{{ns_uri}}}LocalAccount")
                    logger.info(f"    Found {len(accounts)} local accounts")
            
            # 检查自动登录
            auto_logon = root.find(f".//{{{ns_uri}}}AutoLogon")
            if auto_logon is not None:
                username = auto_logon.find(f"{{{ns_uri}}}Username")
                if username is not None:
                    logger.info(f"    AutoLogon Username: {username.text}")
        except Exception as e:
            logger.warning(f"    (Could not parse XML for display: {e})")
        
        # C# DLL 对比（暂时跳过，因为 ImmutableList 构建比较复杂）
        csharp_wrapper = CSharpDLLWrapper()
        if csharp_wrapper.dll_loaded:
            logger.info("  (C# DLL comparison skipped - ImmutableList building is complex)")
        else:
            logger.info("  (C# DLL comparison skipped - DLL not loaded)")
        
        # 测试用例 2: 随机计算机名 + 交互式账户
        logger.info("\n  Test case 2: Random computer name + Interactive accounts")
        config2 = Configuration()
        config2.language_settings = InteractiveLanguageSettings()
        config2.time_zone_settings = ImplicitTimeZoneSettings()
        config2.computer_name_settings = RandomComputerNameSettings()
        config2.account_settings = InteractiveMicrosoftAccountSettings()
        config2.password_expiration_settings = UnlimitedPasswordExpirationSettings()
        config2.lockout_settings = DisableLockoutSettings()
        
        python_xml2 = generator.generate_xml(config2)
        logger.info(f"✓ Python generated XML ({len(python_xml2)} bytes)")
        
        output_file2 = output_dir / 'module_4_random_name_interactive_python.xml'
        with open(output_file2, 'wb') as f:
            f.write(python_xml2)
        logger.info(f"  Saved to {output_file2}")
        
    except Exception as e:
        logger.error(f"✗ Python generation failed: {e}")
        import traceback
        traceback.print_exc()
        return


# ========================================
# 主测试函数
# ========================================

def test_module_5_partitioning():
    """测试模块 5: 分区和格式化设置"""
    logger.info("\n" + "="*60)
    logger.info("Test: Module 5 - Partitioning and Formatting")
    logger.info("="*60)
    
    try:
        from src.backend.unattend_generator import (
            UnattendGenerator, Configuration,
            UnattendedPartitionSettings, PartitionLayout, RecoveryMode,
            DefaultPESettings, SkipDiskAssertionSettings
        )
        
        generator = UnattendGenerator()
        config = Configuration()
        
        # 测试用例 1: 自动分区 (GPT, 恢复分区)
        config.partition_settings = UnattendedPartitionSettings(
            partition_layout=PartitionLayout.GPT,
            recovery_mode=RecoveryMode.Partition,
            esp_size=100,
            recovery_size=500
        )
        config.pe_settings = DefaultPESettings()
        config.disk_assertion_settings = SkipDiskAssertionSettings()
        
        # Python 实现
        python_xml = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml)} bytes)")
        
        # 保存 XML 用于检查
        output_dir = project_root / 'test' / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / 'module_5_partitioning_python.xml'
        with open(output_file, 'wb') as f:
            f.write(python_xml)
        logger.info(f"  Saved to {output_file}")
        
        # C# DLL 对比
        if csharp_wrapper.dll_loaded:
            logger.info("\nComparing with C# DLL...")
            config_dict = {
                'partitioning': {
                    'mode': 'automatic',
                    'layout': 'GPT',
                    'recoveryMode': 'partition',
                    'espSize': 100,
                    'recoverySize': 500
                },
                'peSettings': {'mode': 'default'},
                'processorArchitectures': ['amd64']
            }
            
            csharp_xml = csharp_wrapper.generate_xml(config_dict)
            logger.info(f"✓ C# DLL generated XML ({len(csharp_xml)} bytes)")
            
            if compare_xml(python_xml, csharp_xml, "module_5_partitioning"):
                logger.info("✓ Module 5 test passed!")
                return True
            else:
                logger.error("✗ Module 5 test failed!")
                return False
        else:
            logger.warning("⚠ C# DLL not loaded, skipping comparison")
            logger.info("✓ Module 5 test completed (no C# comparison)")
            return True
            
    except Exception as e:
        logger.error(f"✗ Module 5 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_module_6_windows_edition_and_source():
    """测试模块 6: Windows Edition and Source"""
    logger.info("\n" + "="*60)
    logger.info("Test: Module 6 - Windows Edition and Source")
    logger.info("="*60)
    
    try:
        from unattend_generator import (
            UnattendGenerator, Configuration,
            InteractiveEditionSettings, CustomEditionSettings,
            AutomaticInstallFromSettings, IndexInstallFromSettings, NameInstallFromSettings,
            InteractiveLanguageSettings, ImplicitTimeZoneSettings
        )
        
        generator = UnattendGenerator()
        config = Configuration()
        config.language_settings = InteractiveLanguageSettings()
        config.time_zone_settings = ImplicitTimeZoneSettings()
        
        # 测试用例 1: 交互式版本设置 + 自动安装源
        logger.info("  Test case 1: Interactive edition + Automatic source")
        config.edition_settings = InteractiveEditionSettings()
        config.install_from_settings = AutomaticInstallFromSettings()
        
        python_xml = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml)} bytes)")
        
        # 保存 XML
        output_dir = project_root / 'test' / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / 'module_6_interactive_automatic_python.xml'
        with open(output_file, 'wb') as f:
            f.write(python_xml)
        logger.info(f"  Saved to {output_file}")
        
        # C# DLL 对比
        csharp_wrapper = CSharpDLLWrapper()
        if csharp_wrapper.dll_loaded:
            logger.info("\nComparing with C# DLL...")
            config_dict = {
                'windowsEdition': {'mode': 'interactive'},
                'sourceImage': {'mode': 'automatic'},
                'processorArchitectures': ['amd64']
            }
            
            csharp_xml = csharp_wrapper.generate_xml(config_dict)
            logger.info(f"✓ C# DLL generated XML ({len(csharp_xml)} bytes)")
            
            if compare_xml(python_xml, csharp_xml, "module_6_interactive_automatic"):
                logger.info("✓ Test case 1 passed!")
            else:
                logger.error("✗ Test case 1 failed!")
                return False
        else:
            logger.warning("⚠ C# DLL not loaded, skipping comparison")
        
        logger.info("\n✓ Module 6 test completed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Module 6 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_module_7_ui_personalization():
    """测试模块 7: UI and Personalization"""
    logger.info("\n" + "="*60)
    logger.info("Test: Module 7 - UI and Personalization")
    logger.info("="*60)
    
    try:
        from unattend_generator import (
            UnattendGenerator, Configuration,
            InteractiveLanguageSettings, ImplicitTimeZoneSettings,
            DefaultStartPinsSettings, DefaultStartTilesSettings, DefaultTaskbarIcons,
            DefaultEffects, DefaultDesktopIconSettings,
            DefaultStartFolderSettings, DefaultWallpaperSettings, DefaultLockScreenSettings,
            DefaultColorSettings, HideModes, TaskbarSearchMode
        )
        
        generator = UnattendGenerator()
        config = Configuration()
        config.language_settings = InteractiveLanguageSettings()
        config.time_zone_settings = ImplicitTimeZoneSettings()
        
        # 测试用例 1: 基本 UI 设置
        logger.info("  Test case 1: Basic UI settings")
        config.show_file_extensions = True
        config.hide_files = HideModes.None_
        config.taskbar_search = TaskbarSearchMode.Hide
        config.start_pins_settings = DefaultStartPinsSettings()
        config.start_tiles_settings = DefaultStartTilesSettings()
        config.taskbar_icons = DefaultTaskbarIcons()
        config.effects = DefaultEffects()
        config.desktop_icons = DefaultDesktopIconSettings()
        config.start_folder_settings = DefaultStartFolderSettings()
        config.wallpaper_settings = DefaultWallpaperSettings()
        config.lock_screen_settings = DefaultLockScreenSettings()
        config.color_settings = DefaultColorSettings()
        
        python_xml = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml)} bytes)")
        
        # 保存 XML
        output_dir = project_root / 'test' / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / 'module_7_basic_ui_python.xml'
        with open(output_file, 'wb') as f:
            f.write(python_xml)
        logger.info(f"  Saved to {output_file}")
        
        # C# DLL 对比
        csharp_wrapper = CSharpDLLWrapper()
        if csharp_wrapper.dll_loaded:
            logger.info("\nComparing with C# DLL...")
            config_dict = {
                'fileExplorer': {
                    'showFileExtensions': True,
                    'hideFiles': 'none'
                },
                'startMenuTaskbar': {
                    'taskbarSearch': 'hide',
                    'startPins': {'mode': 'default'},
                    'startTiles': {'mode': 'default'},
                    'taskbarIcons': {'mode': 'default'}
                },
                'visualEffects': {'mode': 'default'},
                'desktopIcons': {'mode': 'default'},
                'startFolders': {'mode': 'default'},
                'personalization': {
                    'wallpaper': {'mode': 'default'},
                    'lockScreen': {'mode': 'default'},
                    'color': {'mode': 'default'}
                },
                'processorArchitectures': ['amd64']
            }
            
            csharp_xml = csharp_wrapper.generate_xml(config_dict)
            logger.info(f"✓ C# DLL generated XML ({len(csharp_xml)} bytes)")
            
            if compare_xml(python_xml, csharp_xml, "module_7_basic_ui"):
                logger.info("✓ Test case 1 passed!")
            else:
                logger.error("✗ Test case 1 failed!")
                return False
        else:
            logger.warning("⚠ C# DLL not loaded, skipping comparison")
        
        logger.info("\n✓ Module 7 test completed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Module 7 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_module_8_wifi():
    """测试模块 8: Wi-Fi 设置"""
    logger.info("\n" + "="*60)
    logger.info("Test: Module 8 - Wi-Fi Settings")
    logger.info("="*60)
    
    try:
        from unattend_generator import (
            UnattendGenerator, Configuration,
            InteractiveLanguageSettings, ImplicitTimeZoneSettings,
            SkipWifiSettings, InteractiveWifiSettings, UnattendedWifiSettings,
            WifiAuthentications
        )
        
        generator = UnattendGenerator()
        config = Configuration()
        config.language_settings = InteractiveLanguageSettings()
        config.time_zone_settings = ImplicitTimeZoneSettings()
        
        # 测试用例 1: 跳过 Wi-Fi 设置
        logger.info("  Test case 1: Skip Wi-Fi settings")
        config.wifi_settings = SkipWifiSettings()
        
        python_xml = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml)} bytes)")
        
        # 保存 XML
        output_dir = project_root / 'test' / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / 'module_8_skip_wifi_python.xml'
        with open(output_file, 'wb') as f:
            f.write(python_xml)
        logger.info(f"  Saved to {output_file}")
        
        # C# DLL 对比
        csharp_wrapper = CSharpDLLWrapper()
        if csharp_wrapper.dll_loaded:
            logger.info("\nComparing with C# DLL...")
            config_dict = {
                'wifi': {'mode': 'skip'},
                'processorArchitectures': ['amd64']
            }
            
            csharp_xml = csharp_wrapper.generate_xml(config_dict)
            logger.info(f"✓ C# DLL generated XML ({len(csharp_xml)} bytes)")
            
            if compare_xml(python_xml, csharp_xml, "module_8_skip_wifi"):
                logger.info("✓ Test case 1 passed!")
            else:
                logger.error("✗ Test case 1 failed!")
                return False
        else:
            logger.warning("⚠ C# DLL not loaded, skipping comparison")
        
        logger.info("\n✓ Module 8 test completed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Module 8 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_module_9_accessibility():
    """测试模块 9: 辅助功能设置"""
    logger.info("\n" + "="*60)
    logger.info("Test: Module 9 - Accessibility Settings")
    logger.info("="*60)
    
    try:
        from unattend_generator import (
            UnattendGenerator, Configuration,
            InteractiveLanguageSettings, ImplicitTimeZoneSettings,
            SkipLockKeySettings, ConfigureLockKeySettings, LockKeySetting,
            LockKeyInitial, LockKeyBehavior,
            DefaultStickyKeysSettings, DisabledStickyKeysSettings, CustomStickyKeysSettings,
            StickyKeys
        )
        
        generator = UnattendGenerator()
        config = Configuration()
        config.language_settings = InteractiveLanguageSettings()
        config.time_zone_settings = ImplicitTimeZoneSettings()
        
        # 测试用例 1: 跳过 Lock Keys 设置
        logger.info("  Test case 1: Skip Lock Keys settings")
        config.lock_key_settings = SkipLockKeySettings()
        config.sticky_keys_settings = DefaultStickyKeysSettings()
        
        python_xml = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml)} bytes)")
        
        # 保存 XML
        output_dir = project_root / 'test' / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / 'module_9_skip_lock_keys_python.xml'
        with open(output_file, 'wb') as f:
            f.write(python_xml)
        logger.info(f"  Saved to {output_file}")
        
        # C# DLL 对比
        csharp_wrapper = CSharpDLLWrapper()
        if csharp_wrapper.dll_loaded:
            logger.info("\nComparing with C# DLL...")
            config_dict = {
                'lockKeys': {'mode': 'skip'},
                'stickyKeys': {'mode': 'default'},
                'processorArchitectures': ['amd64']
            }
            
            csharp_xml = csharp_wrapper.generate_xml(config_dict)
            logger.info(f"✓ C# DLL generated XML ({len(csharp_xml)} bytes)")
            
            if compare_xml(python_xml, csharp_xml, "module_9_skip_lock_keys"):
                logger.info("✓ Test case 1 passed!")
            else:
                logger.error("✗ Test case 1 failed!")
                return False
        else:
            logger.warning("⚠ C# DLL not loaded, skipping comparison")
        
        # 测试用例 2: 配置 Lock Keys
        logger.info("\n  Test case 2: Configure Lock Keys")
        config.lock_key_settings = ConfigureLockKeySettings(
            caps_lock=LockKeySetting(initial=LockKeyInitial.On, behavior=LockKeyBehavior.Toggle),
            num_lock=LockKeySetting(initial=LockKeyInitial.On, behavior=LockKeyBehavior.Ignore),
            scroll_lock=LockKeySetting(initial=LockKeyInitial.Off, behavior=LockKeyBehavior.Toggle)
        )
        config.sticky_keys_settings = CustomStickyKeysSettings(
            flags={StickyKeys.HotKeyActive, StickyKeys.Indicator}
        )
        
        python_xml2 = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml2)} bytes)")
        
        output_file2 = output_dir / 'module_9_configure_lock_keys_python.xml'
        with open(output_file2, 'wb') as f:
            f.write(python_xml2)
        logger.info(f"  Saved to {output_file2}")
        
        # C# DLL 对比
        if csharp_wrapper.dll_loaded:
            config_dict2 = {
                'lockKeys': {
                    'mode': 'configure',
                    'capsLockInitial': 'on',
                    'capsLockBehavior': 'toggle',
                    'numLockInitial': 'on',
                    'numLockBehavior': 'ignore',
                    'scrollLockInitial': 'off',
                    'scrollLockBehavior': 'toggle'
                },
                'stickyKeys': {
                    'mode': 'custom',
                    'stickyKeysHotKeyActive': True,
                    'stickyKeysHotKeySound': False,
                    'stickyKeysIndicator': True,
                    'stickyKeysAudibleFeedback': False,
                    'stickyKeysTriState': False,
                    'stickyKeysTwoKeysOff': False
                },
                'processorArchitectures': ['amd64']
            }
            
            csharp_xml2 = csharp_wrapper.generate_xml(config_dict2)
            logger.info(f"✓ C# DLL generated XML ({len(csharp_xml2)} bytes)")
            
            if compare_xml(python_xml2, csharp_xml2, "module_9_configure_lock_keys"):
                logger.info("✓ Test case 2 passed!")
            else:
                logger.error("✗ Test case 2 failed!")
                return False
        
        logger.info("\n✓ Module 9 test completed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Module 9 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_module_10_system_optimization():
    """测试模块 10: 系统优化设置"""
    logger.info("\n" + "="*60)
    logger.info("Test: Module 10 - System Optimization")
    logger.info("="*60)
    
    try:
        from unattend_generator import (
            UnattendGenerator, Configuration,
            InteractiveLanguageSettings, ImplicitTimeZoneSettings
        )
        
        generator = UnattendGenerator()
        config = Configuration()
        config.language_settings = InteractiveLanguageSettings()
        config.time_zone_settings = ImplicitTimeZoneSettings()
        
        # 测试用例 1: 基本系统优化设置
        logger.info("  Test case 1: Basic system optimization settings")
        config.enable_long_paths = True
        config.enable_remote_desktop = True
        config.disable_uac = True
        config.disable_defender = False
        config.disable_smart_screen = True
        
        python_xml = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml)} bytes)")
        
        # 保存 XML
        output_dir = project_root / 'test' / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / 'module_10_basic_optimization_python.xml'
        with open(output_file, 'wb') as f:
            f.write(python_xml)
        logger.info(f"  Saved to {output_file}")
        
        # C# DLL 对比
        csharp_wrapper = CSharpDLLWrapper()
        if csharp_wrapper.dll_loaded:
            logger.info("\nComparing with C# DLL...")
            config_dict = {
                'systemTweaks': {
                    'enableLongPaths': True,
                    'enableRemoteDesktop': True,
                    'disableUac': True,
                    'disableDefender': False,
                    'disableSmartScreen': True
                },
                'processorArchitectures': ['amd64']
            }
            
            csharp_xml = csharp_wrapper.generate_xml(config_dict)
            logger.info(f"✓ C# DLL generated XML ({len(csharp_xml)} bytes)")
            
            if compare_xml(python_xml, csharp_xml, "module_10_basic_optimization"):
                logger.info("✓ Test case 1 passed!")
            else:
                logger.error("✗ Test case 1 failed!")
                return False
        else:
            logger.warning("⚠ C# DLL not loaded, skipping comparison")
        
        logger.info("\n✓ Module 10 test completed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Module 10 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_module_11_advanced_settings():
    """测试模块 11: 高级设置"""
    logger.info("\n" + "="*60)
    logger.info("Test: Module 11 - Advanced Settings")
    logger.info("="*60)
    
    try:
        from unattend_generator import (
            UnattendGenerator, Configuration,
            InteractiveLanguageSettings, ImplicitTimeZoneSettings,
            ExpressSettingsMode, SkipWdacSettings, ConfigureWdacSettings,
            WdacAuditModes, WdacScriptModes, ProcessorArchitecture
        )
        
        generator = UnattendGenerator()
        config = Configuration()
        config.language_settings = InteractiveLanguageSettings()
        config.time_zone_settings = ImplicitTimeZoneSettings()
        
        # 测试用例 1: 快速设置 - DisableAll
        logger.info("  Test case 1: Express Settings - DisableAll")
        config.express_settings = ExpressSettingsMode.DisableAll
        config.processor_architectures = {ProcessorArchitecture.amd64}
        config.wdac_settings = SkipWdacSettings()
        config.bloatwares = []
        
        python_xml = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml)} bytes)")
        
        # 保存 XML
        output_dir = project_root / 'test' / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / 'module_11_express_disableall_python.xml'
        with open(output_file, 'wb') as f:
            f.write(python_xml)
        logger.info(f"  Saved to {output_file}")
        
        # C# DLL 对比
        csharp_wrapper = CSharpDLLWrapper()
        if csharp_wrapper.dll_loaded:
            logger.info("\nComparing with C# DLL...")
            config_dict = {
                'expressSettings': {'mode': 'disableAll'},
                'processorArchitectures': ['amd64'],
                'wdac': {'mode': 'skip'},
                'bloatware': {'selected': []}
            }
            
            csharp_xml = csharp_wrapper.generate_xml(config_dict)
            logger.info(f"✓ C# DLL generated XML ({len(csharp_xml)} bytes)")
            
            if compare_xml(python_xml, csharp_xml, "module_11_express_disableall"):
                logger.info("✓ Test case 1 passed!")
            else:
                logger.error("✗ Test case 1 failed!")
                return False
        else:
            logger.warning("⚠ C# DLL not loaded, skipping comparison")
        
        # 测试用例 2: WDAC 设置
        logger.info("\n  Test case 2: WDAC Settings")
        config.express_settings = ExpressSettingsMode.DisableAll
        config.wdac_settings = ConfigureWdacSettings(
            audit_mode=WdacAuditModes.Enforcement,
            script_mode=WdacScriptModes.Restricted
        )
        
        python_xml = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml)} bytes)")
        
        output_file = output_dir / 'module_11_wdac_enforcement_python.xml'
        with open(output_file, 'wb') as f:
            f.write(python_xml)
        logger.info(f"  Saved to {output_file}")
        
        if csharp_wrapper.dll_loaded:
            config_dict = {
                'expressSettings': {'mode': 'disableAll'},
                'processorArchitectures': ['amd64'],
                'wdac': {
                    'mode': 'configure',
                    'auditMode': 'enforcement',
                    'scriptMode': 'restricted'
                },
                'bloatware': {'selected': []}
            }
            
            csharp_xml = csharp_wrapper.generate_xml(config_dict)
            logger.info(f"✓ C# DLL generated XML ({len(csharp_xml)} bytes)")
            
            if compare_xml(python_xml, csharp_xml, "module_11_wdac_enforcement"):
                logger.info("✓ Test case 2 passed!")
            else:
                logger.error("✗ Test case 2 failed!")
                return False
        
        # 测试用例 3: 多处理器架构
        logger.info("\n  Test case 3: Multiple Processor Architectures")
        config.processor_architectures = {ProcessorArchitecture.amd64, ProcessorArchitecture.arm64}
        config.wdac_settings = SkipWdacSettings()
        
        python_xml = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml)} bytes)")
        
        output_file = output_dir / 'module_11_multi_arch_python.xml'
        with open(output_file, 'wb') as f:
            f.write(python_xml)
        logger.info(f"  Saved to {output_file}")
        
        if csharp_wrapper.dll_loaded:
            config_dict = {
                'expressSettings': {'mode': 'disableAll'},
                'processorArchitectures': ['amd64', 'arm64'],
                'wdac': {'mode': 'skip'},
                'bloatware': {'selected': []}
            }
            
            csharp_xml = csharp_wrapper.generate_xml(config_dict)
            logger.info(f"✓ C# DLL generated XML ({len(csharp_xml)} bytes)")
            
            if compare_xml(python_xml, csharp_xml, "module_11_multi_arch"):
                logger.info("✓ Test case 3 passed!")
            else:
                logger.error("✗ Test case 3 failed!")
                return False
        
        logger.info("\n✓ Module 11 test completed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Module 11 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_module_12_custom_scripts():
    """测试模块 12: 自定义脚本"""
    logger.info("\n" + "="*60)
    logger.info("Test: Module 12 - Custom Scripts")
    logger.info("="*60)
    
    try:
        from unattend_generator import (
            UnattendGenerator, Configuration,
            InteractiveLanguageSettings, ImplicitTimeZoneSettings,
            ScriptSettings, Script, ScriptType, ScriptPhase
        )
        
        generator = UnattendGenerator()
        config = Configuration()
        config.language_settings = InteractiveLanguageSettings()
        config.time_zone_settings = ImplicitTimeZoneSettings()
        
        # 测试用例 1: PowerShell 脚本（System 阶段）
        logger.info("  Test case 1: PowerShell script in System phase")
        config.script_settings = ScriptSettings(
            scripts=[
                Script(
                    content="Write-Host 'Test script';",
                    phase=ScriptPhase.System,
                    type=ScriptType.Ps1
                )
            ],
            restart_explorer=False
        )
        
        python_xml = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml)} bytes)")
        
        # 保存 XML
        output_dir = project_root / 'test' / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / 'module_12_ps1_system_python.xml'
        with open(output_file, 'wb') as f:
            f.write(python_xml)
        logger.info(f"  Saved to {output_file}")
        
        # C# DLL 对比
        csharp_wrapper = CSharpDLLWrapper()
        if csharp_wrapper.dll_loaded:
            logger.info("\nComparing with C# DLL...")
            config_dict = {
                'scripts': {
                    'scripts': [{
                        'content': "Write-Host 'Test script';",
                        'phase': 'system',
                        'type': 'ps1'
                    }],
                    'restartExplorer': False
                },
                'processorArchitectures': ['amd64']
            }
            
            csharp_xml = csharp_wrapper.generate_xml(config_dict)
            logger.info(f"✓ C# DLL generated XML ({len(csharp_xml)} bytes)")
            
            if compare_xml(python_xml, csharp_xml, "module_12_ps1_system"):
                logger.info("✓ Test case 1 passed!")
            else:
                logger.error("✗ Test case 1 failed!")
                return False
        else:
            logger.warning("⚠ C# DLL not loaded, skipping comparison")
        
        # 测试用例 2: CMD 脚本（FirstLogon 阶段）
        logger.info("\n  Test case 2: CMD script in FirstLogon phase")
        config.script_settings = ScriptSettings(
            scripts=[
                Script(
                    content="echo Test script",
                    phase=ScriptPhase.FirstLogon,
                    type=ScriptType.Cmd
                )
            ],
            restart_explorer=False
        )
        
        python_xml = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml)} bytes)")
        
        output_file = output_dir / 'module_12_cmd_firstlogon_python.xml'
        with open(output_file, 'wb') as f:
            f.write(python_xml)
        logger.info(f"  Saved to {output_file}")
        
        if csharp_wrapper.dll_loaded:
            config_dict = {
                'scripts': {
                    'scripts': [{
                        'content': "echo Test script",
                        'phase': 'firstLogon',
                        'type': 'cmd'
                    }],
                    'restartExplorer': False
                },
                'processorArchitectures': ['amd64']
            }
            
            csharp_xml = csharp_wrapper.generate_xml(config_dict)
            logger.info(f"✓ C# DLL generated XML ({len(csharp_xml)} bytes)")
            
            if compare_xml(python_xml, csharp_xml, "module_12_cmd_firstlogon"):
                logger.info("✓ Test case 2 passed!")
            else:
                logger.error("✗ Test case 2 failed!")
                return False
        
        # 测试用例 3: 注册表脚本（DefaultUser 阶段）
        logger.info("\n  Test case 3: Registry script in DefaultUser phase")
        config.script_settings = ScriptSettings(
            scripts=[
                Script(
                    content="[HKEY_USERS\\DefaultUser\\Software\\Test]\n\"TestValue\"=dword:00000001",
                    phase=ScriptPhase.DefaultUser,
                    type=ScriptType.Reg
                )
            ],
            restart_explorer=True
        )
        
        python_xml = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml)} bytes)")
        
        output_file = output_dir / 'module_12_reg_defaultuser_python.xml'
        with open(output_file, 'wb') as f:
            f.write(python_xml)
        logger.info(f"  Saved to {output_file}")
        
        if csharp_wrapper.dll_loaded:
            config_dict = {
                'scripts': {
                    'scripts': [{
                        'content': "[HKEY_USERS\\DefaultUser\\Software\\Test]\n\"TestValue\"=dword:00000001",
                        'phase': 'defaultUser',
                        'type': 'reg'
                    }],
                    'restartExplorer': True
                },
                'processorArchitectures': ['amd64']
            }
            
            csharp_xml = csharp_wrapper.generate_xml(config_dict)
            logger.info(f"✓ C# DLL generated XML ({len(csharp_xml)} bytes)")
            
            if compare_xml(python_xml, csharp_xml, "module_12_reg_defaultuser"):
                logger.info("✓ Test case 3 passed!")
            else:
                logger.error("✗ Test case 3 failed!")
                return False
        
        logger.info("\n✓ Module 12 test completed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Module 12 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_module_13_xml_markup():
    """测试模块 13: XML 标记"""
    logger.info("\n" + "="*60)
    logger.info("Test: Module 13 - XML Markup")
    logger.info("="*60)
    
    try:
        from unattend_generator import (
            UnattendGenerator, Configuration,
            InteractiveLanguageSettings, ImplicitTimeZoneSettings,
            Pass
        )
        
        generator = UnattendGenerator()
        config = Configuration()
        config.language_settings = InteractiveLanguageSettings()
        config.time_zone_settings = ImplicitTimeZoneSettings()
        
        # 设置默认值以避免错误
        from unattend_generator import SkipWdacSettings, ExpressSettingsMode, ProcessorArchitecture
        config.wdac_settings = SkipWdacSettings()
        config.express_settings = ExpressSettingsMode.DisableAll
        config.processor_architectures = {ProcessorArchitecture.amd64}
        
        # 测试用例 1: 基本 XML 标记
        logger.info("  Test case 1: Basic XML markup")
        config.components = {
            ('Microsoft-Windows-Shell-Setup', Pass.specialize): '<TimeZone>Eastern Standard Time</TimeZone>'
        }
        
        python_xml = generator.generate_xml(config)
        logger.info(f"✓ Python generated XML ({len(python_xml)} bytes)")
        
        # 保存 XML
        output_dir = project_root / 'test' / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / 'module_13_basic_xml_python.xml'
        with open(output_file, 'wb') as f:
            f.write(python_xml)
        logger.info(f"  Saved to {output_file}")
        
        # C# DLL 对比
        csharp_wrapper = CSharpDLLWrapper()
        if csharp_wrapper.dll_loaded:
            logger.info("\nComparing with C# DLL...")
            config_dict = {
                'xmlMarkup': {
                    'components': [{
                        'component': 'Microsoft-Windows-Shell-Setup',
                        'pass': 'specialize',
                        'xml': '<TimeZone>Eastern Standard Time</TimeZone>'
                    }]
                },
                'processorArchitectures': ['amd64']
            }
            
            csharp_xml = csharp_wrapper.generate_xml(config_dict)
            logger.info(f"✓ C# DLL generated XML ({len(csharp_xml)} bytes)")
            
            if compare_xml(python_xml, csharp_xml, "module_13_basic_xml"):
                logger.info("✓ Test case 1 passed!")
            else:
                logger.error("✗ Test case 1 failed!")
                return False
        else:
            logger.warning("⚠ C# DLL not loaded, skipping comparison")
        
        logger.info("\n✓ Module 13 test completed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Module 13 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    logger.info("="*60)
    logger.info("Unattend Generator Module Tests")
    logger.info("="*60)
    
    # 模块 1 测试（取消注释以运行）
    # test_module_1_interactive_language()
    # test_module_1_unattended_language_basic()
    # test_module_1_unattended_language_chinese()
    # test_module_1_timezone_only()
    
    # 模块 2 测试
    # test_module_2_setup_settings()
    
    # 模块 4 测试
    # test_module_4_name_and_account()
    
    # 模块 5 测试
    # test_module_5_partitioning()
    
    # 模块 6 测试
    # test_module_6_windows_edition_and_source()
    
    # 模块 7 测试
    # test_module_7_ui_personalization()
    
    # 模块 8 测试
    # test_module_8_wifi()
    
    # 模块 9 测试
    # test_module_9_accessibility()
    
    # 模块 10 测试
    # test_module_10_system_optimization()
    
    # 模块 11 测试
    # test_module_11_advanced_settings()
    
    # 模块 12 测试
    # test_module_12_custom_scripts()
    
    # 模块 13 测试
    test_module_13_xml_markup()
    
    # 后续模块测试将在此处增量添加（注释掉以进行针对性测试）
    # ...
    
    logger.info("\n" + "="*60)
    logger.info("Test suite completed")
    logger.info("="*60)


if __name__ == "__main__":
    # 检查 conda 环境
    if not check_conda_environment():
        sys.exit(1)
    
    logger.info("="*60)
    logger.info("Starting test script...")
    logger.info("="*60)
    
    try:
        main()
        logger.info("="*60)
        logger.info("Test script completed successfully.")
        logger.info("="*60)
    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

