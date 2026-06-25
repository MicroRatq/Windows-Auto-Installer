/**
 * 自定义配置工作区
 * 实现 autounattend.xml 配置功能
 */

import {
  createRadioContainer,
  setupRadioContainer,
  createComboCard,
  setupComboCard,
  createComboContainer,
  setupComboContainer,
  registerSubPageSystemReset,
  setWorkspaceTitleBreadcrumb,
  setWorkspaceTitleText,
  createMultiColumnCheckboxContainer,
  setupMultiColumnCheckboxContainer,
  setupTextCard,
  getTextCardValue,
  setTextCardValue,
  createDynamicListContainer,
  setupDynamicListContainer,
  showWorkspaceConfirmDialog,
  showWorkspaceMessageDialog,
  rememberSubPageReturnPosition,
  restoreSubPageReturnPosition,
  clearSubPageReturnPosition,
  type DynamicListItem,
  type ComboContainerConfig
} from './workspace'
import { t } from './i18n'
import { templateManager } from './iso-burn'

// ========================================
// 配置数据结构定义
// ========================================

// 区域和语言设置
interface LanguageSettings {
  mode: 'interactive' | 'unattended'
  uiLanguage?: string // Windows显示语言
  systemLocale?: string // 用户区域（与后端字段名对齐）
  inputLocale?: string // 键盘布局（与后端字段名对齐）
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
  disableOobePrivacyPrompts: boolean
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

// 时区设置
interface TimeZoneSettings {
  mode: 'implicit' | 'explicit'
  timeZone?: string
}

// 分区和格式化设置
interface PartitionSettings {
  mode: 'interactive' | 'automatic' | 'custom'
  targetDisk?: number // 目标磁盘索引（0-based）
  layout?: 'MBR' | 'GPT'
  espSize?: number // ESP分区大小 (MB)，默认300
  recoveryMode?: 'partition' | 'folder' | 'none'
  recoverySize?: number // Recovery分区大小 (MB)，默认1000
  diskpartScript?: string
  diskAssertionMode?: 'skip' | 'script' // 磁盘断言模式
  diskAssertionScript?: string // 磁盘断言脚本
}

// Windows版本设置
interface EditionSettings {
  mode: 'interactive' | 'firmware' | 'key' | 'index' | 'name' | 'generic'
  productKey?: string
  editionIndex?: number
  editionName?: string
}

// Windows PE操作设置
interface PESettings {
  mode: 'default' | 'generated' | 'script' | 'custom' // 'custom' 仅用于导入兼容
  cmdScript?: string
  disable8Dot3Names?: boolean // Generated模式下的选项
  pauseBeforeFormatting?: boolean
  pauseBeforeReboot?: boolean
  compactOs?: boolean
  disableDefender?: boolean
  injectVirtioStorageDrivers?: boolean
}

// 用户账户设置
interface Account {
  id: string // UUID
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
  lockoutWindow?: number
}

// 文件资源管理器调整
interface FileExplorer {
  showFileExtensions: boolean
  hideFiles: 'hidden' | 'hiddenSystem' | 'none'
  launchToThisPC: boolean
  classicContextMenu: boolean
  showEndTask: boolean
  hideRecentInQuickAccess: boolean
  hideFrequentInQuickAccess: boolean
  hideCloudFilesInQuickAccess: boolean
  hideRecommendations: boolean
  navigationPane: ExplorerCategoryVisibility
  folderDialog: ExplorerCategoryVisibility
}

interface ExplorerCategoryVisibility {
  hideDesktop: boolean
  hideDocuments: boolean
  hideDownloads: boolean
  hideMusic: boolean
  hidePictures: boolean
  hideVideos: boolean
  hideGallery: boolean
  hideHome: boolean
  hideLibraries: boolean
  hideNetwork: boolean
  hideUserProfile: boolean
}

// 开始菜单和任务栏设置
interface StartMenuTaskbarSettings {
  leftTaskbar: boolean
  hideTaskViewButton: boolean
  taskbarSearch: 'hide' | 'icon' | 'box' | 'label'
  disableWidgets: boolean
  showAllTrayIcons: boolean
  disableBingResults: boolean
  startTilesMode: 'default' | 'empty' | 'custom'
  startTilesXml?: string
  startPinsMode: 'default' | 'empty' | 'custom'
  startPinsJson?: string
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
  disableSac: boolean
  disableUac: boolean
  disableSmartScreen: boolean
  disableSystemRestore: boolean
  disableFastStartup: boolean
  turnOffSystemSounds: boolean
  disableAppSuggestions: boolean
  disableWidgets: boolean
  preventDeviceEncryption: boolean
  disableWindowsUpdate: boolean
  disablePointerPrecision: boolean
  deleteWindowsOld: boolean
  disableCoreIsolation: boolean
}

// 视觉效果
interface VisualEffects {
  mode: 'default' | 'appearance' | 'performance' | 'custom'
  controlAnimations?: boolean
  animateMinMax?: boolean
  taskbarAnimations?: boolean
  dwmAeroPeekEnabled?: boolean
  menuAnimation?: boolean
  tooltipAnimation?: boolean
  selectionFade?: boolean
  dwmSaveThumbnailEnabled?: boolean
  cursorShadow?: boolean
  listviewShadow?: boolean
  thumbnailsOrIcon?: boolean
  listviewAlphaSelect?: boolean
  dragFullWindows?: boolean
  comboBoxAnimation?: boolean
  fontSmoothing?: boolean
  listBoxSmoothScrolling?: boolean
  dropShadow?: boolean
}

// 桌面图标设置
interface DesktopIconSettings {
  mode: 'default' | 'custom'
  deleteEdgeDesktopIcon: boolean
  iconControlPanel?: boolean
  iconDesktop?: boolean
  iconDocuments?: boolean
  iconDownloads?: boolean
  iconGallery?: boolean
  iconHome?: boolean
  iconMusic?: boolean
  iconNetwork?: boolean
  iconPictures?: boolean
  iconRecycleBin?: boolean
  iconThisPC?: boolean
  iconUserFiles?: boolean
  iconVideos?: boolean
}

// 开始菜单文件夹设置
interface StartFolderSettings {
  mode: 'default' | 'custom'
  folders?: {
    Settings?: boolean
    FileExplorer?: boolean
    Documents?: boolean
    Downloads?: boolean
    Music?: boolean
    Pictures?: boolean
    Videos?: boolean
    Network?: boolean
    PersonalFolder?: boolean
  }
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
  hidden?: boolean
}

// 快速设置
type ExpressSettingsMode = 'interactive' | 'enableAll' | 'disableAll'

// 锁定键设置
interface LockKeySettings {
  mode: 'skip' | 'configure'
  capsLockInitial?: 'off' | 'on'
  capsLockBehavior?: 'toggle' | 'ignore'
  numLockInitial?: 'off' | 'on'
  numLockBehavior?: 'toggle' | 'ignore'
  scrollLockInitial?: 'off' | 'on'
  scrollLockBehavior?: 'toggle' | 'ignore'
}

// 粘滞键设置
interface StickyKeysSettings {
  mode: 'default' | 'disabled' | 'custom'
  stickyKeysHotKeyActive?: boolean
  stickyKeysHotKeySound?: boolean
  stickyKeysIndicator?: boolean
  stickyKeysAudibleFeedback?: boolean
  stickyKeysTriState?: boolean
  stickyKeysTwoKeysOff?: boolean
}

// 个性化设置
interface PersonalizationSettings {
  wallpaper: {
    mode: 'default' | 'solid' | 'script'
    color?: string
    script?: string
  }
  lockScreen: {
    mode: 'default' | 'script'
    script?: string
  }
  color: {
    mode: 'default' | 'custom'
    systemTheme?: 'dark' | 'light'
    appsTheme?: 'dark' | 'light'
    accentColor?: string
    accentColorOnStart?: boolean
    accentColorOnBorders?: boolean
    enableTransparency?: boolean
  }
}

// 预装软件移除
interface BloatwareSettings {
  items: string[]
}

// 自定义脚本
interface ScriptItem {
  id: string // UUID
  type: string
  content: string
}

interface ScriptSettings {
  system: ScriptItem[]
  defaultUser: ScriptItem[]
  firstLogon: ScriptItem[]
  userOnce: ScriptItem[]
  restartExplorer: boolean
}

// AppLocker
interface AppLockerSettings {
  mode: 'skip' | 'configure'
  policyXml?: string
}

// XML标记
interface XmlMarkupComponent {
  id: string // UUID
  component: string
  pass: string
  markup: string
}

interface XmlMarkupSettings {
  components: XmlMarkupComponent[]
}

// 完整配置对象
interface UnattendConfig {
  languageSettings: LanguageSettings
  processorArchitectures: ProcessorArchitecture[]
  setupSettings: SetupSettings
  computerName: ComputerNameSettings
  timeZone: TimeZoneSettings
  partitioning: PartitionSettings
  windowsEdition: EditionSettings
  peSettings: PESettings
  accountSettings: AccountSettings
  passwordExpiration: PasswordExpirationSettings
  lockoutSettings: LockoutSettings
  fileExplorer: FileExplorer
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
  appLocker: AppLockerSettings
  xmlMarkup: XmlMarkupSettings
}

// ========================================
// 预设数据由后端提供（动态加载）
// ========================================

type PresetData = {
  languages: Array<{ id: string; name: string }>
  locales: Array<{ id: string; name: string }>
  keyboards: Array<{ id: string; name: string; type?: string }>
  defaultInputProfiles: Array<{ id: string; name: string; primaryInputProfile: string; allowedInputProfiles: string[] }>
  timeZones: Array<{ id: string; name: string }>
  geoLocations: Array<{ id: string; name: string }>
  windowsEditions: Array<{ id: string; name: string; key?: string; index?: number | null }>
  bloatwareItems: Array<{ id: string; name: string }>
}

const EMPTY_PRESET: PresetData = {
  languages: [],
  locales: [],
  keyboards: [],
  defaultInputProfiles: [],
  timeZones: [],
  geoLocations: [],
  windowsEditions: [],
  bloatwareItems: []
}

const CONFIG_STORAGE_KEY = 'windows-auto-installer.iso-config'

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
      disableOobePrivacyPrompts: false,
      useConfigurationSet: false,
      hidePowerShellWindows: false,
      keepSensitiveFiles: false,
      useNarrator: false
    },
    computerName: {
      mode: 'random'
    },
    timeZone: {
      mode: 'implicit'
    },
    partitioning: {
      mode: 'interactive'
    },
    windowsEdition: {
      mode: 'interactive'
    },
    peSettings: {
      mode: 'default',
      compactOs: false,
      disableDefender: false,
      injectVirtioStorageDrivers: false
    },
    accountSettings: {
      mode: 'interactive-local',
      obscurePasswords: true
    },
    passwordExpiration: {
      mode: 'default'
    },
    lockoutSettings: {
      mode: 'default'
    },
    fileExplorer: {
      showFileExtensions: false,
      hideFiles: 'hidden',
      launchToThisPC: false,
      classicContextMenu: false,
      showEndTask: false,
      hideRecentInQuickAccess: false,
      hideFrequentInQuickAccess: false,
      hideCloudFilesInQuickAccess: false,
      hideRecommendations: false,
      navigationPane: {
        hideDesktop: false,
        hideDocuments: false,
        hideDownloads: false,
        hideMusic: false,
        hidePictures: false,
        hideVideos: false,
        hideGallery: false,
        hideHome: false,
        hideLibraries: false,
        hideNetwork: false,
        hideUserProfile: false
      },
      folderDialog: {
        hideDesktop: false,
        hideDocuments: false,
        hideDownloads: false,
        hideMusic: false,
        hidePictures: false,
        hideVideos: false,
        hideGallery: false,
        hideHome: false,
        hideLibraries: false,
        hideNetwork: false,
        hideUserProfile: false
      }
    },
    startMenuTaskbar: {
      leftTaskbar: false,
      hideTaskViewButton: false,
      taskbarSearch: 'box',
      disableWidgets: false,
      showAllTrayIcons: false,
      disableBingResults: false,
      startTilesMode: 'default',
      startPinsMode: 'default'
    },
    systemTweaks: {
      enableLongPaths: false,
      enableRemoteDesktop: false,
      hardenSystemDriveAcl: false,
      deleteJunctions: false,
      allowPowerShellScripts: false,
      disableLastAccess: false,
      preventAutomaticReboot: false,
      disableSac: false,
      disableUac: false,
      disableSmartScreen: false,
      disableSystemRestore: false,
      disableFastStartup: false,
      turnOffSystemSounds: false,
      disableAppSuggestions: false,
      disableWidgets: false,
      preventDeviceEncryption: false,
      disableWindowsUpdate: false,
      disablePointerPrecision: false,
      deleteWindowsOld: false,
      disableCoreIsolation: false
    },
    visualEffects: {
      mode: 'default'
    },
    desktopIcons: {
      mode: 'default',
      deleteEdgeDesktopIcon: false
    },
    startFolders: {
      mode: 'default'
    },
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
      wallpaper: {
        mode: 'default'
      },
      lockScreen: {
        mode: 'default'
      },
      color: {
        mode: 'default'
      }
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
    appLocker: {
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
  private presetData: PresetData = EMPTY_PRESET
  private activeUiPersonalizationSubPage: 'file-explorer' | 'start-taskbar' | 'personalization' | null = null
  private uiPersonalizationRootTitle = ''
  private workspaceTitleListenerBound = false

  constructor() {
    this.config = this.loadPersistedConfig()
  }

  // 获取配置
  getConfig(): UnattendConfig {
    return this.cloneConfig(this.config)
  }

  private cloneConfig<T>(value: T): T {
    return JSON.parse(JSON.stringify(value)) as T
  }

  private normalizeAccount(account: Partial<Account> | undefined): Account {
    return {
      id: account?.id || this.generateUUID(),
      name: account?.name || '',
      displayName: account?.displayName || '',
      password: account?.password || '',
      group: account?.group === 'Administrators' ? 'Administrators' : 'Users'
    }
  }

  private normalizeScriptItem(script: Partial<ScriptItem> | undefined): ScriptItem {
    return {
      id: script?.id || this.generateUUID(),
      type: script?.type || '.ps1',
      content: script?.content || ''
    }
  }

  private normalizeXmlMarkupComponent(component: Partial<XmlMarkupComponent> & { xml?: string } | undefined): XmlMarkupComponent {
    return {
      id: component?.id || this.generateUUID(),
      component: component?.component || '',
      pass: component?.pass || 'specialize',
      markup: component?.markup ?? component?.xml ?? ''
    }
  }

  private normalizeConfig(config: Partial<UnattendConfig> | null | undefined): UnattendConfig {
    const merged = this.deepMerge(createDefaultConfig(), this.cloneConfig(config || {})) as UnattendConfig

    const legacyCompactOS = (config as { compactOS?: unknown } | null | undefined)?.compactOS
    if (typeof legacyCompactOS === 'string') {
      merged.peSettings.compactOs = legacyCompactOS === 'enabled'
    }

    const legacyWdac = (config as { wdac?: Partial<AppLockerSettings> | null } | null | undefined)?.wdac
    if (legacyWdac && typeof legacyWdac === 'object' && typeof legacyWdac.policyXml === 'string' && legacyWdac.policyXml.trim()) {
      merged.appLocker.mode = 'configure'
      merged.appLocker.policyXml = legacyWdac.policyXml
    }

    merged.appLocker.mode = merged.appLocker.mode || 'skip'

    merged.peSettings.compactOs = Boolean(merged.peSettings.compactOs)
    merged.peSettings.injectVirtioStorageDrivers = Boolean(merged.peSettings.injectVirtioStorageDrivers)

    merged.accountSettings.accounts = Array.isArray(merged.accountSettings.accounts)
      ? merged.accountSettings.accounts.map(account => this.normalizeAccount(account))
      : []

    merged.scripts.system = Array.isArray(merged.scripts.system)
      ? merged.scripts.system.map(item => this.normalizeScriptItem(item))
      : []
    merged.scripts.defaultUser = Array.isArray(merged.scripts.defaultUser)
      ? merged.scripts.defaultUser.map(item => this.normalizeScriptItem(item))
      : []
    merged.scripts.firstLogon = Array.isArray(merged.scripts.firstLogon)
      ? merged.scripts.firstLogon.map(item => this.normalizeScriptItem(item))
      : []
    merged.scripts.userOnce = Array.isArray(merged.scripts.userOnce)
      ? merged.scripts.userOnce.map(item => this.normalizeScriptItem(item))
      : []

    merged.xmlMarkup.components = Array.isArray(merged.xmlMarkup.components)
      ? merged.xmlMarkup.components.map(component => this.normalizeXmlMarkupComponent(component as XmlMarkupComponent & { xml?: string }))
      : []

    return merged
  }

  private persistConfig() {
    try {
      localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(this.config))
    } catch (error) {
      console.error('Persist iso-config failed:', error)
    }
  }

  private loadPersistedConfig(): UnattendConfig {
    try {
      const raw = localStorage.getItem(CONFIG_STORAGE_KEY)
      if (!raw) {
        return createDefaultConfig()
      }

      return this.normalizeConfig(JSON.parse(raw) as Partial<UnattendConfig>)
    } catch (error) {
      console.error('Load persisted iso-config failed:', error)
      return createDefaultConfig()
    }
  }

  // 深度合并辅助函数
  private isObject(item: any): boolean {
    return item && typeof item === 'object' && !Array.isArray(item)
  }

  private deepMerge(target: any, source: any): any {
    const output = { ...target }
    if (this.isObject(target) && this.isObject(source)) {
      Object.keys(source).forEach(key => {
        if (this.isObject(source[key]) && !Array.isArray(source[key])) {
          if (!(key in target)) {
            Object.assign(output, { [key]: source[key] })
          } else {
            output[key] = this.deepMerge(target[key], source[key])
          }
        } else {
          Object.assign(output, { [key]: source[key] })
        }
      })
    }
    return output
  }

  // 更新配置
  updateConfig(updates: Partial<UnattendConfig>) {
    this.config = this.normalizeConfig(this.deepMerge(this.config, updates))
    this.persistConfig()
  }


  // 更新特定模块配置
  updateModule<K extends keyof UnattendConfig>(
    module: K,
    updates: Partial<UnattendConfig[K]>
  ) {
    const current = this.config[module]
    if (current && this.isObject(current)) {
      this.config[module] = this.deepMerge(current, updates) as UnattendConfig[K]
    } else {
      this.config[module] = updates as UnattendConfig[K]
    }
    this.config = this.normalizeConfig(this.config)
    this.persistConfig()
  }

  // 获取预设数据
  getPresetData() {
    return this.presetData || EMPTY_PRESET
  }

  private getAutoUiLanguage(): string | null {
    const preset = this.getPresetData()
    const templateLang = templateManager.getTemplate()?.language
    if (templateLang) {
      const normalized = templateLang.toLowerCase().replace(/^(\w+)-(\w+)$/, (_, a, b) => a.toLowerCase() + '-' + b.toUpperCase())
      const found = preset.languages.find(l => l.id.toLowerCase() === normalized.toLowerCase())
      if (found) return found.id
    }
    return null
  }

  private getFirstLanguageCandidates() {
    const preset = this.getPresetData()
    const localeForLanguage: Record<string, string> = {
      'zh-CN': 'zh-Hans-CN',
      'zh-TW': 'zh-Hant-TW',
    }
    const candidateIds = new Set<string>()
    preset.languages.forEach(lang => {
      const matched = preset.locales.find(l => l.id === lang.id)
      if (matched) { candidateIds.add(matched.id); return }
      const fallback = localeForLanguage[lang.id]
      if (fallback && preset.locales.some(l => l.id === fallback)) { candidateIds.add(fallback); return }
    })
    return preset.locales.filter(l => candidateIds.has(l.id))
  }

  private localeForLanguageId(languageId: string): string {
    const map: Record<string, string> = { 'zh-CN': 'zh-Hans-CN', 'zh-TW': 'zh-Hant-TW' }
    return map[languageId] || languageId
  }

  private languageForLocaleId(localeId: string): string {
    const map: Record<string, string> = { 'zh-Hans-CN': 'zh-CN', 'zh-Hant-TW': 'zh-TW' }
    return map[localeId] || localeId
  }

  private getKeyboardsForLanguage(languageId: string) {
    const preset = this.getPresetData()
    const normalizeKeyboardId = (id?: string) => (id || '').toUpperCase()
    const profileId = this.languageForLocaleId(languageId)
    const profile = preset.defaultInputProfiles.find(p => p.id === profileId)
    const allowedProfiles = profile?.allowedInputProfiles || []
    if (!allowedProfiles.length) return preset.keyboards
    return preset.keyboards.filter(k => {
      const nk = normalizeKeyboardId(k.id)
      return allowedProfiles.some(p => {
        const np = normalizeKeyboardId(p)
        return np === nk || np.endsWith(':' + nk)
      })
    })
  }

  private updateKeyboardSelectForLanguage(firstLanguageId: string) {
    const normalizeKeyboardId = (id?: string) => (id || '').toUpperCase()
    const keyboards = this.getKeyboardsForLanguage(firstLanguageId)
    const select = document.querySelector('#config-first-keyboard-card-control') as any
    if (!select) return
    const currentValue = normalizeKeyboardId(this.config.languageSettings.inputLocale || '')
    const fallback = normalizeKeyboardId(keyboards[0]?.id || '')
    const newValue = keyboards.some(k => normalizeKeyboardId(k.id) === currentValue) ? currentValue : fallback
    select.innerHTML = keyboards.map(k => {
      const sel = normalizeKeyboardId(k.id) === newValue ? ' selected' : ''
      return `<fluent-option value="${k.id}"${sel}>${k.name}</fluent-option>`
    }).join('')
    select.value = newValue
    this.updateModule('languageSettings', { inputLocale: newValue })
  }

  // 异步加载预设数据（从后端获取完整数据）
  private async loadPresetData(triggerRender: boolean = false) {
    if (!window.electronAPI?.sendToBackend) {
      if (triggerRender) this.renderAllModules()
      return
    }
    try {
      const raw = (window as any)?.currentLanguage || navigator.language || 'en'
      const lang = raw.startsWith('zh') ? 'zh' : 'en'
      const request = {
        jsonrpc: '2.0',
        id: Date.now(),
        method: 'unattend_get_data',
        params: { lang }
      }
      const response = await window.electronAPI.sendToBackend(request)
      const result = (response && (response.result ?? response)) || {}
      const keyboards = (result.keyboards || []).map((k: any) => ({
        id: (k.id || '').toUpperCase(),
        name: k.name || k.id || '',
        type: k.type
      }))
      const sortByName = (a: { name: string }, b: { name: string }) =>
        a.name.localeCompare(b.name, 'zh-CN')
      const preset: PresetData = {
        languages: (result.languages || []).sort(sortByName),
        locales: (result.locales || []).sort(sortByName),
        keyboards: keyboards.sort(sortByName),
        defaultInputProfiles: result.defaultInputProfiles || [],
        timeZones: (result.timeZones || []).sort(sortByName),
        geoLocations: (result.geoLocations || []).sort(sortByName),
        windowsEditions: result.windowsEditions || [],
        bloatwareItems: result.bloatwareItems || []
      }
      this.presetData = preset
      if (triggerRender) {
        this.renderAllModules()
      }
      const curTemplate = templateManager.getTemplate()
      if (curTemplate?.language) {
        console.log('[iso-config] loaded preset data, re-checking template')
        this.lastTemplateLang = null
        this.onTemplateChanged(curTemplate)
      }
    } catch (error) {
      console.error('Load preset data failed:', error)
      if (triggerRender) {
        this.renderAllModules()
      }
    }
  }

  // 导入配置（从XML解析）
  async importFromXml(xmlContent: string): Promise<void> {
    if (!window.electronAPI) {
      throw new Error('Electron API 不可用')
    }

    try {
      // 将 XML 内容转换为 base64
      const xmlBase64 = btoa(unescape(encodeURIComponent(xmlContent)))

      const request = {
        jsonrpc: '2.0',
        id: 1,
        method: 'unattend_import_xml',
        params: {
          xml: xmlBase64
        }
      }

      const response = await window.electronAPI.sendToBackend(request)
      if (response.error) {
        throw new Error(response.error.message || '导入失败')
      }

      // 更新配置
      if (response.result?.config) {
        // 完全替换配置，而不是合并（确保导入时使用后端返回的完整配置）
        this.config = this.normalizeConfig(response.result.config as Partial<UnattendConfig>)
        this.persistConfig()
        // 重新渲染所有模块以反映新配置
        this.renderAllModules()
      }
    } catch (error: any) {
      console.error('导入 XML 失败:', error)
      throw error
    }
  }

  // 导出配置（生成XML）
  async exportToXml(): Promise<string> {
    if (!window.electronAPI) {
      throw new Error('Electron API 不可用')
    }

    try {
      const config = this.cloneConfig(this.config)
      if (config.languageSettings.mode === 'unattended') {
        config.languageSettings.uiLanguage = config.languageSettings.uiLanguage || this.getFirstLanguageCandidates()[0]?.id || 'en-US'
        config.languageSettings.systemLocale = config.languageSettings.systemLocale || config.languageSettings.uiLanguage
        if (config.timeZone.mode === 'implicit') {
          delete config.languageSettings.geoLocation
        }
      }
      const request = {
        jsonrpc: '2.0',
        id: 1,
        method: 'unattend_export_xml',
        params: {
          config
        }
      }

      const response = await window.electronAPI.sendToBackend(request)
      if (response.error) {
        throw new Error(response.error.message || '导出失败')
      }

      // 解码 base64 返回的 XML
      if (response.result?.xml) {
        const xmlContent = decodeURIComponent(escape(atob(response.result.xml)))
        return xmlContent
      }

      throw new Error('导出结果为空')
    } catch (error: any) {
      console.error('导出 XML 失败:', error)
      throw error
    }
  }

  // 初始化UI
  init(panelId: string) {
    this.panel = document.getElementById(panelId)
    if (!this.panel) {
      console.error(`Panel ${panelId} not found`)
      return
    }
    this.updateSectionTitles()
    this.setupEventListeners()
    registerSubPageSystemReset(this.panel, () => {
      this.resetUiPersonalizationSubPage()
    })
    templateManager.addListener((template) => {
      this.onTemplateChanged(template)
    })
    this.loadPresetData(true)
  }

  private lastTemplateLang: string | null = null

  private onTemplateChanged(template: { language?: string } | null) {
    const newLang = template?.language || null
    const preset = this.getPresetData()
    console.log('[iso-config] template changed, language:', newLang, 'lastApplied:', this.lastTemplateLang, 'presetLanguages:', preset.languages.length)
    if (!newLang) return
    const normalized = newLang.toLowerCase().replace(/^(\w+)-(\w+)$/, (_, a, b) => a.toLowerCase() + '-' + b.toUpperCase())
    const normalizedLower = normalized.toLowerCase()
    console.log('[iso-config] normalized template language:', newLang, '->', normalized, 'lower:', normalizedLower)
    const found = preset.languages.find(l => l.id.toLowerCase() === normalizedLower)
    if (!found) {
      console.log('[iso-config] template language not in preset. Available:', preset.languages.map(l => l.id).join(', '))
      return
    }
    const uiSelect = document.querySelector('#config-ui-language-card-control') as any
    const flSelect = document.querySelector('#config-first-language-card-control') as any
    if (!uiSelect || !flSelect) { console.log('[iso-config] language selects not in DOM yet, skip'); return }
    if (found.id === this.lastTemplateLang && uiSelect.value === found.id) return
    console.log('[iso-config] applying template language:', found.id)
    this.lastTemplateLang = found.id
    const firstLangId = this.localeForLanguageId(found.id)
    this.updateModule('languageSettings', { uiLanguage: found.id, systemLocale: firstLangId })
    uiSelect.value = found.id
    this.updateFirstLanguageOptions(flSelect, firstLangId)
    this.updateKeyboardSelectForLanguage(firstLangId)
  }

  private updateFirstLanguageOptions(select: any, selectedId: string) {
    const candidates = this.getFirstLanguageCandidates()
    select.innerHTML = candidates.map(l => {
      const sel = l.id === selectedId ? ' selected' : ''
      return `<fluent-option value="${l.id}"${sel}>${l.name}</fluent-option>`
    }).join('')
    select.value = selectedId
  }

  // 渲染UI（已废弃，直接调用renderAllModules）
  // @ts-ignore - 保留以备将来使用
  private render() {
    if (!this.panel) return
    this.renderAllModules()
    this.setupEventListeners()
  }

  // 更新 section 标题的 i18n 翻译
  private updateSectionTitles() {
    if (!this.panel) return

    // 更新 Run custom scripts 标题
    const customScriptsSection = this.panel.querySelector('#config-custom-scripts .section-title') as HTMLElement
    if (customScriptsSection) {
      customScriptsSection.textContent = t('isoConfig.customScripts.title') || 'Run custom scripts'
    }

    // 更新 XML markup for more components 标题
    const xmlMarkupSection = this.panel.querySelector('#config-xml-markup .section-title') as HTMLElement
    if (xmlMarkupSection) {
      xmlMarkupSection.textContent = t('isoConfig.xmlMarkup.title') || 'XML markup for more components'
    }
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

    this.resetUiPersonalizationSubPage()

    // 0. Import and Export cards (在最顶部)
    this.renderImportExport()

    // 1. Windows PE Stage (合并 PE 操作、分区和版本设置)
    this.renderWindowsPEStage()

    // 2. Region, Language and Time Zone (合并模块1和6)
    this.renderRegionLanguageTimeZone()

    // 3. Setup settings
    this.renderSetupSettings()

    // 4. Name and Account (合并模块4、11、12、13)
    this.renderNameAndAccount()

    // 7. UI and Personalization (合并模块14、15、16、17、18、25)
    this.renderFileExplorer()
    this.renderStartTaskbar()
    this.renderVisualEffects()
    this.renderDesktopIcons()
    this.renderFoldersStart()
    this.renderPersonalization()

    // 8. Accessibility Settings (合并模块23、24)
    this.renderLockKeys()
    this.renderStickyKeys()

    // 10. System Optimization (合并模块16、22、26)
    this.renderSystemOptimization()

    // 11. Advanced Settings (合并模块5、20、28)
    this.renderAdvancedSettings()

    // 12. Run custom scripts
    this.renderCustomScripts()

    // 13. XML markup for more components
    this.renderXmlMarkup()
  }

  private getOverviewSections(): HTMLElement[] {
    if (!this.panel) return []

    return Array.from(this.panel.children).filter((child): child is HTMLElement => {
      return child instanceof HTMLElement && child.classList.contains('section')
    })
  }

  private ensureUiPersonalizationSubPageContainer(): HTMLElement | null {
    if (!this.panel) return null

    let container = this.panel.querySelector('#iso-config-ui-personalization-subpage') as HTMLElement | null
    if (container) return container

    container = document.createElement('div')
    container.id = 'iso-config-ui-personalization-subpage'
    container.className = 'ws-subpage-page hidden'
    this.panel.appendChild(container)
    return container
  }

  private resetUiPersonalizationSubPage(restorePosition = false) {
    if (!this.panel) return

    const subPage = this.panel.querySelector('#iso-config-ui-personalization-subpage') as HTMLElement | null
    if (subPage) {
      subPage.classList.add('hidden')
      subPage.innerHTML = ''
    }

    this.getOverviewSections().forEach(section => {
      section.style.display = ''
    })

    if (this.activeUiPersonalizationSubPage) {
      setWorkspaceTitleText(t('menus.isoConfig') || this.uiPersonalizationRootTitle || '自定义配置')
    }

    this.activeUiPersonalizationSubPage = null

    if (restorePosition) {
      restoreSubPageReturnPosition(this.panel)
      return
    }

    clearSubPageReturnPosition(this.panel)
  }

  private openUiPersonalizationSubPage(
    subPageId: 'file-explorer' | 'start-taskbar' | 'personalization',
    sourceEntryId?: string
  ) {
    if (!this.panel) return

    const subPage = this.ensureUiPersonalizationSubPageContainer()
    if (!subPage) return

    const currentTitle = (document.getElementById('workspace-title')?.textContent || '').trim()
    this.uiPersonalizationRootTitle = t('menus.isoConfig') || currentTitle || this.uiPersonalizationRootTitle || '自定义配置'
    this.activeUiPersonalizationSubPage = subPageId

    if (sourceEntryId) {
      rememberSubPageReturnPosition(this.panel, `#${sourceEntryId}`)
    }

    this.getOverviewSections().forEach(section => {
      section.style.display = 'none'
    })

    subPage.classList.remove('hidden')
    if (subPageId === 'file-explorer') {
      setWorkspaceTitleBreadcrumb(this.uiPersonalizationRootTitle, t('isoConfig.uiPersonalization.fileExplorer'))
      this.renderFileExplorerContent(subPage)
      return
    }

    if (subPageId === 'personalization') {
      setWorkspaceTitleBreadcrumb(this.uiPersonalizationRootTitle, t('isoConfig.uiPersonalization.personalization'))
      this.renderPersonalizationSubPageContent(subPage)
      return
    }

    setWorkspaceTitleBreadcrumb(this.uiPersonalizationRootTitle, t('isoConfig.uiPersonalization.startTaskbar'))
    this.renderStartTaskbarContent(subPage)
  }

  private renderFileExplorerContent(contentDiv: HTMLElement) {
    const fe = this.config.fileExplorer
    const navigationPane = fe.navigationPane || {} as ExplorerCategoryVisibility
    const folderDialog = fe.folderDialog || {} as ExplorerCategoryVisibility
    const categoryOptions = [
      { value: 'hideDesktop', label: t('isoConfig.uiPersonalization.iconDesktop') },
      { value: 'hideDocuments', label: t('isoConfig.uiPersonalization.iconDocuments') },
      { value: 'hideDownloads', label: t('isoConfig.uiPersonalization.iconDownloads') },
      { value: 'hideMusic', label: t('isoConfig.uiPersonalization.iconMusic') },
      { value: 'hidePictures', label: t('isoConfig.uiPersonalization.iconPictures') },
      { value: 'hideVideos', label: t('isoConfig.uiPersonalization.iconVideos') },
      { value: 'hideGallery', label: t('isoConfig.uiPersonalization.iconGallery') },
      { value: 'hideHome', label: t('isoConfig.uiPersonalization.iconHome') },
      { value: 'hideLibraries', label: t('isoConfig.uiPersonalization.iconLibraries') },
      { value: 'hideNetwork', label: t('isoConfig.uiPersonalization.iconNetwork') },
      { value: 'hideUserProfile', label: t('isoConfig.uiPersonalization.iconUserFiles') }
    ]

    const navigationPaneHtml = createMultiColumnCheckboxContainer({
      id: 'file-explorer-navigation-pane-container',
      name: 'file-explorer-navigation-pane',
      title: t('isoConfig.uiPersonalization.navigationPaneCategories'),
      description: t('isoConfig.uiPersonalization.navigationPaneCategoriesDesc'),
      icon: 'panel-left',
      options: categoryOptions,
      values: {
        hideDesktop: navigationPane.hideDesktop || false,
        hideDocuments: navigationPane.hideDocuments || false,
        hideDownloads: navigationPane.hideDownloads || false,
        hideMusic: navigationPane.hideMusic || false,
        hidePictures: navigationPane.hidePictures || false,
        hideVideos: navigationPane.hideVideos || false,
        hideGallery: navigationPane.hideGallery || false,
        hideHome: navigationPane.hideHome || false,
        hideLibraries: navigationPane.hideLibraries || false,
        hideNetwork: navigationPane.hideNetwork || false,
        hideUserProfile: navigationPane.hideUserProfile || false
      },
      expanded: false,
      showHeader: true,
      minColumnWidth: 180,
      maxColumns: 4
    })

    const folderDialogHtml = createMultiColumnCheckboxContainer({
      id: 'file-explorer-folder-dialog-container',
      name: 'file-explorer-folder-dialog',
      title: t('isoConfig.uiPersonalization.folderDialogCategories'),
      description: t('isoConfig.uiPersonalization.folderDialogCategoriesDesc'),
      icon: 'folder-tree',
      options: categoryOptions,
      values: {
        hideDesktop: folderDialog.hideDesktop || false,
        hideDocuments: folderDialog.hideDocuments || false,
        hideDownloads: folderDialog.hideDownloads || false,
        hideMusic: folderDialog.hideMusic || false,
        hidePictures: folderDialog.hidePictures || false,
        hideVideos: folderDialog.hideVideos || false,
        hideGallery: folderDialog.hideGallery || false,
        hideHome: folderDialog.hideHome || false,
        hideLibraries: folderDialog.hideLibraries || false,
        hideNetwork: folderDialog.hideNetwork || false,
        hideUserProfile: folderDialog.hideUserProfile || false
      },
      expanded: false,
      showHeader: true,
      minColumnWidth: 180,
      maxColumns: 4
    })

    const hideFilesRadioHtml = createRadioContainer({
      id: 'hide-files-container',
      name: 'hide-files-mode',
      title: t('isoConfig.uiPersonalization.hideFiles'),
      description: t('isoConfig.uiPersonalization.hideFilesDesc'),
      icon: 'eye-off',
      options: [
        {
          value: 'hidden',
          label: t('isoConfig.uiPersonalization.hideFilesDefault'),
          description: t('isoConfig.uiPersonalization.hideFilesDefaultDesc')
        },
        {
          value: 'hiddenSystem',
          label: t('isoConfig.uiPersonalization.hideFilesHiddenSystem'),
          description: t('isoConfig.uiPersonalization.hideFilesHiddenSystemDesc')
        },
        {
          value: 'none',
          label: t('isoConfig.uiPersonalization.hideFilesNone'),
          description: t('isoConfig.uiPersonalization.hideFilesNoneDesc')
        }
      ],
      selectedValue: fe.hideFiles || 'hidden',
      expanded: false
    })

    contentDiv.innerHTML = `
      ${hideFilesRadioHtml}
      ${createComboCard({
        id: 'file-explorer-show-extensions',
        title: t('isoConfig.uiPersonalization.showFileExtensions'),
        description: t('isoConfig.uiPersonalization.showFileExtensionsDesc'),
        icon: 'file-code',
        controlType: 'switch',
        value: fe.showFileExtensions || false
      })}
      ${createComboCard({
        id: 'file-explorer-launch-this-pc',
        title: t('isoConfig.uiPersonalization.launchToThisPC'),
        description: t('isoConfig.uiPersonalization.launchToThisPCDesc'),
        icon: 'hard-drive',
        controlType: 'switch',
        value: fe.launchToThisPC || false
      })}
      ${createComboCard({
        id: 'file-explorer-classic-context-menu',
        title: t('isoConfig.systemOptimization.classicContextMenu'),
        description: t('isoConfig.uiPersonalization.classicContextMenuDesc'),
        icon: 'layout-grid',
        controlType: 'switch',
        value: fe.classicContextMenu || false
      })}
      ${createComboCard({
        id: 'file-explorer-show-end-task',
        title: t('isoConfig.systemOptimization.showEndTask'),
        description: t('isoConfig.uiPersonalization.showEndTaskDesc'),
        icon: 'alert-triangle',
        controlType: 'switch',
        value: fe.showEndTask || false
      })}
      ${createComboCard({
        id: 'file-explorer-hide-recent',
        title: t('isoConfig.uiPersonalization.hideRecentInQuickAccess'),
        description: t('isoConfig.uiPersonalization.hideRecentInQuickAccessDesc'),
        icon: 'clock',
        controlType: 'switch',
        value: fe.hideRecentInQuickAccess || false
      })}
      ${createComboCard({
        id: 'file-explorer-hide-frequent',
        title: t('isoConfig.uiPersonalization.hideFrequentInQuickAccess'),
        description: t('isoConfig.uiPersonalization.hideFrequentInQuickAccessDesc'),
        icon: 'folder',
        controlType: 'switch',
        value: fe.hideFrequentInQuickAccess || false
      })}
      ${createComboCard({
        id: 'file-explorer-hide-cloud-files',
        title: t('isoConfig.uiPersonalization.hideCloudFilesInQuickAccess'),
        description: t('isoConfig.uiPersonalization.hideCloudFilesInQuickAccessDesc'),
        icon: 'folder-up',
        controlType: 'switch',
        value: fe.hideCloudFilesInQuickAccess || false
      })}
      ${createComboCard({
        id: 'file-explorer-hide-recommendations',
        title: t('isoConfig.uiPersonalization.hideExplorerRecommendations'),
        description: t('isoConfig.uiPersonalization.hideExplorerRecommendationsDesc'),
        icon: 'sparkles',
        controlType: 'switch',
        value: fe.hideRecommendations || false
      })}
      ${navigationPaneHtml}
      ${folderDialogHtml}
    `

    setupRadioContainer('hide-files-container', 'hide-files-mode', (value) => {
      this.updateModule('fileExplorer', { hideFiles: value as 'hidden' | 'hiddenSystem' | 'none' })
    }, true)

    setupComboCard('file-explorer-show-extensions', (value) => {
      this.updateModule('fileExplorer', { showFileExtensions: value as boolean })
    })
    setupComboCard('file-explorer-launch-this-pc', (value) => {
      this.updateModule('fileExplorer', { launchToThisPC: value as boolean })
    })
    setupComboCard('file-explorer-classic-context-menu', (value) => {
      this.updateModule('fileExplorer', { classicContextMenu: value as boolean })
    })
    setupComboCard('file-explorer-show-end-task', (value) => {
      this.updateModule('fileExplorer', { showEndTask: value as boolean })
    })
    setupComboCard('file-explorer-hide-recent', (value) => {
      this.updateModule('fileExplorer', { hideRecentInQuickAccess: value as boolean })
    })
    setupComboCard('file-explorer-hide-frequent', (value) => {
      this.updateModule('fileExplorer', { hideFrequentInQuickAccess: value as boolean })
    })
    setupComboCard('file-explorer-hide-cloud-files', (value) => {
      this.updateModule('fileExplorer', { hideCloudFilesInQuickAccess: value as boolean })
    })
    setupComboCard('file-explorer-hide-recommendations', (value) => {
      this.updateModule('fileExplorer', { hideRecommendations: value as boolean })
    })
    setupMultiColumnCheckboxContainer('file-explorer-navigation-pane-container', 'file-explorer-navigation-pane', (values) => {
      this.updateModule('fileExplorer', { navigationPane: values as ExplorerCategoryVisibility })
    }, true)
    setupMultiColumnCheckboxContainer('file-explorer-folder-dialog-container', 'file-explorer-folder-dialog', (values) => {
      this.updateModule('fileExplorer', { folderDialog: values as ExplorerCategoryVisibility })
    }, true)

    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  private renderStartTaskbarContent(contentDiv: HTMLElement) {
    const st = this.config.startMenuTaskbar
    const folders = this.config.startFolders

    const taskbarSearchCardHtml = createComboCard({
      id: 'taskbar-search-card',
      title: t('isoConfig.uiPersonalization.taskbarSearch'),
      description: t('isoConfig.uiPersonalization.taskbarSearchDesc'),
      icon: 'search',
      controlType: 'select',
      options: [
        { value: 'box', label: t('isoConfig.uiPersonalization.taskbarSearchBox') },
        { value: 'label', label: t('isoConfig.uiPersonalization.taskbarSearchLabel') },
        { value: 'icon', label: t('isoConfig.uiPersonalization.taskbarSearchIcon') },
        { value: 'hide', label: t('isoConfig.uiPersonalization.taskbarSearchHide') }
      ],
      value: st.taskbarSearch || 'box'
    })

    const startTilesRadioHtml = createRadioContainer({
      id: 'start-tiles-container',
      name: 'start-tiles-mode',
      title: t('isoConfig.uiPersonalization.startTilesMode'),
      description: t('isoConfig.uiPersonalization.startTilesModeDesc'),
      icon: 'grid-3x3',
      options: [
        {
          value: 'default',
          label: t('isoConfig.uiPersonalization.startTilesDefault'),
          description: t('isoConfig.uiPersonalization.startTilesDefaultDesc')
        },
        {
          value: 'empty',
          label: t('isoConfig.uiPersonalization.startTilesEmpty'),
          description: t('isoConfig.uiPersonalization.startTilesEmptyDesc')
        },
        {
          value: 'custom',
          label: t('isoConfig.uiPersonalization.startTilesCustom'),
          description: t('isoConfig.uiPersonalization.startTilesCustomDesc'),
          nestedCards: [
            {
              id: 'start-tiles-xml-card',
              title: t('isoConfig.uiPersonalization.startTilesXml'),
              description: t('isoConfig.uiPersonalization.startTilesXmlDesc'),
              icon: 'code',
              value: st.startTilesXml || '',
              placeholder: `<LayoutModificationTemplate xmlns="http://schemas.microsoft.com/Start/2014/LayoutModificationTemplate" xmlns:defaultlayout="http://schemas.microsoft.com/Start/2014/FullDefaultLayout" xmlns:start="http://schemas.microsoft.com/Start/2014/StartLayout" xmlns:taskbar="http://schemas.microsoft.com/Start/2014/TaskbarLayout" Version="1">
  <defaultlayout:StartLayoutCollection>
    <defaultlayout:DefaultLayout StartLayoutGroupCellWidth="6">
      <start:Group Name="Group1">
        <start:DesktopApplicationTile Size="2x2" Column="0" Row="0" DesktopApplicationLinkPath="%ALLUSERSPROFILE%\\Microsoft\\Windows\\Start Menu\\Programs\\Microsoft Edge.lnk" />
        <start:DesktopApplicationTile Size="2x2" Column="2" Row="0" DesktopApplicationLinkPath="%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\System Tools\\File Explorer.lnk" />
      </start:Group>
    </defaultlayout:DefaultLayout>
  </defaultlayout:StartLayoutCollection>
</LayoutModificationTemplate>`,
              rows: 15,
              borderless: true,
              showImportExport: true
            } as any
          ]
        }
      ],
      selectedValue: st.startTilesMode || 'default',
      expanded: false
    })

    const startPinsRadioHtml = createRadioContainer({
      id: 'start-pins-container',
      name: 'start-pins-mode',
      title: t('isoConfig.uiPersonalization.startPinsMode'),
      description: t('isoConfig.uiPersonalization.startPinsModeDesc'),
      icon: 'pin',
      options: [
        {
          value: 'default',
          label: t('isoConfig.uiPersonalization.startPinsDefault'),
          description: t('isoConfig.uiPersonalization.startPinsDefaultDesc')
        },
        {
          value: 'empty',
          label: t('isoConfig.uiPersonalization.startPinsEmpty'),
          description: t('isoConfig.uiPersonalization.startPinsEmptyDesc')
        },
        {
          value: 'custom',
          label: t('isoConfig.uiPersonalization.startPinsCustom'),
          description: t('isoConfig.uiPersonalization.startPinsCustomDesc'),
          nestedCards: [
            {
              id: 'start-pins-json-card',
              title: t('isoConfig.uiPersonalization.startPinsJson'),
              description: t('isoConfig.uiPersonalization.startPinsJsonDesc'),
              icon: 'code',
              value: st.startPinsJson || '',
              placeholder: `{
  "pinnedList": [
    {
      "desktopAppLink": "%ALLUSERSPROFILE%\\Microsoft\\Windows\\Start Menu\\Programs\\Microsoft Edge.lnk"
    },
    {
      "desktopAppLink": "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\File Explorer.lnk"
    }
  ]
}`,
              rows: 15,
              borderless: true,
              showImportExport: true
            } as any
          ]
        }
      ],
      selectedValue: st.startPinsMode || 'default',
      expanded: false
    })

    const foldersStartRadioHtml = createRadioContainer({
      id: 'folders-start-container',
      name: 'folders-start-mode',
      title: t('isoConfig.uiPersonalization.foldersStart'),
      description: t('isoConfig.uiPersonalization.foldersStartDesc'),
      icon: 'folder',
      options: [
        {
          value: 'default',
          label: t('isoConfig.uiPersonalization.foldersStartDefault'),
          description: t('isoConfig.uiPersonalization.foldersStartDefaultDesc')
        },
        {
          value: 'custom',
          label: t('isoConfig.uiPersonalization.foldersStartCustom'),
          description: t('isoConfig.uiPersonalization.foldersStartCustomDesc'),
          nestedCards: [
            {
              type: 'multiColumnCheckbox',
              config: {
                id: 'folders-start-options-container',
                name: 'folders-start-options',
                options: [
                  { value: 'startFolderDocuments', label: t('isoConfig.uiPersonalization.startFolderDocuments') },
                  { value: 'startFolderDownloads', label: t('isoConfig.uiPersonalization.startFolderDownloads') },
                  { value: 'startFolderFileExplorer', label: t('isoConfig.uiPersonalization.startFolderFileExplorer') },
                  { value: 'startFolderMusic', label: t('isoConfig.uiPersonalization.startFolderMusic') },
                  { value: 'startFolderNetwork', label: t('isoConfig.uiPersonalization.startFolderNetwork') },
                  { value: 'startFolderPersonalFolder', label: t('isoConfig.uiPersonalization.startFolderPersonalFolder') },
                  { value: 'startFolderPictures', label: t('isoConfig.uiPersonalization.startFolderPictures') },
                  { value: 'startFolderSettings', label: t('isoConfig.uiPersonalization.startFolderSettings') },
                  { value: 'startFolderVideos', label: t('isoConfig.uiPersonalization.startFolderVideos') }
                ],
                values: {
                  startFolderDocuments: folders.folders?.Documents || false,
                  startFolderDownloads: folders.folders?.Downloads || false,
                  startFolderFileExplorer: folders.folders?.FileExplorer || false,
                  startFolderMusic: folders.folders?.Music || false,
                  startFolderNetwork: folders.folders?.Network || false,
                  startFolderPersonalFolder: folders.folders?.PersonalFolder || false,
                  startFolderPictures: folders.folders?.Pictures || false,
                  startFolderSettings: folders.folders?.Settings || false,
                  startFolderVideos: folders.folders?.Videos || false
                },
                showHeader: false,
                minColumnWidth: 140,
                maxColumns: 3
              }
            }
          ]
        }
      ],
      selectedValue: folders.mode || 'default',
      expanded: false
    })

    contentDiv.innerHTML = `
      ${createComboCard({
        id: 'taskbar-left',
        title: t('isoConfig.uiPersonalization.leftTaskbar'),
        description: t('isoConfig.uiPersonalization.leftTaskbarDesc'),
        icon: 'align-left',
        controlType: 'switch',
        value: st.leftTaskbar || false
      })}
      ${createComboCard({
        id: 'taskbar-hide-taskview',
        title: t('isoConfig.uiPersonalization.hideTaskViewButton'),
        description: t('isoConfig.uiPersonalization.hideTaskViewButtonDesc'),
        icon: 'layers',
        controlType: 'switch',
        value: st.hideTaskViewButton || false
      })}
      ${createComboCard({
        id: 'taskbar-disable-widgets',
        title: t('isoConfig.uiPersonalization.disableWidgets'),
        description: t('isoConfig.uiPersonalization.disableWidgetsDesc'),
        icon: 'newspaper',
        controlType: 'switch',
        value: st.disableWidgets || false
      })}
      ${createComboCard({
        id: 'taskbar-show-all-tray-icons',
        title: t('isoConfig.uiPersonalization.showAllTrayIcons'),
        description: t('isoConfig.uiPersonalization.showAllTrayIconsDesc'),
        icon: 'eye',
        controlType: 'switch',
        value: st.showAllTrayIcons || false
      })}
      ${createComboCard({
        id: 'taskbar-disable-bing',
        title: t('isoConfig.uiPersonalization.disableBingResults'),
        description: t('isoConfig.uiPersonalization.disableBingResultsDesc'),
        icon: 'search-x',
        controlType: 'switch',
        value: st.disableBingResults || false
      })}
      ${taskbarSearchCardHtml}
      ${startTilesRadioHtml}
      ${startPinsRadioHtml}
      ${foldersStartRadioHtml}
    `

    setupComboCard('taskbar-left', (value) => {
      this.updateModule('startMenuTaskbar', { leftTaskbar: value as boolean })
    })
    setupComboCard('taskbar-hide-taskview', (value) => {
      this.updateModule('startMenuTaskbar', { hideTaskViewButton: value as boolean })
    })
    setupComboCard('taskbar-disable-widgets', (value) => {
      this.updateModule('startMenuTaskbar', { disableWidgets: value as boolean })
    })
    setupComboCard('taskbar-show-all-tray-icons', (value) => {
      this.updateModule('startMenuTaskbar', { showAllTrayIcons: value as boolean })
    })
    setupComboCard('taskbar-disable-bing', (value) => {
      this.updateModule('startMenuTaskbar', { disableBingResults: value as boolean })
    })

    setupComboCard('taskbar-search-card', (value) => {
      this.updateModule('startMenuTaskbar', { taskbarSearch: value as 'hide' | 'icon' | 'box' | 'label' })
    })

    setupRadioContainer('start-tiles-container', 'start-tiles-mode', (value) => {
      this.updateModule('startMenuTaskbar', { startTilesMode: value as 'default' | 'empty' | 'custom' })
      this.renderStartTaskbarContent(contentDiv)
    }, true)

    if (st.startTilesMode === 'custom') {
      setupTextCard('start-tiles-xml-card', (value) => {
        this.updateModule('startMenuTaskbar', { startTilesXml: value })
      }, async () => {
        if (window.electronAPI?.showOpenDialog) {
          const result = await window.electronAPI.showOpenDialog({
            filters: [{ name: 'XML Files', extensions: ['xml', 'txt'] }],
            properties: ['openFile']
          })
          if (!result.canceled && result.filePaths?.[0] && window.electronAPI?.readFile) {
            const content = await window.electronAPI.readFile(result.filePaths[0])
            setTextCardValue('start-tiles-xml-card', content)
            this.updateModule('startMenuTaskbar', { startTilesXml: content })
          }
        }
      }, async () => {
        if (window.electronAPI?.showSaveDialog) {
          const result = await window.electronAPI.showSaveDialog({
            filters: [{ name: 'XML Files', extensions: ['xml'] }],
            defaultPath: 'start-tiles.xml'
          })
          if (!result.canceled && result.filePath && window.electronAPI?.writeFile) {
            const currentValue = getTextCardValue('start-tiles-xml-card', true)
            await window.electronAPI.writeFile(result.filePath, currentValue)
          }
        }
      })
    }

    setupRadioContainer('start-pins-container', 'start-pins-mode', (value) => {
      this.updateModule('startMenuTaskbar', { startPinsMode: value as 'default' | 'empty' | 'custom' })
      this.renderStartTaskbarContent(contentDiv)
    }, true)

    if (st.startPinsMode === 'custom') {
      setupTextCard('start-pins-json-card', (value) => {
        this.updateModule('startMenuTaskbar', { startPinsJson: value })
      }, async () => {
        if (window.electronAPI?.showOpenDialog) {
          const result = await window.electronAPI.showOpenDialog({
            filters: [{ name: 'JSON Files', extensions: ['json', 'txt'] }],
            properties: ['openFile']
          })
          if (!result.canceled && result.filePaths?.[0] && window.electronAPI?.readFile) {
            const content = await window.electronAPI.readFile(result.filePaths[0])
            setTextCardValue('start-pins-json-card', content)
            this.updateModule('startMenuTaskbar', { startPinsJson: content })
          }
        }
      }, async () => {
        if (window.electronAPI?.showSaveDialog) {
          const result = await window.electronAPI.showSaveDialog({
            filters: [{ name: 'JSON Files', extensions: ['json'] }],
            defaultPath: 'start-pins.json'
          })
          if (!result.canceled && result.filePath && window.electronAPI?.writeFile) {
            const currentValue = getTextCardValue('start-pins-json-card', true)
            await window.electronAPI.writeFile(result.filePath, currentValue)
          }
        }
      })
    }

    setupRadioContainer('folders-start-container', 'folders-start-mode', (value) => {
      this.updateModule('startFolders', { mode: value as 'default' | 'custom' })
      this.renderStartTaskbarContent(contentDiv)
    }, true)

    if (folders.mode === 'custom') {
      setupMultiColumnCheckboxContainer('folders-start-options-container', 'folders-start-options', (values) => {
        const foldersObj: Record<string, boolean> = {}
        const keyMap: Record<string, string> = {
          startFolderSettings: 'Settings',
          startFolderFileExplorer: 'FileExplorer',
          startFolderDocuments: 'Documents',
          startFolderDownloads: 'Downloads',
          startFolderMusic: 'Music',
          startFolderPictures: 'Pictures',
          startFolderVideos: 'Videos',
          startFolderNetwork: 'Network',
          startFolderPersonalFolder: 'PersonalFolder'
        }
        Object.keys(values).forEach(key => {
          if (keyMap[key]) {
            foldersObj[keyMap[key]] = values[key] as boolean
          }
        })
        this.updateModule('startFolders', { folders: foldersObj })
      }, false)
    }

    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  private renderPersonalizationSubPageContent(contentDiv: HTMLElement) {
    const ve = this.config.visualEffects
    const pers = this.config.personalization || {
      wallpaper: { mode: 'default' },
      lockScreen: { mode: 'default' },
      color: { mode: 'default' }
    }

    const visualEffectsRadioHtml = createRadioContainer({
      id: 'visual-effects-container',
      name: 'visual-effects-mode',
      title: t('isoConfig.uiPersonalization.visualEffects'),
      description: t('isoConfig.uiPersonalization.visualEffectsDesc'),
      icon: 'sparkles',
      options: [
        {
          value: 'default',
          label: t('isoConfig.uiPersonalization.visualEffectsDefault'),
          description: t('isoConfig.uiPersonalization.visualEffectsDefaultDesc')
        },
        {
          value: 'appearance',
          label: t('isoConfig.uiPersonalization.visualEffectsAppearance'),
          description: t('isoConfig.uiPersonalization.visualEffectsAppearanceDesc')
        },
        {
          value: 'performance',
          label: t('isoConfig.uiPersonalization.visualEffectsPerformance'),
          description: t('isoConfig.uiPersonalization.visualEffectsPerformanceDesc')
        },
        {
          value: 'custom',
          label: t('isoConfig.uiPersonalization.visualEffectsCustom'),
          description: t('isoConfig.uiPersonalization.visualEffectsCustomDesc'),
          nestedCards: [
            {
              type: 'multiColumnCheckbox',
              config: {
                id: 'visual-effects-options-container',
                name: 'visual-effects-options',
                options: [
                  { value: 'controlAnimations', label: t('isoConfig.uiPersonalization.controlAnimations') },
                  { value: 'animateMinMax', label: t('isoConfig.uiPersonalization.animateMinMax') },
                  { value: 'taskbarAnimations', label: t('isoConfig.uiPersonalization.taskbarAnimations') },
                  { value: 'dwmAeroPeekEnabled', label: t('isoConfig.uiPersonalization.dwmAeroPeekEnabled') },
                  { value: 'menuAnimation', label: t('isoConfig.uiPersonalization.menuAnimation') },
                  { value: 'tooltipAnimation', label: t('isoConfig.uiPersonalization.tooltipAnimation') },
                  { value: 'selectionFade', label: t('isoConfig.uiPersonalization.selectionFade') },
                  { value: 'dwmSaveThumbnailEnabled', label: t('isoConfig.uiPersonalization.dwmSaveThumbnailEnabled') },
                  { value: 'cursorShadow', label: t('isoConfig.uiPersonalization.cursorShadow') },
                  { value: 'listviewShadow', label: t('isoConfig.uiPersonalization.listviewShadow') },
                  { value: 'thumbnailsOrIcon', label: t('isoConfig.uiPersonalization.thumbnailsOrIcon') },
                  { value: 'listviewAlphaSelect', label: t('isoConfig.uiPersonalization.listviewAlphaSelect') },
                  { value: 'dragFullWindows', label: t('isoConfig.uiPersonalization.dragFullWindows') },
                  { value: 'comboBoxAnimation', label: t('isoConfig.uiPersonalization.comboBoxAnimation') },
                  { value: 'fontSmoothing', label: t('isoConfig.uiPersonalization.fontSmoothing') },
                  { value: 'listBoxSmoothScrolling', label: t('isoConfig.uiPersonalization.listBoxSmoothScrolling') },
                  { value: 'dropShadow', label: t('isoConfig.uiPersonalization.dropShadow') }
                ],
                values: {
                  controlAnimations: ve.controlAnimations || false,
                  animateMinMax: ve.animateMinMax || false,
                  taskbarAnimations: ve.taskbarAnimations || false,
                  dwmAeroPeekEnabled: ve.dwmAeroPeekEnabled || false,
                  menuAnimation: ve.menuAnimation || false,
                  tooltipAnimation: ve.tooltipAnimation || false,
                  selectionFade: ve.selectionFade || false,
                  dwmSaveThumbnailEnabled: ve.dwmSaveThumbnailEnabled || false,
                  cursorShadow: ve.cursorShadow || false,
                  listviewShadow: ve.listviewShadow || false,
                  thumbnailsOrIcon: ve.thumbnailsOrIcon || false,
                  listviewAlphaSelect: ve.listviewAlphaSelect || false,
                  dragFullWindows: ve.dragFullWindows || false,
                  comboBoxAnimation: ve.comboBoxAnimation || false,
                  fontSmoothing: ve.fontSmoothing || false,
                  listBoxSmoothScrolling: ve.listBoxSmoothScrolling || false,
                  dropShadow: ve.dropShadow || false
                },
                showHeader: false,
                minColumnWidth: 140,
                maxColumns: 3
              }
            }
          ]
        }
      ],
      selectedValue: ve.mode || 'default',
      expanded: false
    })

    const colorModeRadioHtml = createRadioContainer({
      id: 'color-mode-container',
      name: 'color-mode',
      title: t('isoConfig.uiPersonalization.colorMode'),
      description: t('isoConfig.uiPersonalization.personalizationDesc'),
      icon: 'palette',
      options: [
        {
          value: 'default',
          label: t('isoConfig.uiPersonalization.colorDefault'),
          description: t('isoConfig.uiPersonalization.colorDefaultDesc')
        },
        {
          value: 'custom',
          label: t('isoConfig.uiPersonalization.colorCustom'),
          description: t('isoConfig.uiPersonalization.colorCustomDesc'),
          nestedCards: [
            {
              id: 'system-color-theme-card',
              title: t('isoConfig.uiPersonalization.systemColorTheme'),
              description: t('isoConfig.uiPersonalization.systemColorThemeDesc'),
              controlType: 'select',
              options: [
                { value: 'light', label: 'Light' },
                { value: 'dark', label: 'Dark' }
              ],
              value: pers.color?.systemTheme || 'light',
              borderless: true
            },
            {
              id: 'apps-color-theme-card',
              title: t('isoConfig.uiPersonalization.appsColorTheme'),
              description: t('isoConfig.uiPersonalization.appsColorThemeDesc'),
              controlType: 'select',
              options: [
                { value: 'light', label: 'Light' },
                { value: 'dark', label: 'Dark' }
              ],
              value: pers.color?.appsTheme || 'light',
              borderless: true
            },
            {
              id: 'accent-color-card',
              title: t('isoConfig.uiPersonalization.accentColor'),
              description: t('isoConfig.uiPersonalization.accentColorDesc'),
              controlType: 'text',
              value: pers.color?.accentColor || '#0078D4',
              placeholder: '#0078D4',
              borderless: true
            },
            {
              id: 'accent-color-on-start-card',
              title: t('isoConfig.uiPersonalization.accentColorOnStart'),
              description: t('isoConfig.uiPersonalization.accentColorOnStartDesc'),
              controlType: 'switch',
              value: pers.color?.accentColorOnStart || false,
              borderless: true
            },
            {
              id: 'accent-color-on-borders-card',
              title: t('isoConfig.uiPersonalization.accentColorOnBorders'),
              description: t('isoConfig.uiPersonalization.accentColorOnBordersDesc'),
              controlType: 'switch',
              value: pers.color?.accentColorOnBorders || false,
              borderless: true
            },
            {
              id: 'enable-transparency-card',
              title: t('isoConfig.uiPersonalization.enableTransparency'),
              description: t('isoConfig.uiPersonalization.enableTransparencyDesc'),
              controlType: 'switch',
              value: pers.color?.enableTransparency || false,
              borderless: true
            }
          ]
        }
      ],
      selectedValue: pers.color?.mode || 'default',
      expanded: false
    })

    const wallpaperModeRadioHtml = createRadioContainer({
      id: 'wallpaper-mode-container',
      name: 'wallpaper-mode',
      title: t('isoConfig.uiPersonalization.wallpaperMode'),
      description: t('isoConfig.uiPersonalization.wallpaperModeDesc'),
      icon: 'image',
      options: [
        {
          value: 'default',
          label: t('isoConfig.uiPersonalization.wallpaperDefault'),
          description: t('isoConfig.uiPersonalization.wallpaperDefaultDesc')
        },
        {
          value: 'solid',
          label: t('isoConfig.uiPersonalization.wallpaperSolid'),
          description: t('isoConfig.uiPersonalization.wallpaperSolidDesc'),
          nestedCards: [
            {
              id: 'wallpaper-color-card',
              title: t('isoConfig.uiPersonalization.wallpaperColor'),
              description: t('isoConfig.uiPersonalization.wallpaperColorDesc'),
              controlType: 'text',
              value: pers.wallpaper?.color || '#008080',
              placeholder: '#008080',
              borderless: true
            }
          ]
        },
        {
          value: 'script',
          label: t('isoConfig.uiPersonalization.wallpaperScript'),
          description: t('isoConfig.uiPersonalization.wallpaperScriptDesc'),
          nestedCards: [
            {
              id: 'wallpaper-script-card',
              title: t('isoConfig.uiPersonalization.wallpaperPsScript'),
              description: t('isoConfig.uiPersonalization.wallpaperPsScriptDesc'),
              icon: 'code',
              value: pers.wallpaper?.script || '',
              placeholder: `$url = 'https://example.com/wallpaper.jpg';
& {
  $ProgressPreference = 'SilentlyContinue';
  ( Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 30 ).Content;
};`,
              rows: 8,
              borderless: true,
              showImportExport: true
            } as any
          ]
        }
      ],
      selectedValue: pers.wallpaper?.mode || 'default',
      expanded: false
    })

    const lockScreenModeRadioHtml = createRadioContainer({
      id: 'lockscreen-mode-container',
      name: 'lockscreen-mode',
      title: t('isoConfig.uiPersonalization.lockScreenMode'),
      description: t('isoConfig.uiPersonalization.lockScreenModeDesc'),
      icon: 'lock',
      options: [
        {
          value: 'default',
          label: t('isoConfig.uiPersonalization.lockScreenDefault'),
          description: t('isoConfig.uiPersonalization.lockScreenDefaultDesc')
        },
        {
          value: 'script',
          label: t('isoConfig.uiPersonalization.lockScreenScript'),
          description: t('isoConfig.uiPersonalization.lockScreenScriptDesc'),
          nestedCards: [
            {
              id: 'lockscreen-script-card',
              title: t('isoConfig.uiPersonalization.lockScreenPsScript'),
              description: t('isoConfig.uiPersonalization.lockScreenPsScriptDesc'),
              icon: 'code',
              value: pers.lockScreen?.script || '',
              placeholder: `foreach( $drive in [System.IO.DriveInfo]::GetDrives() ) {
  if( $found = Join-Path -Path $drive.RootDirectory -ChildPath 'lockscreen.png' -Resolve -ErrorAction 'SilentlyContinue' ) {
    return [System.IO.File]::ReadAllBytes( $found );
  }
}`,
              rows: 8,
              borderless: true,
              showImportExport: true
            } as any
          ]
        }
      ],
      selectedValue: pers.lockScreen?.mode || 'default',
      expanded: false
    })

    contentDiv.innerHTML = `
      ${visualEffectsRadioHtml}
      ${colorModeRadioHtml}
      ${wallpaperModeRadioHtml}
      ${lockScreenModeRadioHtml}
    `

    setupRadioContainer('visual-effects-container', 'visual-effects-mode', (value) => {
      this.updateModule('visualEffects', { mode: value as 'default' | 'appearance' | 'performance' | 'custom' })
      this.renderPersonalizationSubPageContent(contentDiv)
    }, true)

    if (ve.mode === 'custom') {
      setupMultiColumnCheckboxContainer('visual-effects-options-container', 'visual-effects-options', (values) => {
        this.updateModule('visualEffects', values as Partial<VisualEffects>)
      }, false)
    }

    setupRadioContainer('color-mode-container', 'color-mode', (value) => {
      this.updateModule('personalization', {
        color: {
          ...(pers.color || {}),
          mode: value as 'default' | 'custom'
        }
      })
      this.renderPersonalizationSubPageContent(contentDiv)
    }, true)

    if (pers.color?.mode === 'custom') {
      setupComboCard('system-color-theme-card', (value) => {
        this.updateModule('personalization', { color: { ...(pers.color || {}), systemTheme: value as 'dark' | 'light' } })
      })
      setupComboCard('apps-color-theme-card', (value) => {
        this.updateModule('personalization', { color: { ...(pers.color || {}), appsTheme: value as 'dark' | 'light' } })
      })
      setupComboCard('accent-color-card', (value) => {
        this.updateModule('personalization', { color: { ...(pers.color || {}), accentColor: value as string } })
      })
      setupComboCard('accent-color-on-start-card', (value) => {
        this.updateModule('personalization', { color: { ...(pers.color || {}), accentColorOnStart: value as boolean } })
      })
      setupComboCard('accent-color-on-borders-card', (value) => {
        this.updateModule('personalization', { color: { ...(pers.color || {}), accentColorOnBorders: value as boolean } })
      })
      setupComboCard('enable-transparency-card', (value) => {
        this.updateModule('personalization', { color: { ...(pers.color || {}), enableTransparency: value as boolean } })
      })
    }

    setupRadioContainer('wallpaper-mode-container', 'wallpaper-mode', (value) => {
      this.updateModule('personalization', {
        wallpaper: {
          ...(pers.wallpaper || {}),
          mode: value as 'default' | 'solid' | 'script'
        }
      })
      this.renderPersonalizationSubPageContent(contentDiv)
    }, true)

    if (pers.wallpaper?.mode === 'solid') {
      setupComboCard('wallpaper-color-card', (value) => {
        this.updateModule('personalization', { wallpaper: { ...(pers.wallpaper || {}), color: value as string } })
      })
    }

    if (pers.wallpaper?.mode === 'script') {
      setupTextCard('wallpaper-script-card', (value) => {
        this.updateModule('personalization', { wallpaper: { ...(pers.wallpaper || {}), script: value } })
      }, async () => {
        if (window.electronAPI?.showOpenDialog) {
          const result = await window.electronAPI.showOpenDialog({
            filters: [{ name: 'PowerShell Scripts', extensions: ['ps1', 'txt'] }],
            properties: ['openFile']
          })
          if (!result.canceled && result.filePaths?.[0] && window.electronAPI?.readFile) {
            const content = await window.electronAPI.readFile(result.filePaths[0])
            setTextCardValue('wallpaper-script-card', content)
            this.updateModule('personalization', { wallpaper: { ...(pers.wallpaper || {}), script: content } })
          }
        }
      }, async () => {
        if (window.electronAPI?.showSaveDialog) {
          const result = await window.electronAPI.showSaveDialog({
            filters: [{ name: 'PowerShell Scripts', extensions: ['ps1'] }],
            defaultPath: 'wallpaper.ps1'
          })
          if (!result.canceled && result.filePath && window.electronAPI?.writeFile) {
            const currentValue = getTextCardValue('wallpaper-script-card', true)
            await window.electronAPI.writeFile(result.filePath, currentValue)
          }
        }
      })
    }

    setupRadioContainer('lockscreen-mode-container', 'lockscreen-mode', (value) => {
      this.updateModule('personalization', {
        lockScreen: {
          ...(pers.lockScreen || {}),
          mode: value as 'default' | 'script'
        }
      })
      this.renderPersonalizationSubPageContent(contentDiv)
    }, true)

    if (pers.lockScreen?.mode === 'script') {
      setupTextCard('lockscreen-script-card', (value) => {
        this.updateModule('personalization', { lockScreen: { ...(pers.lockScreen || {}), script: value } })
      }, async () => {
        if (window.electronAPI?.showOpenDialog) {
          const result = await window.electronAPI.showOpenDialog({
            filters: [{ name: 'PowerShell Scripts', extensions: ['ps1', 'txt'] }],
            properties: ['openFile']
          })
          if (!result.canceled && result.filePaths?.[0] && window.electronAPI?.readFile) {
            const content = await window.electronAPI.readFile(result.filePaths[0])
            setTextCardValue('lockscreen-script-card', content)
            this.updateModule('personalization', { lockScreen: { ...(pers.lockScreen || {}), script: content } })
          }
        }
      }, async () => {
        if (window.electronAPI?.showSaveDialog) {
          const result = await window.electronAPI.showSaveDialog({
            filters: [{ name: 'PowerShell Scripts', extensions: ['ps1'] }],
            defaultPath: 'lockscreen.ps1'
          })
          if (!result.canceled && result.filePath && window.electronAPI?.writeFile) {
            const currentValue = getTextCardValue('lockscreen-script-card', true)
            await window.electronAPI.writeFile(result.filePath, currentValue)
          }
        }
      })
    }

    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 设置事件监听器
  private setupEventListeners() {
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

    if (!this.workspaceTitleListenerBound) {
      const workspaceTitle = document.getElementById('workspace-title') as HTMLElement | null
      workspaceTitle?.addEventListener('click', (e: Event) => {
        const target = e.target as HTMLElement
        const backEl = target.closest('[data-subpage-action="back"]')
        if (backEl && this.activeUiPersonalizationSubPage) {
          this.resetUiPersonalizationSubPage(true)
        }
      })
      this.workspaceTitleListenerBound = true
    }
  }

  // 处理导入
  private async handleImport() {
    if (window.electronAPI?.showOpenDialog) {
      try {
        const result = await window.electronAPI.showOpenDialog({
          filters: [{ name: 'XML Files', extensions: ['xml'] }],
          properties: ['openFile']
        })
        if (!result.canceled && result.filePaths?.[0]) {
          // 读取文件
          const filePath = result.filePaths[0]
          const fileContent = await window.electronAPI.readFile(filePath)

          if (fileContent) {
            // 调用后端解析 XML
            await this.importFromXml(fileContent)
            await showWorkspaceMessageDialog('导入成功', '配置已从 XML 导入并应用到当前页面。')
          } else {
            await showWorkspaceMessageDialog('读取失败', '无法读取所选文件。')
          }
        }
      } catch (error: any) {
        await showWorkspaceMessageDialog('导入失败', error.message || '未知错误')
        console.error('Import error:', error)
      }
    }
  }

  private getRenderContent(targetId: string) {
    const direct = this.panel?.querySelector(`#${targetId}`) as HTMLElement | null
    if (direct && direct.classList.contains('section-content')) {
      return direct
    }

    return this.getSectionContent(targetId)
  }

  private renderWindowsPEStage() {
    const pe = this.config.peSettings
    const partitionContent = this.getRenderContent('config-partitioning')
    const editionContent = this.getRenderContent('config-windows-edition')

    this.renderPEOperation('config-pe-operation')

    if (partitionContent) {
      partitionContent.style.display = pe.mode === 'generated' ? '' : 'none'
      if (pe.mode !== 'generated') {
        partitionContent.innerHTML = ''
      }
    }

    if (editionContent) {
      editionContent.style.display = pe.mode === 'generated' ? '' : 'none'
      if (pe.mode !== 'generated') {
        editionContent.innerHTML = ''
      }
    }

    if (pe.mode === 'generated') {
      this.renderPartitioning('config-partitioning')
      this.renderWindowsEditionAndSource('config-windows-edition')
    }
  }

  // 处理导出
  private async handleExport() {
    try {
      // 调用后端生成 XML
      const xml = await this.exportToXml()

      // 保存文件
      if (window.electronAPI?.showSaveDialog) {
        const result = await window.electronAPI.showSaveDialog({
          filters: [{ name: 'XML Files', extensions: ['xml'] }],
          defaultPath: 'autounattend.xml'
        })

        if (!result.canceled && result.filePath) {
          await window.electronAPI.writeFile(result.filePath, xml)
          await showWorkspaceMessageDialog('导出成功', '当前配置已导出为 XML 文件。')
        }
      } else {
        // 如果没有保存对话框，使用下载
        const blob = new Blob([xml], { type: 'application/xml' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'autounattend.xml'
        a.click()
        URL.revokeObjectURL(url)
      }
    } catch (error: any) {
      await showWorkspaceMessageDialog('导出失败', error.message || '未知错误')
      console.error('Export error:', error)
    }
  }

  private restoreWindowFocus() {
    const refocus = () => {
      window.focus()
      const activeElement = document.activeElement as HTMLElement | null
      if (activeElement && typeof activeElement.blur === 'function') {
        activeElement.blur()
      }
    }

    requestAnimationFrame(() => {
      refocus()
      setTimeout(refocus, 50)
    })
  }

  // 恢复默认配置
  private async handleResetToDefault() {
    const confirmed = await showWorkspaceConfirmDialog('恢复默认值', '这会清空当前自定义配置并恢复为默认值。是否继续？')
    if (!confirmed) {
      return
    }

    this.config = createDefaultConfig()
    this.persistConfig()
    this.renderAllModules()
    this.restoreWindowFocus()
  }

  // 渲染导入和导出卡片
  private renderImportExport() {
    if (!this.panel) return

    const importCardId = 'iso-config-import-card'
    const exportCardId = 'iso-config-export-card'
    const resetCardId = 'iso-config-reset-card'

    // 检查卡片是否已存在，如果存在则直接返回，避免重复创建
    if (this.panel.querySelector(`#${importCardId}`) && this.panel.querySelector(`#${exportCardId}`) && this.panel.querySelector(`#${resetCardId}`)) {
      return
    }

    // 获取或创建导入/导出 section 容器
    let section = this.panel.querySelector('.section:first-child') as HTMLElement
    if (!section || !section.querySelector(`#${importCardId}`)) {
      // 如果不存在，创建一个新的 section
      section = document.createElement('div')
      section.className = 'section'
      this.panel.insertBefore(section, this.panel.firstChild)
    } else {
      // 清空现有内容
      section.innerHTML = ''
    }

    // 创建 section-content 容器（与其他 section 保持一致）
    const contentDiv = document.createElement('div')
    contentDiv.className = 'section-content'

    // 创建导入卡片
    const importCardHtml = createComboCard({
      id: importCardId,
      title: t('isoConfig.import.title') || '导入配置',
      description: t('isoConfig.import.description') || '从 XML 文件导入配置',
      icon: 'folder-up',
      controlType: 'clickable',
      value: ''
    })

    // 创建导出卡片
    const exportCardHtml = createComboCard({
      id: exportCardId,
      title: t('isoConfig.export.title') || '导出配置',
      description: t('isoConfig.export.description') || '将当前配置导出为 XML 文件',
      icon: 'folder-down',
      controlType: 'clickable',
      value: ''
    })

    const resetCardHtml = createComboCard({
      id: resetCardId,
      title: '恢复默认值',
      description: '将当前自定义配置恢复为初始默认状态',
      icon: 'rotate-ccw',
      controlType: 'clickable',
      value: ''
    })

    // 直接将卡片 HTML 设置到 contentDiv（与其他 section 保持一致）
    contentDiv.innerHTML = importCardHtml + exportCardHtml + resetCardHtml
    section.appendChild(contentDiv)

    // 初始化图标
    if (window.lucide) {
      window.lucide.createIcons()
    }

    // 设置事件监听
    setupComboCard(importCardId, () => { }, () => {
      this.handleImport()
    })
    setupComboCard(exportCardId, () => { }, () => {
      this.handleExport()
    })
    setupComboCard(resetCardId, () => { }, () => {
      this.handleResetToDefault()
    })
  }

  // 渲染模块1: Region, Language and Time Zone
  private renderRegionLanguageTimeZone() {
    const contentDiv = this.getSectionContent('config-region-language')
    if (!contentDiv) return

    const preset = this.getPresetData()
    const lang = this.config.languageSettings
    const tz = this.config.timeZone

    const normalizeKeyboardId = (id?: string) => (id || '').toUpperCase()
    const defaultKeyboard = normalizeKeyboardId(preset.keyboards[0]?.id || '')
    const firstLanguageCandidates = this.getFirstLanguageCandidates()

    const templateLang = this.getAutoUiLanguage()
    const savedUiLang = lang.uiLanguage
    const savedFl = lang.systemLocale
    const uiLanguageValue = savedUiLang || templateLang || preset.languages[0]?.id || ''
    const firstLanguageValue = savedFl || firstLanguageCandidates.find(l => l.id === this.localeForLanguageId(uiLanguageValue))?.id || firstLanguageCandidates[0]?.id || uiLanguageValue
    const defaultGeo = preset.geoLocations[0]?.id || firstLanguageValue
    const homeRegionValue = lang.geoLocation || defaultGeo
    const defaultTimeZone = preset.timeZones[0]?.id || ''

    const getOptionLabel = (_type: string, _id: string, backendName: string): string => backendName
    const filteredKeyboards = this.getKeyboardsForLanguage(firstLanguageValue)
    const firstKeyboardValue = filteredKeyboards.some(k => normalizeKeyboardId(k.id) === normalizeKeyboardId(lang.inputLocale || ''))
      ? normalizeKeyboardId(lang.inputLocale || '')
      : normalizeKeyboardId(filteredKeyboards[0]?.id || defaultKeyboard)

    // 语言模式 Switch ComboCard
    const languageModeCardHtml = createComboCard({
      id: 'config-language-mode-card',
      title: t('isoConfig.regionLanguage.selectLanguageInSetup'),
      description: t('isoConfig.regionLanguage.selectLanguageInSetupDesc'),
      icon: 'globe',
      controlType: 'switch',
      value: lang.mode === 'interactive'
    })

    const uiLanguageCardHtml = createComboCard({
      id: 'config-ui-language-card',
      title: t('isoConfig.regionLanguage.uiLanguageTitle'),
      description: t('isoConfig.regionLanguage.uiLanguageDesc'),
      icon: 'globe',
      controlType: 'select',
      options: preset.languages.map(l => ({ value: l.id, label: getOptionLabel('language', l.id, l.name) })),
      value: uiLanguageValue
    })

    const firstLanguageCardHtml = createComboCard({
      id: 'config-first-language-card',
      title: t('isoConfig.regionLanguage.firstLanguageTitle'),
      description: t('isoConfig.regionLanguage.firstLanguageDesc'),
      icon: 'languages',
      controlType: 'select',
      options: firstLanguageCandidates.map(l => ({ value: l.id, label: getOptionLabel('locale', l.id, l.name) })),
      value: firstLanguageValue
    })

    // First keyboard layout ComboCard
    const firstKeyboardCardHtml = createComboCard({
      id: 'config-first-keyboard-card',
      title: t('isoConfig.regionLanguage.firstKeyboardTitle'),
      description: '',
      icon: 'keyboard',
      controlType: 'select',
      options: filteredKeyboards.map(k => ({ value: k.id, label: getOptionLabel('keyboard', k.id, k.name) })),
      value: firstKeyboardValue
    })

    // Home location ComboCard
    const homeRegionCardHtml = createComboCard({
      id: 'config-home-region-card',
      title: t('isoConfig.regionLanguage.homeRegionTitle'),
      description: t('isoConfig.regionLanguage.homeRegionDesc'),
      icon: 'map',
      controlType: 'select',
      options: (preset.geoLocations.length ? preset.geoLocations : preset.locales).map(l => ({
        value: l.id,
        label: getOptionLabel('geoLocation', l.id, l.name)
      })),
      value: homeRegionValue
    })

    // 时区模式 Switch ComboCard
    const timezoneModeCardHtml = createComboCard({
      id: 'config-timezone-mode-card',
      title: t('isoConfig.regionLanguage.autoSetTimeZone'),
      description: t('isoConfig.regionLanguage.autoSetTimeZoneDesc'),
      icon: 'clock',
      controlType: 'switch',
      value: tz.mode === 'implicit'
    })

    // 时区选择 ComboCard（始终生成，通过容器控制显隐）
    const timezoneSelectCardHtml = createComboCard({
      id: 'config-timezone-card',
      title: t('isoConfig.regionLanguage.useThisTimeZone'),
      description: '',
      icon: 'map-pin',
      controlType: 'select',
      options: preset.timeZones.map(t => ({ value: t.id, label: getOptionLabel('timezone', t.id, t.name) })),
      value: tz.timeZone || defaultTimeZone
    })

    const unattendedVisible = lang.mode === 'unattended'
    const explicitVisible = tz.mode === 'explicit'

    contentDiv.innerHTML = `
      ${languageModeCardHtml}
      <div id="config-lang-unattended-group" style="display: ${unattendedVisible ? 'flex' : 'none'}; flex-direction: column;">
        ${uiLanguageCardHtml}
        ${firstLanguageCardHtml}
        ${firstKeyboardCardHtml}
      </div>
      ${timezoneModeCardHtml}
      <div id="config-region-explicit-group" style="display: ${explicitVisible ? 'block' : 'none'};">
        ${homeRegionCardHtml}
      </div>
      <div id="config-timezone-explicit-group" style="display: ${explicitVisible ? 'block' : 'none'};">
        ${timezoneSelectCardHtml}
      </div>
    `

    // 语言模式 Switch 事件监听（仅切换显隐，不重新渲染）
    const langGroup = contentDiv.querySelector('#config-lang-unattended-group') as HTMLElement
    setupComboCard('config-language-mode-card', (value) => {
      this.updateModule('languageSettings', { mode: value ? 'interactive' : 'unattended' })
      if (!value) {
        this.updateModule('languageSettings', {
          uiLanguage: uiLanguageValue,
          systemLocale: firstLanguageValue,
          inputLocale: normalizeKeyboardId(firstKeyboardValue || defaultKeyboard),
          geoLocation: tz.mode === 'explicit' ? (homeRegionValue || defaultGeo) : undefined
        })
      }
      if (langGroup) {
        langGroup.style.display = value ? 'none' : 'flex'
      }
    })

    // 语言子卡片事件监听
    setupComboCard('config-ui-language-card', (value) => {
      const newUiLang = (value as string) || uiLanguageValue
      const firstLang = firstLanguageCandidates.find(l => l.id === this.localeForLanguageId(newUiLang))?.id || firstLanguageCandidates[0]?.id || newUiLang
      this.updateModule('languageSettings', { uiLanguage: newUiLang, systemLocale: firstLang })
      const flSelect = contentDiv.querySelector('#config-first-language-card-control') as any
      if (flSelect) this.updateFirstLanguageOptions(flSelect, firstLang)
      this.updateKeyboardSelectForLanguage(firstLang)
    })
    setupComboCard('config-first-language-card', (value) => {
      const newFl = (value as string) || firstLanguageValue
      const matchingUiLang = this.languageForLocaleId(newFl)
      this.updateModule('languageSettings', { uiLanguage: matchingUiLang, systemLocale: newFl })
      const uiSelect = contentDiv.querySelector('#config-ui-language-card-control') as any
      if (uiSelect) uiSelect.value = matchingUiLang
      this.updateKeyboardSelectForLanguage(newFl)
    })
    setupComboCard('config-first-keyboard-card', (value) => {
      this.updateModule('languageSettings', { inputLocale: normalizeKeyboardId(value as string) })
    })
    setupComboCard('config-home-region-card', (value) => {
      this.updateModule('languageSettings', { geoLocation: value as string })
    })

    // 时区模式 Switch 事件监听（仅切换显隐，不重新渲染）
    const tzGroup = contentDiv.querySelector('#config-timezone-explicit-group') as HTMLElement
    const regionGroup = contentDiv.querySelector('#config-region-explicit-group') as HTMLElement
    setupComboCard('config-timezone-mode-card', (value) => {
      const implicit = Boolean(value)
      this.updateModule('timeZone', {
        mode: implicit ? 'implicit' : 'explicit',
        timeZone: implicit ? undefined : (tz.timeZone || defaultTimeZone)
      })
      this.updateModule('languageSettings', {
        uiLanguage: uiLanguageValue,
        systemLocale: firstLanguageValue,
        geoLocation: implicit ? undefined : (homeRegionValue || defaultGeo)
      })
      if (tzGroup) {
        tzGroup.style.display = implicit ? 'none' : 'block'
      }
      if (regionGroup) {
        regionGroup.style.display = implicit ? 'none' : 'block'
      }
    })

    // 时区选择事件监听（始终绑定）
    setupComboCard('config-timezone-card', (value) => {
      this.updateModule('timeZone', { timeZone: value as string })
    })

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

    const disableOobePrivacyPromptsCardHtml = createComboCard({
      id: 'config-disable-oobe-privacy-prompts-card',
      title: t('isoConfig.setupSettings.disableOobePrivacyPrompts'),
      description: t('isoConfig.setupSettings.disableOobePrivacyPromptsDesc'),
      icon: 'shield-x',
      controlType: 'switch',
      value: settings.disableOobePrivacyPrompts
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

    const express = this.config.expressSettings

    const expressSettingsCardHtml = createComboCard({
      id: 'config-express-settings-card',
      title: t('isoConfig.setupSettings.expressSettings'),
      description: t('isoConfig.setupSettings.expressSettingsDesc'),
      icon: 'shield-check',
      controlType: 'select',
      options: [
        { value: 'interactive', label: t('isoConfig.setupSettings.expressInteractive') },
        { value: 'enableAll', label: t('isoConfig.setupSettings.expressEnableAll') },
        { value: 'disableAll', label: t('isoConfig.setupSettings.expressDisableAll') }
      ],
      value: express || 'disableAll'
    })

    const wifi = this.config.wifi

    const networkMode = settings.bypassNetworkCheck ? 'noInternet'
      : wifi.mode === 'unattended' ? 'unattended'
      : wifi.mode === 'fromProfile' ? 'fromProfile'
      : 'interactive'

    const networkRadioHtml = createRadioContainer({
      id: 'network-mode-container',
      name: 'network-mode',
      title: t('isoConfig.setupSettings.networkTitle'),
      description: t('isoConfig.setupSettings.networkDesc'),
      icon: 'wifi',
      options: [
        {
          value: 'noInternet',
          label: t('isoConfig.setupSettings.networkNoInternet'),
          description: t('isoConfig.setupSettings.networkNoInternetDesc')
        },
        {
          value: 'interactive',
          label: t('isoConfig.setupSettings.networkInteractive'),
          description: t('isoConfig.setupSettings.networkInteractiveDesc')
        },
        {
          value: 'unattended',
          label: t('isoConfig.setupSettings.networkUnattended'),
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
              value: wifi.hidden || false,
              borderless: true
            }
          ]
        },
        {
          value: 'fromProfile',
          label: t('isoConfig.setupSettings.networkFromProfile'),
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
      selectedValue: networkMode,
      expanded: false
    })

    contentDiv.innerHTML = `
      ${networkRadioHtml}
      ${expressSettingsCardHtml}
      ${bypassRequirementsCardHtml}
      ${disableOobePrivacyPromptsCardHtml}
      ${useConfigurationSetCardHtml}
      ${hidePowerShellWindowsCardHtml}
      ${keepSensitiveFilesCardHtml}
      ${useNarratorCardHtml}
    `

    // 设置每个 ComboCard 的事件监听
    setupComboCard('config-bypass-requirements-card', (value) => {
      this.updateModule('setupSettings', { bypassRequirementsCheck: value as boolean })
    })

    setupComboCard('config-disable-oobe-privacy-prompts-card', (value) => {
      this.updateModule('setupSettings', { disableOobePrivacyPrompts: value as boolean })
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

    setupComboCard('config-express-settings-card', (value) => {
      this.updateConfig({ expressSettings: value as ExpressSettingsMode })
    })

    setupRadioContainer('network-mode-container', 'network-mode', (value) => {
      if (value === 'noInternet') {
        this.updateModule('setupSettings', { bypassNetworkCheck: true })
        this.updateModule('wifi', { mode: 'skip' })
      } else if (value === 'interactive') {
        this.updateModule('setupSettings', { bypassNetworkCheck: false })
        this.updateModule('wifi', { mode: 'interactive' })
      } else if (value === 'unattended') {
        this.updateModule('setupSettings', { bypassNetworkCheck: false })
        this.updateModule('wifi', { mode: 'unattended' })
      } else if (value === 'fromProfile') {
        this.updateModule('setupSettings', { bypassNetworkCheck: false })
        this.updateModule('wifi', { mode: 'fromProfile' })
      }
      this.renderSetupSettings()
    }, true)

    if (networkMode === 'unattended') {
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
        this.updateModule('wifi', { hidden: value as boolean })
      })
    }

    if (networkMode === 'fromProfile') {
      setupTextCard('config-wifi-profile-xml-card', (value) => {
        this.updateModule('wifi', { profileXml: value })
      }, async () => {
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
      expanded: false
    })

    // 2. User accounts - RadioContainer（将 firstLogon 和 builtinAdminPassword 嵌入到 unattended 选项中）
    const userAccountsRadioHtml = createRadioContainer({
      id: 'user-accounts-container',
      name: 'account-mode',
      title: t('isoConfig.nameAccount.userAccounts'),
      description: '',
      icon: 'users',
      options: [
        {
          value: 'interactive-local',
          label: t('isoConfig.nameAccount.userAccountsInteractiveLocal'),
          description: '',
        },
        {
          value: 'interactive-microsoft',
          label: t('isoConfig.nameAccount.userAccountsInteractiveMicrosoft'),
          description: ''
        },
        {
          value: 'unattended',
          label: t('isoConfig.nameAccount.userAccountsUnattended'),
          description: '',
          nestedCards: [
            {
              id: 'config-first-logon-card',
              title: t('isoConfig.nameAccount.firstLogon'),
              description: t('isoConfig.nameAccount.firstLogonDesc'),
              controlType: 'select',
              options: [
                { value: 'own', label: t('isoConfig.nameAccount.logonOwnAccount') },
                { value: 'builtin', label: t('isoConfig.nameAccount.logonBuiltinAdmin') },
                { value: 'none', label: t('isoConfig.nameAccount.logonNone') }
              ],
              value: accounts.autoLogonMode || 'none',
              borderless: true
            },
            {
              id: 'config-auto-logon-password-card',
              title: t('isoConfig.nameAccount.builtinAdminPassword'),
              description: '',
              controlType: 'text',
              value: accounts.autoLogonPassword || '',
              borderless: true,
              placeholder: ''
            },
            {
              id: 'config-obscure-passwords-card',
              title: t('isoConfig.nameAccount.obscurePasswords'),
              description: t('isoConfig.nameAccount.obscurePasswordsDesc'),
              controlType: 'switch',
              value: accounts.obscurePasswords || false,
              borderless: true
            }
          ]
        }
      ],
      selectedValue: accounts.mode,
      expanded: false
    })

    // 3. Account list - DynamicListContainer (始终显示)
    const accountItems: DynamicListItem[] = (accounts.accounts || []).map(acc => {
      const comboContainerConfig: ComboContainerConfig = {
        id: `config-account-${acc.id}`,
        name: `account-${acc.id}`,
        title: '',
        description: '',
        icon: 'user',
        nestedCards: [
          {
            id: `config-account-name-${acc.id}`,
            field: 'name',
            title: t('isoConfig.nameAccount.accountName'),
            controlType: 'text',
            value: acc.name,
            borderless: true,
            placeholder: ''
          },
          {
            id: `config-account-display-name-${acc.id}`,
            field: 'displayName',
            title: t('isoConfig.nameAccount.displayName'),
            controlType: 'text',
            value: acc.displayName,
            borderless: true,
            placeholder: ''
          },
          {
            id: `config-account-password-${acc.id}`,
            field: 'password',
            title: t('isoConfig.nameAccount.password'),
            controlType: 'text',
            value: acc.password,
            borderless: true,
            placeholder: ''
          },
          {
            id: `config-account-group-${acc.id}`,
            field: 'group',
            title: t('isoConfig.nameAccount.group'),
            controlType: 'select',
            options: [
              { value: 'Administrators', label: t('isoConfig.nameAccount.administrators') },
              { value: 'Users', label: t('isoConfig.nameAccount.users') }
            ],
            value: acc.group,
            borderless: true
          }
        ],
        showHeader: false,
        borderless: true
      }

      return {
        id: acc.id,
        cardType: 'comboContainer',
        cardConfig: comboContainerConfig
      }
    })

    const accountListHtml = createDynamicListContainer({
      id: 'config-accounts-list',
      name: 'accounts-list',
      title: t('isoConfig.nameAccount.accountList'),
      description: t('isoConfig.nameAccount.accountListDesc'),
      icon: 'user-plus',
      itemCardType: 'comboContainer',
      items: accountItems,
      expanded: true,
      showHeader: true,
      embedded: false,
      defaultCardConfig: () => {
        const newId = this.generateUUID()
        return {
          id: `config-account-${newId}`,
          name: `account-${newId}`,
          title: '',
          description: '',
          icon: 'user',
          nestedCards: [
            {
              id: `config-account-name-${newId}`,
              field: 'name',
              title: t('isoConfig.nameAccount.accountName'),
              controlType: 'text',
              value: '',
              borderless: true,
              placeholder: ''
            },
            {
              id: `config-account-display-name-${newId}`,
              field: 'displayName',
              title: t('isoConfig.nameAccount.displayName'),
              controlType: 'text',
              value: '',
              borderless: true,
              placeholder: ''
            },
            {
              id: `config-account-password-${newId}`,
              field: 'password',
              title: t('isoConfig.nameAccount.password'),
              controlType: 'text',
              value: '',
              borderless: true,
              placeholder: ''
            },
            {
              id: `config-account-group-${newId}`,
              field: 'group',
              title: t('isoConfig.nameAccount.group'),
              controlType: 'select',
              options: [
                { value: 'Administrators', label: t('isoConfig.nameAccount.administrators') },
                { value: 'Users', label: t('isoConfig.nameAccount.users') }
              ],
              value: 'Users',
              borderless: true
            }
          ],
          showHeader: false,
          borderless: true
        }
      }
    })

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
      expanded: false
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
              value: (lockout.lockoutWindow || 10).toString(),
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
      expanded: false
    })

    contentDiv.innerHTML = `
      ${computerNameRadioHtml}
      ${userAccountsRadioHtml}
      ${accountListHtml}
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

    // 设置嵌套的 firstLogon ComboCard 事件（仅在 unattended 模式下）
    if (accounts.mode === 'unattended') {
      // First logon select
      setupComboCard('config-first-logon-card', (value) => {
        this.updateModule('accountSettings', { autoLogonMode: value as 'none' | 'builtin' | 'own' })
        this.renderNameAndAccount()
      })

      // Built-in Administrator password (始终显示，但仅在 builtin 模式下有意义)
      setupComboCard('config-auto-logon-password-card', (value) => {
        this.updateModule('accountSettings', { autoLogonPassword: value as string })
      })

      // Obscure passwords
      setupComboCard('config-obscure-passwords-card', (value) => {
        this.updateModule('accountSettings', { obscurePasswords: value as boolean })
      })
    }

    // 3. Account list 事件 - DynamicListContainer
    setupDynamicListContainer(
      'config-accounts-list',
      {
        id: 'config-accounts-list',
        name: 'accounts-list',
        title: t('isoConfig.nameAccount.accountList'),
        description: t('isoConfig.nameAccount.accountListDesc'),
        icon: 'user-plus',
        itemCardType: 'comboContainer',
        items: accountItems,
        expanded: true,
        showHeader: true,
        embedded: false,
        defaultCardConfig: () => {
          const newId = this.generateUUID()
          return {
            id: `config-account-${newId}`,
            name: `account-${newId}`,
            title: '',
            description: '',
            icon: 'user',
            nestedCards: [
              {
                id: `config-account-name-${newId}`,
                field: 'name',
                title: t('isoConfig.nameAccount.accountName'),
                controlType: 'text',
                value: '',
                borderless: true,
                placeholder: ''
              },
              {
                id: `config-account-display-name-${newId}`,
                field: 'displayName',
                title: t('isoConfig.nameAccount.displayName'),
                controlType: 'text',
                value: '',
                borderless: true,
                placeholder: ''
              },
              {
                id: `config-account-password-${newId}`,
                field: 'password',
                title: t('isoConfig.nameAccount.password'),
                controlType: 'text',
                value: '',
                borderless: true,
                placeholder: ''
              },
              {
                id: `config-account-group-${newId}`,
                field: 'group',
                title: t('isoConfig.nameAccount.group'),
                controlType: 'select',
                options: [
                  { value: 'Administrators', label: t('isoConfig.nameAccount.administrators') },
                  { value: 'Users', label: t('isoConfig.nameAccount.users') }
                ],
                value: 'Users',
                borderless: true
              }
            ],
            showHeader: false,
            borderless: true
          }
        }
      },
      (_newItem: DynamicListItem) => {
        // 添加新账户
        const newAccount: Account = {
          id: this.generateUUID(),
          name: '',
          displayName: '',
          password: '',
          group: 'Users'
        }
        const accs = [...(accounts.accounts || []), newAccount]
        this.updateModule('accountSettings', { accounts: accs })
        this.renderNameAndAccount()
      },
      (itemId: string) => {
        // 删除账户
        const accs = (accounts.accounts || []).filter(acc => acc.id !== itemId)
        this.updateModule('accountSettings', { accounts: accs })
        this.renderNameAndAccount()
      },
      (itemId: string, values: any) => {
        // 更新账户 - values 是从 ComboContainer 收集的值对象
        const accs = [...(accounts.accounts || [])]
        const account = accs.find(acc => acc.id === itemId)

        if (account) {
          account.name = (values.name as string) || ''
          account.displayName = (values.displayName as string) || ''
          account.password = (values.password as string) || ''
          account.group = (values.group as 'Administrators' | 'Users') || 'Users'
          this.updateModule('accountSettings', { accounts: accs })
        }
      }
    )

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
        this.updateModule('lockoutSettings', { lockoutWindow: numValue })
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

  // 渲染模块11: Advanced Settings (合并 System tweaks、Virtual machine support、AppLocker)
  private renderAdvancedSettings() {
    const contentDiv = this.getSectionContent('config-advanced-settings')
    if (!contentDiv) return

    const tweaks = this.config.systemTweaks
    const vm = this.config.vmSupport
    const appLocker = this.config.appLocker

    // 1. System Tweaks - MultiColumnCheckboxContainer
    const systemTweaksHtml = createMultiColumnCheckboxContainer({
      id: 'system-tweaks-container',
      name: 'system-tweaks',
      title: t('isoConfig.systemOptimization.systemTweaks'),
      description: '',
      icon: 'settings',
      options: [
        { value: 'enableLongPaths', label: t('isoConfig.systemOptimization.enableLongPaths') },
        { value: 'enableRemoteDesktop', label: t('isoConfig.systemOptimization.enableRemoteDesktop') },
        { value: 'hardenSystemDriveAcl', label: t('isoConfig.systemOptimization.hardenSystemDriveAcl') },
        { value: 'deleteJunctions', label: t('isoConfig.systemOptimization.deleteJunctions') },
        { value: 'allowPowerShellScripts', label: t('isoConfig.systemOptimization.allowPowerShellScripts') },
        { value: 'disableLastAccess', label: t('isoConfig.systemOptimization.disableLastAccess') },
        { value: 'preventAutomaticReboot', label: t('isoConfig.systemOptimization.preventAutomaticReboot') },
        { value: 'disableSac', label: t('isoConfig.systemOptimization.disableSac') },
        { value: 'disableUac', label: t('isoConfig.systemOptimization.disableUac') },
        { value: 'disableSmartScreen', label: t('isoConfig.systemOptimization.disableSmartScreen') },
        { value: 'disableSystemRestore', label: t('isoConfig.systemOptimization.disableSystemRestore') },
        { value: 'disableFastStartup', label: t('isoConfig.systemOptimization.disableFastStartup') },
        { value: 'turnOffSystemSounds', label: t('isoConfig.systemOptimization.turnOffSystemSounds') },
        { value: 'disableAppSuggestions', label: t('isoConfig.systemOptimization.disableAppSuggestions') },
        { value: 'disableWidgets', label: t('isoConfig.systemOptimization.disableWidgets') },
        { value: 'preventDeviceEncryption', label: t('isoConfig.systemOptimization.preventDeviceEncryption') },
        { value: 'disableWindowsUpdate', label: t('isoConfig.systemOptimization.disableWindowsUpdate') },
        { value: 'disablePointerPrecision', label: t('isoConfig.systemOptimization.disablePointerPrecision') },
        { value: 'deleteWindowsOld', label: t('isoConfig.systemOptimization.deleteWindowsOld') },
        { value: 'disableCoreIsolation', label: t('isoConfig.systemOptimization.disableCoreIsolation') }
      ],
      values: {
        enableLongPaths: tweaks.enableLongPaths || false,
        enableRemoteDesktop: tweaks.enableRemoteDesktop || false,
        hardenSystemDriveAcl: tweaks.hardenSystemDriveAcl || false,
        deleteJunctions: tweaks.deleteJunctions || false,
        allowPowerShellScripts: tweaks.allowPowerShellScripts || false,
        disableLastAccess: tweaks.disableLastAccess || false,
        preventAutomaticReboot: tweaks.preventAutomaticReboot || false,
        disableSac: tweaks.disableSac || false,
        disableUac: tweaks.disableUac || false,
        disableSmartScreen: tweaks.disableSmartScreen || false,
        disableSystemRestore: tweaks.disableSystemRestore || false,
        disableFastStartup: tweaks.disableFastStartup || false,
        turnOffSystemSounds: tweaks.turnOffSystemSounds || false,
        disableAppSuggestions: tweaks.disableAppSuggestions || false,
        disableWidgets: tweaks.disableWidgets || false,
        preventDeviceEncryption: tweaks.preventDeviceEncryption || false,
        disableWindowsUpdate: tweaks.disableWindowsUpdate || false,
        disablePointerPrecision: tweaks.disablePointerPrecision || false,
        deleteWindowsOld: tweaks.deleteWindowsOld || false,
        disableCoreIsolation: tweaks.disableCoreIsolation || false
      },
      expanded: false,
      showHeader: true,
      minColumnWidth: 200,
      maxColumns: 4
    })

    // 2. Virtual machine support - ComboContainer
    const vmSupportHtml = createComboContainer({
      id: 'vm-support-container',
      name: 'vm-support',
      title: t('isoConfig.advancedSettings.vmSupport'),
      description: t('isoConfig.advancedSettings.vmSupportDesc'),
      icon: 'box',
      nestedCards: [
        {
          id: 'vm-support-vbox',
          title: t('isoConfig.advancedSettings.vboxGuestAdditions'),
          controlType: 'checkbox',
          value: vm.vBoxGuestAdditions || false,
          borderless: true
        },
        {
          id: 'vm-support-vmware',
          title: t('isoConfig.advancedSettings.vmwareTools'),
          controlType: 'checkbox',
          value: vm.vmwareTools || false,
          borderless: true
        },
        {
          id: 'vm-support-virtio',
          title: t('isoConfig.advancedSettings.virtioGuestTools'),
          controlType: 'checkbox',
          value: vm.virtIoGuestTools || false,
          borderless: true
        },
        {
          id: 'vm-support-parallels',
          title: t('isoConfig.advancedSettings.parallelsTools'),
          controlType: 'checkbox',
          value: vm.parallelsTools || false,
          borderless: true
        }
      ],
      expanded: false
    })

    // 3. AppLocker - 参考磁盘断言的 RadioContainer
    const appLockerRadioHtml = createRadioContainer({
      id: 'app-locker-container',
      name: 'app-locker-mode',
      title: t('isoConfig.advancedSettings.appLocker'),
      description: t('isoConfig.advancedSettings.appLockerDesc'),
      icon: 'shield',
      options: [
        {
          value: 'skip',
          label: t('isoConfig.advancedSettings.appLockerSkip'),
          description: ''
        },
        {
          value: 'configure',
          label: t('isoConfig.advancedSettings.appLockerConfigure'),
          description: '',
          nestedCards: [
            {
              id: 'app-locker-policy-card',
              title: t('isoConfig.advancedSettings.appLockerPolicyXml'),
              description: '',
              icon: 'code',
              value: appLocker.policyXml || '',
              placeholder: `<AppLockerPolicy Version="1">
  <RuleCollection Type="Exe" EnforcementMode="Enabled" />
  <RuleCollection Type="Msi" EnforcementMode="Enabled" />
  <RuleCollection Type="Script" EnforcementMode="Enabled" />
  <RuleCollection Type="Dll" EnforcementMode="NotConfigured" />
  <RuleCollection Type="Appx" EnforcementMode="Enabled" />
</AppLockerPolicy>`,
              rows: 12,
              borderless: true,
              showImportExport: true
            } as any
          ]
        }
      ],
      selectedValue: appLocker.mode || 'skip',
      expanded: false
    })

    contentDiv.innerHTML = `
      ${systemTweaksHtml}
      ${vmSupportHtml}
      ${appLockerRadioHtml}
    `

    // === 事件监听设置 ===

    // 1. System Tweaks
    setupMultiColumnCheckboxContainer('system-tweaks-container', 'system-tweaks', (values) => {
      this.updateModule('systemTweaks', values as Partial<SystemTweaks>)
    }, true)

    // 2. Virtual machine support
    setupComboContainer('vm-support-container', 'vm-support', (values) => {
      // 从嵌套卡片的值中提取各个选项
      const vboxKey = Object.keys(values).find(k => k.includes('vbox'))
      const vmwareKey = Object.keys(values).find(k => k.includes('vmware'))
      const virtioKey = Object.keys(values).find(k => k.includes('virtio'))
      const parallelsKey = Object.keys(values).find(k => k.includes('parallels'))
      this.updateModule('vmSupport', {
        vBoxGuestAdditions: vboxKey ? (values[vboxKey] as boolean) : false,
        vmwareTools: vmwareKey ? (values[vmwareKey] as boolean) : false,
        virtIoGuestTools: virtioKey ? (values[virtioKey] as boolean) : false,
        parallelsTools: parallelsKey ? (values[parallelsKey] as boolean) : false
      })
    }, true, {
      id: 'vm-support-container',
      name: 'vm-support',
      title: t('isoConfig.advancedSettings.vmSupport'),
      description: t('isoConfig.advancedSettings.vmSupportDesc'),
      icon: 'box',
      nestedCards: [
        { id: 'vm-support-vbox', field: 'vbox', title: '', controlType: 'checkbox', value: vm.vBoxGuestAdditions || false, borderless: true },
        { id: 'vm-support-vmware', field: 'vmware', title: '', controlType: 'checkbox', value: vm.vmwareTools || false, borderless: true },
        { id: 'vm-support-virtio', field: 'virtio', title: '', controlType: 'checkbox', value: vm.virtIoGuestTools || false, borderless: true },
        { id: 'vm-support-parallels', field: 'parallels', title: '', controlType: 'checkbox', value: vm.parallelsTools || false, borderless: true }
      ]
    })

    // 3. AppLocker
    setupRadioContainer('app-locker-container', 'app-locker-mode', (value) => {
      this.updateModule('appLocker', { mode: value as 'skip' | 'configure' })
      this.renderAdvancedSettings()
    }, true)

    if (appLocker.mode === 'configure') {
      setupTextCard('app-locker-policy-card', (value) => {
        this.updateModule('appLocker', { policyXml: value })
      }, async () => {
        if (window.electronAPI?.showOpenDialog) {
          const result = await window.electronAPI.showOpenDialog({
            filters: [{ name: 'XML Files', extensions: ['xml', 'txt'] }],
            properties: ['openFile']
          })
          if (!result.canceled && result.filePaths?.[0] && window.electronAPI?.readFile) {
            const content = await window.electronAPI.readFile(result.filePaths[0])
            setTextCardValue('app-locker-policy-card', content)
            this.updateModule('appLocker', { policyXml: content })
          }
        }
      }, async () => {
        if (window.electronAPI?.showSaveDialog) {
          const result = await window.electronAPI.showSaveDialog({
            filters: [{ name: 'XML Files', extensions: ['xml'] }],
            defaultPath: 'AppLockerPolicy.xml'
          })
          if (!result.canceled && result.filePath && window.electronAPI?.writeFile) {
            const currentValue = getTextCardValue('app-locker-policy-card', true)
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

  private renderPEOperation(targetId = 'config-pe-operation') {
    const contentDiv = this.getRenderContent(targetId)
    if (!contentDiv) return

    const pe = this.config.peSettings

    const peModeCardHtml = createComboCard({
      id: 'config-pe-mode-card',
      title: t('isoConfig.peMode.title'),
      description: t('isoConfig.peMode.description'),
      icon: 'terminal',
      controlType: 'select',
      options: [
        { value: 'default', label: t('isoConfig.peMode.interactive') },
        { value: 'generated', label: t('isoConfig.peMode.generated') },
        { value: 'script', label: t('isoConfig.peMode.script') }
      ],
      value: pe.mode
    })

    const generatedOptionsHtml = pe.mode === 'generated'
      ? createComboContainer({
        id: 'pe-generated-options-container',
        name: 'pe-generated-options',
        title: t('isoConfig.peMode.generatedOptions'),
        description: '',
        icon: 'settings-2',
        nestedCards: [
          {
            id: 'config-pe-disable-defender-card',
            field: 'disableDefender',
            title: t('isoConfig.peMode.disableDefender'),
            description: t('isoConfig.peMode.disableDefenderDesc'),
            controlType: 'checkbox',
            value: pe.disableDefender || false,
            borderless: true
          },
          {
            id: 'config-pe-inject-virtio-storage-drivers-card',
            field: 'injectVirtioStorageDrivers',
            title: t('isoConfig.peMode.injectVirtioStorageDrivers'),
            description: t('isoConfig.peMode.injectVirtioStorageDriversDesc'),
            controlType: 'checkbox',
            value: pe.injectVirtioStorageDrivers || false,
            borderless: true
          },
          {
            id: 'config-pe-compact-os-card',
            field: 'compactOs',
            title: t('isoConfig.advancedSettings.compactOS'),
            description: t('isoConfig.advancedSettings.compactOSDesc'),
            controlType: 'checkbox',
            value: pe.compactOs || false,
            borderless: true
          },
          {
            id: 'config-pe-disable-8dot3-card',
            field: 'disable8Dot3Names',
            title: t('isoConfig.advancedSettings.disable8dot3'),
            description: t('isoConfig.advancedSettings.disable8dot3Desc'),
            controlType: 'checkbox',
            value: pe.disable8Dot3Names || false,
            borderless: true
          },
          {
            id: 'config-pe-pause-formatting-card',
            field: 'pauseBeforeFormatting',
            title: t('isoConfig.advancedSettings.pauseFormatting'),
            description: '',
            controlType: 'checkbox',
            value: pe.pauseBeforeFormatting || false,
            borderless: true
          },
          {
            id: 'config-pe-pause-reboot-card',
            field: 'pauseBeforeReboot',
            title: t('isoConfig.advancedSettings.pauseReboot'),
            description: '',
            controlType: 'checkbox',
            value: pe.pauseBeforeReboot || false,
            borderless: true
          }
        ],
        expanded: false
      })
      : ''

    const customScriptHtml = pe.mode === 'script'
      ? createComboContainer({
        id: 'pe-custom-script-container',
        name: 'pe-custom-script',
        title: t('isoConfig.peMode.scriptTitle'),
        description: t('isoConfig.advancedSettings.customPeScriptDesc'),
        icon: 'code',
        nestedCards: [
          {
            id: 'config-pe-custom-script-card',
            title: t('isoConfig.peMode.scriptTitle'),
            description: '',
            icon: 'code',
            value: pe.cmdScript || '',
            placeholder: `@echo off
echo Custom PE script
pause`,
            rows: 10,
            borderless: true,
            showImportExport: true
          } as any
        ],
        expanded: true
      })
      : ''

    contentDiv.innerHTML = `
      ${peModeCardHtml}
      ${generatedOptionsHtml}
      ${customScriptHtml}
    `

    setupComboCard('config-pe-mode-card', (value) => {
      this.updateModule('peSettings', { mode: value as 'default' | 'generated' | 'script' })
      this.renderWindowsPEStage()
    })

    if (pe.mode === 'generated') {
      setupComboContainer('pe-generated-options-container', 'pe-generated-options', (values) => {
        this.updateModule('peSettings', {
          compactOs: Boolean(values.compactOs),
          disable8Dot3Names: Boolean(values.disable8Dot3Names),
          pauseBeforeFormatting: Boolean(values.pauseBeforeFormatting),
          pauseBeforeReboot: Boolean(values.pauseBeforeReboot),
          disableDefender: Boolean(values.disableDefender),
          injectVirtioStorageDrivers: Boolean(values.injectVirtioStorageDrivers)
        })
      }, true, {
        id: 'pe-generated-options-container',
        name: 'pe-generated-options',
        title: t('isoConfig.peMode.generatedOptions'),
        description: '',
        icon: 'settings-2',
        nestedCards: [
          { id: 'config-pe-disable-defender-card', field: 'disableDefender', title: '', controlType: 'checkbox', value: pe.disableDefender || false, borderless: true },
          { id: 'config-pe-inject-virtio-storage-drivers-card', field: 'injectVirtioStorageDrivers', title: '', controlType: 'checkbox', value: pe.injectVirtioStorageDrivers || false, borderless: true },
          { id: 'config-pe-compact-os-card', field: 'compactOs', title: '', controlType: 'checkbox', value: pe.compactOs || false, borderless: true },
          { id: 'config-pe-disable-8dot3-card', field: 'disable8Dot3Names', title: '', controlType: 'checkbox', value: pe.disable8Dot3Names || false, borderless: true },
          { id: 'config-pe-pause-formatting-card', field: 'pauseBeforeFormatting', title: '', controlType: 'checkbox', value: pe.pauseBeforeFormatting || false, borderless: true },
          { id: 'config-pe-pause-reboot-card', field: 'pauseBeforeReboot', title: '', controlType: 'checkbox', value: pe.pauseBeforeReboot || false, borderless: true }
        ]
      })
    }

    if (pe.mode === 'script') {
      setupTextCard('config-pe-custom-script-card', (value) => {
        this.updateModule('peSettings', { cmdScript: value })
      }, async () => {
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

    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染 Windows PE 子模块: Partitioning and formatting
  private renderPartitioning(targetId = 'config-partitioning') {
    const contentDiv = this.getRenderContent(targetId)
    if (!contentDiv) return

    const part = this.config.partitioning
    const partitionLayout = part.layout || 'GPT'

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
              id: 'target-disk-card',
              title: t('isoConfig.partitioning.targetDisk'),
              description: t('isoConfig.partitioning.targetDiskDesc'),
              controlType: 'text' as const,
              value: String(part.targetDisk ?? 0),
              placeholder: '0',
              borderless: true
            },
            {
              id: 'partition-layout-card',
              title: t('isoConfig.partitioning.partitionLayout'),
              description: '',
              icon: 'layout',
              controlType: 'select',
              value: partitionLayout,
              options: [
                { value: 'GPT', label: t('isoConfig.partitioning.gpt') },
                { value: 'MBR', label: t('isoConfig.partitioning.mbr') }
              ],
              borderless: true
            },
            // ESP Size (仅GPT显示)
            ...(partitionLayout === 'GPT' ? [{
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
            }
          ] as any
        }
      ],
      selectedValue: part.mode,
      expanded: false
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
      expanded: false
    })

    contentDiv.innerHTML = `
      ${partitionModeRadioHtml}
      ${diskAssertionRadioHtml}
    `

    // === 事件监听设置 ===

    // 1. 主要分区模式
    setupRadioContainer('partitioning-mode-container', 'partition-mode', (value) => {
      this.updateModule('partitioning', { mode: value as 'interactive' | 'automatic' | 'custom' })
      this.renderPartitioning(targetId)
    }, true)

    // 2. Automatic 模式的嵌套卡片事件
    if (part.mode === 'automatic') {
      setupComboCard('target-disk-card', (value) => {
        this.updateModule('partitioning', { targetDisk: parseInt(value as string) || 0 })
      })

      setupComboCard('partition-layout-card', (value) => {
        this.updateModule('partitioning', { layout: value as 'GPT' | 'MBR' })
        this.renderPartitioning(targetId)
      })

      if (partitionLayout === 'GPT') {
        setupComboCard('esp-size-card', (value) => {
          this.updateModule('partitioning', { espSize: parseInt(value as string) || 300 })
        })
      }

      setupComboCard('recovery-mode-card', (value) => {
        this.updateModule('partitioning', { recoveryMode: value as 'partition' | 'folder' | 'none' })
        this.renderPartitioning(targetId)
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
            this.renderPartitioning(targetId)
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
    }

    // 4. 磁盘断言事件（无条件设置）
    setupRadioContainer('disk-assertion-container', 'disk-assertion-mode', (value) => {
      this.updateModule('partitioning', { diskAssertionMode: value as 'skip' | 'script' })
      this.renderPartitioning(targetId)
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

  // 渲染 Windows PE 子模块: Windows Edition
  private renderWindowsEditionAndSource(targetId = 'config-windows-edition') {
    const contentDiv = this.getRenderContent(targetId)
    if (!contentDiv) return

    const edition = this.config.windowsEdition
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
            options: preset.windowsEditions.map(e => ({
              value: e.id,
              label: e.name || e.id
            })),
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
      expanded: false
    })

    contentDiv.innerHTML = `
      ${editionModeRadioHtml}
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
      this.renderWindowsEditionAndSource(targetId)
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
              <fluent-radio name="account-mode" value="interactive-local" ${accounts.mode === 'interactive-local' ? 'checked' : ''}>交互式添加离线账户</fluent-radio>
              <fluent-radio name="account-mode" value="interactive-microsoft" ${accounts.mode === 'interactive-microsoft' ? 'checked' : ''}>交互式添加在线账户</fluent-radio>
              <fluent-radio name="account-mode" value="unattended" ${accounts.mode === 'unattended' ? 'checked' : ''}>按账户列表创建账户</fluent-radio>
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
          accs.push({ id: this.generateUUID(), name: '', displayName: '', password: '', group: 'Users' })
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
                  <fluent-text-field id="config-lockout-reset" type="number" value="${lockout.lockoutWindow || ''}" placeholder="Minutes" style="width: 100%;"></fluent-text-field>
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
        this.updateModule('lockoutSettings', { lockoutWindow: parseInt(e.target.value) || undefined })
      })
    }
  }

  // 渲染模块14: File Explorer tweaks
  private renderFileExplorer() {
    const contentDiv = this.getSectionContent('config-file-explorer')
    if (!contentDiv) return

    contentDiv.innerHTML = createComboCard({
      id: 'file-explorer-entry-card',
      title: t('isoConfig.uiPersonalization.fileExplorer'),
      description: t('isoConfig.uiPersonalization.fileExplorerEntryDesc'),
      icon: 'folder',
      controlType: 'clickable',
      value: ''
    })

    setupComboCard('file-explorer-entry-card', () => { }, () => {
      this.openUiPersonalizationSubPage('file-explorer', 'file-explorer-entry-card')
    })

    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块15: Start menu and taskbar
  private renderStartTaskbar() {
    const contentDiv = this.getSectionContent('config-start-taskbar')
    if (!contentDiv) return

    contentDiv.innerHTML = createComboCard({
      id: 'start-taskbar-entry-card',
      title: t('isoConfig.uiPersonalization.startTaskbar'),
      description: t('isoConfig.uiPersonalization.startTaskbarEntryDesc'),
      icon: 'layout-grid',
      controlType: 'clickable',
      value: ''
    })

    setupComboCard('start-taskbar-entry-card', () => { }, () => {
      this.openUiPersonalizationSubPage('start-taskbar', 'start-taskbar-entry-card')
    })

    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块16: System tweaks
  // 渲染模块10: System Optimization (合并Remove bloatware)
  private renderSystemOptimization() {
    const contentDiv = this.getSectionContent('config-system-optimization')
    if (!contentDiv) return

    const bloatware = this.config.bloatware
    const preset = this.getPresetData()

    // 1. Remove Bloatware - MultiColumnCheckboxContainer (非嵌入式，显示头部)
    // 先构建选项和值
    const bloatwareOptions = preset.bloatwareItems.map(item => ({
      value: item.id || item.name,
      label: item.name || item.id
    }))
    const bloatwareValues: Record<string, boolean> = {}
    preset.bloatwareItems.forEach(item => {
      const value = item.id || item.name
      if (value) {
        bloatwareValues[value] = bloatware.items.includes(value)
      }
    })

    const removeBloatwareHtml = createMultiColumnCheckboxContainer({
      id: 'remove-bloatware-container',
      name: 'remove-bloatware',
      title: t('isoConfig.systemOptimization.removeBloatware'),
      description: '',
      icon: 'trash-2',
      options: bloatwareOptions,
      values: bloatwareValues,
      expanded: false,
      showHeader: true, // 非嵌入式，显示头部
      minColumnWidth: 180,
      maxColumns: 4 // 限制最大列数，确保文本完整显示
    })

    contentDiv.innerHTML = `
      ${removeBloatwareHtml}
    `

    // === 事件监听设置 ===

    // 1. Remove Bloatware
    setupMultiColumnCheckboxContainer('remove-bloatware-container', 'remove-bloatware', (values) => {
      const items = Object.keys(values).filter(key => values[key] === true)
      this.updateModule('bloatware', { items })
    }, true)

    // 初始化图标
    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块17: Visual effects
  private renderVisualEffects() {
    const contentDiv = this.getSectionContent('config-visual-effects')
    if (!contentDiv) return
    contentDiv.innerHTML = ''
  }

  // 渲染模块18: Desktop icons
  private renderDesktopIcons() {
    const contentDiv = this.getSectionContent('config-desktop-icons')
    if (!contentDiv) return

    const icons = this.config.desktopIcons

    // 1. Delete Edge Desktop Icon - ComboCard switch
    const deleteEdgeIconCardHtml = createComboCard({
      id: 'delete-edge-desktop-icon-card',
      title: t('isoConfig.uiPersonalization.deleteEdgeDesktopIcon'),
      description: '',
      icon: 'trash-2',
      controlType: 'switch',
      value: icons.deleteEdgeDesktopIcon || false
    })

    // 2. Desktop Icons Mode - RadioContainer (嵌套 MultiColumnCheckboxContainer)
    const desktopIconsRadioHtml = createRadioContainer({
      id: 'desktop-icons-container',
      name: 'desktop-icons-mode',
      title: t('isoConfig.uiPersonalization.desktopIcons'),
      description: '',
      icon: 'layout-grid',
      options: [
        {
          value: 'default',
          label: t('isoConfig.uiPersonalization.defaultIcons'),
          description: ''
        },
        {
          value: 'custom',
          label: t('isoConfig.uiPersonalization.customIcons'),
          description: '',
          nestedCards: [
            {
              type: 'multiColumnCheckbox',
              config: {
                id: 'desktop-icons-options-container',
                name: 'desktop-icons-options',
                options: [
                  { value: 'iconControlPanel', label: t('isoConfig.uiPersonalization.iconControlPanel') },
                  { value: 'iconDesktop', label: t('isoConfig.uiPersonalization.iconDesktop') },
                  { value: 'iconDocuments', label: t('isoConfig.uiPersonalization.iconDocuments') },
                  { value: 'iconDownloads', label: t('isoConfig.uiPersonalization.iconDownloads') },
                  { value: 'iconGallery', label: t('isoConfig.uiPersonalization.iconGallery') },
                  { value: 'iconHome', label: t('isoConfig.uiPersonalization.iconHome') },
                  { value: 'iconMusic', label: t('isoConfig.uiPersonalization.iconMusic') },
                  { value: 'iconNetwork', label: t('isoConfig.uiPersonalization.iconNetwork') },
                  { value: 'iconPictures', label: t('isoConfig.uiPersonalization.iconPictures') },
                  { value: 'iconRecycleBin', label: t('isoConfig.uiPersonalization.iconRecycleBin') },
                  { value: 'iconThisPC', label: t('isoConfig.uiPersonalization.iconThisPC') },
                  { value: 'iconUserFiles', label: t('isoConfig.uiPersonalization.iconUserFiles') },
                  { value: 'iconVideos', label: t('isoConfig.uiPersonalization.iconVideos') }
                ],
                values: {
                  iconControlPanel: icons.iconControlPanel || false,
                  iconDesktop: icons.iconDesktop || false,
                  iconDocuments: icons.iconDocuments || false,
                  iconDownloads: icons.iconDownloads || false,
                  iconGallery: icons.iconGallery || false,
                  iconHome: icons.iconHome || false,
                  iconMusic: icons.iconMusic || false,
                  iconNetwork: icons.iconNetwork || false,
                  iconPictures: icons.iconPictures || false,
                  iconRecycleBin: icons.iconRecycleBin || false,
                  iconThisPC: icons.iconThisPC || false,
                  iconUserFiles: icons.iconUserFiles || false,
                  iconVideos: icons.iconVideos || false
                },
                showHeader: false, // 嵌入模式，隐藏头部
                minColumnWidth: 140,
                maxColumns: 3
              }
            }
          ]
        }
      ],
      selectedValue: icons.mode || 'default',
      expanded: false
    })

    contentDiv.innerHTML = `
      ${deleteEdgeIconCardHtml}
      ${desktopIconsRadioHtml}
    `

    // === 事件监听设置 ===

    // 1. Delete Edge Desktop Icon
    setupComboCard('delete-edge-desktop-icon-card', (value) => {
      this.updateModule('desktopIcons', { deleteEdgeDesktopIcon: value as boolean })
    })

    // 2. Desktop Icons mode
    setupRadioContainer('desktop-icons-container', 'desktop-icons-mode', (value) => {
      this.updateModule('desktopIcons', { mode: value as 'default' | 'custom' })
      this.renderDesktopIcons()
    }, true)

    // 3. Custom icons options (仅在custom模式下设置)
    if (icons.mode === 'custom') {
      setupMultiColumnCheckboxContainer('desktop-icons-options-container', 'desktop-icons-options', (values) => {
        this.updateModule('desktopIcons', values as Partial<DesktopIconSettings>)
      }, false) // 不更新头部值（因为已隐藏头部）
    }

    // 初始化图标
    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块19: Folders on Start
  private renderFoldersStart() {
    const contentDiv = this.getSectionContent('config-folders-start')
    if (!contentDiv) return
    contentDiv.innerHTML = ''
  }

  // 渲染模块23: Lock key settings
  private renderLockKeys() {
    const contentDiv = this.getSectionContent('config-lock-keys')
    if (!contentDiv) return

    const lockKeys = this.config.lockKeys

    // Lock Keys Mode - RadioContainer（将配置嵌入到 configure 选项中）
    const lockKeysRadioHtml = createRadioContainer({
      id: 'lock-keys-container',
      name: 'lock-keys-mode',
      title: t('isoConfig.accessibility.lockKeys'),
      description: '',
      icon: 'keyboard',
      options: [
        {
          value: 'skip',
          label: t('isoConfig.accessibility.lockKeysSkip'),
          description: ''
        },
        {
          value: 'configure',
          label: t('isoConfig.accessibility.lockKeysConfigure'),
          description: t('isoConfig.accessibility.lockKeyConfigDesc'),
          nestedCards: [
            // Caps Lock
            {
              id: 'config-caps-lock-initial-card',
              title: `${t('isoConfig.accessibility.lockKeyCapsLock')} - ${t('isoConfig.accessibility.lockKeyInitialState')}`,
              description: '',
              controlType: 'switch',
              value: lockKeys.capsLockInitial === 'on',
              borderless: true
            },
            {
              id: 'config-caps-lock-behavior-card',
              title: `${t('isoConfig.accessibility.lockKeyCapsLock')} - ${t('isoConfig.accessibility.lockKeyBehavior')}`,
              description: '',
              controlType: 'select',
              options: [
                { value: 'toggle', label: t('isoConfig.accessibility.lockKeyToggle') },
                { value: 'ignore', label: t('isoConfig.accessibility.lockKeyIgnore') }
              ],
              value: lockKeys.capsLockBehavior || 'toggle',
              borderless: true
            },
            // Num Lock
            {
              id: 'config-num-lock-initial-card',
              title: `${t('isoConfig.accessibility.lockKeyNumLock')} - ${t('isoConfig.accessibility.lockKeyInitialState')}`,
              description: '',
              controlType: 'switch',
              value: lockKeys.numLockInitial === 'on',
              borderless: true
            },
            {
              id: 'config-num-lock-behavior-card',
              title: `${t('isoConfig.accessibility.lockKeyNumLock')} - ${t('isoConfig.accessibility.lockKeyBehavior')}`,
              description: '',
              controlType: 'select',
              options: [
                { value: 'toggle', label: t('isoConfig.accessibility.lockKeyToggle') },
                { value: 'ignore', label: t('isoConfig.accessibility.lockKeyIgnore') }
              ],
              value: lockKeys.numLockBehavior || 'toggle',
              borderless: true
            },
            // Scroll Lock
            {
              id: 'config-scroll-lock-initial-card',
              title: `${t('isoConfig.accessibility.lockKeyScrollLock')} - ${t('isoConfig.accessibility.lockKeyInitialState')}`,
              description: '',
              controlType: 'switch',
              value: lockKeys.scrollLockInitial === 'on',
              borderless: true
            },
            {
              id: 'config-scroll-lock-behavior-card',
              title: `${t('isoConfig.accessibility.lockKeyScrollLock')} - ${t('isoConfig.accessibility.lockKeyBehavior')}`,
              description: '',
              controlType: 'select',
              options: [
                { value: 'toggle', label: t('isoConfig.accessibility.lockKeyToggle') },
                { value: 'ignore', label: t('isoConfig.accessibility.lockKeyIgnore') }
              ],
              value: lockKeys.scrollLockBehavior || 'toggle',
              borderless: true
            }
          ]
        }
      ],
      selectedValue: lockKeys.mode || 'skip',
      expanded: false
    })

    contentDiv.innerHTML = `
      ${lockKeysRadioHtml}
    `

    // === 事件监听设置 ===

    // 1. Lock Keys mode
    setupRadioContainer('lock-keys-container', 'lock-keys-mode', (value) => {
      this.updateModule('lockKeys', { mode: value as 'skip' | 'configure' })
      this.renderLockKeys()
    }, true)

    // 2. Lock Keys configuration (仅在configure模式下设置)
    if (lockKeys.mode === 'configure') {
      // Caps Lock - Initial State (switch)
      setupComboCard('config-caps-lock-initial-card', (value) => {
        this.updateModule('lockKeys', { capsLockInitial: (value as boolean) ? 'on' : 'off' })
      })

      // Caps Lock - Behavior (select)
      setupComboCard('config-caps-lock-behavior-card', (value) => {
        this.updateModule('lockKeys', { capsLockBehavior: value as 'toggle' | 'ignore' })
      })

      // Num Lock - Initial State (switch)
      setupComboCard('config-num-lock-initial-card', (value) => {
        this.updateModule('lockKeys', { numLockInitial: (value as boolean) ? 'on' : 'off' })
      })

      // Num Lock - Behavior (select)
      setupComboCard('config-num-lock-behavior-card', (value) => {
        this.updateModule('lockKeys', { numLockBehavior: value as 'toggle' | 'ignore' })
      })

      // Scroll Lock - Initial State (switch)
      setupComboCard('config-scroll-lock-initial-card', (value) => {
        this.updateModule('lockKeys', { scrollLockInitial: (value as boolean) ? 'on' : 'off' })
      })

      // Scroll Lock - Behavior (select)
      setupComboCard('config-scroll-lock-behavior-card', (value) => {
        this.updateModule('lockKeys', { scrollLockBehavior: value as 'toggle' | 'ignore' })
      })
    }

    // 初始化图标
    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块24: Sticky keys
  private renderStickyKeys() {
    const contentDiv = this.getSectionContent('config-sticky-keys')
    if (!contentDiv) return

    const sticky = this.config.stickyKeys

    // Sticky Keys Mode - RadioContainer (嵌套多个 ComboCard switch)
    const stickyKeysRadioHtml = createRadioContainer({
      id: 'sticky-keys-container',
      name: 'sticky-keys-mode',
      title: t('isoConfig.accessibility.stickyKeys'),
      description: t('isoConfig.accessibility.stickyKeysDesc'),
      icon: 'keyboard',
      options: [
        {
          value: 'default',
          label: t('isoConfig.accessibility.stickyKeysDefault'),
          description: ''
        },
        {
          value: 'disabled',
          label: t('isoConfig.accessibility.stickyKeysDisabled'),
          description: ''
        },
        {
          value: 'custom',
          label: t('isoConfig.accessibility.stickyKeysCustom'),
          description: '',
          nestedCards: [
            {
              id: 'sticky-keys-hotkey-active',
              title: t('isoConfig.accessibility.stickyKeysHotKeyActive'),
              controlType: 'switch',
              value: sticky.stickyKeysHotKeyActive || false,
              borderless: true
            },
            {
              id: 'sticky-keys-hotkey-sound',
              title: t('isoConfig.accessibility.stickyKeysHotKeySound'),
              controlType: 'switch',
              value: sticky.stickyKeysHotKeySound || false,
              borderless: true
            },
            {
              id: 'sticky-keys-indicator',
              title: t('isoConfig.accessibility.stickyKeysIndicator'),
              controlType: 'switch',
              value: sticky.stickyKeysIndicator || false,
              borderless: true
            },
            {
              id: 'sticky-keys-audible',
              title: t('isoConfig.accessibility.stickyKeysAudibleFeedback'),
              controlType: 'switch',
              value: sticky.stickyKeysAudibleFeedback || false,
              borderless: true
            },
            {
              id: 'sticky-keys-tristate',
              title: t('isoConfig.accessibility.stickyKeysTriState'),
              controlType: 'switch',
              value: sticky.stickyKeysTriState || false,
              borderless: true
            },
            {
              id: 'sticky-keys-two-keys',
              title: t('isoConfig.accessibility.stickyKeysTwoKeysOff'),
              controlType: 'switch',
              value: sticky.stickyKeysTwoKeysOff || false,
              borderless: true
            }
          ]
        }
      ],
      selectedValue: sticky.mode || 'default',
      expanded: false
    })

    contentDiv.innerHTML = `
      ${stickyKeysRadioHtml}
    `

    // === 事件监听设置 ===

    // 1. Sticky Keys mode
    setupRadioContainer('sticky-keys-container', 'sticky-keys-mode', (value) => {
      this.updateModule('stickyKeys', { mode: value as 'default' | 'disabled' | 'custom' })
      this.renderStickyKeys()
    }, true)

    // 2. Custom sticky keys options (仅在custom模式下设置)
    if (sticky.mode === 'custom') {
      setupComboCard('sticky-keys-hotkey-active', (value) => {
        this.updateModule('stickyKeys', { stickyKeysHotKeyActive: value as boolean })
      })
      setupComboCard('sticky-keys-hotkey-sound', (value) => {
        this.updateModule('stickyKeys', { stickyKeysHotKeySound: value as boolean })
      })
      setupComboCard('sticky-keys-indicator', (value) => {
        this.updateModule('stickyKeys', { stickyKeysIndicator: value as boolean })
      })
      setupComboCard('sticky-keys-audible', (value) => {
        this.updateModule('stickyKeys', { stickyKeysAudibleFeedback: value as boolean })
      })
      setupComboCard('sticky-keys-tristate', (value) => {
        this.updateModule('stickyKeys', { stickyKeysTriState: value as boolean })
      })
      setupComboCard('sticky-keys-two-keys', (value) => {
        this.updateModule('stickyKeys', { stickyKeysTwoKeysOff: value as boolean })
      })
    }

    // 初始化图标
    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块25: Personalization settings
  private renderPersonalization() {
    const contentDiv = this.getSectionContent('config-personalization')
    if (!contentDiv) return
    contentDiv.innerHTML = createComboCard({
      id: 'personalization-entry-card',
      title: t('isoConfig.uiPersonalization.personalization'),
      description: t('isoConfig.uiPersonalization.personalizationDesc'),
      icon: 'palette',
      controlType: 'clickable',
      value: ''
    })

    setupComboCard('personalization-entry-card', () => { }, () => {
      this.openUiPersonalizationSubPage('personalization', 'personalization-entry-card')
    })

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
                <input type="checkbox" class="bloatware-item" value="${item.id || item.name}" ${bloatware.items.includes(item.id || item.name) ? 'checked' : ''}>
                <span>${item.name || item.id}</span>
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
        const allItems = preset.bloatwareItems.map(i => i.id || i.name).filter(Boolean)
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

  // 生成UUID辅助函数
  private generateUUID(): string {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      const r = Math.random() * 16 | 0
      const v = c === 'x' ? r : (r & 0x3 | 0x8)
      return v.toString(16)
    })
  }

  // 渲染模块27: Run custom scripts
  private renderCustomScripts() {
    const contentDiv = this.getSectionContent('config-custom-scripts')
    if (!contentDiv) return

    const scripts = this.config.scripts

    // 辅助函数：获取脚本类型选项
    const getScriptTypeOptions = (phase: 'system' | 'defaultUser' | 'firstLogon' | 'userOnce'): Array<{ value: string; label: string }> => {
      if (phase === 'system') {
        return [
          { value: '.reg', label: '.reg' },
          { value: '.cmd', label: '.cmd' },
          { value: '.ps1', label: '.ps1' },
          { value: '.vbs', label: '.vbs' }
        ]
      } else if (phase === 'defaultUser') {
        return [
          { value: '.reg', label: '.reg' },
          { value: '.cmd', label: '.cmd' },
          { value: '.ps1', label: '.ps1' }
        ]
      } else {
        // firstLogon 和 userOnce
        return [
          { value: '.cmd', label: '.cmd' },
          { value: '.ps1', label: '.ps1' },
          { value: '.reg', label: '.reg' },
          { value: '.vbs', label: '.vbs' }
        ]
      }
    }

    // 辅助函数：将ScriptItem转换为DynamicListItem（使用ComboContainer嵌套ComboCard + TextCard）
    const scriptItemToDynamicListItem = (item: ScriptItem, phase: string, _index: number): DynamicListItem => {
      const typeOptions = getScriptTypeOptions(phase as any)

      // 使用 ComboContainer 嵌套 ComboCard（脚本类型选择）和 TextCard（脚本内容输入）
      const comboContainerConfig: ComboContainerConfig = {
        id: `config-${phase}-script-${item.id}`,
        name: `${phase}-script-${item.id}`,
        title: '',
        description: '',
        icon: 'file-code',
        nestedCards: [
          {
            id: `config-${phase}-script-type-${item.id}`,
            field: 'type',
            title: t('isoConfig.customScripts.scriptType'),
            controlType: 'select',
            options: typeOptions,
            value: item.type,
            borderless: true
          },
          {
            id: `config-${phase}-script-content-${item.id}`,
            field: 'content',
            title: t('isoConfig.customScripts.scriptContent'),
            description: t('isoConfig.customScripts.scriptContentDesc'),
            value: item.content,
            placeholder: t('isoConfig.customScripts.scriptContentPlaceholder'),
            rows: 5,
            borderless: true,
            showImportExport: false
          }
        ],
        showHeader: false,
        borderless: true
      }

      return {
        id: item.id,
        cardType: 'comboContainer',
        cardConfig: comboContainerConfig
      }
    }

    // 为每个阶段创建DynamicListContainer
    const systemItems: DynamicListItem[] = scripts.system.map((item, idx) => scriptItemToDynamicListItem(item, 'system', idx))
    const defaultUserItems: DynamicListItem[] = scripts.defaultUser.map((item, idx) => scriptItemToDynamicListItem(item, 'defaultUser', idx))
    const firstLogonItems: DynamicListItem[] = scripts.firstLogon.map((item, idx) => scriptItemToDynamicListItem(item, 'firstLogon', idx))
    const userOnceItems: DynamicListItem[] = scripts.userOnce.map((item, idx) => scriptItemToDynamicListItem(item, 'userOnce', idx))

    // 生成HTML - 使用4个独立的DynamicListContainer
    contentDiv.innerHTML = `
      ${createDynamicListContainer({
      id: 'config-system-scripts-list',
      name: 'system-scripts',
      title: t('isoConfig.customScripts.systemScripts'),
      description: t('isoConfig.customScripts.systemScriptsDesc'),
      icon: 'file-code',
      itemCardType: 'comboContainer',
      items: systemItems,
      expanded: true,
      showHeader: true,
      embedded: false,
      defaultCardConfig: () => {
        const newId = this.generateUUID()
        const typeOptions = getScriptTypeOptions('system')
        return {
          id: `config-system-script-${newId}`,
          name: `system-script-${newId}`,
          title: '',
          description: '',
          icon: 'file-code',
          nestedCards: [
            {
              id: `config-system-script-type-${newId}`,
              field: 'type',
              title: t('isoConfig.customScripts.scriptType'),
              controlType: 'select' as const,
              options: typeOptions,
              value: '.cmd',
              borderless: true
            },
            {
              id: `config-system-script-content-${newId}`,
              field: 'content',
              title: t('isoConfig.customScripts.scriptContent'),
              description: t('isoConfig.customScripts.scriptContentDesc'),
              value: '',
              placeholder: t('isoConfig.customScripts.scriptContentPlaceholder'),
              rows: 5,
              borderless: true,
              showImportExport: false
            }
          ],
          showHeader: false,
          borderless: true
        }
      }
    })}
      ${createDynamicListContainer({
      id: 'config-defaultuser-scripts-list',
      name: 'defaultuser-scripts',
      title: t('isoConfig.customScripts.defaultUserScripts'),
      description: t('isoConfig.customScripts.defaultUserScriptsDesc'),
      icon: 'file-code',
      itemCardType: 'comboContainer',
      items: defaultUserItems,
      expanded: true,
      showHeader: true,
      embedded: false,
      defaultCardConfig: () => {
        const newId = this.generateUUID()
        const typeOptions = getScriptTypeOptions('defaultUser')
        return {
          id: `config-defaultuser-script-${newId}`,
          name: `defaultuser-script-${newId}`,
          title: '',
          description: '',
          icon: 'file-code',
          nestedCards: [
            {
              id: `config-defaultuser-script-type-${newId}`,
              field: 'type',
              title: t('isoConfig.customScripts.scriptType'),
              controlType: 'select' as const,
              options: typeOptions,
              value: '.reg',
              borderless: true
            },
            {
              id: `config-defaultuser-script-content-${newId}`,
              field: 'content',
              title: t('isoConfig.customScripts.scriptContent'),
              description: t('isoConfig.customScripts.scriptContentDesc'),
              value: '',
              placeholder: t('isoConfig.customScripts.scriptContentPlaceholder'),
              rows: 5,
              borderless: true,
              showImportExport: false
            }
          ],
          showHeader: false,
          borderless: true
        }
      }
    })}
      ${createDynamicListContainer({
      id: 'config-firstlogon-scripts-list',
      name: 'firstlogon-scripts',
      title: t('isoConfig.customScripts.firstLogonScripts'),
      description: t('isoConfig.customScripts.firstLogonScriptsDesc'),
      icon: 'file-code',
      itemCardType: 'comboContainer',
      items: firstLogonItems,
      expanded: true,
      showHeader: true,
      embedded: false,
      defaultCardConfig: () => {
        const newId = this.generateUUID()
        const typeOptions = getScriptTypeOptions('firstLogon')
        return {
          id: `config-firstlogon-script-${newId}`,
          name: `firstlogon-script-${newId}`,
          title: '',
          description: '',
          icon: 'file-code',
          nestedCards: [
            {
              id: `config-firstlogon-script-type-${newId}`,
              title: t('isoConfig.customScripts.scriptType'),
              controlType: 'select' as const,
              options: typeOptions,
              value: '.cmd',
              borderless: true
            },
            {
              id: `config-firstlogon-script-content-${newId}`,
              title: t('isoConfig.customScripts.scriptContent'),
              description: t('isoConfig.customScripts.scriptContentDesc'),
              value: '',
              placeholder: t('isoConfig.customScripts.scriptContentPlaceholder'),
              rows: 5,
              borderless: true,
              showImportExport: false
            }
          ],
          showHeader: false,
          borderless: true
        }
      }
    })}
      ${createDynamicListContainer({
      id: 'config-useronce-scripts-list',
      name: 'useronce-scripts',
      title: t('isoConfig.customScripts.userOnceScripts'),
      description: t('isoConfig.customScripts.userOnceScriptsDesc'),
      icon: 'file-code',
      itemCardType: 'comboContainer',
      items: userOnceItems,
      expanded: true,
      showHeader: true,
      embedded: false,
      defaultCardConfig: () => {
        const newId = this.generateUUID()
        const typeOptions = getScriptTypeOptions('userOnce')
        return {
          id: `config-useronce-script-${newId}`,
          name: `useronce-script-${newId}`,
          title: '',
          description: '',
          icon: 'file-code',
          nestedCards: [
            {
              id: `config-useronce-script-type-${newId}`,
              title: t('isoConfig.customScripts.scriptType'),
              controlType: 'select' as const,
              options: typeOptions,
              value: '.cmd',
              borderless: true
            },
            {
              id: `config-useronce-script-content-${newId}`,
              title: t('isoConfig.customScripts.scriptContent'),
              description: t('isoConfig.customScripts.scriptContentDesc'),
              value: '',
              placeholder: t('isoConfig.customScripts.scriptContentPlaceholder'),
              rows: 5,
              borderless: true,
              showImportExport: false
            }
          ],
          showHeader: false,
          borderless: true
        }
      }
    })}
      ${createComboCard({
      id: 'config-restart-explorer',
      title: t('isoConfig.customScripts.restartExplorer'),
      description: '',
      icon: 'refresh-cw',
      controlType: 'switch',
      value: scripts.restartExplorer || false
    })}
    `

    // 设置每个列表容器的事件监听
    const setupListContainer = (phase: 'system' | 'defaultUser' | 'firstLogon' | 'userOnce', containerId: string, items: DynamicListItem[]) => {
      // 获取配置信息
      let title = ''
      let description = ''
      if (phase === 'system') {
        title = t('isoConfig.customScripts.systemScripts')
        description = t('isoConfig.customScripts.systemScriptsDesc')
      } else if (phase === 'defaultUser') {
        title = t('isoConfig.customScripts.defaultUserScripts')
        description = t('isoConfig.customScripts.defaultUserScriptsDesc')
      } else if (phase === 'firstLogon') {
        title = t('isoConfig.customScripts.firstLogonScripts')
        description = t('isoConfig.customScripts.firstLogonScriptsDesc')
      } else if (phase === 'userOnce') {
        title = t('isoConfig.customScripts.userOnceScripts')
        description = t('isoConfig.customScripts.userOnceScriptsDesc')
      }

      setupDynamicListContainer(
        containerId,
        {
          id: containerId,
          name: `${phase}-scripts`,
          title: title,
          description: description,
          icon: 'file-code',
          itemCardType: 'comboContainer',
          items: items,
          expanded: true,
          showHeader: true,
          embedded: false,
          defaultCardConfig: () => {
            const newId = this.generateUUID()
            const typeOptions = getScriptTypeOptions(phase)
            return {
              id: `config-${phase}-script-${newId}`,
              name: `${phase}-script-${newId}`,
              title: '',
              description: '',
              icon: 'file-code',
              nestedCards: [
                {
                  id: `config-${phase}-script-type-${newId}`,
                  field: 'type',
                  title: t('isoConfig.customScripts.scriptType'),
                  controlType: 'select' as const,
                  options: typeOptions,
                  value: phase === 'defaultUser' ? '.reg' : '.cmd',
                  borderless: true
                },
                {
                  id: `config-${phase}-script-content-${newId}`,
                  field: 'content',
                  title: t('isoConfig.customScripts.scriptContent'),
                  description: t('isoConfig.customScripts.scriptContentDesc'),
                  value: '',
                  placeholder: t('isoConfig.customScripts.scriptContentPlaceholder'),
                  rows: 5,
                  borderless: true,
                  showImportExport: false
                }
              ],
              showHeader: false,
              borderless: true
            }
          }
        },
        (newItem: DynamicListItem) => {
          // 添加新项
          // 由于值收集的 key 格式可能不同，我们需要从 cardConfig 中获取初始值
          const defaultType = phase === 'defaultUser' ? '.reg' : '.cmd'
          const newScriptItem: ScriptItem = {
            id: newItem.id,
            type: defaultType,
            content: ''
          }
          const phaseScripts = [...scripts[phase], newScriptItem]
          this.updateModule('scripts', { [phase]: phaseScripts })
          this.renderCustomScripts()
        },
        (itemId: string) => {
          // 删除项
          const phaseScripts = scripts[phase].filter(item => item.id !== itemId)
          this.updateModule('scripts', { [phase]: phaseScripts })
          this.renderCustomScripts()
        },
        (itemId: string, values: any) => {
          const phaseScripts = scripts[phase].map(item => {
            if (item.id === itemId) {
              const updatedItem = { ...item }
              updatedItem.type = (values.type as string) || item.type
              updatedItem.content = (values.content as string) || item.content
              return updatedItem
            }
            return item
          })
          this.updateModule('scripts', { [phase]: phaseScripts })
        }
      )
    }

    setupListContainer('system', 'config-system-scripts-list', systemItems)
    setupListContainer('defaultUser', 'config-defaultuser-scripts-list', defaultUserItems)
    setupListContainer('firstLogon', 'config-firstlogon-scripts-list', firstLogonItems)
    setupListContainer('userOnce', 'config-useronce-scripts-list', userOnceItems)

    setupComboCard('config-restart-explorer', (value) => {
      this.updateModule('scripts', { restartExplorer: value as boolean })
    })

    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  // 渲染模块29: XML markup for more components
  private renderXmlMarkup() {
    const contentDiv = this.getSectionContent('config-xml-markup')
    if (!contentDiv) return

    const xmlMarkup = this.config.xmlMarkup

    // Pass 选项
    const passOptions = [
      { value: 'offlineServicing', label: 'offlineServicing' },
      { value: 'windowsPE', label: 'windowsPE' },
      { value: 'generalize', label: 'generalize' },
      { value: 'specialize', label: 'specialize' },
      { value: 'auditSystem', label: 'auditSystem' },
      { value: 'auditUser', label: 'auditUser' },
      { value: 'oobeSystem', label: 'oobeSystem' }
    ]

    // 辅助函数：将 XML 组件转换为 DynamicListItem
    const componentToDynamicListItem = (comp: XmlMarkupComponent): DynamicListItem => {
      const comboContainerConfig: ComboContainerConfig = {
        id: `config-xml-component-${comp.id}`,
        name: `xml-component-${comp.id}`,
        title: '',
        description: '',
        icon: 'code',
        nestedCards: [
          {
            id: `config-xml-component-name-${comp.id}`,
            field: 'component',
            title: t('isoConfig.xmlMarkup.component'),
            controlType: 'text',
            value: comp.component,
            placeholder: t('isoConfig.xmlMarkup.componentPlaceholder'),
            borderless: true
          },
          {
            id: `config-xml-component-pass-${comp.id}`,
            field: 'pass',
            title: t('isoConfig.xmlMarkup.pass'),
            controlType: 'select',
            options: passOptions,
            value: comp.pass,
            borderless: true
          },
          {
            id: `config-xml-component-markup-${comp.id}`,
            field: 'markup',
            title: t('isoConfig.xmlMarkup.xmlMarkup'),
            description: '',
            value: comp.markup,
            placeholder: '',
            rows: 5,
            borderless: true,
            showImportExport: false
          }
        ],
        showHeader: false,
        borderless: true
      }

      return {
        id: comp.id,
        cardType: 'comboContainer',
        cardConfig: comboContainerConfig
      }
    }

    // 将组件转换为 DynamicListItem
    const items: DynamicListItem[] = xmlMarkup.components.map(comp => componentToDynamicListItem(comp))

    // 生成 HTML
    contentDiv.innerHTML = createDynamicListContainer({
      id: 'config-xml-markup-list',
      name: 'xml-markup',
      title: t('isoConfig.xmlMarkup.title'),
      description: t('isoConfig.xmlMarkup.description'),
      icon: 'code',
      itemCardType: 'comboContainer',
      items: items,
      expanded: true,
      showHeader: true,
      embedded: false,
      defaultCardConfig: () => {
        const newId = this.generateUUID()
        return {
          id: `config-xml-component-${newId}`,
          name: `xml-component-${newId}`,
          title: '',
          description: '',
          icon: 'code',
          nestedCards: [
            {
              id: `config-xml-component-name-${newId}`,
              field: 'component',
              title: t('isoConfig.xmlMarkup.component'),
              controlType: 'text',
              value: '',
              placeholder: t('isoConfig.xmlMarkup.componentPlaceholder'),
              borderless: true
            },
            {
              id: `config-xml-component-pass-${newId}`,
              field: 'pass',
              title: t('isoConfig.xmlMarkup.pass'),
              controlType: 'select',
              options: passOptions,
              value: 'windowsPE',
              borderless: true
            },
            {
              id: `config-xml-component-markup-${newId}`,
              field: 'markup',
              title: t('isoConfig.xmlMarkup.xmlMarkup'),
              description: '',
              value: '',
              placeholder: '',
              rows: 5,
              borderless: true,
              showImportExport: false
            }
          ],
          showHeader: false,
          borderless: true
        }
      }
    })

    // 设置事件监听
    setupDynamicListContainer(
      'config-xml-markup-list',
      {
        id: 'config-xml-markup-list',
        name: 'xml-markup',
        title: t('isoConfig.xmlMarkup.title'),
        description: t('isoConfig.xmlMarkup.description'),
        icon: 'code',
        itemCardType: 'comboContainer',
        items: items,
        expanded: true,
        showHeader: true,
        embedded: false,
        defaultCardConfig: () => {
          const newId = this.generateUUID()
          return {
            id: `config-xml-component-${newId}`,
            name: `xml-component-${newId}`,
            title: '',
            description: '',
            icon: 'code',
            nestedCards: [
              {
                id: `config-xml-component-name-${newId}`,
                field: 'component',
                title: t('isoConfig.xmlMarkup.component'),
                controlType: 'text',
                value: '',
                placeholder: t('isoConfig.xmlMarkup.componentPlaceholder'),
                borderless: true
              },
              {
                id: `config-xml-component-pass-${newId}`,
                field: 'pass',
                title: t('isoConfig.xmlMarkup.pass'),
                controlType: 'select',
                options: passOptions,
                value: 'windowsPE',
                borderless: true
              },
              {
                id: `config-xml-component-markup-${newId}`,
                field: 'markup',
                title: t('isoConfig.xmlMarkup.xmlMarkup'),
                description: '',
                value: '',
                placeholder: '',
                rows: 5,
                borderless: true,
                showImportExport: false
              }
            ],
            showHeader: false,
            borderless: true
          }
        }
      },
      (_newItem: DynamicListItem) => {
        // 添加新项
        const newComponent: XmlMarkupComponent = {
          id: this.generateUUID(),
          component: '',
          pass: 'windowsPE',
          markup: ''
        }
        const components = [...xmlMarkup.components, newComponent]
        this.updateModule('xmlMarkup', { components })
        this.renderXmlMarkup()
      },
      (itemId: string) => {
        // 删除项
        const components = xmlMarkup.components.filter(comp => comp.id !== itemId)
        this.updateModule('xmlMarkup', { components })
        this.renderXmlMarkup()
      },
      (itemId: string, values: any) => {
        // 更新项 - values 是从 ComboContainer 收集的值对象
        const components = [...xmlMarkup.components]
        const component = components.find(comp => comp.id === itemId)

        if (component) {
          component.component = (values.component as string) || ''
          component.pass = (values.pass as string) || 'windowsPE'
          component.markup = (values.markup as string) || ''
          this.updateModule('xmlMarkup', { components })
        }
      }
    )

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
export { createDefaultConfig }

