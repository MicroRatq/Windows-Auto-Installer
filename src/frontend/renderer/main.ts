import {
  provideFluentDesignSystem,
  fluentListbox,
  fluentOption,
  fluentTextField,
  fluentButton,
  fluentSelect,
  fluentProgress,
  fluentMenu,
  fluentMenuItem,
  fluentCheckbox,
  fluentRadio,
  fluentTextArea,
  fluentSwitch
} from '@fluentui/web-components'

// 导入i18n模块
import { t, addLanguageChangeListener, waitForI18nInit } from './i18n'
// 导入下载与缓存模块
import { initIsoCache } from './iso-cache'
// 导入自定义配置模块
import { initIsoConfig } from './iso-config'
// 导入集成与部署模块
import { initIsoBurn } from './iso-burn'
// 导入设置模块
import { settingsManager } from './settings'

// 注册 Fluent UI 组件
provideFluentDesignSystem()
  .register(
    fluentListbox(),
    fluentOption(),
    fluentTextField(),
    fluentButton(),
    fluentSelect(),
    fluentProgress(),
    fluentMenu(),
    fluentMenuItem(),
    fluentCheckbox(),
    fluentRadio(),
    fluentTextArea(),
    fluentSwitch()
  )

// 菜单配置
interface MenuItem {
  id: string
  label: string
  icon: string // Lucide图标名称
}

const settingsMenuItem: MenuItem = { id: 'settings', label: '设置', icon: 'settings' }

const mainMenuItems: MenuItem[] = [
  { id: 'iso', label: '镜像', icon: 'disc' },
  { id: 'system', label: '系统配置', icon: 'settings' },
  { id: 'software', label: '软件安装', icon: 'package' }
]

const subMenuConfig: Record<string, MenuItem[]> = {
  iso: [
    { id: 'iso-cache', label: '下载与缓存', icon: 'download' },
    { id: 'iso-config', label: '自定义配置', icon: 'file-edit' },
    { id: 'iso-burn', label: '集成与部署', icon: 'disc-2' }
  ],
  system: [
    { id: 'migration', label: '系统迁移', icon: 'move' },
    { id: 'activation', label: '系统激活', icon: 'key' }
  ],
  software: [
    { id: 'office', label: 'Office安装', icon: 'file-text' },
    { id: 'packages', label: '软件包安装', icon: 'box' }
  ]
}

// 状态
let currentMainMenu = 'iso'
let currentSubMenu = 'iso-cache'
let sidebarWidth = 200
let isDark = true
let isCollapsed = false // 侧边栏是否折叠

// DOM 元素（在init函数中获取，确保组件已注册）
let subMenuEls: Map<string, any> = new Map() // 存储每个主菜单对应的二级菜单listbox
let sidebarEl: HTMLElement | null = null
let sidebarResizerEl: HTMLElement | null = null
let workspaceTitleEl: HTMLElement | null = null
let workspacePanels: Map<string, HTMLElement> = new Map()
let collapseToggleBtn: HTMLElement | null = null
let collapseIcon: HTMLElement | null = null
let sidebarMenuGroups: HTMLElement | null = null
let iconMenuEl: any = null
let settingsMenuEl: any = null
let pendingSidebarWidth: number | null = null
let resizeFrameId: number | null = null
let activeResizePointerId: number | null = null
let isSidebarAnimating = false
let sidebarAnimationTimeoutId: number | null = null

function findMenuItemById(id: string): MenuItem | undefined {
  if (id === settingsMenuItem.id) {
    return settingsMenuItem
  }

  for (const items of Object.values(subMenuConfig)) {
    const item = items.find(menuItem => menuItem.id === id)
    if (item) {
      return item
    }
  }

  return undefined
}

function updateSettingsMenuState() {
  if (!settingsMenuEl) return

  const settingsOption = settingsMenuEl.querySelector('fluent-option') as any
  if (!settingsOption) return

  const isActive = currentSubMenu === settingsMenuItem.id
  settingsMenuEl.value = isActive ? settingsMenuItem.id : ''
  settingsOption.selected = isActive
  settingsOption.setAttribute('aria-selected', isActive ? 'true' : 'false')
}

