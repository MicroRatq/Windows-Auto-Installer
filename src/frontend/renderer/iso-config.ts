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
  setupComboContainer
} from './workspace'

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
  private renderAllModules() {
    if (!this.panel) return

    // 1. Region, Language and Time Zone (合并模块1和6)
    this.renderRegionLanguageTimeZone()

    // 2. Processor architectures
    this.renderProcessorArch()

    // 3. Setup settings
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

    // 语言模式 Radio 容器
    const languageModeRadioHtml = createRadioContainer({
      id: 'language-mode-container',
      name: 'language-mode',
      title: 'Language mode',
      description: '',
      icon: 'globe',
      options: [
        {
          value: 'interactive',
          label: 'Select language settings interactively during Windows Setup',
          description: ''
        },
        {
          value: 'unattended',
          label: 'Install Windows using these language settings',
          description: ''
        }
      ],
      selectedValue: lang.mode,
      expanded: true
    })

    // Windows display language ComboCard
    const uiLanguageCardHtml = lang.mode === 'unattended'
      ? createComboCard({
        id: 'config-ui-language-card',
        title: 'Windows display language',
        description: 'Windows features like Settings and File Explorer will appear in this language. It must match the language of your Windows 10/11 .iso file.',
        icon: 'globe',
        controlType: 'select',
        selectOptions: preset.languages.map(l => ({ value: l.id, label: l.name })),
        value: lang.uiLanguage || ''
      })
      : ''

    // First language ComboCard
    const firstLanguageCardHtml = lang.mode === 'unattended'
      ? createComboCard({
        id: 'config-first-language-card',
        title: 'First language',
        description: 'The first language will also determine the initial regional format, which defines how numbers, dates, times and currency are formatted.',
        icon: 'languages',
        controlType: 'select',
        selectOptions: preset.locales.map(l => ({ value: l.id, label: l.name })),
        value: lang.locale || ''
      })
      : ''

    // First keyboard layout ComboCard
    const firstKeyboardCardHtml = lang.mode === 'unattended'
      ? createComboCard({
        id: 'config-first-keyboard-card',
        title: 'First keyboard layout',
        description: '',
        icon: 'keyboard',
        controlType: 'select',
        selectOptions: preset.keyboards.map(k => ({ value: k.id, label: k.name })),
        value: lang.keyboard || ''
      })
      : ''

    // 时区模式 Radio 容器
    const timezoneModeRadioHtml = createRadioContainer({
      id: 'timezone-container',
      name: 'timezone-mode',
      title: 'Time zone',
      description: '',
      icon: 'clock',
      options: [
        {
          value: 'implicit',
          label: 'Let Windows determine your time zone based on language and region settings',
          description: ''
        },
        {
          value: 'explicit',
          label: 'Set your time zone explicitly',
          description: 'This is useful when your country or region spans multiple time zones, like Australia or the United States.'
        }
      ],
      selectedValue: tz.mode,
      expanded: true
    })

    // 时区选择 ComboCard
    const timezoneSelectCardHtml = tz.mode === 'explicit'
      ? createComboCard({
        id: 'config-timezone-card',
        title: 'Use this time zone',
        description: '',
        icon: 'map-pin',
        controlType: 'select',
        selectOptions: preset.timeZones.map(t => ({ value: t.id, label: t.name })),
        value: tz.timeZone || ''
      })
      : ''

    contentDiv.innerHTML = `
      ${languageModeRadioHtml}
      ${uiLanguageCardHtml}
      ${firstLanguageCardHtml}
      ${firstKeyboardCardHtml}
      ${timezoneModeRadioHtml}
      ${timezoneSelectCardHtml}
    `

    // 设置语言模式 Radio 容器事件监听
    setupRadioContainer(
      'language-mode-container',
      'language-mode',
      (value) => {
        this.updateModule('languageSettings', { mode: value as 'interactive' | 'unattended' })
        this.renderRegionLanguageTimeZone()
      },
      true
    )

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

    // 设置时区模式 Radio 容器事件监听
    setupRadioContainer(
      'timezone-container',
      'timezone-mode',
      (value) => {
        this.updateModule('timeZone', { mode: value as 'implicit' | 'explicit' })
        this.renderRegionLanguageTimeZone()
      },
      true
    )

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

  // 渲染模块2: Processor architectures
  private renderProcessorArch() {
    const contentDiv = this.getSectionContent('config-processor-arch')
    if (!contentDiv) return

    const archs = this.config.processorArchitectures

    contentDiv.innerHTML = `
      <div class="card">
        <div class="card-left">
          <div class="card-content">
            <div class="card-title">Processor architectures</div>
            <div style="display: flex; gap: 20px; margin-top: 10px; flex-wrap: wrap;">
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" value="x86" ${archs.includes('x86') ? 'checked' : ''}>
                <span>Intel / AMD 32-bit</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" value="amd64" ${archs.includes('amd64') ? 'checked' : ''}>
                <span>Intel / AMD 64-bit</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" value="arm64" ${archs.includes('arm64') ? 'checked' : ''}>
                <span>Windows on Arm64</span>
              </label>
            </div>
          </div>
        </div>
      </div>
    `

    contentDiv.querySelectorAll('input[type="checkbox"]').forEach(cb => {
      cb.addEventListener('change', (e: any) => {
        const value = e.target.value as ProcessorArchitecture
        const checked = e.target.checked
        let newArchs = [...archs]
        if (checked) {
          if (!newArchs.includes(value)) newArchs.push(value)
        } else {
          newArchs = newArchs.filter(a => a !== value)
        }
        this.updateConfig({ processorArchitectures: newArchs })
      })
    })
  }

  // 渲染模块3: Setup settings
  private renderSetupSettings() {
    const contentDiv = this.getSectionContent('config-setup-settings')
    if (!contentDiv) return

    const settings = this.config.setupSettings

    // 使用 ComboCard 为每个设置创建独立的卡片
    const bypassRequirementsCardHtml = createComboCard({
      id: 'config-bypass-requirements-card',
      title: 'Bypass Windows 11 requirements check',
      description: 'Bypass TPM, Secure Boot, RAM, and CPU requirements for Windows 11 installation.',
      icon: 'shield-off',
      controlType: 'switch',
      value: settings.bypassRequirementsCheck
    })

    const bypassNetworkCardHtml = createComboCard({
      id: 'config-bypass-network-card',
      title: 'Allow Windows 11 without internet connection',
      description: 'Only check this if your computer really does not have internet access. You will still need to click "I don\'t have internet" during Setup. If you just want to create local accounts, use the User accounts section instead.',
      icon: 'wifi-off',
      controlType: 'switch',
      value: settings.bypassNetworkCheck
    })

    const useConfigurationSetCardHtml = createComboCard({
      id: 'config-use-configuration-set-card',
      title: 'Use a distribution share / configuration set',
      description: 'Windows Setup will look for a folder named $OEM$ in the root of the drive where autounattend.xml is located and copy its contents to the target partition.',
      icon: 'folder-tree',
      controlType: 'switch',
      value: settings.useConfigurationSet
    })

    const hidePowerShellWindowsCardHtml = createComboCard({
      id: 'config-hide-powershell-card',
      title: 'Hide any PowerShell windows during Setup',
      description: 'PowerShell scripts will run with the -WindowStyle Hidden switch. Do not enable if you use interactive prompts (like Read-Host) in your scripts, as you won\'t be able to answer them without a visible window.',
      icon: 'eye-off',
      controlType: 'switch',
      value: settings.hidePowerShellWindows
    })

    const keepSensitiveFilesCardHtml = createComboCard({
      id: 'config-keep-sensitive-files-card',
      title: 'Keep sensitive files',
      description: 'By default, files like unattend.xml and Wifi.xml which may contain sensitive data will be deleted once Windows Setup finishes. Enable this to keep those files.',
      icon: 'file-lock',
      controlType: 'switch',
      value: settings.keepSensitiveFiles
    })

    const useNarratorCardHtml = createComboCard({
      id: 'config-use-narrator-card',
      title: 'Automatically start Narrator',
      description: 'Narrator is a built-in screen reader that speaks out loud what is on your screen. It will start during Windows Setup and after logon.',
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

    // 1. Computer name - RadioContainer
    const computerNameRadioHtml = createRadioContainer({
      id: 'computer-name-container',
      name: 'computer-name-mode',
      title: 'Computer name',
      description: '',
      icon: 'monitor',
      options: [
        {
          value: 'random',
          label: 'Let Windows generate a random computer name like DESKTOP-ZFAH8Z2',
          description: ''
        },
        {
          value: 'custom',
          label: 'Choose a computer name yourself',
          description: ''
        },
        {
          value: 'script',
          label: 'Provide a Windows PowerShell script to set the computer name dynamically',
          description: ''
        }
      ],
      selectedValue: cn.mode,
      expanded: true
    })

    // Computer name input card
    const computerNameInputHtml = cn.mode === 'custom'
      ? `<div class="card">
          <div class="card-left">
            <div class="card-content">
              <label style="display: block; margin-bottom: 6px; font-weight: 600;">Use this name:</label>
              <fluent-text-field id="config-computer-name-input" value="${cn.name || ''}" placeholder="Enter computer name (max 15 chars)" maxlength="15" style="width: 100%;"></fluent-text-field>
            </div>
          </div>
        </div>`
      : ''

    // Computer name script card
    const computerNameScriptHtml = cn.mode === 'script'
      ? `<div class="card">
          <div class="card-left">
            <div class="card-content">
              <label style="display: block; margin-bottom: 6px; font-weight: 600;">PowerShell script:</label>
              <fluent-text-area id="config-computer-name-script" style="width: 100%; min-height: 120px;" rows="5">${cn.script || "return 'DESKTOP-{0:D3}' -f ( Get-Random -Minimum 0 -Maximum 999 );"}</fluent-text-area>
              <div class="card-description" style="margin-top: 8px;">Your script will be evaluated during Windows Setup. The script must return a single string, which must be a valid computer name. You can use interactive prompts like <code>return Read-Host -Prompt 'Enter computer name';</code></div>
            </div>
          </div>
        </div>`
      : ''

    // 2. User accounts - RadioContainer
    const userAccountsRadioHtml = createRadioContainer({
      id: 'user-accounts-container',
      name: 'account-mode',
      title: 'User accounts',
      description: '',
      icon: 'users',
      options: [
        {
          value: 'unattended',
          label: 'Let Windows Setup create the following local ("offline") accounts',
          description: ''
        },
        {
          value: 'interactive-microsoft',
          label: 'Add a Microsoft ("online") user account interactively during Windows Setup',
          description: ''
        },
        {
          value: 'interactive-local',
          label: 'Add a local ("offline") user account interactively during Windows Setup',
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
              <div class="card-expandable-title">Account list</div>
            </div>
            <div class="card-expandable-arrow">
              <i data-lucide="chevron-down"></i>
            </div>
          </div>
          <div class="card-expandable-content">
            <div class="card-description" style="margin-bottom: 12px;">Leave <strong>Display name</strong> empty unless you want it to be different from <strong>Account name</strong>.</div>
            <div id="config-accounts-list" style="display: flex; flex-direction: column; gap: 12px;">
              ${(accounts.accounts || []).map((acc, idx) => `
                <div class="card" style="background: var(--bg-primary);">
                  <div class="card-content" style="width: 100%;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr auto; gap: 12px; align-items: end;">
                      <div>
                        <label style="display: block; margin-bottom: 6px; font-size: 12px;">Account name:</label>
                        <fluent-text-field class="account-name" data-index="${idx}" value="${acc.name}" maxlength="20" style="width: 100%;"></fluent-text-field>
                      </div>
                      <div>
                        <label style="display: block; margin-bottom: 6px; font-size: 12px;">Display name:</label>
                        <fluent-text-field class="account-display-name" data-index="${idx}" value="${acc.displayName}" maxlength="256" style="width: 100%;"></fluent-text-field>
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
                <i data-lucide="plus"></i> Add account
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
        title: 'First logon',
        description: 'Several settings will only be applied when an administrator logs on for the first time. Choose which account to use for this.',
        icon: 'log-in',
        options: [
          {
            value: 'own',
            label: 'Logon to the first administrator account created above',
            description: ''
          },
          {
            value: 'builtin',
            label: 'Activate built-in account "Administrator" and logon to this account',
            description: ''
          },
          {
            value: 'none',
            label: 'Do not logon',
            description: 'The installation ends with the sign-in screen being shown. Not recommended.'
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
              <label style="display: block; margin-bottom: 6px; font-weight: 600;">Set built-in Administrator password to:</label>
              <fluent-text-field id="config-auto-logon-password" type="password" value="${accounts.autoLogonPassword || ''}" placeholder="Enter password" style="width: 100%;"></fluent-text-field>
            </div>
          </div>
        </div>`
      : ''

    // Obscure passwords - ComboCard
    const obscurePasswordsCardHtml = accounts.mode === 'unattended'
      ? createComboCard({
        id: 'config-obscure-passwords-card',
        title: 'Obscure all account passwords with Base64',
        description: 'Encode passwords in your autounattend.xml file with Base64 encoding for basic obfuscation.',
        icon: 'eye-off',
        controlType: 'switch',
        value: accounts.obscurePasswords || false
      })
      : ''

    // 3. Password expiration - RadioContainer
    const passwordExpirationRadioHtml = createRadioContainer({
      id: 'password-expiration-container',
      name: 'password-expiration-mode',
      title: 'Password expiration',
      description: 'These settings only apply to local accounts. The password of the built-in "Administrator" account never expires.',
      icon: 'shield',
      options: [
        {
          value: 'unlimited',
          label: 'Passwords do not expire',
          description: 'This is in accordance to NIST guidelines that no longer recommend password expiration.'
        },
        {
          value: 'default',
          label: 'Use Windows default',
          description: 'Passwords expire after 42 days.'
        },
        {
          value: 'custom',
          label: 'Use custom password expiration',
          description: ''
        }
      ],
      selectedValue: pe.mode,
      expanded: true
    })

    // Custom password expiration
    const customPasswordExpirationHtml = pe.mode === 'custom'
      ? `<div class="card">
          <div class="card-left">
            <div class="card-content">
              <label style="display: block; margin-bottom: 6px; font-weight: 600;">Passwords expire after (days):</label>
              <fluent-text-field id="config-password-max-age" type="number" value="${pe.maxAge || 42}" min="1" max="999" placeholder="42" style="width: 100%;"></fluent-text-field>
            </div>
          </div>
        </div>`
      : ''

    // 4. Account Lockout policy - RadioContainer
    const accountLockoutRadioHtml = createRadioContainer({
      id: 'account-lockout-container',
      name: 'lockout-mode',
      title: 'Account Lockout policy',
      description: '',
      icon: 'lock',
      options: [
        {
          value: 'default',
          label: 'Use default policy',
          description: 'Windows will lock out an account after 10 failed logon attempts within 10 minutes. After 10 minutes, the account is unlocked automatically.'
        },
        {
          value: 'disabled',
          label: 'Disable policy',
          description: 'Warning: Disabling Account Lockout might leave your computer vulnerable to brute-force attacks.'
        },
        {
          value: 'custom',
          label: 'Use custom policy',
          description: ''
        }
      ],
      selectedValue: lockout.mode,
      expanded: true
    })

    // Custom lockout policy
    const customLockoutHtml = lockout.mode === 'custom'
      ? `<div class="card">
          <div class="card-left">
            <div class="card-content">
              <div class="card-description" style="margin-bottom: 12px;">Configure custom account lockout policy:</div>
              <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px;">
                <div>
                  <label style="display: block; margin-bottom: 6px; font-weight: 600;">Lockout threshold:</label>
                  <fluent-text-field id="config-lockout-threshold" type="number" value="${lockout.lockoutThreshold || 10}" min="0" max="999" placeholder="10" style="width: 100%;"></fluent-text-field>
                  <div class="card-description" style="margin-top: 4px; font-size: 11px;">Failed attempts</div>
                </div>
                <div>
                  <label style="display: block; margin-bottom: 6px; font-weight: 600;">Lockout window:</label>
                  <fluent-text-field id="config-lockout-window" type="number" value="${lockout.resetLockoutCounter || 10}" min="1" max="99999" placeholder="10" style="width: 100%;"></fluent-text-field>
                  <div class="card-description" style="margin-top: 4px; font-size: 11px;">Minutes</div>
                </div>
                <div>
                  <label style="display: block; margin-bottom: 6px; font-weight: 600;">Lockout duration:</label>
                  <fluent-text-field id="config-lockout-duration" type="number" value="${lockout.lockoutDuration || 10}" min="1" max="99999" placeholder="10" style="width: 100%;"></fluent-text-field>
                  <div class="card-description" style="margin-top: 4px; font-size: 11px;">Minutes</div>
                </div>
              </div>
            </div>
          </div>
        </div>`
      : ''

    contentDiv.innerHTML = `
      ${computerNameRadioHtml}
      ${computerNameInputHtml}
      ${computerNameScriptHtml}
      ${userAccountsRadioHtml}
      ${userAccountsListHtml}
      ${firstLogonRadioHtml}
      ${builtinAdminPasswordHtml}
      ${obscurePasswordsCardHtml}
      ${passwordExpirationRadioHtml}
      ${customPasswordExpirationHtml}
      ${accountLockoutRadioHtml}
      ${customLockoutHtml}
    `

    // === 事件监听设置 ===

    // 1. Computer name 事件
    setupRadioContainer('computer-name-container', 'computer-name-mode', (value) => {
      this.updateModule('computerName', { mode: value as 'random' | 'custom' | 'script' })
      this.renderNameAndAccount()
    }, true)

    const nameInput = contentDiv.querySelector('#config-computer-name-input') as any
    if (nameInput) {
      nameInput.addEventListener('input', (e: any) => {
        this.updateModule('computerName', { name: e.target.value })
      })
    }

    const scriptInput = contentDiv.querySelector('#config-computer-name-script') as any
    if (scriptInput) {
      scriptInput.addEventListener('input', (e: any) => {
        this.updateModule('computerName', { script: e.target.value })
      })
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

    const maxAgeInput = contentDiv.querySelector('#config-password-max-age') as any
    if (maxAgeInput) {
      maxAgeInput.addEventListener('input', (e: any) => {
        this.updateModule('passwordExpiration', { maxAge: parseInt(e.target.value) || undefined })
      })
    }

    // 4. Account Lockout policy 事件
    setupRadioContainer('account-lockout-container', 'lockout-mode', (value) => {
      this.updateModule('lockoutSettings', { mode: value as 'default' | 'disabled' | 'custom' })
      this.renderNameAndAccount()
    }, true)

    const thresholdInput = contentDiv.querySelector('#config-lockout-threshold') as any
    if (thresholdInput) {
      thresholdInput.addEventListener('input', (e: any) => {
        this.updateModule('lockoutSettings', { lockoutThreshold: parseInt(e.target.value) || undefined })
      })
    }

    const windowInput = contentDiv.querySelector('#config-lockout-window') as any
    if (windowInput) {
      windowInput.addEventListener('input', (e: any) => {
        this.updateModule('lockoutSettings', { resetLockoutCounter: parseInt(e.target.value) || undefined })
      })
    }

    const durationInput = contentDiv.querySelector('#config-lockout-duration') as any
    if (durationInput) {
      durationInput.addEventListener('input', (e: any) => {
        this.updateModule('lockoutSettings', { lockoutDuration: parseInt(e.target.value) || undefined })
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
      title: 'Compact OS',
      description: '',
      icon: 'archive',
      options: [
        {
          value: 'default',
          label: 'Let Windows decide whether to use Compact OS',
          description: ''
        },
        {
          value: 'enabled',
          label: 'Use Compact OS',
          description: ''
        },
        {
          value: 'disabled',
          label: 'Do not use Compact OS',
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
      title: 'Windows PE operation',
      description: '',
      icon: 'terminal',
      options: [
        {
          value: 'default',
          label: 'Let Windows Setup (setup.exe) handle the Windows PE stage as usual',
          description: ''
        },
        {
          value: 'generated',
          label: 'Generate a .cmd script using the form\'s other settings and also these options',
          description: ''
        },
        {
          value: 'script',
          label: 'Use a custom .cmd script to handle the Windows PE stage',
          description: ''
        }
      ],
      selectedValue: pe.mode,
      expanded: true
    })

    // 2.1 Generated模式 - Checkbox选项
    const generatedOptionsHtml = pe.mode === 'generated'
      ? `<div class="card">
          <div class="card-left">
            <i data-lucide="settings" class="card-icon"></i>
            <div class="card-content">
              <div class="card-title">Generated script options</div>
              <div style="display: flex; flex-direction: column; gap: 12px; margin-top: 12px;">
                <div>
                  <fluent-checkbox id="config-pe-disable-8dot3" ${pe.disable8Dot3Names ? 'checked' : ''}>Disable 8.3 file names</fluent-checkbox>
                  <div class="card-description" style="margin-left: 24px; margin-top: 4px;">This removes all existing short file names such as PROGRA~1 and disables the creation of new ones.</div>
                </div>
                <fluent-checkbox id="config-pe-pause-formatting" ${pe.pauseBeforeFormatting ? 'checked' : ''}>Pause before disk is partitioned and formatted</fluent-checkbox>
                <fluent-checkbox id="config-pe-pause-reboot" ${pe.pauseBeforeReboot ? 'checked' : ''}>Pause before Windows Setup reboots at the end of the Windows PE stage</fluent-checkbox>
              </div>
            </div>
          </div>
        </div>`
      : ''

    // 2.2 Script模式 - 自定义脚本
    const customScriptDefaultValue = `@for %%d in (C D E F G H I J K L M N O P Q T U V Y Z) do @(
    if exist %%d:\\sources\\install.wim set "IMAGE_FILE=%%d:\\sources\\install.wim"
    if exist %%d:\\sources\\install.esd set "IMAGE_FILE=%%d:\\sources\\install.esd"
    if exist %%d:\\sources\\install.swm set "IMAGE_FILE=%%d:\\sources\\install.swm" & set "SWM_PARAM=/SWMFile:%%d:\\sources\\install*.swm"
    if exist %%d:\\autounattend.xml set "XML_FILE=%%d:\\autounattend.xml"
    if exist %%d:\\$OEM$ set "OEM_FOLDER=%%d:\\$OEM$"
    if exist %%d:\\$WinPEDriver$ set "PEDRIVERS_FOLDER=%%d:\\$WinPEDriver$"
)
for /f "tokens=3" %%t in ('reg.exe query HKLM\\System\\Setup /v UnattendFile') do ( if exist %%t set "XML_FILE=%%t" )
@if not defined IMAGE_FILE echo Could not locate install.wim, install.esd or install.swm. & pause & exit /b 1
@if not defined XML_FILE echo Could not locate autounattend.xml. & pause & exit /b 1

rem Install drivers from $WinPEDriver$ folder
if defined PEDRIVERS_FOLDER (
    for /R %PEDRIVERS_FOLDER% %%f IN (*.inf) do drvload.exe "%%f"
)

>X:\\diskpart.txt (
    echo SELECT DISK=0
    echo CLEAN
    echo CONVERT GPT
    echo CREATE PARTITION EFI SIZE=300
    echo FORMAT QUICK FS=FAT32 LABEL="System"
    echo ASSIGN LETTER=S
    echo CREATE PARTITION MSR SIZE=16
    echo CREATE PARTITION PRIMARY
    echo FORMAT QUICK FS=NTFS LABEL="Windows"
    echo ASSIGN LETTER=W
)

diskpart.exe /s X:\\diskpart.txt || ( echo diskpart.exe encountered an error. & pause & exit /b 1 )
dism.exe /Apply-Image /ImageFile:%IMAGE_FILE% %SWM_PARAM% /Name:"Windows 11 Pro" /ApplyDir:W:\\ || ( echo dism.exe encountered an error. & pause & exit /b 1 )
bcdboot.exe W:\\Windows /s S: || ( echo bcdboot.exe encountered an error. & pause & exit /b 1 )

rem Continue with next stage of Windows Setup after reboot
wpeutil.exe reboot`

    const customScriptHtml = pe.mode === 'script'
      ? `<div class="card">
          <div class="card-left">
            <i data-lucide="code" class="card-icon"></i>
            <div class="card-content">
              <div class="card-title">Custom PE script</div>
              <fluent-text-area id="config-pe-custom-script" style="width: 100%; min-height: 400px; font-family: 'Consolas', 'Monaco', monospace;" rows="25">${pe.cmdScript || customScriptDefaultValue}</fluent-text-area>
              <div class="card-description" style="margin-top: 8px;">Your script has to partition and format the disk, copy a Windows image to it and make it bootable. Note that PowerShell is usually not available in Windows PE.</div>
            </div>
          </div>
        </div>`
      : ''

    // 3. Virtual machine support - ComboContainer
    const vmSupportHtml = createComboContainer({
      id: 'vm-support-container',
      name: 'vm-support',
      title: 'Virtual machine support',
      description: 'Make sure to check the usage notes for how to properly configure your VM.',
      icon: 'box',
      options: [
        {
          value: 'vBoxGuestAdditions',
          label: 'Install Oracle VirtualBox Guest Additions',
          description: '',
          controlType: 'checkbox'
        },
        {
          value: 'vmwareTools',
          label: 'Install VMware Tools',
          description: '',
          controlType: 'checkbox'
        },
        {
          value: 'virtIoGuestTools',
          label: 'Install VirtIO Guest Tools and QEMU Guest Agent (e.g. for Proxmox VE)',
          description: '',
          controlType: 'checkbox'
        },
        {
          value: 'parallelsTools',
          label: 'Install Parallels Tools for Parallels Desktop',
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

    // 4. WDAC - RadioContainer
    const wdacRadioHtml = createRadioContainer({
      id: 'wdac-mode-container',
      name: 'wdac-mode',
      title: 'Windows Defender Application Control',
      description: 'Applications in C:\\Windows, C:\\Program Files and C:\\Program Files (x86) are allowed to run. Applications stored elsewhere and those in known user-writable folders are not allowed to run. To disable this WDAC policy later, simply delete the file C:\\Windows\\System32\\CodeIntegrity\\CiPolicies\\Active\\{d26bff32-33a2-48a3-b037-10357ee48427}.cip and reboot.',
      icon: 'shield-alert',
      options: [
        {
          value: 'skip',
          label: 'Do not configure WDAC policy',
          description: ''
        },
        {
          value: 'configure',
          label: 'Configure a basic WDAC policy using these settings',
          description: ''
        }
      ],
      selectedValue: wdac.mode || 'skip',
      expanded: true
    })

    // 4.1 WDAC Configure模式 - Policy设置
    const wdacConfigureHtml = wdac.mode === 'configure'
      ? `${createRadioContainer({
        id: 'wdac-enforcement-container',
        name: 'wdac-enforcement-mode',
        title: 'Choose how to enforce the policy',
        description: '',
        icon: 'shield',
        options: [
          {
            value: 'audit',
            label: 'Auditing mode',
            description: 'Logs drivers and applications that would have been blocked.'
          },
          {
            value: 'auditOnBootFailure',
            label: 'Auditing mode on boot failure',
            description: 'When the policy blocks a system driver and thus would prevent Windows from booting, use audit mode. Otherwise, use enforcement mode.'
          },
          {
            value: 'enforcement',
            label: 'Enforcement mode',
            description: 'Drivers and applications will be blocked unless allowed by the policy.'
          }
        ],
        selectedValue: wdac.enforcementMode || 'auditOnBootFailure',
        expanded: false
      })}
      ${createRadioContainer({
        id: 'wdac-script-enforcement-container',
        name: 'wdac-script-mode',
        title: 'Choose script enforcement',
        description: '',
        icon: 'file-code',
        options: [
          {
            value: 'restricted',
            label: 'Restricted',
            description: 'PowerShell will run in Constrained Language Mode.'
          },
          {
            value: 'unrestricted',
            label: 'Unrestricted',
            description: ''
          }
        ],
        selectedValue: wdac.scriptEnforcement || 'restricted',
        expanded: false
      })}`
      : ''

    contentDiv.innerHTML = `
      ${compactOSRadioHtml}
      ${peOperationRadioHtml}
      ${generatedOptionsHtml}
      ${customScriptHtml}
      ${vmSupportHtml}
      ${wdacRadioHtml}
      ${wdacConfigureHtml}
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

    // 2.1 Generated选项
    if (pe.mode === 'generated') {
      const disable8dot3Check = contentDiv.querySelector('#config-pe-disable-8dot3') as any
      if (disable8dot3Check) {
        disable8dot3Check.addEventListener('change', () => {
          this.updateModule('peSettings', { disable8Dot3Names: disable8dot3Check.checked })
        })
      }

      const pauseFormattingCheck = contentDiv.querySelector('#config-pe-pause-formatting') as any
      if (pauseFormattingCheck) {
        pauseFormattingCheck.addEventListener('change', () => {
          this.updateModule('peSettings', { pauseBeforeFormatting: pauseFormattingCheck.checked })
        })
      }

      const pauseRebootCheck = contentDiv.querySelector('#config-pe-pause-reboot') as any
      if (pauseRebootCheck) {
        pauseRebootCheck.addEventListener('change', () => {
          this.updateModule('peSettings', { pauseBeforeReboot: pauseRebootCheck.checked })
        })
      }
    }

    // 2.2 Custom script
    const scriptInput = contentDiv.querySelector('#config-pe-custom-script') as any
    if (scriptInput) {
      scriptInput.addEventListener('input', (e: any) => {
        this.updateModule('peSettings', { cmdScript: e.target.value })
      })
    }

    // 3. Virtual machine support
    setupComboContainer('vm-support-container', 'vm-support', (values) => {
      this.updateModule('vmSupport', values)
    }, true)

    // 4. WDAC
    setupRadioContainer('wdac-mode-container', 'wdac-mode', (value) => {
      this.updateModule('wdac', { mode: value as 'skip' | 'configure' })
      this.renderAdvancedSettings()
    }, true)

    // 4.1 WDAC Configure
    if (wdac.mode === 'configure') {
      setupRadioContainer('wdac-enforcement-container', 'wdac-enforcement-mode', (value) => {
        this.updateModule('wdac', { enforcementMode: value as 'audit' | 'auditOnBootFailure' | 'enforcement' })
      }, false)

      setupRadioContainer('wdac-script-enforcement-container', 'wdac-script-mode', (value) => {
        this.updateModule('wdac', { scriptEnforcement: value as 'restricted' | 'unrestricted' })
      }, false)
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

    // 1. 主要分区模式 - RadioContainer
    const partitionModeRadioHtml = createRadioContainer({
      id: 'partitioning-mode-container',
      name: 'partition-mode',
      title: 'Partitioning and formatting',
      description: '',
      icon: 'hard-drive',
      options: [
        {
          value: 'interactive',
          label: 'Partition the disk interactively during Windows Setup',
          description: ''
        },
        {
          value: 'automatic',
          label: 'Let Windows Setup wipe, partition and format your hard drive (more specifically, disk 0) using these settings',
          description: ''
        },
        {
          value: 'custom',
          label: 'Use a custom diskpart script to configure your disk(s)',
          description: ''
        }
      ],
      selectedValue: part.mode,
      expanded: true
    })

    // 2. Automatic模式下的设置
    let automaticSettingsHtml = ''
    if (part.mode === 'automatic') {
      // 2.1 Partition layout - RadioContainer
      const partitionLayoutRadioHtml = createRadioContainer({
        id: 'partition-layout-container',
        name: 'partition-layout',
        title: 'Choose partition layout',
        description: '',
        icon: 'layout',
        options: [
          {
            value: 'GPT',
            label: 'GPT',
            description: 'The GPT partition layout must be used for UEFI systems.'
          },
          {
            value: 'MBR',
            label: 'MBR',
            description: 'The MBR-based partition layout must be used for legacy BIOS systems.'
          }
        ],
        selectedValue: part.layout || 'GPT',
        expanded: true
      })

      // ESP Size input (只在GPT模式下显示)
      const espSizeHtml = part.layout === 'GPT'
        ? `<div class="card">
            <div class="card-left">
              <div class="card-content">
                <label style="display: block; margin-bottom: 6px; font-weight: 600;">EFI System Partition (ESP) size:</label>
                <div style="display: flex; align-items: center; gap: 8px;">
                  <fluent-text-field id="config-esp-size" type="number" value="${part.espSize || 300}" min="100" style="width: 150px;"></fluent-text-field>
                  <span>MB</span>
                </div>
              </div>
            </div>
          </div>`
        : ''

      // 2.2 Windows RE - RadioContainer
      const recoveryModeRadioHtml = createRadioContainer({
        id: 'recovery-mode-container',
        name: 'recovery-mode',
        title: 'Choose how to install Windows RE',
        description: 'Windows 24H2 seems to ignore this setting and will always create a recovery partition with a minimum size of 600 MB.',
        icon: 'life-buoy',
        options: [
          {
            value: 'partition',
            label: 'Install on recovery partition',
            description: ''
          },
          {
            value: 'folder',
            label: 'Install on Windows partition',
            description: 'This will install Windows RE in C:\\Recovery. No recovery partition will be created.'
          },
          {
            value: 'none',
            label: 'Remove Windows RE',
            description: 'This will delete the C:\\Recovery folder and thus free about 600 MB of disk space. No recovery partition will be created.'
          }
        ],
        selectedValue: part.recoveryMode || 'partition',
        expanded: true
      })

      // Recovery partition size input (只在partition模式下显示)
      const recoveryPartitionSizeHtml = part.recoveryMode === 'partition'
        ? `<div class="card">
            <div class="card-left">
              <div class="card-content">
                <label style="display: block; margin-bottom: 6px; font-weight: 600;">Recovery partition size:</label>
                <div style="display: flex; align-items: center; gap: 8px;">
                  <fluent-text-field id="config-recovery-size" type="number" value="${part.recoverySize || 1000}" min="300" style="width: 150px;"></fluent-text-field>
                  <span>MB</span>
                </div>
              </div>
            </div>
          </div>`
        : ''

      automaticSettingsHtml = `
        ${partitionLayoutRadioHtml}
        ${espSizeHtml}
        ${recoveryModeRadioHtml}
        ${recoveryPartitionSizeHtml}
      `
    }

    // 3. Custom模式下的设置
    let customSettingsHtml = ''
    if (part.mode === 'custom') {
      // Diskpart script
      const diskpartScriptHtml = `
        <div class="card">
          <div class="card-left">
            <i data-lucide="code" class="card-icon"></i>
            <div class="card-content">
              <div class="card-title">Diskpart script</div>
              <fluent-text-area id="config-diskpart-script" style="width: 100%; min-height: 320px; font-family: 'Consolas', 'Monaco', monospace;" rows="18">${part.diskpartScript || `SELECT DISK=0
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
GPT ATTRIBUTES=0x8000000000000001`}</fluent-text-area>
              <div class="card-description" style="margin-top: 8px;">Drive letter assignments in the script (e.g. <code>ASSIGN LETTER=W</code>) solely affect the Windows PE stage of Windows Setup; these assignments do not persist to the new installation.</div>
            </div>
          </div>
        </div>
      `

      // Install to mode - RadioContainer
      const installToModeRadioHtml = createRadioContainer({
        id: 'install-to-mode-container',
        name: 'install-to-mode',
        title: 'Choose partition to install Windows to',
        description: '',
        icon: 'target',
        options: [
          {
            value: 'available',
            label: 'Install Windows to the first available partition that has enough space and does not already contain an installation of Windows',
            description: ''
          },
          {
            value: 'custom',
            label: 'Install to another partition',
            description: ''
          }
        ],
        selectedValue: part.installToMode || 'available',
        expanded: true
      })

      // Custom install location (只在custom模式下显示)
      const customInstallLocationHtml = part.installToMode === 'custom'
        ? `<div class="card">
            <div class="card-left">
              <div class="card-content">
                <div class="card-title">Install location</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px;">
                  <div>
                    <label style="display: block; margin-bottom: 6px; font-weight: 600;">Disk (0-based):</label>
                    <fluent-text-field id="config-install-to-disk" type="number" value="${part.installToDisk || 0}" min="0" style="width: 100%;"></fluent-text-field>
                  </div>
                  <div>
                    <label style="display: block; margin-bottom: 6px; font-weight: 600;">Partition (1-based):</label>
                    <fluent-text-field id="config-install-to-partition" type="number" value="${part.installToPartition || 3}" min="1" style="width: 100%;"></fluent-text-field>
                  </div>
                </div>
              </div>
            </div>
          </div>`
        : ''

      customSettingsHtml = `
        ${diskpartScriptHtml}
        ${installToModeRadioHtml}
        ${customInstallLocationHtml}
      `
    }

    // 4. Disk Assertion - RadioContainer (显示在所有模式下，但主要用于automatic和custom)
    const diskAssertionRadioHtml = (part.mode === 'automatic' || part.mode === 'custom')
      ? createRadioContainer({
        id: 'disk-assertion-container',
        name: 'disk-assertion-mode',
        title: 'Disk assertion',
        description: 'When you let Windows Setup partition your disks unattendedly, there is a risk they were assigned unexpected index numbers. In rare cases, disk 0 does not refer to your primary hard drive, but rather your USB thumb drive. You can provide VBScript code to check the assigned disk index numbers. If your script returns with WScript.Quit 1, Windows Setup will halt to avoid data loss.',
        icon: 'alert-triangle',
        options: [
          {
            value: 'skip',
            label: 'Do not run a script',
            description: ''
          },
          {
            value: 'script',
            label: 'Run this VBScript code to check disk layout',
            description: ''
          }
        ],
        selectedValue: part.diskAssertionMode || 'skip',
        expanded: true
      })
      : ''

    // Disk assertion script (只在script模式下显示)
    const diskAssertionScriptHtml = (part.mode === 'automatic' || part.mode === 'custom') && part.diskAssertionMode === 'script'
      ? `<div class="card">
          <div class="card-left">
            <i data-lucide="code" class="card-icon"></i>
            <div class="card-content">
              <div class="card-title">VBScript code</div>
              <fluent-text-area id="config-disk-assertion-script" style="width: 100%; min-height: 240px; font-family: 'Consolas', 'Monaco', monospace;" rows="15">${part.diskAssertionScript || `On Error Resume Next
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
End If`}</fluent-text-area>
            </div>
          </div>
        </div>`
      : ''

    contentDiv.innerHTML = `
      ${partitionModeRadioHtml}
      ${automaticSettingsHtml}
      ${customSettingsHtml}
      ${diskAssertionRadioHtml}
      ${diskAssertionScriptHtml}
    `

    // === 事件监听设置 ===

    // 1. 主要分区模式
    setupRadioContainer('partitioning-mode-container', 'partition-mode', (value) => {
      this.updateModule('partitioning', { mode: value as 'interactive' | 'automatic' | 'custom' })
      this.renderPartitioning()
    }, true)

    // 2. Automatic模式下的事件
    if (part.mode === 'automatic') {
      // Partition layout
      setupRadioContainer('partition-layout-container', 'partition-layout', (value) => {
        this.updateModule('partitioning', { layout: value as 'GPT' | 'MBR' })
        this.renderPartitioning()
      }, true)

      // ESP size
      const espSizeInput = contentDiv.querySelector('#config-esp-size') as any
      if (espSizeInput) {
        espSizeInput.addEventListener('input', (e: any) => {
          this.updateModule('partitioning', { espSize: parseInt(e.target.value) || 300 })
        })
      }

      // Recovery mode
      setupRadioContainer('recovery-mode-container', 'recovery-mode', (value) => {
        this.updateModule('partitioning', { recoveryMode: value as 'partition' | 'folder' | 'none' })
        this.renderPartitioning()
      }, true)

      // Recovery partition size
      const recoverySizeInput = contentDiv.querySelector('#config-recovery-size') as any
      if (recoverySizeInput) {
        recoverySizeInput.addEventListener('input', (e: any) => {
          this.updateModule('partitioning', { recoverySize: parseInt(e.target.value) || 1000 })
        })
      }
    }

    // 3. Custom模式下的事件
    if (part.mode === 'custom') {
      // Diskpart script
      const scriptInput = contentDiv.querySelector('#config-diskpart-script') as any
      if (scriptInput) {
        scriptInput.addEventListener('input', (e: any) => {
          this.updateModule('partitioning', { diskpartScript: e.target.value })
        })
      }

      // Install to mode
      setupRadioContainer('install-to-mode-container', 'install-to-mode', (value) => {
        this.updateModule('partitioning', { installToMode: value as 'available' | 'custom' })
        this.renderPartitioning()
      }, true)

      // Custom install location
      const installToDiskInput = contentDiv.querySelector('#config-install-to-disk') as any
      if (installToDiskInput) {
        installToDiskInput.addEventListener('input', (e: any) => {
          this.updateModule('partitioning', { installToDisk: parseInt(e.target.value) || 0 })
        })
      }

      const installToPartitionInput = contentDiv.querySelector('#config-install-to-partition') as any
      if (installToPartitionInput) {
        installToPartitionInput.addEventListener('input', (e: any) => {
          this.updateModule('partitioning', { installToPartition: parseInt(e.target.value) || 3 })
        })
      }
    }

    // 4. Disk Assertion事件
    if (part.mode === 'automatic' || part.mode === 'custom') {
      setupRadioContainer('disk-assertion-container', 'disk-assertion-mode', (value) => {
        this.updateModule('partitioning', { diskAssertionMode: value as 'skip' | 'script' })
        this.renderPartitioning()
      }, true)

      const assertionScriptInput = contentDiv.querySelector('#config-disk-assertion-script') as any
      if (assertionScriptInput) {
        assertionScriptInput.addEventListener('input', (e: any) => {
          this.updateModule('partitioning', { diskAssertionScript: e.target.value })
        })
      }
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

    // 1. Windows Edition Mode - RadioContainer
    const editionModeRadioHtml = createRadioContainer({
      id: 'windows-edition-mode-container',
      name: 'edition-mode',
      title: 'Windows edition',
      description: '',
      icon: 'key',
      options: [
        {
          value: 'generic',
          label: 'Use a generic product key',
          description: 'Such a key can be used to install Windows, but will not activate it. You can change the product key later.'
        },
        {
          value: 'custom',
          label: 'Enter another product key',
          description: ''
        },
        {
          value: 'interactive',
          label: 'Enter a product key interactively during Windows Setup',
          description: 'You can also enter your key in the autounattend.xml file yourself to avoid disclosing it. To do so, find the <Key>00000-00000-00000-00000-00000</Key> element and replace the text with your own key.'
        },
        {
          value: 'firmware',
          label: 'Use product key stored in BIOS/UEFI firmware',
          description: 'Choose this if your computer came pre-installed with Windows and you want to reuse that license.'
        }
      ],
      selectedValue: edition.mode === 'key' ? 'custom' : edition.mode === 'index' || edition.mode === 'name' ? 'generic' : edition.mode,
      expanded: true
    })

    // 2. Generic模式 - 选择Windows版本
    const genericEditionSelectHtml = (edition.mode === 'index' || edition.mode === 'name' || edition.mode === 'generic')
      ? createComboCard({
        id: 'config-windows-edition-card',
        title: 'Install this edition of Windows',
        icon: 'package',
        controlType: 'select',
        selectOptions: preset.windowsEditions.map(e => ({ value: e.id, label: e.name })),
        value: edition.editionName || 'pro'
      })
      : ''

    // 3. Custom模式 - 输入产品密钥
    const customProductKeyHtml = edition.mode === 'key'
      ? `<div class="card">
          <div class="card-left">
            <div class="card-content">
              <label style="display: block; margin-bottom: 6px; font-weight: 600;">Use this product key:</label>
              <fluent-text-field id="config-product-key" value="${edition.productKey || 'VK7JG-NPHTM-C97JM-9MPGT-3V66T'}" placeholder="XXXXX-XXXXX-XXXXX-XXXXX-XXXXX" maxlength="29" pattern="^([A-Z0-9]{5}-){4}[A-Z0-9]{5}$" style="width: 100%;"></fluent-text-field>
            </div>
          </div>
        </div>`
      : ''

    // 4. Source Image Mode - RadioContainer
    const sourceImageModeRadioHtml = createRadioContainer({
      id: 'source-image-mode-container',
      name: 'source-image-mode',
      title: 'Source image',
      description: 'Run Get-WindowsImage -ImagePath "…\\install.wim" in PowerShell to learn the name and index of an image inside a .wim file.',
      icon: 'disc',
      options: [
        {
          value: 'automatic',
          label: 'Select image according to the product key',
          description: ''
        },
        {
          value: 'index',
          label: 'Select image with this index',
          description: ''
        },
        {
          value: 'name',
          label: 'Select image with this name',
          description: ''
        }
      ],
      selectedValue: source.mode || 'automatic',
      expanded: true
    })

    // 5. Index模式 - 输入索引
    const indexInputHtml = source.mode === 'index'
      ? `<div class="card">
          <div class="card-left">
            <div class="card-content">
              <fluent-text-field id="config-source-image-index" type="number" value="${source.imageIndex || 1}" min="1" style="width: 100%;"></fluent-text-field>
            </div>
          </div>
        </div>`
      : ''

    // 6. Name模式 - 输入名称
    const nameInputHtml = source.mode === 'name'
      ? `<div class="card">
          <div class="card-left">
            <div class="card-content">
              <fluent-text-field id="config-source-image-name" value="${source.imageName || 'Windows 11 Pro'}" style="width: 100%;"></fluent-text-field>
            </div>
          </div>
        </div>`
      : ''

    contentDiv.innerHTML = `
      ${editionModeRadioHtml}
      ${genericEditionSelectHtml}
      ${customProductKeyHtml}
      ${sourceImageModeRadioHtml}
      ${indexInputHtml}
      ${nameInputHtml}
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

    // 2. Generic edition select
    if (edition.mode === 'index' || edition.mode === 'name' || edition.mode === 'generic') {
      setupComboCard('config-windows-edition-card', (value) => {
        this.updateModule('windowsEdition', { editionName: value as string, mode: 'name' })
      })
    }

    // 3. Custom product key
    const keyInput = contentDiv.querySelector('#config-product-key') as any
    if (keyInput) {
      keyInput.addEventListener('input', (e: any) => {
        this.updateModule('windowsEdition', { productKey: e.target.value })
      })
    }

    // 4. Source image mode
    setupRadioContainer('source-image-mode-container', 'source-image-mode', (value) => {
      this.updateModule('sourceImage', { mode: value as 'automatic' | 'index' | 'name' })
      this.renderWindowsEditionAndSource()
    }, true)

    // 5. Image index
    const indexInput = contentDiv.querySelector('#config-source-image-index') as any
    if (indexInput) {
      indexInput.addEventListener('input', (e: any) => {
        this.updateModule('sourceImage', { imageIndex: parseInt(e.target.value) || 1 })
      })
    }

    // 6. Image name
    const nameInput = contentDiv.querySelector('#config-source-image-name') as any
    if (nameInput) {
      nameInput.addEventListener('input', (e: any) => {
        this.updateModule('sourceImage', { imageName: e.target.value })
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
            <div class="card-title">File Explorer tweaks</div>
            <div style="display: flex; flex-direction: column; gap: 12px; margin-top: 10px;">
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" ${fe.showFileExtensions ? 'checked' : ''}>
                <span>Show file extensions</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" ${fe.showAllTrayIcons ? 'checked' : ''}>
                <span>Show all tray icons</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" ${fe.hideEdgeFre ? 'checked' : ''}>
                <span>Hide Edge FRE</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" ${fe.disableEdgeStartupBoost ? 'checked' : ''}>
                <span>Disable Edge startup boost</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" ${fe.makeEdgeUninstallable ? 'checked' : ''}>
                <span>Make Edge uninstallable</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" ${fe.deleteEdgeDesktopIcon ? 'checked' : ''}>
                <span>Delete Edge desktop icon</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" ${fe.launchToThisPC ? 'checked' : ''}>
                <span>Launch to This PC</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" ${fe.disableBingResults ? 'checked' : ''}>
                <span>Disable Bing results</span>
              </label>
              <div>
                <label style="display: block; margin-bottom: 6px; font-weight: 600;">Hide files:</label>
                <fluent-select id="config-hide-files" style="width: 100%;">
                  <fluent-option value="hidden" ${fe.hideFiles === 'hidden' ? 'selected' : ''}>Hidden</fluent-option>
                  <fluent-option value="show" ${fe.hideFiles === 'show' ? 'selected' : ''}>Show</fluent-option>
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
            <div class="card-expandable-title">Start menu and taskbar</div>
          </div>
          <div class="card-expandable-arrow">
            <i data-lucide="chevron-down"></i>
          </div>
        </div>
        <div class="card-expandable-content">
          <div style="display: flex; flex-direction: column; gap: 12px;">
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" ${st.leftTaskbar ? 'checked' : ''}>
              <span>Left taskbar</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" ${st.hideTaskViewButton ? 'checked' : ''}>
              <span>Hide Task View button</span>
            </label>
            <div>
              <label style="display: block; margin-bottom: 6px; font-weight: 600;">Taskbar search:</label>
              <fluent-select id="config-taskbar-search" style="width: 100%;">
                <fluent-option value="hide" ${st.taskbarSearch === 'hide' ? 'selected' : ''}>Hide</fluent-option>
                <fluent-option value="icon" ${st.taskbarSearch === 'icon' ? 'selected' : ''}>Icon</fluent-option>
                <fluent-option value="box" ${st.taskbarSearch === 'box' ? 'selected' : ''}>Box</fluent-option>
                <fluent-option value="label" ${st.taskbarSearch === 'label' ? 'selected' : ''}>Label</fluent-option>
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
            <div class="card-expandable-title">System tweaks</div>
          </div>
          <div class="card-expandable-arrow">
            <i data-lucide="chevron-down"></i>
          </div>
        </div>
        <div class="card-expandable-content">
          <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 12px;">
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="enableLongPaths" ${tweaks.enableLongPaths ? 'checked' : ''}>
              <span>Enable long paths</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="enableRemoteDesktop" ${tweaks.enableRemoteDesktop ? 'checked' : ''}>
              <span>Enable Remote Desktop</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="hardenSystemDriveAcl" ${tweaks.hardenSystemDriveAcl ? 'checked' : ''}>
              <span>Harden system drive ACL</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="deleteJunctions" ${tweaks.deleteJunctions ? 'checked' : ''}>
              <span>Delete junctions</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="allowPowerShellScripts" ${tweaks.allowPowerShellScripts ? 'checked' : ''}>
              <span>Allow PowerShell scripts</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableLastAccess" ${tweaks.disableLastAccess ? 'checked' : ''}>
              <span>Disable last access</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="preventAutomaticReboot" ${tweaks.preventAutomaticReboot ? 'checked' : ''}>
              <span>Prevent automatic reboot</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableDefender" ${tweaks.disableDefender ? 'checked' : ''}>
              <span>Disable Defender</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableSac" ${tweaks.disableSac ? 'checked' : ''}>
              <span>Disable SAC</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableUac" ${tweaks.disableUac ? 'checked' : ''}>
              <span>Disable UAC</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableSmartScreen" ${tweaks.disableSmartScreen ? 'checked' : ''}>
              <span>Disable SmartScreen</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableSystemRestore" ${tweaks.disableSystemRestore ? 'checked' : ''}>
              <span>Disable System Restore</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableFastStartup" ${tweaks.disableFastStartup ? 'checked' : ''}>
              <span>Disable fast startup</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="turnOffSystemSounds" ${tweaks.turnOffSystemSounds ? 'checked' : ''}>
              <span>Turn off system sounds</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableAppSuggestions" ${tweaks.disableAppSuggestions ? 'checked' : ''}>
              <span>Disable app suggestions</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableWidgets" ${tweaks.disableWidgets ? 'checked' : ''}>
              <span>Disable widgets</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="preventDeviceEncryption" ${tweaks.preventDeviceEncryption ? 'checked' : ''}>
              <span>Prevent device encryption</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="classicContextMenu" ${tweaks.classicContextMenu ? 'checked' : ''}>
              <span>Classic context menu</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableWindowsUpdate" ${tweaks.disableWindowsUpdate ? 'checked' : ''}>
              <span>Disable Windows Update</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disablePointerPrecision" ${tweaks.disablePointerPrecision ? 'checked' : ''}>
              <span>Disable pointer precision</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="deleteWindowsOld" ${tweaks.deleteWindowsOld ? 'checked' : ''}>
              <span>Delete Windows.old</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="disableCoreIsolation" ${tweaks.disableCoreIsolation ? 'checked' : ''}>
              <span>Disable Core Isolation</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" class="tweak-checkbox" data-key="showEndTask" ${tweaks.showEndTask ? 'checked' : ''}>
              <span>Show End Task</span>
            </label>
          </div>
        </div>
      </div>
      
      <div class="card-expandable expanded">
        <div class="card-expandable-header">
          <div class="card-expandable-header-left">
            <i data-lucide="trash-2" class="card-icon"></i>
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
      
      <div class="card">
        <div class="card-left">
          <i data-lucide="shield-check" class="card-icon"></i>
          <div class="card-content">
            <div class="card-title">Express settings</div>
            <div style="display: flex; gap: 20px; margin-top: 10px;">
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="express-settings-mode" value="interactive" ${express === 'interactive' ? 'checked' : ''}>
                <span>Interactive</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="express-settings-mode" value="enableAll" ${express === 'enableAll' ? 'checked' : ''}>
                <span>Enable all</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="express-settings-mode" value="disableAll" ${express === 'disableAll' ? 'checked' : ''}>
                <span>Disable all</span>
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
            <div class="card-title">Visual effects</div>
            <div class="card-description" style="margin-top: 8px;">Visual effects configuration (TODO: implement detailed options)</div>
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
            <div class="card-title">Desktop icons</div>
            <div style="display: flex; gap: 20px; margin-top: 10px;">
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="desktop-icons-mode" value="default" ${icons.mode === 'default' ? 'checked' : ''}>
                <span>Default desktop icons</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="desktop-icons-mode" value="custom" ${icons.mode === 'custom' ? 'checked' : ''}>
                <span>Custom desktop icons</span>
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
            <div class="card-title">Folders on Start</div>
            <div class="card-description" style="margin-top: 8px;">Start menu folders configuration (TODO: implement folder selection)</div>
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

    // 1. Wi-Fi Mode - RadioContainer
    const wifiModeRadioHtml = createRadioContainer({
      id: 'wifi-mode-container',
      name: 'wifi-mode',
      title: 'WLAN / Wi-Fi setup',
      description: '',
      icon: 'wifi',
      options: [
        {
          value: 'interactive',
          label: 'Configure Wi-Fi interactively during Windows Setup',
          description: ''
        },
        {
          value: 'skip',
          label: 'Skip Wi-Fi configuration',
          description: 'Choose this if you have a wired connection to the internet.'
        },
        {
          value: 'unattended',
          label: 'Configure Wi-Fi using these settings',
          description: ''
        },
        {
          value: 'fromProfile',
          label: 'Configure Wi-Fi using an XML file created by netsh.exe wlan export profile key=clear on another computer',
          description: ''
        }
      ],
      selectedValue: wifi.mode || 'interactive',
      expanded: true
    })

    // 2. Unattended模式 - 显示配置选项
    const unattendedSettingsHtml = wifi.mode === 'unattended'
      ? `<div class="card">
          <div class="card-left">
            <i data-lucide="settings" class="card-icon"></i>
            <div class="card-content">
              <div class="card-title">Wi-Fi Network Settings</div>
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px;">
                <div style="grid-column: 1 / -1;">
                  <label style="display: block; margin-bottom: 6px; font-weight: 600;">Network name (SSID):</label>
                  <fluent-text-field id="config-wifi-ssid" value="${wifi.ssid || ''}" maxlength="32" style="width: 100%;"></fluent-text-field>
                </div>
                <div>
                  <label style="display: block; margin-bottom: 6px; font-weight: 600;">Authentication:</label>
                  <fluent-select id="config-wifi-auth" style="width: 100%;">
                    <fluent-option value="Open" ${wifi.authentication === 'Open' || !wifi.authentication ? 'selected' : ''}>Open</fluent-option>
                    <fluent-option value="WPA2PSK" ${wifi.authentication === 'WPA2PSK' ? 'selected' : ''}>WPA2-Personal AES</fluent-option>
                    <fluent-option value="WPA3SAE" ${wifi.authentication === 'WPA3SAE' ? 'selected' : ''}>WPA3-Personal AES</fluent-option>
                  </fluent-select>
                </div>
                <div>
                  <label style="display: block; margin-bottom: 6px; font-weight: 600;">Password:</label>
                  <fluent-text-field id="config-wifi-password" type="password" value="${wifi.password || '00000000'}" maxlength="63" ${wifi.authentication === 'Open' ? 'disabled' : ''} style="width: 100%;"></fluent-text-field>
                </div>
              </div>
              <div style="margin-top: 12px;">
                <fluent-checkbox id="config-wifi-non-broadcast" ${wifi.nonBroadcast ? 'checked' : ''}>Connect even if not broadcasting</fluent-checkbox>
              </div>
              <div class="card-description" style="margin-top: 12px;">
                <p>If both your Wi-Fi router and your computer's Wi-Fi adapter support it, make sure to select WPA3. Otherwise, Windows Setup will try to switch from WPA2 to WPA3 and require manual interaction.</p>
                <p>You should not enter your actual Wi-Fi password here. Once you have downloaded the autounattend.xml file, find the password enclosed in &lt;keyMaterial&gt;…&lt;/keyMaterial&gt; and adjust it.</p>
              </div>
            </div>
          </div>
        </div>`
      : ''

    // 3. FromProfile模式 - XML输入
    const fromProfileHtml = wifi.mode === 'fromProfile'
      ? `<div class="card">
          <div class="card-left">
            <i data-lucide="code" class="card-icon"></i>
            <div class="card-content">
              <div class="card-title">WLAN Profile XML</div>
              <fluent-text-area id="config-wifi-profile-xml" style="width: 100%; min-height: 480px; font-family: 'Consolas', 'Monaco', monospace;" rows="29">${wifi.profileXml || `<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
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
</WLANProfile>`}</fluent-text-area>
            </div>
          </div>
        </div>`
      : ''

    contentDiv.innerHTML = `
      ${wifiModeRadioHtml}
      ${unattendedSettingsHtml}
      ${fromProfileHtml}
    `

    // === 事件监听设置 ===

    // 1. Wi-Fi mode
    setupRadioContainer('wifi-mode-container', 'wifi-mode', (value) => {
      this.updateModule('wifi', { mode: value as 'interactive' | 'skip' | 'unattended' | 'fromProfile' })
      this.renderWifi()
    }, true)

    // 2. Unattended设置
    if (wifi.mode === 'unattended') {
      const ssidInput = contentDiv.querySelector('#config-wifi-ssid') as any
      if (ssidInput) {
        ssidInput.addEventListener('input', (e: any) => {
          this.updateModule('wifi', { ssid: e.target.value })
        })
      }

      const authSelect = contentDiv.querySelector('#config-wifi-auth') as any
      if (authSelect) {
        authSelect.addEventListener('change', (e: any) => {
          this.updateModule('wifi', { authentication: e.target.value })
          this.renderWifi() // 重新渲染以启用/禁用密码字段
        })
      }

      const passwordInput = contentDiv.querySelector('#config-wifi-password') as any
      if (passwordInput) {
        passwordInput.addEventListener('input', (e: any) => {
          this.updateModule('wifi', { password: e.target.value })
        })
      }

      const nonBroadcastCheck = contentDiv.querySelector('#config-wifi-non-broadcast') as any
      if (nonBroadcastCheck) {
        nonBroadcastCheck.addEventListener('change', () => {
          this.updateModule('wifi', { nonBroadcast: nonBroadcastCheck.checked })
        })
      }
    }

    // 3. FromProfile XML
    const profileXmlInput = contentDiv.querySelector('#config-wifi-profile-xml') as any
    if (profileXmlInput) {
      profileXmlInput.addEventListener('input', (e: any) => {
        this.updateModule('wifi', { profileXml: e.target.value })
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
            <div class="card-title">Lock key settings</div>
            <div style="display: flex; gap: 20px; margin-top: 10px; flex-direction: column;">
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="lock-keys-mode" value="skip" ${lockKeys.mode === 'skip' ? 'checked' : ''}>
                <span>Do not configure lock keys</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="lock-keys-mode" value="configure" ${lockKeys.mode === 'configure' ? 'checked' : ''}>
                <span>Configure lock keys</span>
              </label>
            </div>
          </div>
        </div>
      </div>
      ${lockKeys.mode === 'configure' ? `
        <div class="card-expandable expanded">
          <div class="card-expandable-header">
            <div class="card-expandable-header-left">
              <div class="card-expandable-title">Lock key configuration</div>
            </div>
            <div class="card-expandable-arrow">
              <i data-lucide="chevron-down"></i>
            </div>
          </div>
          <div class="card-expandable-content">
            <div class="card-description">Lock key settings (TODO: implement key list editor)</div>
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
            <div class="card-title">Sticky keys</div>
            <div style="display: flex; gap: 20px; margin-top: 10px; flex-direction: column;">
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="sticky-keys-mode" value="default" ${sticky.mode === 'default' ? 'checked' : ''}>
                <span>Default sticky keys</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="sticky-keys-mode" value="disabled" ${sticky.mode === 'disabled' ? 'checked' : ''}>
                <span>Disabled sticky keys</span>
              </label>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" name="sticky-keys-mode" value="custom" ${sticky.mode === 'custom' ? 'checked' : ''}>
                <span>Custom sticky keys</span>
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
            <div class="card-expandable-title">Personalization settings</div>
          </div>
          <div class="card-expandable-arrow">
            <i data-lucide="chevron-down"></i>
          </div>
        </div>
        <div class="card-expandable-content">
          <div style="display: flex; flex-direction: column; gap: 16px;">
            <div>
              <div class="card-title">Wallpaper</div>
              <div style="display: flex; gap: 20px; margin-top: 10px; flex-direction: column;">
                <label style="display: flex; align-items: center; gap: 8px;">
                  <input type="radio" name="wallpaper-mode" value="default" ${pers.wallpaperMode === 'default' ? 'checked' : ''}>
                  <span>Default wallpaper</span>
                </label>
                <label style="display: flex; align-items: center; gap: 8px;">
                  <input type="radio" name="wallpaper-mode" value="solid" ${pers.wallpaperMode === 'solid' ? 'checked' : ''}>
                  <span>Solid color wallpaper</span>
                </label>
                <label style="display: flex; align-items: center; gap: 8px;">
                  <input type="radio" name="wallpaper-mode" value="script" ${pers.wallpaperMode === 'script' ? 'checked' : ''}>
                  <span>Use PowerShell script to load wallpaper</span>
                </label>
              </div>
              ${pers.wallpaperMode === 'solid' ? `
                <div style="margin-top: 12px;">
                  <label style="display: block; margin-bottom: 6px; font-weight: 600;">Color (hex):</label>
                  <fluent-text-field id="config-wallpaper-color" value="${pers.wallpaperColor || '#000000'}" placeholder="#000000" style="width: 100%;"></fluent-text-field>
                </div>
              ` : ''}
              ${pers.wallpaperMode === 'script' ? `
                <div style="margin-top: 12px;">
                  <label style="display: block; margin-bottom: 6px; font-weight: 600;">PowerShell script:</label>
                  <textarea id="config-wallpaper-script" style="width: 100%; min-height: 100px; padding: 8px; font-family: monospace; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary);">${pers.wallpaperScript || ''}</textarea>
                </div>
              ` : ''}
            </div>
            <div>
              <div class="card-title">Lock screen</div>
              <div style="display: flex; gap: 20px; margin-top: 10px; flex-direction: column;">
                <label style="display: flex; align-items: center; gap: 8px;">
                  <input type="radio" name="lockscreen-mode" value="default" ${pers.lockScreenMode === 'default' ? 'checked' : ''}>
                  <span>Default lock screen</span>
                </label>
                <label style="display: flex; align-items: center; gap: 8px;">
                  <input type="radio" name="lockscreen-mode" value="script" ${pers.lockScreenMode === 'script' ? 'checked' : ''}>
                  <span>Use PowerShell script to load lock screen image</span>
                </label>
              </div>
              ${pers.lockScreenMode === 'script' ? `
                <div style="margin-top: 12px;">
                  <label style="display: block; margin-bottom: 6px; font-weight: 600;">PowerShell script:</label>
                  <textarea id="config-lockscreen-script" style="width: 100%; min-height: 100px; padding: 8px; font-family: monospace; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary);">${pers.lockScreenScript || ''}</textarea>
                </div>
              ` : ''}
            </div>
            <div>
              <div class="card-title">Color</div>
              <div style="display: flex; gap: 20px; margin-top: 10px; flex-direction: column;">
                <label style="display: flex; align-items: center; gap: 8px;">
                  <input type="radio" name="color-mode" value="default" ${pers.colorMode === 'default' ? 'checked' : ''}>
                  <span>Default color</span>
                </label>
                <label style="display: flex; align-items: center; gap: 8px;">
                  <input type="radio" name="color-mode" value="custom" ${pers.colorMode === 'custom' ? 'checked' : ''}>
                  <span>Custom accent color</span>
                </label>
              </div>
              ${pers.colorMode === 'custom' ? `
                <div style="margin-top: 12px;">
                  <label style="display: block; margin-bottom: 6px; font-weight: 600;">Accent color (hex):</label>
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
  }
  return configManager
}

export function getConfigManager(): UnattendConfigManager | null {
  return configManager
}

export type { UnattendConfig }
export { PRESET_DATA, createDefaultConfig }

