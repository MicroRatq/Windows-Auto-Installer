<template>
  <div class="app-container">
    <div class="top-bar">
      <div class="top-bar-left">
        <div class="main-menu">
          <button 
            v-for="item in mainMenuItems" 
            :key="item.id"
            :class="['menu-item', { active: currentMainMenu === item.id }]"
            @click="selectMainMenu(item.id)"
          >
            {{ item.label }}
          </button>
        </div>
        <div class="search-bar">
          <input type="text" placeholder="搜索..." />
        </div>
      </div>
      <div class="top-bar-right">
        <button class="theme-toggle" @click="toggleTheme">🌓</button>
        <button class="window-control" @click="minimizeWindow">−</button>
        <button class="window-control" @click="maximizeWindow">□</button>
        <button class="window-control close" @click="closeWindow">×</button>
      </div>
    </div>
    
    <div class="content-area">
      <div class="sidebar" :style="{ width: sidebarWidth + 'px' }">
        <div class="sidebar-resizer" @mousedown="startResize"></div>
        <div class="sidebar-content">
          <div 
            v-for="item in currentSubMenuItems" 
            :key="item.id"
            :class="['sub-menu-item', { active: currentSubMenu === item.id }]"
            @click="selectSubMenu(item.id)"
          >
            {{ item.label }}
          </div>
          <div class="sidebar-footer">
            <div class="sub-menu-item" @click="openSettings">⚙️ 设置</div>
          </div>
        </div>
      </div>
      
      <div class="workspace">
        <div class="workspace-content">
          <h2>{{ currentSubMenuLabel }}</h2>
          <p>工作区内容将在这里显示</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

// 主题
const isDark = ref(true)

// 主菜单
const mainMenuItems = [
  { id: 'iso', label: '镜像' },
  { id: 'system', label: '系统配置' },
  { id: 'software', label: '软件安装' }
]

const currentMainMenu = ref('iso')

// 子菜单配置
const subMenuConfig = {
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

const currentSubMenu = ref('iso-cache')

const currentSubMenuItems = computed(() => {
  return subMenuConfig[currentMainMenu.value] || []
})

const currentSubMenuLabel = computed(() => {
  const item = currentSubMenuItems.value.find(item => item.id === currentSubMenu.value)
  return item ? item.label : '未知'
})

// 侧边栏宽度
const sidebarWidth = ref(200)
const isResizing = ref(false)

function selectMainMenu(id) {
  currentMainMenu.value = id
  // 切换到该主菜单的第一个子菜单
  if (subMenuConfig[id] && subMenuConfig[id].length > 0) {
    currentSubMenu.value = subMenuConfig[id][0].id
  }
}

function selectSubMenu(id) {
  currentSubMenu.value = id
}

function openSettings() {
  console.log('打开设置')
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
  isDark.value = !isDark.value
  document.body.style.backgroundColor = isDark.value ? 'rgb(24, 24, 24)' : 'rgb(243, 243, 243)'
  document.body.style.color = isDark.value ? 'rgb(243, 243, 243)' : 'rgb(24, 24, 24)'
}

// 侧边栏调整宽度
function startResize(e) {
  isResizing.value = true
  const startX = e.clientX
  const startWidth = sidebarWidth.value
  
  function onMouseMove(e) {
    const newWidth = startWidth + (e.clientX - startX)
    if (newWidth >= 150 && newWidth <= 400) {
      sidebarWidth.value = newWidth
    }
  }
  
  function onMouseUp() {
    isResizing.value = false
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }
  
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

// 测试后端连接
onMounted(async () => {
  if (window.electronAPI) {
    try {
      const response = await window.electronAPI.sendToBackend({
        jsonrpc: '2.0',
        id: 1,
        method: 'ping',
        params: {}
      })
      console.log('后端连接成功:', response)
    } catch (error) {
      console.error('后端连接失败:', error)
    }
  }
})
</script>

<style scoped>
.app-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: rgb(24, 24, 24);
  color: rgb(243, 243, 243);
}

.top-bar {
  height: 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 10px;
  background-color: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  -webkit-app-region: drag;
}

.top-bar-left {
  display: flex;
  align-items: center;
  gap: 20px;
  -webkit-app-region: no-drag;
}

.main-menu {
  display: flex;
  gap: 5px;
}

.menu-item {
  padding: 5px 15px;
  background: transparent;
  border: none;
  color: rgb(243, 243, 243);
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.menu-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.menu-item.active {
  background-color: rgba(255, 255, 255, 0.2);
}

.search-bar input {
  padding: 5px 10px;
  background-color: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  color: rgb(243, 243, 243);
  width: 200px;
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: 5px;
  -webkit-app-region: no-drag;
}

.theme-toggle,
.window-control {
  width: 30px;
  height: 30px;
  background: transparent;
  border: none;
  color: rgb(243, 243, 243);
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.theme-toggle:hover,
.window-control:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.window-control.close:hover {
  background-color: rgba(255, 0, 0, 0.5);
}

.content-area {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.sidebar {
  position: relative;
  background-color: rgba(0, 0, 0, 0.2);
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  min-width: 150px;
  max-width: 400px;
}

.sidebar-resizer {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  cursor: col-resize;
  background-color: transparent;
  transition: background-color 0.2s;
}

.sidebar-resizer:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.sidebar-content {
  padding: 10px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sub-menu-item {
  padding: 10px 15px;
  cursor: pointer;
  border-radius: 4px;
  margin-bottom: 5px;
  transition: background-color 0.2s;
}

.sub-menu-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.sub-menu-item.active {
  background-color: rgba(255, 255, 255, 0.2);
}

.sidebar-footer {
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.workspace {
  flex: 1;
  overflow: auto;
  background-color: rgb(24, 24, 24);
}

.workspace-content {
  padding: 20px;
}

.workspace-content h2 {
  margin-bottom: 10px;
}

.workspace-content p {
  color: rgba(243, 243, 243, 0.7);
}
</style>