function clearListboxSelection(listbox: any) {
  if (!listbox) return

  if ('selectedIndex' in listbox) {
    listbox.selectedIndex = -1
  }

  const options = listbox.querySelectorAll('fluent-option') as NodeListOf<any>
  options.forEach((option: any) => {
    option.selected = false
    option.setAttribute('aria-selected', 'false')
  })
}

function setActiveWorkspacePanel(id: string) {
  workspacePanels.forEach((panel, panelId) => {
    const isActive = panelId === id
    panel.classList.toggle('active', isActive)
    panel.style.display = isActive ? 'block' : 'none'
  })
}

function syncExpandedMenuSelection() {
  if (!currentSubMenu || !currentMainMenu) return

  const currentSubMenuEl = subMenuEls.get(currentMainMenu)
  if (!currentSubMenuEl) return

  currentSubMenuEl.value = currentSubMenu
  const options = currentSubMenuEl.querySelectorAll('fluent-option') as NodeListOf<any>
  options.forEach((option: any) => {
    const isSelected = option.value === currentSubMenu
    option.selected = isSelected
    option.setAttribute('aria-selected', isSelected ? 'true' : 'false')
  })
}

function syncCollapsedIconSelection() {
  if (!currentSubMenu || !iconMenuEl) return

  iconMenuEl.value = currentSubMenu
  const options = iconMenuEl.querySelectorAll('fluent-option') as NodeListOf<any>
  options.forEach((option: any) => {
    const isSelected = option.value === currentSubMenu
    option.selected = isSelected
    option.setAttribute('aria-selected', isSelected ? 'true' : 'false')
  })
}

function finalizeSidebarAnimation(collapsed: boolean) {
  if (!sidebarEl) return

  isSidebarAnimating = false

  if (sidebarAnimationTimeoutId !== null) {
    window.clearTimeout(sidebarAnimationTimeoutId)
    sidebarAnimationTimeoutId = null
  }

  sidebarEl.classList.remove('expanding', 'collapsing')

  if (collapsed) {
    sidebarEl.classList.add('collapsed')
    syncCollapsedIconSelection()
  } else {
    sidebarEl.classList.remove('collapsed')
    syncExpandedMenuSelection()
  }

  if (window.lucide) {
    window.lucide.createIcons()
  }
}

function runSidebarWidthTransition(collapsed: boolean) {
  if (!sidebarEl) return

  const handleTransitionEnd = (event: TransitionEvent) => {
    if (event.target !== sidebarEl || event.propertyName !== 'width') {
      return
    }

    sidebarEl.removeEventListener('transitionend', handleTransitionEnd)
    finalizeSidebarAnimation(collapsed)
  }

  sidebarEl.addEventListener('transitionend', handleTransitionEnd)

  sidebarAnimationTimeoutId = window.setTimeout(() => {
    sidebarEl?.removeEventListener('transitionend', handleTransitionEnd)
    finalizeSidebarAnimation(collapsed)
  }, 380)
}

// 创建带图标的选项
function createMenuOption(item: MenuItem, showLabel: boolean = true): any {
  const option = document.createElement('fluent-option') as any
  option.value = item.id

  // 创建包装元素确保水平排列
  const wrapper = document.createElement('span')
  wrapper.className = 'menu-option-content'
  wrapper.style.display = 'flex'
  wrapper.style.flexDirection = 'row'
  wrapper.style.alignItems = 'center'
  wrapper.style.gap = '8px'

  // 创建图标元素
  const iconEl = document.createElement('i')
  iconEl.setAttribute('data-lucide', item.icon)
  iconEl.className = 'menu-icon'

  wrapper.appendChild(iconEl)

  if (showLabel) {
    // 展开状态：图标 + 文字，使用独立标签避免宽度过渡中被挤成竖排
    const labelEl = document.createElement('span')
    labelEl.className = 'menu-label'
    labelEl.textContent = item.label
    wrapper.appendChild(labelEl)
  } else {
    // 折叠状态：仅图标
    option.title = item.label // 添加提示文字
  }

  option.appendChild(wrapper)
  option.selected = false
  option.setAttribute('aria-selected', 'false')

  // 初始化Lucide图标
  if (window.lucide) {
    window.lucide.createIcons()
  }

  return option
}

