/**
 * 集成与部署工作区
 * 实现 WIM 编辑、镜像导出、设备烧录等功能
 */

import {
  createComboCard,
  setupComboCard,
  createComboContainer,
  createDynamicListContainer,
  setupDynamicListContainer,
  type DynamicListItem,
  type ComboCardConfig,
  type ComboContainerConfig,
  type DynamicListContainerConfig
} from './workspace'
import { getConfigManager, createDefaultConfig } from './iso-config'

// ========================================
// 模板状态管理
// ========================================

export interface IsoTemplate {
  name: string
  path: string
  size?: number
  language?: string
}

class TemplateManager {
  private currentTemplate: IsoTemplate | null = null
  private listeners: Array<(template: IsoTemplate | null) => void> = []

  setTemplate(template: IsoTemplate) {
    this.currentTemplate = template
    console.log('[templateManager] setTemplate, language:', template.language)
    window.dispatchEvent(new CustomEvent('template-changed', { detail: template }))
    this.notify()
  }

  getTemplate(): IsoTemplate | null {
    return this.currentTemplate
  }

  addListener(callback: (template: IsoTemplate | null) => void) {
    this.listeners.push(callback)
    // 立即执行一次以同步初始状态
    callback(this.currentTemplate)
  }

  private notify() {
    this.listeners.forEach(cb => cb(this.currentTemplate))
  }
}

export const templateManager = new TemplateManager()

// ========================================
// 工作区类
// ========================================

export class IsoBurnWorkspace {
  private panel: HTMLElement | null = null
  private integrateInstaller = true
  private fileMappings: Array<{
    id: string
    sourcePath: string
    targetPath: string
  }> = []
  private wimImages: Array<{
    index: number
    name?: string
    edition?: string
    architecture?: string
    build?: string
    label: string
  }> = []
  private selectedWimImageIndex = ''
  private wimImageMessage = '选择当前要写入文件映射和安装器内容的映像索引'
  private wimImageLoading = false
  private exportDirectory = ''
  private latestBuiltIsoPath = ''
  private buildTaskId: string | null = null
  private buildStatus: 'idle' | 'running' | 'completed' | 'failed' = 'idle'
  private buildMessage = '根据当前模板与配置生成镜像文件'
  private burnTaskId: string | null = null
  private burnStatus: 'idle' | 'running' | 'completed' | 'failed' = 'idle'
  private burnMessage = '使用内建驱动器直接将镜像写入选中的 U 盘'

  constructor() {
    this.panel = document.getElementById('workspace-iso-burn')
  }

  init() {
    if (!this.panel) return

    this.setupEventListeners()

    // 1. 订阅模板变化并渲染顶部卡片
    templateManager.addListener((template) => {
      this.renderTemplateCard(template)
      void this.refreshWimImages(template)
    })

    // 2. 渲染 WIM 编辑部分
    this.renderWimEdit()

    // 3. 渲染导出与部署部分
    this.renderExport()
  }

  private renderTemplateCard(template: IsoTemplate | null) {
    const container = document.getElementById('burn-template-card')
    if (!container) return

    if (!template) {
      container.innerHTML = createComboCard({
        id: 'current-template-empty',
        title: '未选择镜像模板',
        description: '请先在“下载与缓存”页面选择一个本地镜像并点击“设为模板”',
        icon: 'triangle-alert',
        controlType: 'none',
        value: '',
        borderColor: 'rgba(255, 152, 0, 0.4)',
        backgroundColor: 'rgba(255, 152, 0, 0.05)'
      })
      this.refreshIcons()
      return
    }

    const cardConfig: ComboCardConfig = {
      id: 'current-template-info',
      title: '当前镜像模板',
      description: `${template.name}\n路径: ${template.path}`,
      icon: 'disc',
      controlType: 'clickable', // 虽然是展示，但设为 clickable 可以引导用户点击返回
      value: ''
    }

    container.innerHTML = createComboCard(cardConfig)
    setupComboCard('current-template-info', () => { }, () => {
      // 点击跳转回下载与缓存
      const cacheMenu = document.querySelector('fluent-option[value="iso-cache"]') as any
      if (cacheMenu) cacheMenu.click()
    })
    this.refreshIcons()
  }

