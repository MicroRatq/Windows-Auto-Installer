/**
 * 镜像配置工作区
 * 实现 autounattend.xml 配置功能
 */

import {
  createRadioContainer,
  setupRadioContainer,
  createComboCard,
  setupComboCard,
  createComboContainer,
  setupComboContainer,
  createTextCard, // 通过 createRadioContainer 的嵌套功能动态调用
  setupTextCard,
  getTextCardValue,
  setTextCardValue
} from './workspace'
import { t } from './i18n'

// ========================================
// 配置数据结构定义
// ========================================

// 区域和语言设置
interface LanguageSettings {
  mode: 'interactive' | 'unattended'
  uiLanguage?: string // Windows显示语言
  locale?: string // 用户区域
  keyboard?: string // 键盘布局
  locale2?: string // 第二语言
  keyboard2?: string // 第二键盘布局
  locale3?: string // 第三语言
  keyboard3?: string // 第三键盘布局
  geoLocation?: string // 地理位置
}

// 处理器架构
type ProcessorArchitecture = 'x86' | 'amd64' | 'arm64'

// 安装设置
interface SetupSettings {
  bypassRequirementsCheck: boolean
  bypassNetworkCheck: boolean
  useConfigurationSet: boolean
  hidePowerShellWindows: boolean
  keepSensitiveFiles: boolean
  useNarrator: boolean
}

// 计算机名设置
interface ComputerNameSettings {
  mode: 'random' | 'custom' | 'script'
  name?: string
  script?: string
}

// 紧凑操作系统
type CompactOSMode = 'default' | 'enabled' | 'disabled'

// 时区设置
interface TimeZoneSettings {
  mode: 'implicit' | 'explicit'
  timeZone?: string
}

// 分区和格式化设置
interface PartitionSettings {
  mode: 'interactive' | 'automatic' | 'custom'
  layout?: 'MBR' | 'GPT'
  espSize?: number // ESP分区大小 (MB)，默认300
  recoveryMode?: 'partition' | 'folder' | 'none'
  recoverySize?: number // Recovery分区大小 (MB)，默认1000
  diskpartScript?: string
  installToMode?: 'available' | 'custom' // 安装到哪个分区
  installToDisk?: number // 安装磁盘（0-based）
  installToPartition?: number // 安装分区（1-based）
  diskAssertionMode?: 'skip' | 'script' // 磁盘断言模式
  diskAssertionScript?: string // 磁盘断言脚本
  // 旧字段保留用于兼容
  installDisk?: number
  installPartition?: number
}

// Windows版本设置
interface EditionSettings {
  mode: 'interactive' | 'firmware' | 'key' | 'index' | 'name' | 'generic'
  productKey?: string
  editionIndex?: number
  editionName?: string
}

// 源镜像设置
interface SourceImageSettings {
  mode?: 'automatic' | 'index' | 'name'
  imageIndex?: number
  imageName?: string
  source?: string // 保留用于兼容
}

// Windows PE操作设置
interface PESettings {
  mode: 'default' | 'generated' | 'script' | 'custom' // 'custom'保留用于兼容
  cmdScript?: string
  disable8Dot3Names?: boolean // Generated模式下的选项
  pauseBeforeFormatting?: boolean
  pauseBeforeReboot?: boolean
}

// 用户账户设置
interface Account {
  name: string
  displayName: string
  password: string
  group: 'Administrators' | 'Users'
}

interface AccountSettings {
  mode: 'interactive-microsoft' | 'interactive-local' | 'unattended'
  accounts?: Account[]
  autoLogonMode?: 'none' | 'builtin' | 'own'
  autoLogonPassword?: string
  obscurePasswords: boolean
}

// 密码过期设置
interface PasswordExpirationSettings {
  mode: 'default' | 'unlimited' | 'custom'
  maxAge?: number
}

// 账户锁定策略
interface LockoutSettings {
  mode: 'default' | 'disabled' | 'custom'
  lockoutThreshold?: number
  lockoutDuration?: number
  resetLockoutCounter?: number
}

// 文件资源管理器调整
interface FileExplorerTweaks {
  showFileExtensions: boolean
  showAllTrayIcons: boolean
  hideFiles: 'hidden' | 'show'
  hideEdgeFre: boolean
  disableEdgeStartupBoost: boolean
  makeEdgeUninstallable: boolean
  deleteEdgeDesktopIcon: boolean
  launchToThisPC: boolean
  disableBingResults: boolean
}

// 开始菜单和任务栏设置
interface StartMenuTaskbarSettings {
  leftTaskbar: boolean
  hideTaskViewButton: boolean
  taskbarSearch: 'hide' | 'icon' | 'box' | 'label'
  startPins?: string[]
  startTiles?: any
  taskbarIcons?: any
}

// 系统调整
interface SystemTweaks {
  enableLongPaths: boolean
  enableRemoteDesktop: boolean
  hardenSystemDriveAcl: boolean
  deleteJunctions: boolean
  allowPowerShellScripts: boolean
  disableLastAccess: boolean
  preventAutomaticReboot: boolean
  disableDefender: boolean
  disableSac: boolean
  disableUac: boolean
  disableSmartScreen: boolean
  disableSystemRestore: boolean
  disableFastStartup: boolean
  turnOffSystemSounds: boolean
  disableAppSuggestions: boolean
  disableWidgets: boolean
  preventDeviceEncryption: boolean
  classicContextMenu: boolean
  disableWindowsUpdate: boolean
  disablePointerPrecision: boolean
  deleteWindowsOld: boolean
  disableCoreIsolation: boolean
  showEndTask: boolean
}

// 视觉效果
interface VisualEffects {
  effects?: any
}

// 桌面图标设置
interface DesktopIconSettings {
  mode: 'default' | 'custom'
  icons?: any
}

// 开始菜单文件夹设置
interface StartFolderSettings {
  folders?: string[]
}

// 虚拟机支持
interface VirtualMachineSupport {
  vBoxGuestAdditions: boolean
  vmwareTools: boolean
  virtIoGuestTools: boolean
  parallelsTools: boolean
}

// WiFi设置
interface WifiSettings {
  mode?: 'skip' | 'interactive' | 'unattended' | 'fromProfile' | 'profile' // 'profile'保留用于兼容
  profileXml?: string
  ssid?: string
  password?: string
  authentication?: 'Open' | 'WPA2PSK' | 'WPA3SAE'
  nonBroadcast?: boolean
}

// 快速设置
type ExpressSettingsMode = 'interactive' | 'enableAll' | 'disableAll'

// 锁定键设置
interface LockKeySettings {
  mode: 'skip' | 'configure'
  keys?: Array<{
    key: string
    initialState: boolean
    whenPressed: string
  }>
}

// 粘滞键设置
interface StickyKeysSettings {
  mode: 'default' | 'disabled' | 'custom'
  enabled?: boolean
}

// 个性化设置
interface PersonalizationSettings {
  wallpaperMode: 'default' | 'solid' | 'script'
  wallpaperColor?: string
  wallpaperScript?: string
  lockScreenMode: 'default' | 'script'
  lockScreenScript?: string
  colorMode: 'default' | 'custom'
  accentColor?: string
}

// 预装软件移除
interface BloatwareSettings {
  items: string[]
}

// 自定义脚本
interface ScriptSettings {
  system: Array<{ type: string; content: string }>
  defaultUser: Array<{ type: string; content: string }>
  firstLogon: Array<{ type: string; content: string }>
  userOnce: Array<{ type: string; content: string }>
  restartExplorer: boolean
}

// Windows Defender应用程序控制
interface WdacSettings {
  mode: 'skip' | 'configure'
  enforcementMode?: 'audit' | 'auditOnBootFailure' | 'enforcement'
  scriptEnforcement?: 'restricted' | 'unrestricted'
}

// XML标记
interface XmlMarkupSettings {
  components: Array<{
    component: string
    pass: string
    markup: string
  }>
}

// 完整配置对象
interface UnattendConfig {
  languageSettings: LanguageSettings
  processorArchitectures: ProcessorArchitecture[]
  setupSettings: SetupSettings
  computerName: ComputerNameSettings
  compactOS: CompactOSMode
  timeZone: TimeZoneSettings
  partitioning: PartitionSettings
  windowsEdition: EditionSettings
  sourceImage: SourceImageSettings
  peSettings: PESettings
  accountSettings: AccountSettings
  passwordExpiration: PasswordExpirationSettings
  lockoutSettings: LockoutSettings
  fileExplorerTweaks: FileExplorerTweaks
  startMenuTaskbar: StartMenuTaskbarSettings
  systemTweaks: SystemTweaks
  visualEffects: VisualEffects
  desktopIcons: DesktopIconSettings
  startFolders: StartFolderSettings
  vmSupport: VirtualMachineSupport
  wifi: WifiSettings
  expressSettings: ExpressSettingsMode
  lockKeys: LockKeySettings
  stickyKeys: StickyKeysSettings
  personalization: PersonalizationSettings
  bloatware: BloatwareSettings
  scripts: ScriptSettings
  wdac: WdacSettings
  xmlMarkup: XmlMarkupSettings
}

// ========================================
// 精简硬编码预设数据
// ========================================

// TODO: 后续从后端获取完整数据
const PRESET_DATA = {
  // 常用语言列表（精简版）
  languages: [
    { id: 'en-US', name: 'English (United States)' },
    { id: 'zh-CN', name: 'Chinese Simplified' },
    { id: 'zh-TW', name: 'Chinese Traditional' },
    { id: 'ja-JP', name: 'Japanese' },
    { id: 'ko-KR', name: 'Korean' },
    { id: 'de-DE', name: 'German' },
    { id: 'fr-FR', name: 'French' },
    { id: 'es-ES', name: 'Spanish' },
    { id: 'ru-RU', name: 'Russian' },
    { id: 'pt-BR', name: 'Brazilian Portuguese' }
  ],

  // 常用用户区域列表（精简版）
  locales: [
    { id: 'en-US', name: 'English (United States)' },
    { id: 'zh-CN', name: 'Chinese (Simplified, China)' },
    { id: 'zh-TW', name: 'Chinese (Traditional, Taiwan)' },
    { id: 'ja-JP', name: 'Japanese (Japan)' },
    { id: 'ko-KR', name: 'Korean (Korea)' },
    { id: 'de-DE', name: 'German (Germany)' },
    { id: 'fr-FR', name: 'French (France)' },
    { id: 'es-ES', name: 'Spanish (Spain)' },
    { id: 'ru-RU', name: 'Russian (Russia)' },
    { id: 'pt-BR', name: 'Portuguese (Brazil)' }
  ],

  // 常用键盘布局（精简版）
  keyboards: [
    { id: '00000409', name: 'US' },
    { id: '00000804', name: 'Chinese Simplified' },
    { id: '00000404', name: 'Chinese Traditional' },
    { id: '00000411', name: 'Japanese' },
    { id: '00000412', name: 'Korean' },
    { id: '00000407', name: 'German' },
    { id: '0000040c', name: 'French' },
    { id: '0000040a', name: 'Spanish' },
    { id: '00000419', name: 'Russian' },
    { id: '00000416', name: 'Portuguese (Brazil)' }
  ],

  // 常用时区（精简版）
  timeZones: [
    { id: 'UTC', name: '(UTC) Coordinated Universal Time' },
    { id: 'Pacific Standard Time', name: '(UTC-08:00) Pacific Time (US & Canada)' },
    { id: 'Central Standard Time', name: '(UTC-06:00) Central Time (US & Canada)' },
    { id: 'Eastern Standard Time', name: '(UTC-05:00) Eastern Time (US & Canada)' },
    { id: 'GMT Standard Time', name: '(UTC+00:00) Dublin, Edinburgh, Lisbon, London' },
    { id: 'W. Europe Standard Time', name: '(UTC+01:00) Amsterdam, Berlin, Bern, Rome, Stockholm, Vienna' },
    { id: 'China Standard Time', name: '(UTC+08:00) Beijing, Chongqing, Hong Kong, Urumqi' },
    { id: 'Tokyo Standard Time', name: '(UTC+09:00) Osaka, Sapporo, Tokyo' },
    { id: 'Korea Standard Time', name: '(UTC+09:00) Seoul' },
    { id: 'AUS Eastern Standard Time', name: '(UTC+10:00) Canberra, Melbourne, Sydney' }
  ],

  // 常用Windows版本（精简版）
  windowsEditions: [
    { id: 'Windows 10 Home', name: 'Windows 10 Home', key: 'TX9XD-98N7V-6WMQ6-BX7FG-H8Q99' },
    { id: 'Windows 10 Pro', name: 'Windows 10 Pro', key: 'W269N-WFGWX-YVC9B-4J6C9-T83GX' },
    { id: 'Windows 11 Home', name: 'Windows 11 Home', key: 'TX9XD-98N7V-6WMQ6-BX7FG-H8Q99' },
    { id: 'Windows 11 Pro', name: 'Windows 11 Pro', key: 'W269N-WFGWX-YVC9B-4J6C9-T83GX' },
    { id: 'Windows 11 Enterprise', name: 'Windows 11 Enterprise', key: 'NPPR9-FWDCX-D2C8J-H872K-2YT43' }
  ],

  // 常用预装软件列表（精简版）
  bloatwareItems: [
    '3D Viewer',
    'Calculator',
    'Mail and Calendar',
    'News',
    'OneNote',
    'Paint',
    'Skype',
    'Solitaire Collection',
    'Teams',
    'Xbox Apps'
  ]
}

// ========================================
// 默认配置
// ========================================

function createDefaultConfig(): UnattendConfig {
  return {
    languageSettings: {
      mode: 'interactive'
    },
    processorArchitectures: ['amd64'],
    setupSettings: {
      bypassRequirementsCheck: false,
      bypassNetworkCheck: false,
      useConfigurationSet: false,
      hidePowerShellWindows: false,
      keepSensitiveFiles: false,
      useNarrator: false
    },
    computerName: {
      mode: 'random'
    },
    compactOS: 'default',
    timeZone: {
      mode: 'implicit'
    },
    partitioning: {
      mode: 'interactive'
    },
    windowsEdition: {
      mode: 'interactive'
    },
    sourceImage: {
      mode: 'automatic'
    },
    peSettings: {
      mode: 'default'
    },
    accountSettings: {
      mode: 'interactive-microsoft',
      obscurePasswords: true
    },
    passwordExpiration: {
      mode: 'default'
    },
    lockoutSettings: {
      mode: 'default'
    },
    fileExplorerTweaks: {
      showFileExtensions: false,
      showAllTrayIcons: false,
      hideFiles: 'hidden',
      hideEdgeFre: false,
      disableEdgeStartupBoost: false,
      makeEdgeUninstallable: false,
      deleteEdgeDesktopIcon: false,
      launchToThisPC: false,
      disableBingResults: false
    },
    startMenuTaskbar: {
      leftTaskbar: false,
      hideTaskViewButton: false,
      taskbarSearch: 'box'
    },
    systemTweaks: {
      enableLongPaths: false,
      enableRemoteDesktop: false,
      hardenSystemDriveAcl: false,
      deleteJunctions: false,
      allowPowerShellScripts: false,
      disableLastAccess: false,
      preventAutomaticReboot: false,
      disableDefender: false,
      disableSac: false,
      disableUac: false,
      disableSmartScreen: false,
      disableSystemRestore: false,
      disableFastStartup: false,
      turnOffSystemSounds: false,
      disableAppSuggestions: false,
      disableWidgets: false,
      preventDeviceEncryption: false,
      classicContextMenu: false,
      disableWindowsUpdate: false,
      disablePointerPrecision: false,
      deleteWindowsOld: false,
      disableCoreIsolation: false,
      showEndTask: false
    },
    visualEffects: {},
    desktopIcons: {
      mode: 'default'
    },
    startFolders: {},
    vmSupport: {
      vBoxGuestAdditions: false,
      vmwareTools: false,
      virtIoGuestTools: false,
      parallelsTools: false
    },
    wifi: {
      mode: 'skip'
    },
    expressSettings: 'disableAll',
    lockKeys: {
      mode: 'skip'
    },
    stickyKeys: {
      mode: 'default'
    },
    personalization: {
      wallpaperMode: 'default',
      lockScreenMode: 'default',
      colorMode: 'default'
    },
    bloatware: {
      items: []
    },
    scripts: {
      system: [],
      defaultUser: [],
      firstLogon: [],
      userOnce: [],
      restartExplorer: false
    },
    wdac: {
      mode: 'skip'
    },
    xmlMarkup: {
      components: []
    }
  }
}

// ========================================
// 配置状态管理
// ========================================

class UnattendConfigManager {
  private config: UnattendConfig
  private panel: HTMLElement | null = null

  constructor() {
    this.config = createDefaultConfig()
  }

  // 获取配置
  getConfig(): UnattendConfig {
    return { ...this.config }
  }

  // 更新配置
  updateConfig(updates: Partial<UnattendConfig>) {
    this.config = { ...this.config, ...updates }
  }

  // 更新特定模块配置
  updateModule<K extends keyof UnattendConfig>(
    module: K,
    updates: Partial<UnattendConfig[K]>
  ) {
    const current = this.config[module]
    if (current && typeof current === 'object' && !Array.isArray(current)) {
      this.config[module] = { ...current, ...updates } as UnattendConfig[K]
    } else {
      this.config[module] = updates as UnattendConfig[K]
    }
  }

  // 获取预设数据
  getPresetData() {
    return PRESET_DATA
  }