// 更新指定主菜单的二级菜单
function updateSubMenu(mainMenuId: string) {
  const subMenuEl = subMenuEls.get(mainMenuId)
  if (!subMenuEl) return

  const items = subMenuConfig[mainMenuId] || []

  subMenuEl.innerHTML = ''

  // 创建选项，初始状态都不选中
  items.forEach(item => {
    const option = createMenuOption(item, true)
    subMenuEl.appendChild(option)
  })
}

// 更新图标菜单（折叠状态）
function updateIconMenu() {
  if (!iconMenuEl) return

  iconMenuEl.innerHTML = ''

  // 收集所有二级菜单项
  const allItems: MenuItem[] = []
  Object.values(subMenuConfig).forEach(items => {
    allItems.push(...items)
  })

  // 创建图标选项
  allItems.forEach(item => {
    const option = createMenuOption(item, false)
    iconMenuEl.appendChild(option)
  })

  // 延迟设置当前选中项，确保DOM已更新
  setTimeout(() => {
    if (!iconMenuEl || !currentSubMenu) return

    // 先清除所有选项的选中状态
    const allOptions = iconMenuEl.querySelectorAll('fluent-option') as NodeListOf<any>
    allOptions.forEach((option: any) => {
      option.selected = false
      option.setAttribute('aria-selected', 'false')
    })

    // 设置当前选中项
    const currentOption = Array.from(allOptions)
      .find((opt: any) => opt.value === currentSubMenu)
    if (currentOption) {
      iconMenuEl.value = currentSubMenu
      currentOption.selected = true
      currentOption.setAttribute('aria-selected', 'true')
    }
  }, 0)
}

// 更新工作区标题和内容
function updateWorkspaceTitle() {
  if (!workspaceTitleEl) return
  const item = findMenuItemById(currentSubMenu)
  workspaceTitleEl.textContent = item ? item.label : '未知'
  setActiveWorkspacePanel(currentSubMenu)
  updateSettingsMenuState()
}

// 选择子菜单
function selectSubMenu(id: string) {
  console.log('Selecting sub menu:', id)
  currentSubMenu = id

  if (id === settingsMenuItem.id) {
    subMenuEls.forEach((subMenuEl) => {
      clearListboxSelection(subMenuEl)
    })

    clearListboxSelection(iconMenuEl)
    updateSettingsMenuState()

    requestAnimationFrame(() => {
      updateWorkspaceTitle()
    })

    return
  }

  // 确定该子菜单属于哪个主菜单
  let parentMainMenu = currentMainMenu
  for (const [mainMenuId, items] of Object.entries(subMenuConfig)) {
    if (items.find(item => item.id === id)) {
      parentMainMenu = mainMenuId
      break
    }
  }

  // 如果切换到了不同的主菜单，更新主菜单
  if (parentMainMenu !== currentMainMenu) {
    currentMainMenu = parentMainMenu
  }

  // 根据官方文档，使用selectedIndex和selectedOptions清除所有listbox的选中状态
  subMenuEls.forEach((subMenuEl, mainMenuId) => {
    if (mainMenuId !== currentMainMenu) {
      if ('selectedIndex' in subMenuEl) {
        (subMenuEl as any).selectedIndex = -1
      }
    }
  })

  // 设置当前选中的listbox
  if (isCollapsed) {
    // 折叠状态：更新图标菜单
    if (iconMenuEl) {
      // 先清除其他listbox的选中状态
      subMenuEls.forEach((subMenuEl, mainMenuId) => {
        if ('selectedIndex' in subMenuEl) {
          (subMenuEl as any).selectedIndex = -1
        }
      })
      // 设置图标菜单选中
      iconMenuEl.value = id
      const options = iconMenuEl.querySelectorAll('fluent-option') as NodeListOf<any>
      options.forEach((option: any) => {
        const isSelected = option.value === id
        option.selected = isSelected
      })
    }
  } else {
    // 展开状态：清除图标菜单，更新对应的二级菜单
    if (iconMenuEl && 'selectedIndex' in iconMenuEl) {
      (iconMenuEl as any).selectedIndex = -1
    }

    clearListboxSelection(settingsMenuEl)

    const currentSubMenuEl = subMenuEls.get(currentMainMenu)
    if (currentSubMenuEl) {
      currentSubMenuEl.value = id
      // 确保选中状态正确设置
      const options = currentSubMenuEl.querySelectorAll('fluent-option') as NodeListOf<any>
      options.forEach((option: any) => {
        const isSelected = option.value === id
        option.selected = isSelected
      })
    }
  }

  // 使用requestAnimationFrame确保DOM更新后更新工作区标题
  requestAnimationFrame(() => {
    updateWorkspaceTitle()
  })
}

