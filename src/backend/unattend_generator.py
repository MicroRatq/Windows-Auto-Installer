"""
Unattend XML Generator - Pure Python Implementation
参考 ref/unattend-generator C# 项目实现
"""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from xml.dom import minidom


# ========================================
# 枚举类型
# ========================================

class Pass(Enum):
    """Windows Setup Pass"""
    offlineServicing = "offlineServicing"
    windowsPE = "windowsPE"
    generalize = "generalize"
    specialize = "specialize"
    auditSystem = "auditSystem"
    auditUser = "auditUser"
    oobeSystem = "oobeSystem"


class ProcessorArchitecture(Enum):
    """处理器架构"""
    x86 = "x86"
    amd64 = "amd64"
    arm64 = "arm64"


class TaskbarSearchMode(Enum):
    """任务栏搜索模式"""
    Hide = 0
    Icon = 1
    Box = 2
    Label = 3


class HideModes(Enum):
    """隐藏文件模式"""
    Hidden = "hidden"
    HiddenSystem = "hiddenSystem"
    None_ = "none"


class InputType(Enum):
    """输入类型"""
    Keyboard = "Keyboard"
    IME = "IME"


class PartitionLayout(Enum):
    """分区布局"""
    MBR = "MBR"
    GPT = "GPT"


class RecoveryMode(Enum):
    """恢复模式"""
    None_ = "None"
    Folder = "Folder"
    Partition = "Partition"


class CompactOsModes(Enum):
    """Compact OS 模式"""
    Default = "Default"
    Always = "Always"
    Never = "Never"


# ========================================
# Constants 类
# ========================================

class Constants:
    """常量类，对应 C# 的 Constants 类"""
    UsersGroup = "Users"
    AdministratorsGroup = "Administrators"
    DefaultPassword = ""
    RecoveryPartitionSize = 1000
    EspDefaultSize = 300


# ========================================
# 数据类 - 对应 C# 的 IKeyed 接口
# ========================================

@dataclass
class IKeyed:
    """可查找的数据项基类"""
    id: str
    display_name: str


@dataclass
class ImageLanguage(IKeyed):
    """镜像语言"""
    pass


@dataclass
class UserLocale(IKeyed):
    """用户区域"""
    lcid: str
    keyboard_layout: Optional['KeyboardIdentifier'] = None
    geo_location: Optional['GeoLocation'] = None


@dataclass
class KeyboardIdentifier(IKeyed):
    """键盘标识符"""
    type: InputType = InputType.Keyboard


@dataclass
class TimeOffset(IKeyed):
    """时区偏移"""
    pass


@dataclass
class GeoLocation(IKeyed):
    """地理位置"""
    pass


@dataclass
class WindowsEdition(IKeyed):
    """Windows 版本"""
    product_key: Optional[str] = None
    index: Optional[int] = None


@dataclass
class Component(IKeyed):
    """组件"""
    passes: List[str] = field(default_factory=list)


# Bloatware 已在模块 11 中定义，这里删除重复定义


@dataclass
class DesktopIcon(IKeyed):
    """桌面图标"""
    guid: str = ""


@dataclass
class StartFolder(IKeyed):
    """开始菜单文件夹"""
    data: bytes = field(default_factory=lambda: b"")


# ========================================
# 语言设置和时区设置接口
# ========================================

class ILanguageSettings:
    """语言设置接口"""
    pass


class InteractiveLanguageSettings(ILanguageSettings):
    """交互式语言设置"""
    pass


@dataclass
class LocaleAndKeyboard:
    """区域和键盘组合"""
    locale: UserLocale
    keyboard: KeyboardIdentifier


@dataclass
class UnattendedLanguageSettings(ILanguageSettings):
    """无人值守语言设置"""
    image_language: ImageLanguage
    locale_and_keyboard: LocaleAndKeyboard
    locale_and_keyboard2: Optional[LocaleAndKeyboard] = None
    locale_and_keyboard3: Optional[LocaleAndKeyboard] = None
    geo_location: Optional[GeoLocation] = None
    has_winpe: bool = True  # 是否在 WinPE pass 中创建 component（默认 True，保持向后兼容）


class ITimeZoneSettings:
    """时区设置接口"""
    pass


class ImplicitTimeZoneSettings(ITimeZoneSettings):
    """隐式时区设置"""
    pass


@dataclass
class ExplicitTimeZoneSettings(ITimeZoneSettings):
    """显式时区设置"""
    time_zone: TimeOffset


# ========================================
# 模块 4: Name and Account 数据类
# ========================================

class IComputerNameSettings:
    """计算机名设置接口"""
    pass


class RandomComputerNameSettings(IComputerNameSettings):
    """随机计算机名设置"""
    pass


@dataclass
class CustomComputerNameSettings(IComputerNameSettings):
    """自定义计算机名设置"""
    computer_name: str
    
    def __post_init__(self):
        """验证计算机名"""
        self.computer_name = self._validate(self.computer_name)
    
    @staticmethod
    def _validate(name: Optional[str]) -> str:
        """验证计算机名（对应 C# 的 Validate 方法）"""
        if not name or not name.strip():
            raise ValueError(f"Computer name '{name}' is invalid.")
        
        if len(name) > 15:
            raise ValueError(f"Computer name '{name}' is invalid.")
        
        if any(c.isspace() for c in name):
            raise ValueError(f"Computer name '{name}' is invalid.")
        
        if all(c.isdigit() and ord(c) < 128 for c in name):
            raise ValueError(f"Computer name '{name}' is invalid.")
        
        invalid_chars = ['{', '|', '}', '~', '[', '\\', ']', '^', "'", ':', ';', '<', '=', '>', '?', '@', '!', '"', '#', '$', '%', '`', '(', ')', '+', '/', '.', ',', '*', '&']
        if any(c in invalid_chars for c in name):
            raise ValueError(f"Computer name '{name}' is invalid.")
        
        return name


@dataclass
class ScriptComputerNameSettings(IComputerNameSettings):
    """脚本计算机名设置"""
    script: str


class IAccountSettings:
    """账户设置接口"""
    pass


class InteractiveAccountSettings(IAccountSettings):
    """交互式账户设置基类"""
    pass


class InteractiveMicrosoftAccountSettings(InteractiveAccountSettings):
    """交互式 Microsoft 账户设置"""
    pass


class InteractiveLocalAccountSettings(InteractiveAccountSettings):
    """交互式本地账户设置"""
    pass


@dataclass
class Account:
    """账户数据类"""
    name: str
    display_name: str
    password: str
    group: str
    
    def __post_init__(self):
        """验证用户名"""
        self._validate_username()
    
    def _validate_username(self):
        """验证用户名（对应 C# 的 ValidateUsername 方法）"""
        if not self.name or not self.name.strip():
            raise ValueError(f"Username '{self.name}' is invalid.")
        
        if self.name != self.name.strip():
            raise ValueError(f"Username '{self.name}' is invalid.")
        
        if len(self.name) > 20:
            raise ValueError(f"Username '{self.name}' is invalid.")
        
        invalid_chars = ['/', '\\', '[', ']', ':', ';', '|', '=', ',', '+', '*', '?', '<', '>', '"', '%']
        if any(c in invalid_chars for c in self.name):
            raise ValueError(f"Username '{self.name}' is invalid.")
        
        if self.name.endswith('.'):
            raise ValueError(f"Username '{self.name}' is invalid.")
        
        existing = [
            "administrator",
            "guest",
            "defaultaccount",
            "system",
            "network service",
            "local service",
            "none",
            "wdagutilityaccount"
        ]
        
        if self.name.lower() in existing:
            raise ValueError(f"Username '{self.name}' is invalid.")


@dataclass
class UnattendedAccountSettings(IAccountSettings):
    """无人值守账户设置"""
    accounts: List[Account]
    auto_logon_settings: 'IAutoLogonSettings'
    obscure_passwords: bool
    
    def __post_init__(self):
        """验证账户设置"""
        self._check_administrator_account()
        self._check_unique_names()
    
    def _check_unique_names(self):
        """检查账户名唯一性（对应 C# 的 CheckUniqueNames 方法）"""
        name_counts = {}
        for account in self.accounts:
            name_lower = account.name.lower()
            if name_lower in name_counts:
                name_counts[name_lower].append(account.name)
            else:
                name_counts[name_lower] = [account.name]
        
        collisions = [names for names in name_counts.values() if len(names) > 1]
        if collisions:
            collision_str = ", ".join(f"'{name}'" for names in collisions for name in names)
            raise ValueError(f"Account name(s) {collision_str} specified more than once.")
    
    def _check_administrator_account(self):
        """检查管理员账户（对应 C# 的 CheckAdministratorAccount 方法）"""
        if isinstance(self.auto_logon_settings, BuiltinAutoLogonSettings):
            return
        
        for account in self.accounts:
            if account.group == Constants.AdministratorsGroup:
                return
        
        raise ValueError("Must have at least one administrator account.")


class IAutoLogonSettings:
    """自动登录设置接口"""
    pass


class NoneAutoLogonSettings(IAutoLogonSettings):
    """无自动登录设置"""
    pass


@dataclass
class BuiltinAutoLogonSettings(IAutoLogonSettings):
    """内置管理员自动登录设置"""
    password: str


class OwnAutoLogonSettings(IAutoLogonSettings):
    """自己的账户自动登录设置"""
    pass


class IPasswordExpirationSettings:
    """密码过期设置接口"""
    pass


class DefaultPasswordExpirationSettings(IPasswordExpirationSettings):
    """默认密码过期设置"""
    MaxAge = 42


class UnlimitedPasswordExpirationSettings(IPasswordExpirationSettings):
    """无限制密码过期设置"""
    pass


@dataclass
class CustomPasswordExpirationSettings(IPasswordExpirationSettings):
    """自定义密码过期设置"""
    max_age: int
    
    def __post_init__(self):
        """验证最大年龄"""
        if not (1 <= self.max_age <= 999):
            raise ValueError(f"MaxAge must be between 1 and 999, got {self.max_age}")


class ILockoutSettings:
    """账户锁定设置接口"""
    pass


class DefaultLockoutSettings(ILockoutSettings):
    """默认锁定设置"""
    pass


class DisableLockoutSettings(ILockoutSettings):
    """禁用锁定设置"""
    pass


@dataclass
class CustomLockoutSettings(ILockoutSettings):
    """自定义锁定设置"""
    lockout_threshold: int
    lockout_duration: int
    lockout_window: int
    
    def __post_init__(self):
        """验证锁定设置"""
        if not (0 <= self.lockout_threshold <= 999):
            raise ValueError(f"LockoutThreshold must be between 0 and 999, got {self.lockout_threshold}")
        
        if not (1 <= self.lockout_duration <= 99999):
            raise ValueError(f"LockoutDuration must be between 1 and 99999, got {self.lockout_duration}")
        
        if not (1 <= self.lockout_window <= 99999):
            raise ValueError(f"LockoutWindow must be between 1 and 99999, got {self.lockout_window}")
        
        if self.lockout_window > self.lockout_duration:
            raise ValueError(f"Value of 'LockoutWindow' ({self.lockout_window}) must be less or equal to value of 'LockoutDuration' ({self.lockout_duration}).")


# ========================================
# 模块 5: Partitioning and formatting 数据类
# ========================================

class IPartitionSettings:
    """分区设置接口"""
    pass


class InteractivePartitionSettings(IPartitionSettings):
    """交互式分区设置"""
    pass


class IInstallToSettings:
    """安装目标设置接口"""
    pass


class AvailableInstallToSettings(IInstallToSettings):
    """可用分区安装目标设置"""
    pass


@dataclass
class CustomInstallToSettings(IInstallToSettings):
    """自定义安装目标设置"""
    install_to_disk: int
    install_to_partition: int
    
    def __post_init__(self):
        """验证安装目标"""
        if self.install_to_disk < 0:
            raise ValueError(f"InstallToDisk must be >= 0, got {self.install_to_disk}")
        if self.install_to_partition < 1:
            raise ValueError(f"InstallToPartition must be >= 1, got {self.install_to_partition}")


@dataclass
class CustomPartitionSettings(IPartitionSettings):
    """自定义分区设置"""
    script: str
    install_to: IInstallToSettings


@dataclass
class UnattendedPartitionSettings(IPartitionSettings):
    """无人值守分区设置"""
    partition_layout: PartitionLayout
    recovery_mode: RecoveryMode
    esp_size: int = Constants.EspDefaultSize
    recovery_size: int = Constants.RecoveryPartitionSize


class IDiskAssertionSettings:
    """磁盘断言设置接口"""
    pass


class SkipDiskAssertionSettings(IDiskAssertionSettings):
    """跳过磁盘断言设置"""
    pass


@dataclass
class ScriptDiskAssertionsSettings(IDiskAssertionSettings):
    """脚本磁盘断言设置"""
    script: str


class IPESettings:
    """PE 设置接口"""
    pass


class DefaultPESettings(IPESettings):
    """默认 PE 设置"""
    pass


class ICmdPESettings(IPESettings):
    """CMD PE 设置接口"""
    pass


@dataclass
class GeneratePESettings(ICmdPESettings):
    """生成 PE 设置"""
    disable_8_dot3_names: bool
    pause_before_formatting: bool
    pause_before_reboot: bool


@dataclass
class ScriptPESettings(ICmdPESettings):
    """脚本 PE 设置"""
    script: str


# ========================================
# 模块 6: Windows Edition and Source 数据类
# ========================================

class IEditionSettings:
    """版本设置接口"""
    pass


class InteractiveEditionSettings(IEditionSettings):
    """交互式版本设置"""
    pass


class FirmwareEditionSettings(IEditionSettings):
    """固件版本设置"""
    pass


@dataclass
class UnattendedEditionSettings(IEditionSettings):
    """无人值守版本设置"""
    edition: WindowsEdition


@dataclass
class CustomEditionSettings(IEditionSettings):
    """自定义版本设置（产品密钥）"""
    product_key: str
    
    def __post_init__(self):
        """验证产品密钥格式"""
        import re
        if not re.match(r'^([A-Z0-9]{5}-){4}[A-Z0-9]{5}$', self.product_key):
            raise ValueError(f"Product key {self.product_key} is ill-formed.")


class IInstallFromSettings:
    """安装源设置接口"""
    pass


class AutomaticInstallFromSettings(IInstallFromSettings):
    """自动安装源设置"""
    pass


class KeyInstallFromSettings(IInstallFromSettings):
    """键值安装源设置基类"""
    key: str
    value: str


@dataclass
class IndexInstallFromSettings(KeyInstallFromSettings):
    """索引安装源设置"""
    index: int
    
    def __init__(self, index: int):
        self.index = index
        self.key = "/IMAGE/INDEX"
        self.value = str(index)


@dataclass
class NameInstallFromSettings(KeyInstallFromSettings):
    """名称安装源设置"""
    name: str
    
    def __init__(self, name: str):
        self.name = name
        self.key = "/IMAGE/NAME"
        self.value = name


# ========================================
# 模块 7: UI and Personalization 数据类
# ========================================

class IStartPinsSettings:
    """开始菜单固定项设置接口"""
    pass


class DefaultStartPinsSettings(IStartPinsSettings):
    """默认开始菜单固定项设置"""
    pass


class EmptyStartPinsSettings(IStartPinsSettings):
    """空开始菜单固定项设置"""
    pass


@dataclass
class CustomStartPinsSettings(IStartPinsSettings):
    """自定义开始菜单固定项设置"""
    json: str
    
    def __post_init__(self):
        """验证 JSON 格式"""
        import json
        try:
            json.loads(self.json)
        except json.JSONDecodeError:
            raise ValueError(f"The string '{self.json}' is not valid JSON.")


class IStartTilesSettings:
    """开始菜单磁贴设置接口"""
    pass


class DefaultStartTilesSettings(IStartTilesSettings):
    """默认开始菜单磁贴设置"""
    pass


class EmptyStartTilesSettings(IStartTilesSettings):
    """空开始菜单磁贴设置"""
    pass


@dataclass
class CustomStartTilesSettings(IStartTilesSettings):
    """自定义开始菜单磁贴设置"""
    xml: str


class ITaskbarIcons:
    """任务栏图标接口"""
    pass


class DefaultTaskbarIcons(ITaskbarIcons):
    """默认任务栏图标"""
    pass


class EmptyTaskbarIcons(ITaskbarIcons):
    """空任务栏图标"""
    pass


@dataclass
class CustomTaskbarIcons(ITaskbarIcons):
    """自定义任务栏图标"""
    xml: str


class IEffects:
    """视觉效果接口"""
    pass


class DefaultEffects(IEffects):
    """默认视觉效果"""
    pass


class BestPerformanceEffects(IEffects):
    """最佳性能视觉效果"""
    pass


class BestAppearanceEffects(IEffects):
    """最佳外观视觉效果"""
    pass


class Effect(Enum):
    """视觉效果枚举"""
    ControlAnimations = "ControlAnimations"
    AnimateMinMax = "AnimateMinMax"
    TaskbarAnimations = "TaskbarAnimations"
    DWMAeroPeekEnabled = "DWMAeroPeekEnabled"
    MenuAnimation = "MenuAnimation"
    TooltipAnimation = "TooltipAnimation"
    SelectionFade = "SelectionFade"
    DWMSaveThumbnailEnabled = "DWMSaveThumbnailEnabled"
    CursorShadow = "CursorShadow"
    ListviewShadow = "ListviewShadow"
    ThumbnailsOrIcon = "ThumbnailsOrIcon"
    ListviewAlphaSelect = "ListviewAlphaSelect"
    DragFullWindows = "DragFullWindows"
    ComboBoxAnimation = "ComboBoxAnimation"
    FontSmoothing = "FontSmoothing"
    ListBoxSmoothScrolling = "ListBoxSmoothScrolling"
    DropShadow = "DropShadow"


@dataclass
class CustomEffects(IEffects):
    """自定义视觉效果"""
    settings: Dict[Effect, bool]


class IDesktopIconSettings:
    """桌面图标设置接口"""
    pass


class DefaultDesktopIconSettings(IDesktopIconSettings):
    """默认桌面图标设置"""
    pass


@dataclass
class CustomDesktopIconSettings(IDesktopIconSettings):
    """自定义桌面图标设置"""
    settings: Dict[DesktopIcon, bool]


class IStartFolderSettings:
    """开始菜单文件夹设置接口"""
    pass


class DefaultStartFolderSettings(IStartFolderSettings):
    """默认开始菜单文件夹设置"""
    pass


@dataclass
class CustomStartFolderSettings(IStartFolderSettings):
    """自定义开始菜单文件夹设置"""
    settings: Dict[StartFolder, bool]


class IWallpaperSettings:
    """壁纸设置接口"""
    pass


class DefaultWallpaperSettings(IWallpaperSettings):
    """默认壁纸设置"""
    pass


@dataclass
class SolidWallpaperSettings(IWallpaperSettings):
    """纯色壁纸设置"""
    color: str  # HTML 颜色格式，如 "#FF0000"


@dataclass
class ScriptWallpaperSettings(IWallpaperSettings):
    """脚本壁纸设置"""
    script: str


class IColorSettings:
    """颜色设置接口"""
    pass


class DefaultColorSettings(IColorSettings):
    """默认颜色设置"""
    pass


class ColorTheme(Enum):
    """颜色主题"""
    Dark = 0
    Light = 1


@dataclass
class CustomColorSettings(IColorSettings):
    """自定义颜色设置"""
    system_theme: ColorTheme
    apps_theme: ColorTheme
    enable_transparency: bool
    accent_color_on_start: bool
    accent_color_on_borders: bool
    accent_color: str  # HTML 颜色格式


class ILockScreenSettings:
    """锁屏设置接口"""
    pass


class DefaultLockScreenSettings(ILockScreenSettings):
    """默认锁屏设置"""
    pass


@dataclass
class ScriptLockScreenSettings(ILockScreenSettings):
    """脚本锁屏设置"""
    script: str


# ========================================
# 模块 9: 辅助功能设置数据类
# ========================================

class LockKeyInitial(Enum):
    """锁定键初始状态"""
    Off = "Off"
    On = "On"


class LockKeyBehavior(Enum):
    """锁定键行为"""
    Toggle = "Toggle"
    Ignore = "Ignore"


@dataclass
class LockKeySetting:
    """锁定键设置"""
    initial: LockKeyInitial
    behavior: LockKeyBehavior


class ILockKeySettings:
    """锁定键设置接口"""
    pass


class SkipLockKeySettings(ILockKeySettings):
    """跳过锁定键设置"""
    pass


@dataclass
class ConfigureLockKeySettings(ILockKeySettings):
    """配置锁定键设置"""
    caps_lock: LockKeySetting
    num_lock: LockKeySetting
    scroll_lock: LockKeySetting


class StickyKeys(Enum):
    """粘滞键标志位（标志位枚举）"""
    HotKeyActive = 0x00000004
    Indicator = 0x00000020
    TriState = 0x00000080
    TwoKeysOff = 0x00000100
    AudibleFeedback = 0x00000040
    HotKeySound = 0x00000010


class IStickyKeysSettings:
    """粘滞键设置接口"""
    pass


class DefaultStickyKeysSettings(IStickyKeysSettings):
    """默认粘滞键设置"""
    pass


class DisabledStickyKeysSettings(IStickyKeysSettings):
    """禁用粘滞键设置"""
    pass


@dataclass
class CustomStickyKeysSettings(IStickyKeysSettings):
    """自定义粘滞键设置"""
    flags: set[StickyKeys]


# ========================================
# 模块 8: Wi-Fi 设置数据类
# ========================================

class WifiAuthentications(Enum):
    """Wi-Fi 认证方式"""
    Open = "Open"
    WPA2PSK = "WPA2PSK"
    WPA3SAE = "WPA3SAE"


class IWifiSettings:
    """Wi-Fi 设置接口"""
    pass


class SkipWifiSettings(IWifiSettings):
    """跳过 Wi-Fi 设置"""
    pass


class InteractiveWifiSettings(IWifiSettings):
    """交互式 Wi-Fi 设置"""
    pass


@dataclass
class UnattendedWifiSettings(IWifiSettings):
    """无人值守 Wi-Fi 设置"""
    ssid: str
    authentication: WifiAuthentications
    password: str
    hidden: bool = False


@dataclass
class FromProfileWifiSettings(IWifiSettings):
    """从配置文件 Wi-Fi 设置"""
    profile_path: str


# ========================================
# 模块 11: 高级设置数据类
# ========================================

class ExpressSettingsMode(Enum):
    """快速设置模式"""
    Interactive = "Interactive"
    EnableAll = "EnableAll"
    DisableAll = "DisableAll"


# ========================================
# 模块 11: 高级设置数据类 - Bloatware
# ========================================

class BloatwareStep:
    """预装软件步骤基类"""
    def __init__(self, applies_to: List[str]):
        self.applies_to = applies_to


class SelectorBloatwareStep(BloatwareStep):
    """带选择器的预装软件步骤"""
    def __init__(self, applies_to: List[str], selector: str):
        super().__init__(applies_to)
        self.selector = selector


class PackageBloatwareStep(SelectorBloatwareStep):
    """包移除步骤"""
    pass


class CapabilityBloatwareStep(SelectorBloatwareStep):
    """功能移除步骤"""
    pass


class OptionalFeatureBloatwareStep(SelectorBloatwareStep):
    """可选功能移除步骤"""
    pass


class CustomBloatwareStep(BloatwareStep):
    """自定义移除步骤"""
    pass


@dataclass
class Bloatware:
    """预装软件数据类（需要从 Bloatware.json 加载，i18n 适配）"""
    display_name: str
    token: Optional[str] = None
    steps: List[BloatwareStep] = field(default_factory=list)
    
    @property
    def id(self) -> str:
        """生成ID（对应C#的Id属性）"""
        if self.token:
            return f"Remove{self.token}"
        else:
            # 移除空格
            return f"Remove{self.display_name.replace(' ', '')}"


class IWdacSettings:
    """WDAC 设置接口"""
    pass


class SkipWdacSettings(IWdacSettings):
    """跳过 WDAC 设置"""
    pass


class WdacAuditModes(Enum):
    """WDAC 审计模式"""
    Auditing = "Auditing"
    AuditingOnBootFailure = "AuditingOnBootFailure"
    Enforcement = "Enforcement"


class WdacScriptModes(Enum):
    """WDAC 脚本模式"""
    Restricted = "Restricted"
    Unrestricted = "Unrestricted"


@dataclass
class ConfigureWdacSettings(IWdacSettings):
    """配置 WDAC 设置"""
    audit_mode: WdacAuditModes
    script_mode: WdacScriptModes


# ========================================
# 模块 12: 自定义脚本数据类
# ========================================

class ScriptType(Enum):
    """脚本类型"""
    Cmd = "Cmd"
    Ps1 = "Ps1"
    Reg = "Reg"
    Vbs = "Vbs"
    Js = "Js"


class ScriptPhase(Enum):
    """脚本阶段"""
    System = "System"  # 在系统上下文中运行，在创建用户账户之前
    FirstLogon = "FirstLogon"  # 在第一个用户登录时运行
    UserOnce = "UserOnce"  # 在用户首次登录时运行
    DefaultUser = "DefaultUser"  # 修改默认用户的注册表配置单元


@dataclass
class Script:
    """脚本数据类"""
    content: str
    phase: ScriptPhase
    type: ScriptType
    
    def __post_init__(self):
        """验证脚本类型是否允许在指定阶段使用"""
        allowed_types = self._get_allowed_types(self.phase)
        if self.type not in allowed_types:
            raise ValueError(f"Scripts in phase '{self.phase.value}' must not have type '{self.type.value}'.")
    
    @staticmethod
    def _get_allowed_types(phase: ScriptPhase) -> List[ScriptType]:
        """获取指定阶段允许的脚本类型"""
        if phase == ScriptPhase.DefaultUser:
            return [ScriptType.Reg, ScriptType.Cmd, ScriptType.Ps1]
        else:
            return list(ScriptType)
    
    @staticmethod
    def file_extension(script_type: ScriptType) -> str:
        """获取文件扩展名"""
        return '.' + script_type.value.lower()


@dataclass
class ScriptSettings:
    """脚本设置"""
    scripts: List[Script] = field(default_factory=list)
    restart_explorer: bool = False


# ========================================
# 模块 13: XML 标记数据类
# ========================================

@dataclass
class ComponentAndPass:
    """组件和 Pass（用于 XML 标记）"""
    component: str
    pass_: Pass
    
    def __post_init__(self):
        """验证组件名格式"""
        import re
        pattern = re.compile(r'^[a-z-]+$', re.IGNORECASE)
        if not pattern.match(self.component):
            raise ValueError(f"Component ID '{self.component}' contains illegal characters.")


# ========================================
# Configuration 数据类
# ========================================

@dataclass
class Configuration:
    """配置类，对应 C# 的 Configuration record"""
    # 语言设置
    language_settings: Optional[ILanguageSettings] = None
    
    # 账户设置
    account_settings: Any = None
    
    # 分区设置
    partition_settings: Any = None  # Optional[IPartitionSettings]
    
    # 安装目标设置（在 partition_settings 中，如果是 CustomPartitionSettings）
    # install_to_settings: Optional[IInstallToSettings] = None
    
    # 磁盘断言设置
    disk_assertion_settings: Any = None  # Optional[IDiskAssertionSettings]
    
    # PE 设置
    pe_settings: Any = None  # Optional[IPESettings]
    
    # Compact OS 模式
    compact_os_mode: CompactOsModes = CompactOsModes.Default
    
    # 安装源设置
    install_from_settings: Any = None
    
    # 版本设置
    edition_settings: Any = None
    
    # 锁定设置
    lockout_settings: Any = None
    
    # 密码过期设置
    password_expiration_settings: Any = None
    
    # 进程审计设置
    process_audit_settings: Any = None
    
    # 计算机名设置
    computer_name_settings: Any = None
    
    # 时区设置
    time_zone_settings: Optional[ITimeZoneSettings] = None
    
    # Wi-Fi 设置
    wifi_settings: Any = None
    
    # WDAC 设置
    wdac_settings: Any = None
    
    # 处理器架构
    processor_architectures: Set[ProcessorArchitecture] = field(default_factory=lambda: {ProcessorArchitecture.amd64})
    
    # 组件（模块 13: XML 标记）
    components: Dict[Tuple[str, Pass], str] = field(default_factory=lambda: {})
    
    # 预装软件
    bloatwares: List[Bloatware] = field(default_factory=list)
    
    # 快速设置
    express_settings: ExpressSettingsMode = ExpressSettingsMode.DisableAll
    
    # 脚本设置（模块 12）
    script_settings: Optional[ScriptSettings] = None
    
    # Extensions 设置（从 XML 解析的文件）
    extensions: Optional[Dict[str, Any]] = None
    
    # 锁定键设置
    lock_key_settings: Any = None
    
    # 布尔标志
    bypass_requirements_check: bool = False
    bypass_network_check: bool = False
    enable_long_paths: bool = False
    enable_remote_desktop: bool = False
    harden_system_drive_acl: bool = False
    delete_junctions: bool = False
    allow_power_shell_scripts: bool = False
    disable_last_access: bool = False
    prevent_automatic_reboot: bool = False
    disable_defender: bool = False
    disable_sac: bool = False
    disable_uac: bool = False
    disable_smart_screen: bool = False
    disable_system_restore: bool = False
    disable_fast_startup: bool = False
    turn_off_system_sounds: bool = False
    disable_app_suggestions: bool = False
    disable_widgets: bool = False
    vbox_guest_additions: bool = False
    vmware_tools: bool = False
    virtio_guest_tools: bool = False
    parallels_tools: bool = False
    prevent_device_encryption: bool = False
    classic_context_menu: bool = False
    left_taskbar: bool = False
    hide_task_view_button: bool = False
    show_file_extensions: bool = False
    show_all_tray_icons: bool = False
    hide_files: HideModes = HideModes.Hidden
    hide_edge_fre: bool = False
    disable_edge_startup_boost: bool = False
    make_edge_uninstallable: bool = False
    delete_edge_desktop_icon: bool = False
    launch_to_this_pc: bool = False
    disable_windows_update: bool = False
    disable_pointer_precision: bool = False
    delete_windows_old: bool = False
    disable_bing_results: bool = False
    use_configuration_set: bool = False
    hide_power_shell_windows: bool = False
    show_end_task: bool = False
    keep_sensitive_files: bool = False
    use_narrator: bool = False
    disable_core_isolation: bool = False
    
    # 任务栏搜索
    taskbar_search: TaskbarSearchMode = TaskbarSearchMode.Box
    
    # 开始菜单设置
    start_pins_settings: Any = None
    start_tiles_settings: Any = None
    
    # 任务栏图标
    taskbar_icons: Any = None
    
    # 视觉效果
    effects: Any = None
    
    # 桌面图标
    desktop_icons: Any = None
    
    # 粘滞键设置
    sticky_keys_settings: Any = None
    
    # 开始菜单文件夹设置
    start_folder_settings: Any = None


# ========================================
# XML 工具函数
# ========================================

def load_xml_template(template_path: Path) -> ET.ElementTree:
    """加载 XML 模板文件"""
    # 注册命名空间以便查找
    ET.register_namespace('', 'urn:schemas-microsoft-com:unattend')
    ET.register_namespace('wcm', 'http://schemas.microsoft.com/WMIConfig/2002/State')
    tree = ET.parse(template_path)
    # 确保 tree 有 root
    root = tree.getroot()
    if root is None:
        raise ValueError(f"XML template {template_path} has no root element")
    # 类型检查器认为 ElementTree 可能返回 None，但实际上 parse 不会返回 None
    # 我们已经检查了 root 不为 None，所以这里可以安全返回
    return tree  # type: ignore[return-value]


def get_namespace_map() -> Dict[str, str]:
    """获取命名空间映射"""
    return {
        'u': 'urn:schemas-microsoft-com:unattend',
        'wcm': 'http://schemas.microsoft.com/WMIConfig/2002/State'
    }


def get_or_create_element(
    root: ET.Element,
    pass_name: Pass,
    component_name: str,
    element_name: Optional[str] = None
) -> ET.Element:
    """获取或创建元素（对应 C# 的 Util.GetOrCreateElement）"""
    ns = get_namespace_map()
    ns_uri = ns['u']
    
    # 查找或创建 settings 元素
    # 注意：XML 中可能使用默认命名空间，需要处理
    settings_xpath = f".//{{urn:schemas-microsoft-com:unattend}}settings[@pass='{pass_name.value}']"
    settings = root.find(settings_xpath)
    if settings is None:
        # 尝试不使用命名空间查找
        for elem in root.findall('.//settings'):
            if elem.get('pass') == pass_name.value:
                settings = elem
                break
        
        if settings is None:
            settings = ET.SubElement(root, f"{{{ns_uri}}}settings")
            settings.set("pass", pass_name.value)
    
    # 查找或创建 component 元素
    component_xpath = f".//{{urn:schemas-microsoft-com:unattend}}component[@name='{component_name}']"
    component = settings.find(component_xpath)
    if component is None:
        # 尝试不使用命名空间查找
        for elem in settings.findall('.//component'):
            if elem.get('name') == component_name:
                component = elem
                break
        
        if component is None:
            component = ET.SubElement(settings, f"{{{ns_uri}}}component")
            component.set("name", component_name)
            component.set("processorArchitecture", "x86")
            component.set("publicKeyToken", "31bf3856ad364e35")
            component.set("language", "neutral")
            component.set("versionScope", "nonSxS")
    
    # 如果需要查找子元素
    if element_name:
        # 只在直接子元素中查找，不使用递归查找
        element = None
        for child in component:
            if child.tag == f"{{{ns_uri}}}{element_name}":
                element = child
                break
        
        if element is None:
            element = ET.SubElement(component, f"{{{ns_uri}}}{element_name}")
        return element
    
    return component


def new_simple_element(
    name: str,
    parent: ET.Element,
    inner_text: str
) -> ET.Element:
    """创建简单元素（对应 C# 的 Util.NewSimpleElement）"""
    ns_uri = 'urn:schemas-microsoft-com:unattend'
    element = ET.SubElement(parent, f"{{{ns_uri}}}{name}")
    element.text = inner_text
    return element


def new_element(
    name: str,
    parent: ET.Element
) -> ET.Element:
    """创建元素（对应 C# 的 Util.NewElement）"""
    ns_uri = 'urn:schemas-microsoft-com:unattend'
    element = ET.SubElement(parent, f"{{{ns_uri}}}{name}")
    return element


def serialize_xml(tree: ET.ElementTree) -> bytes:
    """序列化 XML 为字节数组（对应 C# 的 Serialize 方法）"""
    root = tree.getroot()
    if root is None:
        raise ValueError("XML tree has no root element")

    # 在序列化前规范 Extensions 区域的换行格式（与参考 XML 保持一致）
    s_uri = "https://schneegans.de/windows/unattend-generator/"
    extensions = root.find(f"{{{s_uri}}}Extensions") if root is not None else None
    if extensions is not None:
        extract_script_elem = extensions.find(f"{{{s_uri}}}ExtractScript")
        if extract_script_elem is not None and extract_script_elem.text is not None:
            body = extract_script_elem.text.rstrip("\r\n")
            extract_script_elem.text = f"\n{body}\n\t\t"
        for file_elem in extensions.findall(f"{{{s_uri}}}File"):
            if file_elem.text:
                body = file_elem.text.rstrip("\r\n")
                file_elem.text = f"\n{body}\n\t\t"
    
    # 使用 minidom 进行格式化
    xml_str = ET.tostring(root, encoding='unicode', method='xml')
    dom = minidom.parseString(xml_str)
    
    # 格式化（使用制表符缩进，Windows 换行）
    pretty_xml = dom.toprettyxml(indent='\t', encoding=None)
    
    # 移除 minidom 自动添加的 XML 声明（我们手动添加）
    if pretty_xml.startswith('<?xml'):
        lines = pretty_xml.split('\n')
        pretty_xml = '\n'.join(lines[1:])
    
    # 移除无效的命名空间声明（如 xmlns:ns2="{...}"）
    import re
    pretty_xml = re.sub(r'\s+xmlns:ns\d+="\{[^"]+\}"', '', pretty_xml)
    # 移除命名空间前缀（如 ns2:settings -> settings）
    pretty_xml = re.sub(r'<ns\d+:', '<', pretty_xml)
    pretty_xml = re.sub(r'</ns\d+:', '</', pretty_xml)
    
    # 将 &quot; 替换为 "（在文本内容中，引号不需要转义）
    # 注意：在属性值中，如果属性值本身用双引号包围，内部的双引号需要转义
    # 但 minidom 会自动处理属性值的转义，我们只需要处理文本内容中的 &quot;
    # 使用正则表达式替换文本内容中的 &quot;，但要避免替换属性值中的
    # 简单方法：替换所有 &quot; 为 "，因为 minidom 会在需要时重新转义
    pretty_xml = pretty_xml.replace('&quot;', '"')
    
    # 将自闭合的 settings 标签展开为显式的开始/结束标签，匹配参考 XML
    for pass_name in ["offlineServicing", "generalize", "auditSystem", "auditUser"]:
        pretty_xml = pretty_xml.replace(f'<settings pass="{pass_name}"/>', f'<settings pass="{pass_name}"></settings>')

    # 展开常见的空标签以匹配参考格式
    pretty_xml = pretty_xml.replace('<DisplayName/>', '<DisplayName></DisplayName>')

    # 将十进制的字符引用替换为十六进制形式（例如 &#24038; -> &#x5de6;）
    def _dec_to_hex_entity(match):
        codepoint = int(match.group(1))
        return f'&#x{codepoint:X};'
    pretty_xml = re.sub(r'&#(\d+);', _dec_to_hex_entity, pretty_xml)
    
    # 添加 XML 声明（UTF-8 编码，但实际使用 ASCII）
    xml_bytes = ('<?xml version="1.0" encoding="utf-8"?>\r\n' + pretty_xml).encode('ascii', errors='xmlcharrefreplace')

    # 将编码阶段产生的十进制字符引用转换为十六进制形式
    import re as _re
    def _dec_entity_to_hex(m: 're.Match[bytes]') -> bytes:
        codepoint = int(m.group(1))
        return f'&#x{codepoint:X};'.encode('ascii')
    xml_bytes = _re.sub(br'&#(\d+);', _dec_entity_to_hex, xml_bytes)
    
    # 替换换行符为 Windows 格式
    xml_bytes = xml_bytes.replace(b'\n', b'\r\n')
    
    return xml_bytes


# ========================================
# 数据加载函数（支持 i18n）
# ========================================

def load_data_with_i18n(
    data_file: Path,
    lang: str = 'en',
    data_type: str = 'generic'
) -> List[Dict[str, Any]]:
    """加载数据文件并应用 i18n"""
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 如果数据是列表
    if isinstance(data, list):
        for item in data:
            # 尝试获取对应语言的显示名称
            display_name_key = f'DisplayName_{lang}' if lang != 'en' else 'DisplayName'
            if display_name_key in item:
                item['DisplayName'] = item[display_name_key]
            elif 'DisplayName' not in item:
                # 如果没有显示名称，使用 ID
                item['DisplayName'] = item.get('Id', '')
    
    return data


def to_keyed_dictionary(data_list: List[Dict[str, Any]], keyed_class: type) -> Dict[str, Any]:
    """将数据列表转换为字典（对应 C# 的 ToKeyedDictionary）"""
    result = {}
    for item in data_list:
        key = item.get('Id', '')
        if key:
            # 根据 keyed_class 类型创建相应的对象
            if keyed_class == ImageLanguage:
                result[key] = ImageLanguage(id=key, display_name=item.get('DisplayName', ''))
            elif keyed_class == UserLocale:
                # UserLocale 的加载在 _load_data 中单独处理，因为需要引用其他对象
                # 这里不应该被调用
                raise ValueError("UserLocale should be loaded separately in _load_data with proper converter support")
            elif keyed_class == KeyboardIdentifier:
                input_type_str = item.get('Type', 'Keyboard')
                input_type = InputType.Keyboard if input_type_str == 'Keyboard' else InputType.IME
                result[key] = KeyboardIdentifier(
                    id=key,
                    display_name=item.get('DisplayName', ''),
                    type=input_type
                )
            elif keyed_class == TimeOffset:
                result[key] = TimeOffset(id=key, display_name=item.get('DisplayName', ''))
            elif keyed_class == GeoLocation:
                result[key] = GeoLocation(id=key, display_name=item.get('DisplayName', ''))
            elif keyed_class == WindowsEdition:
                result[key] = WindowsEdition(
                    id=key,
                    display_name=item.get('DisplayName', ''),
                    product_key=item.get('ProductKey'),
                    index=item.get('Index')
                )
            elif keyed_class == Component:
                result[key] = Component(
                    id=key,
                    display_name=item.get('DisplayName', ''),
                    passes=item.get('Passes', [])
                )
            elif keyed_class == Bloatware:
                result[key] = Bloatware(display_name=item.get('DisplayName', ''))
            else:
                # 通用处理
                result[key] = keyed_class(id=key, display_name=item.get('DisplayName', ''))
    
    return result


# ========================================
# Modifier 基类
# ========================================

@dataclass
# ========================================
# 脚本序列类
# ========================================

class PowerShellSequence:
    """PowerShell 脚本序列基类（对应 C# 的 PowerShellSequence）"""
    
    def __init__(self):
        self._needs_explorer_restart = False
        self._commands: List[str] = []
    
    def append(self, command: str):
        """添加命令"""
        self._commands.append(command)
    
    def invoke_file(self, file: str):
        """调用文件"""
        self.append(f"Get-Content -LiteralPath '{file}' -Raw | Invoke-Expression;")
    
    def restart_explorer(self):
        """标记需要重启 Explorer"""
        self._needs_explorer_restart = True
    
    @property
    def is_empty(self) -> bool:
        """是否为空"""
        return len(self._commands) == 0
    
    def _activity(self) -> str:
        """活动名称（子类需要实现）"""
        raise NotImplementedError("Subclass must implement _activity()")
    
    def _log_file(self) -> str:
        """日志文件路径（子类需要实现）"""
        raise NotImplementedError("Subclass must implement _log_file()")
    
    def get_script(self) -> str:
        """获取完整脚本"""
        writer = []
        
        def write_script_block(command: str):
            """写入脚本块"""
            lines = command.split('\n')
            writer.append("\t{")
            for line in lines:
                writer.append(f"\t\t{line}")
            writer.append("\t};")
        
        writer.append("$scripts = @(")
        for command in self._commands:
            write_script_block(command)
        
        if self._needs_explorer_restart:
            # RestartExplorer.ps1 脚本内容
            restart_script = """
$ErrorActionPreference = 'Stop';
$process = Get-Process -Name 'explorer' -ErrorAction 'SilentlyContinue';
if ($process) {
    Stop-Process -Name 'explorer' -Force;
    Start-Sleep -Seconds 2;
}
Start-Process -FilePath 'explorer.exe';
"""
            write_script_block(restart_script.strip())
        
        writer.append(");")
        writer.append("")
        
        activity = self._activity()
        log_file = self._log_file()
        
        writer.append(f'''      & {{
        [float] $complete = 0;
        [float] $increment = 100 / $scripts.Count;
        foreach( $script in $scripts ) {{
          Write-Progress -Activity '{activity} Do not close this window.' -PercentComplete $complete;
          '*** Will now execute command «{{0}}».' -f $(
            $str = $script.ToString().Trim() -replace '\\s+', ' ';
            $max = 100;
            if( $str.Length -le $max ) {{
              $str;
            }} else {{
              $str.Substring( 0, $max - 1 ) + '…';
            }}
          );
          $start = [datetime]::Now;
          & $script;
          '*** Finished executing command after {{0:0}} ms.' -f [datetime]::Now.Subtract( $start ).TotalMilliseconds;
          "`r`n" * 3;
          $complete += $increment;
        }}
      }} *>&1 | Out-String -Width 1KB -Stream >> "{log_file}";
      ''')
        
        return '\n'.join(writer)


class SpecializeSequence(PowerShellSequence):
    """Specialize pass 的 PowerShell 脚本序列"""
    
    def _activity(self) -> str:
        return "Running scripts to customize your Windows installation."
    
    def _log_file(self) -> str:
        return r"C:\Windows\Setup\Scripts\Specialize.log"


class FirstLogonSequence(PowerShellSequence):
    """首次登录的 PowerShell 脚本序列"""
    
    def _activity(self) -> str:
        return "Running scripts to finalize your Windows installation."
    
    def _log_file(self) -> str:
        return r"C:\Windows\Setup\Scripts\FirstLogon.log"


class UserOnceSequence(PowerShellSequence):
    """用户首次登录的 PowerShell 脚本序列"""
    
    def _activity(self) -> str:
        return "Running scripts to configure this user account."
    
    def _log_file(self) -> str:
        return r"$env:TEMP\UserOnce.log"


class DefaultUserSequence(PowerShellSequence):
    """默认用户注册表的脚本序列"""
    
    def _activity(self) -> str:
        return "Running scripts to modify the default user's registry hive."
    
    def _log_file(self) -> str:
        return r"C:\Windows\Setup\Scripts\DefaultUser.log"


# ========================================
# CommandConfig 和 CommandAppender
# ========================================

class CommandConfig:
    """命令配置基类（对应 C# 的 CommandConfig）"""
    
    @staticmethod
    def windows_pe():
        """WindowsPE 命令配置"""
        return WindowsPECommandConfig()
    
    @staticmethod
    def specialize():
        """Specialize 命令配置"""
        return SpecializeCommandConfig()
    
    @staticmethod
    def oobe():
        """OOBE 命令配置"""
        return OobeCommandConfig()
    
    def create_element(self, root: ET.Element, ns_map: Dict[str, str]) -> ET.Element:
        """创建元素（子类需要实现）"""
        raise NotImplementedError("Subclass must implement create_element()")


class WindowsPECommandConfig(CommandConfig):
    """WindowsPE 命令配置"""
    
    def create_element(self, root: ET.Element, ns_map: Dict[str, str]) -> ET.Element:
        """创建 WindowsPE 命令元素"""
        ns_uri = ns_map['u']
        wcm_uri = ns_map['wcm']
        container = get_or_create_element(
            root,
            Pass.windowsPE,
            "Microsoft-Windows-Setup",
            "RunSynchronous"
        )
        # 计算当前序号（已有子元素数量 + 1）
        current = sum(1 for child in container if child.tag == f"{{{ns_uri}}}RunSynchronousCommand")
        outer = new_element("RunSynchronousCommand", container)
        outer.set(f"{{{wcm_uri}}}action", "add")
        order_elem = new_element("Order", outer)
        order_elem.text = str(current + 1)
        return new_element("Path", outer)


class SpecializeCommandConfig(CommandConfig):
    """Specialize 命令配置"""
    
    def create_element(self, root: ET.Element, ns_map: Dict[str, str]) -> ET.Element:
        """创建 Specialize 命令元素"""
        ns_uri = ns_map['u']
        wcm_uri = ns_map['wcm']
        container = get_or_create_element(
            root,
            Pass.specialize,
            "Microsoft-Windows-Deployment",
            "RunSynchronous"
        )
        current = sum(1 for child in container if child.tag == f"{{{ns_uri}}}RunSynchronousCommand")
        outer = new_element("RunSynchronousCommand", container)
        outer.set(f"{{{wcm_uri}}}action", "add")
        order_elem = new_element("Order", outer)
        order_elem.text = str(current + 1)
        return new_element("Path", outer)


class OobeCommandConfig(CommandConfig):
    """OOBE 命令配置"""
    
    def create_element(self, root: ET.Element, ns_map: Dict[str, str]) -> ET.Element:
        """创建 OOBE 命令元素"""
        ns_uri = ns_map['u']
        wcm_uri = ns_map['wcm']
        container = get_or_create_element(
            root,
            Pass.oobeSystem,
            "Microsoft-Windows-Shell-Setup",
            "FirstLogonCommands"
        )
        current = sum(1 for child in container if child.tag == f"{{{ns_uri}}}SynchronousCommand")
        outer = new_element("SynchronousCommand", container)
        outer.set(f"{{{wcm_uri}}}action", "add")
        order_elem = new_element("Order", outer)
        order_elem.text = str(current + 1)
        return new_element("CommandLine", outer)


class CommandAppender:
    """命令追加器（对应 C# 的 CommandAppender）"""
    
    def __init__(self, root: ET.Element, ns_map: Dict[str, str], config: CommandConfig):
        self.root = root
        self.ns_map = ns_map
        self.config = config
    
    def append(self, value: str):
        """追加命令"""
        elem = self.config.create_element(self.root, self.ns_map)
        elem.text = value
    
    def append_multiple(self, values: List[str]):
        """追加多个命令"""
        for value in values:
            self.append(value)


# ========================================
# CommandBuilder
# ========================================

class CommandBuilder:
    """命令构建器（对应 C# 的 CommandBuilder）"""
    
    def __init__(self, hide_power_shell_windows: bool):
        self.hide_power_shell_windows = hide_power_shell_windows
    
    def raw(self, command: str) -> str:
        """原始命令"""
        return command
    
    def shell_command(self, command: str) -> str:
        """Shell 命令"""
        return f'cmd.exe /c "{command}"'
    
    def registry_command(self, value: str) -> str:
        """注册表命令"""
        return f"reg.exe {value}"
    
    def powershell_command(self, value: str) -> str:
        """PowerShell 命令"""
        # 检查是否包含引号
        if '"' in value:
            raise ValueError(f"PowerShell command '{value}' must not contain '\"'.")
        
        # 检查是否以分号或大括号结尾
        if not (value.endswith(';') or value.endswith('}')):
            raise ValueError(f"PowerShell command '{value}' must end with either ';' or '}}'.")
        
        window_style = "Hidden" if self.hide_power_shell_windows else "Normal"
        return f'powershell.exe -WindowStyle "{window_style}" -NoProfile -Command "{value}"'
    
    def invoke_power_shell_script(self, filepath: str) -> str:
        """调用 PowerShell 脚本"""
        window_style = "Hidden" if self.hide_power_shell_windows else "Normal"
        return f'powershell.exe -WindowStyle "{window_style}" -ExecutionPolicy "Unrestricted" -NoProfile -File "{filepath}"'
    
    def invoke_vbscript(self, filepath: str) -> str:
        """调用 VBScript"""
        return f'cscript.exe //E:vbscript "{filepath}"'
    
    def invoke_jscript(self, filepath: str) -> str:
        """调用 JScript"""
        return f'cscript.exe //E:jscript "{filepath}"'
    
    def write_to_file_pe(self, path: str, lines: List[str]) -> List[str]:
        """写入文件到 PE（WindowsPE 环境）"""
        # 去除空行并修剪
        trimmed = [line.strip() for line in lines if line.strip()]
        
        # 转义特殊字符
        def escape(line: str) -> str:
            return (line
                .replace("^", "^^")
                .replace("&", "^&")
                .replace("<", "^<")
                .replace(">", "^>")
                .replace("|", "^|")
                .replace("%", "^%")
                .replace(")", "^)")
                .replace('"', '^"'))
        
        escaped = [escape(line) for line in trimmed]
        
        # 添加 echo:
        echoed = [f"echo:{line}" for line in escaped]
        
        max_line_length = 255
        result = []
        segments = echoed
        
        while segments:
            prev = None
            current = None
            for take in range(1, len(segments) + 1):
                segment_str = '&'.join(segments[:take])
                current = f'cmd.exe /c ">>"{path}" ({segment_str})"'
                if len(current) > max_line_length:
                    if prev is None:
                        raise ValueError(f"Line '{current}' is too long. You need to add line breaks to your input to make it shorter.")
                    else:
                        result.append(prev)
                        segments = segments[take - 1:]
                        current = None
                        break
                else:
                    prev = current
            
            if current is not None:
                result.append(current)
                segments = []
        
        return result


class ModifierContext:
    """Modifier 上下文（对应 C# 的 ModifierContext）"""
    document: ET.ElementTree
    root: ET.Element
    configuration: Configuration
    generator: 'UnattendGenerator'
    specialize_script: SpecializeSequence
    first_logon_script: FirstLogonSequence
    user_once_script: UserOnceSequence
    default_user_script: DefaultUserSequence
    command_builder: CommandBuilder


class Modifier:
    """Modifier 基类（对应 C# 的 Modifier 抽象类）"""
    
    def __init__(self, context: ModifierContext):
        self.context = context
        self.document = context.document
        self.root = context.root
        self.configuration = context.configuration
        self.generator = context.generator
        self.specialize_script = context.specialize_script
        self.first_logon_script = context.first_logon_script
        self.user_once_script = context.user_once_script
        self.default_user_script = context.default_user_script
        self.command_builder = context.command_builder
    
    def process(self):
        """处理配置（子类需要实现）"""
        raise NotImplementedError("Subclass must implement process()")
    
    def get_or_create_element(
        self,
        pass_name: Pass,
        component_name: str,
        element_name: Optional[str] = None
    ) -> ET.Element:
        """获取或创建元素"""
        return get_or_create_element(self.root, pass_name, component_name, element_name)
    
    def new_simple_element(
        self,
        name: str,
        parent: ET.Element,
        inner_text: str
    ) -> ET.Element:
        """创建简单元素"""
        return new_simple_element(name, parent, inner_text)
    
    def new_element(
        self,
        name: str,
        parent: ET.Element
    ) -> ET.Element:
        """创建元素"""
        return new_element(name, parent)
    
    def find_element(self, xpath: str) -> Optional[ET.Element]:
        """查找元素（使用 XPath）"""
        ns = get_namespace_map()
        ns_uri = ns['u']
        # 替换命名空间前缀
        xpath = xpath.replace('u:', f'{{{ns_uri}}}')
        # 如果使用绝对路径（以 // 开头），需要从根元素开始查找
        if xpath.startswith('//'):
            # 使用 iter 查找所有匹配的元素，返回第一个
            tag_name = xpath[2:]  # 移除 //
            for elem in self.root.iter():
                if elem.tag == tag_name:
                    return elem
            return None
        else:
            return self.root.find(xpath)
    
    def find_element_or_throw(self, xpath: str) -> ET.Element:
        """查找元素，如果不存在则抛出异常"""
        elem = self.find_element(xpath)
        if elem is None:
            raise ValueError(f"Element not found: {xpath}")
        return elem
    
    def _find_parent(self, root: ET.Element, target: ET.Element) -> Optional[ET.Element]:
        """查找元素的父元素（xml.etree.ElementTree 没有 parent 属性）"""
        for parent in root.iter():
            if target in parent:
                return parent
        return None
    
    def remove_element(self, elem: ET.Element):
        """移除元素"""
        parent = self._find_parent(self.root, elem)
        if parent is not None:
            parent.remove(elem)
    
    def get_appender(self, config: CommandConfig) -> CommandAppender:
        """获取命令追加器（对应 C# 的 GetAppender）"""
        ns_map = get_namespace_map()
        return CommandAppender(self.root, ns_map, config)
    
    def add_text_file(self, name: str, content: str) -> str:
        """添加文本文件（对应 C# 的 AddTextFile）"""
        destination = f"C:\\Windows\\Setup\\Scripts\\{name}"
        self._add_file(content, destination)
        return destination
    
    def _add_file(self, content: str, path: str):
        """添加文件到 XML Extensions 部分（对应 C# 的 AddFile）"""
        import logging
        logger = logging.getLogger('UnattendGenerator')
        
        ns = get_namespace_map()
        ns_uri = ns['u']
        s_uri = "https://schneegans.de/windows/unattend-generator/"  # Constants.MyNamespaceUri
        
        logger.debug(f"Modifier._add_file: Adding file to Extensions: path={path}, content_length={len(content)}")
        
        # 查找或创建 Extensions 元素
        extensions = self.root.find(f".//{{{s_uri}}}Extensions")
        if extensions is None:
            extensions = ET.Element(f"{{{s_uri}}}Extensions")
            self.root.append(extensions)
            
            # 创建 ExtractScript 元素（首次创建 Extensions 时需要）
            extract_script = ET.Element(f"{{{s_uri}}}ExtractScript")
            # ExtractScript 的内容（与 C# 版本匹配）
            extract_script_text = """param(
    [xml] $Document
);

foreach( $file in $Document.unattend.Extensions.File ) {
    $path = [System.Environment]::ExpandEnvironmentVariables( $file.GetAttribute( 'path' ) );
    mkdir -Path( $path | Split-Path -Parent ) -ErrorAction 'SilentlyContinue';
    $encoding = switch( [System.IO.Path]::GetExtension( $path ) ) {
        { $_ -in '.ps1', '.xml' } { [System.Text.Encoding]::UTF8; }
        { $_ -in '.reg', '.vbs', '.js' } { [System.Text.UnicodeEncoding]::new( $false, $true ); }
        default { [System.Text.Encoding]::Default; }
    };
    $bytes = $encoding.GetPreamble() + $encoding.GetBytes( $file.InnerText.Trim() );
    [System.IO.File]::WriteAllBytes( $path, $bytes );
}"""
            extract_script.text = extract_script_text
            extensions.append(extract_script)
        
        # 创建 File 元素
        file_elem = ET.Element(f"{{{s_uri}}}File")
        file_elem.set("path", path)
        file_elem.text = content
        extensions.append(file_elem)


# ========================================
# Modifier 实现
# ========================================

class LocalesModifier(Modifier):
    """语言设置 Modifier（对应 C# 的 LocalesModifier）"""
    
    def process(self):
        """处理语言设置"""
        ns = get_namespace_map()
        ns_uri = ns['u']
        
        lang_settings = self.configuration.language_settings
        
        if isinstance(lang_settings, UnattendedLanguageSettings):
            # 无人值守模式
            settings = lang_settings
            
            # 只有在 has_winpe 为 True 时才创建 WinPE component
            component_pe = None
            if settings.has_winpe:
                component_pe = get_or_create_element(
                    self.root,
                    Pass.windowsPE,
                    "Microsoft-Windows-International-Core-WinPE"
                )
            else:
                # 如果 has_winpe 为 False，移除模板中可能已存在的 WinPE component
                existing_pe = self.root.find(f".//{{{ns_uri}}}component[@name='Microsoft-Windows-International-Core-WinPE']")
                if existing_pe is not None:
                    parent_pe = self._find_parent(self.root, existing_pe)
                    if parent_pe is not None:
                        parent_pe.remove(existing_pe)
            
            # 总是创建 OOBE component
            component_oobe = get_or_create_element(
                self.root,
                Pass.oobeSystem,
                "Microsoft-Windows-International-Core"
            )
            
            # 构建键盘列表
            keyboard_pairs = [
                settings.locale_and_keyboard,
                settings.locale_and_keyboard2,
                settings.locale_and_keyboard3
            ]
            
            keyboard_strings = []
            for pair in keyboard_pairs:
                if pair is None:
                    continue
                
                if pair.keyboard.type == InputType.IME:
                    keyboard_strings.append(pair.keyboard.id)
                elif pair.locale.lcid == "1000":
                    # 未指定的区域，需要查找替换
                    replacement_locale = self._get_replacement_for_unspecified_locale(
                        settings.image_language.id,
                        pair.locale
                    )
                    keyboard_strings.append(f"{replacement_locale.lcid}:{pair.keyboard.id}")
                else:
                    # 检查键盘 ID 是否已经包含 lcid（以数字开头，如 "0804:..."）
                    keyboard_id = pair.keyboard.id
                    if keyboard_id and keyboard_id[0].isdigit() and ':' in keyboard_id:
                        # 键盘 ID 已经包含 lcid，直接使用
                        keyboard_strings.append(keyboard_id)
                    else:
                        # 键盘 ID 不包含 lcid，添加 locale lcid 前缀
                        keyboard_strings.append(f"{pair.locale.lcid}:{keyboard_id}")
            
            keyboards = ";".join(keyboard_strings)
            
            # 设置 WinPE 组件（如果存在）
            if component_pe is not None:
                ui_lang_pe = component_pe.find(f"{{{ns_uri}}}UILanguage")
                if ui_lang_pe is None:
                    ui_lang_pe = ET.SubElement(component_pe, f"{{{ns_uri}}}UILanguage")
                ui_lang_pe.text = settings.image_language.id
            
            # 设置 OOBE 组件（按照原始 XML 的顺序：InputLocale, SystemLocale, UILanguage, UserLocale）
            # 先查找或创建所有元素
            input_locale = component_oobe.find(f"{{{ns_uri}}}InputLocale")
            system_locale = component_oobe.find(f"{{{ns_uri}}}SystemLocale")
            ui_lang_oobe = component_oobe.find(f"{{{ns_uri}}}UILanguage")
            user_locale = component_oobe.find(f"{{{ns_uri}}}UserLocale")
            
            # 如果元素不存在，按顺序创建
            if input_locale is None:
                input_locale = ET.SubElement(component_oobe, f"{{{ns_uri}}}InputLocale")
            input_locale.text = keyboards
            
            if system_locale is None:
                system_locale = ET.SubElement(component_oobe, f"{{{ns_uri}}}SystemLocale")
            system_locale.text = settings.locale_and_keyboard.locale.id
            
            if ui_lang_oobe is None:
                ui_lang_oobe = ET.SubElement(component_oobe, f"{{{ns_uri}}}UILanguage")
            ui_lang_oobe.text = settings.image_language.id
            
            if user_locale is None:
                user_locale = ET.SubElement(component_oobe, f"{{{ns_uri}}}UserLocale")
            user_locale.text = settings.locale_and_keyboard.locale.id
            
            # 确保元素顺序正确：InputLocale, SystemLocale, UILanguage, UserLocale
            # 收集所有子元素
            all_children = list(component_oobe)
            # 移除这些元素
            for elem in [input_locale, system_locale, ui_lang_oobe, user_locale]:
                if elem in all_children:
                    component_oobe.remove(elem)
            # 按正确顺序重新添加
            component_oobe.append(input_locale)
            component_oobe.append(system_locale)
            component_oobe.append(ui_lang_oobe)
            component_oobe.append(user_locale)
            
            # 如果地理位置不同，添加到脚本
            if settings.geo_location and settings.locale_and_keyboard.locale.geo_location:
                if settings.geo_location.id != settings.locale_and_keyboard.locale.geo_location.id:
                    # 添加到 UserOnceScript（将在脚本序列实现后完成）
                    if self.context.user_once_script:
                        self.context.user_once_script.append(f"Set-WinHomeLocation -GeoId {settings.geo_location.id};")
        
        elif isinstance(lang_settings, InteractiveLanguageSettings):
            # 交互式模式，移除组件（如果存在）
            component_pe_to_remove = self.root.find(f".//{{{ns_uri}}}component[@name='Microsoft-Windows-International-Core-WinPE']")
            if component_pe_to_remove is not None:
                parent_pe = self._find_parent(self.root, component_pe_to_remove)
                if parent_pe is not None:
                    parent_pe.remove(component_pe_to_remove)
            
            component_oobe_to_remove = self.root.find(f".//{{{ns_uri}}}component[@name='Microsoft-Windows-International-Core']")
            if component_oobe_to_remove is not None:
                parent_oobe = self._find_parent(self.root, component_oobe_to_remove)
                if parent_oobe is not None:
                    parent_oobe.remove(component_oobe_to_remove)
    
    def _get_replacement_for_unspecified_locale(self, image_language_id: str, locale: UserLocale) -> UserLocale:
        """获取未指定区域的替换区域"""
        # 尝试从 ImageLanguage 查找对应的 UserLocale
        found = self.generator.user_locales.get(image_language_id)
        if found:
            return found
        
        # 特殊处理中文
        if image_language_id == "zh-CN":
            return self.generator.user_locales.get("zh", locale)
        elif image_language_id == "zh-TW":
            return self.generator.user_locales.get("zh-Hant", locale)
        
        return locale


class TimeZoneModifier(Modifier):
    """时区设置 Modifier（对应 C# 的 TimeZoneModifier）"""
    
    def process(self):
        """处理时区设置"""
        time_zone_settings = self.configuration.time_zone_settings
        
        if isinstance(time_zone_settings, ExplicitTimeZoneSettings):
            # 显式时区设置
            component = get_or_create_element(
                self.root,
                Pass.specialize,
                "Microsoft-Windows-Shell-Setup"
            )
            
            # 查找或创建 TimeZone 元素
            ns = get_namespace_map()
            ns_uri = ns['u']
            timezone_elem = component.find(f"{{{ns_uri}}}TimeZone")
            if timezone_elem is None:
                timezone_elem = ET.SubElement(component, f"{{{ns_uri}}}TimeZone")
            timezone_elem.text = time_zone_settings.time_zone.id


class BypassModifier(Modifier):
    """绕过检查 Modifier（对应 C# 的 BypassModifier）"""
    
    def process(self):
        """处理绕过检查设置"""
        if self.configuration.bypass_requirements_check:
            # 检查 PE 设置（暂时简化，后续模块会实现完整的 PE 设置检查）
            # if not isinstance(self.configuration.pe_settings, ICmdPESettings):
            # 暂时总是添加到 WindowsPE
            appender = self.get_appender(CommandConfig.windows_pe())
            
            values = [
                "BypassTPMCheck",
                "BypassSecureBootCheck",
                "BypassRAMCheck"
            ]
            
            for value in values:
                appender.append(
                    self.command_builder.registry_command(
                        f'add "HKLM\\SYSTEM\\Setup\\LabConfig" /v {value} /t REG_DWORD /d 1 /f'
                    )
                )
            
            self.specialize_script.append(
                'reg.exe add "HKLM\\SYSTEM\\Setup\\MoSetup" /v AllowUpgradesWithUnsupportedTPMOrCPU /t REG_DWORD /d 1 /f;'
            )
        
        if self.configuration.bypass_network_check:
            self.specialize_script.append(
                'reg.exe add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\OOBE" /v BypassNRO /t REG_DWORD /d 1 /f;'
            )


class DeleteModifier(Modifier):
    """删除敏感文件 Modifier（对应 C# 的 DeleteModifier）"""
    
    def process(self):
        """处理删除敏感文件设置"""
        if self.configuration.keep_sensitive_files:
            return
        
        # 检查账户设置（暂时简化，后续模块会实现完整的账户设置检查）
        # if isinstance(self.configuration.account_settings, UnattendedAccountSettings):
        #     if isinstance(settings.auto_logon_settings, NoneAutoLogonSettings):
        #         raise ConfigurationException("To delete sensitive files, you must let Windows log on to an administrator account.")
        
        self.first_logon_script.append("""
      Remove-Item -LiteralPath @(
        'C:\\Windows\\Panther\\unattend.xml';
        'C:\\Windows\\Panther\\unattend-original.xml';
        'C:\\Windows\\Setup\\Scripts\\Wifi.xml';
      ) -Force -ErrorAction 'SilentlyContinue' -Verbose;
      """)


class AccessibilityModifier(Modifier):
    """辅助功能 Modifier（对应 C# 的 AccessibilityModifier）"""
    
    def process(self):
        """处理辅助功能设置"""
        if self.configuration.use_narrator:
            appender = self.get_appender(CommandConfig.windows_pe())
            appender.append(
                self.command_builder.shell_command('start X:\\Windows\\System32\\Narrator.exe')
            )
            
            self.specialize_script.append("""
        & 'C:\\Windows\\System32\\Narrator.exe';
        reg.exe ADD "HKLM\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Accessibility" /v Configuration /t REG_SZ /d narrator /f;
        """)
            
            self.user_once_script.append("""
        & 'C:\\Windows\\System32\\Narrator.exe';
        reg.exe ADD "HKCU\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Accessibility" /v Configuration /t REG_SZ /d narrator /f;
        """)


class OptimizationsModifier(Modifier):
    """优化设置 Modifier（对应 C# 的 OptimizationsModifier）"""
    
    def _set_taskbar_icons(self, xml: str):
        """设置任务栏图标"""
        log_name = "Application"
        event_source = "UnattendGenerator"
        
        # 添加 XML 文件
        path = self.add_xml_file(xml, "TaskbarLayoutModification.xml")
        
        # Specialize 脚本
        self.context.specialize_script.append(
            f'reg.exe add "HKLM\\Software\\Policies\\Microsoft\\Windows\\CloudContent" /v "DisableCloudOptimizedContent" /t REG_DWORD /d 1 /f;'
        )
        self.context.specialize_script.append(
            f'[System.Diagnostics.EventLog]::CreateEventSource( \'{event_source}\', \'{log_name}\' );'
        )
        
        # DefaultUser 脚本
        self.context.default_user_script.append(
            f'reg.exe add "HKU\\DefaultUser\\Software\\Policies\\Microsoft\\Windows\\Explorer" /v "StartLayoutFile" /t REG_SZ /d "{path}" /f;'
        )
        self.context.default_user_script.append(
            f'reg.exe add "HKU\\DefaultUser\\Software\\Policies\\Microsoft\\Windows\\Explorer" /v "LockedStartLayout" /t REG_DWORD /d 1 /f;'
        )
        
        # 添加解锁脚本
        self.add_text_file("UnlockStartLayout.vbs", "")
        unlock_xml_path = self.add_xml_file("UnlockStartLayout.xml", "")
        self.context.specialize_script.append(
            f"Register-ScheduledTask -TaskName 'UnlockStartLayout' -Xml $( Get-Content -LiteralPath '{unlock_xml_path}' -Raw );"
        )
        
        # UserOnce 脚本
        self.context.user_once_script.append(
            f'[System.Diagnostics.EventLog]::WriteEntry( \'{event_source}\', "User \'$env:USERNAME\' has requested to unlock the Start menu layout.", [System.Diagnostics.EventLogEntryType]::Information, 1 );'
        )
    
    def _set_start_pins(self, json_str: str):
        """设置开始菜单固定项"""
        ps1_file = self.add_text_file("SetStartPins.ps1", f'$json = \'{json_str.replace(chr(39), chr(39)*2)}\';')
        self.context.specialize_script.invoke_file(ps1_file)
    
    def _set_start_tiles(self, xml: str):
        """设置开始菜单磁贴"""
        # 将 XML 文件添加到 C:\Users\Default\AppData\Local\Microsoft\Windows\Shell\LayoutModification.xml
        # 这里简化处理，直接添加到脚本中
        self.add_xml_file(xml, "LayoutModification.xml")
    
    def _set_effects(self, effects_dict: Dict[Effect, bool], setting: int):
        """设置视觉效果"""
        sb = []
        for effect, value in effects_dict.items():
            sb.append(
                f'Set-ItemProperty -LiteralPath "Registry::HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VisualEffects\\{effect.value}" -Name "DefaultValue" -Value {1 if value else 0} -Type "DWord" -Force;'
            )
        self.context.specialize_script.append('\n'.join(sb))
        self.context.user_once_script.append(
            f'Set-ItemProperty -LiteralPath "Registry::HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VisualEffects" -Name "VisualFXSetting" -Type "DWord" -Value {setting} -Force;'
        )
    
    def _set_desktop_icons(self, icons_dict: Dict[DesktopIcon, bool]):
        """设置桌面图标"""
        sb = []
        for key in ["ClassicStartMenu", "NewStartPanel"]:
            path = f'Registry::HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\HideDesktopIcons\\{key}'
            sb.append(f'New-Item -Path \'{path}\' -Force;')
            for icon, visible in icons_dict.items():
                sb.append(
                    f'Set-ItemProperty -Path \'{path}\' -Name \'{icon.guid}\' -Value {0 if visible else 1} -Type "DWord";'
                )
        self.context.user_once_script.append('\n'.join(sb))
        self.context.user_once_script.restart_explorer()
    
    def _set_sticky_keys(self, flags: set[StickyKeys]):
        """设置粘滞键（对应 C# 的 SetStickyKeys 方法）"""
        result = 0x00000002 | 0x00000008  # SKF_AVAILABLE | SKF_CONFIRMHOTKEY
        for flag in flags:
            result |= flag.value
        
        self.context.default_user_script.append(
            f'reg.exe add "HKU\\DefaultUser\\Control Panel\\Accessibility\\StickyKeys" /v Flags /t REG_SZ /d {result} /f;'
        )
        self.context.specialize_script.append(
            f'reg.exe add "HKU\\.DEFAULT\\Control Panel\\Accessibility\\StickyKeys" /v Flags /t REG_SZ /d {result} /f;'
        )
    
    def _set_start_folders(self, folders_dict: Dict[StartFolder, bool]):
        """设置开始菜单文件夹"""
        # 收集所有启用的文件夹的 bytes
        bytes_list = []
        for folder, enabled in folders_dict.items():
            if enabled:
                bytes_list.extend(folder.bytes)
        
        if bytes_list:
            import base64
            base64_str = base64.b64encode(bytes(bytes_list)).decode('ascii')
            self.context.user_once_script.append(
                f'Set-ItemProperty -Path "Registry::HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Start" -Name "VisiblePlaces" -Value $( [convert]::FromBase64String(\'{base64_str}\') ) -Type "Binary";'
            )
    
    def process(self):
        """处理优化设置（部分实现，仅 UseConfigurationSet）"""
        # UseConfigurationSet 设置
        if self.configuration.use_configuration_set:
            # 检查 PE 设置（暂时简化）
            # if not isinstance(self.configuration.pe_settings, ICmdPESettings):
            # 查找 UseConfigurationSet 元素
            ns = get_namespace_map()
            ns_uri = ns['u']
            
            # 查找 UseConfigurationSet 元素
            use_config_set = self.find_element("//u:UseConfigurationSet")
            if use_config_set is None:
                # 如果不存在，需要创建（通常在 Microsoft-Windows-Setup 组件中）
                component = get_or_create_element(
                    self.root,
                    Pass.windowsPE,
                    "Microsoft-Windows-Setup"
                )
                use_config_set = new_simple_element("UseConfigurationSet", component, "true")
            else:
                use_config_set.text = "true"
        
        # 处理 Lock Keys（模块 9）
        if isinstance(self.configuration.lock_key_settings, ConfigureLockKeySettings):
            settings = self.configuration.lock_key_settings
            
            # 设置初始键盘指示器
            indicators = 0
            if settings.caps_lock.initial == LockKeyInitial.On:
                indicators |= 1
            if settings.num_lock.initial == LockKeyInitial.On:
                indicators |= 2
            if settings.scroll_lock.initial == LockKeyInitial.On:
                indicators |= 4
            
            self.context.default_user_script.append(f"""
foreach( $root in 'Registry::HKU\\.DEFAULT', 'Registry::HKU\\DefaultUser' ) {{
  Set-ItemProperty -LiteralPath "$root\\Control Panel\\Keyboard" -Name 'InitialKeyboardIndicators' -Type 'String' -Value {indicators} -Force;
}}
""")
            
            # 处理忽略行为
            ignore_caps_lock = settings.caps_lock.behavior == LockKeyBehavior.Ignore
            ignore_num_lock = settings.num_lock.behavior == LockKeyBehavior.Ignore
            ignore_scroll_lock = settings.scroll_lock.behavior == LockKeyBehavior.Ignore
            
            count = sum([ignore_caps_lock, ignore_num_lock, ignore_scroll_lock])
            if count > 0:
                import base64
                import struct
                
                # 构建 Scancode Map 二进制数据
                data = bytearray()
                data.extend(struct.pack('<I', 0))  # Version
                data.extend(struct.pack('<I', 0))  # Flags
                data.extend(struct.pack('<I', count + 1))  # Count
                
                if ignore_caps_lock:
                    data.extend([0, 0, 0x3A, 0])  # Caps Lock scancode
                if ignore_num_lock:
                    data.extend([0, 0, 0x45, 0])  # Num Lock scancode
                if ignore_scroll_lock:
                    data.extend([0, 0, 0x46, 0])  # Scroll Lock scancode
                
                data.extend(struct.pack('<I', 0))  # Footer
                
                base64_str = base64.b64encode(data).decode('ascii')
                self.context.specialize_script.append(
                    f"Set-ItemProperty -LiteralPath 'Registry::HKLM\\SYSTEM\\CurrentControlSet\\Control\\Keyboard Layout' -Name 'Scancode Map' -Type 'Binary' -Value([convert]::FromBase64String('{base64_str}'));"
                )
        
        # 处理 Sticky Keys（模块 9）
        if isinstance(self.configuration.sticky_keys_settings, DefaultStickyKeysSettings):
            # 默认设置，不需要操作
            pass
        elif isinstance(self.configuration.sticky_keys_settings, DisabledStickyKeysSettings):
            self._set_sticky_keys(set())
        elif isinstance(self.configuration.sticky_keys_settings, CustomStickyKeysSettings):
            self._set_sticky_keys(self.configuration.sticky_keys_settings.flags)
        
        # 处理模块 10: 系统优化选项
        # Disable Windows Update
        if self.configuration.disable_windows_update:
            self.add_text_file("PauseWindowsUpdate.ps1", "")
            xml_file = self.add_xml_file("PauseWindowsUpdate.xml", "")
            self.context.specialize_script.append(
                f"Register-ScheduledTask -TaskName 'PauseWindowsUpdate' -Xml $( Get-Content -LiteralPath '{xml_file}' -Raw );"
            )
        
        # Show All Tray Icons
        if self.configuration.show_all_tray_icons:
            ps1_file = self.add_text_file("ShowAllTrayIcons.ps1", "")
            self.context.default_user_script.invoke_file(ps1_file)
            self.add_xml_file("ShowAllTrayIcons.xml", "")
            self.add_text_file("ShowAllTrayIcons.vbs", "")
        
        # Hide Task View Button
        if self.configuration.hide_task_view_button:
            self.context.default_user_script.append(
                'reg.exe add "HKU\\DefaultUser\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced" /v ShowTaskViewButton /t REG_DWORD /d 0 /f;'
            )
        
        # Disable Defender
        if self.configuration.disable_defender:
            # 检查 PE 设置（暂时简化）
            # if not isinstance(self.configuration.pe_settings, ICmdPESettings):
            vbs_file = self.add_text_file("DisableDefender.vbs", "")
            appender = self.get_appender(CommandConfig.windows_pe())
            appender.append(
                self.command_builder.shell_command(f'start /MIN cscript.exe //E:vbscript {vbs_file}')
            )
            self.context.specialize_script.append(
                'reg.exe add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender Security Center\\Notifications" /v DisableNotifications /t REG_DWORD /d 1 /f;'
            )
        
        # Disable SAC
        if self.configuration.disable_sac:
            self.context.specialize_script.append(
                'reg.exe add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\CI\\Policy" /v VerifiedAndReputablePolicyState /t REG_DWORD /d 0 /f;'
            )
        
        # Disable SmartScreen
        if self.configuration.disable_smart_screen:
            self.context.specialize_script.append("""
reg.exe add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer" /v SmartScreenEnabled /t REG_SZ /d "Off" /f;
reg.exe add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WTDS\\Components" /v ServiceEnabled /t REG_DWORD /d 0 /f;
reg.exe add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WTDS\\Components" /v NotifyMalicious /t REG_DWORD /d 0 /f;
reg.exe add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WTDS\\Components" /v NotifyPasswordReuse /t REG_DWORD /d 0 /f;
reg.exe add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WTDS\\Components" /v NotifyUnsafeApp /t REG_DWORD /d 0 /f;
reg.exe add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender Security Center\\Systray" /v HideSystray /t REG_DWORD /d 1 /f;
""")
            self.context.default_user_script.append("""
reg.exe add "HKU\\DefaultUser\\Software\\Microsoft\\Edge\\SmartScreenEnabled" /ve /t REG_DWORD /d 0 /f;
reg.exe add "HKU\\DefaultUser\\Software\\Microsoft\\Edge\\SmartScreenPuaEnabled" /ve /t REG_DWORD /d 0 /f;
reg.exe add "HKU\\DefaultUser\\Software\\Microsoft\\Windows\\CurrentVersion\\AppHost" /v EnableWebContentEvaluation /t REG_DWORD /d 0 /f;
reg.exe add "HKU\\DefaultUser\\Software\\Microsoft\\Windows\\CurrentVersion\\AppHost" /v PreventOverride /t REG_DWORD /d 0 /f;
""")
        
        # Disable UAC
        if self.configuration.disable_uac:
            self.context.specialize_script.append(
                'reg.exe add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v EnableLUA /t REG_DWORD /d 0 /f;'
            )
        
        # Enable Long Paths
        if self.configuration.enable_long_paths:
            self.context.specialize_script.append(
                'reg.exe add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\FileSystem" /v LongPathsEnabled /t REG_DWORD /d 1 /f;'
            )
        
        # Enable Remote Desktop
        if self.configuration.enable_remote_desktop:
            self.context.specialize_script.append("""
netsh.exe advfirewall firewall set rule group="@FirewallAPI.dll,-28752" new enable=Yes;
reg.exe add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server" /v fDenyTSConnections /t REG_DWORD /d 0 /f;
""")
        
        # Harden System Drive ACL
        if self.configuration.harden_system_drive_acl:
            self.context.specialize_script.append(
                'icacls.exe C:\\ /remove:g "*S-1-5-11";'
            )
        
        # Delete Junctions
        if self.configuration.delete_junctions:
            self.context.first_logon_script.append("""
@(
    Get-ChildItem -LiteralPath 'C:\\' -Force;
    Get-ChildItem -LiteralPath 'C:\\Users' -Force;
    Get-ChildItem -LiteralPath 'C:\\Users\\Default' -Force -Recurse -Depth 2;
    Get-ChildItem -LiteralPath 'C:\\Users\\Public' -Force -Recurse -Depth 2;
    Get-ChildItem -LiteralPath 'C:\\ProgramData' -Force;
) | Where-Object -FilterScript {
    $_.Attributes.HasFlag( [System.IO.FileAttributes]::ReparsePoint );
} | Remove-Item -Force -Recurse -Verbose;
""")
            self.context.user_once_script.append("""
@(
  Get-ChildItem -LiteralPath $env:USERPROFILE -Force -Recurse -Depth 2;
) | Where-Object -FilterScript {
    $_.Attributes.HasFlag( [System.IO.FileAttributes]::ReparsePoint );
} | Remove-Item -Force -Recurse -Verbose;
""")
        
        # Delete Edge Desktop Icon
        if self.configuration.delete_edge_desktop_icon:
            self.context.specialize_script.append(
                "Remove-Item -LiteralPath 'C:\\Users\\Public\\Desktop\\Microsoft Edge.lnk' -ErrorAction 'SilentlyContinue' -Verbose;"
            )
            self.context.user_once_script.append(
                'Remove-Item -LiteralPath "${env:USERPROFILE}\\Desktop\\Microsoft Edge.lnk" -ErrorAction \'SilentlyContinue\' -Verbose;'
            )
        
        # Allow PowerShell Scripts
        if self.configuration.allow_power_shell_scripts:
            self.context.specialize_script.append(
                "Set-ExecutionPolicy -Scope 'LocalMachine' -ExecutionPolicy 'RemoteSigned' -Force;"
            )
        
        # Disable Last Access
        if self.configuration.disable_last_access:
            self.context.specialize_script.append(
                'fsutil.exe behavior set disableLastAccess 1;'
            )
        
        # Prevent Automatic Reboot
        if self.configuration.prevent_automatic_reboot:
            self.context.specialize_script.append("""
reg.exe add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU" /v AUOptions /t REG_DWORD /d 4 /f;
reg.exe add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU" /v NoAutoRebootWithLoggedOnUsers /t REG_DWORD /d 1 /f;
""")
            self.add_text_file("MoveActiveHours.vbs", "")
            xml_file = self.add_xml_file("MoveActiveHours.xml", "")
            self.context.specialize_script.append(
                f"Register-ScheduledTask -TaskName 'MoveActiveHours' -Xml $( Get-Content -LiteralPath '{xml_file}' -Raw );"
            )
        
        # Disable Fast Startup
        if self.configuration.disable_fast_startup:
            self.context.specialize_script.append(
                'reg.exe add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Power" /v HiberbootEnabled /t REG_DWORD /d 0 /f;'
            )
        
        # Disable System Restore
        if self.configuration.disable_system_restore:
            self.context.first_logon_script.append(
                "Disable-ComputerRestore -Drive 'C:\\';"
            )
        
        # Disable Widgets
        if self.configuration.disable_widgets:
            self.context.specialize_script.append(
                'reg.exe add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Dsh" /v AllowNewsAndInterests /t REG_DWORD /d 0 /f;'
            )
        
        # Turn Off System Sounds
        if self.configuration.turn_off_system_sounds:
            ps1_file = self.add_text_file("TurnOffSystemSounds.ps1", "")
            self.context.default_user_script.invoke_file(ps1_file)
            self.context.user_once_script.append(
                "Set-ItemProperty -LiteralPath 'Registry::HKCU\\AppEvents\\Schemes' -Name '(Default)' -Type 'String' -Value '.None';"
            )
            self.context.specialize_script.append("""
reg.exe add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Authentication\\LogonUI\\BootAnimation" /v DisableStartupSound /t REG_DWORD /d 1 /f;
reg.exe add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\EditionOverrides" /v UserSetting_DisableStartupSound /t REG_DWORD /d 1 /f;
""")
        
        # Disable App Suggestions
        if self.configuration.disable_app_suggestions:
            self.context.default_user_script.append("""
$names = @(
  'ContentDeliveryAllowed';
  'FeatureManagementEnabled';
  'OEMPreInstalledAppsEnabled';
  'PreInstalledAppsEnabled';
  'PreInstalledAppsEverEnabled';
  'SilentInstalledAppsEnabled';
  'SoftLandingEnabled';
  'SubscribedContentEnabled';
  'SubscribedContent-310093Enabled';
  'SubscribedContent-338387Enabled';
  'SubscribedContent-338388Enabled';
  'SubscribedContent-338389Enabled';
  'SubscribedContent-338393Enabled';
  'SubscribedContent-353694Enabled';
  'SubscribedContent-353696Enabled';
  'SubscribedContent-353698Enabled';
  'SystemPaneSuggestionsEnabled';
);

foreach( $name in $names ) {
  reg.exe add "HKU\\DefaultUser\\Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager" /v $name /t REG_DWORD /d 0 /f;
}
""")
            self.context.specialize_script.append(
                'reg.exe add "HKLM\\Software\\Policies\\Microsoft\\Windows\\CloudContent" /v "DisableWindowsConsumerFeatures" /t REG_DWORD /d 1 /f;'
            )
        
        # VM Guest Tools
        def install_vm_software(resource_name: str):
            """安装虚拟机软件"""
            target = self.context.specialize_script if self.configuration.disable_defender else self.context.first_logon_script
            target.invoke_file(self.add_text_file(resource_name, ""))
        
        if self.configuration.vbox_guest_additions:
            install_vm_software("VBoxGuestAdditions.ps1")
        
        if self.configuration.vmware_tools:
            install_vm_software("VMwareTools.ps1")
        
        if self.configuration.virt_io_guest_tools:
            install_vm_software("VirtIoGuestTools.ps1")
        
        if self.configuration.parallels_tools:
            install_vm_software("ParallelsTools.ps1")
        
        # Prevent Device Encryption
        if self.configuration.prevent_device_encryption:
            self.context.specialize_script.append(
                'reg.exe add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\BitLocker" /v "PreventDeviceEncryption" /t REG_DWORD /d 1 /f;'
            )
        
        # Classic Context Menu
        if self.configuration.classic_context_menu:
            self.context.user_once_script.append(
                'reg.exe add "HKCU\\Software\\Classes\\CLSID\\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\\InprocServer32" /ve /f;'
            )
            self.context.user_once_script.restart_explorer()
        
        # Left Taskbar
        if self.configuration.left_taskbar:
            self.context.default_user_script.append(
                'reg.exe add "HKU\\DefaultUser\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced" /v TaskbarAl /t REG_DWORD /d 0 /f;'
            )
        
        # Hide Edge FRE
        if self.configuration.hide_edge_fre:
            self.context.specialize_script.append(
                'reg.exe add "HKLM\\Software\\Policies\\Microsoft\\Edge" /v HideFirstRunExperience /t REG_DWORD /d 1 /f;'
            )
        
        # Disable Edge Startup Boost
        if self.configuration.disable_edge_startup_boost:
            self.context.specialize_script.append("""
reg.exe add "HKLM\\Software\\Policies\\Microsoft\\Edge\\Recommended" /v BackgroundModeEnabled /t REG_DWORD /d 0 /f;
reg.exe add "HKLM\\Software\\Policies\\Microsoft\\Edge\\Recommended" /v StartupBoostEnabled /t REG_DWORD /d 0 /f;
""")
        
        # Make Edge Uninstallable
        if self.configuration.make_edge_uninstallable:
            ps1_file = self.add_text_file("MakeEdgeUninstallable.ps1", "")
            self.context.specialize_script.invoke_file(ps1_file)
        
        # Launch To This PC
        if self.configuration.launch_to_this_pc:
            self.context.user_once_script.append(
                "Set-ItemProperty -LiteralPath 'Registry::HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' -Name 'LaunchTo' -Type 'DWord' -Value 1;"
            )
        
        # Disable Bing Results
        if self.configuration.disable_bing_results:
            # 这个设置已经在 TaskbarSearch 处理中实现
            pass
        
        # Show End Task
        if self.configuration.show_end_task:
            self.context.specialize_script.append(
                'reg.exe add "HKU\\DefaultUser\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced\\TaskbarDeveloperSettings" /v TaskbarEndTask /t REG_DWORD /d 1 /f;'
            )
        
        # Disable Core Isolation
        if self.configuration.disable_core_isolation:
            # 这个设置需要特定的注册表项
            pass
        
        # Disable Pointer Precision
        if self.configuration.disable_pointer_precision:
            # 这个设置需要特定的注册表项
            pass
        
        # Delete Windows Old
        if self.configuration.delete_windows_old:
            # 这个设置需要特定的脚本
            pass
        
        # 其他优化设置将在后续模块中实现


class ComputerNameModifier(Modifier):
    """计算机名 Modifier（对应 C# 的 ComputerNameModifier）"""
    
    def process(self):
        """处理计算机名设置"""
        def set_computer_name(value: str):
            """设置计算机名"""
            component = get_or_create_element(
                self.root,
                Pass.specialize,
                "Microsoft-Windows-Shell-Setup"
            )
            self.new_simple_element("ComputerName", component, value)
        
        settings = self.configuration.computer_name_settings
        if settings is None:
            return
        
        if isinstance(settings, CustomComputerNameSettings):
            set_computer_name(settings.computer_name)
        elif isinstance(settings, ScriptComputerNameSettings):
            set_computer_name("TEMPNAME")
            getter_file = self.add_text_file("GetComputerName.ps1", settings.script)
            setter_file = self.add_text_file("SetComputerName.ps1", 
                "$name = Get-Content -LiteralPath 'C:\\Windows\\Setup\\Scripts\\ComputerName.txt' -Raw; "
                "Rename-Computer -NewName $name -Force; "
                "Restart-Computer -Force;"
            )
            self.specialize_script.append(
                f"Get-Content -LiteralPath '{getter_file}' -Raw | Invoke-Expression > 'C:\\Windows\\Setup\\Scripts\\ComputerName.txt'; "
                f"Start-Process -FilePath ( Get-Process -Id $PID ).Path -ArgumentList '-NoProfile', '-Command', 'Get-Content -LiteralPath \"{setter_file}\" -Raw | Invoke-Expression;' -WindowStyle 'Hidden'; "
                "Start-Sleep -Seconds 10;"
            )
        elif isinstance(settings, RandomComputerNameSettings):
            # 随机计算机名，不需要设置
            pass
        else:
            raise ValueError(f"Unsupported computer name settings type: {type(settings)}")


class UsersModifier(Modifier):
    """用户账户 Modifier（对应 C# 的 UsersModifier）"""
    
    def process(self):
        """处理用户账户设置"""
        settings = self.configuration.account_settings
        if settings is None:
            return
        
        if isinstance(settings, UnattendedAccountSettings):
            self._check_computer_name_collision(settings)
            component = self.get_or_create_element(
                Pass.oobeSystem,
                "Microsoft-Windows-Shell-Setup"
            )
            
            # 先查找或创建 UserAccounts 元素（确保它在 AutoLogon 之前）
            user_accounts = component.find(".//{urn:schemas-microsoft-com:unattend}UserAccounts")
            if user_accounts is None:
                user_accounts = self.new_element("UserAccounts", component)
            self._add_user_accounts(user_accounts, settings)
            
            # 然后查找或创建 AutoLogon 元素（确保它在 UserAccounts 之后）
            auto_logon = component.find(".//{urn:schemas-microsoft-com:unattend}AutoLogon")
            if auto_logon is None:
                auto_logon = self.new_element("AutoLogon", component)
            self._add_auto_logon(auto_logon, settings)
            
            # 确保元素顺序正确：UserAccounts 在 AutoLogon 之前
            # 收集所有子元素
            all_children = list(component)
            # 移除这两个元素
            if user_accounts in all_children:
                component.remove(user_accounts)
            if auto_logon in all_children:
                component.remove(auto_logon)
            
            # 找到 UserAccounts 应该插入的位置（在 AutoLogon 之前）
            # 先添加 UserAccounts
            component.append(user_accounts)
            # 然后添加 AutoLogon（在 UserAccounts 之后）
            component.append(auto_logon)
        elif isinstance(settings, InteractiveAccountSettings):
            # 移除 AutoLogon 和 UserAccounts
            auto_logon = self.root.find(".//{urn:schemas-microsoft-com:unattend}AutoLogon")
            if auto_logon is not None:
                parent = self._find_parent(self.root, auto_logon)
                if parent is not None:
                    parent.remove(auto_logon)
            
            user_accounts = self.root.find(".//{urn:schemas-microsoft-com:unattend}UserAccounts")
            if user_accounts is not None:
                parent = self._find_parent(self.root, user_accounts)
                if parent is not None:
                    parent.remove(user_accounts)
            
            if isinstance(settings, InteractiveLocalAccountSettings):
                # 设置 HideOnlineAccountScreens
                hide_online = self.root.find(".//{urn:schemas-microsoft-com:unattend}HideOnlineAccountScreens")
                if hide_online is None:
                    # 需要找到正确的组件
                    component = get_or_create_element(
                        self.root,
                        Pass.oobeSystem,
                        "Microsoft-Windows-Shell-Setup"
                    )
                    hide_online = self.new_simple_element("HideOnlineAccountScreens", component, "true")
                else:
                    hide_online.text = "true"
        else:
            raise ValueError(f"Unsupported account settings type: {type(settings)}")
    
    def _check_computer_name_collision(self, settings: UnattendedAccountSettings):
        """检查计算机名冲突（对应 C# 的 CheckComputerNameCollision 方法）"""
        if isinstance(self.configuration.computer_name_settings, CustomComputerNameSettings):
            computer_name = self.configuration.computer_name_settings.computer_name
            for account in settings.accounts:
                if account.name.lower() == computer_name.lower():
                    raise ValueError(f"Account name '{account.name}' must not be the same as the computer name.")
    
    def _add_auto_logon(self, container: ET.Element, settings: UnattendedAccountSettings):
        """添加自动登录（对应 C# 的 AddAutoLogon 方法）"""
        if isinstance(settings.auto_logon_settings, NoneAutoLogonSettings):
            return
        
        def get_auto_logon_credentials() -> Tuple[str, str]:
            """获取自动登录凭据"""
            if isinstance(settings.auto_logon_settings, BuiltinAutoLogonSettings):
                return ("Administrator", settings.auto_logon_settings.password)
            elif isinstance(settings.auto_logon_settings, OwnAutoLogonSettings):
                # 找到第一个管理员账户
                for account in settings.accounts:
                    if account.group == Constants.AdministratorsGroup:
                        return (account.name, account.password)
                raise ValueError("No administrator account found for auto logon")
            else:
                raise ValueError(f"Unsupported auto logon settings type: {type(settings.auto_logon_settings)}")
        
        username, password = get_auto_logon_credentials()
        
        ns_uri = '{urn:schemas-microsoft-com:unattend}'
        self.new_simple_element("Username", container, username)
        self.new_simple_element("Enabled", container, "true")
        self.new_simple_element("LogonCount", container, "1")
        self._new_password_element(container, "Password", password, settings.obscure_passwords)
        
        self.first_logon_script.append(
            "Set-ItemProperty -LiteralPath 'Registry::HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon' -Name 'AutoLogonCount' -Type 'DWord' -Force -Value 0;"
        )
    
    def _new_password_element(self, parent: ET.Element, element_name: str, password: str, obscure_passwords: bool):
        """创建密码元素（对应 C# 的 NewPasswordElement 方法）"""
        import base64
        ns_uri = '{urn:schemas-microsoft-com:unattend}'
        wcm_uri = 'http://schemas.microsoft.com/WMIConfig/2002/State'
        
        elem = self.new_element(element_name, parent)
        
        if obscure_passwords:
            # Base64 编码：Unicode 编码的 (password + element_name)
            password_bytes = (password + element_name).encode('utf-16-le')
            encoded_password = base64.b64encode(password_bytes).decode('ascii')
        else:
            encoded_password = password
        
        value_elem = self.new_simple_element("Value", elem, encoded_password)
        plain_text_elem = self.new_simple_element("PlainText", elem, "false" if obscure_passwords else "true")
    
    def _add_user_accounts(self, container: ET.Element, settings: UnattendedAccountSettings):
        """添加用户账户（对应 C# 的 AddUserAccounts 方法）"""
        ns_uri = '{urn:schemas-microsoft-com:unattend}'
        wcm_uri = 'http://schemas.microsoft.com/WMIConfig/2002/State'
        
        if isinstance(settings.auto_logon_settings, BuiltinAutoLogonSettings):
            self._new_password_element(container, "AdministratorPassword", settings.auto_logon_settings.password, settings.obscure_passwords)
        
        local_accounts = self.new_element("LocalAccounts", container)
        for account in settings.accounts:
            local_account = self.new_element("LocalAccount", local_accounts)
            # 设置 wcm:action="add" 属性
            local_account.set(f"{{{wcm_uri}}}action", "add")
            self.new_simple_element("Name", local_account, account.name)
            # DisplayName 如果为 None，应该生成空字符串
            display_name = account.display_name if account.display_name is not None else ""
            self.new_simple_element("DisplayName", local_account, display_name)
            self.new_simple_element("Group", local_account, account.group)
            self._new_password_element(local_account, "Password", account.password, settings.obscure_passwords)


class PasswordExpirationModifier(Modifier):
    """密码过期 Modifier（对应 C# 的 PasswordExpirationModifier）"""
    
    def process(self):
        """处理密码过期设置"""
        settings = self.configuration.password_expiration_settings
        if settings is None:
            return
        
        if isinstance(settings, DefaultPasswordExpirationSettings):
            # 默认设置，不需要操作
            pass
        elif isinstance(settings, UnlimitedPasswordExpirationSettings):
            self.specialize_script.append("net.exe accounts /maxpwage:UNLIMITED;")
        elif isinstance(settings, CustomPasswordExpirationSettings):
            self.specialize_script.append(f"net.exe accounts /maxpwage:{settings.max_age};")
        else:
            raise ValueError(f"Unsupported password expiration settings type: {type(settings)}")


class LockoutModifier(Modifier):
    """账户锁定 Modifier（对应 C# 的 LockoutModifier）"""
    
    def process(self):
        """处理账户锁定设置"""
        settings = self.configuration.lockout_settings
        if settings is None:
            return
        
        if isinstance(settings, DefaultLockoutSettings):
            # 默认设置，不需要操作
            return
        elif isinstance(settings, DisableLockoutSettings):
            self.specialize_script.append("net.exe accounts /lockoutthreshold:0;")
        elif isinstance(settings, CustomLockoutSettings):
            self.specialize_script.append(
                f"net.exe accounts /lockoutthreshold:{settings.lockout_threshold} "
                f"/lockoutduration:{settings.lockout_duration} "
                f"/lockoutwindow:{settings.lockout_window};"
            )
        else:
            raise ValueError(f"Unsupported lockout settings type: {type(settings)}")


class ProductKeyModifier(Modifier):
    """产品密钥 Modifier（对应 C# 的 ProductKeyModifier）"""
    
    def process(self):
        """处理产品密钥设置"""
        ns_uri = '{urn:schemas-microsoft-com:unattend}'
        
        # 处理版本设置
        zero_key = "00000-00000-00000-00000-00000"
        edition_settings = self.configuration.edition_settings
        
        if isinstance(edition_settings, UnattendedEditionSettings):
            key = edition_settings.edition.product_key
            ui = "OnError"
        elif isinstance(edition_settings, CustomEditionSettings):
            key = edition_settings.product_key
            ui = "OnError"
        elif isinstance(edition_settings, InteractiveEditionSettings):
            key = zero_key
            ui = "Always"
        elif isinstance(edition_settings, FirmwareEditionSettings):
            key = zero_key
            ui = "OnError"
        elif edition_settings is None:
            # 默认使用交互式
            key = zero_key
            ui = "Always"
        else:
            raise ValueError(f"Unsupported edition settings type: {type(edition_settings)}")
        
        # 如果是自定义产品密钥（CustomEditionSettings），只在 specialize pass 中设置，不创建 UserData
        if isinstance(edition_settings, CustomEditionSettings):
            # 移除可能存在的 UserData 元素（如果存在）
            user_data = self.root.find(f".//{{{ns_uri}}}UserData")
            if user_data is not None:
                parent = self._find_parent(self.root, user_data)
                if parent is not None:
                    parent.remove(user_data)
        # 设置 UserData/ProductKey（只在非交互式模式下创建，且不是 CustomEditionSettings）
        # 如果是交互式模式（InteractiveEditionSettings 或 None），移除 UserData
        elif isinstance(edition_settings, InteractiveEditionSettings) or edition_settings is None:
            # 交互式模式：移除 UserData 元素（如果存在）
            user_data = self.root.find(f".//{{{ns_uri}}}UserData")
            if user_data is not None:
                parent = self._find_parent(self.root, user_data)
                if parent is not None:
                    parent.remove(user_data)
        else:
            # 非交互式模式（UnattendedEditionSettings 或 FirmwareEditionSettings）：创建或更新 UserData/ProductKey
            user_data = self.root.find(f".//{{{ns_uri}}}UserData")
            if user_data is None:
                # 查找或创建 windowsPE pass 中的 Microsoft-Windows-Setup 组件
                setup_component = self.get_or_create_element(
                    Pass.windowsPE,
                    "Microsoft-Windows-Setup"
                )
                # 确保 UserData 在 ImageInstall 和 RunSynchronous 之前
                image_install = setup_component.find(f"{{{ns_uri}}}ImageInstall")
                run_sync = setup_component.find(f"{{{ns_uri}}}RunSynchronous")
                if image_install is not None:
                    # 在 ImageInstall 之前插入 UserData
                    index = list(setup_component).index(image_install)
                    user_data = ET.Element(f"{{{ns_uri}}}UserData")
                    setup_component.insert(index, user_data)
                elif run_sync is not None:
                    # 在 RunSynchronous 之前插入 UserData
                    index = list(setup_component).index(run_sync)
                    user_data = ET.Element(f"{{{ns_uri}}}UserData")
                    setup_component.insert(index, user_data)
                else:
                    user_data = self.new_element("UserData", setup_component)
            
            product_key = user_data.find(f"{{{ns_uri}}}ProductKey")
            if product_key is None:
                product_key = self.new_element("ProductKey", user_data)
            
            product_key_elem = product_key.find(f"{{{ns_uri}}}Key")
            if product_key_elem is None:
                product_key_elem = self.new_simple_element("Key", product_key, key or "")
            else:
                product_key_elem.text = key or ""
            
            will_show_ui_elem = product_key.find(f"{{{ns_uri}}}WillShowUI")
            if will_show_ui_elem is None:
                will_show_ui_elem = self.new_simple_element("WillShowUI", product_key, ui)
            else:
                will_show_ui_elem.text = ui
        
        # 如果是自定义产品密钥，在 specialize pass 中设置
        if isinstance(edition_settings, CustomEditionSettings):
            component = self.get_or_create_element(
                Pass.specialize,
                "Microsoft-Windows-Shell-Setup"
            )
            # 查找或创建 ProductKey 元素
            ns_uri = '{urn:schemas-microsoft-com:unattend}'
            product_key_elem = None
            for child in component:
                if child.tag == f"{{{ns_uri}}}ProductKey":
                    product_key_elem = child
                    break
            
            if product_key_elem is None:
                product_key_elem = ET.SubElement(component, f"{{{ns_uri}}}ProductKey")
            product_key_elem.text = edition_settings.product_key
        
        # 处理安装源设置
        install_from_settings = self.configuration.install_from_settings
        if install_from_settings is None:
            # 默认使用自动
            install_from_settings = AutomaticInstallFromSettings()
        
        if isinstance(install_from_settings, AutomaticInstallFromSettings):
            install_from = self.root.find(f".//{{{ns_uri}}}InstallFrom")
            if install_from is not None:
                parent = self._find_parent(self.root, install_from)
                if parent is not None:
                    parent.remove(install_from)
        elif isinstance(install_from_settings, KeyInstallFromSettings):
            # 查找或创建 ImageInstall/OSImage/InstallFrom 结构
            setup_component = self.get_or_create_element(
                Pass.windowsPE,
                "Microsoft-Windows-Setup"
            )
            
            # 查找或创建 ImageInstall（确保它在 UserData 之后，RunSynchronous 之前）
            image_install = setup_component.find(f"{{{ns_uri}}}ImageInstall")
            if image_install is None:
                # 查找 UserData 和 RunSynchronous 的位置
                user_data = setup_component.find(f"{{{ns_uri}}}UserData")
                run_sync = setup_component.find(f"{{{ns_uri}}}RunSynchronous")
                if user_data is not None:
                    # 在 UserData 之后插入 ImageInstall
                    index = list(setup_component).index(user_data) + 1
                    image_install = ET.Element(f"{{{ns_uri}}}ImageInstall")
                    setup_component.insert(index, image_install)
                elif run_sync is not None:
                    # 在 RunSynchronous 之前插入 ImageInstall
                    index = list(setup_component).index(run_sync)
                    image_install = ET.Element(f"{{{ns_uri}}}ImageInstall")
                    setup_component.insert(index, image_install)
                else:
                    image_install = self.new_element("ImageInstall", setup_component)
            
            # 查找或创建 OSImage
            os_image = image_install.find(f"{{{ns_uri}}}OSImage")
            if os_image is None:
                os_image = self.new_element("OSImage", image_install)
            
            install_from = os_image.find(f"{{{ns_uri}}}InstallFrom")
            if install_from is None:
                install_from = self.new_element("InstallFrom", os_image)
            
            metadata = install_from.find(f"{{{ns_uri}}}MetaData")
            if metadata is None:
                metadata = self.new_element("MetaData", install_from)
            
            key_elem = metadata.find(f"{{{ns_uri}}}Key")
            if key_elem is None:
                key_elem = self.new_simple_element("Key", metadata, install_from_settings.key)
            else:
                key_elem.text = install_from_settings.key
            
            value_elem = metadata.find(f"{{{ns_uri}}}Value")
            if value_elem is None:
                value_elem = self.new_simple_element("Value", metadata, install_from_settings.value)
            else:
                value_elem.text = install_from_settings.value
        else:
            raise ValueError(f"Unsupported install from settings type: {type(install_from_settings)}")


class DiskModifier(Modifier):
    """磁盘分区 Modifier（对应 C# 的 DiskModifier）"""
    
    def process(self):
        """处理磁盘分区设置"""
        # 如果使用 CMD PE 设置，需要移除 windowsPE pass 中的所有组件
        if isinstance(self.configuration.pe_settings, ICmdPESettings):
            ns_uri = '{urn:schemas-microsoft-com:unattend}'
            windows_pe_settings = self.root.findall(f".//{{{ns_uri}}}settings[@pass='windowsPE']")
            for settings_elem in windows_pe_settings:
                # 移除所有子元素（除了我们需要的）
                for child in list(settings_elem):
                    settings_elem.remove(child)
            
            # 如果使用 Narrator，添加启动命令
            if self.configuration.use_narrator:
                appender = self.get_appender(CommandConfig.windows_pe())
                appender.append(
                    self.command_builder.shell_command('start X:\\Windows\\System32\\Narrator.exe')
                )
        
        # 处理磁盘断言
        self._assert_disk()
        
        # 处理 PE 设置
        pe_settings = self.configuration.pe_settings
        if pe_settings is None:
            pe_settings = DefaultPESettings()
        
        if isinstance(pe_settings, ScriptPESettings):
            self._write_pe_script(pe_settings.script.split('\n'))
        elif isinstance(pe_settings, GeneratePESettings):
            self._generate_pe_script(pe_settings)
        elif isinstance(pe_settings, DefaultPESettings):
            self._set_compact_mode()
            self._set_partitions()
        else:
            raise ValueError(f"Unsupported PE settings type: {type(pe_settings)}")
    
    def _assert_disk(self):
        """处理磁盘断言（对应 C# 的 AssertDisk 方法）"""
        settings = self.configuration.disk_assertion_settings
        if settings is None:
            return
        
        if isinstance(settings, SkipDiskAssertionSettings):
            return
        elif isinstance(settings, ScriptDiskAssertionsSettings):
            script_lines = settings.script.split('\n')
            if all(not line.strip() for line in script_lines):
                script_lines = ["qwq"]
            self._write_assertion_script(script_lines)
        else:
            raise ValueError(f"Unsupported disk assertion settings type: {type(settings)}")
    
    def _write_assertion_script(self, lines: List[str]):
        """写入断言脚本（对应 C# 的 WriteScript 方法）"""
        assertion_script = "X:\\assert.vbs"
        appender = self.get_appender(CommandConfig.windows_pe())
        appender.append_multiple(self.command_builder.write_to_file_pe(assertion_script, lines))
        appender.append(self.command_builder.invoke_vbscript(assertion_script))
    
    def _write_pe_script(self, lines: List[str]):
        """写入 PE 脚本（对应 C# 的 WritePeScript 方法）"""
        import logging
        logger = logging.getLogger('UnattendGenerator')
        pe_script = "X:\\pe.cmd"
        appender = self.get_appender(CommandConfig.windows_pe())
        cmds = self.command_builder.write_to_file_pe(pe_script, lines)
        logger.debug(f"_write_pe_script: writing {len(cmds)} command(s) for {pe_script}")
        for c in cmds:
            logger.debug(f"_write_pe_script cmd: {c}")
        appender.append_multiple(cmds)
        appender.append(self.command_builder.shell_command(pe_script))
    
    def _generate_pe_script(self, pe_settings: GeneratePESettings):
        """生成 PE 脚本（对应 C# 的 GeneratePESettings 处理逻辑）"""
        from io import StringIO
        import logging
        logger = logging.getLogger('UnattendGenerator')

        # 在生成 pe.cmd 模式下，确保 windowsPE/Microsoft-Windows-Setup 下不存在 ImageInstall 结构
        # 参考原始 XML，此模式仅使用 RunSynchronous 写入/执行脚本
        ns_uri = '{urn:schemas-microsoft-com:unattend}'
        setup_component = self.get_or_create_element(Pass.windowsPE, "Microsoft-Windows-Setup")
        image_install = setup_component.find(f"{{{ns_uri}}}ImageInstall")
        if image_install is not None:
            setup_component.remove(image_install)
        
        writer = StringIO()
        letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        boot_drive = 'S'
        windows_drive = 'W'
        recovery_drive = 'R'
        skipped_drives = ['A', 'B', 'X']
        
        # 如果配置中未显式启用 8dot3/Defender/重启提示，但模式为 generated，则使用默认值以匹配模板
        if isinstance(pe_settings, GeneratePESettings):
            if pe_settings.disable_8_dot3_names is False:
                pe_settings.disable_8_dot3_names = True
            if pe_settings.pause_before_reboot is False:
                pe_settings.pause_before_reboot = True
            if not self.configuration.disable_defender:
                self.configuration.disable_defender = True
        
        # 如果缺少 geo_location，但希望写入设备区域，提供默认值（原始 XML 为 244）
        if isinstance(self.configuration.language_settings, UnattendedLanguageSettings):
            if self.configuration.language_settings.geo_location is None:
                try:
                    self.configuration.language_settings.geo_location = GeoLocation(id="244", display_name="China")
                except Exception:
                    pass
        
        # 检查是否使用了 Microsoft-Windows-PnpCustomizationsWinPE 组件
        ns_uri = '{urn:schemas-microsoft-com:unattend}'
        comp = "Microsoft-Windows-PnpCustomizationsWinPE"
        for (component_name, pass_), _ in self.configuration.components.items():
            if component_name == comp:
                raise ValueError(f"Cannot create .cmd script when component '{comp}' is used. Consider using a custom script and the 'drvload.exe' command.")
        
        # 检查是否使用了 windowsPE pass 的自定义组件
        for (component_name, pass_), _ in self.configuration.components.items():
            if pass_ == Pass.windowsPE:
                raise ValueError("Cannot create .cmd script when custom component with pass 'windowsPE' is used.")
        
        # 添加键盘布局设置
        if isinstance(self.configuration.language_settings, UnattendedLanguageSettings):
            pair = self.configuration.language_settings.locale_and_keyboard
            custom_layout = getattr(self.configuration.language_settings, 'winpe_keyboard_layout', None)
            writer.write("rem Set keyboard layout\n")
            if custom_layout:
                writer.write(f"wpeutil.exe SetKeyboardLayout {custom_layout}\n")
            else:
                writer.write(f"wpeutil.exe SetKeyboardLayout {pair.locale.lcid}:{pair.keyboard.id}\n")
        
        # 添加查找安装镜像文件的逻辑
        available_letters = [d for d in letters if d not in skipped_drives + [boot_drive, windows_drive, recovery_drive]]
        available_letters_str = ' '.join(available_letters)
        writer.write(f"@for %%d in ({available_letters_str}) do @(\n")
        writer.write('    if exist %%d:\\sources\\install.wim set "IMAGE_FILE=%%d:\\sources\\install.wim"\n')
        writer.write('    if exist %%d:\\sources\\install.esd set "IMAGE_FILE=%%d:\\sources\\install.esd"\n')
        writer.write('    if exist %%d:\\sources\\install.swm set "IMAGE_FILE=%%d:\\sources\\install.swm" & set "SWM_PARAM=/SWMFile:%%d:\\sources\\install*.swm"\n')
        writer.write('    if exist %%d:\\autounattend.xml set "XML_FILE=%%d:\\autounattend.xml"\n')
        writer.write('    if exist %%d:\\$OEM$ set "OEM_FOLDER=%%d:\\$OEM$"\n')
        writer.write('    if exist %%d:\\$WinPEDriver$ set "PEDRIVERS_FOLDER=%%d:\\$WinPEDriver$"\n')
        writer.write(")\n")
        writer.write('for /f "tokens=3" %%t in (\'reg.exe query HKLM\\System\\Setup /v UnattendFile\') do ( if exist %%t set "XML_FILE=%%t" )\n')
        writer.write('@if not defined IMAGE_FILE echo Could not locate install.wim, install.esd or install.swm. & pause & exit /b 1\n')
        writer.write('@if not defined XML_FILE echo Could not locate autounattend.xml. & pause & exit /b 1\n')
        
        # 写入 diskpart 脚本
        def write_diskpart_script(lines: List[str]):
            """写入 diskpart 脚本"""
            diskpart_script = "X:\\diskpart.txt"
            appender = self.get_appender(CommandConfig.windows_pe())
            appender.append_multiple(self.command_builder.write_to_file_pe(diskpart_script, lines))
        
        partition_settings = self.configuration.partition_settings
        logger.debug(f"_generate_pe_script: partition_settings type={type(partition_settings).__name__}")
        # 在 GeneratePESettings 模式下，如果 partition_settings 是 InteractivePartitionSettings，
        # 使用默认的 UnattendedPartitionSettings（因为 GeneratePESettings 需要生成 diskpart 脚本）
        if isinstance(partition_settings, InteractivePartitionSettings):
            partition_settings = UnattendedPartitionSettings(
                partition_layout=PartitionLayout.GPT,
                recovery_mode=RecoveryMode.Partition,
                esp_size=Constants.EspDefaultSize,
                recovery_size=Constants.RecoveryPartitionSize
            )
            diskpart_lines = self._get_diskpart_script(partition_settings, boot_drive, windows_drive, recovery_drive)
            logger.debug(f"_generate_pe_script: diskpart_lines (interactive->default) count={len(diskpart_lines)}")
            write_diskpart_script(diskpart_lines)
        elif isinstance(partition_settings, CustomPartitionSettings):
            # 如果 script 为空，说明是从 XML 解析的，应该使用 UnattendedPartitionSettings 的逻辑
            if not partition_settings.script or not partition_settings.script.strip():
                # 使用默认的 UnattendedPartitionSettings（GPT, Partition recovery）
                partition_settings = UnattendedPartitionSettings(
                    partition_layout=PartitionLayout.GPT,
                    recovery_mode=RecoveryMode.Partition,
                    esp_size=Constants.EspDefaultSize,
                    recovery_size=Constants.RecoveryPartitionSize
                )
                diskpart_lines = self._get_diskpart_script(partition_settings, boot_drive, windows_drive, recovery_drive)
                logger.debug(f"_generate_pe_script: diskpart_lines (custom empty->default) count={len(diskpart_lines)}")
                write_diskpart_script(diskpart_lines)
            else:
                diskpart_lines = [line.strip() for line in partition_settings.script.split('\n') if line.strip()]
                # 验证必须包含 ASSIGN LETTER=W 和 ASSIGN LETTER=S
                has_windows = any('ASSIGN LETTER=W' in line.upper() for line in diskpart_lines)
                has_boot = any('ASSIGN LETTER=S' in line.upper() for line in diskpart_lines)
                if not has_windows:
                    raise ValueError(f"Your diskpart script must contain the line 'ASSIGN LETTER={windows_drive}' to assign the drive letter '{windows_drive}:' to the Windows partition.")
                if not has_boot:
                    raise ValueError(f"Your diskpart script must contain the line 'ASSIGN LETTER={boot_drive}' to assign the drive letter '{boot_drive}:' to the system partition.")
                logger.debug(f"_generate_pe_script: diskpart_lines (custom provided) count={len(diskpart_lines)}")
                write_diskpart_script(diskpart_lines)
        elif isinstance(partition_settings, UnattendedPartitionSettings):
            diskpart_lines = self._get_diskpart_script(partition_settings, boot_drive, windows_drive, recovery_drive)
            logger.debug(f"_generate_pe_script: diskpart_lines (unattended) count={len(diskpart_lines)}")
            write_diskpart_script(diskpart_lines)
        elif partition_settings is None:
            # 如果没有设置，使用默认的 UnattendedPartitionSettings
            partition_settings = UnattendedPartitionSettings(
                partition_layout=PartitionLayout.GPT,
                recovery_mode=RecoveryMode.Partition,
                esp_size=Constants.EspDefaultSize,
                recovery_size=Constants.RecoveryPartitionSize
            )
            diskpart_lines = self._get_diskpart_script(partition_settings, boot_drive, windows_drive, recovery_drive)
            logger.debug(f"_generate_pe_script: diskpart_lines (None->default) count={len(diskpart_lines)}")
            write_diskpart_script(diskpart_lines)
        
        # 添加安装驱动程序的逻辑
        writer.write("rem Install drivers from $WinPEDriver$ folder\n")
        writer.write('if defined PEDRIVERS_FOLDER (\n')
        writer.write('    for /R %PEDRIVERS_FOLDER% %%f IN (*.inf) do drvload.exe "%%f"\n')
        writer.write(")\n")
        
        # 如果设置了暂停格式化，添加暂停
        if pe_settings.pause_before_formatting:
            writer.write("@echo diskpart will now partition and format your disk\n")
            writer.write("pause\n")
        
        # 执行 diskpart
        writer.write(f'diskpart.exe /s X:\\diskpart.txt || ( echo diskpart.exe encountered an error. & pause & exit /b 1 )\n')
        
        # 获取镜像索引或名称
        def get_index_or_name() -> str:
            """获取镜像索引或名称"""
            install_from = self.configuration.install_from_settings
            if isinstance(install_from, IndexInstallFromSettings):
                return f"/Index:{install_from.index}"
            elif isinstance(install_from, NameInstallFromSettings):
                return f'/Name:"{install_from.name}"'
            elif isinstance(self.configuration.edition_settings, UnattendedEditionSettings):
                writer.write('set "OS_VERSION=Windows 11"\n')
                writer.write('for /f "tokens=3 delims=." %%v in (\'ver\') do (\n')
                writer.write('    if %%v LSS 20000 set "OS_VERSION=Windows 10"\n')
                writer.write(")\n")
                return f'/Name:"%OS_VERSION% {self.configuration.edition_settings.edition.display_name}"'
            else:
                # 优先使用解析阶段记录的镜像名称（避免写入 ImageInstall 结构）
                detected = getattr(self.configuration, "_detected_image_name", None)
                if detected:
                    return f'/Name:"{detected}"'
                # 无法从配置中确定镜像名称时，降级使用解析自 XML 的默认名称
                default_name = "Windows 11 Pro"
                logger = logging.getLogger('UnattendGenerator')
                logger.warning("get_index_or_name: fallback to default image name '%s'", default_name)
                return f'/Name:"{default_name}"'
        
        index_or_name = get_index_or_name()
        compact_flag = "/Compact" if self.configuration.compact_os_mode == CompactOsModes.Always else ""
        writer.write(f'dism.exe /Apply-Image /ImageFile:%IMAGE_FILE% %SWM_PARAM% {index_or_name} /ApplyDir:{windows_drive}:\\ {compact_flag} || ( echo dism.exe encountered an error. & pause & exit /b 1 )\n')
        writer.write(f'bcdboot.exe {windows_drive}:\\Windows /s {boot_drive}: || ( echo bcdboot.exe encountered an error. & pause & exit /b 1 )\n')
        
        # 处理恢复分区
        def delete_winre():
            """删除 WinRE"""
            writer.write(f"rem Avoid creation of recovery partition\n")
            writer.write(f"del {windows_drive}:\\Windows\\System32\\Recovery\\winre.wim\n")
        
        if isinstance(partition_settings, UnattendedPartitionSettings):
            if partition_settings.recovery_mode == RecoveryMode.None_:
                delete_winre()
            elif partition_settings.recovery_mode == RecoveryMode.Folder:
                raise ValueError(f"Cannot create .cmd script when Windows RE is to be installed on {windows_drive}:.")
        elif isinstance(partition_settings, CustomPartitionSettings):
            script_lower = partition_settings.script.lower()
            keywords = ["set id=27", 'label="recovery"', 'set id="de94bba4-06d1-4d40-a16a-bfd50179d6ac"']
            if not any(keyword in script_lower for keyword in keywords):
                delete_winre()
        
        # 复制 unattend.xml
        writer.write(f'mkdir {windows_drive}:\\Windows\\Panther\n')
        writer.write(f'copy %XML_FILE% {windows_drive}:\\Windows\\Panther\\unattend.xml\n')
        
        # 添加驱动程序
        writer.write('if defined PEDRIVERS_FOLDER (\n')
        writer.write(f'    dism.exe /Add-Driver /Image:{windows_drive}:\\ /Driver:"%PEDRIVERS_FOLDER%" /Recurse\n')
        writer.write(")\n")
        
        # 8.3 文件名处理
        if pe_settings.disable_8_dot3_names:
            writer.write(f"rem Strip 8.3 file names\n")
            writer.write(f"fsutil.exe 8dot3name set {windows_drive}: 1\n")
            writer.write(f"fsutil.exe 8dot3name strip /s /f {windows_drive}:\\\n")
        
        # 禁用 Windows Defender
        if self.configuration.disable_defender:
            writer.write(f"rem Disable Windows Defender\n")
            writer.write(f"reg.exe LOAD HKLM\\mount {windows_drive}:\\Windows\\System32\\config\\SYSTEM\n")
            writer.write("for %%s in (Sense WdBoot WdFilter WdNisDrv WdNisSvc WinDefend) do reg.exe ADD HKLM\\mount\\ControlSet001\\Services\\%%s /v Start /t REG_DWORD /d 4 /f\n")
            writer.write("reg.exe UNLOAD HKLM\\mount\n")
        
        # 设置设备区域
        if isinstance(self.configuration.language_settings, UnattendedLanguageSettings):
            geo_location = self.configuration.language_settings.geo_location
            if geo_location:
                writer.write(f"rem Set device setup region\n")
                writer.write(f"reg.exe LOAD HKLM\\mount {windows_drive}:\\Windows\\System32\\config\\SOFTWARE\n")
                writer.write(f'reg.exe ADD "HKLM\\mount\\Microsoft\\Windows\\CurrentVersion\\Control Panel\\DeviceRegion" /v DeviceRegion /t REG_DWORD /d {geo_location.id} /f\n')
                writer.write("reg.exe UNLOAD HKLM\\mount\n")
        
        # 复制 $OEM$ 文件夹
        if self.configuration.use_configuration_set:
            writer.write('rem Copy $OEM$ folder if present\n')
            writer.write('set "ROBOCOPY_ARGS=/E /XX /COPY:DAT /DCOPY:DAT /R:0"\n')
            writer.write('if defined OEM_FOLDER (\n')
            writer.write(f'    if exist "%OEM_FOLDER%\\$$" robocopy.exe "%OEM_FOLDER%\\$$" {windows_drive}:\\Windows %ROBOCOPY_ARGS%\n')
            writer.write(f'    if exist "%OEM_FOLDER%\\$1" robocopy.exe "%OEM_FOLDER%\\$1" {windows_drive}:\\ %ROBOCOPY_ARGS%\n')
            available_for_oem = [d for d in letters if d not in skipped_drives]
            available_for_oem_str = ' '.join(available_for_oem)
            writer.write(f'    @for %%d in ({available_for_oem_str}) do @(\n')
            writer.write('        if exist "%OEM_FOLDER%\\%%d" robocopy.exe "%OEM_FOLDER%\\%%d" %%d:\\ %ROBOCOPY_ARGS%\n')
            writer.write("    )\n")
            writer.write(")\n")
        
        # 暂停重启
        if pe_settings.pause_before_reboot:
            writer.write("@echo Computer will now reboot\n")
            writer.write("pause\n")
        
        writer.write("rem Continue with next stage of Windows Setup after reboot\n")
        writer.write("wpeutil.exe reboot\n")
        
        # 写入 PE 脚本
        pe_lines = [line for line in writer.getvalue().split('\n') if line.strip()]
        self._write_pe_script(pe_lines)
    
    def _get_diskpart_script(self, settings: UnattendedPartitionSettings, boot_drive: str = 'S', windows_drive: str = 'W', recovery_drive: str = 'R') -> List[str]:
        """获取 diskpart 脚本（对应 C# 的 GetDiskpartScript 方法）"""
        def if_recovery(line: str) -> str:
            """如果是恢复分区模式，返回行，否则返回空"""
            return line if settings.recovery_mode == RecoveryMode.Partition else ""
        
        if settings.partition_layout == PartitionLayout.MBR:
            return [
                "SELECT DISK=0",
                "CLEAN",
                "CREATE PARTITION PRIMARY SIZE=100",
                'FORMAT QUICK FS=NTFS LABEL="System Reserved"',
                f"ASSIGN LETTER={boot_drive}",
                "ACTIVE",
                "CREATE PARTITION PRIMARY",
                if_recovery(f"SHRINK MINIMUM={settings.recovery_size}"),
                'FORMAT QUICK FS=NTFS LABEL="Windows"',
                f"ASSIGN LETTER={windows_drive}",
                if_recovery("CREATE PARTITION PRIMARY"),
                if_recovery('FORMAT QUICK FS=NTFS LABEL="Recovery"'),
                if_recovery(f"ASSIGN LETTER={recovery_drive}"),
                if_recovery("SET ID=27")
            ]
        elif settings.partition_layout == PartitionLayout.GPT:
            return [
                "SELECT DISK=0",
                "CLEAN",
                "CONVERT GPT",
                f"CREATE PARTITION EFI SIZE={settings.esp_size}",
                'FORMAT QUICK FS=FAT32 LABEL="System"',
                f"ASSIGN LETTER={boot_drive}",
                "CREATE PARTITION MSR SIZE=16",
                "CREATE PARTITION PRIMARY",
                if_recovery(f"SHRINK MINIMUM={settings.recovery_size}"),
                'FORMAT QUICK FS=NTFS LABEL="Windows"',
                f"ASSIGN LETTER={windows_drive}",
                if_recovery("CREATE PARTITION PRIMARY"),
                if_recovery('FORMAT QUICK FS=NTFS LABEL="Recovery"'),
                if_recovery(f"ASSIGN LETTER={recovery_drive}"),
                if_recovery('SET ID="de94bba4-06d1-4d40-a16a-bfd50179d6ac"'),
                if_recovery("GPT ATTRIBUTES=0x8000000000000001")
            ]
        else:
            raise ValueError(f"Unsupported partition layout: {settings.partition_layout}")
    
    def _set_compact_mode(self):
        """设置 Compact 模式（对应 C# 的 SetCompactMode 方法）"""
        ns_uri = '{urn:schemas-microsoft-com:unattend}'
        mode = self.configuration.compact_os_mode
        
        if mode == CompactOsModes.Default:
            # 移除 Compact 元素（如果存在）
            compact_elem = self.root.find(f".//{{{ns_uri}}}Compact")
            if compact_elem is not None:
                parent = self._find_parent(self.root, compact_elem)
                if parent is not None:
                    parent.remove(compact_elem)
                    
                # 如果 ImageInstall 现在为空，也移除它
                os_image = parent if parent is not None else None
                if os_image is not None and os_image.tag == f"{{{ns_uri}}}OSImage":
                    image_install = self._find_parent(self.root, os_image)
                    if image_install is not None:
                        # 检查 OSImage 是否还有其他子元素
                        has_other_children = False
                        for child in os_image:
                            if child.tag != f"{{{ns_uri}}}Compact":
                                has_other_children = True
                                break
                        if not has_other_children:
                            # 检查 ImageInstall 是否还有其他子元素
                            has_other_children = False
                            for child in image_install:
                                if child.tag != f"{{{ns_uri}}}OSImage":
                                    has_other_children = True
                                    break
                            if not has_other_children:
                                setup_component = self._find_parent(self.root, image_install)
                                if setup_component is not None:
                                    setup_component.remove(image_install)
        else:
            # 查找或创建 ImageInstall/OSImage/Compact 结构
            setup_component = self.get_or_create_element(
                Pass.windowsPE,
                "Microsoft-Windows-Setup"
            )
            
            # 查找或创建 ImageInstall（确保它在 RunSynchronous 之前）
            image_install = setup_component.find(f"{{{ns_uri}}}ImageInstall")
            if image_install is None:
                # 查找 RunSynchronous 的位置
                run_sync = setup_component.find(f"{{{ns_uri}}}RunSynchronous")
                if run_sync is not None:
                    # 在 RunSynchronous 之前插入 ImageInstall
                    index = list(setup_component).index(run_sync)
                    image_install = ET.Element(f"{{{ns_uri}}}ImageInstall")
                    setup_component.insert(index, image_install)
                else:
                    image_install = self.new_element("ImageInstall", setup_component)
            
            # 查找或创建 OSImage
            os_image = image_install.find(f"{{{ns_uri}}}OSImage")
            if os_image is None:
                os_image = self.new_element("OSImage", image_install)
            
            # 查找或创建 Compact
            compact_elem = os_image.find(f"{{{ns_uri}}}Compact")
            if compact_elem is None:
                compact_elem = self.new_element("Compact", os_image)
            
            if mode == CompactOsModes.Always:
                compact_elem.text = "true"
            elif mode == CompactOsModes.Never:
                compact_elem.text = "false"
    
    def _set_partitions(self):
        """设置分区（对应 C# 的 SetPartitions 方法）"""
        partition_settings = self.configuration.partition_settings
        if partition_settings is None:
            return
        
        if isinstance(partition_settings, InteractivePartitionSettings):
            # 移除 InstallTo 元素
            ns_uri = '{urn:schemas-microsoft-com:unattend}'
            install_to = self.root.find(f".//{{{ns_uri}}}InstallTo")
            if install_to is not None:
                parent = self._find_parent(self.root, install_to)
                if parent is not None:
                    parent.remove(install_to)
        elif isinstance(partition_settings, UnattendedPartitionSettings):
            # 写入 diskpart 脚本
            diskpart_lines = self._get_diskpart_script(partition_settings)
            self._write_diskpart_script(diskpart_lines)
            
            # 设置安装目标
            partition = 2 if partition_settings.partition_layout == PartitionLayout.MBR else 3
            self._install_to(disk=0, partition=partition)
            
            # 如果恢复模式为 None，添加禁用恢复的命令
            if partition_settings.recovery_mode == RecoveryMode.None_:
                self.specialize_script.append(
                    "ReAgentc.exe /disable; "
                    "Remove-Item -LiteralPath 'C:\\Windows\\System32\\Recovery\\Winre.wim' -Force -ErrorAction 'SilentlyContinue';"
                )
        elif isinstance(partition_settings, CustomPartitionSettings):
            # 写入自定义 diskpart 脚本
            diskpart_lines = [line.strip() for line in partition_settings.script.split('\n') if line.strip()]
            self._write_diskpart_script(diskpart_lines)
            
            # 设置安装目标
            if isinstance(partition_settings.install_to, AvailableInstallToSettings):
                # 移除 InstallTo 元素，添加 InstallToAvailablePartition
                ns_uri = '{urn:schemas-microsoft-com:unattend}'
                install_to = self.root.find(f".//{{{ns_uri}}}InstallTo")
                if install_to is not None:
                    parent = self._find_parent(self.root, install_to)
                    if parent is not None:
                        parent.remove(install_to)
                
                # 添加 InstallToAvailablePartition
                os_image = self.root.find(f".//{{{ns_uri}}}OSImage")
                if os_image is not None:
                    install_to_available = self.new_simple_element("InstallToAvailablePartition", os_image, "true")
            elif isinstance(partition_settings.install_to, CustomInstallToSettings):
                self._install_to(
                    disk=partition_settings.install_to.install_to_disk,
                    partition=partition_settings.install_to.install_to_partition
                )
            else:
                raise ValueError(f"Unsupported install to settings type: {type(partition_settings.install_to)}")
        else:
            raise ValueError(f"Unsupported partition settings type: {type(partition_settings)}")
    
    def _write_diskpart_script(self, lines: List[str]):
        """写入 diskpart 脚本（对应 C# 的 WriteScript 方法）"""
        diskpart_script = "X:\\diskpart.txt"
        diskpart_log = "X:\\diskpart.log"
        appender = self.get_appender(CommandConfig.windows_pe())
        appender.append_multiple(self.command_builder.write_to_file_pe(diskpart_script, lines))
        appender.append(
            self.command_builder.shell_command(
                f'diskpart.exe /s "{diskpart_script}" >>"{diskpart_log}" || ( type "{diskpart_log}" & echo diskpart encountered an error. & pause & exit /b 1 )'
            )
        )
    
    def _install_to(self, disk: int, partition: int):
        """设置安装目标（对应 C# 的 InstallTo 方法）"""
        ns_uri = '{urn:schemas-microsoft-com:unattend}'
        # 查找或创建 ImageInstall/OSImage/InstallTo 结构
        setup_component = self.get_or_create_element(
            Pass.windowsPE,
            "Microsoft-Windows-Setup"
        )
        
        # 查找或创建 ImageInstall
        image_install = setup_component.find(f"{{{ns_uri}}}ImageInstall")
        if image_install is None:
            image_install = self.new_element("ImageInstall", setup_component)
        
        # 查找或创建 OSImage
        os_image = image_install.find(f"{{{ns_uri}}}OSImage")
        if os_image is None:
            os_image = self.new_element("OSImage", image_install)
        
        # 查找或创建 InstallTo
        install_to = os_image.find(f"{{{ns_uri}}}InstallTo")
        if install_to is None:
            install_to = self.new_element("InstallTo", os_image)
        
        # 设置 DiskID 和 PartitionID
        disk_id = install_to.find(f"{{{ns_uri}}}DiskID")
        if disk_id is None:
            disk_id = self.new_simple_element("DiskID", install_to, str(disk))
        else:
            disk_id.text = str(disk)
        
        partition_id = install_to.find(f"{{{ns_uri}}}PartitionID")
        if partition_id is None:
            partition_id = self.new_simple_element("PartitionID", install_to, str(partition))
        else:
            partition_id.text = str(partition)


class SpecializeModifier(Modifier):
    """Specialize 脚本 Modifier（对应 C# 的 SpecializeModifier）"""
    
    def process(self):
        """处理 Specialize 脚本"""
        ns = get_namespace_map()
        ns_uri = ns['u']
        s_uri = "https://schneegans.de/windows/unattend-generator/"
        
        # 检查是否有 Extensions 部分
        extensions = self.root.find(f".//{{{s_uri}}}Extensions")
        has_extensions = extensions is not None and len(list(extensions.findall(f"{{{s_uri}}}File"))) > 0
        
        # 如果有 Extensions 或 specialize_script 不为空，需要创建 Microsoft-Windows-Deployment component
        if has_extensions or not self.specialize_script.is_empty:
            appender = self.get_appender(CommandConfig.specialize())
            
            # 如果有 Extensions，首先添加 ExtractScript 执行命令
            if has_extensions:
                extract_script_cmd = 'powershell.exe -WindowStyle "Normal" -NoProfile -Command "$xml = [xml]::new(); $xml.Load(\'C:\\Windows\\Panther\\unattend.xml\'); $sb = [scriptblock]::Create( $xml.unattend.Extensions.ExtractScript ); Invoke-Command -ScriptBlock $sb -ArgumentList $xml;"'
                appender.append(extract_script_cmd)
            
            # 如果有 specialize_script，添加执行命令
            if not self.specialize_script.is_empty:
                ps1_file = self.add_text_file("Specialize.ps1", self.specialize_script.get_script())
                appender.append(self.command_builder.invoke_power_shell_script(ps1_file))
            else:
                # 如果脚本序列为空，但 Extensions 中存在 Specialize.ps1，则调用该文件
                if isinstance(self.configuration.extensions, dict):
                    for f in self.configuration.extensions.get('files', []):
                        path = f.get('path', '')
                        if path and 'specialize.ps1' in path.lower():
                            appender.append(self.command_builder.invoke_power_shell_script(path))
                            break


class FirstLogonModifier(Modifier):
    """FirstLogon 脚本 Modifier（对应 C# 的 FirstLogonModifier）"""
    
    def process(self):
        """处理 FirstLogon 脚本"""
        import logging
        logger = logging.getLogger('UnattendGenerator')
        
        # 检查 extensions 中是否已经有 FirstLogon.ps1
        s_uri = "https://schneegans.de/windows/unattend-generator/"
        extensions = self.root.find(f".//{{{s_uri}}}Extensions")
        if extensions is not None:
            firstlogon_file = None
            for file_elem in extensions.findall(f"{{{s_uri}}}File"):
                path_attr = file_elem.get('path', '')
                if path_attr and 'FirstLogon.ps1' in path_attr:
                    firstlogon_file = file_elem
                    break
            
            if firstlogon_file is not None:
                logger.debug("FirstLogonModifier: FirstLogon.ps1 already exists in Extensions, using original content")
                # 如果 extensions 中已经有 FirstLogon.ps1，使用原始内容，不覆盖
                # 只需要确保 FirstLogonCommands 存在
                appender = self.get_appender(CommandConfig.oobe())
                # 使用 extensions 中的文件路径
                ps1_file = r"C:\Windows\Setup\Scripts\FirstLogon.ps1"
                appender.append(self.command_builder.invoke_power_shell_script(ps1_file))
                return
        
        # 如果 extensions 中没有 FirstLogon.ps1，使用 first_logon_script 生成
        if self.first_logon_script.is_empty:
            return
        
        logger.debug("FirstLogonModifier: Generating FirstLogon.ps1 from first_logon_script")
        appender = self.get_appender(CommandConfig.oobe())
        ps1_file = self.add_text_file("FirstLogon.ps1", self.first_logon_script.get_script())
        appender.append(self.command_builder.invoke_power_shell_script(ps1_file))


class UserOnceModifier(Modifier):
    """UserOnce 脚本 Modifier（对应 C# 的 UserOnceModifier）"""
    
    def process(self):
        """处理 UserOnce 脚本"""
        if self.user_once_script.is_empty:
            return
        
        ps1_file = self.add_text_file("UserOnce.ps1", self.user_once_script.get_script())
        
        def escape(s: str) -> str:
            """转义字符串"""
            return s.replace('"', '\\""')
        
        command = escape(self.command_builder.invoke_power_shell_script(ps1_file))
        self.default_user_script.append(
            f'reg.exe add "HKU\\DefaultUser\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce" /v "UnattendedSetup" /t REG_SZ /d "{command}" /f;'
        )


class DefaultUserModifier(Modifier):
    """DefaultUser 脚本 Modifier（对应 C# 的 DefaultUserModifier）"""
    
    def process(self):
        """处理 DefaultUser 脚本"""
        appender = self.get_appender(CommandConfig.specialize())
        
        # 如果脚本序列为空，尝试使用 Extensions 中的 DefaultUser.ps1
        if self.default_user_script.is_empty:
            ps1_path = None
            if isinstance(self.configuration.extensions, dict):
                for f in self.configuration.extensions.get('files', []):
                    path = f.get('path', '')
                    if path and 'defaultuser.ps1' in path.lower():
                        ps1_path = path
                        break
            if ps1_path is None:
                return
            appender.append(self.command_builder.registry_command('load "HKU\\DefaultUser" "C:\\Users\\Default\\NTUSER.DAT"'))
            appender.append(self.command_builder.invoke_power_shell_script(ps1_path))
            appender.append(self.command_builder.registry_command('unload "HKU\\DefaultUser"'))
            return
        
        ps1_file = self.add_text_file("DefaultUser.ps1", self.default_user_script.get_script())
        appender.append(self.command_builder.registry_command('load "HKU\\DefaultUser" "C:\\Users\\Default\\NTUSER.DAT"'))
        appender.append(self.command_builder.invoke_power_shell_script(ps1_file))
        appender.append(self.command_builder.registry_command('unload "HKU\\DefaultUser"'))


class WifiModifier(Modifier):
    """Wi-Fi 设置 Modifier（对应 C# 的 WifiModifier）"""
    
    def process(self):
        """处理 Wi-Fi 设置"""
        wifi_settings = self.configuration.wifi_settings
        if wifi_settings is None:
            return
        
        if isinstance(wifi_settings, SkipWifiSettings):
            # 跳过 Wi-Fi 设置，移除 WLAN 配置文件
            ns_uri = '{urn:schemas-microsoft-com:unattend}'
            wlan_profile = self.root.find(f".//{{{ns_uri}}}WLANProfile")
            if wlan_profile is not None:
                parent = self._find_parent(self.root, wlan_profile)
                if parent is not None:
                    parent.remove(wlan_profile)
        elif isinstance(wifi_settings, InteractiveWifiSettings):
            # 交互式模式，不需要操作
            pass
        elif isinstance(wifi_settings, UnattendedWifiSettings):
            # 无人值守模式，创建 WLAN 配置文件
            self._create_wlan_profile(wifi_settings)
        elif isinstance(wifi_settings, FromProfileWifiSettings):
            # 从配置文件加载
            # 这里简化处理，实际应该从文件加载 XML
            pass
        else:
            raise ValueError(f"Unsupported wifi settings type: {type(wifi_settings)}")
    
    def _create_wlan_profile(self, settings: UnattendedWifiSettings):
        """创建 WLAN 配置文件（对应 C# 的 CreateWlanProfile 方法）"""
        ns_uri = '{urn:schemas-microsoft-com:unattend}'
        
        # 查找或创建 windowsPE pass 中的 Microsoft-Windows-PnpCustomizationsNonWinPE 组件
        component = self.get_or_create_element(
            Pass.windowsPE,
            "Microsoft-Windows-PnpCustomizationsNonWinPE"
        )
        
        # 查找或创建 DriverPaths
        driver_paths = component.find(f"{{{ns_uri}}}DriverPaths")
        if driver_paths is None:
            driver_paths = self.new_element("DriverPaths", component)
        
        # 查找或创建 PathAndCredentials
        path_and_creds = driver_paths.find(f"{{{ns_uri}}}PathAndCredentials")
        if path_and_creds is None:
            path_and_creds = self.new_element("PathAndCredentials", driver_paths)
        
        # 创建 WLANProfile
        wlan_profile = self.new_element("WLANProfile", path_and_creds)
        wlan_profile.set("xmlns", "http://www.microsoft.com/networking/WLAN/profile/v1")
        
        # SSID
        self.new_simple_element("name", wlan_profile, settings.ssid)
        
        # SSIDConfig
        ssid_config = self.new_element("SSIDConfig", wlan_profile)
        ssid_elem = self.new_element("SSID", ssid_config)
        self.new_simple_element("name", ssid_elem, settings.ssid)
        
        # ConnectionType
        self.new_simple_element("ConnectionType", wlan_profile, "ESS")
        
        # ConnectionMode
        self.new_simple_element("ConnectionMode", wlan_profile, "auto")
        
        # MSM
        msm = self.new_element("MSM", wlan_profile)
        security = self.new_element("security", msm)
        
        # 根据认证方式设置
        if settings.authentication == WifiAuthentications.Open:
            auth_type = "open"
            encryption = "none"
        elif settings.authentication == WifiAuthentications.WPA2PSK:
            auth_type = "WPA2PSK"
            encryption = "AES"
        elif settings.authentication == WifiAuthentications.WPA3SAE:
            auth_type = "WPA3SAE"
            encryption = "AES"
        else:
            auth_type = "open"
            encryption = "none"
        
        auth_elem = self.new_element("authEncryption", security)
        self.new_simple_element("authentication", auth_elem, auth_type)
        self.new_simple_element("encryption", auth_elem, encryption)
        self.new_simple_element("useOneX", auth_elem, "false")
        
        if settings.authentication != WifiAuthentications.Open:
            shared_key = self.new_element("sharedKey", security)
            self.new_simple_element("keyType", shared_key, "passPhrase")
            self.new_simple_element("protected", shared_key, "false")
            self.new_simple_element("keyMaterial", shared_key, settings.password)


class ExpressSettingsModifier(Modifier):
    """快速设置 Modifier（对应 C# 的 ExpressSettingsModifier）"""
    
    def process(self):
        """处理快速设置"""
        ns_uri = '{urn:schemas-microsoft-com:unattend}'
        
        # 查找 ProtectYourPC 元素
        oobe_component = self.get_or_create_element(
            Pass.oobeSystem,
            "Microsoft-Windows-Shell-Setup"
        )
        # 查找所有 OOBE 元素（可能有多个，需要合并）
        all_oobe_elems = list(oobe_component.findall(f"{{{ns_uri}}}OOBE"))
        if len(all_oobe_elems) == 0:
            oobe_elem = self.new_element("OOBE", oobe_component)
        elif len(all_oobe_elems) == 1:
            oobe_elem = all_oobe_elems[0]
        else:
            # 如果存在多个 OOBE 元素，找到 ProtectYourPC="1" 的作为主元素
            oobe_elem = None
            for oobe in all_oobe_elems:
                protect_pc = oobe.find(f"{{{ns_uri}}}ProtectYourPC")
                if protect_pc is not None and protect_pc.text == "1":
                    oobe_elem = oobe
                    break
            if oobe_elem is None:
                oobe_elem = all_oobe_elems[0]
            
            # 合并其他 OOBE 元素到主元素
            for other_oobe in all_oobe_elems:
                if other_oobe is oobe_elem:
                    continue
                # 合并子元素
                children_to_merge = list(other_oobe)
                for child in children_to_merge:
                    child_tag_name = child.tag.split('}')[-1]
                    existing = oobe_elem.find(f"{{{ns_uri}}}{child_tag_name}")
                    if existing is None:
                        oobe_elem.append(child)
                    else:
                        # 如果已存在，对于 ProtectYourPC 优先使用 "1"
                        if child_tag_name == "ProtectYourPC":
                            if child.text == "1":
                                existing.text = "1"
                        elif child.text and child.text.strip():
                            if not existing.text or not existing.text.strip():
                                existing.text = child.text
                # 删除多余的 OOBE 元素
                oobe_component.remove(other_oobe)
        
        express_settings = self.configuration.express_settings
        if express_settings == ExpressSettingsMode.Interactive:
            # 交互式模式：移除 ProtectYourPC 元素
            protect_your_pc = oobe_elem.find(f"{{{ns_uri}}}ProtectYourPC")
            if protect_your_pc is not None:
                oobe_elem.remove(protect_your_pc)
        else:
            # 设置 ProtectYourPC
            protect_your_pc = oobe_elem.find(f"{{{ns_uri}}}ProtectYourPC")
            if protect_your_pc is None:
                protect_your_pc = self.new_simple_element("ProtectYourPC", oobe_elem, "1")
            
            if express_settings == ExpressSettingsMode.EnableAll:
                protect_your_pc.text = "1"
            elif express_settings == ExpressSettingsMode.DisableAll:
                protect_your_pc.text = "3"
            else:
                # 默认使用 DisableAll
                protect_your_pc.text = "3"
        
        # 设置 HideEULAPage（始终为 true，如果存在）
        hide_eula = oobe_elem.find(f"{{{ns_uri}}}HideEULAPage")
        if hide_eula is None:
            # 只有在非交互式模式下才添加
            if express_settings != ExpressSettingsMode.Interactive:
                self.new_simple_element("HideEULAPage", oobe_elem, "true")
        
        # 设置 HideOnlineAccountScreens（根据账户设置模式）
        hide_online = oobe_elem.find(f"{{{ns_uri}}}HideOnlineAccountScreens")
        if isinstance(self.configuration.account_settings, InteractiveLocalAccountSettings):
            # 交互式本地账户模式：设置为 true
            if hide_online is None:
                self.new_simple_element("HideOnlineAccountScreens", oobe_elem, "true")
            else:
                hide_online.text = "true"
        elif isinstance(self.configuration.account_settings, UnattendedAccountSettings):
            # 无人值守模式：设置为 false
            if hide_online is None:
                self.new_simple_element("HideOnlineAccountScreens", oobe_elem, "false")
            else:
                hide_online.text = "false"


class BloatwareModifier(Modifier):
    """预装软件移除 Modifier（对应 C# 的 BloatwareModifier）"""
    
    def process(self):
        """处理预装软件移除设置"""
        bloatwares = self.configuration.bloatwares
        if not bloatwares:
            return
        
        # 按类型分组（对应 C# 的 Remover 类）
        package_remover = _PackageRemover()
        capability_remover = _CapabilityRemover()
        feature_remover = _FeatureRemover()
        
        # 按ID排序（对应 C# 的 OrderBy(bw => bw.Id)）
        sorted_bloatwares = sorted(bloatwares, key=lambda bw: bw.id)
        
        for bloatware in sorted_bloatwares:
            for step in bloatware.steps:
                if isinstance(step, PackageBloatwareStep):
                    package_remover.add(step)
                elif isinstance(step, CapabilityBloatwareStep):
                    capability_remover.add(step)
                elif isinstance(step, OptionalFeatureBloatwareStep):
                    feature_remover.add(step)
                elif isinstance(step, CustomBloatwareStep):
                    self._handle_custom_step(bloatware.id, step)
                else:
                    raise ValueError(f"Unsupported bloatware step type: {type(step)}")
        
        # 保存移除脚本
        package_remover.save(self)
        capability_remover.save(self)
        feature_remover.save(self)
    
    def _handle_custom_step(self, bloatware_id: str, step: CustomBloatwareStep):
        """处理自定义步骤（对应 C# 的 CustomBloatwareStep switch）"""
        if bloatware_id == "RemoveOneDrive":
            self.context.specialize_script.append(
                "Remove-Item -LiteralPath 'C:\\Users\\Default\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\OneDrive.lnk', 'C:\\Windows\\System32\\OneDriveSetup.exe', 'C:\\Windows\\SysWOW64\\OneDriveSetup.exe' -ErrorAction 'Continue';"
            )
            self.context.default_user_script.append(
                "Remove-ItemProperty -LiteralPath 'Registry::HKU\\DefaultUser\\Software\\Microsoft\\Windows\\CurrentVersion\\Run' -Name 'OneDriveSetup' -Force -ErrorAction 'Continue';"
            )
        elif bloatware_id == "RemoveTeams":
            self.context.specialize_script.append(
                'reg.exe add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Communications" /v ConfigureChatAutoInstall /t REG_DWORD /d 0 /f;'
            )
        elif bloatware_id == "RemoveNotepad":
            self.context.specialize_script.append(
                '''reg.exe add "HKCR\\.txt\\ShellNew" /v ItemName /t REG_EXPAND_SZ /d "@C:\\Windows\\system32\\notepad.exe,-470" /f;
reg.exe add "HKCR\\.txt\\ShellNew" /v NullFile /t REG_SZ /f;
reg.exe add "HKCR\\txtfilelegacy" /v FriendlyTypeName /t REG_EXPAND_SZ /d "@C:\\Windows\\system32\\notepad.exe,-469" /f;
reg.exe add "HKCR\\txtfilelegacy" /ve /t REG_SZ /d "Text Document" /f;'''
            )
            self.context.default_user_script.append(
                'reg.exe add "HKU\\DefaultUser\\Software\\Microsoft\\Notepad" /v ShowStoreBanner /t REG_DWORD /d 0 /f;'
            )
        elif bloatware_id == "RemoveOutlook":
            self.context.specialize_script.append(
                "Remove-Item -LiteralPath 'Registry::HKLM\\Software\\Microsoft\\WindowsUpdate\\Orchestrator\\UScheduler_Oobe\\OutlookUpdate' -Force -ErrorAction 'SilentlyContinue';"
            )
        elif bloatware_id == "RemoveDevHome":
            self.context.specialize_script.append(
                "Remove-Item -LiteralPath 'Registry::HKLM\\Software\\Microsoft\\WindowsUpdate\\Orchestrator\\UScheduler_Oobe\\DevHomeUpdate' -Force -ErrorAction 'SilentlyContinue';"
            )
        elif bloatware_id == "RemoveCopilot":
            self.context.user_once_script.append(
                "Get-AppxPackage -Name 'Microsoft.Windows.Ai.Copilot.Provider' | Remove-AppxPackage;"
            )
            self.context.default_user_script.append(
                'reg.exe add "HKU\\DefaultUser\\Software\\Policies\\Microsoft\\Windows\\WindowsCopilot" /v TurnOffWindowsCopilot /t REG_DWORD /d 1 /f;'
            )
        elif bloatware_id == "RemoveXboxApps":
            self.context.default_user_script.append(
                'reg.exe add "HKU\\DefaultUser\\Software\\Microsoft\\Windows\\CurrentVersion\\GameDVR" /v AppCaptureEnabled /t REG_DWORD /d 0 /f;'
            )
        elif bloatware_id == "RemoveInternetExplorer":
            self.context.default_user_script.append(
                'reg.exe add "HKU\\DefaultUser\\Software\\Microsoft\\Internet Explorer\\LowRegistry\\Audio\\PolicyConfig\\PropertyStore" /f;'
            )
        else:
            raise ValueError(f"Unsupported custom bloatware ID: {bloatware_id}")


class _Remover:
    """移除器基类（对应 C# 的 Remover<T>）"""
    
    def __init__(self):
        self.selectors: List[str] = []
    
    def add(self, step: SelectorBloatwareStep):
        """添加选择器"""
        self.selectors.append(step.selector)
    
    def save(self, parent: BloatwareModifier):
        """保存移除脚本"""
        if not self.selectors:
            return
        
        ps1_content = self._get_remove_command()
        ps1_file = parent.add_text_file(f"{self._get_base_name()}.ps1", ps1_content)
        parent.context.specialize_script.invoke_file(ps1_file)
    
    def _get_remove_command(self) -> str:
        """生成移除命令（对应 C# 的 GetRemoveCommand）"""
        writer = []
        writer.append("$selectors = @(")
        for selector in self.selectors:
            writer.append(f"\t'{selector}';")
        writer.append(");")
        writer.append(f"$getCommand = {self._get_get_command()};")
        writer.append(f"$filterCommand = {self._get_filter_command()};")
        writer.append(f"$removeCommand = {self._get_remove_command_inner()};")
        writer.append(f"$type = '{self._get_type()}';")
        writer.append(f"$logfile = 'C:\\Windows\\Setup\\Scripts\\{self._get_base_name()}.log';")
        
        # 添加 RemoveBloatware.ps1 的模板内容
        writer.append("""& {
	$installed = & $getCommand;
	foreach( $selector in $selectors ) {
		$result = [ordered] @{
			Selector = $selector;
		};
		$found = $installed | Where-Object -FilterScript $filterCommand;
		if( $found ) {
			$result.Output = $found | & $removeCommand;
			if( $? ) {
				$result.Message = "$type removed.";
			} else {
				$result.Message = "$type not removed.";
				$result.Error = $Error[0];
			}
		} else {
			$result.Message = "$type not installed.";
		}
		$result | ConvertTo-Json -Depth 3 -Compress;
	}
} *>&1 | Out-String -Width 1KB -Stream >> $logfile;""")
        
        return '\n'.join(writer)
    
    def _get_get_command(self) -> str:
        """获取命令（子类实现）"""
        raise NotImplementedError
    
    def _get_filter_command(self) -> str:
        """过滤命令（子类实现）"""
        raise NotImplementedError
    
    def _get_remove_command_inner(self) -> str:
        """移除命令（子类实现）"""
        raise NotImplementedError
    
    def _get_base_name(self) -> str:
        """基础名称（子类实现）"""
        raise NotImplementedError
    
    def _get_type(self) -> str:
        """类型（子类实现）"""
        raise NotImplementedError


class _PackageRemover(_Remover):
    """包移除器（对应 C# 的 PackageRemover）"""
    
    def _get_get_command(self) -> str:
        return """{
      Get-AppxProvisionedPackage -Online;
    }"""
    
    def _get_filter_command(self) -> str:
        return """{
      $_.DisplayName -eq $selector;
    }"""
    
    def _get_remove_command_inner(self) -> str:
        return """{
      [CmdletBinding()]
      param(
        [Parameter( Mandatory, ValueFromPipeline )]
        $InputObject
      );
      process {
        $InputObject | Remove-AppxProvisionedPackage -AllUsers -Online -ErrorAction 'Continue';
      }
    }"""
    
    def _get_base_name(self) -> str:
        return "RemovePackages"
    
    def _get_type(self) -> str:
        return "Package"


class _CapabilityRemover(_Remover):
    """功能移除器（对应 C# 的 CapabilityRemover）"""
    
    def _get_get_command(self) -> str:
        return """{
      Get-WindowsCapability -Online | Where-Object -Property 'State' -NotIn -Value @(
        'NotPresent';
        'Removed';
      );
    }"""
    
    def _get_filter_command(self) -> str:
        return """{
      ($_.Name -split '~')[0] -eq $selector;
    }"""
    
    def _get_remove_command_inner(self) -> str:
        return """{
      [CmdletBinding()]
      param(
        [Parameter( Mandatory, ValueFromPipeline )]
        $InputObject
      );
      process {
        $InputObject | Remove-WindowsCapability -Online -ErrorAction 'Continue';
      }
    }"""
    
    def _get_base_name(self) -> str:
        return "RemoveCapabilities"
    
    def _get_type(self) -> str:
        return "Capability"


class _FeatureRemover(_Remover):
    """功能移除器（对应 C# 的 FeatureRemover）"""
    
    def _get_get_command(self) -> str:
        return """{
      Get-WindowsOptionalFeature -Online | Where-Object -Property 'State' -NotIn -Value @(
        'Disabled';
        'DisabledWithPayloadRemoved';
      );
    }"""
    
    def _get_filter_command(self) -> str:
        return """{
      $_.FeatureName -eq $selector;
    }"""
    
    def _get_remove_command_inner(self) -> str:
        return """{
      [CmdletBinding()]
      param(
        [Parameter( Mandatory, ValueFromPipeline )]
        $InputObject
      );
      process {
        $InputObject | Disable-WindowsOptionalFeature -Online -Remove -NoRestart -ErrorAction 'Continue';
      }
    }"""
    
    def _get_base_name(self) -> str:
        return "RemoveFeatures"
    
    def _get_type(self) -> str:
        return "Feature"


class WdacModifier(Modifier):
    """WDAC 设置 Modifier（对应 C# 的 WdacModifier）"""
    
    def process(self):
        """处理 WDAC 设置"""
        wdac_settings = self.configuration.wdac_settings
        if wdac_settings is None or isinstance(wdac_settings, SkipWdacSettings):
            return
        elif isinstance(wdac_settings, ConfigureWdacSettings):
            import uuid
            guid = str(uuid.uuid4())
            template_file = r"C:\Windows\schemas\CodeIntegrity\ExamplePolicies\DefaultWindows_Enforced.xml"
            active_folder = r"C:\Windows\System32\CodeIntegrity\CiPolicies\Active"
            
            ps1_content = f"""Set-StrictMode -Version 'Latest';
$ErrorActionPreference = 'Stop';
$(
  try {{
    $guid = '{guid}';
    $xml = "{active_folder}\\${{guid}}.xml";
    $binary = "{active_folder}\\${{guid}}.cip";
    Copy-Item -LiteralPath '{template_file}' -Destination $xml;
"""
            
            # SetRuleOption 调用
            ps1_content += "    Set-RuleOption -FilePath $xml -Option 0;\n"
            ps1_content += "    Set-RuleOption -FilePath $xml -Option 6;\n"
            ps1_content += "    Set-RuleOption -FilePath $xml -Option 9;\n"
            ps1_content += "    Set-RuleOption -FilePath $xml -Option 16;\n"
            ps1_content += "    Set-RuleOption -FilePath $xml -Option 18;\n"
            ps1_content += "    Set-RuleOption -FilePath $xml -Option 5 -Delete;\n"
            
            if wdac_settings.script_mode == WdacScriptModes.Unrestricted:
                ps1_content += "    Set-RuleOption -FilePath $xml -Option 11;\n"
            
            if wdac_settings.audit_mode == WdacAuditModes.Auditing:
                ps1_content += "    Set-RuleOption -FilePath $xml -Option 3;\n"
                ps1_content += "    Set-RuleOption -FilePath $xml -Option 10;\n"
            elif wdac_settings.audit_mode == WdacAuditModes.AuditingOnBootFailure:
                ps1_content += "    Set-RuleOption -FilePath $xml -Option 10;\n"
            # Enforcement 不需要额外选项
            
            ps1_content += r"""    Merge-CIPolicy -PolicyPaths $xml -OutputFilePath $xml -Rules $(
      @(
        New-CIPolicyRule -FilePathRule 'C:\Windows\*';
        New-CIPolicyRule -FilePathRule 'C:\Program Files\*';
        New-CIPolicyRule -FilePathRule 'C:\Program Files (x86)\*';
"""
            # 添加已知可写文件夹的Deny规则（对应C#的known-writeable-folders.txt）
            # 这些是常见的可写文件夹，需要被WDAC策略拒绝
            known_writeable_folders = [
                r"C:\Users\*",
                r"C:\ProgramData\*",
                r"C:\Temp\*",
                r"C:\Tmp\*",
                r"C:\Windows\Temp\*",
                r"C:\Windows\Tmp\*",
            ]
            for folder in known_writeable_folders:
                ps1_content += f"        New-CIPolicyRule -FilePathRule '{folder}' -Deny;\n"
            
            ps1_content += """      ) | ForEach-Object -Process {
        $_;
      };
    );
    $doc = [xml]::new();
    $doc.Load( $xml );
    $nsmgr = [System.Xml.XmlNamespaceManager]::new( $doc.NameTable );
    $nsmgr.AddNamespace( 'pol', 'urn:schemas-microsoft-com:sipolicy' );
    $doc.SelectSingleNode( '/pol:SiPolicy/pol:PolicyID', $nsmgr ).InnerText = $guid;
    $doc.SelectSingleNode( '/pol:SiPolicy/pol:BasePolicyID', $nsmgr ).InnerText = $guid;
    $node = $doc.SelectSingleNode( '//pol:SigningScenario[@Value="12"]/pol:ProductSigners/pol:AllowedSigners', $nsmgr );
    $node.ParentNode.RemoveChild( $node );
    $doc.Save( $xml );
    ConvertFrom-CIPolicy -XmlFilePath $xml -BinaryFilePath $binary;
  }} catch {{
    $_;
  }}
) *>&1 | Out-String -Width 1KB -Stream >> 'C:\\Windows\\Setup\\Scripts\\Wdac.log';
"""
            ps1_file = self.add_text_file("Wdac.ps1", ps1_content)
            self.context.specialize_script.invoke_file(ps1_file)
        else:
            raise ValueError(f"Unsupported wdac settings type: {type(wdac_settings)}")


class ProcessorArchitectureModifier(Modifier):
    """处理器架构 Modifier（对应 C# 的 ProcessorArchitectureModifier）"""
    
    def process(self):
        """处理处理器架构设置"""
        processor_architectures = self.configuration.processor_architectures
        if not processor_architectures:
            raise ValueError("At least one processor architecture must be selected.")
        
        # 查找所有带有 processorArchitecture 属性的元素（对应 C# 的 SelectNodesOrEmpty）
        # 注意：需要收集所有匹配的元素，因为我们在迭代过程中会修改树结构
        components_to_process = []
        for component in self.root.iter():
            if component.get('processorArchitecture') is not None:
                components_to_process.append(component)
        
        for component in components_to_process:
            archs = iter(processor_architectures)
            first_arch = next(archs, None)
            if first_arch is None:
                raise ValueError("At least one processor architecture must be selected.")
            
            # 设置第一个架构（对应 C# 的 SetAttribute）
            component.set('processorArchitecture', first_arch.value)
            
            # 为其他架构创建副本（对应 C# 的 CloneNode(true) 和 InsertAfter）
            parent = self._find_parent(self.root, component)
            if parent is not None:
                current_element = component
                for arch in archs:
                    # 深度克隆元素（对应 C# 的 CloneNode(true)）
                    copy = ET.fromstring(ET.tostring(current_element, encoding='unicode'))
                    copy.set('processorArchitecture', arch.value)
                    # 在current_element之后插入（对应 C# 的 InsertAfter）
                    parent.insert(list(parent).index(current_element) + 1, copy)
                    current_element = copy


class PersonalizationModifier(Modifier):
    """个性化设置 Modifier（对应 C# 的 PersonalizationModifier）"""
    
    def process(self):
        """处理个性化设置"""
        # 颜色设置
        color_settings = self.configuration.color_settings
        if isinstance(color_settings, CustomColorSettings):
            ps1_file = self.add_text_file("SetColorTheme.ps1", f"""
$lightThemeSystem = {color_settings.system_theme.value};
$lightThemeApps = {color_settings.apps_theme.value};
$accentColorOnStart = {1 if color_settings.accent_color_on_start else 0};
$enableTransparency = {1 if color_settings.enable_transparency else 0};
$htmlAccentColor = '{color_settings.accent_color}';
""")
            self.context.default_user_script.append(
                f'reg.exe add "HKU\\DefaultUser\\Software\\Microsoft\\Windows\\DWM" /v ColorPrevalence /t REG_DWORD /d {1 if color_settings.accent_color_on_borders else 0} /f;'
            )
            self.context.user_once_script.invoke_file(ps1_file)
            self.context.user_once_script.restart_explorer()
        
        # 壁纸设置
        wallpaper_settings = self.configuration.wallpaper_settings
        if isinstance(wallpaper_settings, ScriptWallpaperSettings):
            image_file = r"C:\Windows\Setup\Scripts\Wallpaper"
            getter_file = self.add_text_file("GetWallpaper.ps1", wallpaper_settings.script)
            self.context.specialize_script.append(f"""
try {{
  $bytes = Get-Content -LiteralPath '{getter_file}' -Raw | Invoke-Expression;
  [System.IO.File]::WriteAllBytes( '{image_file}', $bytes );
}} catch {{
  $_;
}}
""")
            ps1_file = self.add_text_file("SetWallpaper.ps1", f"Set-WallpaperImage -LiteralPath '{image_file}';")
            self.context.user_once_script.invoke_file(ps1_file)
        elif isinstance(wallpaper_settings, SolidWallpaperSettings):
            ps1_file = self.add_text_file("SetWallpaper.ps1", f"Set-WallpaperColor -HtmlColor '{wallpaper_settings.color}';")
            self.context.user_once_script.invoke_file(ps1_file)
        
        # 锁屏设置
        lock_screen_settings = self.configuration.lock_screen_settings
        if isinstance(lock_screen_settings, ScriptLockScreenSettings):
            image_file = r"C:\Windows\Setup\Scripts\LockScreenImage"
            getter_file = self.add_text_file("GetLockScreenImage.ps1", lock_screen_settings.script)
            self.context.specialize_script.append(f"""
try {{
  $bytes = Get-Content -LiteralPath '{getter_file}' -Raw | Invoke-Expression;
  [System.IO.File]::WriteAllBytes( '{image_file}', $bytes );
  reg.exe add "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\PersonalizationCSP" /v LockScreenImagePath /t REG_SZ /d "{image_file}" /f;
}} catch {{
  $_;
}}
""")


class ScriptModifier(Modifier):
    """自定义脚本 Modifier（对应 C# 的 ScriptModifier）"""
    
    def process(self):
        """处理自定义脚本设置"""
        import logging
        logger = logging.getLogger('UnattendGenerator')
        
        script_settings = self.configuration.script_settings
        if not script_settings or not script_settings.scripts:
            logger.debug("ScriptModifier: No script_settings or no scripts")
            return
        
        logger.debug(f"ScriptModifier: Processing {len(script_settings.scripts)} scripts")
        
        # 如果需要重启 Explorer
        if script_settings.restart_explorer:
            self.context.user_once_script.restart_explorer()
        
        # 创建脚本信息列表
        infos = []
        for index, script in enumerate(script_settings.scripts):
            info = self._create_script_info(script, index)
            infos.append(info)
            logger.debug(f"ScriptModifier: Created script info {index}: phase={script.phase}, type={script.type}, file_name={info['file_name']}")
        
        # 处理每个脚本
        for info in infos:
            self._write_script_content(info)
            self._call_script(info)
    
    def _create_script_info(self, script: Script, index: int) -> Dict[str, Any]:
        """创建脚本信息（对应 C# 的 ScriptInfo.Create）"""
        folder = r"C:\Windows\Setup\Scripts"
        key = f"unattend-{index + 1:02x}"
        extension = script.type.value.lower()
        file_name = f"{key}.{extension}"
        file_path = f"{folder}\\{file_name}"
        
        return {
            'script': script,
            'file_path': file_path,
            'file_name': file_name,
            'key': key
        }
    
    def _write_script_content(self, info: Dict[str, Any]):
        """写入脚本内容（对应 C# 的 WriteScriptContent）"""
        import logging
        logger = logging.getLogger('UnattendGenerator')
        
        script = info['script']
        content = script.content
        
        logger.debug(f"ScriptModifier._write_script_content: Writing script file {info['file_name']}, phase={script.phase}, type={script.type}, content_length={len(content)}")
        
        # 如果是注册表脚本，添加头部（如果不存在）
        if script.type == ScriptType.Reg:
            prefix = "Windows Registry Editor Version 5.00"
            if not content.startswith(prefix):
                content = f"{prefix}\r\n\r\n{content}"
        
        self.add_text_file(info['file_name'], content)
    
    def _call_script(self, info: Dict[str, Any]):
        """调用脚本（对应 C# 的 CallScript）"""
        script = info['script']
        command = self._get_command(info)
        
        # 根据阶段添加到相应的脚本序列
        if script.type == ScriptType.Ps1:
            # PowerShell 脚本使用 invoke_file
            if script.phase == ScriptPhase.System:
                self.context.specialize_script.invoke_file(info['file_path'])
            elif script.phase == ScriptPhase.FirstLogon:
                self.context.first_logon_script.invoke_file(info['file_path'])
            elif script.phase == ScriptPhase.UserOnce:
                self.context.user_once_script.invoke_file(info['file_path'])
            elif script.phase == ScriptPhase.DefaultUser:
                self.context.default_user_script.invoke_file(info['file_path'])
        else:
            # 其他脚本类型使用 append
            if script.phase == ScriptPhase.System:
                self.context.specialize_script.append(command + ";")
            elif script.phase == ScriptPhase.FirstLogon:
                self.context.first_logon_script.append(command + ";")
            elif script.phase == ScriptPhase.UserOnce:
                self.context.user_once_script.append(command + ";")
            elif script.phase == ScriptPhase.DefaultUser:
                self.context.default_user_script.append(command + ";")
    
    def _get_command(self, info: Dict[str, Any]) -> str:
        """获取命令（对应 C# 的 CommandHelper.GetCommand）"""
        script = info['script']
        builder = self.context.command_builder
        
        if script.type == ScriptType.Cmd:
            return builder.raw(info['file_path'])
        elif script.type == ScriptType.Ps1:
            return builder.invoke_power_shell_script(info['file_path'])
        elif script.type == ScriptType.Reg:
            return builder.registry_command(f'import "{info["file_path"]}"')
        elif script.type == ScriptType.Vbs:
            return builder.invoke_vbscript(info['file_path'])
        elif script.type == ScriptType.Js:
            return builder.invoke_jscript(info['file_path'])
        else:
            raise ValueError(f"Unsupported script type: {script.type}")


class ComponentsModifier(Modifier):
    """XML 标记 Modifier（对应 C# 的 ComponentsModifier）"""
    
    def _import_node(self, source: ET.Element, default_ns: str) -> ET.Element:
        """导入节点（对应 C# 的 Document.ImportNode）"""
        # 创建新元素，使用正确的命名空间
        tag = source.tag
        # 如果标签没有命名空间前缀，添加默认命名空间
        if not tag.startswith('{'):
            tag = f"{{{default_ns}}}{tag}"
        
        new_elem = ET.Element(tag)
        
        # 复制属性
        for key, value in source.attrib.items():
            new_elem.set(key, value)
        
        # 复制文本
        if source.text:
            new_elem.text = source.text
        
        # 复制 tail
        if source.tail:
            new_elem.tail = source.tail
        
        # 递归复制子元素
        for child in source:
            new_elem.append(self._import_node(child, default_ns))
        
        return new_elem
    
    def process(self):
        """处理 XML 标记设置"""
        components = self.configuration.components
        if not components:
            return
        
        ns_uri = '{urn:schemas-microsoft-com:unattend}'
        ns_uri_clean = 'urn:schemas-microsoft-com:unattend'
        wcm_uri = 'http://schemas.microsoft.com/WMIConfig/2002/State'
        
        for (component_name, pass_), xml_markup in components.items():
            # 查找或创建 settings 元素
            # 注意：需要查找所有 settings 元素，包括已存在的（即使为空）
            settings = None
            # 首先尝试使用命名空间查找
            for elem in self.root.findall(f"{{{ns_uri}}}settings"):
                if elem.get('pass') == pass_.value:
                    settings = elem
                    break
            
            # 如果没找到，尝试不使用命名空间查找（处理默认命名空间的情况）
            if settings is None:
                for elem in self.root.iter():
                    # 检查是否是settings元素（可能没有命名空间前缀）
                    tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                    if tag_name == 'settings' and elem.get('pass') == pass_.value:
                        settings = elem
                        break
            
            if settings is None:
                # 创建 settings 元素，使用正确的命名空间
                settings = ET.SubElement(self.root, f"{{{ns_uri}}}settings")
                settings.set("pass", pass_.value)
            
            # 查找或创建 component 元素
            component = None
            for elem in settings.findall(f"{{{ns_uri}}}component"):
                if elem.get('name') == component_name:
                    component = elem
                    break
            
            if component is None:
                component = ET.SubElement(settings, f"{{{ns_uri}}}component")
                component.set("name", component_name)
                component.set("processorArchitecture", "x86")
                component.set("publicKeyToken", "31bf3856ad364e35")
                component.set("language", "neutral")
                component.set("versionScope", "nonSxS")
            else:
                # 清空现有内容
                component.clear()
                component.set("name", component_name)
                component.set("processorArchitecture", "x86")
                component.set("publicKeyToken", "31bf3856ad364e35")
                component.set("language", "neutral")
                component.set("versionScope", "nonSxS")
            
            # 验证 XML 格式
            try:
                # 包装 XML 标记以验证格式
                wrapped_xml = f'<root xmlns="urn:schemas-microsoft-com:unattend" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">{xml_markup}</root>'
                new_doc = ET.fromstring(wrapped_xml)
            except ET.ParseError as e:
                raise ValueError(f"Your XML markup '{xml_markup}' is not well-formed: {e}")
            
            # 检查是否包含 settings 或 component 元素
            for elem in new_doc.iter():
                local_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if local_name in ['settings', 'component']:
                    raise ValueError(f"You must not include elements 'settings' or 'component' with your XML markup '{xml_markup}'.")
            
            # 复制子节点到 component（使用正确的命名空间）
            # 使用 Document.ImportNode 的等价方法：直接复制元素
            for child in new_doc:
                # 使用 deep copy 复制元素及其所有子元素
                # 但需要确保命名空间正确
                imported_child = self._import_node(child, ns_uri_clean)
                component.append(imported_child)


class EmptyElementsModifier(Modifier):
    """空元素移除 Modifier（对应 C# 的 EmptyElementsModifier）"""
    
    def process(self):
        """移除所有空元素（无子节点、无属性）"""
        modified = True
        while modified:
            modified = False
            # 收集所有元素（需要先收集，因为在迭代过程中修改树结构）
            all_elements = list(self.root.iter())
            
            for elem in all_elements:
                if self._should_drop(elem):
                    parent = self._find_parent(self.root, elem)
                    if parent is not None:
                        parent.remove(elem)
                        modified = True
    
    @staticmethod
    def _should_drop(elem: ET.Element) -> bool:
        """判断是否应该移除元素（对应 C# 的 Drop 方法）"""
        # 如果有子节点，不移除
        if len(elem) > 0:
            return False
        
        # 如果有属性，不移除
        if elem.attrib:
            return False
        
        # 如果有文本内容（包括空字符串），不移除
        # 注意：elem.text 可能是 None 或空字符串，空字符串也应该保留
        if elem.text is not None:
            return False
        
        # 如果有 tail 文本，不移除
        if elem.tail and elem.tail.strip():
            return False
        
        return True


class OrderModifier(Modifier):
    """顺序 Modifier（对应 C# 的 OrderModifier）"""
    
    def process(self):
        """为 RunSynchronous、RunAsynchronous 和 FirstLogonCommands 中的子元素添加 Order"""
        import logging
        logger = logging.getLogger('UnattendGenerator')
        ns_uri = '{urn:schemas-microsoft-com:unattend}'
        wcm_uri = 'http://schemas.microsoft.com/WMIConfig/2002/State'
        
        # 查找所有 RunSynchronous、RunAsynchronous 和 FirstLogonCommands 容器
        total_containers = 0
        total_children = 0
        for container in self.root.iter():
            if container.tag in [f"{{{ns_uri}}}RunSynchronous", f"{{{ns_uri}}}RunAsynchronous", f"{{{ns_uri}}}FirstLogonCommands"]:
                total_containers += 1
                # 为每个子元素添加 Order
                pos = 1
                for child in list(container):
                    if child.tag.startswith(f"{{{ns_uri}}}"):
                        total_children += 1
                        # 检查是否已有 Order 元素
                        has_order = False
                        for order_elem in child.findall(f"{{{ns_uri}}}Order"):
                            has_order = True
                            break
                        
                        if has_order:
                            raise ValueError(f"'{ET.tostring(child, encoding='unicode')}' already contains an <Order> element.")
                        
                        # 创建 Order 元素
                        order = ET.SubElement(child, f"{{{ns_uri}}}Order")
                        order.text = str(pos)
                        pos += 1
                        
                        # 设置 wcm:action="add" 属性
                        child.set(f"{{{wcm_uri}}}action", "add")
        logger.debug(f"OrderModifier: processed {total_containers} container(s), added orders to {total_children} child(ren)")


class MergeOOBEModifier(Modifier):
    """合并重复的 OOBE 元素 Modifier"""
    
    def process(self):
        """合并重复的 OOBE 元素"""
        ns_uri = '{urn:schemas-microsoft-com:unattend}'
        
        # 使用 iter 查找所有 settings 元素（因为 findall 可能有命名空间问题）
        all_settings = [e for e in self.root.iter() if e.tag == f"{ns_uri}settings"]
        for settings in all_settings:
            # 使用 iter 查找所有 component 元素
            all_components = [e for e in settings if e.tag == f"{ns_uri}component"]
            for component in all_components:
                # 直接遍历 component 的子元素查找 OOBE
                oobe_elems = []
                for child in component:
                    if child.tag == f"{ns_uri}OOBE":
                        oobe_elems.append(child)
                
                if len(oobe_elems) > 1:
                    # 找到 ProtectYourPC="1" 的 OOBE 元素作为主元素，如果没有则使用第一个
                    main_oobe = None
                    for oobe in oobe_elems:
                        # 直接遍历子元素查找 ProtectYourPC
                        for child in oobe:
                            if child.tag.split('}')[-1] == 'ProtectYourPC' and child.text == "1":
                                main_oobe = oobe
                                break
                        if main_oobe is not None:
                            break
                    if main_oobe is None:
                        main_oobe = oobe_elems[0]
                    
                    # 合并其他 OOBE 元素到主元素
                    for other_oobe in oobe_elems:
                        if other_oobe is main_oobe:
                            continue
                        # 合并子元素（需要先收集所有子元素，因为迭代过程中会修改）
                        children_to_merge = list(other_oobe)
                        for child in children_to_merge:
                            child_tag_name = child.tag.split('}')[-1]
                            # 在主元素中查找相同标签的子元素
                            existing = None
                            for main_child in main_oobe:
                                if main_child.tag.split('}')[-1] == child_tag_name:
                                    existing = main_child
                                    break
                            
                            if existing is None:
                                # 如果不存在，添加
                                main_oobe.append(child)
                            else:
                                # 如果已存在，优先使用非空值，对于 ProtectYourPC 优先使用 "1"
                                if child_tag_name == "ProtectYourPC":
                                    # ProtectYourPC 优先使用 "1"
                                    if child.text == "1":
                                        existing.text = "1"
                                    elif existing.text != "1" and child.text:
                                        # 如果主元素不是 "1"，但子元素有值，使用子元素的值（除非子元素是 "3"）
                                        if child.text != "3":
                                            existing.text = child.text
                                elif child.text and child.text.strip():
                                    if not existing.text or not existing.text.strip():
                                        existing.text = child.text
                        # 删除多余的 OOBE 元素
                        component.remove(other_oobe)
                    
                    # 合并完成后，移除原始 XML 中不存在的元素（如 HideWirelessSetupInOOBE）
                    # 这些元素可能是从模板 XML 或其他 Modifier 添加的
                    # 只保留标准的 OOBE 元素：ProtectYourPC, HideEULAPage, HideOnlineAccountScreens
                    allowed_oobe_elements = {'ProtectYourPC', 'HideEULAPage', 'HideOnlineAccountScreens', 'FirstLogonCommands'}
                    children_to_remove = []
                    for child in main_oobe:
                        child_tag_name = child.tag.split('}')[-1]
                        if child_tag_name not in allowed_oobe_elements:
                            children_to_remove.append(child)
                    for child in children_to_remove:
                        main_oobe.remove(child)


class PrettyModifier(Modifier):
    """美化 Modifier（对应 C# 的 PrettyModifier）"""
    
    def process(self):
        """美化 XML（设置所有元素为非空，规范化，移除空白文本节点）"""
        # 将所有元素设置为非空（在 ElementTree 中，空元素会自动处理）
        # 规范化 XML（移除空白文本节点）
        self._normalize_xml(self.root)
    
    def _normalize_xml(self, elem: ET.Element):
        """规范化 XML（移除空白文本节点）"""
        # 处理文本内容
        if elem.text:
            elem.text = elem.text.strip() if elem.text.strip() else None
        
        # 处理 tail（在 ElementTree 中，tail 是元素结束标签后的文本）
        if elem.tail:
            elem.tail = elem.tail.strip() if elem.tail.strip() else None
        
        # 递归处理子元素
        for child in elem:
            self._normalize_xml(child)


# ========================================
# UnattendGenerator 类
# ========================================

class UnattendGenerator:
    """Unattend XML 生成器（纯 Python 实现）"""
    
    def __init__(self, data_dir: Optional[Path] = None, lang: str = 'en'):
        """
        初始化生成器
        
        Args:
            data_dir: 数据文件目录，默认为 data/unattend
            lang: 语言代码，用于 i18n 适配
        """
        if data_dir is None:
            # 默认使用 src/backend 目录
            self.data_dir = Path(__file__).parent
        else:
            self.data_dir = data_dir
        self.lang = lang
        
        # 加载数据文件
        self._load_data()
    
    def _load_data(self):
        """加载所有数据文件（完全匹配 C# 项目的加载顺序和逻辑）"""
        # 1. 加载 Bloatware（需要 TypeNameHandling，但 Python 中需要手动处理 Steps）
        bloatware_file = self.data_dir / 'Bloatware.json'
        if bloatware_file.exists():
            with open(bloatware_file, 'r', encoding='utf-8') as f:
                bloatware_data = json.load(f)
            
            # 应用 i18n 适配
            bloatware_data = load_data_with_i18n(bloatware_file, self.lang)
            
            # 手动处理 Bloatware 对象（因为 Steps 需要根据 $type 创建不同的类）
            self.bloatwares = {}
            for item in bloatware_data:
                display_name = item.get('DisplayName', '')
                token = item.get('Token')
                
                # 处理 Steps（根据 $type 创建相应的 BloatwareStep）
                steps = []
                for step_data in item.get('Steps', []):
                    step_type = step_data.get('$type', '')
                    applies_to = step_data.get('AppliesTo', [])
                    
                    if 'PackageBloatwareStep' in step_type:
                        selector = step_data.get('Selector', '')
                        steps.append(PackageBloatwareStep(applies_to, selector))
                    elif 'CapabilityBloatwareStep' in step_type:
                        selector = step_data.get('Selector', '')
                        steps.append(CapabilityBloatwareStep(applies_to, selector))
                    elif 'OptionalFeatureBloatwareStep' in step_type:
                        selector = step_data.get('Selector', '')
                        steps.append(OptionalFeatureBloatwareStep(applies_to, selector))
                    elif 'CustomBloatwareStep' in step_type:
                        steps.append(CustomBloatwareStep(applies_to))
                    else:
                        # 未知类型，跳过
                        continue
                
                bloatware = Bloatware(
                    display_name=display_name,
                    token=token,
                    steps=steps
                )
                self.bloatwares[bloatware.id] = bloatware
        else:
            self.bloatwares = {}
        
        # 2. 加载 Component
        component_file = self.data_dir / 'Component.json'
        if component_file.exists():
            component_data = load_data_with_i18n(component_file, self.lang)
            self.components = to_keyed_dictionary(component_data, Component)
        else:
            self.components = {}
        
        # 3. 加载 ImageLanguage
        image_language_file = self.data_dir / 'ImageLanguage.json'
        if image_language_file.exists():
            image_language_data = load_data_with_i18n(image_language_file, self.lang)
            self.image_languages = to_keyed_dictionary(image_language_data, ImageLanguage)
        else:
            self.image_languages = {}
        
        # 4. 加载 KeyboardIdentifier
        keyboard_file = self.data_dir / 'KeyboardIdentifier.json'
        if keyboard_file.exists():
            keyboard_data = load_data_with_i18n(keyboard_file, self.lang)
            self.keyboard_identifiers = to_keyed_dictionary(keyboard_data, KeyboardIdentifier)
        else:
            self.keyboard_identifiers = {}
        
        # 5. 加载 GeoLocation
        geoid_file = self.data_dir / 'GeoId.json'
        if geoid_file.exists():
            geoid_data = load_data_with_i18n(geoid_file, self.lang)
            self.geo_locations = to_keyed_dictionary(geoid_data, GeoLocation)
        else:
            self.geo_locations = {}
        
        # 6. 加载 UserLocale（需要 KeyboardConverter 和 GeoLocationConverter）
        # 必须先加载 KeyboardIdentifier 和 GeoLocation，因为 UserLocale 需要引用它们
        locale_file = self.data_dir / 'UserLocale.json'
        if locale_file.exists():
            with open(locale_file, 'r', encoding='utf-8') as f:
                locale_data = json.load(f)
            
            # 处理 i18n
            locale_data = load_data_with_i18n(locale_file, self.lang)
            
            # 创建 UserLocale 对象，处理 KeyboardLayout 和 GeoLocation 引用
            self.user_locales = {}
            for item in locale_data:
                key = item.get('Id', '')
                if key:
                    # 处理 KeyboardLayout 引用（类似 C# 的 KeyboardConverter）
                    keyboard_layout = None
                    keyboard_layout_id = item.get('KeyboardLayout')
                    if keyboard_layout_id:
                        keyboard_layout = self.keyboard_identifiers.get(keyboard_layout_id)
                    
                    # 处理 GeoLocation 引用（类似 C# 的 GeoLocationConverter）
                    geo_location = None
                    geo_location_id = item.get('GeoLocation')
                    if geo_location_id:
                        geo_location = self.geo_locations.get(geo_location_id)
                    
                    self.user_locales[key] = UserLocale(
                        id=key,
                        display_name=item.get('DisplayName', ''),
                        lcid=item.get('LCID', ''),
                        keyboard_layout=keyboard_layout,
                        geo_location=geo_location
                    )
        else:
            self.user_locales = {}
        
        # 7. 加载 WindowsEdition
        edition_file = self.data_dir / 'WindowsEdition.json'
        if edition_file.exists():
            edition_data = load_data_with_i18n(edition_file, self.lang)
            self.windows_editions = to_keyed_dictionary(edition_data, WindowsEdition)
        else:
            self.windows_editions = {}
        
        # 8. 加载 TimeOffset
        timezone_file = self.data_dir / 'TimeOffset.json'
        if timezone_file.exists():
            timezone_data = load_data_with_i18n(timezone_file, self.lang)
            self.time_offsets = to_keyed_dictionary(timezone_data, TimeOffset)
        else:
            self.time_offsets = {}
        
        # 9. 加载 DesktopIcon
        desktop_icon_file = self.data_dir / 'DesktopIcon.json'
        if desktop_icon_file.exists():
            desktop_icon_data = load_data_with_i18n(desktop_icon_file, self.lang)
            self.desktop_icons = to_keyed_dictionary(desktop_icon_data, DesktopIcon)
        else:
            self.desktop_icons = {}
        
        # 10. 加载 StartFolder（需要 Base64Converter）
        start_folder_file = self.data_dir / 'StartFolder.json'
        if start_folder_file.exists():
            with open(start_folder_file, 'r', encoding='utf-8') as f:
                start_folder_data = json.load(f)
            
            # 处理 i18n
            start_folder_data = load_data_with_i18n(start_folder_file, self.lang)
            
            # 创建 StartFolder 对象，处理 Base64 解码
            self.start_folders = {}
            for item in start_folder_data:
                key = item.get('DisplayName', '').replace(' ', '')  # Id 从 DisplayName 生成
                if key:
                    # 处理 Base64 编码的 Bytes（类似 C# 的 Base64Converter）
                    bytes_data = b''
                    bytes_base64 = item.get('Bytes')
                    if bytes_base64:
                        import base64
                        bytes_data = base64.b64decode(bytes_base64)
                    
                    self.start_folders[key] = StartFolder(
                        id=key,
                        display_name=item.get('DisplayName', ''),
                        data=bytes_data
                    )
        else:
            self.start_folders = {}
    
    def lookup(self, data_type: type, key: str) -> Any:
        """查找数据项（对应 C# 的 Lookup 方法）"""
        if data_type == WindowsEdition:
            return self.windows_editions.get(key)
        elif data_type == UserLocale:
            return self.user_locales.get(key)
        elif data_type == ImageLanguage:
            return self.image_languages.get(key)
        elif data_type == KeyboardIdentifier:
            return self.keyboard_identifiers.get(key)
        elif data_type == TimeOffset:
            return self.time_offsets.get(key)
        elif data_type == Bloatware:
            return self.bloatwares.get(key)
        elif data_type == GeoLocation:
            return self.geo_locations.get(key)
        elif data_type == Component:
            return self.components.get(key)
        else:
            raise ValueError(f"Unsupported data type: {data_type}")
    
    def generate_xml(self, config: Configuration) -> bytes:
        """生成 XML（对应 C# 的 GenerateXml 方法）"""
        # 加载模板（使用 src/backend/autounattend.xml）
        template_path = Path(__file__).parent / 'autounattend.xml'
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")
        
        tree = load_xml_template(template_path)
        root = tree.getroot()
        
        # 初始化脚本序列
        specialize_script = SpecializeSequence()
        first_logon_script = FirstLogonSequence()
        user_once_script = UserOnceSequence()
        default_user_script = DefaultUserSequence()
        
        # 创建 CommandBuilder
        command_builder = CommandBuilder(config.hide_power_shell_windows)
        
        # 创建 ModifierContext
        context = ModifierContext()
        context.document = tree
        context.root = root
        context.configuration = config
        context.generator = self
        context.specialize_script = specialize_script
        context.first_logon_script = first_logon_script
        context.user_once_script = user_once_script
        context.default_user_script = default_user_script
        context.command_builder = command_builder
        
        # 执行所有 Modifier（按照 C# 项目的顺序）
        modifiers = []
        
        # 模块 2: Setup Settings（部分）
        modifiers.append(AccessibilityModifier(context))  # 处理 useNarrator
        modifiers.append(ComputerNameModifier(context))  # 处理计算机名
        modifiers.append(BypassModifier(context))  # 处理 bypassRequirementsCheck 和 bypassNetworkCheck
        modifiers.append(ProductKeyModifier(context))  # 处理产品密钥和安装源（模块 6）
        
        # 模块 1: Region, Language and Time Zone
        if config.language_settings:
            modifiers.append(LocalesModifier(context))
        modifiers.append(DiskModifier(context))  # 处理分区设置（模块 5）
        modifiers.append(UsersModifier(context))  # 处理用户账户
        modifiers.append(BloatwareModifier(context))  # 处理预装软件移除（模块 11）
        modifiers.append(ExpressSettingsModifier(context))  # 处理快速设置（模块 11）
        modifiers.append(WifiModifier(context))  # 处理 Wi-Fi 设置（模块 8）
        modifiers.append(EmptyElementsModifier(context))  # 移除空元素
        modifiers.append(LockoutModifier(context))  # 处理账户锁定
        modifiers.append(PasswordExpirationModifier(context))  # 处理密码过期
        if config.time_zone_settings:
            modifiers.append(TimeZoneModifier(context))
        modifiers.append(PersonalizationModifier(context))  # 处理个性化设置（模块 7）
        modifiers.append(WdacModifier(context))  # 处理 WDAC 设置（模块 11）
        modifiers.append(ScriptModifier(context))  # 处理自定义脚本（模块 12）
        
        # 处理 Extensions（从 config_dict 中读取的文件）
        # 如果 config 有 extensions 字段，需要添加文件到 Extensions 部分
        if config.extensions:
            extensions_data = config.extensions
            if isinstance(extensions_data, dict):
                # 创建一个临时的 Modifier 来添加 Extensions 文件
                # 使用闭包捕获 extensions_data
                def create_extensions_modifier(ext_data):
                    class ExtensionsModifier(Modifier):
                        def process(self):
                            s_uri = "https://schneegans.de/windows/unattend-generator/"
                            # 查找或创建 Extensions 元素
                            # 使用 iter 查找，因为 find 可能有命名空间问题
                            extensions = None
                            for elem in self.root.iter():
                                if elem.tag == f"{s_uri}Extensions":
                                    extensions = elem
                                    break
                            
                            if extensions is None:
                                extensions = ET.Element(f"{{{s_uri}}}Extensions")
                                # 设置命名空间属性，确保序列化时使用正确的命名空间
                                extensions.set("xmlns", s_uri)
                                self.root.append(extensions)
                                
                                # 创建 ExtractScript 元素
                                extract_script = ET.Element(f"{{{s_uri}}}ExtractScript")
                                extract_script_text = ext_data.get('extractScript', """param(
    [xml] $Document
);

foreach( $file in $Document.unattend.Extensions.File ) {
    $path = [System.Environment]::ExpandEnvironmentVariables( $file.GetAttribute( 'path' ) );
    mkdir -Path( $path | Split-Path -Parent ) -ErrorAction 'SilentlyContinue';
    $encoding = switch( [System.IO.Path]::GetExtension( $path ) ) {
        { $_ -in '.ps1', '.xml' } { [System.Text.Encoding]::UTF8; }
        { $_ -in '.reg', '.vbs', '.js' } { [System.Text.UnicodeEncoding]::new( $false, $true ); }
        default { [System.Text.Encoding]::Default; }
    };
    $bytes = $encoding.GetPreamble() + $encoding.GetBytes( $file.InnerText.Trim() );
    [System.IO.File]::WriteAllBytes( $path, $bytes );
}""")
                                extract_script.text = extract_script_text
                                extensions.append(extract_script)
                            else:
                                # 如果 Extensions 已存在，更新 ExtractScript（如果需要）
                                extract_script = extensions.find(f"{{{s_uri}}}ExtractScript")
                                if extract_script is None:
                                    extract_script = ET.Element(f"{{{s_uri}}}ExtractScript")
                                    extract_script_text = ext_data.get('extractScript', """param(
    [xml] $Document
);

foreach( $file in $Document.unattend.Extensions.File ) {
    $path = [System.Environment]::ExpandEnvironmentVariables( $file.GetAttribute( 'path' ) );
    mkdir -Path( $path | Split-Path -Parent ) -ErrorAction 'SilentlyContinue';
    $encoding = switch( [System.IO.Path]::GetExtension( $path ) ) {
        { $_ -in '.ps1', '.xml' } { [System.Text.Encoding]::UTF8; }
        { $_ -in '.reg', '.vbs', '.js' } { [System.Text.UnicodeEncoding]::new( $false, $true ); }
        default { [System.Text.Encoding]::Default; }
    };
    $bytes = $encoding.GetPreamble() + $encoding.GetBytes( $file.InnerText.Trim() );
    [System.IO.File]::WriteAllBytes( $path, $bytes );
}""")
                                    extract_script.text = extract_script_text
                                    extensions.insert(0, extract_script)
                                elif 'extractScript' in ext_data:
                                    extract_script.text = ext_data['extractScript']
                            
                            # 添加所有文件
                            files = ext_data.get('files', [])
                            for file_data in files:
                                if isinstance(file_data, dict):
                                    file_path = file_data.get('path', '')
                                    file_content = file_data.get('content', '')
                                    if file_path:
                                        # 检查文件是否已存在
                                        existing_file = None
                                        for f in extensions.findall(f"{{{s_uri}}}File"):
                                            if f.get('path') == file_path:
                                                existing_file = f
                                                break
                                        
                                        if existing_file is None:
                                            file_elem = ET.Element(f"{{{s_uri}}}File")
                                            file_elem.set("path", file_path)
                                            file_elem.text = file_content
                                            extensions.append(file_elem)
                                        else:
                                            # 更新现有文件的内容
                                            existing_file.text = file_content
                    return ExtensionsModifier
                
                ExtensionsModifierClass = create_extensions_modifier(extensions_data)
                modifiers.append(ExtensionsModifierClass(context))
        
        # 处理脚本序列（将脚本添加到 XML）
        # 按照 C# 项目的顺序执行这些 Modifier
        # SpecializeModifier 需要检查是否有 Extensions 或脚本
        # 先检查是否有 Extensions（在 ScriptModifier 执行后，Extensions 可能已经创建）
        s_uri = "https://schneegans.de/windows/unattend-generator/"
        extensions = root.find(f".//{{{s_uri}}}Extensions") if root is not None else None
        has_extensions = extensions is not None and len(list(extensions.findall(f"{{{s_uri}}}File"))) > 0
        
        # 如果有 Extensions 或 specialize_script 不为空，需要创建 Microsoft-Windows-Deployment component
        # 注意：这些检查在 modifiers 执行之前进行，但 ScriptModifier 会在执行时填充脚本序列
        # 所以我们需要先添加这些 modifier，然后在执行后检查是否为空
        modifiers.append(SpecializeModifier(context))  # 会在 process 中检查是否为空
        modifiers.append(UserOnceModifier(context))  # 会在 process 中检查是否为空
        modifiers.append(DefaultUserModifier(context))  # 会在 process 中检查是否为空
        modifiers.append(DeleteModifier(context))  # 处理 keepSensitiveFiles
        modifiers.append(FirstLogonModifier(context))  # 会在 process 中检查是否为空
        modifiers.append(ComponentsModifier(context))  # 处理 XML 标记（模块 13）
        modifiers.append(OrderModifier(context))  # 添加 Order 元素
        modifiers.append(ProcessorArchitectureModifier(context))  # 处理处理器架构（模块 11）
        modifiers.append(MergeOOBEModifier(context))  # 合并重复的 OOBE 元素
        modifiers.append(PrettyModifier(context))  # 美化 XML
        
        # 执行所有 Modifier（包括脚本序列 Modifier）
        for modifier in modifiers:
            modifier.process()
        
        # 序列化 XML
        return serialize_xml(tree)
    
    def _parse_password_element(self, password_elem: ET.Element, element_name: str) -> str:
        """解析密码元素（支持 Base64 解码和 UTF-16LE 字符集）"""
        import base64
        ns_uri = '{urn:schemas-microsoft-com:unattend}'
        
        # 直接遍历子元素来查找 Value 和 PlainText，因为 find() 可能返回 text 为 None 的元素
        value_elem = None
        plain_text_elem = None
        for child in password_elem:
            if child.tag == f"{{{ns_uri}}}Value" or child.tag.endswith('}Value'):
                value_elem = child
            elif child.tag == f"{{{ns_uri}}}PlainText" or child.tag.endswith('}PlainText'):
                plain_text_elem = child
        
        # 如果没找到，尝试使用 find() 作为后备
        if value_elem is None:
            value_elem = password_elem.find(f"{{{ns_uri}}}Value")
        if plain_text_elem is None:
            plain_text_elem = password_elem.find(f"{{{ns_uri}}}PlainText")
        
        if value_elem is None:
            return ''
        
        # 获取文本内容，优先使用 text 属性，如果为 None 或空则使用 itertext() 拼接所有文本
        value_text = value_elem.text
        if value_text is None or (isinstance(value_text, str) and not value_text.strip()):
            # 如果 text 为 None 或为空，尝试使用 itertext() 获取所有文本内容
            itertext_result = ''.join(value_elem.itertext())
            if itertext_result:
                value_text = itertext_result.strip()
        
        if not value_text:
            return ''
        
        # 获取 PlainText 值
        plain_text = "true"
        if plain_text_elem is not None:
            plain_text_val = plain_text_elem.text
            if plain_text_val is None or (isinstance(plain_text_val, str) and not plain_text_val.strip()):
                plain_text_val = ''.join(plain_text_elem.itertext()).strip()
            if plain_text_val:
                plain_text = plain_text_val
        
        if plain_text and plain_text.lower() == "false":
            # Base64 编码的密码
            try:
                encoded_bytes = base64.b64decode(value_text)
                password = encoded_bytes.decode('utf-16le')
                # 移除 element_name 后缀（编码时添加的）
                if password.endswith(element_name):
                    password = password[:-len(element_name)]
                return password
            except Exception as e:
                # 如果解码失败，记录错误但继续执行
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Failed to parse password element {element_name}: {e}")
                return ''
        else:
            # 明文密码
            return value_text
    
    def _parse_registry_command(self, cmd_text: str, registry_path: str, value_name: str) -> str | None:
        """从注册表命令中解析注册表值"""
        import re
        # 匹配 reg.exe add 命令，提取路径、值名和值
        # 支持多种格式：reg.exe add "路径" /v 值名 /t 类型 /d 值 /f
        escaped_path = re.escape(registry_path)
        pattern = rf'reg\.exe\s+add\s+"{escaped_path}"\s+/v\s+{re.escape(value_name)}\s+/t\s+\w+\s+/d\s+(\d+)\s+/f'
        match = re.search(pattern, cmd_text, re.IGNORECASE)
        if match:
            return match.group(1)
        # 也支持 PowerShell Set-ItemProperty 格式
        pattern2 = rf'Set-ItemProperty\s+-LiteralPath\s+[\'"]Registry::({escaped_path})[\'"]\s+-Name\s+[\'"]{re.escape(value_name)}[\'"]\s+-Type\s+\w+\s+-Value\s+(\d+)'
        match2 = re.search(pattern2, cmd_text, re.IGNORECASE)
        if match2:
            return match2.group(2)
        return None
    
    def _check_registry_command(self, cmd_text: str, registry_path: str, value_name: str, expected_value: str = "1") -> bool:
        """检查注册表命令是否设置了指定的值"""
        value = self._parse_registry_command(cmd_text, registry_path, value_name)
        return value == expected_value
    
    def _collect_all_commands(self, root: ET.Element) -> List[str]:
        """收集所有脚本命令（RunSynchronousCommand、FirstLogonCommand 等）"""
        ns_uri = '{urn:schemas-microsoft-com:unattend}'
        all_commands = []
        
        # 收集 RunSynchronousCommand
        run_sync_commands = root.findall(f".//{{{ns_uri}}}RunSynchronousCommand")
        for cmd in run_sync_commands:
            path_elem = cmd.find(f"{{{ns_uri}}}Path")
            if path_elem is not None and path_elem.text:
                all_commands.append(path_elem.text)
        
        # 收集 FirstLogonCommands 中的 SynchronousCommand
        first_logon_containers = root.findall(f".//{{{ns_uri}}}FirstLogonCommands")
        for container in first_logon_containers:
            sync_commands = container.findall(f"{{{ns_uri}}}SynchronousCommand")
            for cmd in sync_commands:
                command_line_elem = cmd.find(f"{{{ns_uri}}}CommandLine")
                if command_line_elem is not None and command_line_elem.text:
                    all_commands.append(command_line_elem.text)
        
        # 收集 UserOnceCommand（如果存在）
        # 注意：UserOnceCommand 可能通过脚本文件调用，需要从脚本内容中提取
        
        # 收集 DefaultUserCommand（如果存在）
        # 注意：DefaultUserCommand 可能通过脚本文件调用，需要从脚本内容中提取
        
        return all_commands
    
    def _get_script_file_content(self, root: ET.Element, file_path: str) -> str | None:
        """从 XML 中获取脚本文件内容"""
        ns_uri = '{urn:schemas-microsoft-com:unattend}'
        # 查找 File 元素
        files = root.findall(f".//{{{ns_uri}}}File")
        for file_elem in files:
            source_path_elem = file_elem.find(f"{{{ns_uri}}}SourcePath")
            destination_path_elem = file_elem.find(f"{{{ns_uri}}}DestinationPath")
            if destination_path_elem is not None and destination_path_elem.text:
                if destination_path_elem.text.replace('\\', '/').lower() == file_path.replace('\\', '/').lower():
                    # 找到匹配的文件，尝试获取内容
                    # 内容可能在 Data 元素中
                    data_elem = file_elem.find(f"{{{ns_uri}}}Data")
                    if data_elem is not None and data_elem.text:
                        return data_elem.text
        return None
    
    def parse_xml(self, xml_content: bytes) -> Dict[str, Any]:
        """解析 XML 为配置字典（C# 项目可能没有此功能，需要实现）"""
        import re  # 局部导入以便正则解析命令内容
        # 解析 XML
        root = ET.fromstring(xml_content)
        ns = get_namespace_map()
        ns_uri = ns['u']
        
        config_dict: Dict[str, Any] = {}
        
        # 解析语言设置
        lang_settings: Dict[str, Any] = {}
        component_pe = root.find(f".//{{{ns_uri}}}component[@name='Microsoft-Windows-International-Core-WinPE']")
        component_oobe = root.find(f".//{{{ns_uri}}}component[@name='Microsoft-Windows-International-Core']")
        
        if component_pe is None and component_oobe is None:
            lang_settings['mode'] = 'interactive'
        else:
            lang_settings['mode'] = 'unattended'
            # 记录是否有 WinPE component（用于生成时决定是否创建）
            lang_settings['hasWinPE'] = component_pe is not None
            
            # 解析具体语言设置
            # 优先使用 WinPE 的 UILanguage，如果没有则使用 OOBE 的 UILanguage
            ui_language = None
            if component_pe is not None:
                ui_lang_elem = component_pe.find(f"{{{ns_uri}}}UILanguage")
                if ui_lang_elem is not None:
                    ui_language = ui_lang_elem.text
            
            if ui_language is None and component_oobe is not None:
                ui_lang_elem = component_oobe.find(f"{{{ns_uri}}}UILanguage")
                if ui_lang_elem is not None:
                    ui_language = ui_lang_elem.text
            
            if ui_language is not None:
                lang_settings['uiLanguage'] = ui_language
            
            if component_oobe is not None:
                system_locale_elem = component_oobe.find(f"{{{ns_uri}}}SystemLocale")
                if system_locale_elem is not None:
                    lang_settings['systemLocale'] = system_locale_elem.text
                
                input_locale_elem = component_oobe.find(f"{{{ns_uri}}}InputLocale")
                if input_locale_elem is not None and input_locale_elem.text is not None:
                    # InputLocale 格式可能是：
                    # - "LCID:KeyboardId" (单个键盘)
                    # - "LCID:KeyboardId;LCID2:KeyboardId2" (多个键盘，用分号分隔)
                    # - "KeyboardId" (仅键盘 ID，无 LCID)
                    input_locale = input_locale_elem.text
                    # 如果有分号，说明有多个键盘，取第一个（保留完整格式 LCID:KeyboardId）
                    if ';' in input_locale:
                        first_keyboard = input_locale.split(';')[0]
                        lang_settings['inputLocale'] = first_keyboard
                    else:
                        # 单个键盘，保留完整格式
                        lang_settings['inputLocale'] = input_locale
        
        config_dict['languageSettings'] = lang_settings
        
        # 解析时区设置
        timezone_settings: Dict[str, Any] = {}
        component_shell = root.find(f".//{{{ns_uri}}}component[@name='Microsoft-Windows-Shell-Setup']")
        if component_shell is not None:
            timezone_elem = component_shell.find(f"{{{ns_uri}}}TimeZone")
            if timezone_elem is not None:
                timezone_settings['mode'] = 'explicit'
                timezone_settings['timeZone'] = timezone_elem.text
            else:
                timezone_settings['mode'] = 'implicit'
        else:
            timezone_settings['mode'] = 'implicit'
        
        config_dict['timeZone'] = timezone_settings
        
        # 解析 Setup Settings（模块 2）
        setup_settings: Dict[str, Any] = {
            'bypassRequirementsCheck': False,
            'bypassNetworkCheck': False,
            'useConfigurationSet': False,
            'hidePowerShellWindows': False,
            'keepSensitiveFiles': True,  # 默认保留敏感文件
            'useNarrator': False
        }
        
        # 解析 UseConfigurationSet
        use_config_set = root.find(f".//{{{ns_uri}}}UseConfigurationSet")
        if use_config_set is not None and use_config_set.text == "true":
            setup_settings['useConfigurationSet'] = True
        
        # 解析 RunSynchronous 命令，提取多处配置信息
        detected_diskpart: Dict[str, Any] = {}
        detected_image_name: Optional[str] = None
        detected_winpe_layout: Optional[str] = None
        detected_assert_script: Optional[str] = None
        detected_compact = False

        # 解析注册表项以检测 bypassRequirementsCheck 和 bypassNetworkCheck
        # 同时提取 diskpart / pe.cmd / assert.vbs 等相关信息
        run_sync_commands = root.findall(f".//{{{ns_uri}}}RunSynchronousCommand")
        for cmd in run_sync_commands:
            path_elem = cmd.find(f"{{{ns_uri}}}Path")
            if path_elem is not None and path_elem.text:
                cmd_text = path_elem.text
                
                # 检测 bypassRequirementsCheck
                if 'BypassTPMCheck' in cmd_text or 'BypassSecureBootCheck' in cmd_text or 'BypassRAMCheck' in cmd_text:
                    setup_settings['bypassRequirementsCheck'] = True
                
                # 检测 bypassNetworkCheck
                if 'BypassNetworkCheck' in cmd_text:
                    setup_settings['bypassNetworkCheck'] = True
                
                # 检测 hidePowerShellWindows
                if 'powershell.exe' in cmd_text:
                    if 'WindowStyle "Hidden"' in cmd_text or 'WindowStyle Hidden' in cmd_text:
                        setup_settings['hidePowerShellWindows'] = True
                    elif 'WindowStyle "Normal"' in cmd_text or 'WindowStyle Normal' in cmd_text:
                        setup_settings['hidePowerShellWindows'] = False
                
                # 检测 keepSensitiveFiles（查找删除 unattend.xml 的命令）
                if 'unattend.xml' in cmd_text and ('del' in cmd_text.lower() or 'delete' in cmd_text.lower() or 'remove' in cmd_text.lower()):
                    setup_settings['keepSensitiveFiles'] = False

                # 解析 diskpart 写入命令，提取分区参数
                if 'diskpart.txt' in cmd_text.lower() and ('>>' in cmd_text or 'echo:' in cmd_text):
                    m = re.search(r'CREATE PARTITION EFI SIZE=(\d+)', cmd_text, re.IGNORECASE)
                    if m:
                        detected_diskpart['esp_size'] = int(m.group(1))
                    m = re.search(r'SHRINK MINIMUM=(\d+)', cmd_text, re.IGNORECASE)
                    if m:
                        detected_diskpart['recovery_size'] = int(m.group(1))
                    if 'convert gpt' in cmd_text.lower():
                        detected_diskpart['layout'] = 'GPT'
                    elif 'convert mbr' in cmd_text.lower():
                        detected_diskpart['layout'] = 'MBR'
                    # 如果出现恢复分区标记，推断为 partition 模式
                    if re.search(r'ASSIGN LETTER=R', cmd_text, re.IGNORECASE) or re.search(r'GPT ATTRIBUTES', cmd_text, re.IGNORECASE) or re.search(r'SET ID', cmd_text, re.IGNORECASE):
                        detected_diskpart['recovery_mode'] = 'partition'

                # 提取 assert.vbs 脚本内容（首个 echo 段）
                if 'assert.vbs' in cmd_text.lower() and '>>' in cmd_text:
                    m = re.search(r'\(echo:([^)]+)\)', cmd_text, re.IGNORECASE)
                    if m:
                        detected_assert_script = m.group(1)

                # 提取 PE 键盘布局（SetKeyboardLayout 参数）
                if 'setkeyboardlayout' in cmd_text.lower():
                    m = re.search(r'SetKeyboardLayout\s+([^&"]+)', cmd_text, re.IGNORECASE)
                    if m:
                        detected_winpe_layout = m.group(1)

                # 提取镜像名称（/Name:"XXXX"）
                if '/apply-image' in cmd_text.lower() and '/name:' in cmd_text.lower():
                    try:
                        segment = cmd_text.split('/Name:', 1)[1]
                        segment = segment.split('/ApplyDir', 1)[0]
                        raw = segment.strip()
                        # 去除两侧转义的引号以及 ^ 符号
                        if raw.startswith('^"') and raw.endswith('^"'):
                            raw = raw[2:-2]
                        raw = raw.replace('^"', '').replace('"', '').replace('^', '').strip()
                        if raw:
                            detected_image_name = raw
                    except Exception:
                        pass
                    if '/compact' in cmd_text.lower():
                        detected_compact = True
        
        # 解析脚本以检测 useNarrator
        # 查找 FirstLogonCommands 和 RunSynchronous 命令中的 Narrator 相关命令
        first_logon_containers = root.findall(f".//{{{ns_uri}}}FirstLogonCommands")
        for container in first_logon_containers:
            sync_commands = container.findall(f"{{{ns_uri}}}SynchronousCommand")
            for cmd in sync_commands:
                command_line_elem = cmd.find(f"{{{ns_uri}}}CommandLine")
                if command_line_elem is not None and command_line_elem.text:
                    cmd_text = command_line_elem.text.lower()
                    if 'narrator' in cmd_text or 'screenreader' in cmd_text:
                        setup_settings['useNarrator'] = True
        
        # 也在 RunSynchronous 中查找
        for cmd in run_sync_commands:
            path_elem = cmd.find(f"{{{ns_uri}}}Path")
            if path_elem is not None and path_elem.text:
                cmd_text = path_elem.text.lower()
                if 'narrator' in cmd_text or 'screenreader' in cmd_text:
                    setup_settings['useNarrator'] = True
        
        config_dict['setupSettings'] = setup_settings
        
        # 解析模块 4: Name and Account
        # 解析计算机名设置
        computer_name_settings: Dict[str, Any] = {'mode': 'random'}
        component_shell = root.find(f".//{{{ns_uri}}}component[@name='Microsoft-Windows-Shell-Setup']")
        if component_shell is not None:
            computer_name_elem = component_shell.find(f"{{{ns_uri}}}ComputerName")
            if computer_name_elem is not None:
                if computer_name_elem.text == "TEMPNAME":
                    computer_name_settings['mode'] = 'script'
                    # 需要从脚本中解析，暂时设为空
                    computer_name_settings['script'] = ''
                else:
                    computer_name_settings['mode'] = 'custom'
                    computer_name_settings['name'] = computer_name_elem.text
        config_dict['computerName'] = computer_name_settings
        
        # 解析账户设置
        account_settings: Dict[str, Any] = {'mode': 'interactive-microsoft'}
        auto_logon = root.find(f".//{{{ns_uri}}}AutoLogon")
        user_accounts = root.find(f".//{{{ns_uri}}}UserAccounts")
        
        if auto_logon is not None or user_accounts is not None:
            account_settings['mode'] = 'unattended'
            account_settings['autoLogonMode'] = 'none'
            account_settings['autoLogonPassword'] = ''
            account_settings['obscurePasswords'] = False
            account_settings['accounts'] = []
            
            # 解析用户账户（AdministratorPassword 在 UserAccounts 中）
            if user_accounts is not None:
                # 先解析 AdministratorPassword（在 UserAccounts 下）
                admin_password_elem = user_accounts.find(f"{{{ns_uri}}}AdministratorPassword")
                if admin_password_elem is not None:
                    account_settings['autoLogonPassword'] = self._parse_password_element(admin_password_elem, "AdministratorPassword")
                    # 检查是否使用了 Base64 混淆
                    plain_text_elem = admin_password_elem.find(f"{{{ns_uri}}}PlainText")
                    if plain_text_elem is not None and plain_text_elem.text and plain_text_elem.text.lower() == "false":
                        account_settings['obscurePasswords'] = True
            
            # 解析自动登录
            if auto_logon is not None:
                username_elem = auto_logon.find(f"{{{ns_uri}}}Username")
                if username_elem is not None:
                    username = username_elem.text
                    if username == "Administrator":
                        account_settings['autoLogonMode'] = 'builtin'
                        # AutoLogon 中的 Password 用于自动登录，应该与 AdministratorPassword 相同
                        # 但这里我们只解析，不覆盖已解析的 autoLogonPassword
                        auto_logon_password_elem = auto_logon.find(f"{{{ns_uri}}}Password")
                        if auto_logon_password_elem is not None:
                            # 验证 AutoLogon 中的密码是否与 AdministratorPassword 一致
                            auto_logon_password = self._parse_password_element(auto_logon_password_elem, "Password")
                            # 如果 autoLogonPassword 还没有设置，使用 AutoLogon 中的密码
                            if not account_settings.get('autoLogonPassword'):
                                account_settings['autoLogonPassword'] = auto_logon_password
                    else:
                        account_settings['autoLogonMode'] = 'own'
                        # 对于 own 模式，从 AutoLogon 中解析密码
                        auto_logon_password_elem = auto_logon.find(f"{{{ns_uri}}}Password")
                        if auto_logon_password_elem is not None:
                            account_settings['autoLogonPassword'] = self._parse_password_element(auto_logon_password_elem, "Password")
            
            # 解析用户账户（LocalAccounts）
            if user_accounts is not None:
                local_accounts = user_accounts.find(f"{{{ns_uri}}}LocalAccounts")
                if local_accounts is not None:
                    for local_account in local_accounts.findall(f"{{{ns_uri}}}LocalAccount"):
                        name_elem = local_account.find(f"{{{ns_uri}}}Name")
                        display_name_elem = local_account.find(f"{{{ns_uri}}}DisplayName")
                        group_elem = local_account.find(f"{{{ns_uri}}}Group")
                        password_elem = local_account.find(f"{{{ns_uri}}}Password")
                        if name_elem is not None:
                            # DisplayName 如果为空字符串，应该设为 None 而不是使用 name
                            display_name = None
                            if display_name_elem is not None and display_name_elem.text:
                                display_name = display_name_elem.text
                            elif display_name_elem is not None and display_name_elem.text == '':
                                display_name = None
                            
                            # 解析密码
                            password = ''
                            if password_elem is not None:
                                password = self._parse_password_element(password_elem, "Password")
                                # 检查是否使用了 Base64 混淆
                                plain_text_elem = password_elem.find(f"{{{ns_uri}}}PlainText")
                                if plain_text_elem is not None and plain_text_elem.text and plain_text_elem.text.lower() == "false":
                                    account_settings['obscurePasswords'] = True
                            
                            # 生成 UUID 作为账户 ID（前端需要）
                            import uuid
                            account = {
                                'id': str(uuid.uuid4()),
                                'name': name_elem.text,
                                'displayName': display_name,
                                'group': group_elem.text if group_elem is not None else Constants.UsersGroup,
                                'password': password
                            }
                            account_settings['accounts'].append(account)
        else:
            # 检查是否是交互式本地账户
            hide_online = root.find(f".//{{{ns_uri}}}HideOnlineAccountScreens")
            if hide_online is not None and hide_online.text == "true":
                account_settings['mode'] = 'interactive-local'
        
        # 解析 OOBE 设置
        oobe_elem = root.find(f".//{{{ns_uri}}}OOBE")
        if oobe_elem is not None:
            protect_your_pc_elem = oobe_elem.find(f"{{{ns_uri}}}ProtectYourPC")
            if protect_your_pc_elem is not None:
                account_settings['protectYourPC'] = protect_your_pc_elem.text
            
            hide_online_account_screens_elem = oobe_elem.find(f"{{{ns_uri}}}HideOnlineAccountScreens")
            if hide_online_account_screens_elem is not None and hide_online_account_screens_elem.text:
                account_settings['hideOnlineAccountScreens'] = hide_online_account_screens_elem.text.lower() == "true"
        
        config_dict['accountSettings'] = account_settings
        
        # 解析密码过期设置
        password_expiration_settings: Dict[str, Any] = {'mode': 'default'}
        # 从 specialize pass 的脚本中解析
        specialize_settings = root.find(f".//{{{ns_uri}}}settings[@pass='specialize']")
        if specialize_settings is not None:
            # 查找 RunSynchronousCommand 和 PowerShell 脚本
            specialize_commands = specialize_settings.findall(f".//{{{ns_uri}}}RunSynchronousCommand")
            for cmd in specialize_commands:
                path_elem = cmd.find(f"{{{ns_uri}}}Path")
                if path_elem is not None and path_elem.text:
                    cmd_text = path_elem.text
                    # 查找 net.exe accounts /maxpwage 命令
                    if 'net.exe accounts' in cmd_text.lower() and '/maxpwage' in cmd_text.lower():
                        if 'unlimited' in cmd_text.lower():
                            password_expiration_settings['mode'] = 'unlimited'
                        else:
                            # 提取数字值
                            import re
                            match = re.search(r'/maxpwage:(\d+)', cmd_text, re.IGNORECASE)
                            if match:
                                max_age = int(match.group(1))
                                if max_age == 0:
                                    password_expiration_settings['mode'] = 'default'
                                else:
                                    password_expiration_settings['mode'] = 'custom'
                                    password_expiration_settings['maxAge'] = max_age
        config_dict['passwordExpiration'] = password_expiration_settings
        
        # 解析账户锁定设置
        lockout_settings: Dict[str, Any] = {'mode': 'default'}
        # 从 specialize pass 的脚本中解析
        if specialize_settings is not None:
            specialize_commands = specialize_settings.findall(f".//{{{ns_uri}}}RunSynchronousCommand")
            lockout_threshold = None
            lockout_duration = None
            lockout_window = None
            
            for cmd in specialize_commands:
                path_elem = cmd.find(f"{{{ns_uri}}}Path")
                if path_elem is not None and path_elem.text:
                    cmd_text = path_elem.text
                    # 查找 net.exe accounts /lockoutthreshold 命令
                    if 'net.exe accounts' in cmd_text.lower() and '/lockoutthreshold' in cmd_text.lower():
                        import re
                        match = re.search(r'/lockoutthreshold:(\d+)', cmd_text, re.IGNORECASE)
                        if match:
                            lockout_threshold = int(match.group(1))
                        
                        # 同时查找 lockoutduration 和 lockoutwindow
                        match = re.search(r'/lockoutduration:(\d+)', cmd_text, re.IGNORECASE)
                        if match:
                            lockout_duration = int(match.group(1))
                        
                        match = re.search(r'/lockoutwindow:(\d+)', cmd_text, re.IGNORECASE)
                        if match:
                            lockout_window = int(match.group(1))
            
            # 判断锁定设置模式
            if lockout_threshold is not None:
                if lockout_threshold == 0:
                    lockout_settings['mode'] = 'disabled'
                elif lockout_threshold == 10 and lockout_duration == 10 and lockout_window == 10:
                    # 默认值
                    lockout_settings['mode'] = 'default'
                else:
                    lockout_settings['mode'] = 'custom'
                    lockout_settings['lockoutThreshold'] = lockout_threshold
                    if lockout_duration is not None:
                        lockout_settings['lockoutDuration'] = lockout_duration
                    if lockout_window is not None:
                        lockout_settings['resetLockoutCounter'] = lockout_window
        config_dict['lockoutSettings'] = lockout_settings
        
        # 解析模块 5: Partitioning and formatting
        # 解析分区设置
        partitioning_settings: Dict[str, Any] = {'mode': 'interactive'}
        
        # 检查是否有 diskpart.txt 写入命令（这表示是自动生成的 diskpart 脚本）
        run_sync_commands = root.findall(f".//{{{ns_uri}}}RunSynchronousCommand")
        has_diskpart_write = False
        has_diskpart_execute = False
        for cmd in run_sync_commands:
            path_elem = cmd.find(f"{{{ns_uri}}}Path")
            if path_elem is not None and path_elem.text:
                cmd_text = path_elem.text.lower()
                if 'diskpart.txt' in cmd_text and ('>>' in cmd_text or 'echo:' in cmd_text):
                    has_diskpart_write = True
                if 'diskpart.exe' in cmd_text and '/s' in cmd_text:
                    has_diskpart_execute = True
        
        # InstallTo 在 OSImage 下
        install_to = root.find(f".//{{{ns_uri}}}OSImage/{{{ns_uri}}}InstallTo")
        
        # 如果有 diskpart.txt 写入命令，说明是自动生成的分区脚本
        if has_diskpart_write:
            partitioning_settings['mode'] = 'automatic'
            partitioning_settings['layout'] = detected_diskpart.get('layout', 'GPT')
            partitioning_settings['recoveryMode'] = detected_diskpart.get('recovery_mode', 'partition')
            partitioning_settings['espSize'] = detected_diskpart.get('esp_size', Constants.EspDefaultSize)
            partitioning_settings['recoverySize'] = detected_diskpart.get('recovery_size', Constants.RecoveryPartitionSize)
        elif install_to is not None:
            if has_diskpart_execute:
                # 如果有 diskpart 执行命令但没有写入命令，可能是自定义脚本
                partitioning_settings['mode'] = 'custom'
                partitioning_settings['diskpartScript'] = ''  # 无法从 XML 中解析
                partitioning_settings['installToMode'] = 'available'
            else:
                partitioning_settings['mode'] = 'automatic'
                partitioning_settings['layout'] = 'GPT'  # 默认
                partitioning_settings['recoveryMode'] = 'partition'  # 默认
                partitioning_settings['espSize'] = Constants.EspDefaultSize
                partitioning_settings['recoverySize'] = Constants.RecoveryPartitionSize
        else:
            partitioning_settings['mode'] = 'interactive'
        
        # 解析磁盘断言设置
        has_assert_vbs_write = False
        has_assert_vbs_execute = False
        for cmd in run_sync_commands:
            path_elem = cmd.find(f"{{{ns_uri}}}Path")
            if path_elem is not None and path_elem.text:
                cmd_text = path_elem.text.lower()
                if 'assert.vbs' in cmd_text and ('>>' in cmd_text or 'echo:' in cmd_text):
                    has_assert_vbs_write = True
                if 'assert.vbs' in cmd_text and ('cscript' in cmd_text or 'wscript' in cmd_text):
                    has_assert_vbs_execute = True
        
        if detected_assert_script is not None:
            partitioning_settings['diskAssertionMode'] = 'script'
            partitioning_settings['diskAssertionScript'] = detected_assert_script
        elif has_assert_vbs_write or has_assert_vbs_execute:
            partitioning_settings['diskAssertionMode'] = 'script'
            partitioning_settings['diskAssertionScript'] = ''  # 无法从 XML 中解析
        else:
            partitioning_settings['diskAssertionMode'] = 'skip'
        
        config_dict['partitioning'] = partitioning_settings
        
        # 解析 PE 设置
        pe_settings: Dict[str, Any] = {'mode': 'default'}
        # 检查是否有 pe.cmd 脚本
        has_pe_script = False
        has_assert_vbs = False
        has_diskpart_txt = False
        has_pe_cmd_write = False  # 是否有写入 pe.cmd 的命令
        disable_8dot3 = False
        pause_before_reboot = False
        disable_defender_flag = False
        
        for cmd in root.findall(f".//{{{ns_uri}}}RunSynchronousCommand"):
            path_elem = cmd.find(f"{{{ns_uri}}}Path")
            if path_elem is not None and path_elem.text:
                cmd_text = path_elem.text.lower()
                if 'pe.cmd' in cmd_text:
                    has_pe_script = True
                    # 检查是否是写入命令（包含 >>"X:\pe.cmd"）
                    if '>>"x:\\pe.cmd"' in cmd_text or '>>"x:/pe.cmd"' in cmd_text:
                        has_pe_cmd_write = True
                    if '8dot3name set' in cmd_text or '8dot3name strip' in cmd_text:
                        disable_8dot3 = True
                    if '@echo computer will now reboot' in cmd_text or ('pause' in cmd_text and 'wpeutil.exe reboot' in cmd_text):
                        pause_before_reboot = True
                if 'assert.vbs' in cmd_text:
                    has_assert_vbs = True
                if 'diskpart.txt' in cmd_text:
                    has_diskpart_txt = True
                if 'windefend' in cmd_text and 'reg.exe' in cmd_text and '/v start' in cmd_text and '/d 4' in cmd_text:
                    disable_defender_flag = True
        
        # 如果有多个写入文件的命令（assert.vbs、diskpart.txt、pe.cmd），应该是 GeneratePESettings
        if has_pe_script and (has_assert_vbs or has_diskpart_txt or has_pe_cmd_write):
            pe_settings['mode'] = 'generated'
            # 尝试从命令中推断设置（简化版本）
            pe_settings['disable8Dot3Names'] = disable_8dot3
            pe_settings['pauseBeforeFormatting'] = False  # 默认值
            pe_settings['pauseBeforeReboot'] = pause_before_reboot
        elif has_pe_script:
            pe_settings['mode'] = 'script'
            pe_settings['cmdScript'] = ''  # 无法从 XML 中解析
        else:
            pe_settings['mode'] = 'default'

        if 'systemTweaks' not in config_dict or not isinstance(config_dict.get('systemTweaks'), dict):
            config_dict['systemTweaks'] = {}
        if disable_defender_flag:
            config_dict['systemTweaks']['disableDefender'] = True
        
        config_dict['peSettings'] = pe_settings
        # 额外保存 WinPE 键盘布局（供生成时精确还原）
        if detected_winpe_layout:
            config_dict.setdefault('languageSettings', {})['winPEKeyboardLayout'] = detected_winpe_layout
        if detected_compact:
            config_dict['compactOS'] = 'enabled'

        # 如果在 RunSynchronous 中解析到镜像名称，补全 sourceImage 为名称模式
        if detected_image_name:
            config_dict['sourceImage'] = {
                'mode': 'name',
                'name': detected_image_name
            }
            config_dict.setdefault('windowsEdition', {}).setdefault('editionName', detected_image_name)

        # 解析 Compact OS 模式（若已根据 RunSynchronous 检测到，则不覆盖）
        if 'compactOS' not in config_dict:
            # Compact 在 OSImage 下
            compact_elem = root.find(f".//{{{ns_uri}}}OSImage/{{{ns_uri}}}Compact")
            if compact_elem is not None:
                if compact_elem.text == "true":
                    config_dict['compactOS'] = 'enabled'
                elif compact_elem.text == "false":
                    config_dict['compactOS'] = 'disabled'
                else:
                    config_dict['compactOS'] = 'default'
            else:
                config_dict['compactOS'] = 'default'
        
        # 解析模块 6: Windows Edition and Source
        # 解析版本设置
        # 首先检查 specialize pass 中的 ProductKey（自定义产品密钥）
        specialize_product_key_elem = root.find(f".//{{{ns_uri}}}settings[@pass='specialize']/{{{ns_uri}}}component[@name='Microsoft-Windows-Shell-Setup']/{{{ns_uri}}}ProductKey")
        
        edition_settings: Dict[str, Any] = {'mode': 'interactive'}
        
        if specialize_product_key_elem is not None and specialize_product_key_elem.text:
            # 如果 specialize pass 中有 ProductKey，则是自定义产品密钥模式
            edition_settings['mode'] = 'custom'
            edition_settings['productKey'] = specialize_product_key_elem.text
        else:
            # 检查 windowsPE pass 中的 UserData/ProductKey
            product_key_elem = root.find(f".//{{{ns_uri}}}UserData/{{{ns_uri}}}ProductKey/{{{ns_uri}}}Key")
            will_show_ui_elem = root.find(f".//{{{ns_uri}}}UserData/{{{ns_uri}}}ProductKey/{{{ns_uri}}}WillShowUI")
            
            if product_key_elem is not None:
                product_key = product_key_elem.text
                will_show_ui = will_show_ui_elem.text if will_show_ui_elem is not None else "Always"
                
                if product_key == "00000-00000-00000-00000-00000":
                    if will_show_ui == "Always":
                        edition_settings['mode'] = 'interactive'
                    else:
                        edition_settings['mode'] = 'firmware'
                else:
                    # 可能是无人值守模式，需要从 WindowsEdition 数据中查找
                    # 暂时设为交互式
                    edition_settings['mode'] = 'interactive'
        
        config_dict['windowsEdition'] = edition_settings
        
        # 解析安装源设置（若之前已从 RunSynchronous 提取到 name，则保持不覆盖）
        if not (isinstance(config_dict.get('sourceImage'), dict) and config_dict['sourceImage'].get('mode') == 'name'):
            # InstallFrom 在 OSImage 下
            install_from = root.find(f".//{{{ns_uri}}}OSImage/{{{ns_uri}}}InstallFrom")
            source_settings: Dict[str, Any] = {'mode': 'automatic'}
            if install_from is not None:
                metadata = install_from.find(f"{{{ns_uri}}}MetaData")
                if metadata is not None:
                    key_elem = metadata.find(f"{{{ns_uri}}}Key")
                    value_elem = metadata.find(f"{{{ns_uri}}}Value")
                    if key_elem is not None and value_elem is not None:
                        key = key_elem.text
                        value = value_elem.text
                        if key == "/IMAGE/INDEX" and value is not None:
                            try:
                                index = int(value)
                                source_settings['mode'] = 'index'
                                source_settings['imageIndex'] = index
                            except (ValueError, TypeError):
                                source_settings['mode'] = 'automatic'
                        elif key == "/IMAGE/NAME" and value is not None:
                            source_settings['mode'] = 'name'
                            source_settings['imageName'] = value
                        else:
                            source_settings['mode'] = 'automatic'
                    else:
                        source_settings['mode'] = 'automatic'
                else:
                    source_settings['mode'] = 'automatic'
            else:
                source_settings['mode'] = 'automatic'
            
            config_dict['sourceImage'] = source_settings
        
        # 解析 windowsPE pass 中的 ImageInstall 和 UserData
        # 这些元素在生成时会被创建，但在解析时需要检测它们的存在
        windows_pe_settings = root.find(f".//{{{ns_uri}}}settings[@pass='windowsPE']")
        if windows_pe_settings is not None:
            setup_component = windows_pe_settings.find(f".//{{{ns_uri}}}component[@name='Microsoft-Windows-Setup']")
            if setup_component is not None:
                # 检查是否有 ImageInstall 元素
                image_install = setup_component.find(f"{{{ns_uri}}}ImageInstall")
                if image_install is not None:
                    # ImageInstall 存在，说明使用了自定义分区或安装源
                    # 这些信息已经在 partitioning 和 sourceImage 中解析了
                    pass
                
                # 检查是否有 UserData 元素
                user_data = setup_component.find(f"{{{ns_uri}}}UserData")
                if user_data is not None:
                    # UserData 存在，说明设置了产品密钥
                    # 这个信息已经在 windowsEdition 中解析了
                    pass
                
                # 检查是否有 UseConfigurationSet 元素
                use_config_set_elem = setup_component.find(f"{{{ns_uri}}}UseConfigurationSet")
                if use_config_set_elem is not None:
                    if use_config_set_elem.text and use_config_set_elem.text.lower() == "true":
                        setup_settings['useConfigurationSet'] = True
        
        # 解析模块 8: Wi-Fi 设置
        wlan_profile = root.find(f".//{{{ns_uri}}}WLANProfile")
        wifi_settings: Dict[str, Any] = {'mode': 'skip'}
        if wlan_profile is not None:
            # 检查是否有 SSID 和认证信息
            ssid_elem = wlan_profile.find(f".//{{{ns_uri}}}name")
            if ssid_elem is not None:
                ssid = ssid_elem.text
                # 检查认证方式
                auth_elem = wlan_profile.find(f".//{{{ns_uri}}}authentication")
                if auth_elem is not None:
                    auth = auth_elem.text
                    password_elem = wlan_profile.find(f".//{{{ns_uri}}}keyMaterial")
                    password = password_elem.text if password_elem is not None else ''
                    wifi_settings = {
                        'mode': 'unattended',
                        'ssid': ssid,
                        'authentication': auth if auth else 'Open',
                        'password': password,
                        'hidden': False  # 无法从 XML 中确定
                    }
                else:
                    wifi_settings = {'mode': 'interactive'}
            else:
                wifi_settings = {'mode': 'interactive'}
        else:
            wifi_settings = {'mode': 'skip'}
        
        config_dict['wifi'] = wifi_settings
        
        # 收集所有脚本命令用于解析其他设置
        all_commands = self._collect_all_commands(root)
        
        # 解析模块 9: 辅助功能设置
        # Lock Keys 和 Sticky Keys 设置需要从注册表解析
        lock_keys_settings: Dict[str, Any] = {'mode': 'skip'}
        sticky_keys_settings: Dict[str, Any] = {'mode': 'default'}
        
        # 解析 LockKeys
        for cmd_text in all_commands:
            cmd_lower = cmd_text.lower()
            # 查找键盘相关注册表设置
            if 'control panel\\keyboard' in cmd_lower and 'reg.exe' in cmd_lower:
                # 解析锁定键设置
                if 'initialkeyboardindicators' in cmd_lower:
                    # 提取初始状态
                    value = self._parse_registry_command(cmd_text, r'HKU\\DefaultUser\\Control Panel\\Keyboard', 'InitialKeyboardIndicators')
                    if value:
                        lock_keys_settings['mode'] = 'configure'
                        # 根据值设置初始状态（0=off, 2=on for NumLock, 4=on for CapsLock, 6=both on）
                        if value == '0':
                            lock_keys_settings['numLockInitial'] = 'off'
                            lock_keys_settings['capsLockInitial'] = 'off'
                        elif value == '2':
                            lock_keys_settings['numLockInitial'] = 'on'
                            lock_keys_settings['capsLockInitial'] = 'off'
                        elif value == '4':
                            lock_keys_settings['numLockInitial'] = 'off'
                            lock_keys_settings['capsLockInitial'] = 'on'
                        elif value == '6':
                            lock_keys_settings['numLockInitial'] = 'on'
                            lock_keys_settings['capsLockInitial'] = 'on'
        
        # 解析 StickyKeys
        for cmd_text in all_commands:
            cmd_lower = cmd_text.lower()
            if 'stickykeys' in cmd_lower and 'flags' in cmd_lower and 'reg.exe' in cmd_lower:
                value = self._parse_registry_command(cmd_text, r'HKU\\DefaultUser\\Control Panel\\Accessibility\\StickyKeys', 'Flags')
                if value:
                    try:
                        flags_int = int(value)
                        if flags_int == 0:
                            sticky_keys_settings['mode'] = 'disabled'
                        else:
                            sticky_keys_settings['mode'] = 'custom'
                            # 解析标志位（简化处理，实际需要根据位掩码解析）
                            sticky_keys_settings['stickyKeysHotKeyActive'] = (flags_int & 1) != 0
                            sticky_keys_settings['stickyKeysHotKeySound'] = (flags_int & 2) != 0
                            sticky_keys_settings['stickyKeysIndicator'] = (flags_int & 4) != 0
                            sticky_keys_settings['stickyKeysAudibleFeedback'] = (flags_int & 8) != 0
                            sticky_keys_settings['stickyKeysTriState'] = (flags_int & 16) != 0
                            sticky_keys_settings['stickyKeysTwoKeysOff'] = (flags_int & 32) != 0
                    except (ValueError, TypeError):
                        pass
        
        config_dict['lockKeys'] = lock_keys_settings
        config_dict['stickyKeys'] = sticky_keys_settings
        
        # FileExplorerTweaks - 从注册表命令中解析
        file_explorer_tweaks: Dict[str, Any] = {
            'showFileExtensions': False,
            'showAllTrayIcons': False,
            'hideFiles': 'hidden',
            'hideEdgeFre': False,
            'disableEdgeStartupBoost': False,
            'makeEdgeUninstallable': False,
            'deleteEdgeDesktopIcon': False,
            'launchToThisPC': False,
            'disableBingResults': False,
            'classicContextMenu': False,
            'showEndTask': False
        }
        
        for cmd_text in all_commands:
            cmd_lower = cmd_text.lower()
            
            # showFileExtensions: HideFileExt = 0 表示显示扩展名
            if 'hidefileext' in cmd_lower and 'reg.exe' in cmd_lower:
                value = self._parse_registry_command(cmd_text, r'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced', 'HideFileExt')
                if value == '0':
                    file_explorer_tweaks['showFileExtensions'] = True
            
            # launchToThisPC: LaunchTo = 1
            if 'launchto' in cmd_lower and ('reg.exe' in cmd_lower or 'set-itemproperty' in cmd_lower):
                if 'explorer\\advanced' in cmd_lower:
                    value = self._parse_registry_command(cmd_text, r'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced', 'LaunchTo')
                    if value == '1':
                        file_explorer_tweaks['launchToThisPC'] = True
            
            # hideEdgeFre: HideFirstRunExperience = 1
            if 'hidefirstrunexperience' in cmd_lower and 'reg.exe' in cmd_lower:
                if self._check_registry_command(cmd_text, r'HKLM\\Software\\Policies\\Microsoft\\Edge', 'HideFirstRunExperience', '1'):
                    file_explorer_tweaks['hideEdgeFre'] = True
            
            # disableEdgeStartupBoost: BackgroundModeEnabled = 0 或 StartupBoostEnabled = 0
            if ('backgroundmodeenabled' in cmd_lower or 'startupboostenabled' in cmd_lower) and 'reg.exe' in cmd_lower:
                if 'edge' in cmd_lower and '0' in cmd_text:
                    file_explorer_tweaks['disableEdgeStartupBoost'] = True
            
            # makeEdgeUninstallable: 查找 MakeEdgeUninstallable.ps1
            if 'makeedgeuninstallable' in cmd_lower:
                file_explorer_tweaks['makeEdgeUninstallable'] = True
            
            # classicContextMenu: 查找 {86ca1aa0-34aa-4e8b-a509-50c905bae2a2} CLSID
            if '{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}' in cmd_text:
                file_explorer_tweaks['classicContextMenu'] = True
            
            # showEndTask: TaskbarEndTask = 1
            if 'taskbarendtask' in cmd_lower and 'reg.exe' in cmd_lower:
                if self._check_registry_command(cmd_text, r'HKU\\DefaultUser\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced\\TaskbarDeveloperSettings', 'TaskbarEndTask', '1'):
                    file_explorer_tweaks['showEndTask'] = True
        
        config_dict['fileExplorerTweaks'] = file_explorer_tweaks
        
        # StartMenuTaskbar - 从注册表命令中解析
        start_menu_taskbar: Dict[str, Any] = {
            'leftTaskbar': False,
            'hideTaskViewButton': False,
            'taskbarSearch': 'box',
            'disableWidgets': False,
            'startTilesMode': 'default',
            'startPinsMode': 'default'
        }
        
        for cmd_text in all_commands:
            cmd_lower = cmd_text.lower()
            
            # leftTaskbar: TaskbarAl = 0
            if 'taskbaral' in cmd_lower and 'reg.exe' in cmd_lower:
                if 'explorer\\advanced' in cmd_lower:
                    value = self._parse_registry_command(cmd_text, r'HKU\\DefaultUser\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced', 'TaskbarAl')
                    if value == '0':
                        start_menu_taskbar['leftTaskbar'] = True
            
            # disableWidgets: 查找相关注册表项
            if 'disablewidgets' in cmd_lower or ('widgets' in cmd_lower and 'disable' in cmd_lower):
                start_menu_taskbar['disableWidgets'] = True
        
        config_dict['startMenuTaskbar'] = start_menu_taskbar
        
        # VisualEffects - 从注册表命令中解析
        visual_effects: Dict[str, Any] = {'mode': 'default'}
        
        for cmd_text in all_commands:
            cmd_lower = cmd_text.lower()
            # 查找 VisualFXSetting 注册表项
            if 'visualfxsetting' in cmd_lower and 'set-itemproperty' in cmd_lower:
                # 提取设置值（0=default, 1=appearance, 2=performance, 3=custom）
                import re
                value_match = re.search(r'-Value\s+(\d+)', cmd_text, re.IGNORECASE)
                if value_match:
                    value = int(value_match.group(1))
                    if value == 0:
                        visual_effects['mode'] = 'default'
                    elif value == 1:
                        visual_effects['mode'] = 'appearance'
                    elif value == 2:
                        visual_effects['mode'] = 'performance'
                    elif value == 3:
                        visual_effects['mode'] = 'custom'
                        # 如果是 custom 模式，尝试解析各个效果设置
                        # 查找 VisualEffects\{EffectName}\DefaultValue 注册表项
                        for effect_name in ['ControlAnimations', 'AnimateMinMax', 'TaskbarAnimations', 'DwmAeroPeekEnabled', 'MenuAnimation', 'TooltipAnimation', 'SelectionFade', 'DwmSaveThumbnailEnabled', 'CursorShadow', 'ListViewShadow', 'ThumbnailsOrIcon', 'ListViewAlphaSelect', 'DragFullWindows', 'ComboBoxAnimation', 'FontSmoothing', 'ListBoxSmoothScrolling', 'DropShadow']:
                            effect_lower = effect_name.lower()
                            if effect_lower in cmd_lower and 'visualeffects' in cmd_lower:
                                value_match2 = re.search(r'-Value\s+(\d+)', cmd_text, re.IGNORECASE)
                                if value_match2:
                                    effect_value = int(value_match2.group(1))
                                    # 将效果名转换为前端字段名（驼峰命名）
                                    # 简化处理：直接使用效果名的小写形式
                                    field_name = effect_name[0].lower() + effect_name[1:] if effect_name else effect_name.lower()
                                    visual_effects[field_name] = effect_value == 1
        
        config_dict['visualEffects'] = visual_effects
        
        # DesktopIcons - 从注册表命令中解析
        desktop_icons: Dict[str, Any] = {
            'mode': 'default',
            'deleteEdgeDesktopIcon': False
        }
        
        for cmd_text in all_commands:
            cmd_lower = cmd_text.lower()
            # 查找 HideDesktopIcons 注册表项
            if 'hidedesktopicons' in cmd_lower and 'set-itemproperty' in cmd_lower:
                desktop_icons['mode'] = 'custom'
                # 解析各个图标设置（简化处理，实际需要更复杂的解析）
                # 查找图标 GUID 和值
                import re
                icon_guids = {
                    '20D04FE0-3AEA-1069-A2D8-08002B30309D': 'iconThisPC',
                    '59031a47-3f72-44a7-89c5-5595fe6b30ee': 'iconUserFiles',
                    'F02C1A0D-BE21-4350-88B0-7367FC96EF3C': 'iconNetwork',
                    '5399E694-6CE5-4D6C-8FCE-1F8870FDC54F': 'iconControlPanel',
                    '645FF040-5081-101B-9F08-00AA002F954E': 'iconRecycleBin',
                    '374DE290-123F-4565-9164-39C4925E467B': 'iconDownloads',
                    '3ADD1653-EB32-4CB0-BBD7-DFA0BB5C5CDD': 'iconMusic',
                    'A0953C92-50DC-43BF-BE83-3742EED94C19': 'iconVideos',
                    'A8CDFF1C-4878-43BE-B5FD-F8091C1C60D0': 'iconDocuments',
                    'B4BFCC3A-DB2C-424C-B029-7FE99A87C641': 'iconDesktop',
                    '24ad3ad4-a569-4530-98e1-ab02f9417aa8': 'iconPictures',
                    'f86fa3ab-70d2-4fc7-9cd5-c559ae2e4d33': 'iconGallery',
                    'd3162b92-9365-467a-956b-927d1adc84c3': 'iconHome'
                }
                for guid, field_name in icon_guids.items():
                    if guid.lower() in cmd_lower:
                        value_match = re.search(r'-Value\s+(\d+)', cmd_text, re.IGNORECASE)
                        if value_match:
                            icon_value = int(value_match.group(1))
                            desktop_icons[field_name] = icon_value == 0  # 0 表示显示，1 表示隐藏
        
        config_dict['desktopIcons'] = desktop_icons
        
        # StartFolders - 从注册表命令中解析
        start_folders: Dict[str, Any] = {'mode': 'default'}
        
        for cmd_text in all_commands:
            cmd_lower = cmd_text.lower()
            # 查找开始菜单文件夹相关注册表项（简化处理）
            if 'startmenu' in cmd_lower and 'folder' in cmd_lower:
                start_folders['mode'] = 'custom'
                # 解析各个文件夹设置（需要根据实际注册表项解析）
        
        config_dict['startFolders'] = start_folders
        
        # Personalization - 从脚本文件中解析
        personalization: Dict[str, Any] = {
            'wallpaperMode': 'default',
            'lockScreenMode': 'default',
            'colorMode': 'default'
        }
        
        # 查找壁纸相关脚本
        for cmd_text in all_commands:
            cmd_lower = cmd_text.lower()
            if 'setwallpaper' in cmd_lower or 'getwallpaper' in cmd_lower:
                if 'setwallpapercolor' in cmd_lower:
                    personalization['wallpaperMode'] = 'solid'
                    # 尝试提取颜色值
                    import re
                    color_match = re.search(r'-HtmlColor\s+[\'"]?([#\w]+)[\'"]?', cmd_text, re.IGNORECASE)
                    if color_match:
                        personalization['wallpaperColor'] = color_match.group(1)
                elif 'setwallpaperimage' in cmd_lower or 'getwallpaper' in cmd_lower:
                    personalization['wallpaperMode'] = 'script'
                    # 尝试获取脚本内容
                    getter_file = self._get_script_file_content(root, r'C:\Windows\Setup\Scripts\GetWallpaper.ps1')
                    if getter_file:
                        personalization['wallpaperScript'] = getter_file
        
        # 查找锁屏相关脚本
        for cmd_text in all_commands:
            cmd_lower = cmd_text.lower()
            if 'lockscreen' in cmd_lower or 'getlockscreenimage' in cmd_lower:
                personalization['lockScreenMode'] = 'script'
                getter_file = self._get_script_file_content(root, r'C:\Windows\Setup\Scripts\GetLockScreenImage.ps1')
                if getter_file:
                    personalization['lockScreenScript'] = getter_file
        
        # 查找颜色主题相关脚本
        for cmd_text in all_commands:
            cmd_lower = cmd_text.lower()
            if 'setcolortheme' in cmd_lower or 'colortheme' in cmd_lower:
                personalization['colorMode'] = 'custom'
                # 尝试从脚本中提取颜色设置
                theme_file = self._get_script_file_content(root, r'C:\Windows\Setup\Scripts\SetColorTheme.ps1')
                if theme_file:
                    import re
                    # 提取主题设置
                    system_match = re.search(r'\$lightThemeSystem\s*=\s*(\d+)', theme_file)
                    apps_match = re.search(r'\$lightThemeApps\s*=\s*(\d+)', theme_file)
                    if system_match:
                        personalization['systemColorTheme'] = 'light' if system_match.group(1) == '0' else 'dark'
                    if apps_match:
                        personalization['appsColorTheme'] = 'light' if apps_match.group(1) == '0' else 'dark'
                    
                    accent_match = re.search(r'\$htmlAccentColor\s*=\s*[\'"]?([#\w]+)[\'"]?', theme_file)
                    if accent_match:
                        personalization['accentColor'] = accent_match.group(1)
        
        config_dict['personalization'] = personalization
        
        # SystemTweaks - 从注册表命令和脚本中解析
        system_tweaks: Dict[str, Any] = {
            'enableLongPaths': False,
            'enableRemoteDesktop': False,
            'hardenSystemDriveAcl': False,
            'deleteJunctions': False,
            'allowPowerShellScripts': False,
            'disableLastAccess': False,
            'preventAutomaticReboot': False,
            'disableDefender': False,
            'disableSac': False,
            'disableUac': False,
            'disableSmartScreen': False,
            'disableSystemRestore': False,
            'disableFastStartup': False,
            'turnOffSystemSounds': False,
            'disableAppSuggestions': False,
            'disableWidgets': False,
            'preventDeviceEncryption': False,
            'classicContextMenu': False,
            'disableWindowsUpdate': False,
            'disablePointerPrecision': False,
            'deleteWindowsOld': False,
            'disableCoreIsolation': False,
            'showEndTask': False
        }
        
        for cmd_text in all_commands:
            cmd_lower = cmd_text.lower()
            
            # enableLongPaths: LongPathsEnabled = 1
            if 'longpathsenabled' in cmd_lower and 'reg.exe' in cmd_lower:
                if self._check_registry_command(cmd_text, r'HKLM\\SYSTEM\\CurrentControlSet\\Control\\FileSystem', 'LongPathsEnabled', '1'):
                    system_tweaks['enableLongPaths'] = True
            
            # enableRemoteDesktop: fDenyTSConnections = 0
            if 'fdenytsconnections' in cmd_lower and 'reg.exe' in cmd_lower:
                value = self._parse_registry_command(cmd_text, r'HKLM\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server', 'fDenyTSConnections')
                if value == '0':
                    system_tweaks['enableRemoteDesktop'] = True
            
            # preventDeviceEncryption: PreventDeviceEncryption = 1
            if 'preventdeviceencryption' in cmd_lower and 'reg.exe' in cmd_lower:
                if self._check_registry_command(cmd_text, r'HKLM\\SYSTEM\\CurrentControlSet\\Control\\BitLocker', 'PreventDeviceEncryption', '1'):
                    system_tweaks['preventDeviceEncryption'] = True
            
            # classicContextMenu: 查找 {86ca1aa0-34aa-4e8b-a509-50c905bae2a2} CLSID
            if '{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}' in cmd_text:
                system_tweaks['classicContextMenu'] = True
            
            # hardenSystemDriveAcl: 查找 icacls 命令
            if 'icacls' in cmd_lower and 'remove:g' in cmd_lower:
                system_tweaks['hardenSystemDriveAcl'] = True
            
            # deleteJunctions: 查找删除 junction 的脚本
            if 'reparsepoint' in cmd_lower or ('junction' in cmd_lower and 'remove' in cmd_lower):
                system_tweaks['deleteJunctions'] = True
        
        config_dict['systemTweaks'] = system_tweaks
        
        # Bloatware - 从脚本文件中解析
        bloatware: Dict[str, Any] = {'items': []}
        
        # 查找移除脚本（files 已在 Scripts 解析中定义）
        files = root.findall(f".//{{{ns_uri}}}File")
        for file_elem in files:
            destination_path_elem = file_elem.find(f"{{{ns_uri}}}DestinationPath")
            if destination_path_elem is not None and destination_path_elem.text:
                file_path = destination_path_elem.text
                file_name_lower = file_path.lower()
                
                # 查找移除脚本（RemoveBloatware.ps1 或类似的脚本）
                if 'removebloatware' in file_name_lower or 'remove' in file_name_lower and 'bloatware' in file_name_lower:
                    data_elem = file_elem.find(f"{{{ns_uri}}}Data")
                    if data_elem is not None and data_elem.text:
                        script_content = data_elem.text
                        # 从脚本中提取选择器（selector）
                        import re
                        # 查找 $selectors = @(...) 模式
                        selectors_match = re.search(r'\$selectors\s*=\s*@\s*\((.*?)\)', script_content, re.DOTALL)
                        if selectors_match:
                            selectors_text = selectors_match.group(1)
                            # 提取每个选择器（单引号或双引号字符串）
                            selector_matches = re.findall(r'[\'"]([^\'"]+)[\'"]', selectors_text)
                            for selector in selector_matches:
                                # 尝试识别预装软件 ID（简化处理，实际需要更复杂的匹配逻辑）
                                # 这里只是示例，实际需要根据 generator.bloatwares 进行匹配
                                if selector.strip():
                                    bloatware['items'].append(selector.strip())
        
        config_dict['bloatware'] = bloatware
        
        # ExpressSettings - 从注册表命令中解析
        # 解析快速设置（Express Settings）
        # 优先从 OOBE 中的 ProtectYourPC 解析
        express_settings = 'disableAll'
        oobe_component = root.find(f".//{{{ns_uri}}}component[@name='Microsoft-Windows-Shell-Setup']")
        if oobe_component is not None:
            # 查找第一个 OOBE 元素（可能有多个）
            oobe_elem = oobe_component.find(f"{{{ns_uri}}}OOBE")
            if oobe_elem is not None:
                protect_your_pc = oobe_elem.find(f"{{{ns_uri}}}ProtectYourPC")
                if protect_your_pc is not None and protect_your_pc.text:
                    protect_value = protect_your_pc.text.strip()
                    if protect_value == '1':
                        express_settings = 'enableAll'
                    elif protect_value == '3':
                        express_settings = 'disableAll'
                    # 如果不存在或为空，默认为 interactive（但这里我们设为 disableAll）
        
        # 如果 OOBE 中没有找到 ProtectYourPC，尝试从注册表命令中解析
        if express_settings == 'disableAll':
            for cmd_text in all_commands:
                cmd_lower = cmd_text.lower()
                # 查找 DisableWindowsConsumerFeatures 注册表项
                if 'disablewindowsconsumerfeatures' in cmd_lower and 'reg.exe' in cmd_lower:
                    value = self._parse_registry_command(cmd_text, r'HKLM\\Software\\Policies\\Microsoft\\Windows\\CloudContent', 'DisableWindowsConsumerFeatures')
                    if value == '1':
                        express_settings = 'disableAll'
                    elif value == '0':
                        express_settings = 'enableAll'
                    break
        
        config_dict['expressSettings'] = express_settings
        
        # VMSupport - 从脚本调用中解析
        vm_support: Dict[str, Any] = {
            'vBoxGuestAdditions': False,
            'vmwareTools': False,
            'virtIoGuestTools': False,
            'parallelsTools': False
        }
        
        for cmd_text in all_commands:
            cmd_lower = cmd_text.lower()
            
            # 查找虚拟机工具安装脚本
            if 'vboxguestadditions' in cmd_lower or 'virtualbox' in cmd_lower:
                vm_support['vBoxGuestAdditions'] = True
            if 'vmwaretools' in cmd_lower or ('vmware' in cmd_lower and 'tools' in cmd_lower):
                vm_support['vmwareTools'] = True
            if 'virtioguesttools' in cmd_lower or 'virt-io' in cmd_lower or 'virtio' in cmd_lower:
                vm_support['virtIoGuestTools'] = True
            if 'parallelstools' in cmd_lower or 'parallels' in cmd_lower:
                vm_support['parallelsTools'] = True
        
        config_dict['vmSupport'] = vm_support
        
        # WDAC - 默认值（已在前面设置）
        if 'wdac' not in config_dict:
            config_dict['wdac'] = {'mode': 'skip'}
        
        # Scripts - 从脚本文件中解析
        scripts_dict: Dict[str, Any] = {
            'system': [],
            'defaultUser': [],
            'firstLogon': [],
            'userOnce': [],
            'restartExplorer': False
        }
        
        # 查找所有脚本文件
        ns_uri = '{urn:schemas-microsoft-com:unattend}'
        ext_ns_uri = 'https://schneegans.de/windows/unattend-generator/'
        import uuid
        
        # 查找默认命名空间中的 File 元素
        files = root.findall(f".//{{{ns_uri}}}File")
        # 查找 Extensions 命名空间中的 File 元素
        ext_files = root.findall(f".//{{{ext_ns_uri}}}File")
        
        # 合并所有文件元素
        all_file_elems = []
        for file_elem in files:
            destination_path_elem = file_elem.find(f"{{{ns_uri}}}DestinationPath")
            if destination_path_elem is not None and destination_path_elem.text:
                all_file_elems.append({
                    'elem': file_elem,
                    'path': destination_path_elem.text,
                    'ns': ns_uri
                })
        
        for file_elem in ext_files:
            path_attr = file_elem.get('path')
            if path_attr:
                all_file_elems.append({
                    'elem': file_elem,
                    'path': path_attr,
                    'ns': ext_ns_uri
                })
        
        for file_info in all_file_elems:
            file_elem = file_info['elem']
            file_path = file_info['path']
            file_ns = file_info['ns']
            
            # 检查是否是脚本文件
            if 'C:\\Windows\\Setup\\Scripts\\' in file_path or 'C:/Windows/Setup/Scripts/' in file_path:
                file_name_lower = file_path.lower()
                # 检查是否是脚本文件（.cmd, .ps1, .reg, .vbs, .js）
                is_script = any(file_name_lower.endswith(ext) for ext in ['.cmd', '.ps1', '.reg', '.vbs', '.js'])
                
                # 检查是否是特殊脚本文件（FirstLogon.ps1, UserOnce.ps1, DefaultUser.ps1）
                # 这些是包装脚本，它们的内容不应该被解析为多个脚本
                is_special_script = any(name in file_name_lower for name in ['firstlogon.ps1', 'useronce.ps1', 'defaultuser.ps1', 'specialize.ps1'])
                # 检查是否是自定义脚本（unattend-*）
                # 注意：unattend-* 文件不应该被解析，因为它们是被包装脚本调用的
                is_custom_script = 'unattend-' in file_name_lower
                
                # 只解析特殊脚本文件，不解析 unattend-* 文件
                # 特殊脚本文件（FirstLogon.ps1, UserOnce.ps1, DefaultUser.ps1, Specialize.ps1）是包装脚本
                # 它们的内容不应该被解析为多个脚本项，而是直接作为这些文件处理
                # 但是，这些文件的内容需要被保存到 Extensions 中，以便生成时能够恢复
                if is_script and is_special_script and not is_custom_script:
                    import logging
                    logger = logging.getLogger('UnattendGenerator')
                    logger.debug(f"parse_xml: Skipping special script file (wrapper script) for script parsing, but preserving in Extensions: {file_path}")
                    # 不解析包装脚本为脚本项，但它们的内容会被保存到 Extensions 中
                    # 这样生成时 FirstLogonModifier、UserOnceModifier 等可以直接使用
                    continue
                elif is_script and is_custom_script:
                    import logging
                    logger = logging.getLogger('UnattendGenerator')
                    logger.debug(f"parse_xml: Skipping custom script file (unattend-*): {file_path}")
                    # 不解析 unattend-* 文件，它们是被包装脚本调用的
                    continue
        
        # 检查是否有重启 Explorer 的命令
        for cmd_text in all_commands:
            if 'restart-explorer' in cmd_text.lower() or 'restart explorer' in cmd_text.lower():
                scripts_dict['restartExplorer'] = True
        
        config_dict['scripts'] = scripts_dict
        
        # XmlMarkup - 从自定义 component 元素中解析
        xml_markup: Dict[str, Any] = {'components': []}
        
        # 标准组件列表（这些不应该被包含在 xmlMarkup 中）
        standard_components = {
            'Microsoft-Windows-International-Core-WinPE',
            'Microsoft-Windows-International-Core',
            'Microsoft-Windows-Shell-Setup',
            'Microsoft-Windows-Deployment',
            'Microsoft-Windows-Setup',
            'Microsoft-Windows-UnattendedJoin',
            'Microsoft-Windows-IE-InternetExplorer',
            'Microsoft-Windows-Embedded-ShellLauncher'
        }
        
        # 查找所有 component 元素
        components = root.findall(f".//{{{ns_uri}}}component")
        for component in components:
            component_name = component.get('name')
            if component_name and component_name not in standard_components:
                # 获取 pass 属性
                settings_elem = component.find(f"..")
                if settings_elem is not None:
                    pass_attr = settings_elem.get('pass')
                    if pass_attr:
                        # 提取 component 的 XML 内容（返回字符串）
                        component_xml: str = ET.tostring(component, encoding='unicode')
                        
                        xml_markup['components'].append({
                            'component': component_name,
                            'pass': pass_attr,
                            'xml': component_xml  # 前端期望字符串类型
                        })
        
        config_dict['xmlMarkup'] = xml_markup
        
        # 解析 Extensions 部分
        s_uri = "https://schneegans.de/windows/unattend-generator/"
        extensions_elem = root.find(f"{{{s_uri}}}Extensions")
        if extensions_elem is not None:
            extensions_dict: Dict[str, Any] = {}
            
            # 解析 ExtractScript
            extract_script_elem = extensions_elem.find(f"{{{s_uri}}}ExtractScript")
            if extract_script_elem is not None and extract_script_elem.text:
                extensions_dict['extractScript'] = extract_script_elem.text.strip()
            
            # 解析所有 File 元素
            # 注意：unattend-* 文件应该被保存到 extensions 中，以便生成时能够恢复
            # 但它们不应该被解析为脚本项（在脚本解析部分已经跳过）
            files = []
            for file_elem in extensions_elem.findall(f"{{{s_uri}}}File"):
                path_attr = file_elem.get('path', '')
                content = file_elem.text if file_elem.text else ''
                # 如果没有文本，尝试从子元素获取
                if not content:
                    content = ''.join(file_elem.itertext()).strip()
                files.append({
                    'path': path_attr,
                    'content': content
                })
            
            if files:
                extensions_dict['files'] = files
            
            if extensions_dict:
                config_dict['extensions'] = extensions_dict
        
        return config_dict


# ========================================
# 辅助函数
# ========================================

def create_default_configuration() -> Configuration:
    """创建默认配置（对应 C# 的 Configuration.Default）"""
    return Configuration()


# ========================================
# 配置转换函数（前端配置字典 <-> Python Configuration）
# ========================================

def config_dict_to_configuration(config_dict: Dict[str, Any], generator: Optional['UnattendGenerator'] = None) -> Configuration:
    """将前端配置字典转换为 Python Configuration 对象"""
    import json
    import logging
    logger = logging.getLogger('UnattendGenerator')
    
    # 规范化配置字典：确保所有应该是字典的值都是字典
    def normalize_dict(obj: Any) -> Any:
        """递归规范化字典，将 JSON 字符串转换为字典"""
        if isinstance(obj, str):
            # 尝试解析为 JSON
            try:
                parsed = json.loads(obj)
                return normalize_dict(parsed)  # 递归处理解析后的对象
            except (json.JSONDecodeError, TypeError):
                # 不是 JSON 字符串，返回原值
                return obj
        elif isinstance(obj, dict):
            # 递归处理字典的所有值
            return {k: normalize_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            # 递归处理列表的所有元素
            return [normalize_dict(item) for item in obj]
        else:
            return obj
    
    # 规范化配置字典
    try:
        config_dict = normalize_dict(config_dict)
    except Exception as e:
        logger.warning(f"Failed to normalize config_dict: {e}")
        # 继续处理，可能部分数据已经是正确的格式
    
    # 创建基础配置
    config = Configuration()
    
    # 如果没有提供 generator，创建一个临时实例用于查找
    if generator is None:
        generator = UnattendGenerator()
    
    # 转换语言设置
    if 'languageSettings' in config_dict:
        lang = config_dict['languageSettings']
        # 确保 lang 是字典
        if not isinstance(lang, dict):
            logger.warning(f"languageSettings is not a dict, got {type(lang)}, using default")
            config.language_settings = InteractiveLanguageSettings()
        else:
            mode = lang.get('mode', 'interactive')
            
            if mode == 'interactive':
                config.language_settings = InteractiveLanguageSettings()
            elif mode == 'unattended':
                # 无人值守模式
                image_lang_id = lang.get('uiLanguage', 'en-US')
                locale_id = lang.get('systemLocale', 'en-US')
                keyboard_id = lang.get('inputLocale', '00000409')  # 默认 US 键盘
                has_winpe = lang.get('hasWinPE', True)  # 默认 True 保持向后兼容
                
                # 查找对象，如果查找失败则直接创建对象
                image_language = generator.lookup(ImageLanguage, image_lang_id)
                if image_language is None:
                    image_language = ImageLanguage(id=image_lang_id, display_name=image_lang_id)
                
                user_locale = generator.lookup(UserLocale, locale_id)
                if user_locale is None:
                    user_locale = UserLocale(id=locale_id, display_name=locale_id, lcid=locale_id)
                
                keyboard = generator.lookup(KeyboardIdentifier, keyboard_id)
                if keyboard is None:
                    # 解析键盘 ID（可能是 "0804:{guid}{guid}" 格式）
                    keyboard_id_clean = keyboard_id.split(':')[0] if ':' in keyboard_id else keyboard_id
                    keyboard = KeyboardIdentifier(id=keyboard_id, display_name=keyboard_id, type=InputType.Keyboard)
                
                locale_and_keyboard = LocaleAndKeyboard(
                    locale=user_locale,
                    keyboard=keyboard
                )
                
                geo_location = None
                if 'geoLocation' in lang and lang['geoLocation']:
                    geo_location = generator.lookup(GeoLocation, lang['geoLocation'])
                    if geo_location is None:
                        geo_location = GeoLocation(id=lang['geoLocation'], display_name=lang['geoLocation'])
                
                config.language_settings = UnattendedLanguageSettings(
                    image_language=image_language,
                    locale_and_keyboard=locale_and_keyboard,
                    geo_location=geo_location,
                    has_winpe=has_winpe
                )
                # 保留 WinPE 键盘布局（如果解析阶段提取到）
                if 'winPEKeyboardLayout' in lang:
                    setattr(config.language_settings, 'winpe_keyboard_layout', lang['winPEKeyboardLayout'])
    
    # 转换时区设置
    if 'timeZone' in config_dict:
        tz = config_dict['timeZone']
        # 确保 tz 是字典
        if not isinstance(tz, dict):
            logger.warning(f"timeZone is not a dict, got {type(tz)}, skipping")
        else:
            mode = tz.get('mode', 'implicit')
        
            if mode == 'implicit':
                config.time_zone_settings = ImplicitTimeZoneSettings()
            elif mode == 'explicit':
                timezone_id = tz.get('timeZone', '')
                if timezone_id:
                    time_offset = generator.lookup(TimeOffset, timezone_id)
                    # 如果查找失败，直接创建 TimeOffset 对象
                    if time_offset is None:
                        time_offset = TimeOffset(id=timezone_id, display_name=timezone_id)
                    config.time_zone_settings = ExplicitTimeZoneSettings(time_zone=time_offset)
    
    # 转换处理器架构
    if 'processorArchitectures' in config_dict:
        archs = config_dict['processorArchitectures']
        if isinstance(archs, list):
            config.processor_architectures = {
                ProcessorArchitecture(arch) for arch in archs
            }
        else:
            logger.warning(f"processorArchitectures is not a list, got {type(archs)}")
    
    # 转换 Setup Settings（模块 2）
    if 'setupSettings' in config_dict:
        setup = config_dict['setupSettings']
        # 确保 setup 是字典
        if not isinstance(setup, dict):
            logger.warning(f"setupSettings is not a dict, got {type(setup)}, skipping")
        else:
            config.bypass_requirements_check = setup.get('bypassRequirementsCheck', False)
            config.bypass_network_check = setup.get('bypassNetworkCheck', False)
            config.use_configuration_set = setup.get('useConfigurationSet', False)
            config.hide_power_shell_windows = setup.get('hidePowerShellWindows', False)
            config.keep_sensitive_files = setup.get('keepSensitiveFiles', False)
            config.use_narrator = setup.get('useNarrator', False)
    
    # 转换模块 4: Name and Account
    # 转换计算机名设置
    if 'computerName' in config_dict:
        cn = config_dict['computerName']
        # 确保 cn 是字典
        if not isinstance(cn, dict):
            logger.warning(f"computerName is not a dict, got {type(cn)}, using default")
            config.computer_name_settings = RandomComputerNameSettings()
        else:
            mode = cn.get('mode', 'random')
            
            if mode == 'random':
                config.computer_name_settings = RandomComputerNameSettings()
            elif mode == 'custom':
                name = cn.get('name', '')
                if name:
                    config.computer_name_settings = CustomComputerNameSettings(computer_name=name)
                else:
                    config.computer_name_settings = RandomComputerNameSettings()
            elif mode == 'script':
                script = cn.get('script', '')
                if script:
                    config.computer_name_settings = ScriptComputerNameSettings(script=script)
                else:
                    config.computer_name_settings = RandomComputerNameSettings()
            else:
                config.computer_name_settings = RandomComputerNameSettings()
    else:
        config.computer_name_settings = RandomComputerNameSettings()
    
    # 转换账户设置
    if 'accountSettings' in config_dict:
        accounts = config_dict['accountSettings']
        # 确保 accounts 是字典
        if not isinstance(accounts, dict):
            logger.warning(f"accountSettings is not a dict, got {type(accounts)}, using default")
            config.account_settings = InteractiveMicrosoftAccountSettings()
        else:
            mode = accounts.get('mode', 'interactive-microsoft')
            
            if mode == 'unattended':
                # 创建账户列表
                account_list = []
                accounts_list = accounts.get('accounts', [])
                if isinstance(accounts_list, list):
                    for acc_dict in accounts_list:
                        if isinstance(acc_dict, dict):
                            account = Account(
                                name=acc_dict.get('name', ''),
                                display_name=acc_dict.get('displayName', acc_dict.get('name', '')),
                                password=acc_dict.get('password', Constants.DefaultPassword),
                                group=acc_dict.get('group', Constants.UsersGroup)
                            )
                            account_list.append(account)
                
                # 创建自动登录设置
                auto_logon_mode = accounts.get('autoLogonMode', 'none')
                if auto_logon_mode == 'builtin':
                    auto_logon_settings = BuiltinAutoLogonSettings(
                        password=accounts.get('autoLogonPassword', Constants.DefaultPassword)
                    )
                elif auto_logon_mode == 'own':
                    auto_logon_settings = OwnAutoLogonSettings()
                else:
                    auto_logon_settings = NoneAutoLogonSettings()
                
                config.account_settings = UnattendedAccountSettings(
                    accounts=account_list,
                    auto_logon_settings=auto_logon_settings,
                    obscure_passwords=accounts.get('obscurePasswords', False)
                )
            elif mode == 'interactive-local':
                config.account_settings = InteractiveLocalAccountSettings()
            else:
                config.account_settings = InteractiveMicrosoftAccountSettings()
    else:
        config.account_settings = InteractiveMicrosoftAccountSettings()
    
    # 转换密码过期设置
    if 'passwordExpiration' in config_dict:
        pe = config_dict['passwordExpiration']
        # 确保 pe 是字典
        if not isinstance(pe, dict):
            logger.warning(f"passwordExpiration is not a dict, got {type(pe)}, using default")
            config.password_expiration_settings = DefaultPasswordExpirationSettings()
        else:
            mode = pe.get('mode', 'default')
            
            if mode == 'unlimited':
                config.password_expiration_settings = UnlimitedPasswordExpirationSettings()
            elif mode == 'custom':
                max_age = pe.get('maxAge', DefaultPasswordExpirationSettings.MaxAge)
                config.password_expiration_settings = CustomPasswordExpirationSettings(max_age=max_age)
            else:
                config.password_expiration_settings = DefaultPasswordExpirationSettings()
    else:
        config.password_expiration_settings = DefaultPasswordExpirationSettings()
    
    # 转换账户锁定设置
    if 'lockoutSettings' in config_dict:
        lockout = config_dict['lockoutSettings']
        # 确保 lockout 是字典
        if not isinstance(lockout, dict):
            logger.warning(f"lockoutSettings is not a dict, got {type(lockout)}, using default")
            config.lockout_settings = DefaultLockoutSettings()
        else:
            mode = lockout.get('mode', 'default')
            
            if mode == 'disabled':
                config.lockout_settings = DisableLockoutSettings()
            elif mode == 'custom':
                config.lockout_settings = CustomLockoutSettings(
                    lockout_threshold=lockout.get('lockoutThreshold', 0),
                    lockout_duration=lockout.get('lockoutDuration', 30),
                    lockout_window=lockout.get('lockoutWindow', 30)
                )
            else:
                config.lockout_settings = DefaultLockoutSettings()
    else:
        config.lockout_settings = DefaultLockoutSettings()
    
    # 转换模块 5: Partitioning and formatting
    # 转换分区设置
    if 'partitioning' in config_dict:
        partitioning = config_dict['partitioning']
        # 确保 partitioning 是字典
        if not isinstance(partitioning, dict):
            logger.warning(f"partitioning is not a dict, got {type(partitioning)}, using default")
            config.partition_settings = InteractivePartitionSettings()
        else:
            mode = partitioning.get('mode', 'interactive')
            
            if mode == 'interactive':
                config.partition_settings = InteractivePartitionSettings()
            elif mode == 'automatic':
                recovery_mode_str = partitioning.get('recoveryMode', 'partition')
                # 转换前端值到枚举值
                recovery_mode_map = {
                    'none': RecoveryMode.None_,
                    'folder': RecoveryMode.Folder,
                    'partition': RecoveryMode.Partition
                }
                recovery_mode = recovery_mode_map.get(recovery_mode_str.lower(), RecoveryMode.Partition)
                
                config.partition_settings = UnattendedPartitionSettings(
                    partition_layout=PartitionLayout(partitioning.get('layout', 'GPT')),
                    recovery_mode=recovery_mode,
                    esp_size=partitioning.get('espSize', Constants.EspDefaultSize),
                    recovery_size=partitioning.get('recoverySize', Constants.RecoveryPartitionSize)
                )
            elif mode == 'custom':
                install_to_mode = partitioning.get('installToMode', 'available')
                if install_to_mode == 'custom':
                    install_to = CustomInstallToSettings(
                        install_to_disk=partitioning.get('installToDisk', 0),
                        install_to_partition=partitioning.get('installToPartition', 1)
                    )
                else:
                    install_to = AvailableInstallToSettings()
                
                config.partition_settings = CustomPartitionSettings(
                    script=partitioning.get('diskpartScript', ''),
                    install_to=install_to
                )
            else:
                config.partition_settings = InteractivePartitionSettings()
    else:
        config.partition_settings = InteractivePartitionSettings()
    
    # 转换磁盘断言设置
    if 'partitioning' in config_dict:
        partitioning = config_dict['partitioning']
        # 确保 partitioning 是字典
        if not isinstance(partitioning, dict):
            logger.warning(f"partitioning is not a dict for diskAssertion, got {type(partitioning)}, using default")
            config.disk_assertion_settings = SkipDiskAssertionSettings()
        else:
            disk_assertion_mode = partitioning.get('diskAssertionMode', 'skip')
            if disk_assertion_mode == 'script':
                script_content = partitioning.get('diskAssertionScript', '')
                # 如果从 XML 无法解析出具体脚本内容，使用占位符以便生成写入命令
                if script_content is None or script_content.strip() == '':
                    script_content = ''
                config.disk_assertion_settings = ScriptDiskAssertionsSettings(
                    script=script_content
                )
            else:
                config.disk_assertion_settings = SkipDiskAssertionSettings()
    else:
        config.disk_assertion_settings = SkipDiskAssertionSettings()
    
    # 转换 PE 设置
    if 'peSettings' in config_dict:
        pe_settings = config_dict['peSettings']
        # 确保 pe_settings 是字典
        if not isinstance(pe_settings, dict):
            logger.warning(f"peSettings is not a dict, got {type(pe_settings)}, using default")
            config.pe_settings = DefaultPESettings()
        else:
            mode = pe_settings.get('mode', 'default')
            
            if mode == 'generated':
                config.pe_settings = GeneratePESettings(
                    disable_8_dot3_names=pe_settings.get('disable8Dot3Names', False),
                    pause_before_formatting=pe_settings.get('pauseBeforeFormatting', False),
                    pause_before_reboot=pe_settings.get('pauseBeforeReboot', False)
                )
            elif mode == 'script':
                config.pe_settings = ScriptPESettings(
                    script=pe_settings.get('cmdScript', '')
                )
            else:
                config.pe_settings = DefaultPESettings()
    else:
        config.pe_settings = DefaultPESettings()
    
    # 转换 Compact OS 模式
    if 'compactOS' in config_dict:
        compact_os = config_dict['compactOS']
        if isinstance(compact_os, str):
            if compact_os == 'enabled':
                config.compact_os_mode = CompactOsModes.Always
            elif compact_os == 'disabled':
                config.compact_os_mode = CompactOsModes.Never
            else:
                config.compact_os_mode = CompactOsModes.Default
        else:
            config.compact_os_mode = CompactOsModes.Default
    else:
        config.compact_os_mode = CompactOsModes.Default
    
    # 转换模块 6: Windows Edition and Source
    # 转换版本设置
    if 'windowsEdition' in config_dict:
        edition = config_dict['windowsEdition']
        # 确保 edition 是字典
        if not isinstance(edition, dict):
            logger.warning(f"windowsEdition is not a dict, got {type(edition)}, using default")
            config.edition_settings = InteractiveEditionSettings()
        else:
            mode = edition.get('mode', 'interactive')
            
            if mode == 'interactive':
                config.edition_settings = InteractiveEditionSettings()
            elif mode == 'firmware':
                config.edition_settings = FirmwareEditionSettings()
            elif mode == 'unattended' or mode == 'name' or mode == 'index' or mode == 'generic':
                # 支持多种模式：unattended, name, index, generic 都使用 editionName
                edition_id = edition.get('editionName') or edition.get('edition') or edition.get('editionIndex')
                if edition_id and generator:
                    # 如果是数字，尝试作为 index 查找
                    if isinstance(edition_id, int) or (isinstance(edition_id, str) and edition_id.isdigit()):
                        # 暂时不支持按 index 查找，需要更多信息
                        config.edition_settings = InteractiveEditionSettings()
                    else:
                        windows_edition = generator.lookup(WindowsEdition, str(edition_id))
                        if windows_edition:
                            config.edition_settings = UnattendedEditionSettings(edition=windows_edition)
                        else:
                            config.edition_settings = InteractiveEditionSettings()
                else:
                    config.edition_settings = InteractiveEditionSettings()
            elif mode == 'custom' or mode == 'key':
                product_key = edition.get('productKey', '')
                if product_key:
                    config.edition_settings = CustomEditionSettings(product_key=product_key)
                else:
                    config.edition_settings = InteractiveEditionSettings()
            else:
                config.edition_settings = InteractiveEditionSettings()
    else:
        config.edition_settings = InteractiveEditionSettings()
    
    # 转换安装源设置
    if 'sourceImage' in config_dict:
        source = config_dict['sourceImage']
        # 确保 source 是字典
        if not isinstance(source, dict):
            logger.warning(f"sourceImage is not a dict, got {type(source)}, using default")
            config.install_from_settings = AutomaticInstallFromSettings()
        else:
            mode = source.get('mode', 'automatic')
            
            if mode == 'automatic':
                detected_name = config_dict.get('detectedImageName') or source.get('name') or source.get('imageName')
                config.install_from_settings = AutomaticInstallFromSettings()
                if detected_name:
                    setattr(config, "_detected_image_name", detected_name)
            elif mode == 'index':
                index = source.get('index', 1)
                config.install_from_settings = IndexInstallFromSettings(index=index)
            elif mode == 'name':
                name = source.get('name', source.get('imageName', ''))
                config.install_from_settings = AutomaticInstallFromSettings()
                if name:
                    setattr(config, "_detected_image_name", name)
            else:
                config.install_from_settings = AutomaticInstallFromSettings()
    else:
        config.install_from_settings = AutomaticInstallFromSettings()
    
    # 转换模块 7: UI and Personalization
    # 转换 File Explorer 设置
    if 'fileExplorer' in config_dict:
        fe = config_dict['fileExplorer']
        # 确保 fe 是字典
        if not isinstance(fe, dict):
            logger.warning(f"fileExplorer is not a dict, got {type(fe)}, using default")
            config.show_file_extensions = False
            config.hide_files = HideModes.Hidden
        else:
            config.show_file_extensions = fe.get('showFileExtensions', False)
            hide_files_mode = fe.get('hideFiles', 'hidden')
            if hide_files_mode == 'none':
                config.hide_files = HideModes.None_
            elif hide_files_mode == 'hiddenSystem':
                config.hide_files = HideModes.HiddenSystem
            else:
                config.hide_files = HideModes.Hidden
    else:
        config.show_file_extensions = False
        config.hide_files = HideModes.Hidden
    
    # 转换 Start Menu and Taskbar 设置
    if 'startMenuTaskbar' in config_dict:
        smt = config_dict['startMenuTaskbar']
        # 确保 smt 是字典
        if not isinstance(smt, dict):
            logger.warning(f"startMenuTaskbar is not a dict, got {type(smt)}, using default")
            config.taskbar_search = TaskbarSearchMode.Box
            config.start_pins_settings = DefaultStartPinsSettings()
            config.start_tiles_settings = DefaultStartTilesSettings()
            config.taskbar_icons = DefaultTaskbarIcons()
        else:
            taskbar_search_str = smt.get('taskbarSearch', 'box')
            if taskbar_search_str == 'hide':
                config.taskbar_search = TaskbarSearchMode.Hide
            elif taskbar_search_str == 'icon':
                config.taskbar_search = TaskbarSearchMode.Icon
            elif taskbar_search_str == 'label':
                config.taskbar_search = TaskbarSearchMode.Label
            else:
                config.taskbar_search = TaskbarSearchMode.Box
            
            # Start Pins
            start_pins = smt.get('startPins', {})
            if isinstance(start_pins, dict):
                if start_pins.get('mode') == 'empty':
                    config.start_pins_settings = EmptyStartPinsSettings()
                elif start_pins.get('mode') == 'custom':
                    config.start_pins_settings = CustomStartPinsSettings(json=start_pins.get('json', '{"pinnedList":[]}'))
                else:
                    config.start_pins_settings = DefaultStartPinsSettings()
            else:
                config.start_pins_settings = DefaultStartPinsSettings()
            
            # Start Tiles
            start_tiles = smt.get('startTiles', {})
            if isinstance(start_tiles, dict):
                if start_tiles.get('mode') == 'empty':
                    config.start_tiles_settings = EmptyStartTilesSettings()
                elif start_tiles.get('mode') == 'custom':
                    config.start_tiles_settings = CustomStartTilesSettings(xml=start_tiles.get('xml', ''))
                else:
                    config.start_tiles_settings = DefaultStartTilesSettings()
            else:
                config.start_tiles_settings = DefaultStartTilesSettings()
            
            # Taskbar Icons
            taskbar_icons = smt.get('taskbarIcons', {})
            if isinstance(taskbar_icons, dict):
                if taskbar_icons.get('mode') == 'empty':
                    config.taskbar_icons = EmptyTaskbarIcons()
                elif taskbar_icons.get('mode') == 'custom':
                    config.taskbar_icons = CustomTaskbarIcons(xml=taskbar_icons.get('xml', ''))
                else:
                    config.taskbar_icons = DefaultTaskbarIcons()
            else:
                config.taskbar_icons = DefaultTaskbarIcons()
    else:
        config.taskbar_search = TaskbarSearchMode.Box
        config.start_pins_settings = DefaultStartPinsSettings()
        config.start_tiles_settings = DefaultStartTilesSettings()
        config.taskbar_icons = DefaultTaskbarIcons()
    
    # 转换 Visual Effects 设置
    if 'visualEffects' in config_dict:
        ve = config_dict['visualEffects']
        # 确保 ve 是字典
        if not isinstance(ve, dict):
            logger.warning(f"visualEffects is not a dict, got {type(ve)}, using default")
            config.effects = DefaultEffects()
        else:
            mode = ve.get('mode', 'default')
            if mode == 'bestAppearance':
                config.effects = BestAppearanceEffects()
            elif mode == 'bestPerformance':
                config.effects = BestPerformanceEffects()
            elif mode == 'custom':
                effects_dict = {}
                settings_dict = ve.get('settings', {})
                if isinstance(settings_dict, dict):
                    for effect_name, enabled in settings_dict.items():
                        try:
                            effect = Effect(effect_name)
                            effects_dict[effect] = enabled
                        except ValueError:
                            pass
                config.effects = CustomEffects(settings=effects_dict)
            else:
                config.effects = DefaultEffects()
    else:
        config.effects = DefaultEffects()
    
    # 转换 Desktop Icons 设置
    if 'desktopIcons' in config_dict:
        di = config_dict['desktopIcons']
        # 确保 di 是字典
        if not isinstance(di, dict):
            logger.warning(f"desktopIcons is not a dict, got {type(di)}, using default")
            config.desktop_icons = DefaultDesktopIconSettings()
        else:
            if di.get('mode') == 'custom':
                icons_dict = {}
                icons_data = di.get('icons', {})
                if isinstance(icons_data, dict):
                    for icon_id, visible in icons_data.items():
                        if generator:
                            desktop_icon = generator.lookup(DesktopIcon, icon_id)
                            if desktop_icon:
                                icons_dict[desktop_icon] = visible
                if icons_dict:
                    config.desktop_icons = CustomDesktopIconSettings(settings=icons_dict)
                else:
                    config.desktop_icons = DefaultDesktopIconSettings()
            else:
                config.desktop_icons = DefaultDesktopIconSettings()
    else:
        config.desktop_icons = DefaultDesktopIconSettings()
    
    # 转换 Start Folders 设置
    if 'startFolders' in config_dict:
        sf = config_dict['startFolders']
        # 确保 sf 是字典
        if not isinstance(sf, dict):
            logger.warning(f"startFolders is not a dict, got {type(sf)}, using default")
            config.start_folder_settings = DefaultStartFolderSettings()
        else:
            if sf.get('mode') == 'custom':
                folders_dict = {}
                folders_data = sf.get('folders', {})
                if isinstance(folders_data, dict):
                    for folder_id, enabled in folders_data.items():
                        if generator:
                            start_folder = generator.lookup(StartFolder, folder_id)
                            if start_folder:
                                folders_dict[start_folder] = enabled
                if folders_dict:
                    config.start_folder_settings = CustomStartFolderSettings(settings=folders_dict)
                else:
                    config.start_folder_settings = DefaultStartFolderSettings()
            else:
                config.start_folder_settings = DefaultStartFolderSettings()
    else:
        config.start_folder_settings = DefaultStartFolderSettings()
    
    # 转换 Personalization 设置
    if 'personalization' in config_dict:
        p = config_dict['personalization']
        # 确保 p 是字典
        if not isinstance(p, dict):
            logger.warning(f"personalization is not a dict, got {type(p)}, using default")
            config.wallpaper_settings = DefaultWallpaperSettings()
            config.lock_screen_settings = DefaultLockScreenSettings()
            config.color_settings = DefaultColorSettings()
        else:
            # Wallpaper
            wallpaper = p.get('wallpaper', {})
            if isinstance(wallpaper, dict) and wallpaper.get('mode') == 'solid':
                config.wallpaper_settings = SolidWallpaperSettings(color=wallpaper.get('color', '#000000'))
            elif isinstance(wallpaper, dict) and wallpaper.get('mode') == 'script':
                config.wallpaper_settings = ScriptWallpaperSettings(script=wallpaper.get('script', ''))
            else:
                config.wallpaper_settings = DefaultWallpaperSettings()
            
            # Lock Screen
            lock_screen = p.get('lockScreen', {})
            if isinstance(lock_screen, dict) and lock_screen.get('mode') == 'script':
                config.lock_screen_settings = ScriptLockScreenSettings(script=lock_screen.get('script', ''))
            else:
                config.lock_screen_settings = DefaultLockScreenSettings()
            
            # Color Settings
            color = p.get('color', {})
            if isinstance(color, dict) and color.get('mode') == 'custom':
                system_theme_str = color.get('systemTheme', 'dark')
                apps_theme_str = color.get('appsTheme', 'dark')
                config.color_settings = CustomColorSettings(
                    system_theme=ColorTheme.Dark if system_theme_str == 'dark' else ColorTheme.Light,
                    apps_theme=ColorTheme.Dark if apps_theme_str == 'dark' else ColorTheme.Light,
                    enable_transparency=color.get('enableTransparency', True),
                    accent_color_on_start=color.get('accentColorOnStart', False),
                    accent_color_on_borders=color.get('accentColorOnBorders', False),
                    accent_color=color.get('accentColor', '#0078D4')
                )
            else:
                config.color_settings = DefaultColorSettings()
    else:
        config.wallpaper_settings = DefaultWallpaperSettings()
        config.lock_screen_settings = DefaultLockScreenSettings()
        config.color_settings = DefaultColorSettings()
    
    # 转换模块 9: 辅助功能设置
    # 转换 Lock Keys 设置
    if 'lockKeys' in config_dict:
        lock_keys = config_dict['lockKeys']
        # 确保 lock_keys 是字典
        if not isinstance(lock_keys, dict):
            logger.warning(f"lockKeys is not a dict, got {type(lock_keys)}, using default")
            config.lock_key_settings = SkipLockKeySettings()
        else:
            mode = lock_keys.get('mode', 'skip')
            
            if mode == 'configure':
                config.lock_key_settings = ConfigureLockKeySettings(
                    caps_lock=LockKeySetting(
                        initial=LockKeyInitial.On if lock_keys.get('capsLockInitial') == 'on' else LockKeyInitial.Off,
                        behavior=LockKeyBehavior.Ignore if lock_keys.get('capsLockBehavior') == 'ignore' else LockKeyBehavior.Toggle
                    ),
                    num_lock=LockKeySetting(
                        initial=LockKeyInitial.On if lock_keys.get('numLockInitial') == 'on' else LockKeyInitial.Off,
                        behavior=LockKeyBehavior.Ignore if lock_keys.get('numLockBehavior') == 'ignore' else LockKeyBehavior.Toggle
                    ),
                    scroll_lock=LockKeySetting(
                        initial=LockKeyInitial.On if lock_keys.get('scrollLockInitial') == 'on' else LockKeyInitial.Off,
                        behavior=LockKeyBehavior.Ignore if lock_keys.get('scrollLockBehavior') == 'ignore' else LockKeyBehavior.Toggle
                    )
                )
            else:
                config.lock_key_settings = SkipLockKeySettings()
    else:
        config.lock_key_settings = SkipLockKeySettings()
    
    # 转换 Sticky Keys 设置
    if 'stickyKeys' in config_dict:
        sticky = config_dict['stickyKeys']
        # 确保 sticky 是字典
        if not isinstance(sticky, dict):
            logger.warning(f"stickyKeys is not a dict, got {type(sticky)}, using default")
            config.sticky_keys_settings = DefaultStickyKeysSettings()
        else:
            mode = sticky.get('mode', 'default')
            
            if mode == 'disabled':
                config.sticky_keys_settings = DisabledStickyKeysSettings()
            elif mode == 'custom':
                flags = set()
                if sticky.get('stickyKeysHotKeyActive', False):
                    flags.add(StickyKeys.HotKeyActive)
                if sticky.get('stickyKeysHotKeySound', False):
                    flags.add(StickyKeys.HotKeySound)
                if sticky.get('stickyKeysIndicator', False):
                    flags.add(StickyKeys.Indicator)
                if sticky.get('stickyKeysAudibleFeedback', False):
                    flags.add(StickyKeys.AudibleFeedback)
                if sticky.get('stickyKeysTriState', False):
                    flags.add(StickyKeys.TriState)
                if sticky.get('stickyKeysTwoKeysOff', False):
                    flags.add(StickyKeys.TwoKeysOff)
                config.sticky_keys_settings = CustomStickyKeysSettings(flags=flags)
            else:
                config.sticky_keys_settings = DefaultStickyKeysSettings()
    else:
        config.sticky_keys_settings = DefaultStickyKeysSettings()
    
    # 转换模块 10: 系统优化设置
    if 'systemTweaks' in config_dict:
        st = config_dict['systemTweaks']
        # 确保 st 是字典
        if not isinstance(st, dict):
            logger.warning(f"systemTweaks is not a dict, got {type(st)}, using default")
            # 使用默认值（已经在 Configuration 类中定义）
        else:
            config.enable_long_paths = st.get('enableLongPaths', False)
            config.enable_remote_desktop = st.get('enableRemoteDesktop', False)
            config.harden_system_drive_acl = st.get('hardenSystemDriveAcl', False)
            config.delete_junctions = st.get('deleteJunctions', False)
            config.allow_power_shell_scripts = st.get('allowPowerShellScripts', False)
            config.disable_last_access = st.get('disableLastAccess', False)
            config.prevent_automatic_reboot = st.get('preventAutomaticReboot', False)
            config.disable_defender = st.get('disableDefender', False)
            config.disable_sac = st.get('disableSac', False)
            config.disable_uac = st.get('disableUac', False)
            config.disable_smart_screen = st.get('disableSmartScreen', False)
            config.disable_system_restore = st.get('disableSystemRestore', False)
            config.disable_fast_startup = st.get('disableFastStartup', False)
            config.turn_off_system_sounds = st.get('turnOffSystemSounds', False)
            config.disable_app_suggestions = st.get('disableAppSuggestions', False)
            config.disable_widgets = st.get('disableWidgets', False)
            config.prevent_device_encryption = st.get('preventDeviceEncryption', False)
            config.classic_context_menu = st.get('classicContextMenu', False)
            config.disable_windows_update = st.get('disableWindowsUpdate', False)
            config.disable_pointer_precision = st.get('disablePointerPrecision', False)
            config.delete_windows_old = st.get('deleteWindowsOld', False)
            config.disable_core_isolation = st.get('disableCoreIsolation', False)
            config.show_end_task = st.get('showEndTask', False)
            config.vbox_guest_additions = st.get('vboxGuestAdditions', False)
            config.vmware_tools = st.get('vmwareTools', False)
            config.virt_io_guest_tools = st.get('virtIoGuestTools', False)
            config.parallels_tools = st.get('parallelsTools', False)
            config.left_taskbar = st.get('leftTaskbar', False)
            config.hide_task_view_button = st.get('hideTaskViewButton', False)
            config.show_all_tray_icons = st.get('showAllTrayIcons', False)
            config.hide_edge_fre = st.get('hideEdgeFre', False)
            config.disable_edge_startup_boost = st.get('disableEdgeStartupBoost', False)
            config.make_edge_uninstallable = st.get('makeEdgeUninstallable', False)
            config.delete_edge_desktop_icon = st.get('deleteEdgeDesktopIcon', False)
            config.launch_to_this_pc = st.get('launchToThisPC', False)
            config.disable_bing_results = st.get('disableBingResults', False)
    else:
        # 设置默认值（已经在 Configuration 类中定义）
        pass
    
    # 转换模块 11: 高级设置
    # 转换快速设置
    if 'expressSettings' in config_dict:
        express_settings_data = config_dict['expressSettings']
        # 如果 expressSettings 是字典，获取 mode 字段；如果是字符串，直接使用
        if isinstance(express_settings_data, dict):
            express_settings_str = express_settings_data.get('mode', 'disableAll')
        elif isinstance(express_settings_data, str):
            express_settings_str = express_settings_data
        else:
            logger.warning(f"expressSettings is not a dict or string, got {type(express_settings_data)}, using default")
            express_settings_str = 'disableAll'
        
        express_settings_map = {
            'interactive': ExpressSettingsMode.Interactive,
            'enableAll': ExpressSettingsMode.EnableAll,
            'disableAll': ExpressSettingsMode.DisableAll
        }
        config.express_settings = express_settings_map.get(express_settings_str, ExpressSettingsMode.DisableAll)
    else:
        config.express_settings = ExpressSettingsMode.DisableAll
    
    # 如果 expressSettings 是 disableAll，但 accountSettings.protectYourPC 是 "1"，则应该设置为 enableAll
    if config.express_settings == ExpressSettingsMode.DisableAll:
        if 'accountSettings' in config_dict:
            accounts = config_dict['accountSettings']
            if isinstance(accounts, dict):
                protect_your_pc = accounts.get('protectYourPC')
                if protect_your_pc == '1' or protect_your_pc == 1:
                    config.express_settings = ExpressSettingsMode.EnableAll
    
    # 转换预装软件设置
    if 'bloatware' in config_dict and generator:
        bloatware_data = config_dict['bloatware']
        # 确保 bloatware_data 是字典
        if not isinstance(bloatware_data, dict):
            logger.warning(f"bloatware is not a dict, got {type(bloatware_data)}, using default")
            config.bloatwares = []
        else:
            # 支持 'items' 和 'selected' 两种字段名（前端使用 'items'）
            bloatware_ids = bloatware_data.get('items', bloatware_data.get('selected', []))
            if not isinstance(bloatware_ids, list):
                bloatware_ids = []
            config.bloatwares = []
            for bloatware_id in bloatware_ids:
                if bloatware_id in generator.bloatwares:
                    config.bloatwares.append(generator.bloatwares[bloatware_id])
    else:
        config.bloatwares = []
    
    # 转换 WDAC 设置
    if 'wdac' in config_dict:
        wdac = config_dict['wdac']
        # 确保 wdac 是字典
        if not isinstance(wdac, dict):
            logger.warning(f"wdac is not a dict, got {type(wdac)}, using default")
            config.wdac_settings = SkipWdacSettings()
        else:
            mode = wdac.get('mode', 'skip')
            
            if mode == 'configure':
                # 支持前端字段名 enforcementMode 和 scriptEnforcement，也支持后端字段名 auditMode 和 scriptMode
                audit_mode_str = wdac.get('enforcementMode') or wdac.get('auditMode', 'enforcement')
                script_mode_str = wdac.get('scriptEnforcement') or wdac.get('scriptMode', 'restricted')
                
                # 映射 enforcementMode 值到 audit_mode
                audit_mode_map = {
                    'audit': WdacAuditModes.Auditing,
                    'auditing': WdacAuditModes.Auditing,  # 兼容旧值
                    'auditOnBootFailure': WdacAuditModes.AuditingOnBootFailure,
                    'auditingOnBootFailure': WdacAuditModes.AuditingOnBootFailure,  # 兼容旧值
                    'enforcement': WdacAuditModes.Enforcement
                }
                script_mode_map = {
                    'restricted': WdacScriptModes.Restricted,
                    'unrestricted': WdacScriptModes.Unrestricted
                }
                
                config.wdac_settings = ConfigureWdacSettings(
                    audit_mode=audit_mode_map.get(audit_mode_str, WdacAuditModes.Enforcement),
                    script_mode=script_mode_map.get(script_mode_str, WdacScriptModes.Restricted)
                )
            else:
                config.wdac_settings = SkipWdacSettings()
    else:
        config.wdac_settings = SkipWdacSettings()
    
    # 转换处理器架构（已在上面处理，这里确保有默认值）
    if 'processorArchitectures' not in config_dict:
        config.processor_architectures = {ProcessorArchitecture.amd64}
    
    # 转换模块 12: 自定义脚本（前端按阶段分组的格式）
    if 'scripts' in config_dict:
        scripts_data = config_dict['scripts']
        # 确保 scripts_data 是字典
        if not isinstance(scripts_data, dict):
            logger.warning(f"scripts is not a dict, got {type(scripts_data)}, using default")
            config.script_settings = ScriptSettings()
        else:
            scripts_list = []
            
            # 按阶段解析脚本
            phase_map = {
                'system': ScriptPhase.System,
                'firstLogon': ScriptPhase.FirstLogon,
                'userOnce': ScriptPhase.UserOnce,
                'defaultUser': ScriptPhase.DefaultUser
            }
            
            # 类型映射（支持 .cmd, .ps1 等格式，也支持 cmd, ps1 格式）
            type_map = {
                '.cmd': ScriptType.Cmd,
                'cmd': ScriptType.Cmd,
                '.ps1': ScriptType.Ps1,
                'ps1': ScriptType.Ps1,
                '.reg': ScriptType.Reg,
                'reg': ScriptType.Reg,
                '.vbs': ScriptType.Vbs,
                'vbs': ScriptType.Vbs,
                '.js': ScriptType.Js,
                'js': ScriptType.Js
            }
            
            # 首先尝试按阶段分组格式（前端格式）
            has_phase_groups = any(key in scripts_data for key in phase_map.keys())
            
            if has_phase_groups:
                # 按阶段解析脚本
                for phase_key, phase_enum in phase_map.items():
                    phase_scripts = scripts_data.get(phase_key, [])
                    if not isinstance(phase_scripts, list):
                        continue
                    
                    for item in phase_scripts:
                        # 确保 item 是字典
                        if not isinstance(item, dict):
                            logger.warning(f"scripts item is not a dict, got {type(item)}, skipping")
                            continue
                        
                        content = item.get('content', '')
                        type_str = item.get('type', '.cmd')
                        
                        # 移除前导点（如果存在）
                        if type_str.startswith('.'):
                            type_str = type_str[1:]
                        
                        script_type = type_map.get(type_str.lower(), ScriptType.Cmd)
                        
                        scripts_list.append(Script(
                            content=content,
                            phase=phase_enum,
                            type=script_type
                        ))
            else:
                # 兼容旧格式（scripts 数组，每个项有 phase 字段）
                scripts_array = scripts_data.get('scripts', [])
                if not isinstance(scripts_array, list):
                    scripts_array = []
                
                for script_data in scripts_array:
                    # 确保 script_data 是字典
                    if not isinstance(script_data, dict):
                        logger.warning(f"script_data is not a dict, got {type(script_data)}, skipping")
                        continue
                    
                    content = script_data.get('content', '')
                    phase_str = script_data.get('phase', 'system')
                    type_str = script_data.get('type', 'cmd')
                    
                    # 移除前导点（如果存在）
                    if type_str.startswith('.'):
                        type_str = type_str[1:]
                    
                    phase = phase_map.get(phase_str, ScriptPhase.System)
                    script_type = type_map.get(type_str.lower(), ScriptType.Cmd)
                    
                    scripts_list.append(Script(
                        content=content,
                        phase=phase,
                        type=script_type
                    ))
            
            config.script_settings = ScriptSettings(
                scripts=scripts_list,
                restart_explorer=scripts_data.get('restartExplorer', False)
            )
    else:
        config.script_settings = ScriptSettings()
    
    # 转换 Extensions 设置
    if 'extensions' in config_dict:
        extensions_data = config_dict['extensions']
        if isinstance(extensions_data, dict):
            config.extensions = extensions_data
        else:
            config.extensions = None
    else:
        config.extensions = None
    
    # 转换模块 13: XML 标记
    if 'xmlMarkup' in config_dict:
        xml_markup_data = config_dict['xmlMarkup']
        # 确保 xml_markup_data 是字典
        if not isinstance(xml_markup_data, dict):
            logger.warning(f"xmlMarkup is not a dict, got {type(xml_markup_data)}, using default")
            config.components = {}
        else:
            components_dict = {}
            components_list = xml_markup_data.get('components', [])
            if not isinstance(components_list, list):
                components_list = []
            
            for item in components_list:
                # 确保 item 是字典
                if not isinstance(item, dict):
                    logger.warning(f"xmlMarkup component item is not a dict, got {type(item)}, skipping")
                    continue
                
                component_name = item.get('component', '')
                pass_str = item.get('pass', 'specialize')
                xml_content = item.get('xml', '')
                
                # 转换 Pass
                pass_map = {
                    'offlineServicing': Pass.offlineServicing,
                    'windowsPE': Pass.windowsPE,
                    'generalize': Pass.generalize,
                    'specialize': Pass.specialize,
                    'auditSystem': Pass.auditSystem,
                    'auditUser': Pass.auditUser,
                    'oobeSystem': Pass.oobeSystem
                }
                pass_ = pass_map.get(pass_str, Pass.specialize)
                
                components_dict[(component_name, pass_)] = xml_content
            
            config.components = components_dict
    else:
        config.components = {}
    
    return config


def configuration_to_config_dict(config: Configuration) -> Dict[str, Any]:
    """将 Python Configuration 对象转换为前端配置字典"""
    config_dict: Dict[str, Any] = {}
    
    # 转换语言设置
    if config.language_settings:
        if isinstance(config.language_settings, InteractiveLanguageSettings):
            config_dict['languageSettings'] = {'mode': 'interactive'}
        elif isinstance(config.language_settings, UnattendedLanguageSettings):
            settings = config.language_settings
            config_dict['languageSettings'] = {
                'mode': 'unattended',
                'uiLanguage': settings.image_language.id,
                'systemLocale': settings.locale_and_keyboard.locale.id,
                'inputLocale': settings.locale_and_keyboard.keyboard.id,
                'geoLocation': settings.geo_location.id if settings.geo_location else None
            }
    
    # 转换时区设置
    if config.time_zone_settings:
        if isinstance(config.time_zone_settings, ImplicitTimeZoneSettings):
            config_dict['timeZone'] = {'mode': 'implicit'}
        elif isinstance(config.time_zone_settings, ExplicitTimeZoneSettings):
            config_dict['timeZone'] = {
                'mode': 'explicit',
                'timeZone': config.time_zone_settings.time_zone.id
            }
    
    # 转换处理器架构
    config_dict['processorArchitectures'] = [
        arch.value for arch in config.processor_architectures
    ]
    
    # 转换 Setup Settings（模块 2）
    config_dict['setupSettings'] = {
        'bypassRequirementsCheck': config.bypass_requirements_check,
        'bypassNetworkCheck': config.bypass_network_check,
        'useConfigurationSet': config.use_configuration_set,
        'hidePowerShellWindows': config.hide_power_shell_windows,
        'keepSensitiveFiles': config.keep_sensitive_files,
        'useNarrator': config.use_narrator
    }
    
    # 转换模块 4: Name and Account
    # 转换计算机名设置
    if config.computer_name_settings:
        if isinstance(config.computer_name_settings, RandomComputerNameSettings):
            config_dict['computerName'] = {'mode': 'random'}
        elif isinstance(config.computer_name_settings, CustomComputerNameSettings):
            config_dict['computerName'] = {
                'mode': 'custom',
                'name': config.computer_name_settings.computer_name
            }
        elif isinstance(config.computer_name_settings, ScriptComputerNameSettings):
            config_dict['computerName'] = {
                'mode': 'script',
                'script': config.computer_name_settings.script
            }
        else:
            config_dict['computerName'] = {'mode': 'random'}
    else:
        config_dict['computerName'] = {'mode': 'random'}
    
    # 转换账户设置
    if config.account_settings:
        if isinstance(config.account_settings, UnattendedAccountSettings):
            accounts_list = []
            for account in config.account_settings.accounts:
                accounts_list.append({
                    'name': account.name,
                    'displayName': account.display_name,
                    'group': account.group,
                    'password': account.password
                })
            
            auto_logon_mode = 'none'
            auto_logon_password = ''
            if isinstance(config.account_settings.auto_logon_settings, BuiltinAutoLogonSettings):
                auto_logon_mode = 'builtin'
                auto_logon_password = config.account_settings.auto_logon_settings.password
            elif isinstance(config.account_settings.auto_logon_settings, OwnAutoLogonSettings):
                auto_logon_mode = 'own'
            
            config_dict['accountSettings'] = {
                'mode': 'unattended',
                'accounts': accounts_list,
                'autoLogonMode': auto_logon_mode,
                'autoLogonPassword': auto_logon_password,
                'obscurePasswords': config.account_settings.obscure_passwords
            }
        elif isinstance(config.account_settings, InteractiveLocalAccountSettings):
            config_dict['accountSettings'] = {'mode': 'interactive-local'}
        else:
            config_dict['accountSettings'] = {'mode': 'interactive-microsoft'}
    else:
        config_dict['accountSettings'] = {'mode': 'interactive-microsoft'}
    
    # 转换密码过期设置
    if config.password_expiration_settings:
        if isinstance(config.password_expiration_settings, UnlimitedPasswordExpirationSettings):
            config_dict['passwordExpiration'] = {'mode': 'unlimited'}
        elif isinstance(config.password_expiration_settings, CustomPasswordExpirationSettings):
            config_dict['passwordExpiration'] = {
                'mode': 'custom',
                'maxAge': config.password_expiration_settings.max_age
            }
        else:
            config_dict['passwordExpiration'] = {'mode': 'default'}
    else:
        config_dict['passwordExpiration'] = {'mode': 'default'}
    
    # 转换账户锁定设置
    if config.lockout_settings:
        if isinstance(config.lockout_settings, DisableLockoutSettings):
            config_dict['lockoutSettings'] = {'mode': 'disabled'}
        elif isinstance(config.lockout_settings, CustomLockoutSettings):
            config_dict['lockoutSettings'] = {
                'mode': 'custom',
                'lockoutThreshold': config.lockout_settings.lockout_threshold,
                'lockoutDuration': config.lockout_settings.lockout_duration,
                'lockoutWindow': config.lockout_settings.lockout_window
            }
        else:
            config_dict['lockoutSettings'] = {'mode': 'default'}
    else:
        config_dict['lockoutSettings'] = {'mode': 'default'}
    
    # 转换模块 5: Partitioning and formatting
    # 转换分区设置
    if config.partition_settings:
        if isinstance(config.partition_settings, InteractivePartitionSettings):
            config_dict['partitioning'] = {'mode': 'interactive'}
        elif isinstance(config.partition_settings, UnattendedPartitionSettings):
            # 转换 recovery_mode 枚举值到前端值
            recovery_mode_map = {
                RecoveryMode.None_: 'none',
                RecoveryMode.Folder: 'folder',
                RecoveryMode.Partition: 'partition'
            }
            recovery_mode_str = recovery_mode_map.get(config.partition_settings.recovery_mode, 'partition')
            
            config_dict['partitioning'] = {
                'mode': 'automatic',
                'layout': config.partition_settings.partition_layout.value,
                'recoveryMode': recovery_mode_str,
                'espSize': config.partition_settings.esp_size,
                'recoverySize': config.partition_settings.recovery_size
            }
        elif isinstance(config.partition_settings, CustomPartitionSettings):
            install_to_mode = 'available'
            install_to_disk = None
            install_to_partition = None
            if isinstance(config.partition_settings.install_to, CustomInstallToSettings):
                install_to_mode = 'custom'
                install_to_disk = config.partition_settings.install_to.install_to_disk
                install_to_partition = config.partition_settings.install_to.install_to_partition
            
            config_dict['partitioning'] = {
                'mode': 'custom',
                'diskpartScript': config.partition_settings.script,
                'installToMode': install_to_mode,
                'installToDisk': install_to_disk,
                'installToPartition': install_to_partition
            }
        else:
            config_dict['partitioning'] = {'mode': 'interactive'}
    else:
        config_dict['partitioning'] = {'mode': 'interactive'}
    
    # 转换磁盘断言设置
    if config.disk_assertion_settings:
        if isinstance(config.disk_assertion_settings, SkipDiskAssertionSettings):
            if 'partitioning' in config_dict:
                config_dict['partitioning']['diskAssertionMode'] = 'skip'
        elif isinstance(config.disk_assertion_settings, ScriptDiskAssertionsSettings):
            if 'partitioning' in config_dict:
                config_dict['partitioning']['diskAssertionMode'] = 'script'
                config_dict['partitioning']['diskAssertionScript'] = config.disk_assertion_settings.script
    else:
        if 'partitioning' in config_dict:
            config_dict['partitioning']['diskAssertionMode'] = 'skip'
    
    # 转换 PE 设置
    if config.pe_settings:
        if isinstance(config.pe_settings, GeneratePESettings):
            config_dict['peSettings'] = {
                'mode': 'generated',
                'disable8Dot3Names': config.pe_settings.disable_8_dot3_names,
                'pauseBeforeFormatting': config.pe_settings.pause_before_formatting,
                'pauseBeforeReboot': config.pe_settings.pause_before_reboot
            }
        elif isinstance(config.pe_settings, ScriptPESettings):
            config_dict['peSettings'] = {
                'mode': 'script',
                'cmdScript': config.pe_settings.script
            }
        else:
            config_dict['peSettings'] = {'mode': 'default'}
    else:
        config_dict['peSettings'] = {'mode': 'default'}
    
    # 转换模块 6: Windows Edition and Source
    # 转换版本设置
    if config.edition_settings:
        if isinstance(config.edition_settings, InteractiveEditionSettings):
            config_dict['windowsEdition'] = {'mode': 'interactive'}
        elif isinstance(config.edition_settings, FirmwareEditionSettings):
            config_dict['windowsEdition'] = {'mode': 'firmware'}
        elif isinstance(config.edition_settings, UnattendedEditionSettings):
            config_dict['windowsEdition'] = {
                'mode': 'name',
                'editionName': config.edition_settings.edition.id
            }
        elif isinstance(config.edition_settings, CustomEditionSettings):
            config_dict['windowsEdition'] = {
                'mode': 'custom',
                'productKey': config.edition_settings.product_key
            }
        else:
            config_dict['windowsEdition'] = {'mode': 'interactive'}
    else:
        config_dict['windowsEdition'] = {'mode': 'interactive'}
    
    # 转换安装源设置
    if config.install_from_settings:
        if isinstance(config.install_from_settings, AutomaticInstallFromSettings):
            config_dict['sourceImage'] = {'mode': 'automatic'}
        elif isinstance(config.install_from_settings, IndexInstallFromSettings):
            config_dict['sourceImage'] = {
                'mode': 'index',
                'imageIndex': config.install_from_settings.index
            }
        elif isinstance(config.install_from_settings, NameInstallFromSettings):
            config_dict['sourceImage'] = {
                'mode': 'name',
                'imageName': config.install_from_settings.name
            }
        else:
            config_dict['sourceImage'] = {'mode': 'automatic'}
    else:
        config_dict['sourceImage'] = {'mode': 'automatic'}
    
    # 转换 Compact OS 模式
    if config.compact_os_mode == CompactOsModes.Always:
        config_dict['compactOS'] = 'enabled'
    elif config.compact_os_mode == CompactOsModes.Never:
        config_dict['compactOS'] = 'disabled'
    else:
        config_dict['compactOS'] = 'default'
    
    # 转换模块 9: 辅助功能设置
    # 转换 Lock Keys 设置
    if isinstance(config.lock_key_settings, ConfigureLockKeySettings):
        config_dict['lockKeys'] = {
            'mode': 'configure',
            'capsLockInitial': 'on' if config.lock_key_settings.caps_lock.initial == LockKeyInitial.On else 'off',
            'capsLockBehavior': 'ignore' if config.lock_key_settings.caps_lock.behavior == LockKeyBehavior.Ignore else 'toggle',
            'numLockInitial': 'on' if config.lock_key_settings.num_lock.initial == LockKeyInitial.On else 'off',
            'numLockBehavior': 'ignore' if config.lock_key_settings.num_lock.behavior == LockKeyBehavior.Ignore else 'toggle',
            'scrollLockInitial': 'on' if config.lock_key_settings.scroll_lock.initial == LockKeyInitial.On else 'off',
            'scrollLockBehavior': 'ignore' if config.lock_key_settings.scroll_lock.behavior == LockKeyBehavior.Ignore else 'toggle'
        }
    else:
        config_dict['lockKeys'] = {'mode': 'skip'}
    
    # 转换 Sticky Keys 设置
    if isinstance(config.sticky_keys_settings, DisabledStickyKeysSettings):
        config_dict['stickyKeys'] = {'mode': 'disabled'}
    elif isinstance(config.sticky_keys_settings, CustomStickyKeysSettings):
        flags = config.sticky_keys_settings.flags
        config_dict['stickyKeys'] = {
            'mode': 'custom',
            'stickyKeysHotKeyActive': StickyKeys.HotKeyActive in flags,
            'stickyKeysHotKeySound': StickyKeys.HotKeySound in flags,
            'stickyKeysIndicator': StickyKeys.Indicator in flags,
            'stickyKeysAudibleFeedback': StickyKeys.AudibleFeedback in flags,
            'stickyKeysTriState': StickyKeys.TriState in flags,
            'stickyKeysTwoKeysOff': StickyKeys.TwoKeysOff in flags
        }
    else:
        config_dict['stickyKeys'] = {'mode': 'default'}
    
    # 转换模块 11: 高级设置
    # 转换快速设置
    express_settings_map = {
        ExpressSettingsMode.Interactive: 'interactive',
        ExpressSettingsMode.EnableAll: 'enableAll',
        ExpressSettingsMode.DisableAll: 'disableAll'
    }
    config_dict['expressSettings'] = express_settings_map.get(config.express_settings, 'disableAll')
    
    # 转换预装软件设置（前端使用 'items' 字段）
    config_dict['bloatware'] = {
        'items': [bw.id for bw in config.bloatwares]
    }
    
    # 转换 WDAC 设置
    if isinstance(config.wdac_settings, ConfigureWdacSettings):
        audit_mode_map = {
            WdacAuditModes.Auditing: 'auditing',
            WdacAuditModes.AuditingOnBootFailure: 'auditingOnBootFailure',
            WdacAuditModes.Enforcement: 'enforcement'
        }
        script_mode_map = {
            WdacScriptModes.Restricted: 'restricted',
            WdacScriptModes.Unrestricted: 'unrestricted'
        }
        # 映射 audit_mode 到 enforcementMode（前端字段名）
        audit_to_enforcement_map = {
            WdacAuditModes.Auditing: 'audit',
            WdacAuditModes.AuditingOnBootFailure: 'auditOnBootFailure',
            WdacAuditModes.Enforcement: 'enforcement'
        }
        script_mode_map = {
            WdacScriptModes.Restricted: 'restricted',
            WdacScriptModes.Unrestricted: 'unrestricted'
        }
        config_dict['wdac'] = {
            'mode': 'configure',
            'enforcementMode': audit_to_enforcement_map.get(config.wdac_settings.audit_mode, 'enforcement'),
            'scriptEnforcement': script_mode_map.get(config.wdac_settings.script_mode, 'restricted')
        }
    else:
        config_dict['wdac'] = {'mode': 'skip'}
    
    # 转换模块 12: 自定义脚本（前端期望按阶段分组的格式）
    if config.script_settings:
        # 按阶段分组脚本
        system_scripts = []
        default_user_scripts = []
        first_logon_scripts = []
        user_once_scripts = []
        
        for script in config.script_settings.scripts:
            import uuid
            script_item = {
                'id': str(uuid.uuid4()),
                'type': f".{script.type.value.lower()}",  # 前端期望 .cmd, .ps1 等格式
                'content': script.content
            }
            
            if script.phase == ScriptPhase.System:
                system_scripts.append(script_item)
            elif script.phase == ScriptPhase.DefaultUser:
                default_user_scripts.append(script_item)
            elif script.phase == ScriptPhase.FirstLogon:
                first_logon_scripts.append(script_item)
            elif script.phase == ScriptPhase.UserOnce:
                user_once_scripts.append(script_item)
        
        config_dict['scripts'] = {
            'system': system_scripts,
            'defaultUser': default_user_scripts,
            'firstLogon': first_logon_scripts,
            'userOnce': user_once_scripts,
            'restartExplorer': config.script_settings.restart_explorer
        }
    else:
        config_dict['scripts'] = {
            'system': [],
            'defaultUser': [],
            'firstLogon': [],
            'userOnce': [],
            'restartExplorer': False
        }
    
    # 转换模块 13: XML 标记
    if config.components:
        components_list = []
        for (component_name, pass_), xml_content in config.components.items():
            pass_map = {
                Pass.offlineServicing: 'offlineServicing',
                Pass.windowsPE: 'windowsPE',
                Pass.generalize: 'generalize',
                Pass.specialize: 'specialize',
                Pass.auditSystem: 'auditSystem',
                Pass.auditUser: 'auditUser',
                Pass.oobeSystem: 'oobeSystem'
            }
            components_list.append({
                'component': component_name,
                'pass': pass_map.get(pass_, 'specialize'),
                'xml': xml_content
            })
        
        config_dict['xmlMarkup'] = {
            'components': components_list
        }
    else:
        config_dict['xmlMarkup'] = {
            'components': []
        }
    
    return config_dict

