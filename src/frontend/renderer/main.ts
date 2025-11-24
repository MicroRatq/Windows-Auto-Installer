import {
  provideFluentDesignSystem,
  fluentListbox,
  fluentOption,
  fluentTextField,
  fluentButton
} from '@fluentui/web-components'

// 注册 Fluent UI 组件
provideFluentDesignSystem()
  .register(
    fluentListbox(),
    fluentOption(),
    fluentTextField(),
    fluentButton()
  )

// 菜单配置
interface MenuItem {
  id: string
  label: string
}

const mainMenuItems: MenuItem[] = [
  { id: 'iso', label: '镜像' },
  { id: 'system', label: '系统配置' },
  { id: 'software', label: '软件安装' }
]

const subMenuConfig: Record<string, MenuItem[]> = {
  iso: [
    { id: 'iso-cache', label: '镜像缓存' },
    { id: 'iso-config', label: '镜像配置' },
    { id: 'iso-burn', label: '镜像烧录' }
  ],
  system: [
    { id: 'migration', label: '系统迁移' },
    { id: 'activation', label: '系统激活' }
  ],
  software: [
    { id: 'office', label: 'Office安装' },
    { id: 'packages', label: '软件包安装' }
  ]
}

// 状态
let currentMainMenu = 'iso'
let currentSubMenu = 'iso-cache'
let sidebarWidth = 200
let isDark = true

// DOM 元素（在init函数中获取，确保组件已注册）
let mainMenuEl: any = null
let subMenuEl: any = null
let sidebarEl: HTMLElement | null = null
let sidebarResizerEl: HTMLElement | null = null
let workspaceTitleEl: HTMLElement | null = null
let workspacePanels: Map<string, HTMLElement> = new Map()

// 更新二级菜单
function updateSubMenu() {
  if (!subMenuEl) return
  
  const items = subMenuConfig[currentMainMenu] || []
  
  // 如果当前子菜单不在新菜单中，先切换到第一个
  if (items.length > 0 && !items.find(item => item.id === currentSubMenu)) {
    currentSubMenu = items[0].id
  }
  
  subMenuEl.innerHTML = ''
  
  // 创建选项，使用更新后的 currentSubMenu
  items.forEach(item => {
    const option = document.createElement('fluent-option') as any
    option.value = item.id
    option.textContent = item.label
    const isSelected = item.id === currentSubMenu
    option.selected = isSelected
    if (isSelected) {
      option.setAttribute('aria-selected', 'true')
    } else {
      option.setAttribute('aria-selected', 'false')
    }
    subMenuEl.appendChild(option)
  })
  
  // 更新listbox的值和选中状态 - 使用 setTimeout 确保组件已渲染
  if (subMenuEl) {
    subMenuEl.value = currentSubMenu
    setTimeout(() => {
      const options = subMenuEl.querySelectorAll('fluent-option') as NodeListOf<any>
      options.forEach((option: any) => {
        const isSelected = option.value === currentSubMenu
        option.selected = isSelected
        if (isSelected) {
          option.setAttribute('aria-selected', 'true')
        } else {
          option.setAttribute('aria-selected', 'false')
        }
      })
    }, 50)
  }
  
  updateWorkspaceTitle()
}

// 更新工作区标题和内容
function updateWorkspaceTitle() {
  if (!workspaceTitleEl) return
  const items = subMenuConfig[currentMainMenu] || []
  const item = items.find(item => item.id === currentSubMenu)
  workspaceTitleEl.textContent = item ? item.label : '未知'
  
  // 切换工作区面板
  workspacePanels.forEach((panel, id) => {
    if (id === currentSubMenu) {
      panel.classList.add('active')
    } else {
      panel.classList.remove('active')
    }
  })
}

// 选择主菜单
function selectMainMenu(id: string) {
  console.log('Selecting main menu:', id)
  currentMainMenu = id
  
  // 更新主菜单选中状态
  if (mainMenuEl) {
    mainMenuEl.value = id
    // 更新所有option的selected状态
    const options = mainMenuEl.querySelectorAll('fluent-option') as NodeListOf<any>
    options.forEach((option: any) => {
      const isSelected = option.value === id
      option.selected = isSelected
      if (isSelected) {
        option.setAttribute('aria-selected', 'true')
      } else {
        option.setAttribute('aria-selected', 'false')
      }
    })
  }
  
  // 切换到该主菜单的第一个子菜单
  const items = subMenuConfig[id] || []
  if (items.length > 0) {
    currentSubMenu = items[0].id
  }
  
  updateSubMenu()
  updateWorkspaceTitle()
}

