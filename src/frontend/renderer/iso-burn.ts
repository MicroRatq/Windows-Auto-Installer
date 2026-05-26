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

// ========================================
// 模板状态管理
// ========================================

export interface IsoTemplate {
  name: string
  path: string
  size?: number
}

class TemplateManager {
  private currentTemplate: IsoTemplate | null = null
  private listeners: Array<(template: IsoTemplate | null) => void> = []

  setTemplate(template: IsoTemplate) {
    this.currentTemplate = template
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
  private fileMappings: Array<{
    id: string
    sourcePath: string
    targetPath: string
  }> = []
  private exportDirectory = ''

  constructor() {
    this.panel = document.getElementById('workspace-iso-burn')
  }

  init() {
    if (!this.panel) return

    this.setupEventListeners()

    // 1. 订阅模板变化并渲染顶部卡片
    templateManager.addListener((template) => {
      this.renderTemplateCard(template)
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
      container.innerHTML = `
        <div class="info-card info-card-warning" style="margin-bottom: 20px;">
          <div class="info-card-content">
            <div class="info-card-title">未选择镜像模板</div>
            <div class="info-card-description">请先在“下载与缓存”页面选择一个本地镜像并点击“设为模板”</div>
          </div>
        </div>
      `
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
      value: true
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
      ${createDynamicListContainer(mappingConfig)}
    `

    setupComboCard('burn-integrate-installer', (val) => {
      console.log('Integrate installer:', val)
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

          const sourceKey = Object.keys(value).find(key => key.includes('source'))
          const targetKey = Object.keys(value).find(key => key.includes('target'))

          return {
            ...mapping,
            sourcePath: (sourceKey ? value[sourceKey] : '') as string || '',
            targetPath: (targetKey ? value[targetKey] : '') as string || ''
          }
        })
      }
    )
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
    const burnActionConfig: ComboCardConfig = {
      id: 'burn-action-direct',
      title: '烧录镜像到可移动存储设备',
      description: '使用内建驱动器直接将镜像写入选中的 U 盘',
      icon: 'zap',
      controlType: 'button',
      buttonLabel: '开始烧录',
      value: '',
      borderless: true
    }

    const imageBurnConfig: ComboContainerConfig = {
      id: 'burn-image-burn-container',
      title: '镜像烧录',
      description: '选择设备后将生成的 ISO 直接写入启动盘',
      icon: 'hard-drive-download',
      expanded: false,
      nestedCards: [deviceSelectConfig, burnActionConfig]
    }

    const ventoyDeviceConfig = this.createDeviceSelectCardConfig('burn-device-select-ventoy')
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

    const clearActionConfig: ComboCardConfig = {
      id: 'burn-action-clear',
      title: '清除所有部署环境',
      description: '恢复 U 盘为普通单分区数据盘状态',
      icon: 'trash-2',
      controlType: 'button',
      buttonLabel: '清除环境',
      buttonAppearance: 'outline',
      value: '',
      borderless: true
    }

    const ventoyDeployConfig: ComboContainerConfig = {
      id: 'burn-ventoy-deploy-container',
      title: 'Ventoy 部署',
      description: '部署 Ventoy、复制 ISO，或清理部署环境',
      icon: 'package-open',
      expanded: false,
      nestedCards: [ventoyDeviceConfig, ventoyActionConfig, clearActionConfig]
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

    setupComboCard('burn-device-select-ventoy', (val) => {
      console.log('Ventoy device selected:', val)
    })

    setupComboCard('burn-action-direct', () => { }, () => {
      console.log('Execute direct burn')
    })

    setupComboCard('burn-action-ventoy', () => { }, () => {
      console.log('Execute ventoy deploy')
    })

    setupComboCard('burn-action-clear', () => { }, () => {
      console.log('Execute clear environment')
    })

    setupComboCard('burn-action-export-local', () => { }, () => {
      console.log('Execute local export')
    })
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
      description: '根据当前模板与配置生成镜像文件',
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