  // 导入配置（从XML解析，TODO: 后端实现）
  async importFromXml(xmlContent: string): Promise<void> {
    // TODO: 调用后端解析XML并更新配置
    console.log('Import from XML (TODO: implement backend)', xmlContent)
  }

  // 导出配置（生成XML，TODO: 后端实现）
  async exportToXml(): Promise<string> {
    // TODO: 调用后端生成XML
    console.log('Export to XML (TODO: implement backend)', this.config)
    return ''
  }

  // 初始化UI
  init(panelId: string) {
    this.panel = document.getElementById(panelId)
    if (!this.panel) {
      console.error(`Panel ${panelId} not found`)
      return
    }
    // 不清空panel，因为HTML中已经有框架结构
    this.renderAllModules()
    this.setupEventListeners()
  }

  // 渲染UI（已废弃，直接调用renderAllModules）
  // @ts-ignore - 保留以备将来使用
  private render() {
    if (!this.panel) return
    this.renderAllModules()
    this.setupEventListeners()
  }

  // 辅助函数：获取或创建section内容容器
  private getSectionContent(sectionId: string): HTMLElement | null {
    const section = document.getElementById(sectionId)
    if (!section) return null

    let contentDiv = section.querySelector('.section-content') as HTMLElement
    if (!contentDiv) {
      contentDiv = document.createElement('div')
      contentDiv.className = 'section-content'
      // 插入到section-title之后
      const title = section.querySelector('.section-title')
      if (title && title.nextSibling) {
        section.insertBefore(contentDiv, title.nextSibling)
      } else {
        section.appendChild(contentDiv)
      }
    }
    return contentDiv
  }

  // 渲染所有模块
  public renderAllModules() {
    if (!this.panel) return

    // 1. Region, Language and Time Zone (合并模块1和6)
    this.renderRegionLanguageTimeZone()

    // 2. Setup settings
    this.renderSetupSettings()

    // 4. Name and Account (合并模块4、11、12、13)
    this.renderNameAndAccount()

    // 5. Partitioning and formatting
    this.renderPartitioning()

    // 6. Windows Edition and Source (合并模块8和9)
    this.renderWindowsEditionAndSource()

    // 7. UI and Personalization (合并模块14、15、16、17、18、25)
    this.renderFileExplorer()
    this.renderStartTaskbar()
    this.renderVisualEffects()
    this.renderDesktopIcons()
    this.renderFoldersStart()
    this.renderPersonalization()

    // 8. WLAN / Wi-Fi setup
    this.renderWifi()

    // 9. Accessibility Settings (合并模块23、24)
    this.renderLockKeys()
    this.renderStickyKeys()

    // 10. System Optimization (合并模块16、22、26)
    this.renderSystemOptimization()

    // 11. Advanced Settings (合并模块5、10、20、28)
    this.renderAdvancedSettings()

    // 12. Run custom scripts
    this.renderCustomScripts()

    // 13. XML markup for more components
    this.renderXmlMarkup()
  }

  // 设置事件监听器
  private setupEventListeners() {
    // 导入/导出按钮
    const importBtn = document.getElementById('iso-config-import-btn')
    const exportBtn = document.getElementById('iso-config-export-btn')

    if (importBtn) {
      importBtn.addEventListener('click', () => this.handleImport())
    }
    if (exportBtn) {
      exportBtn.addEventListener('click', () => this.handleExport())
    }

    // 使用事件委托处理可展开card的展开/折叠
    // 这样动态生成的卡片也能正常工作
    if (this.panel) {
      this.panel.addEventListener('click', (e: Event) => {
        const target = e.target as HTMLElement
        // 查找是否点击了card-expandable-header或其子元素
        const header = target.closest('.card-expandable-header')
        if (header) {
          const card = header.closest('.card-expandable')
          if (card) {
            card.classList.toggle('expanded')
            // 重新初始化图标以确保展开/折叠图标正确显示
            if (window.lucide) {
              window.lucide.createIcons()
            }
          }
        }
      })
    }
  }

  // 处理导入
  private async handleImport() {
    // TODO: 实现导入功能（调用后端）
    if (window.electronAPI?.showOpenDialog) {
      const result = await window.electronAPI.showOpenDialog({
        filters: [{ name: 'XML Files', extensions: ['xml'] }],
        properties: ['openFile']
      })
      if (!result.canceled && result.filePaths?.[0]) {
        // TODO: 读取文件并调用后端解析
        console.log('Import file:', result.filePaths[0])
      }
    }
  }

  // 处理导出
  private async handleExport() {
    // TODO: 实现导出功能（调用后端生成XML）
    const xml = await this.exportToXml()
    console.log('Export XML:', xml)
  }

