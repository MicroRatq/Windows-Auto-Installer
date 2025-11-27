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
  icon: string // Lucide图标名称
}

const mainMenuItems: MenuItem[] = [
  { id: 'iso', label: '镜像', icon: 'disc' },
  { id: 'system', label: '系统配置', icon: 'settings' },
  { id: 'software', label: '软件安装', icon: 'package' }
]

const subMenuConfig: Record<string, MenuItem[]> = {
  iso: [
    { id: 'iso-cache', label: '镜像缓存', icon: 'download' },
    { id: 'iso-config', label: '镜像配置', icon: 'file-edit' },
    { id: 'iso-burn', label: '镜像烧录', icon: 'disc-2' }
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
    // 展开状态：图标 + 文字
    const textNode = document.createTextNode(item.label)
    wrapper.appendChild(textNode)
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

// 选择子菜单
function selectSubMenu(id: string) {
  console.log('Selecting sub menu:', id)
  currentSubMenu = id

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

// 切换侧边栏折叠状态
function toggleCollapse() {
  isCollapsed = !isCollapsed

  if (!sidebarEl || !sidebarMenuGroups || !iconMenuEl || !collapseIcon) return

  if (isCollapsed) {
    // 折叠：先添加折叠类让文本立即消失，然后更新图标菜单
    sidebarEl.classList.add('collapsed') // 添加折叠类，文本立即消失
    sidebarEl.style.width = '70px' // 折叠后的宽度，确保图标完整显示

    // 使用requestAnimationFrame确保文本消失后再更新图标菜单
    requestAnimationFrame(() => {
      updateIconMenu()

      // 确保图标菜单可见
      if (iconMenuEl) {
        iconMenuEl.style.display = 'block'
      }

      // 延迟确保激活状态，等待updateIconMenu中的setTimeout完成
      setTimeout(() => {
        if (currentSubMenu && iconMenuEl) {
          iconMenuEl.value = currentSubMenu
          const options = iconMenuEl.querySelectorAll('fluent-option') as NodeListOf<any>
          options.forEach((option: any) => {
            const isSelected = option.value === currentSubMenu
            option.selected = isSelected
            option.setAttribute('aria-selected', isSelected ? 'true' : 'false')
          })
        }

        // 重新初始化Lucide图标
        if (window.lucide) {
          window.lucide.createIcons()
        }
      }, 10)
    })
  } else {
    // 展开：先移除折叠类，然后隐藏图标菜单
    sidebarEl.classList.remove('collapsed') // 移除折叠类，触发CSS过渡
    sidebarEl.style.width = sidebarWidth + 'px'

    // 使用requestAnimationFrame确保动画流畅
    requestAnimationFrame(() => {
      if (iconMenuEl) {
        iconMenuEl.style.display = 'none'
      }

      // 保持当前激活状态在对应的二级菜单中
      if (currentSubMenu && currentMainMenu) {
        const currentSubMenuEl = subMenuEls.get(currentMainMenu)
        if (currentSubMenuEl) {
          currentSubMenuEl.value = currentSubMenu
          const options = currentSubMenuEl.querySelectorAll('fluent-option') as NodeListOf<any>
          options.forEach((option: any) => {
            const isSelected = option.value === currentSubMenu
            option.selected = isSelected
            option.setAttribute('aria-selected', isSelected ? 'true' : 'false')
          })
        }
      }

      // 重新初始化Lucide图标
      if (window.lucide) {
        window.lucide.createIcons()
      }
    })
  }
}

// 初始化
function init() {
  // 获取DOM元素
  sidebarEl = document.getElementById('sidebar')
  sidebarResizerEl = document.getElementById('sidebar-resizer')
  workspaceTitleEl = document.getElementById('workspace-title')
  collapseToggleBtn = document.getElementById('collapse-toggle')
  collapseIcon = document.getElementById('collapse-icon')
  sidebarMenuGroups = document.getElementById('sidebar-menu-groups')
  iconMenuEl = document.getElementById('icon-menu')

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