// 选择子菜单
function selectSubMenu(id: string) {
  console.log('Selecting sub menu:', id)
  currentSubMenu = id
  
  // 更新子菜单选中状态
  if (subMenuEl) {
    subMenuEl.value = id
    // 更新所有option的selected状态
    const options = subMenuEl.querySelectorAll('fluent-option') as NodeListOf<any>
    options.forEach((option: any) => {
      const isSelected = option.value === id
      option.selected = isSelected
      if (isSelected) {
        option.setAttribute('aria-selected', 'true')
      } else {
        option.setAttribute('aria-selected', 'false')
      }
    })
  }
  updateWorkspaceTitle()
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
function startResize(e: MouseEvent) {
  const startX = e.clientX
  const startWidth = sidebarWidth
  
  function onMouseMove(e: MouseEvent) {
    const newWidth = startWidth + (e.clientX - startX)
    if (newWidth >= 150 && newWidth <= 400) {
      sidebarWidth = newWidth
      if (sidebarEl) {
        sidebarEl.style.width = sidebarWidth + 'px'
      }
    }
  }
  
  function onMouseUp() {
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }
  
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

// 打开设置
function openSettings() {
  console.log('打开设置')
}

// 初始化
function init() {
  // 获取DOM元素
  mainMenuEl = document.getElementById('main-menu') as any
  subMenuEl = document.getElementById('sub-menu') as any
  sidebarEl = document.getElementById('sidebar')
  sidebarResizerEl = document.getElementById('sidebar-resizer')
  workspaceTitleEl = document.getElementById('workspace-title')
  
  // 初始化工作区面板映射
  const panelIds = [
    'iso-cache', 'iso-config', 'iso-burn',
    'migration', 'activation',
    'office', 'packages'
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
  
  // 初始化主菜单
  if (mainMenuEl) {
    mainMenuEl.value = currentMainMenu
    
    // 设置初始选中项 - 使用 setTimeout 确保 Fluent UI 组件完全初始化
    setTimeout(() => {
      const mainMenuOptions = mainMenuEl.querySelectorAll('fluent-option') as NodeListOf<any>
      mainMenuOptions.forEach((option: any) => {
        const isSelected = option.value === currentMainMenu
        option.selected = isSelected
        if (isSelected) {
          option.setAttribute('aria-selected', 'true')
        } else {
          option.setAttribute('aria-selected', 'false')
        }
      })
    }, 100)
    
    // 监听主菜单变化事件 - 使用多种方式确保捕获
    mainMenuEl.addEventListener('change', (event: Event) => {
      const target = event.target as any
      const selectedId = target.value
      console.log('Main menu change event:', selectedId, event)
      if (selectedId && selectedId !== currentMainMenu) {
        selectMainMenu(selectedId)
      }
    })
    
    // 也监听点击事件（直接点击option）
    mainMenuEl.addEventListener('click', (event: MouseEvent) => {
      const target = event.target as HTMLElement
      const option = target.closest('fluent-option') as any
      if (option && option.value) {
        const selectedId = option.value
        console.log('Main menu click event:', selectedId)
        if (selectedId !== currentMainMenu) {
          mainMenuEl.value = selectedId
          selectMainMenu(selectedId)
        }
      }
    })
    
    // 使用MutationObserver监听value属性变化
    const mainMenuObserver = new MutationObserver(() => {
      const currentValue = mainMenuEl.value
      if (currentValue && currentValue !== currentMainMenu) {
        console.log('Main menu value changed via observer:', currentValue)
        selectMainMenu(currentValue)
      }
    })
    mainMenuObserver.observe(mainMenuEl, {
      attributes: true,
      attributeFilter: ['value'],
      childList: true,
      subtree: true
    })
  }
  
  // 初始化二级菜单
  updateSubMenu()
  
  if (subMenuEl) {
    subMenuEl.value = currentSubMenu
    
    // 确保初始选中项已设置 - 使用 setTimeout 确保 Fluent UI 组件完全初始化
    setTimeout(() => {
      const subMenuOptions = subMenuEl.querySelectorAll('fluent-option') as NodeListOf<any>
      subMenuOptions.forEach((option: any) => {
        const isSelected = option.value === currentSubMenu
        option.selected = isSelected
        if (isSelected) {
          option.setAttribute('aria-selected', 'true')
        } else {
          option.setAttribute('aria-selected', 'false')
        }
      })
    }, 100)
    
    // 监听二级菜单变化事件 - 使用多种方式确保捕获
    subMenuEl.addEventListener('change', (event: Event) => {
      const target = event.target as any
      const selectedValue = target.value
      console.log('Sub menu change event:', selectedValue, event)
      if (selectedValue && selectedValue !== currentSubMenu) {
        selectSubMenu(selectedValue)
      }
    })
    
    // 也监听点击事件（直接点击option）
    subMenuEl.addEventListener('click', (event: MouseEvent) => {
      const target = event.target as HTMLElement
      const option = target.closest('fluent-option') as any
      if (option && option.value) {
        const selectedValue = option.value
        console.log('Sub menu click event:', selectedValue)
        if (selectedValue !== currentSubMenu) {
          subMenuEl.value = selectedValue
          selectSubMenu(selectedValue)
        }
      }
    })
    
    // 使用MutationObserver监听value属性变化
    const subMenuObserver = new MutationObserver(() => {
      const currentValue = subMenuEl.value
      if (currentValue && currentValue !== currentSubMenu) {
        console.log('Sub menu value changed via observer:', currentValue)
        selectSubMenu(currentValue)
      }
    })
    subMenuObserver.observe(subMenuEl, {
      attributes: true,
      attributeFilter: ['value'],
      childList: true,
      subtree: true
    })
  }
  
  // 初始化工作区显示
  updateWorkspaceTitle()
  
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
  const settingsBtn = document.getElementById('settings-button')
  if (settingsBtn) {
    settingsBtn.addEventListener('click', openSettings)
  }
  
  // 侧边栏调整
  if (sidebarResizerEl) {
    sidebarResizerEl.addEventListener('mousedown', startResize)
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
  
  console.log('应用初始化完成')
}

// 等待DOM加载完成
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init)
} else {
  init()
}