// 窗口控制
function minimizeWindow() {
  window.electronAPI?.windowMinimize()
}

function maximizeWindow() {
  window.electronAPI?.windowMaximize()
}

function closeWindow() {
  window.electronAPI?.windowClose()
}

// 主题切换
function toggleTheme() {
  isDark = !isDark
  const root = document.documentElement
  if (isDark) {
    root.removeAttribute('data-theme')
  } else {
    root.setAttribute('data-theme', 'light')
  }
  console.log('主题切换为:', isDark ? '深色' : '浅色')
}

// 侧边栏调整宽度
function startResize(e: PointerEvent) {
  e.preventDefault()

  if (isCollapsed || !sidebarResizerEl) {
    return
  }

  activeResizePointerId = e.pointerId
  sidebarResizerEl.setPointerCapture(e.pointerId)

  const startX = e.clientX
  const startWidth = sidebarWidth

  document.body.classList.add('sidebar-resizing')

  const flushSidebarWidth = () => {
    resizeFrameId = null

    if (pendingSidebarWidth === null || !sidebarEl) {
      return
    }

    sidebarWidth = pendingSidebarWidth
    sidebarEl.style.width = `${sidebarWidth}px`
  }

  function onPointerMove(e: PointerEvent) {
    if (e.pointerId !== activeResizePointerId) {
      return
    }

    e.preventDefault()

    pendingSidebarWidth = Math.max(150, Math.min(400, startWidth + (e.clientX - startX)))

    if (resizeFrameId === null) {
      resizeFrameId = requestAnimationFrame(flushSidebarWidth)
    }
  }

  function stopResize() {
    document.body.classList.remove('sidebar-resizing')

    if (resizeFrameId !== null) {
      cancelAnimationFrame(resizeFrameId)
      resizeFrameId = null
    }

    if (pendingSidebarWidth !== null && sidebarEl) {
      sidebarWidth = pendingSidebarWidth
      sidebarEl.style.width = `${sidebarWidth}px`
    }

    pendingSidebarWidth = null
    activeResizePointerId = null
    document.removeEventListener('pointermove', onPointerMove)
    document.removeEventListener('pointerup', onPointerUp)
    document.removeEventListener('pointercancel', onPointerCancel)
    window.removeEventListener('blur', onWindowBlur)

    if (sidebarResizerEl && sidebarResizerEl.hasPointerCapture(e.pointerId)) {
      sidebarResizerEl.releasePointerCapture(e.pointerId)
    }
  }

  function onPointerUp(e: PointerEvent) {
    if (e.pointerId !== activeResizePointerId) {
      return
    }

    stopResize()
  }

  function onPointerCancel(e: PointerEvent) {
    if (e.pointerId !== activeResizePointerId) {
      return
    }

    stopResize()
  }

  function onWindowBlur() {
    stopResize()
  }

  document.addEventListener('pointermove', onPointerMove)
  document.addEventListener('pointerup', onPointerUp)
  document.addEventListener('pointercancel', onPointerCancel)
  window.addEventListener('blur', onWindowBlur)
}

// 打开设置
function openSettings() {
  console.log('打开设置')
  selectSubMenu(settingsMenuItem.id)
}