  private renderWimEdit() {
    const container = document.querySelector('#burn-wim-edit .section-content') as HTMLElement
    if (!container) return

    // 1. 集成 Auto Installer 开关
    const switchConfig: ComboCardConfig = {
      id: 'burn-integrate-installer',
      title: '将 Windows Auto Installer 集成到镜像',
      description: '勾选后，会在目标镜像中预置本安装器及所需运行环境',
      icon: 'package-plus',
      controlType: 'switch',
      value: this.integrateInstaller
    }

    const wimImageSelectConfig: ComboCardConfig = {
      id: 'burn-selected-wim-image',
      title: '目标 WIM 映像',
      description: this.wimImageMessage,
      icon: 'layers',
      controlType: 'select',
      options: this.getWimImageOptions(),
      value: this.selectedWimImageIndex
    }

    // 2. 文件映射动态列表
    const mappingConfig: DynamicListContainerConfig = {
      id: 'burn-file-mappings',
      name: 'file-mappings',
      title: '自定义文件映射',
      description: '将本地文件或目录添加到镜像中的指定位置',
      icon: 'files',
      itemCardType: 'comboContainer',
      expanded: true,
      defaultCardConfig: () => this.createMappingCardConfig(),
      items: this.fileMappings.map(mapping => this.createMappingListItem(mapping))
    }

    container.innerHTML = `
      ${createComboCard(switchConfig)}
      ${createComboCard(wimImageSelectConfig)}
      ${createDynamicListContainer(mappingConfig)}
    `

    setupComboCard('burn-integrate-installer', (val) => {
      this.integrateInstaller = Boolean(val)
    })

    setupComboCard('burn-selected-wim-image', (val) => {
      this.selectedWimImageIndex = String(val || '')
    })

    // Mapping 列表监听
    setupDynamicListContainer('burn-file-mappings', mappingConfig,
      (newItem) => {
        this.fileMappings = [
          ...this.fileMappings,
          {
            id: newItem.id,
            sourcePath: '',
            targetPath: ''
          }
        ]
        this.renderWimEdit()
      },
      (itemId) => {
        this.fileMappings = this.fileMappings.filter(mapping => mapping.id !== itemId)
        this.renderWimEdit()
      },
      (itemId, value) => {
        this.fileMappings = this.fileMappings.map(mapping => {
          if (mapping.id !== itemId) return mapping

          return {
            ...mapping,
            sourcePath: (value.sourcePath as string) || '',
            targetPath: (value.targetPath as string) || ''
          }
        })
      }
    )

    this.refreshIcons()
  }

  private setupEventListeners() {
    if (this.panel) {
      this.panel.addEventListener('click', (e: Event) => {
        const target = e.target as HTMLElement
        const header = target.closest('.card-expandable-header')
        if (header) {
          const card = header.closest('.card-expandable')
          if (card) {
            card.classList.toggle('expanded')
            if (window.lucide) {
              window.lucide.createIcons()
            }
          }
        }
      })
    }
  }