  // 渲染模块1: Region, Language and Time Zone
  private renderRegionLanguageTimeZone() {
    const contentDiv = this.getSectionContent('config-region-language')
    if (!contentDiv) return

    const preset = this.getPresetData()
    const lang = this.config.languageSettings
    const tz = this.config.timeZone

    // 语言模式 Switch ComboCard
    const languageModeCardHtml = createComboCard({
      id: 'config-language-mode-card',
      title: t('isoConfig.regionLanguage.selectLanguageInSetup'),
      description: t('isoConfig.regionLanguage.selectLanguageInSetupDesc'),
      icon: 'globe',
      controlType: 'switch',
      value: lang.mode === 'interactive'
    })

    // Windows display language ComboCard
    const uiLanguageCardHtml = lang.mode === 'unattended'
      ? createComboCard({
        id: 'config-ui-language-card',
        title: t('isoConfig.regionLanguage.uiLanguageTitle'),
        description: t('isoConfig.regionLanguage.uiLanguageDesc'),
        icon: 'globe',
        controlType: 'select',
        options: preset.languages.map(l => ({ value: l.id, label: l.name })),
        value: lang.uiLanguage || ''
      })
      : ''

    // First language ComboCard
    const firstLanguageCardHtml = lang.mode === 'unattended'
      ? createComboCard({
        id: 'config-first-language-card',
        title: t('isoConfig.regionLanguage.firstLanguageTitle'),
        description: t('isoConfig.regionLanguage.firstLanguageDesc'),
        icon: 'languages',
        controlType: 'select',
        options: preset.locales.map(l => ({ value: l.id, label: l.name })),
        value: lang.locale || ''
      })
      : ''

    // First keyboard layout ComboCard
    const firstKeyboardCardHtml = lang.mode === 'unattended'
      ? createComboCard({
        id: 'config-first-keyboard-card',
        title: t('isoConfig.regionLanguage.firstKeyboardTitle'),
        description: '',
        icon: 'keyboard',
        controlType: 'select',
        options: preset.keyboards.map(k => ({ value: k.id, label: k.name })),
        value: lang.keyboard || ''
      })
      : ''

    // 时区模式 Switch ComboCard
    const timezoneModeCardHtml = createComboCard({
      id: 'config-timezone-mode-card',
      title: t('isoConfig.regionLanguage.autoSetTimeZone'),
      description: t('isoConfig.regionLanguage.autoSetTimeZoneDesc'),
      icon: 'clock',
      controlType: 'switch',
      value: tz.mode === 'implicit'
    })

    // 时区选择 ComboCard
    const timezoneSelectCardHtml = tz.mode === 'explicit'
      ? createComboCard({
        id: 'config-timezone-card',
        title: t('isoConfig.regionLanguage.useThisTimeZone'),
        description: '',
        icon: 'map-pin',
        controlType: 'select',
        options: preset.timeZones.map(t => ({ value: t.id, label: t.name })),
        value: tz.timeZone || ''
      })
      : ''

    contentDiv.innerHTML = `
      ${languageModeCardHtml}
      ${uiLanguageCardHtml}
      ${firstLanguageCardHtml}
      ${firstKeyboardCardHtml}
      ${timezoneModeCardHtml}
      ${timezoneSelectCardHtml}
    `

    // 设置语言模式 Switch ComboCard 事件监听
    setupComboCard('config-language-mode-card', (value) => {
      this.updateModule('languageSettings', {
        mode: value ? 'interactive' : 'unattended'
      })
      this.renderRegionLanguageTimeZone()
    })

    // 设置 Windows display language ComboCard 事件监听
    if (lang.mode === 'unattended') {
      setupComboCard('config-ui-language-card', (value) => {
        this.updateModule('languageSettings', { uiLanguage: value as string })
      })

      setupComboCard('config-first-language-card', (value) => {
        this.updateModule('languageSettings', { locale: value as string })
      })

      setupComboCard('config-first-keyboard-card', (value) => {
        this.updateModule('languageSettings', { keyboard: value as string })
      })
    }

    // 设置时区模式 Switch ComboCard 事件监听
    setupComboCard('config-timezone-mode-card', (value) => {
      this.updateModule('timeZone', {
        mode: value ? 'implicit' : 'explicit'
      })
      this.renderRegionLanguageTimeZone()
    })

    // 设置时区选择 ComboCard 事件监听
    if (tz.mode === 'explicit') {
      setupComboCard('config-timezone-card', (value) => {
        this.updateModule('timeZone', { timeZone: value as string })
      })
    }

    // 初始化图标
    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块2: Setup settings
  private renderSetupSettings() {
    const contentDiv = this.getSectionContent('config-setup-settings')
    if (!contentDiv) return

    const settings = this.config.setupSettings

    // 使用 ComboCard 为每个设置创建独立的卡片
    const bypassRequirementsCardHtml = createComboCard({
      id: 'config-bypass-requirements-card',
      title: t('isoConfig.setupSettings.bypassRequirements'),
      description: t('isoConfig.setupSettings.bypassRequirementsDesc'),
      icon: 'shield-off',
      controlType: 'switch',
      value: settings.bypassRequirementsCheck
    })

    const bypassNetworkCardHtml = createComboCard({
      id: 'config-bypass-network-card',
      title: t('isoConfig.setupSettings.bypassNetwork'),
      description: t('isoConfig.setupSettings.bypassNetworkDesc'),
      icon: 'wifi-off',
      controlType: 'switch',
      value: settings.bypassNetworkCheck
    })

    const useConfigurationSetCardHtml = createComboCard({
      id: 'config-use-configuration-set-card',
      title: t('isoConfig.setupSettings.useConfigurationSet'),
      description: t('isoConfig.setupSettings.useConfigurationSetDesc'),
      icon: 'folder-tree',
      controlType: 'switch',
      value: settings.useConfigurationSet
    })

    const hidePowerShellWindowsCardHtml = createComboCard({
      id: 'config-hide-powershell-card',
      title: t('isoConfig.setupSettings.hidePowerShell'),
      description: t('isoConfig.setupSettings.hidePowerShellDesc'),
      icon: 'eye-off',
      controlType: 'switch',
      value: settings.hidePowerShellWindows
    })

    const keepSensitiveFilesCardHtml = createComboCard({
      id: 'config-keep-sensitive-files-card',
      title: t('isoConfig.setupSettings.keepSensitiveFiles'),
      description: t('isoConfig.setupSettings.keepSensitiveFilesDesc'),
      icon: 'file-lock',
      controlType: 'switch',
      value: settings.keepSensitiveFiles
    })

    const useNarratorCardHtml = createComboCard({
      id: 'config-use-narrator-card',
      title: t('isoConfig.setupSettings.useNarrator'),
      description: t('isoConfig.setupSettings.useNarratorDesc'),
      icon: 'volume-2',
      controlType: 'switch',
      value: settings.useNarrator
    })

    contentDiv.innerHTML = `
      ${bypassRequirementsCardHtml}
      ${bypassNetworkCardHtml}
      ${useConfigurationSetCardHtml}
      ${hidePowerShellWindowsCardHtml}
      ${keepSensitiveFilesCardHtml}
      ${useNarratorCardHtml}
    `

    // 设置每个 ComboCard 的事件监听
    setupComboCard('config-bypass-requirements-card', (value) => {
      this.updateModule('setupSettings', { bypassRequirementsCheck: value as boolean })
    })

    setupComboCard('config-bypass-network-card', (value) => {
      this.updateModule('setupSettings', { bypassNetworkCheck: value as boolean })
    })

    setupComboCard('config-use-configuration-set-card', (value) => {
      this.updateModule('setupSettings', { useConfigurationSet: value as boolean })
    })

    setupComboCard('config-hide-powershell-card', (value) => {
      this.updateModule('setupSettings', { hidePowerShellWindows: value as boolean })
    })

    setupComboCard('config-keep-sensitive-files-card', (value) => {
      this.updateModule('setupSettings', { keepSensitiveFiles: value as boolean })
    })

    setupComboCard('config-use-narrator-card', (value) => {
      this.updateModule('setupSettings', { useNarrator: value as boolean })
    })

    // 初始化图标
    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块4: Name and Account (合并Computer name、User accounts、Password expiration、Account Lockout policy)
  private renderNameAndAccount() {
    const contentDiv = this.getSectionContent('config-name-account')
    if (!contentDiv) return

    const cn = this.config.computerName
    const accounts = this.config.accountSettings
    const pe = this.config.passwordExpiration
    const lockout = this.config.lockoutSettings

    // 1. Computer name - RadioContainer（带嵌套卡片）
    const computerNameRadioHtml = createRadioContainer({
      id: 'computer-name-container',
      name: 'computer-name-mode',
      title: t('isoConfig.nameAccount.computerName'),
      description: '',
      icon: 'monitor',
      options: [
        {
          value: 'random',
          label: t('isoConfig.nameAccount.computerNameRandom'),
          description: ''
        },
        {
          value: 'custom',
          label: t('isoConfig.nameAccount.computerNameCustom'),
          description: '',
          nestedCards: [
            {
              id: 'config-computer-name-input-card',
              title: t('isoConfig.nameAccount.useThisName'),
              description: '',
              controlType: 'text',
              value: cn.name || '',
              borderless: true,
              placeholder: 'DESKTOP-PC'
            }
          ]
        },
        {
          value: 'script',
          label: t('isoConfig.nameAccount.computerNameScript'),
          description: '',
          nestedCards: [
            {
              id: 'config-computer-name-script-card',
              title: t('isoConfig.nameAccount.powerShellScript'),
              description: '',
              value: cn.script || '',
              placeholder: "return 'DESKTOP-{0:D3}' -f ( Get-Random -Minimum 0 -Maximum 999 );",
              rows: 5,
              borderless: true,
              showImportExport: true
            } as any // TextCard 配置
          ]
        }
      ],
      selectedValue: cn.mode,
      expanded: true
    })

    // 2. User accounts - RadioContainer
    const userAccountsRadioHtml = createRadioContainer({
      id: 'user-accounts-container',
      name: 'account-mode',
      title: t('isoConfig.nameAccount.userAccounts'),
      description: '',
      icon: 'users',
      options: [
        {
          value: 'unattended',
          label: t('isoConfig.nameAccount.userAccountsUnattended'),
          description: ''
        },
        {
          value: 'interactive-microsoft',
          label: t('isoConfig.nameAccount.userAccountsInteractiveMicrosoft'),
          description: ''
        },
        {
          value: 'interactive-local',
          label: t('isoConfig.nameAccount.userAccountsInteractiveLocal'),
          description: ''
        }
      ],
      selectedValue: accounts.mode,
      expanded: true
    })

    // User accounts list (只在 unattended 模式下显示)
    const userAccountsListHtml = accounts.mode === 'unattended'
      ? `<div class="card-expandable expanded">
          <div class="card-expandable-header">
            <div class="card-expandable-header-left">
              <i data-lucide="user-plus" class="card-icon"></i>
              <div class="card-expandable-title">${t('isoConfig.nameAccount.accountList')}</div>
            </div>
            <div class="card-expandable-arrow">
              <i data-lucide="chevron-down"></i>
            </div>
          </div>
          <div class="card-expandable-content">
            <div class="card-description" style="margin-bottom: 12px;">${t('isoConfig.nameAccount.accountListDesc')}</div>
            <div id="config-accounts-list" style="display: flex; flex-direction: column; gap: 12px;">
              ${(accounts.accounts || []).map((acc, idx) => `
                <div class="card" style="background: var(--bg-primary);">
                  <div class="card-content" style="width: 100%;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr auto; gap: 12px; align-items: end;">
                      <div>
                        <label style="display: block; margin-bottom: 6px; font-size: 12px;">${t('isoConfig.nameAccount.accountName')}</label>
                        <fluent-text-field class="account-name" data-index="${idx}" value="${acc.name}" maxlength="20" style="width: 100%;"></fluent-text-field>
                      </div>
                      <div>
                        <label style="display: block; margin-bottom: 6px; font-size: 12px;">${t('isoConfig.nameAccount.displayName')}</label>
                        <fluent-text-field class="account-display-name" data-index="${idx}" value="${acc.displayName}" maxlength="256" style="width: 100%;"></fluent-text-field>
                      </div>
                      <div>
                        <label style="display: block; margin-bottom: 6px; font-size: 12px;">${t('isoConfig.nameAccount.password')}</label>
                        <fluent-text-field class="account-password" data-index="${idx}" type="password" value="${acc.password}" style="width: 100%;"></fluent-text-field>
                      </div>
                      <div>
                        <label style="display: block; margin-bottom: 6px; font-size: 12px;">${t('isoConfig.nameAccount.group')}</label>
                        <fluent-select class="account-group" data-index="${idx}" style="width: 100%;">
                          <fluent-option value="Administrators" ${acc.group === 'Administrators' ? 'selected' : ''}>${t('isoConfig.nameAccount.administrators')}</fluent-option>
                          <fluent-option value="Users" ${acc.group === 'Users' ? 'selected' : ''}>${t('isoConfig.nameAccount.users')}</fluent-option>
                        </fluent-select>
                      </div>
                      <fluent-button class="account-remove" data-index="${idx}" appearance="stealth">
                        <i data-lucide="trash-2"></i>
                      </fluent-button>
                    </div>
                  </div>
                </div>
              `).join('')}
            </div>
            <div style="margin-top: 12px;">
              <fluent-button id="config-add-account" appearance="outline">
                <i data-lucide="plus"></i> ${t('common.add')}
              </fluent-button>
            </div>
          </div>
        </div>`
      : ''

    // First logon - RadioContainer (只在 unattended 模式下显示)
    const firstLogonRadioHtml = accounts.mode === 'unattended'
      ? createRadioContainer({
        id: 'first-logon-container',
        name: 'auto-logon-mode',
        title: t('isoConfig.nameAccount.firstLogon'),
        description: t('isoConfig.nameAccount.firstLogonDesc'),
        icon: 'log-in',
        options: [
          {
            value: 'own',
            label: t('isoConfig.nameAccount.logonOwnAccount'),
            description: ''
          },
          {
            value: 'builtin',
            label: t('isoConfig.nameAccount.logonBuiltinAdmin'),
            description: ''
          },
          {
            value: 'none',
            label: t('isoConfig.nameAccount.logonNone'),
            description: t('isoConfig.nameAccount.logonNoneDesc')
          }
        ],
        selectedValue: accounts.autoLogonMode || 'none',
        expanded: true
      })
      : ''

    // Built-in Administrator password (只在 builtin 模式下显示)
    const builtinAdminPasswordHtml = accounts.mode === 'unattended' && accounts.autoLogonMode === 'builtin'
      ? `<div class="card">
          <div class="card-left">
            <div class="card-content">
              <label style="display: block; margin-bottom: 6px; font-weight: 600;">${t('isoConfig.nameAccount.builtinAdminPassword')}</label>
              <fluent-text-field id="config-auto-logon-password" type="password" value="${accounts.autoLogonPassword || ''}" style="width: 100%;"></fluent-text-field>
            </div>
          </div>
        </div>`
      : ''

    // Obscure passwords - ComboCard
    const obscurePasswordsCardHtml = accounts.mode === 'unattended'
      ? createComboCard({
        id: 'config-obscure-passwords-card',
        title: t('isoConfig.nameAccount.obscurePasswords'),
        description: t('isoConfig.nameAccount.obscurePasswordsDesc'),
        icon: 'eye-off',
        controlType: 'switch',
        value: accounts.obscurePasswords || false
      })
      : ''

    // 3. Password expiration - RadioContainer（带嵌套 ComboCard）
    const passwordExpirationRadioHtml = createRadioContainer({
      id: 'password-expiration-container',
      name: 'password-expiration-mode',
      title: t('isoConfig.nameAccount.passwordExpiration'),
      description: t('isoConfig.nameAccount.passwordExpirationDesc'),
      icon: 'shield',
      options: [
        {
          value: 'unlimited',
          label: t('isoConfig.nameAccount.passwordUnlimited'),
          description: t('isoConfig.nameAccount.passwordUnlimitedDesc')
        },
        {
          value: 'default',
          label: t('isoConfig.nameAccount.passwordDefault'),
          description: t('isoConfig.nameAccount.passwordDefaultDesc')
        },
        {
          value: 'custom',
          label: t('isoConfig.nameAccount.passwordCustom'),
          description: '',
          nestedCards: [
            {
              id: 'config-password-max-age-card',
              title: t('isoConfig.nameAccount.passwordExpireAfter'),
              description: '',
              controlType: 'text',
              value: (pe.maxAge || 42).toString(),
              borderless: true,
              placeholder: '42'
            }
          ]
        }
      ],
      selectedValue: pe.mode,
      expanded: true
    })

    // 4. Account Lockout policy - RadioContainer（带嵌套 ComboCard）
    const accountLockoutRadioHtml = createRadioContainer({
      id: 'account-lockout-container',
      name: 'lockout-mode',
      title: t('isoConfig.nameAccount.accountLockout'),
      description: '',
      icon: 'lock',
      options: [
        {
          value: 'default',
          label: t('isoConfig.nameAccount.lockoutDefault'),
          description: t('isoConfig.nameAccount.lockoutDefaultDesc')
        },
        {
          value: 'disabled',
          label: t('isoConfig.nameAccount.lockoutDisabled'),
          description: t('isoConfig.nameAccount.lockoutDisabledDesc')
        },
        {
          value: 'custom',
          label: t('isoConfig.nameAccount.lockoutCustom'),
          description: t('isoConfig.nameAccount.lockoutCustomDesc'),
          nestedCards: [
            {
              id: 'config-lockout-threshold-card',
              title: t('isoConfig.nameAccount.lockoutThreshold'),
              description: t('isoConfig.nameAccount.failedAttempts'),
              controlType: 'text',
              value: (lockout.lockoutThreshold || 10).toString(),
              borderless: true,
              placeholder: '10'
            },
            {
              id: 'config-lockout-window-card',
              title: t('isoConfig.nameAccount.lockoutWindow'),
              description: t('isoConfig.nameAccount.minutes'),
              controlType: 'text',
              value: (lockout.resetLockoutCounter || 10).toString(),
              borderless: true,
              placeholder: '10'
            },
            {
              id: 'config-lockout-duration-card',
              title: t('isoConfig.nameAccount.lockoutDuration'),
              description: t('isoConfig.nameAccount.minutes'),
              controlType: 'text',
              value: (lockout.lockoutDuration || 10).toString(),
              borderless: true,
              placeholder: '10'
            }
          ]
        }
      ],
      selectedValue: lockout.mode,
      expanded: true
    })

    contentDiv.innerHTML = `
      ${computerNameRadioHtml}
      ${userAccountsRadioHtml}
      ${userAccountsListHtml}
      ${firstLogonRadioHtml}
      ${builtinAdminPasswordHtml}
      ${obscurePasswordsCardHtml}
      ${passwordExpirationRadioHtml}
      ${accountLockoutRadioHtml}
    `

    // === 事件监听设置 ===

    // 1. Computer name 事件
    setupRadioContainer('computer-name-container', 'computer-name-mode', (value) => {
      this.updateModule('computerName', { mode: value as 'random' | 'custom' | 'script' })
      this.renderNameAndAccount()
    }, true)

    // 设置嵌套卡片的事件监听
    if (cn.mode === 'custom') {
      setupComboCard('config-computer-name-input-card', (value) => {
        this.updateModule('computerName', { name: value as string })
      })
    } else if (cn.mode === 'script') {
      setupTextCard(
        'config-computer-name-script-card',
        (value) => {
          this.updateModule('computerName', { script: value })
        },
        async () => {
          // 导入脚本
          if (window.electronAPI?.showOpenDialog) {
            const result = await window.electronAPI.showOpenDialog({
              filters: [{ name: 'PowerShell Scripts', extensions: ['ps1', 'txt'] }],
              properties: ['openFile']
            })
            if (!result.canceled && result.filePaths?.[0] && window.electronAPI?.readFile) {
              const content = await window.electronAPI.readFile(result.filePaths[0])
              setTextCardValue('config-computer-name-script-card', content)
              this.updateModule('computerName', { script: content })
            }
          }
        },
        async () => {
          // 导出脚本
          if (window.electronAPI?.showSaveDialog) {
            const result = await window.electronAPI.showSaveDialog({
              filters: [{ name: 'PowerShell Scripts', extensions: ['ps1'] }],
              defaultPath: 'computer-name.ps1'
            })
            if (!result.canceled && result.filePath && window.electronAPI?.writeFile) {
              // 获取当前值，如果为空则使用placeholder中的默认脚本
              const currentValue = getTextCardValue('config-computer-name-script-card', true)
              await window.electronAPI.writeFile(result.filePath, currentValue)
            }
          }
        }
      )
    }

    // 2. User accounts 事件
    setupRadioContainer('user-accounts-container', 'account-mode', (value) => {
      this.updateModule('accountSettings', { mode: value as 'interactive-microsoft' | 'interactive-local' | 'unattended' })
      this.renderNameAndAccount()
    }, true)

    if (accounts.mode === 'unattended') {
      // 添加账户
      const addBtn = contentDiv.querySelector('#config-add-account')
      if (addBtn) {
        addBtn.addEventListener('click', () => {
          const accs = accounts.accounts || []
          accs.push({ name: '', displayName: '', password: '', group: 'Users' })
          this.updateModule('accountSettings', { accounts: accs })
          this.renderNameAndAccount()
        })
      }

      // 移除账户
      contentDiv.querySelectorAll('.account-remove').forEach(btn => {
        btn.addEventListener('click', (e: any) => {
          const idx = parseInt(e.target.closest('[data-index]').dataset.index)
          const accs = [...(accounts.accounts || [])]
          accs.splice(idx, 1)
          this.updateModule('accountSettings', { accounts: accs })
          this.renderNameAndAccount()
        })
      })

      // 更新账户字段
      contentDiv.querySelectorAll('.account-name, .account-display-name, .account-password').forEach(field => {
        field.addEventListener('input', (e: any) => {
          const idx = parseInt(e.target.dataset.index)
          const accs = [...(accounts.accounts || [])]
          const fieldType = e.target.classList.contains('account-name') ? 'name' :
            e.target.classList.contains('account-display-name') ? 'displayName' : 'password'
          accs[idx] = { ...accs[idx], [fieldType]: e.target.value }
          this.updateModule('accountSettings', { accounts: accs })
        })
      })

      // 更新账户组
      contentDiv.querySelectorAll('.account-group').forEach(select => {
        select.addEventListener('change', (e: any) => {
          const idx = parseInt(e.target.dataset.index)
          const accs = [...(accounts.accounts || [])]
          accs[idx] = { ...accs[idx], group: e.target.value }
          this.updateModule('accountSettings', { accounts: accs })
        })
      })

      // First logon 事件
      setupRadioContainer('first-logon-container', 'auto-logon-mode', (value) => {
        this.updateModule('accountSettings', { autoLogonMode: value as 'none' | 'builtin' | 'own' })
        this.renderNameAndAccount()
      }, true)

      // Built-in Administrator password
      const autoLogonPwd = contentDiv.querySelector('#config-auto-logon-password') as any
      if (autoLogonPwd) {
        autoLogonPwd.addEventListener('input', (e: any) => {
          this.updateModule('accountSettings', { autoLogonPassword: e.target.value })
        })
      }

      // Obscure passwords
      setupComboCard('config-obscure-passwords-card', (value) => {
        this.updateModule('accountSettings', { obscurePasswords: value as boolean })
      })
    }

    // 3. Password expiration 事件
    setupRadioContainer('password-expiration-container', 'password-expiration-mode', (value) => {
      this.updateModule('passwordExpiration', { mode: value as 'default' | 'unlimited' | 'custom' })
      this.renderNameAndAccount()
    }, true)

    // 设置嵌套的 ComboCard 事件监听
    if (pe.mode === 'custom') {
      setupComboCard('config-password-max-age-card', (value) => {
        const numValue = parseInt(value as string) || 42
        this.updateModule('passwordExpiration', { maxAge: numValue })
      })
    }

    // 4. Account Lockout policy 事件
    setupRadioContainer('account-lockout-container', 'lockout-mode', (value) => {
      this.updateModule('lockoutSettings', { mode: value as 'default' | 'disabled' | 'custom' })
      this.renderNameAndAccount()
    }, true)

    // 设置嵌套的 ComboCard 事件监听
    if (lockout.mode === 'custom') {
      setupComboCard('config-lockout-threshold-card', (value) => {
        const numValue = parseInt(value as string) || 10
        this.updateModule('lockoutSettings', { lockoutThreshold: numValue })
      })

      setupComboCard('config-lockout-window-card', (value) => {
        const numValue = parseInt(value as string) || 10
        this.updateModule('lockoutSettings', { resetLockoutCounter: numValue })
      })

      setupComboCard('config-lockout-duration-card', (value) => {
        const numValue = parseInt(value as string) || 10
        this.updateModule('lockoutSettings', { lockoutDuration: numValue })
      })
    }

    // 初始化图标
    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块11: Advanced Settings (合并Compact OS、PE operation、Virtual machine support、WDAC)
  private renderAdvancedSettings() {
    const contentDiv = this.getSectionContent('config-advanced-settings')
    if (!contentDiv) return

    const compactOS = this.config.compactOS
    const pe = this.config.peSettings
    const vm = this.config.vmSupport
    const wdac = this.config.wdac

    // 1. Compact OS - RadioContainer
    const compactOSRadioHtml = createRadioContainer({
      id: 'compact-os-container',
      name: 'compact-os-mode',
      title: t('isoConfig.advancedSettings.compactOS'),
      description: '',
      icon: 'archive',
      options: [
        {
          value: 'default',
          label: t('isoConfig.advancedSettings.compactOSDefault'),
          description: ''
        },
        {
          value: 'enabled',
          label: t('isoConfig.advancedSettings.compactOSEnabled'),
          description: ''
        },
        {
          value: 'disabled',
          label: t('isoConfig.advancedSettings.compactOSDisabled'),
          description: ''
        }
      ],
      selectedValue: compactOS,
      expanded: true
    })

    // 2. Windows PE operation - RadioContainer
    const peOperationRadioHtml = createRadioContainer({
      id: 'pe-operation-container',
      name: 'pe-mode',
      title: t('isoConfig.advancedSettings.peOperation'),
      description: '',
      icon: 'terminal',
      options: [
        {
          value: 'default',
          label: t('isoConfig.advancedSettings.peDefault'),
          description: ''
        },
        {
          value: 'generated',
          label: t('isoConfig.advancedSettings.peGenerated'),
          description: '',
          nestedCards: [
            {
              id: 'config-pe-disable-8dot3-card',
              title: t('isoConfig.advancedSettings.disable8dot3'),
              description: t('isoConfig.advancedSettings.disable8dot3Desc'),
              controlType: 'checkbox',
              value: pe.disable8Dot3Names || false,
              borderless: true
            },
            {
              id: 'config-pe-pause-formatting-card',
              title: t('isoConfig.advancedSettings.pauseFormatting'),
              description: '',
              controlType: 'checkbox',
              value: pe.pauseBeforeFormatting || false,
              borderless: true
            },
            {
              id: 'config-pe-pause-reboot-card',
              title: t('isoConfig.advancedSettings.pauseReboot'),
              description: '',
              controlType: 'checkbox',
              value: pe.pauseBeforeReboot || false,
              borderless: true
            }
          ]
        },
        {
          value: 'script',
          label: t('isoConfig.advancedSettings.peScript'),
          description: '',
          nestedCards: [
            {
              id: 'config-pe-custom-script-card',
              title: t('isoConfig.advancedSettings.customPeScript'),
              description: t('isoConfig.advancedSettings.customPeScriptDesc'),
              icon: 'code',
              value: pe.cmdScript || '',
              placeholder: `@echo off
echo Custom PE script
pause`,
              rows: 10,
              borderless: true,
              showImportExport: true
            } as any
          ]
        }
      ],
      selectedValue: pe.mode,
      expanded: true
    })


    // 3. Virtual machine support - ComboContainer
    const vmSupportHtml = createComboContainer({
      id: 'vm-support-container',
      name: 'vm-support',
      title: t('isoConfig.advancedSettings.vmSupport'),
      description: t('isoConfig.advancedSettings.vmSupportDesc'),
      icon: 'box',
      options: [
        {
          value: 'vBoxGuestAdditions',
          label: t('isoConfig.advancedSettings.vboxGuestAdditions'),
          description: '',
          controlType: 'checkbox'
        },
        {
          value: 'vmwareTools',
          label: t('isoConfig.advancedSettings.vmwareTools'),
          description: '',
          controlType: 'checkbox'
        },
        {
          value: 'virtIoGuestTools',
          label: t('isoConfig.advancedSettings.virtioGuestTools'),
          description: '',
          controlType: 'checkbox'
        },
        {
          value: 'parallelsTools',
          label: t('isoConfig.advancedSettings.parallelsTools'),
          description: '',
          controlType: 'checkbox'
        }
      ],
      values: {
        vBoxGuestAdditions: vm.vBoxGuestAdditions || false,
        vmwareTools: vm.vmwareTools || false,
        virtIoGuestTools: vm.virtIoGuestTools || false,
        parallelsTools: vm.parallelsTools || false
      },
      expanded: true
    })

    // 4. WDAC - ComboCard Switch
    const wdacCardHtml = createComboCard({
      id: 'wdac-mode-card',
      title: t('isoConfig.advancedSettings.wdac'),
      description: t('isoConfig.advancedSettings.wdacDesc'),
      icon: 'shield-alert',
      controlType: 'switch',
      value: wdac.mode === 'configure'
    })

    // 4.1 WDAC Configure模式 - Policy设置 (独立显示)
    const wdacEnforcementHtml = wdac.mode === 'configure'
      ? createRadioContainer({
        id: 'wdac-enforcement-container',
        name: 'wdac-enforcement-mode',
        title: t('isoConfig.advancedSettings.wdacEnforcement'),
        description: '',
        icon: 'shield',
        options: [
          {
            value: 'audit',
            label: t('isoConfig.advancedSettings.wdacAudit'),
            description: t('isoConfig.advancedSettings.wdacAuditDesc')
          },
          {
            value: 'auditOnBootFailure',
            label: t('isoConfig.advancedSettings.wdacAuditBootFailure'),
            description: t('isoConfig.advancedSettings.wdacAuditBootFailureDesc')
          },
          {
            value: 'enforcement',
            label: t('isoConfig.advancedSettings.wdacEnforcementMode'),
            description: t('isoConfig.advancedSettings.wdacEnforcementDesc')
          }
        ],
        selectedValue: wdac.enforcementMode || 'auditOnBootFailure',
        expanded: true
      })
      : ''

    const wdacScriptHtml = wdac.mode === 'configure'
      ? createRadioContainer({
        id: 'wdac-script-enforcement-container',
        name: 'wdac-script-mode',
        title: t('isoConfig.advancedSettings.wdacScriptEnforcement'),
        description: '',
        icon: 'file-code',
        options: [
          {
            value: 'restricted',
            label: t('isoConfig.advancedSettings.wdacScriptRestricted'),
            description: t('isoConfig.advancedSettings.wdacScriptRestrictedDesc')
          },
          {
            value: 'unrestricted',
            label: t('isoConfig.advancedSettings.wdacScriptUnrestricted'),
            description: ''
          }
        ],
        selectedValue: wdac.scriptEnforcement || 'restricted',
        expanded: true
      })
      : ''

    contentDiv.innerHTML = `
      ${compactOSRadioHtml}
      ${peOperationRadioHtml}
      ${vmSupportHtml}
      ${wdacCardHtml}
      ${wdacEnforcementHtml}
      ${wdacScriptHtml}
    `

    // === 事件监听设置 ===

    // 1. Compact OS
    setupRadioContainer('compact-os-container', 'compact-os-mode', (value) => {
      this.updateConfig({ compactOS: value as CompactOSMode })
    }, true)

    // 2. PE operation
    setupRadioContainer('pe-operation-container', 'pe-mode', (value) => {
      this.updateModule('peSettings', { mode: value as 'default' | 'generated' | 'script' })
      this.renderAdvancedSettings()
    }, true)

    // 2.1 Generated 选项 (嵌套)
    if (pe.mode === 'generated') {
      setupComboCard('config-pe-disable-8dot3-card', (value) => {
        this.updateModule('peSettings', { disable8Dot3Names: value as boolean })
      })

      setupComboCard('config-pe-pause-formatting-card', (value) => {
        this.updateModule('peSettings', { pauseBeforeFormatting: value as boolean })
      })

      setupComboCard('config-pe-pause-reboot-card', (value) => {
        this.updateModule('peSettings', { pauseBeforeReboot: value as boolean })
      })
    }

    // 2.2 Custom script (嵌套)
    if (pe.mode === 'script') {
      setupTextCard('config-pe-custom-script-card', (value) => {
        this.updateModule('peSettings', { cmdScript: value })
      }, async () => {
        // 导入脚本
        if (window.electronAPI?.showOpenDialog) {
          const result = await window.electronAPI.showOpenDialog({
            filters: [{ name: 'Script Files', extensions: ['cmd', 'bat', 'txt'] }],
            properties: ['openFile']
          })
          if (!result.canceled && result.filePaths?.[0] && window.electronAPI?.readFile) {
            const content = await window.electronAPI.readFile(result.filePaths[0])
            setTextCardValue('config-pe-custom-script-card', content)
            this.updateModule('peSettings', { cmdScript: content })
          }
        }
      }, async () => {
        // 导出脚本
        if (window.electronAPI?.showSaveDialog) {
          const result = await window.electronAPI.showSaveDialog({
            filters: [{ name: 'Batch Files', extensions: ['cmd', 'bat'] }],
            defaultPath: 'pe-script.cmd'
          })
          if (!result.canceled && result.filePath && window.electronAPI?.writeFile) {
            const currentValue = getTextCardValue('config-pe-custom-script-card', true)
            await window.electronAPI.writeFile(result.filePath, currentValue)
          }
        }
      })
    }

    // 3. Virtual machine support
    setupComboContainer('vm-support-container', 'vm-support', (values) => {
      this.updateModule('vmSupport', values)
    }, true)

    // 4. WDAC Switch
    setupComboCard('wdac-mode-card', (value) => {
      const enabled = value as boolean
      this.updateModule('wdac', { mode: enabled ? 'configure' : 'skip' })
      this.renderAdvancedSettings()
    })

    // 4.1 WDAC Configure (仅在启用时显示)
    if (wdac.mode === 'configure') {
      setupRadioContainer('wdac-enforcement-container', 'wdac-enforcement-mode', (value) => {
        this.updateModule('wdac', { enforcementMode: value as 'audit' | 'auditOnBootFailure' | 'enforcement' })
      }, true)

      setupRadioContainer('wdac-script-enforcement-container', 'wdac-script-mode', (value) => {
        this.updateModule('wdac', { scriptEnforcement: value as 'restricted' | 'unrestricted' })
      }, true)
    }

    // 初始化图标
    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块7: Partitioning and formatting
  private renderPartitioning() {
    const contentDiv = this.getSectionContent('config-partitioning')
    if (!contentDiv) return

    const part = this.config.partitioning

    // 1. 主要分区模式 - RadioContainer (带嵌套)
    const partitionModeRadioHtml = createRadioContainer({
      id: 'partitioning-mode-container',
      name: 'partition-mode',
      title: t('isoConfig.partitioning.title'),
      description: '',
      icon: 'hard-drive',
      options: [
        {
          value: 'interactive',
          label: t('isoConfig.partitioning.interactive'),
          description: ''
        },
        {
          value: 'automatic',
          label: t('isoConfig.partitioning.automatic'),
          description: '',
          nestedCards: [
            // Partition Layout Select
            {
              id: 'partition-layout-card',
              title: t('isoConfig.partitioning.partitionLayout'),
              description: '',
              icon: 'layout',
              controlType: 'select',
              value: part.layout || 'GPT',
              options: [
                { value: 'GPT', label: t('isoConfig.partitioning.gpt') },
                { value: 'MBR', label: t('isoConfig.partitioning.mbr') }
              ],
              borderless: true
            },
            // ESP Size (仅GPT显示)
            ...(part.layout === 'GPT' ? [{
              id: 'esp-size-card',
              title: t('isoConfig.partitioning.espSize') + ' (MB)',
              description: t('isoConfig.partitioning.gptDesc'),
              controlType: 'text' as const,
              value: String(part.espSize || 300),
              placeholder: '300',
              borderless: true
            }] : []),
            // Windows RE Mode Select
            {
              id: 'recovery-mode-card',
              title: t('isoConfig.partitioning.windowsRe'),
              description: t('isoConfig.partitioning.windowsReDesc'),
              icon: 'life-buoy',
              controlType: 'select',
              value: part.recoveryMode || 'partition',
              options: [
                { value: 'partition', label: t('isoConfig.partitioning.rePartition') },
                { value: 'folder', label: t('isoConfig.partitioning.reFolder') },
                { value: 'none', label: t('isoConfig.partitioning.reNone') }
              ],
              borderless: true
            },
            // Recovery Partition Size (总是显示)
            {
              id: 'recovery-size-card',
              title: t('isoConfig.partitioning.recoverySize') + ' (MB)',
              description: t('isoConfig.partitioning.recoverySizeDesc'),
              controlType: 'text' as const,
              value: String(part.recoverySize || 1000),
              placeholder: '1000',
              borderless: true
            }
          ] as any
        },
        {
          value: 'custom',
          label: t('isoConfig.partitioning.custom'),
          description: '',
          nestedCards: [
            // Diskpart Script
            {
              id: 'diskpart-script-card',
              title: t('isoConfig.partitioning.diskpartScript'),
              description: t('isoConfig.partitioning.diskpartScriptDesc'),
              icon: 'code',
              value: part.diskpartScript || '',
              placeholder: `SELECT DISK=0
CLEAN
CONVERT GPT
CREATE PARTITION EFI SIZE=300
FORMAT QUICK FS=FAT32 LABEL="System"
ASSIGN LETTER=S
CREATE PARTITION MSR SIZE=16
CREATE PARTITION PRIMARY
SHRINK MINIMUM=1000
FORMAT QUICK FS=NTFS LABEL="Windows"
ASSIGN LETTER=W
CREATE PARTITION PRIMARY
FORMAT QUICK FS=NTFS LABEL="Recovery"
ASSIGN LETTER=R
SET ID="de94bba4-06d1-4d40-a16a-bfd50179d6ac"
GPT ATTRIBUTES=0x8000000000000001`,
              rows: 18,
              borderless: true,
              showImportExport: true
            },
            // Install To Mode Select
            {
              id: 'install-to-mode-card',
              title: t('isoConfig.partitioning.installTo'),
              description: '',
              icon: 'target',
              controlType: 'select',
              value: part.installToMode || 'available',
              options: [
                { value: 'available', label: t('isoConfig.partitioning.installToAvailable') },
                { value: 'custom', label: t('isoConfig.partitioning.installToCustom') }
              ],
              borderless: true
            },
            // Install Disk (无条件显示)
            {
              id: 'install-to-disk-card',
              title: t('isoConfig.partitioning.installDisk'),
              description: t('isoConfig.partitioning.installDiskDesc'),
              controlType: 'text' as const,
              value: String(part.installToDisk || 0),
              placeholder: '0',
              borderless: true
            },
            // Install Partition (无条件显示)
            {
              id: 'install-to-partition-card',
              title: t('isoConfig.partitioning.installPartition'),
              description: t('isoConfig.partitioning.installPartitionDesc'),
              controlType: 'text' as const,
              value: String(part.installToPartition || 3),
              placeholder: '3',
              borderless: true
            }
          ] as any
        }
      ],
      selectedValue: part.mode,
      expanded: true
    })

    // 2. 磁盘断言 RadioContainer（无条件显示）
    const diskAssertionRadioHtml = createRadioContainer({
      id: 'disk-assertion-container',
      name: 'disk-assertion-mode',
      title: t('isoConfig.partitioning.diskAssertion'),
      description: t('isoConfig.partitioning.diskAssertionDesc'),
      icon: 'alert-triangle',
      options: [
        {
          value: 'skip',
          label: t('isoConfig.partitioning.diskAssertionSkip'),
          description: ''
        },
        {
          value: 'script',
          label: t('isoConfig.partitioning.diskAssertionScript'),
          description: '',
          nestedCards: [
            {
              id: 'disk-assertion-script-card',
              title: t('isoConfig.partitioning.vbscriptCode'),
              description: '',
              icon: 'code',
              value: part.diskAssertionScript || '',
              placeholder: `On Error Resume Next
Set wmi = GetObject("winmgmts:\\\\.\\root\\cimv2")
Set drive = wmi.Get("Win32_DiskDrive.DeviceID='\\\\.\\PHYSICALDRIVE0'")
If Err.Number <> 0 Then
    Msgbox Err.Description
    WScript.Quit 1
End If
If drive.InterfaceType = "IDE" Or drive.InterfaceType = "SCSI" Then
    WScript.Quit 0
Else
    MsgBox "Assertion failed."
    WScript.Quit 1
End If`,
              rows: 15,
              borderless: true,
              showImportExport: true
            } as any
          ]
        }
      ],
      selectedValue: part.diskAssertionMode || 'skip',
      expanded: true
    })

    contentDiv.innerHTML = `
      ${partitionModeRadioHtml}
      ${diskAssertionRadioHtml}
    `

    // === 事件监听设置 ===

    // 1. 主要分区模式
    setupRadioContainer('partitioning-mode-container', 'partition-mode', (value) => {
      this.updateModule('partitioning', { mode: value as 'interactive' | 'automatic' | 'custom' })
      this.renderPartitioning()
    }, true)

    // 2. Automatic 模式的嵌套卡片事件
    if (part.mode === 'automatic') {
      setupComboCard('partition-layout-card', (value) => {
        this.updateModule('partitioning', { layout: value as 'GPT' | 'MBR' })
        this.renderPartitioning()
      })

      if (part.layout === 'GPT') {
        setupComboCard('esp-size-card', (value) => {
          this.updateModule('partitioning', { espSize: parseInt(value as string) || 300 })
        })
      }

      setupComboCard('recovery-mode-card', (value) => {
        this.updateModule('partitioning', { recoveryMode: value as 'partition' | 'folder' | 'none' })
        this.renderPartitioning()
      })

      // Recovery Size (无条件设置)
      setupComboCard('recovery-size-card', (value) => {
        this.updateModule('partitioning', { recoverySize: parseInt(value as string) || 1000 })
      })
    }

    // 3. Custom 模式的嵌套卡片事件
    if (part.mode === 'custom') {
      setupTextCard('diskpart-script-card', (value) => {
        this.updateModule('partitioning', { diskpartScript: value })
      }, async () => {
        if (window.electronAPI?.showOpenDialog) {
          const result = await window.electronAPI.showOpenDialog({
            filters: [{ name: 'Diskpart Script', extensions: ['txt', 'diskpart'] }],
            properties: ['openFile']
          })
          if (!result.canceled && result.filePaths?.[0] && window.electronAPI?.readFile) {
            const content = await window.electronAPI.readFile(result.filePaths[0])
            this.updateModule('partitioning', { diskpartScript: content })
            this.renderPartitioning()
          }
        }
      }, async () => {
        if (window.electronAPI?.showSaveDialog) {
          const result = await window.electronAPI.showSaveDialog({
            filters: [{ name: 'Diskpart Script', extensions: ['txt'] }],
            defaultPath: 'diskpart-script.txt'
          })
          if (!result.canceled && result.filePath && window.electronAPI?.writeFile) {
            // 获取当前值，如果为空则使用placeholder中的默认脚本
            const currentValue = getTextCardValue('diskpart-script-card', true)
            await window.electronAPI.writeFile(result.filePath, currentValue)
          }
        }
      })

      setupComboCard('install-to-mode-card', (value) => {
        this.updateModule('partitioning', { installToMode: value as 'available' | 'custom' })
        this.renderPartitioning()
      })

      // Install Disk & Partition (无条件设置)
      setupComboCard('install-to-disk-card', (value) => {
        this.updateModule('partitioning', { installToDisk: parseInt(value as string) || 0 })
      })

      setupComboCard('install-to-partition-card', (value) => {
        this.updateModule('partitioning', { installToPartition: parseInt(value as string) || 3 })
      })
    }

    // 4. 磁盘断言事件（无条件设置）
    setupRadioContainer('disk-assertion-container', 'disk-assertion-mode', (value) => {
      this.updateModule('partitioning', { diskAssertionMode: value as 'skip' | 'script' })
      this.renderPartitioning()
    }, true)

    if (part.diskAssertionMode === 'script') {
      setupTextCard('disk-assertion-script-card', (value) => {
        this.updateModule('partitioning', { diskAssertionScript: value })
      }, async () => {
        // 导入脚本
        if (window.electronAPI?.showOpenDialog) {
          const result = await window.electronAPI.showOpenDialog({
            filters: [{ name: 'VBScript Files', extensions: ['vbs', 'txt'] }],
            properties: ['openFile']
          })
          if (!result.canceled && result.filePaths?.[0] && window.electronAPI?.readFile) {
            const content = await window.electronAPI.readFile(result.filePaths[0])
            setTextCardValue('disk-assertion-script-card', content)
            this.updateModule('partitioning', { diskAssertionScript: content })
          }
        }
      }, async () => {
        // 导出脚本
        if (window.electronAPI?.showSaveDialog) {
          const result = await window.electronAPI.showSaveDialog({
            filters: [{ name: 'VBScript Files', extensions: ['vbs'] }],
            defaultPath: 'disk-assertion.vbs'
          })
          if (!result.canceled && result.filePath && window.electronAPI?.writeFile) {
            // 获取当前值，如果为空则使用placeholder中的默认脚本
            const currentValue = getTextCardValue('disk-assertion-script-card', true)
            await window.electronAPI.writeFile(result.filePath, currentValue)
          }
        }
      })
    }

    // 初始化图标
    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块8+9: Windows Edition and Source (合并)
  private renderWindowsEditionAndSource() {
    const contentDiv = this.getSectionContent('config-windows-edition')
    if (!contentDiv) return

    const edition = this.config.windowsEdition
    const source = this.config.sourceImage
    const preset = this.getPresetData()

    // 1. Windows Edition Mode - RadioContainer (带嵌套)
    const editionModeRadioHtml = createRadioContainer({
      id: 'windows-edition-mode-container',
      name: 'edition-mode',
      title: t('isoConfig.windowsEdition.title'),
      description: '',
      icon: 'key',
      options: [
        {
          value: 'generic',
          label: t('isoConfig.windowsEdition.generic'),
          description: t('isoConfig.windowsEdition.genericDesc'),
          nestedCards: [
            {
              id: 'config-windows-edition-card',
              title: t('isoConfig.windowsEdition.installThisEdition'),
              icon: 'package',
              controlType: 'select',
              options: preset.windowsEditions.map(e => ({ value: e.id, label: e.name })),
              value: edition.editionName || 'pro',
              borderless: true
            }
          ]
        },
        {
          value: 'custom',
          label: t('isoConfig.windowsEdition.custom'),
          description: '',
          nestedCards: [
            {
              id: 'config-product-key-card',
              title: t('isoConfig.windowsEdition.useThisProductKey'),
              description: '',
              controlType: 'text',
              value: edition.productKey || '',
              placeholder: 'XXXXX-XXXXX-XXXXX-XXXXX-XXXXX',
              borderless: true
            }
          ]
        },
        {
          value: 'interactive',
          label: t('isoConfig.windowsEdition.interactive'),
          description: t('isoConfig.windowsEdition.interactiveDesc')
        },
        {
          value: 'firmware',
          label: t('isoConfig.windowsEdition.firmware'),
          description: t('isoConfig.windowsEdition.firmwareDesc')
        }
      ],
      selectedValue: edition.mode === 'key' ? 'custom' : edition.mode === 'index' || edition.mode === 'name' ? 'generic' : edition.mode,
      expanded: true
    })

    // 2. Source Image Mode - RadioContainer (带嵌套)
    const sourceImageModeRadioHtml = createRadioContainer({
      id: 'source-image-mode-container',
      name: 'source-image-mode',
      title: t('isoConfig.windowsEdition.sourceImage'),
      description: t('isoConfig.windowsEdition.sourceImageDesc'),
      icon: 'disc',
      options: [
        {
          value: 'automatic',
          label: t('isoConfig.windowsEdition.selectByKey'),
          description: ''
        },
        {
          value: 'index',
          label: t('isoConfig.windowsEdition.selectByIndex'),
          description: '',
          nestedCards: [
            {
              id: 'config-source-image-index-card',
              title: t('isoConfig.windowsEdition.selectByIndex'),
              description: '',
              controlType: 'text',
              value: String(source.imageIndex || 1),
              placeholder: '1',
              borderless: true
            }
          ]
        },
        {
          value: 'name',
          label: t('isoConfig.windowsEdition.selectByName'),
          description: '',
          nestedCards: [
            {
              id: 'config-source-image-name-card',
              title: t('isoConfig.windowsEdition.selectByName'),
              description: '',
              controlType: 'text',
              value: source.imageName || '',
              placeholder: 'Windows 11 Pro',
              borderless: true
            }
          ]
        }
      ],
      selectedValue: source.mode || 'automatic',
      expanded: true
    })

    contentDiv.innerHTML = `
      ${editionModeRadioHtml}
      ${sourceImageModeRadioHtml}
    `

    // === 事件监听设置 ===

    // 1. Edition mode
    setupRadioContainer('windows-edition-mode-container', 'edition-mode', (value) => {
      // 将UI的值映射回配置的mode
      let mode: 'interactive' | 'firmware' | 'key' | 'index' | 'name' = 'interactive'
      if (value === 'generic') {
        mode = 'name' // 默认使用name模式
      } else if (value === 'custom') {
        mode = 'key'
      } else {
        mode = value as 'interactive' | 'firmware'
      }
      this.updateModule('windowsEdition', { mode })
      this.renderWindowsEditionAndSource()
    }, true)

    // 2. Generic edition select (嵌套)
    if (edition.mode === 'index' || edition.mode === 'name' || edition.mode === 'generic') {
      setupComboCard('config-windows-edition-card', (value) => {
        this.updateModule('windowsEdition', { editionName: value as string, mode: 'name' })
      })
    }

    // 3. Custom product key (嵌套)
    if (edition.mode === 'key') {
      setupComboCard('config-product-key-card', (value) => {
        this.updateModule('windowsEdition', { productKey: value as string })
      })
    }

    // 4. Source image mode
    setupRadioContainer('source-image-mode-container', 'source-image-mode', (value) => {
      this.updateModule('sourceImage', { mode: value as 'automatic' | 'index' | 'name' })
      this.renderWindowsEditionAndSource()
    }, true)

    // 5. Source image index (嵌套)
    if (source.mode === 'index') {
      setupComboCard('config-source-image-index-card', (value) => {
        this.updateModule('sourceImage', { imageIndex: parseInt(value as string) || 1 })
      })
    }

    // 6. Source image name (嵌套)
    if (source.mode === 'name') {
      setupComboCard('config-source-image-name-card', (value) => {
        this.updateModule('sourceImage', { imageName: value as string })
      })
    }

    // 初始化图标
    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块11: User accounts (已合并到 renderNameAndAccount)
  private renderUserAccounts() {
    const contentDiv = this.getSectionContent('config-user-accounts')
    if (!contentDiv) return

    const accounts = this.config.accountSettings

    contentDiv.innerHTML = `
      <div class="card">
        <div class="card-left">
          <div class="card-content">
            <div class="card-title">Account mode</div>
            <div class="radio-group" data-name="account-mode" style="display: flex; gap: 20px; margin-top: 10px; flex-direction: column;">
              <fluent-radio name="account-mode" value="interactive-microsoft" ${accounts.mode === 'interactive-microsoft' ? 'checked' : ''}>Select account settings interactively (Microsoft account)</fluent-radio>
              <fluent-radio name="account-mode" value="interactive-local" ${accounts.mode === 'interactive-local' ? 'checked' : ''}>Select account settings interactively (Local account)</fluent-radio>
              <fluent-radio name="account-mode" value="unattended" ${accounts.mode === 'unattended' ? 'checked' : ''}>Create user accounts unattended</fluent-radio>
            </div>
          </div>
        </div>
      </div>
      ${accounts.mode === 'unattended' ? `
        <div class="card-expandable expanded">
          <div class="card-expandable-header">
            <div class="card-expandable-header-left">
              <div class="card-expandable-title">User accounts</div>
            </div>
            <div class="card-expandable-arrow">
              <i data-lucide="chevron-down"></i>
            </div>
          </div>
          <div class="card-expandable-content">
            <div id="config-accounts-list" style="display: flex; flex-direction: column; gap: 12px;">
              ${(accounts.accounts || []).map((acc, idx) => `
                <div class="card" style="background: var(--bg-primary);">
                  <div class="card-content" style="width: 100%;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr auto; gap: 12px; align-items: end;">
                      <div>
                        <label style="display: block; margin-bottom: 6px; font-size: 12px;">Account name:</label>
                        <fluent-text-field class="account-name" data-index="${idx}" value="${acc.name}" style="width: 100%;"></fluent-text-field>
                      </div>
                      <div>
                        <label style="display: block; margin-bottom: 6px; font-size: 12px;">Display name:</label>
                        <fluent-text-field class="account-display-name" data-index="${idx}" value="${acc.displayName}" style="width: 100%;"></fluent-text-field>
                      </div>
                      <div>
                        <label style="display: block; margin-bottom: 6px; font-size: 12px;">Password:</label>
                        <fluent-text-field class="account-password" data-index="${idx}" type="password" value="${acc.password}" style="width: 100%;"></fluent-text-field>
                      </div>
                      <div>
                        <label style="display: block; margin-bottom: 6px; font-size: 12px;">Group:</label>
                        <fluent-select class="account-group" data-index="${idx}" style="width: 100%;">
                          <fluent-option value="Administrators" ${acc.group === 'Administrators' ? 'selected' : ''}>Administrators</fluent-option>
                          <fluent-option value="Users" ${acc.group === 'Users' ? 'selected' : ''}>Users</fluent-option>
                        </fluent-select>
                      </div>
                      <fluent-button class="account-remove" data-index="${idx}" appearance="stealth">Remove</fluent-button>
                    </div>
                  </div>
                </div>
              `).join('')}
            </div>
            <div style="margin-top: 12px;">
              <fluent-button id="config-add-account" appearance="outline">Add account</fluent-button>
            </div>
            <div style="margin-top: 16px;">
              <div class="card-title">Auto logon</div>
              <div class="radio-group" data-name="auto-logon-mode" style="display: flex; gap: 20px; margin-top: 10px; flex-direction: column;">
                <fluent-radio name="auto-logon-mode" value="none" ${accounts.autoLogonMode === 'none' ? 'checked' : ''}>Do not auto logon</fluent-radio>
                <fluent-radio name="auto-logon-mode" value="builtin" ${accounts.autoLogonMode === 'builtin' ? 'checked' : ''}>Auto logon as built-in Administrator</fluent-radio>
                <fluent-radio name="auto-logon-mode" value="own" ${accounts.autoLogonMode === 'own' ? 'checked' : ''}>Auto logon as own account</fluent-radio>
              </div>
              ${accounts.autoLogonMode === 'builtin' ? `
                <div style="margin-top: 12px;">
                  <label style="display: block; margin-bottom: 6px; font-weight: 600;">Password:</label>
                  <fluent-text-field id="config-auto-logon-password" type="password" value="${accounts.autoLogonPassword || ''}" style="width: 100%;"></fluent-text-field>
                </div>
              ` : ''}
            </div>
            <div style="margin-top: 16px;">
              <fluent-checkbox id="config-obscure-passwords" ${accounts.obscurePasswords ? 'checked' : ''}>Obscure passwords</fluent-checkbox>
            </div>
          </div>
        </div>
      ` : ''}
    `

    contentDiv.querySelectorAll('fluent-radio[name="account-mode"]').forEach(radio => {
      (radio as any).addEventListener('change', () => {
        const selectedRadio = contentDiv.querySelector('fluent-radio[name="account-mode"][checked]') as any
        if (selectedRadio) {
          this.updateModule('accountSettings', { mode: selectedRadio.value })
          this.renderUserAccounts()
        }
      })
    })

    if (accounts.mode === 'unattended') {
      // 添加账户
      const addBtn = contentDiv.querySelector('#config-add-account')
      if (addBtn) {
        addBtn.addEventListener('click', () => {
          const accs = accounts.accounts || []
          accs.push({ name: '', displayName: '', password: '', group: 'Users' })
          this.updateModule('accountSettings', { accounts: accs })
          this.renderUserAccounts()
        })
      }

      // 移除账户
      contentDiv.querySelectorAll('.account-remove').forEach(btn => {
        btn.addEventListener('click', (e: any) => {
          const idx = parseInt(e.target.closest('[data-index]').dataset.index)
          const accs = [...(accounts.accounts || [])]
          accs.splice(idx, 1)
          this.updateModule('accountSettings', { accounts: accs })
          this.renderUserAccounts()
        })
      })

      // 更新账户字段
      contentDiv.querySelectorAll('.account-name, .account-display-name, .account-password').forEach(field => {
        field.addEventListener('input', (e: any) => {
          const idx = parseInt(e.target.dataset.index)
          const accs = [...(accounts.accounts || [])]
          const fieldType = e.target.classList.contains('account-name') ? 'name' :
            e.target.classList.contains('account-display-name') ? 'displayName' : 'password'
          accs[idx] = { ...accs[idx], [fieldType]: e.target.value }
          this.updateModule('accountSettings', { accounts: accs })
        })
      })

      contentDiv.querySelectorAll('.account-group').forEach(select => {
        select.addEventListener('change', (e: any) => {
          const idx = parseInt(e.target.dataset.index)
          const accs = [...(accounts.accounts || [])]
          accs[idx] = { ...accs[idx], group: e.target.value }
          this.updateModule('accountSettings', { accounts: accs })
        })
      })

      // 自动登录
      contentDiv.querySelectorAll('fluent-radio[name="auto-logon-mode"]').forEach(radio => {
        (radio as any).addEventListener('change', () => {
          const selectedRadio = contentDiv.querySelector('fluent-radio[name="auto-logon-mode"][checked]') as any
          if (selectedRadio) {
            this.updateModule('accountSettings', { autoLogonMode: selectedRadio.value })
            this.renderUserAccounts()
          }
        })
      })

      const autoLogonPwd = contentDiv.querySelector('#config-auto-logon-password') as any
      if (autoLogonPwd) {
        autoLogonPwd.addEventListener('input', (e: any) => {
          this.updateModule('accountSettings', { autoLogonPassword: e.target.value })
        })
      }

      const obscureCheck = contentDiv.querySelector('#config-obscure-passwords') as any
      if (obscureCheck) {
        obscureCheck.addEventListener('change', () => {
          this.updateModule('accountSettings', { obscurePasswords: obscureCheck.checked })
        })
      }

      // 初始化图标
      if (window.lucide) {
        window.lucide.createIcons()
      }
    }
  }

  // 渲染模块12: Password expiration
  private renderPasswordExpiration() {
    const contentDiv = this.getSectionContent('config-password-expiration')
    if (!contentDiv) return

    const pe = this.config.passwordExpiration

    contentDiv.innerHTML = `
      <div class="card">
        <div class="card-left">
          <div class="card-content">
            <div class="card-title">Password expiration</div>
            <div class="radio-group" data-name="password-expiration-mode" style="display: flex; gap: 20px; margin-top: 10px; flex-direction: column;">
              <fluent-radio name="password-expiration-mode" value="default" ${pe.mode === 'default' ? 'checked' : ''}>Use default password expiration</fluent-radio>
              <fluent-radio name="password-expiration-mode" value="unlimited" ${pe.mode === 'unlimited' ? 'checked' : ''}>Unlimited password expiration</fluent-radio>
              <fluent-radio name="password-expiration-mode" value="custom" ${pe.mode === 'custom' ? 'checked' : ''}>Custom maximum password age (days)</fluent-radio>
            </div>
            ${pe.mode === 'custom' ? `
              <div style="margin-top: 12px;">
                <fluent-text-field id="config-password-max-age" type="number" value="${pe.maxAge || ''}" placeholder="Enter days" style="width: 100%;"></fluent-text-field>
              </div>
            ` : ''}
          </div>
        </div>
      </div>
    `

    contentDiv.querySelectorAll('fluent-radio[name="password-expiration-mode"]').forEach(radio => {
      (radio as any).addEventListener('change', () => {
        const selectedRadio = contentDiv.querySelector('fluent-radio[name="password-expiration-mode"][checked]') as any
        if (selectedRadio) {
          this.updateModule('passwordExpiration', { mode: selectedRadio.value })
          this.renderPasswordExpiration()
        }
      })
    })

    const maxAgeInput = contentDiv.querySelector('#config-password-max-age') as any
    if (maxAgeInput) {
      maxAgeInput.addEventListener('input', (e: any) => {
        this.updateModule('passwordExpiration', { maxAge: parseInt(e.target.value) || undefined })
      })
    }
  }

  // 渲染模块13: Account Lockout policy
  private renderAccountLockout() {
    const contentDiv = this.getSectionContent('config-account-lockout')
    if (!contentDiv) return

    const lockout = this.config.lockoutSettings

    contentDiv.innerHTML = `
      <div class="card">
        <div class="card-left">
          <div class="card-content">
            <div class="card-title">Account Lockout policy</div>
            <div style="display: flex; gap: 20px; margin-top: 10px; flex-direction: column;">
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="lockout-mode" value="default" ${lockout.mode === 'default' ? 'checked' : ''}>
                <span>Use default lockout policy</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="lockout-mode" value="disabled" ${lockout.mode === 'disabled' ? 'checked' : ''}>
                <span>Disable account lockout</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="lockout-mode" value="custom" ${lockout.mode === 'custom' ? 'checked' : ''}>
                <span>Custom lockout policy</span>
              </label>
            </div>
            ${lockout.mode === 'custom' ? `
              <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-top: 12px;">
                <div>
                  <label style="display: block; margin-bottom: 6px; font-size: 12px;">Lockout threshold:</label>
                  <fluent-text-field id="config-lockout-threshold" type="number" value="${lockout.lockoutThreshold || ''}" placeholder="Attempts" style="width: 100%;"></fluent-text-field>
                </div>
                <div>
                  <label style="display: block; margin-bottom: 6px; font-size: 12px;">Lockout duration (minutes):</label>
                  <fluent-text-field id="config-lockout-duration" type="number" value="${lockout.lockoutDuration || ''}" placeholder="Minutes" style="width: 100%;"></fluent-text-field>
                </div>
                <div>
                  <label style="display: block; margin-bottom: 6px; font-size: 12px;">Reset counter (minutes):</label>
                  <fluent-text-field id="config-lockout-reset" type="number" value="${lockout.resetLockoutCounter || ''}" placeholder="Minutes" style="width: 100%;"></fluent-text-field>
                </div>
              </div>
            ` : ''}
          </div>
        </div>
      </div>
    `

    contentDiv.querySelectorAll('input[name="lockout-mode"]').forEach(radio => {
      radio.addEventListener('change', (e: any) => {
        this.updateModule('lockoutSettings', { mode: e.target.value })
        this.renderAccountLockout()
      })
    })

    const thresholdInput = contentDiv.querySelector('#config-lockout-threshold') as any
    if (thresholdInput) {
      thresholdInput.addEventListener('input', (e: any) => {
        this.updateModule('lockoutSettings', { lockoutThreshold: parseInt(e.target.value) || undefined })
      })
    }

    const durationInput = contentDiv.querySelector('#config-lockout-duration') as any
    if (durationInput) {
      durationInput.addEventListener('input', (e: any) => {
        this.updateModule('lockoutSettings', { lockoutDuration: parseInt(e.target.value) || undefined })
      })
    }

    const resetInput = contentDiv.querySelector('#config-lockout-reset') as any
    if (resetInput) {
      resetInput.addEventListener('input', (e: any) => {
        this.updateModule('lockoutSettings', { resetLockoutCounter: parseInt(e.target.value) || undefined })
      })
    }
  }

  // 渲染模块14: File Explorer tweaks
  private renderFileExplorer() {
    const contentDiv = this.getSectionContent('config-file-explorer')
    if (!contentDiv) return

    const fe = this.config.fileExplorerTweaks

    contentDiv.innerHTML = `
      <div class="card">
        <div class="card-left">
          <div class="card-content">
            <div class="card-title">${t('isoConfig.uiPersonalization.fileExplorer')}</div>
            <div style="display: flex; flex-direction: column; gap: 12px; margin-top: 10px;">
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" ${fe.showFileExtensions ? 'checked' : ''}>
                <span>${t('isoConfig.uiPersonalization.showFileExtensions')}</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" ${fe.showAllTrayIcons ? 'checked' : ''}>
                <span>${t('isoConfig.uiPersonalization.showAllTrayIcons')}</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" ${fe.hideEdgeFre ? 'checked' : ''}>
                <span>${t('isoConfig.uiPersonalization.hideEdgeFre')}</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" ${fe.disableEdgeStartupBoost ? 'checked' : ''}>
                <span>${t('isoConfig.uiPersonalization.disableEdgeStartupBoost')}</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" ${fe.makeEdgeUninstallable ? 'checked' : ''}>
                <span>${t('isoConfig.uiPersonalization.makeEdgeUninstallable')}</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" ${fe.deleteEdgeDesktopIcon ? 'checked' : ''}>
                <span>${t('isoConfig.uiPersonalization.deleteEdgeDesktopIcon')}</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" ${fe.launchToThisPC ? 'checked' : ''}>
                <span>${t('isoConfig.uiPersonalization.launchToThisPC')}</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" ${fe.disableBingResults ? 'checked' : ''}>
                <span>${t('isoConfig.uiPersonalization.disableBingResults')}</span>
              </label>
              <div>
                <label style="display: block; margin-bottom: 6px; font-weight: 600;">${t('isoConfig.uiPersonalization.hideFiles')}</label>
                <fluent-select id="config-hide-files" style="width: 100%;">
                  <fluent-option value="hidden" ${fe.hideFiles === 'hidden' ? 'selected' : ''}>${t('isoConfig.uiPersonalization.hidden')}</fluent-option>
                  <fluent-option value="show" ${fe.hideFiles === 'show' ? 'selected' : ''}>${t('isoConfig.uiPersonalization.show')}</fluent-option>
                </fluent-select>
              </div>
            </div>
          </div>
        </div>
      </div>
    `

    const checkboxes = contentDiv.querySelectorAll('input[type="checkbox"]')
    const keys: (keyof FileExplorerTweaks)[] = [
      'showFileExtensions', 'showAllTrayIcons', 'hideEdgeFre',
      'disableEdgeStartupBoost', 'makeEdgeUninstallable', 'deleteEdgeDesktopIcon',
      'launchToThisPC', 'disableBingResults'
    ]
    checkboxes.forEach((cb, i) => {
      cb.addEventListener('change', (e: any) => {
        this.updateModule('fileExplorerTweaks', { [keys[i]]: e.target.checked })
      })
    })

    const hideFilesSelect = contentDiv.querySelector('#config-hide-files') as any
    if (hideFilesSelect) {
      hideFilesSelect.addEventListener('change', (e: any) => {
        this.updateModule('fileExplorerTweaks', { hideFiles: e.target.value })
      })
    }
  }

  // 渲染模块15: Start menu and taskbar
  private renderStartTaskbar() {
    const contentDiv = this.getSectionContent('config-start-taskbar')
    if (!contentDiv) return

    const st = this.config.startMenuTaskbar

    contentDiv.innerHTML = `
      <div class="card-expandable expanded">
        <div class="card-expandable-header">
          <div class="card-expandable-header-left">
            <div class="card-expandable-title">${t('isoConfig.uiPersonalization.startTaskbar')}</div>
          </div>
          <div class="card-expandable-arrow">
            <i data-lucide="chevron-down"></i>
          </div>
        </div>
        <div class="card-expandable-content">
          <div style="display: flex; flex-direction: column; gap: 12px;">
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" ${st.leftTaskbar ? 'checked' : ''}>
              <span>${t('isoConfig.uiPersonalization.leftTaskbar')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" ${st.hideTaskViewButton ? 'checked' : ''}>
              <span>${t('isoConfig.uiPersonalization.hideTaskViewButton')}</span>
            </label>
            <div>
              <label style="display: block; margin-bottom: 6px; font-weight: 600;">${t('isoConfig.uiPersonalization.taskbarSearch')}</label>
              <fluent-select id="config-taskbar-search" style="width: 100%;">
                <fluent-option value="hide" ${st.taskbarSearch === 'hide' ? 'selected' : ''}>${t('isoConfig.uiPersonalization.searchHide')}</fluent-option>
                <fluent-option value="icon" ${st.taskbarSearch === 'icon' ? 'selected' : ''}>${t('isoConfig.uiPersonalization.searchIcon')}</fluent-option>
                <fluent-option value="box" ${st.taskbarSearch === 'box' ? 'selected' : ''}>${t('isoConfig.uiPersonalization.searchBox')}</fluent-option>
                <fluent-option value="label" ${st.taskbarSearch === 'label' ? 'selected' : ''}>${t('isoConfig.uiPersonalization.searchLabel')}</fluent-option>
              </fluent-select>
            </div>
          </div>
        </div>
      </div>
    `

    const leftTaskbarCheck = contentDiv.querySelector('input[type="checkbox"]') as HTMLInputElement
    if (leftTaskbarCheck) {
      leftTaskbarCheck.addEventListener('change', (e: any) => {
        this.updateModule('startMenuTaskbar', { leftTaskbar: e.target.checked })
      })
    }

    const hideTaskViewCheck = contentDiv.querySelectorAll('input[type="checkbox"]')[1] as HTMLInputElement
    if (hideTaskViewCheck) {
      hideTaskViewCheck.addEventListener('change', (e: any) => {
        this.updateModule('startMenuTaskbar', { hideTaskViewButton: e.target.checked })
      })
    }

    const searchSelect = contentDiv.querySelector('#config-taskbar-search') as any
    if (searchSelect) {
      searchSelect.addEventListener('change', (e: any) => {
        this.updateModule('startMenuTaskbar', { taskbarSearch: e.target.value })
      })
    }

    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块16: System tweaks
  // 渲染模块10: System Optimization (合并System tweaks、Remove bloatware、Express settings)
  private renderSystemOptimization() {
    const contentDiv = this.getSectionContent('config-system-optimization')
    if (!contentDiv) return

    const tweaks = this.config.systemTweaks
    const bloatware = this.config.bloatware
    const express = this.config.expressSettings
    const preset = this.getPresetData()

    contentDiv.innerHTML = `
      <div class="card-expandable expanded">
        <div class="card-expandable-header">
          <div class="card-expandable-header-left">
            <i data-lucide="settings" class="card-icon"></i>
            <div class="card-expandable-title">${t('isoConfig.systemOptimization.systemTweaks')}</div>
          </div>
          <div class="card-expandable-arrow">
            <i data-lucide="chevron-down"></i>
          </div>
        </div>
        <div class="card-expandable-content">
          <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 12px;">
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="enableLongPaths" ${tweaks.enableLongPaths ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.enableLongPaths')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="enableRemoteDesktop" ${tweaks.enableRemoteDesktop ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.enableRemoteDesktop')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="hardenSystemDriveAcl" ${tweaks.hardenSystemDriveAcl ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.hardenSystemDriveAcl')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="deleteJunctions" ${tweaks.deleteJunctions ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.deleteJunctions')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="allowPowerShellScripts" ${tweaks.allowPowerShellScripts ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.allowPowerShellScripts')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableLastAccess" ${tweaks.disableLastAccess ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.disableLastAccess')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="preventAutomaticReboot" ${tweaks.preventAutomaticReboot ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.preventAutomaticReboot')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableDefender" ${tweaks.disableDefender ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.disableDefender')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableSac" ${tweaks.disableSac ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.disableSac')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableUac" ${tweaks.disableUac ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.disableUac')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableSmartScreen" ${tweaks.disableSmartScreen ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.disableSmartScreen')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableSystemRestore" ${tweaks.disableSystemRestore ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.disableSystemRestore')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableFastStartup" ${tweaks.disableFastStartup ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.disableFastStartup')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="turnOffSystemSounds" ${tweaks.turnOffSystemSounds ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.turnOffSystemSounds')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableAppSuggestions" ${tweaks.disableAppSuggestions ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.disableAppSuggestions')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableWidgets" ${tweaks.disableWidgets ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.disableWidgets')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="preventDeviceEncryption" ${tweaks.preventDeviceEncryption ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.preventDeviceEncryption')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="classicContextMenu" ${tweaks.classicContextMenu ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.classicContextMenu')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableWindowsUpdate" ${tweaks.disableWindowsUpdate ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.disableWindowsUpdate')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disablePointerPrecision" ${tweaks.disablePointerPrecision ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.disablePointerPrecision')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="deleteWindowsOld" ${tweaks.deleteWindowsOld ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.deleteWindowsOld')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableCoreIsolation" ${tweaks.disableCoreIsolation ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.disableCoreIsolation')}</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="showEndTask" ${tweaks.showEndTask ? 'checked' : ''}>
              <span>${t('isoConfig.systemOptimization.showEndTask')}</span>
            </label>
          </div>
        </div>
      </div>
      
      <div class="card-expandable expanded">
        <div class="card-expandable-header">
          <div class="card-expandable-header-left">
            <i data-lucide="trash-2" class="card-icon"></i>
            <div class="card-expandable-title">${t('isoConfig.systemOptimization.removeBloatware')}</div>
          </div>
          <div class="card-expandable-arrow">
            <i data-lucide="chevron-down"></i>
          </div>
        </div>
        <div class="card-expandable-content">
          <div style="display: flex; gap: 10px; margin-bottom: 12px;">
            <fluent-button id="config-bloatware-select-all" appearance="outline">${t('common.selectAll')}</fluent-button>
            <fluent-button id="config-bloatware-deselect-all" appearance="outline">${t('common.deselectAll')}</fluent-button>
          </div>
          <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px;">
            ${preset.bloatwareItems.map(item => `
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" class="bloatware-item" value="${item}" ${bloatware.items.includes(item) ? 'checked' : ''}>
                <span>${item}</span>
              </label>
            `).join('')}
          </div>
        </div>
      </div>
      
      <div class="card">
        <div class="card-left">
          <i data-lucide="shield-check" class="card-icon"></i>
          <div class="card-content">
            <div class="card-title">${t('isoConfig.systemOptimization.expressSettings')}</div>
            <div style="display: flex; gap: 20px; margin-top: 10px;">
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="express-settings-mode" value="interactive" ${express === 'interactive' ? 'checked' : ''}>
                <span>${t('isoConfig.systemOptimization.expressInteractive')}</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="express-settings-mode" value="enableAll" ${express === 'enableAll' ? 'checked' : ''}>
                <span>${t('isoConfig.systemOptimization.expressEnableAll')}</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="express-settings-mode" value="disableAll" ${express === 'disableAll' ? 'checked' : ''}>
                <span>${t('isoConfig.systemOptimization.expressDisableAll')}</span>
              </label>
            </div>
          </div>
        </div>
      </div>
    `

    // System tweaks事件监听
    contentDiv.querySelectorAll('.tweak-checkbox').forEach(cb => {
      cb.addEventListener('change', (e: any) => {
        const key = e.target.dataset.key
        this.updateModule('systemTweaks', { [key]: e.target.checked })
      })
    })

    // Bloatware事件监听
    const selectAllBtn = contentDiv.querySelector('#config-bloatware-select-all')
    const deselectAllBtn = contentDiv.querySelector('#config-bloatware-deselect-all')
    const bloatwareCheckboxes = contentDiv.querySelectorAll('.bloatware-item')

    if (selectAllBtn) {
      selectAllBtn.addEventListener('click', () => {
        const allItems = preset.bloatwareItems.map(i => i)
        this.updateModule('bloatware', { items: allItems })
        this.renderSystemOptimization()
      })
    }

    if (deselectAllBtn) {
      deselectAllBtn.addEventListener('click', () => {
        this.updateModule('bloatware', { items: [] })
        this.renderSystemOptimization()
      })
    }

    bloatwareCheckboxes.forEach(cb => {
      cb.addEventListener('change', (e: any) => {
        const item = e.target.value
        const items = [...bloatware.items]
        if (e.target.checked) {
          if (!items.includes(item)) items.push(item)
        } else {
          const idx = items.indexOf(item)
          if (idx > -1) items.splice(idx, 1)
        }
        this.updateModule('bloatware', { items })
      })
    })

    // Express settings事件监听
    contentDiv.querySelectorAll('input[name="express-settings-mode"]').forEach(radio => {
      radio.addEventListener('change', (e: any) => {
        this.updateConfig({ expressSettings: e.target.value as ExpressSettingsMode })
      })
    })

    // 初始化图标
    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块17: Visual effects
  private renderVisualEffects() {
    const contentDiv = this.getSectionContent('config-visual-effects')
    if (!contentDiv) return
    contentDiv.innerHTML = `
      <div class="card">
        <div class="card-left">
          <div class="card-content">
            <div class="card-title">${t('isoConfig.uiPersonalization.visualEffects')}</div>
            <div class="card-description" style="margin-top: 8px;">${t('isoConfig.uiPersonalization.visualEffectsDesc')}</div>
          </div>
        </div>
      </div>
    `
  }

  // 渲染模块18: Desktop icons
  private renderDesktopIcons() {
    const contentDiv = this.getSectionContent('config-desktop-icons')
    if (!contentDiv) return

    const icons = this.config.desktopIcons

    contentDiv.innerHTML = `
      <div class="card">
        <div class="card-left">
          <div class="card-content">
            <div class="card-title">${t('isoConfig.uiPersonalization.desktopIcons')}</div>
            <div style="display: flex; gap: 20px; margin-top: 10px;">
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="desktop-icons-mode" value="default" ${icons.mode === 'default' ? 'checked' : ''}>
                <span>${t('isoConfig.uiPersonalization.defaultIcons')}</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="desktop-icons-mode" value="custom" ${icons.mode === 'custom' ? 'checked' : ''}>
                <span>${t('isoConfig.uiPersonalization.customIcons')}</span>
              </label>
            </div>
          </div>
        </div>
      </div>
    `

    contentDiv.querySelectorAll('input[name="desktop-icons-mode"]').forEach(radio => {
      radio.addEventListener('change', (e: any) => {
        this.updateModule('desktopIcons', { mode: e.target.value })
      })
    })
  }

  // 渲染模块19: Folders on Start
  private renderFoldersStart() {
    const contentDiv = this.getSectionContent('config-folders-start')
    if (!contentDiv) return

    // const folders = this.config.startFolders // TODO: 实现文件夹选择功能

    contentDiv.innerHTML = `
      <div class="card">
        <div class="card-left">
          <div class="card-content">
            <div class="card-title">${t('isoConfig.uiPersonalization.foldersStart')}</div>
            <div class="card-description" style="margin-top: 8px;">${t('isoConfig.uiPersonalization.foldersStartDesc')}</div>
          </div>
        </div>
      </div>
    `
  }

  // 渲染模块21: WLAN / Wi-Fi setup
  private renderWifi() {
    const contentDiv = this.getSectionContent('config-wifi')
    if (!contentDiv) return

    const wifi = this.config.wifi

    // 1. Wi-Fi Mode - RadioContainer (带嵌套)
    const wifiModeRadioHtml = createRadioContainer({
      id: 'wifi-mode-container',
      name: 'wifi-mode',
      title: t('isoConfig.wifi.title'),
      description: '',
      icon: 'wifi',
      options: [
        {
          value: 'interactive',
          label: t('isoConfig.wifi.interactive'),
          description: ''
        },
        {
          value: 'skip',
          label: t('isoConfig.wifi.skip'),
          description: t('isoConfig.wifi.skipDesc')
        },
        {
          value: 'unattended',
          label: t('isoConfig.wifi.unattended'),
          description: `${t('isoConfig.wifi.wpa3Note')}\n${t('isoConfig.wifi.passwordNote')}`,
          nestedCards: [
            {
              id: 'config-wifi-ssid-card',
              title: t('isoConfig.wifi.ssid'),
              description: '',
              controlType: 'text',
              value: wifi.ssid || '',
              placeholder: 'WLAN-123456',
              borderless: true
            },
            {
              id: 'config-wifi-auth-card',
              title: t('isoConfig.wifi.authentication'),
              description: '',
              controlType: 'select',
              value: wifi.authentication || 'Open',
              options: [
                { value: 'Open', label: t('isoConfig.wifi.authOpen') },
                { value: 'WPA2PSK', label: t('isoConfig.wifi.authWPA2') },
                { value: 'WPA3SAE', label: t('isoConfig.wifi.authWPA3') }
              ],
              borderless: true
            },
            {
              id: 'config-wifi-password-card',
              title: t('isoConfig.nameAccount.password'),
              description: '',
              controlType: 'text',
              value: wifi.password || '00000000',
              placeholder: 'password',
              borderless: true
            },
            {
              id: 'config-wifi-non-broadcast-card',
              title: t('isoConfig.wifi.nonBroadcast'),
              description: '',
              controlType: 'checkbox',
              value: wifi.nonBroadcast || false,
              borderless: true
            }
          ]
        },
        {
          value: 'fromProfile',
          label: t('isoConfig.wifi.fromProfile'),
          description: '',
          nestedCards: [
            {
              id: 'config-wifi-profile-xml-card',
              title: t('isoConfig.wifi.profileXml'),
              description: '',
              icon: 'code',
              value: wifi.profileXml || '',
              placeholder: `<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
  <name>WLAN-123456</name>
  <SSIDConfig>
    <SSID>
      <hex>574C414E2D313233343536</hex>
      <name>WLAN-123456</name>
    </SSID>
    <nonBroadcast>true</nonBroadcast>
  </SSIDConfig>
  <connectionType>ESS</connectionType>
  <connectionMode>auto</connectionMode>
  <MSM>
    <security>
      <authEncryption>
        <authentication>WPA3SAE</authentication>
        <encryption>AES</encryption>
        <useOneX>false</useOneX>
        <transitionMode xmlns="http://www.microsoft.com/networking/WLAN/profile/v4">true</transitionMode>
      </authEncryption>
      <sharedKey>
        <keyType>passPhrase</keyType>
        <protected>false</protected>
        <keyMaterial>password</keyMaterial>
      </sharedKey>
    </security>
  </MSM>
</WLANProfile>`,
              rows: 29,
              borderless: true,
              showImportExport: true
            } as any
          ]
        }
      ],
      selectedValue: wifi.mode || 'interactive',
      expanded: true
    })

    contentDiv.innerHTML = `
      ${wifiModeRadioHtml}
    `

    // === 事件监听设置 ===

    // 1. Wi-Fi mode
    setupRadioContainer('wifi-mode-container', 'wifi-mode', (value) => {
      this.updateModule('wifi', { mode: value as 'interactive' | 'skip' | 'unattended' | 'fromProfile' })
      this.renderWifi()
    }, true)

    // 2. Unattended 设置 (嵌套)
    if (wifi.mode === 'unattended') {
      setupComboCard('config-wifi-ssid-card', (value) => {
        this.updateModule('wifi', { ssid: value as string })
      })

      setupComboCard('config-wifi-auth-card', (value) => {
        this.updateModule('wifi', { authentication: value as 'Open' | 'WPA2PSK' | 'WPA3SAE' })
      })

      setupComboCard('config-wifi-password-card', (value) => {
        this.updateModule('wifi', { password: value as string })
      })

      setupComboCard('config-wifi-non-broadcast-card', (value) => {
        this.updateModule('wifi', { nonBroadcast: value as boolean })
      })
    }

    // 3. FromProfile 设置 (嵌套)
    if (wifi.mode === 'fromProfile') {
      setupTextCard('config-wifi-profile-xml-card', (value) => {
        this.updateModule('wifi', { profileXml: value })
      }, async () => {
        // 导入 XML
        if (window.electronAPI?.showOpenDialog) {
          const result = await window.electronAPI.showOpenDialog({
            filters: [{ name: 'XML Files', extensions: ['xml', 'txt'] }],
            properties: ['openFile']
          })
          if (!result.canceled && result.filePaths?.[0] && window.electronAPI?.readFile) {
            const content = await window.electronAPI.readFile(result.filePaths[0])
            setTextCardValue('config-wifi-profile-xml-card', content)
            this.updateModule('wifi', { profileXml: content })
          }
        }
      }, async () => {
        // 导出 XML
        if (window.electronAPI?.showSaveDialog) {
          const result = await window.electronAPI.showSaveDialog({
            filters: [{ name: 'XML Files', extensions: ['xml'] }],
            defaultPath: 'wlan-profile.xml'
          })
          if (!result.canceled && result.filePath && window.electronAPI?.writeFile) {
            const currentValue = getTextCardValue('config-wifi-profile-xml-card', true)
            await window.electronAPI.writeFile(result.filePath, currentValue)
          }
        }
      })
    }

    // 初始化图标
    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块23: Lock key settings
  private renderLockKeys() {
    const contentDiv = this.getSectionContent('config-lock-keys')
    if (!contentDiv) return

    const lockKeys = this.config.lockKeys

    contentDiv.innerHTML = `
      <div class="card">
        <div class="card-left">
          <div class="card-content">
            <div class="card-title">${t('isoConfig.accessibility.lockKeys')}</div>
            <div style="display: flex; gap: 20px; margin-top: 10px; flex-direction: column;">
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="lock-keys-mode" value="skip" ${lockKeys.mode === 'skip' ? 'checked' : ''}>
                <span>${t('isoConfig.accessibility.lockKeysSkip')}</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="lock-keys-mode" value="configure" ${lockKeys.mode === 'configure' ? 'checked' : ''}>
                <span>${t('isoConfig.accessibility.lockKeysConfigure')}</span>
              </label>
            </div>
          </div>
        </div>
      </div>
      ${lockKeys.mode === 'configure' ? `
        <div class="card-expandable expanded">
          <div class="card-expandable-header">
            <div class="card-expandable-header-left">
              <div class="card-expandable-title">${t('isoConfig.accessibility.lockKeyConfig')}</div>
            </div>
            <div class="card-expandable-arrow">
              <i data-lucide="chevron-down"></i>
            </div>
          </div>
          <div class="card-expandable-content">
            <div class="card-description">${t('isoConfig.accessibility.lockKeyConfigDesc')}</div>
          </div>
        </div>
      ` : ''}
    `

    contentDiv.querySelectorAll('input[name="lock-keys-mode"]').forEach(radio => {
      radio.addEventListener('change', (e: any) => {
        this.updateModule('lockKeys', { mode: e.target.value })
        this.renderLockKeys()
      })
    })

    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块24: Sticky keys
  private renderStickyKeys() {
    const contentDiv = this.getSectionContent('config-sticky-keys')
    if (!contentDiv) return

    const sticky = this.config.stickyKeys

    contentDiv.innerHTML = `
      <div class="card">
        <div class="card-left">
          <div class="card-content">
            <div class="card-title">${t('isoConfig.accessibility.stickyKeys')}</div>
            <div style="display: flex; gap: 20px; margin-top: 10px; flex-direction: column;">
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="sticky-keys-mode" value="default" ${sticky.mode === 'default' ? 'checked' : ''}>
                <span>${t('isoConfig.accessibility.stickyKeysDefault')}</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="sticky-keys-mode" value="disabled" ${sticky.mode === 'disabled' ? 'checked' : ''}>
                <span>${t('isoConfig.accessibility.stickyKeysDisabled')}</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="sticky-keys-mode" value="custom" ${sticky.mode === 'custom' ? 'checked' : ''}>
                <span>${t('isoConfig.accessibility.stickyKeysCustom')}</span>
              </label>
            </div>
          </div>
        </div>
      </div>
    `

    contentDiv.querySelectorAll('input[name="sticky-keys-mode"]').forEach(radio => {
      radio.addEventListener('change', (e: any) => {
        this.updateModule('stickyKeys', { mode: e.target.value })
      })
    })
  }

  // 渲染模块25: Personalization settings
  private renderPersonalization() {
    const contentDiv = this.getSectionContent('config-personalization')
    if (!contentDiv) return

    const pers = this.config.personalization

    contentDiv.innerHTML = `
      <div class="card-expandable expanded">
        <div class="card-expandable-header">
          <div class="card-expandable-header-left">
            <div class="card-expandable-title">${t('isoConfig.uiPersonalization.personalization')}</div>
          </div>
          <div class="card-expandable-arrow">
            <i data-lucide="chevron-down"></i>
          </div>
        </div>
        <div class="card-expandable-content">
          <div style="display: flex; flex-direction: column; gap: 16px;">
            <div>
              <div class="card-title">${t('isoConfig.uiPersonalization.wallpaper')}</div>
              <div style="display: flex; gap: 20px; margin-top: 10px; flex-direction: column;">
                <label style="display: flex; align-items: center; gap: 8px;">
                  <input type="radio" name="wallpaper-mode" value="default" ${pers.wallpaperMode === 'default' ? 'checked' : ''}>
                  <span>${t('isoConfig.uiPersonalization.wallpaperDefault')}</span>
                </label>
                <label style="display: flex; align-items: center; gap: 8px;">
                  <input type="radio" name="wallpaper-mode" value="solid" ${pers.wallpaperMode === 'solid' ? 'checked' : ''}>
                  <span>${t('isoConfig.uiPersonalization.wallpaperSolid')}</span>
                </label>
                <label style="display: flex; align-items: center; gap: 8px;">
                  <input type="radio" name="wallpaper-mode" value="script" ${pers.wallpaperMode === 'script' ? 'checked' : ''}>
                  <span>${t('isoConfig.uiPersonalization.wallpaperScript')}</span>
                </label>
              </div>
              ${pers.wallpaperMode === 'solid' ? `
                <div style="margin-top: 12px;">
                  <label style="display: block; margin-bottom: 6px; font-weight: 600;">${t('isoConfig.uiPersonalization.wallpaperColor')}</label>
                  <fluent-text-field id="config-wallpaper-color" value="${pers.wallpaperColor || '#000000'}" placeholder="#000000" style="width: 100%;"></fluent-text-field>
                </div>
              ` : ''}
              ${pers.wallpaperMode === 'script' ? `
                <div style="margin-top: 12px;">
                  <label style="display: block; margin-bottom: 6px; font-weight: 600;">${t('isoConfig.uiPersonalization.wallpaperPsScript')}</label>
                  <textarea id="config-wallpaper-script" style="width: 100%; min-height: 100px; padding: 8px; font-family: monospace; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary);">${pers.wallpaperScript || ''}</textarea>
                </div>
              ` : ''}
            </div>
            <div>
              <div class="card-title">${t('isoConfig.uiPersonalization.lockScreen')}</div>
              <div style="display: flex; gap: 20px; margin-top: 10px; flex-direction: column;">
                <label style="display: flex; align-items: center; gap: 8px;">
                  <input type="radio" name="lockscreen-mode" value="default" ${pers.lockScreenMode === 'default' ? 'checked' : ''}>
                  <span>${t('isoConfig.uiPersonalization.lockScreenDefault')}</span>
                </label>
                <label style="display: flex; align-items: center; gap: 8px;">
                  <input type="radio" name="lockscreen-mode" value="script" ${pers.lockScreenMode === 'script' ? 'checked' : ''}>
                  <span>${t('isoConfig.uiPersonalization.lockScreenScript')}</span>
                </label>
              </div>
              ${pers.lockScreenMode === 'script' ? `
                <div style="margin-top: 12px;">
                  <label style="display: block; margin-bottom: 6px; font-weight: 600;">${t('isoConfig.uiPersonalization.lockScreenPsScript')}</label>
                  <textarea id="config-lockscreen-script" style="width: 100%; min-height: 100px; padding: 8px; font-family: monospace; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary);">${pers.lockScreenScript || ''}</textarea>
                </div>
              ` : ''}
            </div>
            <div>
              <div class="card-title">${t('isoConfig.uiPersonalization.color')}</div>
              <div style="display: flex; gap: 20px; margin-top: 10px; flex-direction: column;">
                <label style="display: flex; align-items: center; gap: 8px;">
                  <input type="radio" name="color-mode" value="default" ${pers.colorMode === 'default' ? 'checked' : ''}>
                  <span>${t('isoConfig.uiPersonalization.colorDefault')}</span>
                </label>
                <label style="display: flex; align-items: center; gap: 8px;">
                  <input type="radio" name="color-mode" value="custom" ${pers.colorMode === 'custom' ? 'checked' : ''}>
                  <span>${t('isoConfig.uiPersonalization.colorCustom')}</span>
                </label>
              </div>
              ${pers.colorMode === 'custom' ? `
                <div style="margin-top: 12px;">
                  <label style="display: block; margin-bottom: 6px; font-weight: 600;">${t('isoConfig.uiPersonalization.accentColor')}</label>
                  <fluent-text-field id="config-accent-color" value="${pers.accentColor || '#0078d4'}" placeholder="#0078d4" style="width: 100%;"></fluent-text-field>
                </div>
              ` : ''}
            </div>
          </div>
        </div>
      </div>
    `

    contentDiv.querySelectorAll('input[name="wallpaper-mode"]').forEach(radio => {
      radio.addEventListener('change', (e: any) => {
        this.updateModule('personalization', { wallpaperMode: e.target.value })
        this.renderPersonalization()
      })
    })

    contentDiv.querySelectorAll('input[name="lockscreen-mode"]').forEach(radio => {
      radio.addEventListener('change', (e: any) => {
        this.updateModule('personalization', { lockScreenMode: e.target.value })
        this.renderPersonalization()
      })
    })

    contentDiv.querySelectorAll('input[name="color-mode"]').forEach(radio => {
      radio.addEventListener('change', (e: any) => {
        this.updateModule('personalization', { colorMode: e.target.value })
        this.renderPersonalization()
      })
    })

    const wallpaperColorInput = contentDiv.querySelector('#config-wallpaper-color') as any
    if (wallpaperColorInput) {
      wallpaperColorInput.addEventListener('input', (e: any) => {
        this.updateModule('personalization', { wallpaperColor: e.target.value })
      })
    }

    const wallpaperScriptInput = contentDiv.querySelector('#config-wallpaper-script') as HTMLTextAreaElement
    if (wallpaperScriptInput) {
      wallpaperScriptInput.addEventListener('input', (e: any) => {
        this.updateModule('personalization', { wallpaperScript: e.target.value })
      })
    }

    const lockscreenScriptInput = contentDiv.querySelector('#config-lockscreen-script') as HTMLTextAreaElement
    if (lockscreenScriptInput) {
      lockscreenScriptInput.addEventListener('input', (e: any) => {
        this.updateModule('personalization', { lockScreenScript: e.target.value })
      })
    }

    const accentColorInput = contentDiv.querySelector('#config-accent-color') as any
    if (accentColorInput) {
      accentColorInput.addEventListener('input', (e: any) => {
        this.updateModule('personalization', { accentColor: e.target.value })
      })
    }

    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块26: Remove bloatware
  private renderBloatware() {
    const contentDiv = this.getSectionContent('config-bloatware')
    if (!contentDiv) return

    const bloatware = this.config.bloatware
    const preset = this.getPresetData()

    contentDiv.innerHTML = `
      <div class="card-expandable expanded">
        <div class="card-expandable-header">
          <div class="card-expandable-header-left">
            <div class="card-expandable-title">Remove bloatware</div>
          </div>
          <div class="card-expandable-arrow">
            <i data-lucide="chevron-down"></i>
          </div>
        </div>
        <div class="card-expandable-content">
          <div style="display: flex; gap: 10px; margin-bottom: 12px;">
            <fluent-button id="config-bloatware-select-all" appearance="outline">Select all</fluent-button>
            <fluent-button id="config-bloatware-deselect-all" appearance="outline">Deselect all</fluent-button>
          </div>
          <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px;">
            ${preset.bloatwareItems.map(item => `
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" class="bloatware-item" value="${item}" ${bloatware.items.includes(item) ? 'checked' : ''}>
                <span>${item}</span>
              </label>
            `).join('')}
          </div>
        </div>
      </div>
    `

    const selectAllBtn = contentDiv.querySelector('#config-bloatware-select-all')
    const deselectAllBtn = contentDiv.querySelector('#config-bloatware-deselect-all')
    const checkboxes = contentDiv.querySelectorAll('.bloatware-item')

    if (selectAllBtn) {
      selectAllBtn.addEventListener('click', () => {
        const allItems = preset.bloatwareItems.map(i => i)
        this.updateModule('bloatware', { items: allItems })
        this.renderBloatware()
      })
    }

    if (deselectAllBtn) {
      deselectAllBtn.addEventListener('click', () => {
        this.updateModule('bloatware', { items: [] })
        this.renderBloatware()
      })
    }

    checkboxes.forEach(cb => {
      cb.addEventListener('change', (e: any) => {
        const item = e.target.value
        const items = [...bloatware.items]
        if (e.target.checked) {
          if (!items.includes(item)) items.push(item)
        } else {
          const idx = items.indexOf(item)
          if (idx > -1) items.splice(idx, 1)
        }
        this.updateModule('bloatware', { items })
      })
    })

    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块27: Run custom scripts
  private renderCustomScripts() {
    const contentDiv = this.getSectionContent('config-custom-scripts')
    if (!contentDiv) return

    const scripts = this.config.scripts

    contentDiv.innerHTML = `
      <div class="card-expandable expanded">
        <div class="card-expandable-header">
          <div class="card-expandable-header-left">
            <div class="card-expandable-title">Run custom scripts</div>
          </div>
          <div class="card-expandable-arrow">
            <i data-lucide="chevron-down"></i>
          </div>
        </div>
        <div class="card-expandable-content">
          <div style="display: flex; flex-direction: column; gap: 20px;">
            <div>
              <div class="card-title">System scripts</div>
              <div class="card-description" style="margin-top: 6px;">These scripts will run in the system context, before user accounts are created.</div>
              <div id="config-system-scripts" style="margin-top: 12px;">
                ${scripts.system.map((s, idx) => `
                  <div class="card" style="background: var(--bg-primary); margin-bottom: 8px;">
                    <div class="card-content">
                      <div style="display: grid; grid-template-columns: 100px 1fr auto; gap: 12px; align-items: center;">
                        <fluent-select class="script-type" data-phase="system" data-index="${idx}" style="width: 100%;">
                          <fluent-option value=".reg" ${s.type === '.reg' ? 'selected' : ''}>.reg</fluent-option>
                          <fluent-option value=".cmd" ${s.type === '.cmd' ? 'selected' : ''}>.cmd</fluent-option>
                          <fluent-option value=".ps1" ${s.type === '.ps1' ? 'selected' : ''}>.ps1</fluent-option>
                          <fluent-option value=".vbs" ${s.type === '.vbs' ? 'selected' : ''}>.vbs</fluent-option>
                        </fluent-select>
                        <textarea class="script-content" data-phase="system" data-index="${idx}" style="width: 100%; min-height: 60px; padding: 8px; font-family: monospace; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary);">${s.content}</textarea>
                        <fluent-button class="script-remove" data-phase="system" data-index="${idx}" appearance="stealth">Remove</fluent-button>
                      </div>
                    </div>
                  </div>
                `).join('')}
                <fluent-button id="config-add-system-script" appearance="outline" style="margin-top: 8px;">Add script</fluent-button>
              </div>
            </div>
            <div>
              <div class="card-title">DefaultUser scripts</div>
              <div class="card-description" style="margin-top: 6px;">Use these scripts to modify the default user's registry hive.</div>
              <div id="config-defaultuser-scripts" style="margin-top: 12px;">
                ${scripts.defaultUser.map((s, idx) => `
                  <div class="card" style="background: var(--bg-primary); margin-bottom: 8px;">
                    <div class="card-content">
                      <div style="display: grid; grid-template-columns: 100px 1fr auto; gap: 12px; align-items: center;">
                        <fluent-select class="script-type" data-phase="defaultUser" data-index="${idx}" style="width: 100%;">
                          <fluent-option value=".reg" ${s.type === '.reg' ? 'selected' : ''}>.reg</fluent-option>
                          <fluent-option value=".cmd" ${s.type === '.cmd' ? 'selected' : ''}>.cmd</fluent-option>
                          <fluent-option value=".ps1" ${s.type === '.ps1' ? 'selected' : ''}>.ps1</fluent-option>
                        </fluent-select>
                        <textarea class="script-content" data-phase="defaultUser" data-index="${idx}" style="width: 100%; min-height: 60px; padding: 8px; font-family: monospace; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary);">${s.content}</textarea>
                        <fluent-button class="script-remove" data-phase="defaultUser" data-index="${idx}" appearance="stealth">Remove</fluent-button>
                      </div>
                    </div>
                  </div>
                `).join('')}
                <fluent-button id="config-add-defaultuser-script" appearance="outline" style="margin-top: 8px;">Add script</fluent-button>
              </div>
            </div>
            <div>
              <div class="card-title">FirstLogon scripts</div>
              <div class="card-description" style="margin-top: 6px;">These scripts will run when the first user logs on after Windows has been installed.</div>
              <div id="config-firstlogon-scripts" style="margin-top: 12px;">
                ${scripts.firstLogon.map((s, idx) => `
                  <div class="card" style="background: var(--bg-primary); margin-bottom: 8px;">
                    <div class="card-content">
                      <div style="display: grid; grid-template-columns: 100px 1fr auto; gap: 12px; align-items: center;">
                        <fluent-select class="script-type" data-phase="firstLogon" data-index="${idx}" style="width: 100%;">
                          <fluent-option value=".cmd" ${s.type === '.cmd' ? 'selected' : ''}>.cmd</fluent-option>
                          <fluent-option value=".ps1" ${s.type === '.ps1' ? 'selected' : ''}>.ps1</fluent-option>
                          <fluent-option value=".reg" ${s.type === '.reg' ? 'selected' : ''}>.reg</fluent-option>
                          <fluent-option value=".vbs" ${s.type === '.vbs' ? 'selected' : ''}>.vbs</fluent-option>
                        </fluent-select>
                        <textarea class="script-content" data-phase="firstLogon" data-index="${idx}" style="width: 100%; min-height: 60px; padding: 8px; font-family: monospace; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary);">${s.content}</textarea>
                        <fluent-button class="script-remove" data-phase="firstLogon" data-index="${idx}" appearance="stealth">Remove</fluent-button>
                      </div>
                    </div>
                  </div>
                `).join('')}
                <fluent-button id="config-add-firstlogon-script" appearance="outline" style="margin-top: 8px;">Add script</fluent-button>
              </div>
            </div>
            <div>
              <div class="card-title">UserOnce scripts</div>
              <div class="card-description" style="margin-top: 6px;">These scripts will run whenever a user logs on for the first time.</div>
              <div id="config-useronce-scripts" style="margin-top: 12px;">
                ${scripts.userOnce.map((s, idx) => `
                  <div class="card" style="background: var(--bg-primary); margin-bottom: 8px;">
                    <div class="card-content">
                      <div style="display: grid; grid-template-columns: 100px 1fr auto; gap: 12px; align-items: center;">
                        <fluent-select class="script-type" data-phase="userOnce" data-index="${idx}" style="width: 100%;">
                          <fluent-option value=".cmd" ${s.type === '.cmd' ? 'selected' : ''}>.cmd</fluent-option>
                          <fluent-option value=".ps1" ${s.type === '.ps1' ? 'selected' : ''}>.ps1</fluent-option>
                          <fluent-option value=".reg" ${s.type === '.reg' ? 'selected' : ''}>.reg</fluent-option>
                          <fluent-option value=".vbs" ${s.type === '.vbs' ? 'selected' : ''}>.vbs</fluent-option>
                        </fluent-select>
                        <textarea class="script-content" data-phase="userOnce" data-index="${idx}" style="width: 100%; min-height: 60px; padding: 8px; font-family: monospace; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary);">${s.content}</textarea>
                        <fluent-button class="script-remove" data-phase="userOnce" data-index="${idx}" appearance="stealth">Remove</fluent-button>
                      </div>
                    </div>
                  </div>
                `).join('')}
                <fluent-button id="config-add-useronce-script" appearance="outline" style="margin-top: 8px;">Add script</fluent-button>
              </div>
            </div>
            <div>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" id="config-restart-explorer" ${scripts.restartExplorer ? 'checked' : ''}>
                <span>Restart File Explorer after scripts have run</span>
              </label>
            </div>
          </div>
        </div>
      </div>
    `

    // 添加脚本按钮
    const addSystemBtn = contentDiv.querySelector('#config-add-system-script')
    const addDefaultUserBtn = contentDiv.querySelector('#config-add-defaultuser-script')
    const addFirstLogonBtn = contentDiv.querySelector('#config-add-firstlogon-script')
    const addUserOnceBtn = contentDiv.querySelector('#config-add-useronce-script')

    if (addSystemBtn) {
      addSystemBtn.addEventListener('click', () => {
        const sysScripts = [...scripts.system, { type: '.cmd', content: '' }]
        this.updateModule('scripts', { system: sysScripts })
        this.renderCustomScripts()
      })
    }

    if (addDefaultUserBtn) {
      addDefaultUserBtn.addEventListener('click', () => {
        const defUserScripts = [...scripts.defaultUser, { type: '.reg', content: '' }]
        this.updateModule('scripts', { defaultUser: defUserScripts })
        this.renderCustomScripts()
      })
    }

    if (addFirstLogonBtn) {
      addFirstLogonBtn.addEventListener('click', () => {
        const firstLogonScripts = [...scripts.firstLogon, { type: '.cmd', content: '' }]
        this.updateModule('scripts', { firstLogon: firstLogonScripts })
        this.renderCustomScripts()
      })
    }

    if (addUserOnceBtn) {
      addUserOnceBtn.addEventListener('click', () => {
        const userOnceScripts = [...scripts.userOnce, { type: '.cmd', content: '' }]
        this.updateModule('scripts', { userOnce: userOnceScripts })
        this.renderCustomScripts()
      })
    }

    // 移除脚本
    contentDiv.querySelectorAll('.script-remove').forEach(btn => {
      btn.addEventListener('click', (e: any) => {
        const phase = e.target.dataset.phase
        const idx = parseInt(e.target.dataset.index)
        const phaseScripts = [...scripts[phase as keyof ScriptSettings] as Array<{ type: string; content: string }>]
        phaseScripts.splice(idx, 1)
        this.updateModule('scripts', { [phase]: phaseScripts })
        this.renderCustomScripts()
      })
    })

    // 更新脚本类型和内容
    contentDiv.querySelectorAll('.script-type').forEach(select => {
      select.addEventListener('change', (e: any) => {
        const phase = e.target.dataset.phase
        const idx = parseInt(e.target.dataset.index)
        const phaseScripts = [...scripts[phase as keyof ScriptSettings] as Array<{ type: string; content: string }>]
        phaseScripts[idx] = { ...phaseScripts[idx], type: e.target.value }
        this.updateModule('scripts', { [phase]: phaseScripts })
      })
    })

    contentDiv.querySelectorAll('.script-content').forEach(textarea => {
      textarea.addEventListener('input', (e: any) => {
        const phase = e.target.dataset.phase
        const idx = parseInt(e.target.dataset.index)
        const phaseScripts = [...scripts[phase as keyof ScriptSettings] as Array<{ type: string; content: string }>]
        phaseScripts[idx] = { ...phaseScripts[idx], content: e.target.value }
        this.updateModule('scripts', { [phase]: phaseScripts })
      })
    })

    const restartExplorerCheck = contentDiv.querySelector('#config-restart-explorer') as HTMLInputElement
    if (restartExplorerCheck) {
      restartExplorerCheck.addEventListener('change', (e: any) => {
        this.updateModule('scripts', { restartExplorer: e.target.checked })
      })
    }

    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块28: Windows Defender Application Control
  private renderWdac() {
    const contentDiv = this.getSectionContent('config-wdac')
    if (!contentDiv) return

    const wdac = this.config.wdac

    contentDiv.innerHTML = `
      <div class="card">
        <div class="card-left">
          <div class="card-content">
            <div class="card-title">Windows Defender Application Control</div>
            <div style="display: flex; gap: 20px; margin-top: 10px; flex-direction: column;">
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="wdac-mode" value="skip" ${wdac.mode === 'skip' ? 'checked' : ''}>
                <span>Do not configure WDAC policy</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="wdac-mode" value="configure" ${wdac.mode === 'configure' ? 'checked' : ''}>
                <span>Configure a basic WDAC policy</span>
              </label>
            </div>
          </div>
        </div>
      </div>
      ${wdac.mode === 'configure' ? `
        <div class="card-expandable expanded">
          <div class="card-expandable-header">
            <div class="card-expandable-header-left">
              <div class="card-expandable-title">WDAC Policy Settings</div>
            </div>
            <div class="card-expandable-arrow">
              <i data-lucide="chevron-down"></i>
            </div>
          </div>
          <div class="card-expandable-content">
            <div style="display: flex; flex-direction: column; gap: 12px;">
              <div>
                <label style="display: block; margin-bottom: 6px; font-weight: 600;">Enforcement mode:</label>
                <fluent-select id="config-wdac-enforcement" style="width: 100%;">
                  <fluent-option value="audit" ${wdac.enforcementMode === 'audit' ? 'selected' : ''}>Auditing mode</fluent-option>
                  <fluent-option value="auditOnBootFailure" ${wdac.enforcementMode === 'auditOnBootFailure' ? 'selected' : ''}>Auditing mode on boot failure</fluent-option>
                  <fluent-option value="enforcement" ${wdac.enforcementMode === 'enforcement' ? 'selected' : ''}>Enforcement mode</fluent-option>
                </fluent-select>
              </div>
              <div>
                <label style="display: block; margin-bottom: 6px; font-weight: 600;">Script enforcement:</label>
                <fluent-select id="config-wdac-script-enforcement" style="width: 100%;">
                  <fluent-option value="restricted" ${wdac.scriptEnforcement === 'restricted' ? 'selected' : ''}>Restricted</fluent-option>
                  <fluent-option value="unrestricted" ${wdac.scriptEnforcement === 'unrestricted' ? 'selected' : ''}>Unrestricted</fluent-option>
                </fluent-select>
              </div>
            </div>
          </div>
        </div>
      ` : ''}
    `

    contentDiv.querySelectorAll('input[name="wdac-mode"]').forEach(radio => {
      radio.addEventListener('change', (e: any) => {
        this.updateModule('wdac', { mode: e.target.value })
        this.renderWdac()
      })
    })

    const enforcementSelect = contentDiv.querySelector('#config-wdac-enforcement') as any
    if (enforcementSelect) {
      enforcementSelect.addEventListener('change', (e: any) => {
        this.updateModule('wdac', { enforcementMode: e.target.value })
      })
    }

    const scriptEnforcementSelect = contentDiv.querySelector('#config-wdac-script-enforcement') as any
    if (scriptEnforcementSelect) {
      scriptEnforcementSelect.addEventListener('change', (e: any) => {
        this.updateModule('wdac', { scriptEnforcement: e.target.value })
      })
    }

    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块29: XML markup for more components
  private renderXmlMarkup() {
    const contentDiv = this.getSectionContent('config-xml-markup')
    if (!contentDiv) return

    const xmlMarkup = this.config.xmlMarkup

    contentDiv.innerHTML = `
      <div class="card-expandable expanded">
        <div class="card-expandable-header">
          <div class="card-expandable-header-left">
            <div class="card-expandable-title">XML markup for more components</div>
          </div>
          <div class="card-expandable-arrow">
            <i data-lucide="chevron-down"></i>
          </div>
        </div>
        <div class="card-expandable-content">
          <div class="card-description" style="margin-bottom: 12px;">You can add settings for all available components to add functionality not yet covered by this generator.</div>
          <div id="config-xml-components" style="display: flex; flex-direction: column; gap: 12px;">
            ${xmlMarkup.components.map((comp, idx) => `
              <div class="card" style="background: var(--bg-primary);">
                <div class="card-content">
                  <div style="display: grid; grid-template-columns: 200px 150px 1fr auto; gap: 12px; align-items: start;">
                    <div>
                      <label style="display: block; margin-bottom: 6px; font-size: 12px;">Component:</label>
                      <fluent-text-field class="xml-component-name" data-index="${idx}" value="${comp.component}" placeholder="Microsoft-Windows-..." style="width: 100%;"></fluent-text-field>
                    </div>
                    <div>
                      <label style="display: block; margin-bottom: 6px; font-size: 12px;">Pass:</label>
                      <fluent-select class="xml-component-pass" data-index="${idx}" style="width: 100%;">
                        <fluent-option value="offlineServicing" ${comp.pass === 'offlineServicing' ? 'selected' : ''}>offlineServicing</fluent-option>
                        <fluent-option value="windowsPE" ${comp.pass === 'windowsPE' ? 'selected' : ''}>windowsPE</fluent-option>
                        <fluent-option value="generalize" ${comp.pass === 'generalize' ? 'selected' : ''}>generalize</fluent-option>
                        <fluent-option value="specialize" ${comp.pass === 'specialize' ? 'selected' : ''}>specialize</fluent-option>
                        <fluent-option value="auditSystem" ${comp.pass === 'auditSystem' ? 'selected' : ''}>auditSystem</fluent-option>
                        <fluent-option value="auditUser" ${comp.pass === 'auditUser' ? 'selected' : ''}>auditUser</fluent-option>
                        <fluent-option value="oobeSystem" ${comp.pass === 'oobeSystem' ? 'selected' : ''}>oobeSystem</fluent-option>
                      </fluent-select>
                    </div>
                    <div>
                      <label style="display: block; margin-bottom: 6px; font-size: 12px;">XML Markup:</label>
                      <textarea class="xml-component-markup" data-index="${idx}" style="width: 100%; min-height: 80px; padding: 8px; font-family: monospace; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary);">${comp.markup}</textarea>
                    </div>
                    <fluent-button class="xml-component-remove" data-index="${idx}" appearance="stealth">Remove</fluent-button>
                  </div>
                </div>
              </div>
            `).join('')}
          </div>
          <fluent-button id="config-add-xml-component" appearance="outline" style="margin-top: 12px;">Add component</fluent-button>
        </div>
      </div>
    `

    const addBtn = contentDiv.querySelector('#config-add-xml-component')
    if (addBtn) {
      addBtn.addEventListener('click', () => {
        const components = [...xmlMarkup.components, { component: '', pass: 'windowsPE', markup: '' }]
        this.updateModule('xmlMarkup', { components })
        this.renderXmlMarkup()
      })
    }

    contentDiv.querySelectorAll('.xml-component-remove').forEach(btn => {
      btn.addEventListener('click', (e: any) => {
        const idx = parseInt(e.target.dataset.index)
        const components = [...xmlMarkup.components]
        components.splice(idx, 1)
        this.updateModule('xmlMarkup', { components })
        this.renderXmlMarkup()
      })
    })

    contentDiv.querySelectorAll('.xml-component-name').forEach(input => {
      input.addEventListener('input', (e: any) => {
        const idx = parseInt(e.target.dataset.index)
        const components = [...xmlMarkup.components]
        components[idx] = { ...components[idx], component: e.target.value }
        this.updateModule('xmlMarkup', { components })
      })
    })

    contentDiv.querySelectorAll('.xml-component-pass').forEach(select => {
      select.addEventListener('change', (e: any) => {
        const idx = parseInt(e.target.dataset.index)
        const components = [...xmlMarkup.components]
        components[idx] = { ...components[idx], pass: e.target.value }
        this.updateModule('xmlMarkup', { components })
      })
    })

    contentDiv.querySelectorAll('.xml-component-markup').forEach(textarea => {
      textarea.addEventListener('input', (e: any) => {
        const idx = parseInt(e.target.dataset.index)
        const components = [...xmlMarkup.components]
        components[idx] = { ...components[idx], markup: e.target.value }
        this.updateModule('xmlMarkup', { components })
      })
    })

    if (window.lucide) {
      window.lucide.createIcons()
    }
  }
}

// ========================================
// 导出
// ========================================

let configManager: UnattendConfigManager | null = null

export function initIsoConfig() {
  if (!configManager) {
    configManager = new UnattendConfigManager()
    configManager.init('workspace-iso-config')

    // 监听语言切换事件，重新渲染所有模块
    window.addEventListener('language-changed', () => {
      console.log('Language changed, re-rendering ISO config modules')
      if (configManager) {
        configManager.renderAllModules()
      }
    })
  }
  return configManager
}

export function getConfigManager(): UnattendConfigManager | null {
  return configManager
}

export type { UnattendConfig }
export { PRESET_DATA, createDefaultConfig }