// 切换侧边栏折叠状态
function toggleCollapse() {
  if (!sidebarEl || !sidebarMenuGroups || !iconMenuEl || !collapseIcon) return

  if (isSidebarAnimating) {
    return
  }

  isCollapsed = !isCollapsed
  isSidebarAnimating = true

  if (isCollapsed) {
    syncExpandedMenuSelection()
    updateIconMenu()
    sidebarEl.classList.remove('expanding', 'collapsed')
    sidebarEl.classList.add('collapsing')
    sidebarEl.style.width = '70px'
    runSidebarWidthTransition(true)
  } else {
    syncExpandedMenuSelection()
    sidebarEl.classList.remove('collapsing', 'collapsed')
    sidebarEl.classList.add('expanding')
    sidebarEl.style.width = sidebarWidth + 'px'
    runSidebarWidthTransition(false)
  }
}

// 初始化
async function init() {
  // 等待 i18n 初始化完成
  await waitForI18nInit()

  // 获取DOM元素
  sidebarEl = document.getElementById('sidebar')
  sidebarResizerEl = document.getElementById('sidebar-resizer')
  workspaceTitleEl = document.getElementById('workspace-title')
  collapseToggleBtn = document.getElementById('collapse-toggle')
  collapseIcon = document.getElementById('collapse-icon')
  sidebarMenuGroups = document.getElementById('sidebar-menu-groups')
  iconMenuEl = document.getElementById('icon-menu')
  settingsMenuEl = document.getElementById('settings-menu')

  // 初始化所有二级菜单listbox
  const mainMenuIds = ['iso', 'system', 'software']
  mainMenuIds.forEach(mainMenuId => {
    const subMenuEl = document.getElementById(`sub-menu-${mainMenuId}`) as any
    if (subMenuEl) {
      subMenuEls.set(mainMenuId, subMenuEl)
    }
  })

  // 初始化工作区面板映射
  const panelIds = [
    'iso-cache', 'iso-config', 'iso-burn',
    'migration', 'activation',
    'office', 'packages',
    'settings'
  ]
  panelIds.forEach(id => {
    const panel = document.getElementById(`workspace-${id}`)
    if (panel) {
      workspacePanels.set(id, panel)
    }
  })

  // 设置初始侧边栏宽度
  if (sidebarEl) {
    sidebarEl.style.width = sidebarWidth + 'px'
  }

  // 初始化主题
  if (!isDark) {
    document.documentElement.setAttribute('data-theme', 'light')
  }

  // 初始化所有二级菜单
  mainMenuIds.forEach(mainMenuId => {
    updateSubMenu(mainMenuId)
  })

  // 为每个二级菜单添加事件监听（仅监听点击事件）
  subMenuEls.forEach((subMenuEl, mainMenuId) => {
    // 只监听点击事件，不监听change事件
    // 这样可以避免程序设置value时触发change事件导致的递归调用
    subMenuEl.addEventListener('click', (event: MouseEvent) => {
      const target = event.target as HTMLElement
      const option = target.closest('fluent-option') as any
      if (option && option.value) {
        const selectedValue = option.value
        console.log('Sub menu click event:', selectedValue)
        if (selectedValue !== currentSubMenu) {
          // 不在这里设置value，让selectSubMenu统一处理
          selectSubMenu(selectedValue)
        }
      }
    })
  })

  // 为图标菜单添加事件监听
  if (iconMenuEl) {
    iconMenuEl.addEventListener('click', (event: MouseEvent) => {
      const target = event.target as HTMLElement
      const option = target.closest('fluent-option') as any
      if (option && option.value) {
        const selectedValue = option.value
        console.log('Icon menu click event:', selectedValue)
        if (selectedValue !== currentSubMenu) {
          selectSubMenu(selectedValue)
        }
      }
    })
  }

  if (settingsMenuEl) {
    settingsMenuEl.addEventListener('click', (event: MouseEvent) => {
      const target = event.target as HTMLElement
      const option = target.closest('fluent-option') as any
      if (option?.value === settingsMenuItem.id && currentSubMenu !== settingsMenuItem.id) {
        selectSubMenu(settingsMenuItem.id)
      }
    })
  }

  // 折叠按钮事件监听
  if (collapseToggleBtn) {
    collapseToggleBtn.addEventListener('click', toggleCollapse)
  }

  // 初始化Lucide图标
  if (window.lucide) {
    window.lucide.createIcons()
  }

  // 设置初始选中状态，确保只有一个选项被激活
  setTimeout(() => {
    // 清除其他listbox的选中状态
    subMenuEls.forEach((subMenuEl, mainMenuId) => {
      if (mainMenuId !== currentMainMenu) {
        if ('selectedIndex' in subMenuEl) {
          (subMenuEl as any).selectedIndex = -1
        }
      }
    })

    // 设置当前选中的listbox
    const currentSubMenuEl = subMenuEls.get(currentMainMenu)
    if (currentSubMenuEl) {
      currentSubMenuEl.value = currentSubMenu
      // 确保选中状态正确设置
      const options = currentSubMenuEl.querySelectorAll('fluent-option') as NodeListOf<any>
      options.forEach((option: any) => {
        const isSelected = option.value === currentSubMenu
        option.selected = isSelected
      })
    }

    // 使用requestAnimationFrame确保DOM更新后更新工作区标题
    requestAnimationFrame(() => {
      updateWorkspaceTitle()
    })
  }, 100)

  // 窗口控制按钮
  const minimizeBtn = document.getElementById('window-minimize')
  if (minimizeBtn) {
    minimizeBtn.addEventListener('click', minimizeWindow)
  }

  const maximizeBtn = document.getElementById('window-maximize')
  if (maximizeBtn) {
    maximizeBtn.addEventListener('click', maximizeWindow)
  }

  const closeBtn = document.getElementById('window-close')
  if (closeBtn) {
    closeBtn.addEventListener('click', closeWindow)
  }

  // 主题切换
  const themeToggle = document.getElementById('theme-toggle')
  if (themeToggle) {
    themeToggle.addEventListener('click', toggleTheme)
  }

  // 设置按钮
  // 侧边栏调整
  if (sidebarResizerEl) {
    sidebarResizerEl.addEventListener('pointerdown', startResize)
  }

  // 测试后端连接
  if (window.electronAPI) {
    window.electronAPI.sendToBackend({
      jsonrpc: '2.0',
      id: 1,
      method: 'ping',
      params: {}
    }).then((response: any) => {
      console.log('后端连接成功:', response)
    }).catch((error: any) => {
      console.error('后端连接失败:', error)
    })
  }

  // 初始化下载与缓存工作区
  if (typeof initIsoCache === 'function') {
    initIsoCache()
  }

  // 初始化自定义配置工作区
  if (typeof initIsoConfig === 'function') {
    initIsoConfig()
  }

  // 初始化集成与部署工作区
  if (typeof initIsoBurn === 'function') {
    initIsoBurn()
  }

  // 初始化设置页面
  settingsManager.init()

  // 监听语言切换事件，更新section标题
  addLanguageChangeListener(() => {
    updateSectionTitles()
  })

  // 初始化section标题
  updateSectionTitles()

  console.log('应用初始化完成')
}

// 更新所有section标题
function updateSectionTitles() {
  const sectionTitles: Record<string, string> = {
    'config-region-language': t('isoConfig.regionLanguage.title'),
    'config-setup-settings': t('isoConfig.setupSettings.title'),
    'config-name-account': t('isoConfig.nameAccount.title'),
    'config-windows-pe-stage': t('isoConfig.windowsPEStage.title'),
    'config-ui-personalization': t('isoConfig.uiPersonalization.title'),
    'config-wifi': t('isoConfig.wifi.title'),
    'config-accessibility': t('isoConfig.accessibility.title'),
    'config-system-optimization': t('isoConfig.systemOptimization.title'),
    'config-advanced-settings': t('isoConfig.advancedSettings.title')
  }

  Object.entries(sectionTitles).forEach(([sectionId, title]) => {
    const sectionEl = document.getElementById(sectionId)
    if (sectionEl) {
      const titleEl = sectionEl.querySelector('.section-title')
      if (titleEl) {
        titleEl.textContent = title
      }
    }
  })
}

// 等待DOM加载完成
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init)
} else {
  init()
}