  private renderExport() {
    const container = document.querySelector('#burn-export .section-content') as HTMLElement
    if (!container) return

    const localExportConfig: ComboContainerConfig = {
      id: 'burn-local-export-container',
      title: '本地导出',
      description: '生成 ISO 并保存到本地目录',
      icon: 'folder-output',
      expanded: false,
      nestedCards: [
        this.createExportDirectoryCardConfig(),
        this.createExportActionCardConfig()
      ]
    }

    const deviceSelectConfig = this.createDeviceSelectCardConfig('burn-device-select-burn')
    const burnRefreshDevicesConfig: ComboCardConfig = {
      id: 'burn-refresh-devices-burn',
      title: '刷新存储设备列表',
      description: '重新扫描当前可用于烧录的移动存储设备',
      icon: 'refresh-cw',
      controlType: 'button',
      buttonLabel: '刷新列表',
      buttonAppearance: 'outline',
      value: '',
      borderless: true
    }
    const burnActionConfig: ComboCardConfig = {
      id: 'burn-action-direct',
      title: '烧录镜像到可移动存储设备',
      description: this.getBurnActionDescription(),
      icon: 'zap',
      controlType: 'button',
      buttonLabel: '开始烧录',
      value: '',
      borderless: true
    }
    const burnClearActionConfig: ComboCardConfig = {
      id: 'burn-action-clear',
      title: '清除所有部署环境',
      description: '恢复目标设备为普通单分区数据盘状态',
      icon: 'trash-2',
      controlType: 'button',
      buttonLabel: '清除环境',
      buttonAppearance: 'outline',
      value: '',
      borderless: true
    }

    const imageBurnConfig: ComboContainerConfig = {
      id: 'burn-image-burn-container',
      title: '镜像烧录',
      description: '选择设备后将生成的 ISO 直接写入启动盘',
      icon: 'hard-drive-download',
      expanded: false,
      nestedCards: [deviceSelectConfig, burnRefreshDevicesConfig, burnActionConfig, burnClearActionConfig]
    }

    const ventoyDeviceConfig = this.createDeviceSelectCardConfig('burn-device-select-ventoy')
    const ventoyRefreshDevicesConfig: ComboCardConfig = {
      id: 'burn-refresh-devices-ventoy',
      title: '刷新存储设备列表',
      description: '重新扫描当前可用于 Ventoy 部署的移动存储设备',
      icon: 'refresh-cw',
      controlType: 'button',
      buttonLabel: '刷新列表',
      buttonAppearance: 'outline',
      value: '',
      borderless: true
    }
    const ventoyActionConfig: ComboCardConfig = {
      id: 'burn-action-ventoy',
      title: '将 Ventoy 部署到移动设备并复制镜像',
      description: '自动格式化为 Ventoy 启动盘并将生成的 ISO 放入其中',
      icon: 'layers',
      controlType: 'button',
      buttonLabel: '开始部署',
      value: '',
      borderless: true
    }

    const ventoyDeployConfig: ComboContainerConfig = {
      id: 'burn-ventoy-deploy-container',
      title: 'Ventoy 部署',
      description: '部署 Ventoy 并复制生成的 ISO 到目标设备',
      icon: 'package-open',
      expanded: false,
      nestedCards: [ventoyDeviceConfig, ventoyRefreshDevicesConfig, ventoyActionConfig]
    }

    container.innerHTML = `
      ${createComboContainer(localExportConfig)}
      ${createComboContainer(imageBurnConfig)}
      ${createComboContainer(ventoyDeployConfig)}
    `

    // 选择导出目录
    setupComboCard('burn-export-dir', () => { }, async () => {
      await this.pickExportDirectory()
    })

    this.refreshDeviceList()

    setupComboCard('burn-device-select-burn', (val) => {
      console.log('Burn device selected:', val)
    })

    setupComboCard('burn-refresh-devices-burn', () => { }, () => {
      void this.refreshDeviceList()
    })

    setupComboCard('burn-device-select-ventoy', (val) => {
      console.log('Ventoy device selected:', val)
    })

    setupComboCard('burn-refresh-devices-ventoy', () => { }, () => {
      void this.refreshDeviceList()
    })

    setupComboCard('burn-action-direct', () => { }, () => {
      void this.startBurnTask()
    })

    setupComboCard('burn-action-ventoy', () => { }, () => {
      console.log('Execute ventoy deploy')
    })

    setupComboCard('burn-action-clear', () => { }, () => {
      console.log('Execute clear environment')
    })

    setupComboCard('burn-action-export-local', () => { }, () => {
      void this.startBuildTask()
    })

    this.refreshIcons()
  }

  private getBurnActionDescription(): string {
    if (this.burnStatus === 'running') {
      return this.burnMessage
    }

    if (this.burnStatus === 'completed' && this.latestBuiltIsoPath) {
      return `最近烧录镜像: ${this.latestBuiltIsoPath}`
    }

    if (this.burnStatus === 'failed') {
      return this.burnMessage
    }

    if (this.latestBuiltIsoPath) {
      return `将使用最近导出的镜像: ${this.latestBuiltIsoPath}`
    }

    return this.burnMessage
  }

  private createMappingCardConfig(mapping?: { id: string, sourcePath: string, targetPath: string }): ComboContainerConfig {
    const mappingId = mapping?.id || `mapping-${Date.now()}`

    return {
      id: `burn-file-mapping-${mappingId}`,
      name: `burn-file-mapping-${mappingId}`,
      title: '',
      description: '',
      icon: 'file-plus-2',
      showHeader: false,
      borderless: true,
      nestedCards: [
        {
          id: `burn-file-mapping-source-${mappingId}`,
          field: 'sourcePath',
          title: '本地源路径',
          description: '输入待集成的本地文件或目录路径',
          icon: 'folder-open',
          controlType: 'text',
          value: mapping?.sourcePath || '',
          placeholder: '例如: D:\\Drivers\\',
          borderless: true
        },
        {
          id: `burn-file-mapping-target-${mappingId}`,
          field: 'targetPath',
          title: 'WIM 内目标路径',
          description: '输入镜像内的目标目录',
          icon: 'folder-tree',
          controlType: 'text',
          value: mapping?.targetPath || '',
          placeholder: '例如: \\Windows\\Setup\\Scripts\\',
          borderless: true
        }
      ]
    }
  }

  private createMappingListItem(mapping: { id: string, sourcePath: string, targetPath: string }): DynamicListItem {
    return {
      id: mapping.id,
      cardType: 'comboContainer',
      cardConfig: this.createMappingCardConfig(mapping)
    }
  }

  private createExportDirectoryCardConfig(): ComboCardConfig {
    return {
      id: 'burn-export-dir',
      title: '导出目录',
      description: this.exportDirectory || '未选择目录 (默认导出到桌面)',
      icon: 'folder-output',
      controlType: 'button',
      buttonLabel: '选择目录',
      buttonAppearance: 'outline',
      value: '',
      borderless: true
    }
  }

  private createExportActionCardConfig(): ComboCardConfig {
    return {
      id: 'burn-action-export-local',
      title: '导出 ISO 到本地目录',
      description: this.buildMessage,
      icon: 'download',
      controlType: 'button',
      buttonLabel: '执行导出',
      value: '',
      borderless: true
    }
  }

  private createDeviceSelectCardConfig(id: string): ComboCardConfig {
    return {
      id,
      title: '目标移动存储设备',
      description: '选择用于烧录或部署的 USB 闪存盘',
      icon: 'usb',
      controlType: 'select',
      options: [
        { value: '', label: '未检测到可用设备' }
      ],
      value: '',
      borderless: true
    }
  }

  private async pickExportDirectory() {
    if (!window.electronAPI?.showOpenDialog) return

    try {
      const result = await window.electronAPI.showOpenDialog({
        title: '选择导出目录',
        properties: ['openDirectory']
      })
      if (!result.canceled && result.filePaths.length > 0) {
        this.exportDirectory = result.filePaths[0]
        const card = document.getElementById('burn-export-dir') as HTMLElement
        const desc = card?.querySelector('.card-description') as HTMLElement
        if (desc) {
          desc.textContent = this.exportDirectory
        }
        console.log('Selected export dir:', this.exportDirectory)
      }
    } catch (err) {
      console.error('Failed to pick directory:', err)
    }
  }

  private async startBuildTask() {
    const template = templateManager.getTemplate()
    if (!template?.path) {
      alert('请先在“下载与缓存”中选择一个镜像模板')
      return
    }

    if (!this.exportDirectory) {
      alert('请先选择导出目录')
      return
    }

    if (!window.electronAPI?.sendToBackend) {
      alert('Electron API 不可用')
      return
    }

    const configManager = getConfigManager()
    const config = configManager ? configManager.getConfig() : createDefaultConfig()
    const outputName = `${this.sanitizeFileName(template.name || 'custom')}_customized.iso`
    const validatedMappings = this.getValidatedFileMappings()
    if (!validatedMappings) {
      return
    }

    this.buildStatus = 'running'
    this.buildMessage = '正在构建 ISO，请稍候...'
    this.syncExportActionCards()

    try {
      const response = await window.electronAPI.sendToBackend({
        jsonrpc: '2.0',
        id: Date.now(),
        method: 'deployment_build_start',
        params: {
          template_iso: template.path,
          export_dir: this.exportDirectory,
          output_name: outputName,
          integrate_installer: this.integrateInstaller,
          selected_wim_image_index: this.selectedWimImageIndex,
          file_mappings: validatedMappings,
          config
        }
      })

      const taskId = response?.result?.task_id as string | undefined
      if (!taskId) {
        throw new Error('未获取到构建任务 ID')
      }

      this.buildTaskId = taskId
      this.pollBuildStatus(taskId)
    } catch (err: any) {
      this.buildStatus = 'failed'
      this.buildMessage = `导出失败: ${err?.message || '未知错误'}`
      this.syncExportActionCards()
    }
  }

  private async pollBuildStatus(taskId: string) {
    if (!window.electronAPI?.sendToBackend) return

    try {
      const response = await window.electronAPI.sendToBackend({
        jsonrpc: '2.0',
        id: Date.now(),
        method: 'deployment_build_status',
        params: { task_id: taskId }
      })

      const status = response?.result || {}
      const progress = status.progress || {}
      if (status.status === 'completed') {
        this.buildStatus = 'completed'
        this.latestBuiltIsoPath = status.result?.iso_path || status.result?.output_path || ''
        this.buildMessage = this.latestBuiltIsoPath
          ? `导出完成: ${this.latestBuiltIsoPath}`
          : '导出完成'
        this.syncExportActionCards()
        return
      }

      if (status.status === 'failed') {
        this.buildStatus = 'failed'
        this.buildMessage = `导出失败: ${status.error || '未知错误'}`
        this.syncExportActionCards()
        return
      }

      this.buildMessage = this.formatBuildProgressMessage(progress)
      this.syncExportActionCards()
      window.setTimeout(() => {
        void this.pollBuildStatus(taskId)
      }, 1000)
    } catch (err: any) {
      this.buildStatus = 'failed'
      this.buildMessage = `导出状态查询失败: ${err?.message || '未知错误'}`
      this.syncExportActionCards()
    }
  }

  private async startBurnTask() {
    if (!this.latestBuiltIsoPath) {
      alert('请先执行本地导出，生成可烧录的 ISO')
      return
    }

    const burnDeviceSelect = document.getElementById('burn-device-select-burn-control') as any
    const devicePath = burnDeviceSelect?.value || ''
    if (!devicePath) {
      alert('请选择目标移动存储设备')
      return
    }

    if (!window.electronAPI?.sendToBackend) {
      alert('Electron API 不可用')
      return
    }

    this.burnStatus = 'running'
    this.burnMessage = '正在烧录镜像，请勿移除设备...'
    this.syncExportActionCards()

    try {
      const response = await window.electronAPI.sendToBackend({
        jsonrpc: '2.0',
        id: Date.now(),
        method: 'burn_start',
        params: {
          iso_path: this.latestBuiltIsoPath,
          device_path: devicePath
        }
      })

      const taskId = response?.result?.task_id as string | undefined
      if (!taskId) {
        throw new Error('未获取到烧录任务 ID')
      }

      this.burnTaskId = taskId
      this.pollBurnStatus(taskId)
    } catch (err: any) {
      this.burnStatus = 'failed'
      this.burnMessage = `烧录失败: ${err?.message || '未知错误'}`
      this.syncExportActionCards()
    }
  }

  private async pollBurnStatus(taskId: string) {
    if (!window.electronAPI?.sendToBackend) return

    try {
      const response = await window.electronAPI.sendToBackend({
        jsonrpc: '2.0',
        id: Date.now(),
        method: 'burn_status',
        params: { task_id: taskId }
      })

      const status = response?.result || {}
      if (status.status === 'completed') {
        this.burnStatus = 'completed'
        this.burnMessage = '烧录完成'
        this.syncExportActionCards()
        return
      }

      if (status.status === 'failed') {
        this.burnStatus = 'failed'
        this.burnMessage = `烧录失败: ${status.error || '未知错误'}`
        this.syncExportActionCards()
        return
      }

      this.burnMessage = '正在烧录镜像，请勿移除设备...'
      this.syncExportActionCards()
      window.setTimeout(() => {
        void this.pollBurnStatus(taskId)
      }, 1000)
    } catch (err: any) {
      this.burnStatus = 'failed'
      this.burnMessage = `烧录状态查询失败: ${err?.message || '未知错误'}`
      this.syncExportActionCards()
    }
  }

  private syncExportActionCards() {
    this.updateCardDescription('burn-action-export-local', this.buildMessage)
    this.updateCardDescription('burn-action-direct', this.getBurnActionDescription())
  }

  private updateCardDescription(cardId: string, description: string) {
    const card = document.getElementById(cardId) as HTMLElement | null
    const descriptionEl = card?.querySelector('.card-description') as HTMLElement | null
    if (descriptionEl) {
      descriptionEl.textContent = description
    }
  }

  private sanitizeFileName(name: string): string {
    const baseName = name.replace(/\.[^.]+$/, '')
    const sanitized = baseName.replace(/[<>:"/\\|?*]+/g, '_').trim()
    return sanitized || 'custom'
  }

  private refreshIcons() {
    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  private getWimImageOptions(): Array<{ value: string, label: string }> {
    if (this.wimImages.length === 0) {
      return [{ value: '', label: '暂无可用映像' }]
    }

    return this.wimImages.map(image => ({
      value: String(image.index),
      label: image.label
    }))
  }

  private async refreshWimImages(template: IsoTemplate | null) {
    this.wimImages = []
    this.selectedWimImageIndex = ''
    this.wimImageLoading = false

    if (!template?.path) {
      this.wimImageMessage = '请先选择镜像模板'
      this.renderWimEdit()
      return
    }

    this.wimImageLoading = true
    this.wimImageMessage = '已检测到模板变化，正在读取 WIM 映像列表...'
    this.renderWimEdit()

    if (!window.electronAPI?.sendToBackend) {
      this.wimImageLoading = false
      this.wimImageMessage = 'Electron API 不可用，无法读取 WIM 映像列表'
      this.renderWimEdit()
      return
    }

    try {
      const response = await window.electronAPI.sendToBackend({
        jsonrpc: '2.0',
        id: Date.now(),
        method: 'deployment_list_wim_images',
        params: {
          template_iso: template.path
        }
      })

      if (templateManager.getTemplate()?.path !== template.path) {
        return
      }

      const images = Array.isArray(response?.result?.images) ? response.result.images : []
      this.wimImages = images.map((image: any) => ({
        index: Number(image.index),
        name: image.name,
        edition: image.edition,
        architecture: image.architecture,
        build: image.build,
        label: image.label || `${image.index} - ${image.name || 'Image'}`
      })).filter(image => Number.isFinite(image.index) && image.index > 0)

      if (this.wimImages.length > 0) {
        this.selectedWimImageIndex = String(this.wimImages[0].index)
        this.wimImageMessage = '选择当前要写入文件映射和安装器内容的映像索引'
      } else {
        this.wimImageMessage = '当前模板未发现可编辑的 install.wim/install.esd 映像'
      }
    } catch (err: any) {
      this.wimImages = []
      this.selectedWimImageIndex = ''
      this.wimImageMessage = `读取 WIM 映像失败: ${err?.message || '未知错误'}`
    } finally {
      this.wimImageLoading = false
    }

    this.renderWimEdit()
  }

  private getValidatedFileMappings(): Array<{ source_path: string, target_path: string }> | null {
    const normalized = this.fileMappings
      .map(item => ({
        source_path: item.sourcePath.trim(),
        target_path: item.targetPath.trim()
      }))
      .filter(item => item.source_path || item.target_path)

    for (const mapping of normalized) {
      if (!mapping.source_path || !mapping.target_path) {
        alert('自定义文件映射中的本地源路径和 WIM 目标路径都必须填写')
        return null
      }
    }

    return normalized
  }

  private formatBuildProgressMessage(progress: any): string {
    const message = typeof progress?.message === 'string' ? progress.message : ''
    const percent = typeof progress?.percent === 'number' ? `${progress.percent}%` : ''

    if (message && percent) {
      return `${message} (${percent})`
    }
    if (message) {
      return message
    }
    return '正在构建 ISO，请稍候...'
  }

  private async refreshDeviceList() {
    if (!window.electronAPI?.sendToBackend) return
    try {
      const response = await window.electronAPI.sendToBackend({
        jsonrpc: '2.0',
        id: Date.now(),
        method: 'burn_list_devices',
        params: {}
      })
      
      const devices = (response?.result?.devices || []) as Array<{path: string, label: string, size: number}>
      ;['burn-device-select-burn-control', 'burn-device-select-ventoy-control'].forEach(selectId => {
        const select = document.getElementById(selectId) as any
        if (!select) return

        if (devices.length > 0) {
          select.innerHTML = devices.map(d => {
            const sizeGB = (d.size / (1024 ** 3)).toFixed(1)
            const label = d.label || '未知卷标'
            return `<fluent-option value="${d.path}">${label} (${d.path}) - ${sizeGB} GB</fluent-option>`
          }).join('')
          select.value = devices[0].path
        } else {
          select.innerHTML = '<fluent-option value="">未检测到可用设备</fluent-option>'
        }
      })
    } catch (err) {
      console.error('Failed to list devices:', err)
    }
  }
}

export function initIsoBurn() {
  try {
    const workspace = new IsoBurnWorkspace()
    workspace.init()
    
    // 确保图标加载
    if ((window as any).lucide) {
      (window as any).lucide.createIcons()
    }
  } catch (err) {
    console.error('Failed to init IsoBurn workspace:', err)
  }
}
