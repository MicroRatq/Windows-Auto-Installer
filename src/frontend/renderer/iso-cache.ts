/**
 * 镜像缓存工作区
 * 实现镜像下载、导入、列表管理等功能
 */

// 通知类型
type NotificationType = 'error' | 'success' | 'info' | 'warning'

// 通知项接口
interface NotificationItem {
    id: string
    type: NotificationType
    message: string
    details?: string
    timestamp: number
}

// 通知管理器
class NotificationManager {
    private notifications: NotificationItem[] = []
    private container: HTMLElement | null = null
    private isCollapsed: boolean = false
    private maxNotifications: number = 10

    constructor() {
        this.createContainer()
    }

    private createContainer() {
        // 创建通知栏容器
        this.container = document.createElement('div')
        this.container.id = 'notification-container'
        this.container.className = 'notification-container'
        document.body.appendChild(this.container)
        this.updateUI()
    }

    showNotification(type: NotificationType, message: string, details?: string) {
        const notification: NotificationItem = {
            id: `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            type,
            message,
            details,
            timestamp: Date.now()
        }

        this.notifications.unshift(notification) // 新通知添加到开头

        // 限制最大通知数量
        if (this.notifications.length > this.maxNotifications) {
            this.notifications = this.notifications.slice(0, this.maxNotifications)
        }

        this.updateUI()
    }

    removeNotification(id: string) {
        this.notifications = this.notifications.filter(n => n.id !== id)
        this.updateUI()
    }

    clearAll() {
        this.notifications = []
        this.updateUI()
    }

    toggleCollapse() {
        this.isCollapsed = !this.isCollapsed
        this.updateUI()
    }

    private updateUI() {
        if (!this.container) return

        this.container.innerHTML = ''

        if (this.notifications.length === 0) {
            this.container.style.display = 'none'
            return
        }

        this.container.style.display = 'block'

        // 创建通知卡片列表容器（包含卡片和底部操作栏）
        const cardsContainer = document.createElement('div')
        cardsContainer.className = 'notification-cards-container'
        if (this.isCollapsed) {
            cardsContainer.style.display = 'none'
        }

        // 显示所有通知卡片
        this.notifications.forEach(notification => {
            const card = this.createNotificationCard(notification)
            cardsContainer.appendChild(card)
        })

        // 创建底部操作栏（放在同一个容器内）
        const footer = document.createElement('div')
        footer.className = 'notification-footer'

        const title = document.createElement('span')
        title.className = 'notification-footer-title'
        title.textContent = '所有通知'
        footer.appendChild(title)

        const buttonsContainer = document.createElement('div')
        buttonsContainer.className = 'notification-footer-buttons'

        // 清除所有通知按钮
        const clearAllBtn = document.createElement('button')
        clearAllBtn.className = 'notification-footer-btn'
        clearAllBtn.id = 'notification-clear-all'
        clearAllBtn.setAttribute('type', 'button')
        const clearIcon = document.createElement('i')
        clearIcon.setAttribute('data-lucide', 'trash-2')
        const clearText = document.createTextNode('清除所有通知')
        clearAllBtn.appendChild(clearIcon)
        clearAllBtn.appendChild(clearText)
        clearAllBtn.addEventListener('click', () => this.clearAll())
        buttonsContainer.appendChild(clearAllBtn)

        // 收起/展开按钮
        const collapseBtn = document.createElement('button')
        collapseBtn.className = 'notification-footer-btn'
        collapseBtn.id = 'notification-collapse'
        collapseBtn.setAttribute('type', 'button')
        const collapseIcon = document.createElement('i')
        collapseIcon.setAttribute('data-lucide', this.isCollapsed ? 'chevron-down' : 'chevron-up')
        const collapseText = document.createTextNode(this.isCollapsed ? '展开' : '收起')
        collapseBtn.appendChild(collapseIcon)
        collapseBtn.appendChild(collapseText)
        collapseBtn.addEventListener('click', () => this.toggleCollapse())
        buttonsContainer.appendChild(collapseBtn)

        footer.appendChild(buttonsContainer)

        // 将底部操作栏添加到同一个容器内
        cardsContainer.appendChild(footer)

        // 将整个容器添加到通知栏
        this.container.appendChild(cardsContainer)

        // 确保图标在DOM插入后初始化
        if (window.lucide) {
            window.lucide.createIcons()
        }
    }

    private createNotificationCard(notification: NotificationItem): HTMLElement {
        const card = document.createElement('div')
        card.className = `notification-card ${notification.type}`
        card.dataset.notificationId = notification.id

        // 左侧图标
        const icon = document.createElement('div')
        icon.className = 'notification-icon'
        const iconName = notification.type === 'error' ? 'x-circle' :
            notification.type === 'success' ? 'check-circle' :
                notification.type === 'warning' ? 'alert-triangle' : 'info'
        const iconElement = document.createElement('i')
        iconElement.setAttribute('data-lucide', iconName)
        icon.appendChild(iconElement)

        // 内容区域
        const content = document.createElement('div')
        content.className = 'notification-content'

        const message = document.createElement('div')
        message.className = 'notification-message'
        message.textContent = notification.message

        content.appendChild(message)

        if (notification.details) {
            const details = document.createElement('div')
            details.className = 'notification-details'
            details.textContent = notification.details
            content.appendChild(details)
        }

        // 右侧关闭按钮
        const closeBtn = document.createElement('button')
        closeBtn.className = 'notification-close'
        closeBtn.setAttribute('type', 'button')
        closeBtn.setAttribute('aria-label', '关闭')
        const closeIcon = document.createElement('i')
        closeIcon.setAttribute('data-lucide', 'x')
        closeBtn.appendChild(closeIcon)
        closeBtn.addEventListener('click', () => this.removeNotification(notification.id))

        card.appendChild(icon)
        card.appendChild(content)
        card.appendChild(closeBtn)

        // 初始化图标 - 使用setTimeout确保DOM已插入
        setTimeout(() => {
            if (window.lucide) {
                window.lucide.createIcons()
            }
        }, 0)

        return card
    }
}

// 后端API调用封装
class IsoCacheAPI {
    private requestId = 0

    private async callBackend(method: string, params: any = {}): Promise<any> {
        if (!window.electronAPI) {
            throw new Error('Electron API 不可用')
        }

        const id = ++this.requestId
        const request = {
            jsonrpc: '2.0',
            id,
            method,
            params
        }

        try {
            console.log(`[API] 调用后端方法: ${method}`, params)
            const response = await window.electronAPI.sendToBackend(request)
            console.log(`[API] 后端响应 (${method}):`, response)
            if (response.error) {
                throw new Error(response.error.message || '后端错误')
            }
            // 确保返回结果存在
            if (response.result === undefined || response.result === null) {
                console.warn(`后端方法 ${method} 返回了空结果:`, response)
                return null
            }
            console.log(`[API] 后端方法 ${method} 返回结果:`, response.result)
            return response.result
        } catch (error: any) {
            console.error(`后端调用失败 (${method}):`, error)
            throw error
        }
    }

    async listSources(): Promise<string[]> {
        return this.callBackend('iso_list_sources')
    }

    async testMirror(source: string, url?: string): Promise<{ speed?: number; latency?: number }> {
        try {
            // 使用异步任务接口，避免长耗时阻塞后端IPC
            const startResp = await this.callBackend('iso_test_mirror_start', { source, url })
            const taskId = startResp?.task_id
            if (!taskId) {
                throw new Error('iso_test_mirror_start did not return task_id')
            }

            const startTime = Date.now()
            const timeoutMs = 5 * 60 * 1000
            let result: any = null

            while (true) {
                const statusResp = await this.callBackend('iso_test_mirror_status', { task_id: taskId })
                const status = statusResp?.status

                if (status === 'completed') {
                    result = statusResp.result
                    break
                }
                if (status === 'failed') {
                    throw new Error(statusResp.error || 'iso_test_mirror task failed')
                }
                if (status === 'not_found') {
                    throw new Error('iso_test_mirror task not found')
                }

                if (Date.now() - startTime > timeoutMs) {
                    throw new Error('iso_test_mirror task timeout')
                }

                await new Promise(resolve => setTimeout(resolve, 500))
            }
            // 转换字段名：download_speed -> speed
            console.log('testMirror 原始结果:', result)
            console.log('testMirror 原始结果类型:', typeof result)
            console.log('testMirror download_speed:', result?.download_speed, '类型:', typeof result?.download_speed)
            console.log('testMirror latency:', result?.latency, '类型:', typeof result?.latency)

            if (!result || typeof result !== 'object') {
                console.warn('testMirror 返回了无效结果:', result)
                return { speed: undefined, latency: undefined }
            }

            // 处理 download_speed：如果是 -1 或无效值则转为 undefined，否则保留原值
            let speed: number | undefined = undefined
            if (result.download_speed !== undefined && result.download_speed !== null) {
                const speedValue = typeof result.download_speed === 'number'
                    ? result.download_speed
                    : parseFloat(String(result.download_speed))
                console.log('speedValue 计算:', speedValue, 'isNaN:', isNaN(speedValue), '> 0:', speedValue > 0)
                if (!isNaN(speedValue) && speedValue > 0 && speedValue !== -1) {
                    speed = speedValue
                }
            }

            // 处理 latency：如果是 -1 或无效值则转为 undefined，否则保留原值
            let latency: number | undefined = undefined
            if (result.latency !== undefined && result.latency !== null) {
                const latencyValue = typeof result.latency === 'number'
                    ? result.latency
                    : parseFloat(String(result.latency))
                console.log('latencyValue 计算:', latencyValue, 'isNaN:', isNaN(latencyValue), '> 0:', latencyValue > 0)
                if (!isNaN(latencyValue) && latencyValue > 0 && latencyValue !== -1) {
                    latency = latencyValue
                }
            }

            console.log('testMirror 处理后结果:', { speed, latency })
            return { speed, latency }
        } catch (error) {
            console.error('testMirror 调用失败:', error)
            return { speed: undefined, latency: undefined }
        }
    }

    async startTestMirror(source: string, url?: string): Promise<{ task_id: string }> {
        return this.callBackend('iso_start_test_mirror', { source, url })
    }

    async getTestStatus(taskId: string): Promise<{ status: string; elapsed: number; result?: any; error?: string }> {
        return this.callBackend('iso_get_test_status', { task_id: taskId })
    }

    async cancelTest(taskId: string): Promise<{ success: boolean }> {
        return this.callBackend('iso_cancel_test', { task_id: taskId })
    }

    async listVersions(osType?: string): Promise<{ [os: string]: string[] }> {
        return this.callBackend('iso_list_versions', { os_type: osType })
    }

    async listImages(source: string, filters: any = {}): Promise<any[]> {
        // 只支持local源（用于加载本地镜像列表）
        if (source !== 'local') {
            throw new Error('listImages only supports "local" source. Use fetchDownloadUrlStart for remote sources.')
        }
        // 使用异步任务接口，避免长耗时阻塞后端IPC
        const startResp = await this.callBackend('iso_list_images_start', { source, filter: filters })
        const taskId = startResp?.task_id
        if (!taskId) {
            throw new Error('iso_list_images_start did not return task_id')
        }

        // 轮询任务状态，直到完成或失败
        const startTime = Date.now()
        const timeoutMs = 5 * 60 * 1000 // 5分钟上限，防止意外卡死

        while (true) {
            const statusResp = await this.callBackend('iso_list_images_status', { task_id: taskId })
            const status = statusResp?.status

            if (status === 'completed') {
                return (statusResp.result as any[]) || []
            }
            if (status === 'failed') {
                throw new Error(statusResp.error || 'iso_list_images task failed')
            }
            if (status === 'not_found') {
                throw new Error('iso_list_images task not found')
            }

            if (Date.now() - startTime > timeoutMs) {
                throw new Error('iso_list_images task timeout')
            }

            await new Promise(resolve => setTimeout(resolve, 500))
        }
    }

    async fetchDownloadUrlStart(source: string, config: { os: string; version: string; language: string; arch: string }): Promise<{ task_id: string }> {
        return this.callBackend('iso_fetch_download_url_start', {
            source,
            os: config.os,
            version: config.version,
            language: config.language,
            arch: config.arch
        })
    }

    async fetchDownloadUrlStatus(taskId: string): Promise<{ status: string; result?: any; error?: string }> {
        return this.callBackend('iso_fetch_download_url_status', { task_id: taskId })
    }

    async downloadImage(url?: string, urlType?: string, outputPath?: string, source?: string, config?: { os: string; version: string; language: string; arch: string }): Promise<{ task_id: string; status: string }> {
        if (source && config && outputPath) {
            // 使用配置参数创建下载任务
            return this.callBackend('iso_download', {
                source,
                config,
                output_path: outputPath
            })
        } else if (url && outputPath) {
            // 使用直接URL创建下载任务（兼容旧代码）
            return this.callBackend('iso_download', {
                url,
                url_type: urlType || 'http',
                output_path: outputPath
            })
        } else {
            throw new Error('Must provide either (source+config+outputPath) or (url+outputPath)')
        }
    }

    async getDownloadProgress(taskId: string): Promise<any> {
        return this.callBackend('iso_download_progress', { task_id: taskId })
    }

    async importIso(filePath: string, overwrite: boolean = false): Promise<any> {
        // 使用异步任务接口导入ISO，便于展示状态
        const startResp = await this.callBackend('iso_import_start', { iso_path: filePath, overwrite })
        const taskId = startResp?.task_id
        if (!taskId) {
            throw new Error('iso_import_start did not return task_id')
        }

        const startTime = Date.now()
        const timeoutMs = 30 * 60 * 1000 // 导入可能很久，给足时间

        while (true) {
            const statusResp = await this.callBackend('iso_import_status', { task_id: taskId })
            const status = statusResp?.status

            if (status === 'completed') {
                return statusResp.result
            }
            if (status === 'failed') {
                throw new Error(statusResp.error || 'iso_import task failed')
            }
            if (status === 'not_found') {
                throw new Error('iso_import task not found')
            }

            if (Date.now() - startTime > timeoutMs) {
                throw new Error('iso_import task timeout')
            }

            await new Promise(resolve => setTimeout(resolve, 1000))
        }
    }

    async deleteIso(filePath: string): Promise<{ success: boolean }> {
        return this.callBackend('iso_delete', { file_path: filePath })
    }

    async verifyIso(filePath: string, checksum?: string): Promise<{ valid: boolean }> {
        return this.callBackend('iso_verify', { file_path: filePath, checksum })
    }

    async verifyIsoStart(filePath: string, checksum?: string): Promise<{ task_id: string }> {
        return this.callBackend('iso_verify_start', { file_path: filePath, checksum })
    }

    async verifyIsoStatus(taskId: string): Promise<any> {
        return this.callBackend('iso_verify_status', { task_id: taskId })
    }


    async identifyIso(filePath: string): Promise<any> {
        // 使用异步任务接口识别ISO
        const startResp = await this.callBackend('iso_identify_start', { file_path: filePath })
        const taskId = startResp?.task_id
        if (!taskId) {
            throw new Error('iso_identify_start did not return task_id')
        }

        const startTime = Date.now()
        const timeoutMs = 30 * 60 * 1000

        while (true) {
            const statusResp = await this.callBackend('iso_identify_status', { task_id: taskId })
            const status = statusResp?.status

            if (status === 'completed') {
                return statusResp.result
            }
            if (status === 'failed') {
                throw new Error(statusResp.error || 'iso_identify task failed')
            }
            if (status === 'not_found') {
                throw new Error('iso_identify task not found')
            }

            if (Date.now() - startTime > timeoutMs) {
                throw new Error('iso_identify task timeout')
            }

            await new Promise(resolve => setTimeout(resolve, 1000))
        }
    }

    async cancelDownload(taskId: string): Promise<{ success: boolean }> {
        return this.callBackend('iso_cancel_download', { task_id: taskId })
    }
}

// 镜像缓存工作区状态
interface IsoCacheState {
    selectedSource: string
    selectedVersion: string
    selectedLanguage: string
    selectedArch: string
    imageList: any[]
    downloadTasks: Map<string, any>
    importProgress: { progress: number; status: string } | null
    mirrorTestResult: { speed?: number; latency?: number } | null
    testTaskId: string | null
    testStatusInterval: number | null
}

// 镜像缓存工作区类
class IsoCacheWorkspace {
    private api: IsoCacheAPI
    private state: IsoCacheState
    private container: HTMLElement | null = null
    private progressInterval: number | null = null
    private notificationManager: NotificationManager

    constructor() {
        this.api = new IsoCacheAPI()
        this.notificationManager = new NotificationManager()
        this.state = {
            selectedSource: 'microsoft',
            selectedVersion: '',
            selectedLanguage: 'zh-cn',
            selectedArch: 'x64',
            imageList: [],
            downloadTasks: new Map(),
            importProgress: null,
            mirrorTestResult: null,
            testTaskId: null,
            testStatusInterval: null
        }
    }

    // 初始化工作区
    async init() {
        this.container = document.getElementById('workspace-iso-cache')
        if (!this.container) {
            console.error('未找到镜像缓存工作区容器')
            return
        }

        // 清空容器
        this.container.innerHTML = ''

        // 渲染UI
        this.render()

        // 加载初始数据
        await this.loadInitialData()

        // 开始轮询下载进度
        this.startProgressPolling()
    }

    // 渲染UI
    private render() {
        if (!this.container) return

        // 下载源选择 Card
        this.renderSourceCard()

        // 镜像下载配置 Card
        this.renderDownloadCard()

        // 本地导入 Card
        this.renderImportCard()

        // 镜像列表区域
        this.renderImageList()
    }

    // 渲染下载源选择 Card
    private renderSourceCard() {
        if (!this.container) return

        const card = document.createElement('div')
        card.className = 'card'

        const left = document.createElement('div')
        left.className = 'card-left'
        left.innerHTML = `
      <i data-lucide="server" class="card-icon small"></i>
      <div class="card-content">
        <div class="card-title compact">下载源</div>
        <div class="card-description compact">选择镜像下载源并测试连接速度</div>
      </div>
    `

        const right = document.createElement('div')
        right.className = 'card-right'
        right.innerHTML = `
      <fluent-select id="source-select" style="width: 150px; margin-right: 10px;">
        <fluent-option value="microsoft">Microsoft 官方</fluent-option>
        <fluent-option value="msdn">MSDN 镜像站</fluent-option>
      </fluent-select>
      <fluent-button id="test-mirror-btn" appearance="neutral">测试速度</fluent-button>
      <div id="mirror-test-result" class="status-badge" style="margin-left: 10px; display: none;"></div>
    `

        card.appendChild(left)
        card.appendChild(right)
        this.container.appendChild(card)

        // 初始化图标
        if (window.lucide) {
            window.lucide.createIcons()
        }

        // 绑定事件
        const sourceSelect = document.getElementById('source-select') as any
        const testBtn = document.getElementById('test-mirror-btn') as any

        if (sourceSelect) {
            sourceSelect.value = this.state.selectedSource
            sourceSelect.addEventListener('change', (e: any) => {
                this.state.selectedSource = e.target.value
                this.loadImageList()
            })
        }

        if (testBtn) {
            testBtn.addEventListener('click', () => this.testMirror())
        }
    }

    // 渲染镜像下载配置 Card
    private renderDownloadCard() {
        if (!this.container) return

        const card = document.createElement('div')
        card.className = 'card'

        const left = document.createElement('div')
        left.className = 'card-left'
        left.innerHTML = `
      <i data-lucide="download" class="card-icon small"></i>
      <div class="card-content">
        <div class="card-title compact">下载配置</div>
        <div class="card-description compact">选择Windows版本、语言和架构</div>
      </div>
    `

        const right = document.createElement('div')
        right.className = 'card-right'
        right.innerHTML = `
      <fluent-select id="version-select" style="width: 120px; margin-right: 10px;">
        <fluent-option value="">选择版本</fluent-option>
      </fluent-select>
      <fluent-select id="language-select" style="width: 120px; margin-right: 10px;">
        <fluent-option value="zh-cn">简体中文</fluent-option>
        <fluent-option value="zh-tw">繁体中文</fluent-option>
        <fluent-option value="en-us">English</fluent-option>
      </fluent-select>
      <fluent-select id="arch-select" style="width: 100px; margin-right: 10px;">
        <fluent-option value="x64">x64</fluent-option>
        <fluent-option value="arm64">ARM64</fluent-option>
      </fluent-select>
      <fluent-button id="download-btn" appearance="accent">下载</fluent-button>
    `

        card.appendChild(left)
        card.appendChild(right)
        this.container.appendChild(card)

        // 初始化图标
        if (window.lucide) {
            window.lucide.createIcons()
        }

        // 设置默认值
        const languageSelect = document.getElementById('language-select') as any
        const archSelect = document.getElementById('arch-select') as any
        if (languageSelect) languageSelect.value = this.state.selectedLanguage
        if (archSelect) archSelect.value = this.state.selectedArch

        // 绑定事件
        const versionSelect = document.getElementById('version-select') as any
        const downloadBtn = document.getElementById('download-btn') as any

        if (versionSelect) {
            versionSelect.addEventListener('change', (e: any) => {
                this.state.selectedVersion = e.target.value
            })
        }

        if (languageSelect) {
            languageSelect.addEventListener('change', (e: any) => {
                this.state.selectedLanguage = e.target.value
            })
        }

        if (archSelect) {
            archSelect.addEventListener('change', (e: any) => {
                this.state.selectedArch = e.target.value
            })
        }

        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => this.startDownload())
        }
    }

    // 渲染本地导入 Card
    private renderImportCard() {
        if (!this.container) return

        const card = document.createElement('div')
        card.className = 'card card-clickable'

        const left = document.createElement('div')
        left.className = 'card-left'
        left.innerHTML = `
      <i data-lucide="folder-up" class="card-icon small"></i>
      <div class="card-content">
        <div class="card-title compact">本地导入</div>
        <div class="card-description compact">从本地目录导入ISO文件</div>
      </div>
    `

        const right = document.createElement('div')
        right.className = 'card-right'
        right.innerHTML = `
      <input type="file" id="import-file-input" accept=".iso" style="display: none;">
      <div id="import-progress-container" style="display: none; margin-right: 10px; width: 200px;">
        <fluent-progress id="import-progress" value="0" max="100"></fluent-progress>
        <div id="import-status" style="font-size: 12px; margin-top: 5px; color: var(--text-secondary);"></div>
      </div>
      <div class="card-indicator">
        <i data-lucide="chevron-right"></i>
      </div>
    `

        card.appendChild(left)
        card.appendChild(right)
        this.container.appendChild(card)

        // 初始化图标
        if (window.lucide) {
            window.lucide.createIcons()
        }

        // 绑定事件到card
        card.addEventListener('click', async () => {
            if (window.electronAPI?.showOpenDialog) {
                try {
                    const result = await window.electronAPI.showOpenDialog({
                        title: '选择ISO文件',
                        filters: [
                            { name: 'ISO文件', extensions: ['iso'] },
                            { name: '所有文件', extensions: ['*'] }
                        ],
                        properties: ['openFile']
                    })

                    if (!result.canceled && result.filePaths && result.filePaths.length > 0) {
                        this.importIso(result.filePaths[0])
                    }
                } catch (error: any) {
                    console.error('打开文件对话框失败:', error)
                    this.notificationManager.showNotification('error', '打开文件对话框失败', error.message)
                }
            } else {
                // 回退到HTML文件输入
                const fileInput = document.getElementById('import-file-input') as HTMLInputElement
                if (fileInput) {
                    fileInput.click()
                    fileInput.addEventListener('change', (e: any) => {
                        const file = e.target.files?.[0]
                        if (file) {
                            this.importIso(file.name)
                        }
                    }, { once: true })
                }
            }
        })
    }

    // 渲染镜像列表
    private renderImageList() {
        if (!this.container) return

        // 下载中任务区域
        const downloadingSection = document.createElement('div')
        downloadingSection.className = 'iso-cache-section'
        downloadingSection.innerHTML = '<h3 class="section-title">下载任务</h3>'

        const downloadingContainer = document.createElement('div')
        downloadingContainer.id = 'downloading-tasks-container'
        downloadingContainer.className = 'card-list-container with-divider'
        downloadingContainer.innerHTML = '<div class="empty-state compact">暂无下载任务</div>'

        downloadingSection.appendChild(downloadingContainer)
        this.container.appendChild(downloadingSection)

        const section = document.createElement('div')
        section.className = 'iso-cache-section'
        section.innerHTML = '<h3 class="section-title">本地镜像</h3>'

        const listContainer = document.createElement('div')
        listContainer.id = 'image-list-container'
        listContainer.className = 'card-list-container'

        section.appendChild(listContainer)
        this.container.appendChild(section)

        // 初始化下载任务显示
        this.updateDownloadingTasks()
    }

    // 更新镜像列表显示
    private updateImageList() {
        // 先更新下载中任务
        this.updateDownloadingTasks()

        // 再更新已缓存镜像列表
        const container = document.getElementById('image-list-container')
        if (!container) {
            console.warn('[updateImageList] 未找到镜像列表容器')
            return
        }

        container.innerHTML = ''

        console.log('[updateImageList] 当前镜像列表数量:', this.state.imageList.length)
        console.log('[updateImageList] 镜像列表内容:', this.state.imageList)

        if (this.state.imageList.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无镜像文件</div>'
            return
        }

        this.state.imageList.forEach((image, index) => {
            console.log(`[updateImageList] 创建镜像Card ${index + 1}:`, image.name)
            const card = this.createImageCard(image)
            container.appendChild(card)
        })

        // 初始化图标
        if (window.lucide) {
            window.lucide.createIcons()
        }
    }

    // 更新下载中任务显示
    private updateDownloadingTasks() {
        const container = document.getElementById('downloading-tasks-container')
        if (!container) return

        container.innerHTML = ''

        if (this.state.downloadTasks.size === 0) {
            container.innerHTML = '<div class="empty-state compact">暂无下载任务</div>'
            return
        }

        // 为每个下载任务创建Card
        for (const [taskId, task] of this.state.downloadTasks.entries()) {
            const card = this.createDownloadingCard(taskId, task)
            card.setAttribute('data-task-id', taskId) // 添加data属性以便后续查找
            container.appendChild(card)
        }

        // 初始化图标
        if (window.lucide) {
            window.lucide.createIcons()
        }
    }

    // 创建下载中任务Card
    private createDownloadingCard(taskId: string, task: any): HTMLElement {
        const card = document.createElement('div')
        card.className = 'card card-transparent'

        const left = document.createElement('div')
        left.className = 'card-left'

        // 下载图标
        const icon = document.createElement('i')
        icon.setAttribute('data-lucide', task.isFailed ? 'alert-circle' : 'download')
        icon.className = 'card-icon'

        // 信息区域
        const info = document.createElement('div')
        info.className = 'card-content'

        const fileName = document.createElement('div')
        fileName.className = 'card-title'
        // 根据配置参数生成文件名，或使用outputPath
        let displayName = '正在下载...'
        if (task.image?.name) {
            displayName = task.image.name
        } else if (task.config) {
            // 根据配置生成显示名称
            const { os, version, language, arch } = task.config
            displayName = `${os} ${version} ${language} ${arch}`
        } else if (task.outputPath) {
            displayName = task.outputPath.split('/').pop() || '正在下载...'
        }
        fileName.textContent = displayName

        // 状态显示区域
        const statusContainer = document.createElement('div')
        statusContainer.id = `status-${taskId}`

        // 检查是否是失败状态
        if (task.isFailed || task.status === 'failed') {
            // 显示错误状态
            const errorStatus = document.createElement('div')
            errorStatus.className = 'status-error'
            errorStatus.style.color = 'var(--error-color, #d32f2f)'
            errorStatus.style.fontSize = '12px'
            errorStatus.textContent = task.error || '下载失败'
            statusContainer.appendChild(errorStatus)
        } else {
            // 进度条（默认隐藏，仅在downloading状态显示）
            const progress = document.createElement('div')
            progress.className = 'progress-container'
            progress.id = `progress-container-${taskId}`
            progress.style.display = 'none'
            const progressBar = document.createElement('fluent-progress')
            progressBar.id = `progress-${taskId}`
            progressBar.setAttribute('value', '0')
            progressBar.setAttribute('max', '100')
            const progressText = document.createElement('div')
            progressText.id = `progress-text-${taskId}`
            progressText.className = 'progress-text'
            progressText.textContent = '准备中...'
            progress.appendChild(progressBar)
            progress.appendChild(progressText)

            // URL获取中状态（默认显示）
            const fetchingStatus = document.createElement('div')
            fetchingStatus.className = 'status-loading'
            fetchingStatus.id = `fetching-status-${taskId}`
            fetchingStatus.innerHTML = '<i data-lucide="loader"></i> URL获取中'

            statusContainer.appendChild(fetchingStatus)
            statusContainer.appendChild(progress)
        }

        info.appendChild(fileName)
        info.appendChild(statusContainer)

        left.appendChild(icon)
        left.appendChild(info)

        // 右侧按钮
        const right = document.createElement('div')
        right.className = 'card-right'

        if (task.isFailed || task.status === 'failed') {
            // 失败状态：显示删除按钮
            const deleteBtn = document.createElement('fluent-button')
            deleteBtn.setAttribute('appearance', 'neutral')
            deleteBtn.textContent = '删除'
            deleteBtn.addEventListener('click', () => {
                this.state.downloadTasks.delete(taskId)
                this.updateDownloadingTasks()
            })
            right.appendChild(deleteBtn)
        } else {
            // 正常状态：显示取消按钮
            const cancelBtn = document.createElement('fluent-button')
            cancelBtn.setAttribute('appearance', 'neutral')
            cancelBtn.textContent = '取消'
            cancelBtn.addEventListener('click', () => this.cancelDownload(taskId))
            right.appendChild(cancelBtn)
        }

        card.appendChild(left)
        card.appendChild(right)

        // 初始化图标
        if (window.lucide) {
            window.lucide.createIcons()
        }

        return card
    }

    // 创建镜像 Card
    private createImageCard(image: any): HTMLElement {
        const card = document.createElement('div')
        card.className = 'card'

        const left = document.createElement('div')
        left.className = 'card-left'

        // 图标
        const icon = document.createElement('i')
        icon.setAttribute('data-lucide', 'disc')
        icon.className = 'card-icon'

        // 信息区域
        const info = document.createElement('div')
        info.className = 'card-content'

        const fileName = document.createElement('div')
        fileName.className = 'card-title'

        // 文件名文本
        const fileNameText = document.createTextNode(image.name || '未知文件')
        fileName.appendChild(fileNameText)

        // 仅对文件名格式不匹配的添加"需要识别"标识（在文件名末尾）
        if (image.needs_identification) {
            const identifyBadge = document.createElement('span')
            identifyBadge.className = 'badge warning'
            identifyBadge.innerHTML = ' <i data-lucide="alert-circle" class="badge-icon"></i> <span class="badge-text">需要识别</span>'
            identifyBadge.title = 'Click "自动识别" in menu to identify this ISO file'
            fileName.appendChild(identifyBadge)
        }

        const meta = document.createElement('div')
        meta.className = 'card-description'

        // 检查状态标记
        if (image.verifying) {
            // 校验中状态
            const verifyingStatus = document.createElement('div')
            verifyingStatus.className = 'status-loading'
            verifyingStatus.innerHTML = '<i data-lucide="loader"></i> 校验中'
            meta.appendChild(verifyingStatus)
        } else if (image.redownloading) {
            // 重新下载中状态
            const redownloadStatus = document.createElement('div')
            redownloadStatus.className = 'status-loading'
            redownloadStatus.innerHTML = '<i data-lucide="loader"></i> 重新下载中'
            meta.appendChild(redownloadStatus)
        } else {
            // 正常显示元数据
            const metaItems: string[] = []
            if (image.os_type) metaItems.push(`OS: ${image.os_type}`)
            if (image.version) metaItems.push(`版本: ${image.version}`)
            if (image.build) metaItems.push(`构建: ${image.build}`)
            if (image.language) metaItems.push(`语言: ${image.language}`)
            if (image.architecture) metaItems.push(`架构: ${image.architecture}`)
            if (image.size) {
                const sizeGB = (image.size / (1024 ** 3)).toFixed(2)
                metaItems.push(`大小: ${sizeGB} GB`)
            }
            meta.textContent = metaItems.join(' | ')
        }

        info.appendChild(fileName)
        info.appendChild(meta)

        // 下载进度（如果正在下载且不是重新下载）
        // 重新下载时，进度条只在下载任务区域显示，不在镜像列表card中显示
        if (!image.redownloading) {
            const taskId = this.findTaskIdByPath(image.url)
            if (taskId) {
                const task = this.state.downloadTasks.get(taskId)
                // 只有非重新下载任务才在镜像列表card中显示进度条
                if (task && !task.isRedownload) {
                    const progress = document.createElement('div')
                    progress.className = 'progress-container'
                    const progressBar = document.createElement('fluent-progress')
                    progressBar.id = `progress-${taskId}`
                    progressBar.setAttribute('value', '0')
                    progressBar.setAttribute('max', '100')
                    const progressText = document.createElement('div')
                    progressText.id = `progress-text-${taskId}`
                    progressText.className = 'progress-text'
                    progress.appendChild(progressBar)
                    progress.appendChild(progressText)
                    info.appendChild(progress)
                }
            }
        }

        left.appendChild(icon)
        left.appendChild(info)

        // 右侧操作菜单
        const right = document.createElement('div')
        right.className = 'card-right'

        const menuButton = document.createElement('fluent-button')
        menuButton.setAttribute('appearance', 'stealth')
        menuButton.innerHTML = '<i data-lucide="more-horizontal"></i>'
        menuButton.className = 'menu-trigger'

        const menu = document.createElement('fluent-menu')
        menu.style.display = 'none'

        const deleteItem = document.createElement('fluent-menu-item')
        deleteItem.textContent = '删除'
        deleteItem.addEventListener('click', () => {
            menu.style.display = 'none'
            this.handleDelete(image)
        })

        const verifyItem = document.createElement('fluent-menu-item')
        verifyItem.textContent = '校验'
        verifyItem.addEventListener('click', () => {
            menu.style.display = 'none'
            this.handleVerify(image)
        })

        const redownloadItem = document.createElement('fluent-menu-item')
        redownloadItem.textContent = '重新下载'
        redownloadItem.addEventListener('click', () => {
            menu.style.display = 'none'
            this.handleRedownload(image)
        })

        // 如果文件需要识别，添加自动识别菜单项（放在最前面）
        if (image.needs_identification) {
            const identifyItem = document.createElement('fluent-menu-item')
            identifyItem.textContent = '自动识别'
            identifyItem.addEventListener('click', () => {
                menu.style.display = 'none'
                this.handleIdentify(image)
            })
            menu.appendChild(identifyItem)
        }

        menu.appendChild(deleteItem)
        menu.appendChild(verifyItem)
        menu.appendChild(redownloadItem)

        menuButton.addEventListener('click', (e: Event) => {
            e.stopPropagation()
            // 关闭其他所有菜单
            document.querySelectorAll('fluent-menu').forEach((m) => {
                if (m !== menu) {
                    (m as HTMLElement).style.display = 'none'
                }
            })
            // 切换当前菜单
            const isVisible = menu.style.display === 'block'
            menu.style.display = isVisible ? 'none' : 'block'
        })

        // 点击外部关闭菜单
        const closeMenuHandler = (e: Event) => {
            if (!menu.contains(e.target as Node) && !menuButton.contains(e.target as Node)) {
                menu.style.display = 'none'
            }
        }
        document.addEventListener('click', closeMenuHandler)

        right.appendChild(menuButton)
        right.appendChild(menu)

        // 初始化图标
        if (window.lucide) {
            window.lucide.createIcons()
        }

        card.appendChild(left)
        card.appendChild(right)

        return card
    }

    // 加载初始数据
    private async loadInitialData() {
        try {
            await this.loadImageList()
            await this.loadVersions()
        } catch (error) {
            console.error('加载初始数据失败:', error)
        }
    }

    // 加载可用版本列表
    private async loadVersions() {
        try {
            // 从配置文件获取可用版本列表（包含description字段）
            const versionsData = await this.api.listVersions()

            // 更新版本选择器
            const versionSelect = document.getElementById('version-select') as any
            if (versionSelect) {
                // 保留"选择版本"选项
                const firstOption = versionSelect.querySelector('fluent-option[value=""]')
                versionSelect.innerHTML = ''
                if (firstOption) {
                    versionSelect.appendChild(firstOption)
                }

                // 按操作系统分组显示版本
                // 优先显示Windows 11，然后Windows 10
                const osOrder = ['Windows 11', 'Windows 10']

                for (const osKey of osOrder) {
                    if (!versionsData || !(osKey in versionsData)) continue

                    // 添加分组标题（使用disabled的option）
                    const groupHeader = document.createElement('fluent-option')
                    groupHeader.setAttribute('disabled', 'true')
                    groupHeader.textContent = osKey
                    versionSelect.appendChild(groupHeader)

                    // 获取该OS下的所有版本（现在versionsData[osKey]是对象，包含description和build）
                    const osVersions = versionsData[osKey] as any
                    const versionKeys = Object.keys(osVersions).sort((a, b) => {
                        // 按版本号降序排列（简单字符串比较，适用于25H2, 24H2等格式）
                        return b.localeCompare(a)
                    })

                    // 添加版本选项
                    for (const versionKey of versionKeys) {
                        const option = document.createElement('fluent-option')
                            ; (option as any).value = versionKey
                        option.textContent = versionKey
                        versionSelect.appendChild(option)
                    }
                }
            }
        } catch (error) {
            console.error('加载版本列表失败:', error)
        }
    }

    // 加载镜像列表
    private async loadImageList() {
        const container = document.getElementById('image-list-container')
        if (container) {
            container.innerHTML = '<div class="empty-state">正在加载镜像列表...</div>'
        }

        try {
            // 保存当前镜像列表中的状态标记（verifying、redownloading）
            const stateMap = new Map<string, { verifying?: boolean; redownloading?: boolean }>()
            for (const image of this.state.imageList) {
                if (image.url) {
                    const state: { verifying?: boolean; redownloading?: boolean } = {}
                    if (image.verifying) state.verifying = true
                    if (image.redownloading) state.redownloading = true
                    if (state.verifying || state.redownloading) {
                        stateMap.set(image.url, state)
                    }
                }
            }

            console.log('[loadImageList] 开始加载本地镜像列表...')
            const images = await this.api.listImages('local', {})
            console.log('[loadImageList] 后端返回的镜像列表:', images)
            console.log('[loadImageList] 镜像数量:', images?.length || 0)

            if (!images || !Array.isArray(images)) {
                console.warn('[loadImageList] 后端返回的不是数组:', images)
                this.state.imageList = []
            } else {
                // 恢复状态标记
                for (const image of images) {
                    if (image.url && stateMap.has(image.url)) {
                        const savedState = stateMap.get(image.url)!
                        if (savedState.verifying) image.verifying = true
                        if (savedState.redownloading) image.redownloading = true
                    }
                }
                this.state.imageList = images
            }

            console.log('[loadImageList] 更新后的镜像列表:', this.state.imageList)
            this.updateImageList()
        } catch (error: any) {
            console.error('[loadImageList] 加载镜像列表失败:', error)
            if (container) {
                container.innerHTML = `<div class="empty-state">加载失败: ${error.message || '未知错误'}<br><button onclick="location.reload()" style="margin-top: 10px; padding: 8px 16px;">重试</button></div>`
            }
        }
    }

    // 测试镜像源速度
    private async testMirror() {
        const resultEl = document.getElementById('mirror-test-result')
        const testBtn = document.getElementById('test-mirror-btn') as any

        // 如果正在测试，则中止
        if (this.state.testTaskId) {
            await this.cancelTest()
            return
        }

        // 开始新测试
        if (testBtn) {
            testBtn.textContent = '中止测速'
        }

        if (resultEl) {
            resultEl.style.display = 'block'
            resultEl.textContent = '测试中（0s）'
        }

        try {
            console.log('开始调用 startTestMirror，source:', this.state.selectedSource)
            const { task_id } = await this.api.startTestMirror(this.state.selectedSource)
            this.state.testTaskId = task_id
            console.log('测试任务ID:', task_id)

            // 开始轮询状态（移除超时机制，完全依赖后端超时）
            this.startTestStatusPolling()
        } catch (error: any) {
            console.error('启动测速失败:', error)
            if (resultEl) {
                resultEl.textContent = `测试失败: ${error.message || '未知错误'}`
            }
            if (testBtn) {
                testBtn.disabled = false
                testBtn.textContent = '测试速度'
            }
            this.state.testTaskId = null
        }
    }

    // 开始轮询测试状态
    private startTestStatusPolling() {
        // 清除之前的轮询
        if (this.state.testStatusInterval) {
            clearInterval(this.state.testStatusInterval)
        }

        const resultEl = document.getElementById('mirror-test-result')
        const testBtn = document.getElementById('test-mirror-btn') as any

        // 每秒轮询一次状态
        this.state.testStatusInterval = window.setInterval(async () => {
            if (!this.state.testTaskId) {
                if (this.state.testStatusInterval) {
                    clearInterval(this.state.testStatusInterval)
                    this.state.testStatusInterval = null
                }
                return
            }

            try {
                const status = await this.api.getTestStatus(this.state.testTaskId)
                console.log('测试状态:', status)

                // 更新状态显示
                if (resultEl) {
                    if (status.status === 'running') {
                        resultEl.textContent = `测试中（${status.elapsed}s）`
                    } else if (status.status === 'cancelling') {
                        resultEl.textContent = `正在中止（${status.elapsed}s）`
                    } else if (status.status === 'completed') {
                        // 测试完成
                        if (this.state.testStatusInterval) {
                            clearInterval(this.state.testStatusInterval)
                            this.state.testStatusInterval = null
                        }

                        const result = status.result
                        this.state.mirrorTestResult = {
                            speed: result?.download_speed > 0 ? result.download_speed : undefined,
                            latency: result?.latency > 0 ? result.latency : undefined
                        }

                        const parts: string[] = []
                        if (this.state.mirrorTestResult.speed) {
                            const speedMBps = this.state.mirrorTestResult.speed / 1024 / 1024
                            parts.push(`速度: ${speedMBps.toFixed(2)} MB/s`)
                        }
                        if (this.state.mirrorTestResult.latency) {
                            parts.push(`延迟: ${this.state.mirrorTestResult.latency.toFixed(0)} ms`)
                        }

                        if (parts.length === 0) {
                            resultEl.textContent = '测试失败或无法获取结果'
                        } else {
                            resultEl.textContent = parts.join(' | ')
                        }

                        if (testBtn) {
                            testBtn.disabled = false
                            testBtn.textContent = '测试速度'
                        }
                        this.state.testTaskId = null
                    } else if (status.status === 'cancelled') {
                        // 测试已中止
                        if (this.state.testStatusInterval) {
                            clearInterval(this.state.testStatusInterval)
                            this.state.testStatusInterval = null
                        }
                        resultEl.textContent = '测试已中止'
                        if (testBtn) {
                            testBtn.disabled = false
                            testBtn.textContent = '测试速度'
                        }
                        this.state.testTaskId = null
                    } else if (status.status === 'failed') {
                        // 测试失败
                        if (this.state.testStatusInterval) {
                            clearInterval(this.state.testStatusInterval)
                            this.state.testStatusInterval = null
                        }
                        resultEl.textContent = `测试失败: ${status.error || '未知错误'}`
                        if (testBtn) {
                            testBtn.disabled = false
                            testBtn.textContent = '测试速度'
                        }
                        this.state.testTaskId = null
                    }
                }
            } catch (error: any) {
                console.error('获取测试状态失败:', error)
                // 如果获取状态失败，可能是任务不存在，停止轮询
                if (this.state.testStatusInterval) {
                    clearInterval(this.state.testStatusInterval)
                    this.state.testStatusInterval = null
                }
                if (resultEl) {
                    resultEl.textContent = '获取测试状态失败'
                }
                if (testBtn) {
                    testBtn.disabled = false
                    testBtn.textContent = '测试速度'
                }
                this.state.testTaskId = null
            }
        }, 1000) as any
    }

    // 中止测试
    private async cancelTest() {
        if (!this.state.testTaskId) {
            return
        }

        const resultEl = document.getElementById('mirror-test-result')
        const testBtn = document.getElementById('test-mirror-btn') as any

        try {
            await this.api.cancelTest(this.state.testTaskId)
            console.log('测试已中止')

            // 停止轮询
            if (this.state.testStatusInterval) {
                clearInterval(this.state.testStatusInterval)
                this.state.testStatusInterval = null
            }

            if (resultEl) {
                resultEl.textContent = '正在中止...'
            }

            // 等待状态更新（最多等待3秒）
            const taskId = this.state.testTaskId  // 保存 taskId，避免在异步过程中被清空
            if (taskId) {
                let attempts = 0
                while (attempts < 30) {
                    if (!this.state.testTaskId) {
                        // 如果 taskId 已被清空，停止等待
                        break
                    }
                    try {
                        const status = await this.api.getTestStatus(taskId)
                        if (status.status === 'cancelled' || status.status === 'completed' || status.status === 'failed') {
                            if (resultEl) {
                                resultEl.textContent = '测试已中止'
                            }
                            break
                        }
                    } catch (error) {
                        // 如果获取状态失败（例如任务不存在），停止等待
                        console.error('获取测试状态失败:', error)
                        break
                    }
                    await new Promise(resolve => setTimeout(resolve, 100))
                    attempts++
                }
            }

            if (testBtn) {
                testBtn.disabled = false
                testBtn.textContent = '测试速度'
            }
            this.state.testTaskId = null
        } catch (error: any) {
            console.error('中止测试失败:', error)
            if (resultEl) {
                resultEl.textContent = `中止失败: ${error.message || '未知错误'}`
            }
            if (testBtn) {
                testBtn.disabled = false
                testBtn.textContent = '测试速度'
            }
            this.state.testTaskId = null
        }
    }

    // 开始下载
    private async startDownload() {
        if (!this.state.selectedVersion) {
            this.notificationManager.showNotification('warning', '请选择版本')
            return
        }

        try {
            // 构建配置参数
            const os = this.state.selectedSource === 'microsoft' ? 'Windows11' : 'Windows10'
            const config = {
                os,
                version: this.state.selectedVersion,
                language: this.state.selectedLanguage,
                arch: this.state.selectedArch
            }

            // 生成输出路径（使用配置信息生成文件名）
            const outputPath = `data/isos/download.iso`

            // 立即调用后端API创建下载任务（后端会立即返回task_id，不等待URL获取）
            let taskId: string
            try {
                const result = await this.api.downloadImage(undefined, undefined, outputPath, this.state.selectedSource, config)
                taskId = result.task_id
            } catch (error: any) {
                // 如果后端调用失败，创建失败任务显示在下载列表中
                const failedTaskId = `failed-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
                this.state.downloadTasks.set(failedTaskId, {
                    outputPath,
                    progress: 0,
                    status: 'failed',
                    error: error.message || '下载启动失败',
                    isFailed: true,
                    config
                })
                this.updateDownloadingTasks()
                this.notificationManager.showNotification('error', '下载失败', error.message)
                return
            }

            // 立即创建下载任务显示（使用后端返回的task_id）
            this.state.downloadTasks.set(taskId, {
                outputPath,
                progress: 0,
                status: 'fetching', // 初始状态为获取URL/magnet中
                config
            })

            // 立即更新下载中任务显示
            this.updateDownloadingTasks()

            // 刷新镜像列表（不阻塞）
            this.loadImageList().catch((error) => {
                console.error('刷新镜像列表失败:', error)
            })
        } catch (error: any) {
            this.notificationManager.showNotification('error', '下载失败', error.message)
        }
    }

    // 导入ISO
    private async importIso(filePath: string) {
        const progressContainer = document.getElementById('import-progress-container')
        const progressBar = document.getElementById('import-progress') as any
        const statusText = document.getElementById('import-status')

        if (progressContainer) progressContainer.style.display = 'block'
        if (progressBar) progressBar.value = 0
        if (statusText) statusText.textContent = '正在识别版本...'

        this.state.importProgress = { progress: 0, status: '识别中' }

        try {
            // 注意：实际导入进度需要通过其他方式获取（如后端推送或轮询）
            // 这里简化处理，只显示开始和完成状态
            const result = await this.api.importIso(filePath, false)

            if (result.success) {
                if (progressBar) progressBar.value = 100
                if (statusText) statusText.textContent = '导入成功'

                // 刷新镜像列表
                await this.loadImageList()

                setTimeout(() => {
                    if (progressContainer) progressContainer.style.display = 'none'
                }, 2000)
            } else {
                if (statusText) statusText.textContent = `导入失败: ${result.message}`
            }
        } catch (error: any) {
            if (statusText) statusText.textContent = `导入失败: ${error.message}`
        }
    }

    // 处理删除
    private async handleDelete(image: any) {
        // 移除确认对话框，直接执行删除

        try {
            const result = await this.api.deleteIso(image.url)
            if (result.success) {
                await this.loadImageList()
                this.notificationManager.showNotification('success', '删除成功')
            } else {
                this.notificationManager.showNotification('error', '删除失败', (result as any).error || '未知错误')
            }
        } catch (error: any) {
            this.notificationManager.showNotification('error', '删除失败', error.message)
        }
    }

    // 处理校验
    private async handleVerify(image: any) {
        try {
            // 在镜像数据中添加校验中状态
            const imageIndex = this.state.imageList.findIndex((img: any) => img.url === image.url)
            if (imageIndex !== -1) {
                this.state.imageList[imageIndex].verifying = true
                this.updateImageList()
            }

            // 启动异步校验任务
            const result = await this.api.verifyIsoStart(image.url, image.checksum)
            const taskId = result.task_id

            // 轮询校验状态
            const verifyInterval = window.setInterval(async () => {
                try {
                    const status = await this.api.verifyIsoStatus(taskId)

                    if (status.status === 'completed') {
                        clearInterval(verifyInterval)
                        const verifyResult = status.result

                        // 移除校验中状态
                        if (imageIndex !== -1) {
                            delete this.state.imageList[imageIndex].verifying
                            this.updateImageList()
                        }

                        if (verifyResult?.valid) {
                            this.notificationManager.showNotification('success', '校验通过')
                        } else {
                            this.notificationManager.showNotification('error', '校验失败')
                        }
                    } else if (status.status === 'failed' || status.error) {
                        clearInterval(verifyInterval)

                        // 移除校验中状态
                        if (imageIndex !== -1) {
                            delete this.state.imageList[imageIndex].verifying
                            this.updateImageList()
                        }

                        this.notificationManager.showNotification('error', '校验失败', status.error || '未知错误')
                    }
                } catch (error: any) {
                    clearInterval(verifyInterval)

                    // 移除校验中状态
                    if (imageIndex !== -1) {
                        delete this.state.imageList[imageIndex].verifying
                        this.updateImageList()
                    }

                    this.notificationManager.showNotification('error', '校验失败', error.message)
                }
            }, 500) // 每500ms轮询一次
        } catch (error: any) {
            // 移除校验中状态
            const imageIndex = this.state.imageList.findIndex((img: any) => img.url === image.url)
            if (imageIndex !== -1) {
                delete this.state.imageList[imageIndex].verifying
                this.updateImageList()
            }

            this.notificationManager.showNotification('error', '校验失败', error.message)
        }
    }

    // 处理自动识别
    private async handleIdentify(image: any) {
        try {
            const result = await this.api.identifyIso(image.url)

            if (result.success) {
                this.notificationManager.showNotification('success', '识别成功！文件已重命名为标准格式。')
                // 刷新镜像列表
                await this.loadImageList()
            } else {
                this.notificationManager.showNotification('error', '识别失败', result.message || '未知错误')
            }
        } catch (error: any) {
            this.notificationManager.showNotification('error', '识别失败', error.message)
        }
    }

    // 处理重新下载
    private async handleRedownload(image: any) {
        // 移除确认对话框，直接执行重新下载

        try {
            // 在镜像数据中添加重新下载中状态
            const imageIndex = this.state.imageList.findIndex((img: any) => img.url === image.url)
            if (imageIndex !== -1) {
                this.state.imageList[imageIndex].redownloading = true
                this.updateImageList()
            }

            // 从镜像信息中提取配置参数
            const osType = image.os_type || (image.source_type === 'me' ? 'Windows11' : 'Windows10')
            const os = osType.includes('11') ? 'Windows11' : 'Windows10'
            const config = {
                os,
                version: image.version || '',
                language: image.language || 'zh-cn',
                arch: image.architecture || 'x64'
            }

            // 确定下载源
            const source = image.source_type === 'me' ? 'microsoft' : 'msdn'

            // 使用配置参数创建下载任务
            const result = await this.api.downloadImage(undefined, undefined, image.url, source, config)

            // 存储下载任务
            this.state.downloadTasks.set(result.task_id, {
                outputPath: image.url,
                progress: 0,
                status: 'fetching',
                isRedownload: true, // 标记为重新下载任务
                config,
                image // 保留image信息用于后续处理
            })

            // 更新下载任务显示
            this.updateDownloadingTasks()

            // 开始轮询进度（startProgressPolling会自动轮询所有下载任务）
            this.startProgressPolling()

            this.notificationManager.showNotification('success', '重新下载已开始')
        } catch (error: any) {
            // 移除重新下载中状态
            const imageIndex = this.state.imageList.findIndex((img: any) => img.url === image.url)
            if (imageIndex !== -1) {
                delete this.state.imageList[imageIndex].redownloading
                this.updateImageList()
            }

            this.notificationManager.showNotification('error', '重新下载失败', error.message)
        }
    }

    // 取消下载
    private async cancelDownload(taskId: string) {
        // 移除确认对话框，直接执行取消

        try {
            const task = this.state.downloadTasks.get(taskId)

            const result = await this.api.cancelDownload(taskId)
            if (result.success) {
                // 如果是重新下载任务，移除镜像数据中的redownloading状态标记
                if (task?.isRedownload && task?.image) {
                    const imageIndex = this.state.imageList.findIndex((img: any) => img.url === task.image.url)
                    if (imageIndex !== -1) {
                        delete this.state.imageList[imageIndex].redownloading
                        this.updateImageList()
                    }
                }

                // 后端会很快把状态标记为 cancelled，这里先从前端列表中移除
                this.state.downloadTasks.delete(taskId)
                this.updateDownloadingTasks()
                this.notificationManager.showNotification('success', '下载已取消')
            } else {
                this.notificationManager.showNotification('error', '取消下载失败', '后端返回失败')
            }
        } catch (error: any) {
            this.notificationManager.showNotification('error', '取消下载失败', error.message)
        }
    }

    // 查找任务ID
    private findTaskIdByPath(filePath: string): string | null {
        for (const [taskId, task] of this.state.downloadTasks.entries()) {
            if (task.outputPath === filePath) {
                return taskId
            }
        }
        return null
    }

    // 开始轮询下载进度
    private startProgressPolling() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval)
        }

        this.progressInterval = window.setInterval(async () => {
            for (const [taskId, task] of this.state.downloadTasks.entries()) {
                // 跳过失败任务（已显示错误状态）
                if (task.isFailed) {
                    continue
                }

                try {
                    const progress = await this.api.getDownloadProgress(taskId)

                    // 处理fetching状态（获取URL/magnet中）
                    if (progress.status === 'fetching') {
                        const fetchingStatus = document.getElementById(`fetching-status-${taskId}`)
                        const progressContainer = document.getElementById(`progress-container-${taskId}`)

                        if (fetchingStatus) {
                            fetchingStatus.style.display = 'flex'
                        }
                        if (progressContainer) {
                            progressContainer.style.display = 'none'
                        }
                        continue
                    }

                    // 更新下载中任务的进度显示
                    if (progress.status === 'downloading') {
                        // 隐藏URL获取状态，显示进度条
                        const fetchingStatus = document.getElementById(`fetching-status-${taskId}`)
                        const progressContainer = document.getElementById(`progress-container-${taskId}`)

                        if (fetchingStatus) {
                            fetchingStatus.style.display = 'none'
                        }
                        if (progressContainer) {
                            progressContainer.style.display = 'block'
                        }
                        const percent = (progress.progress || 0) * 100
                        const downloaded = progress.downloaded || 0
                        const total = progress.total || 0
                        const speed = progress.speed || 0
                        const downloadedMB = (downloaded / 1024 / 1024).toFixed(2)
                        const totalMB = total > 0 ? (total / 1024 / 1024).toFixed(2) : ''
                        const speedMB = speed > 0 ? (speed / 1024 / 1024).toFixed(2) : ''
                        const percentLabel = total > 0 ? `${percent.toFixed(1)}%` : '下载中'
                        const sizeLabel = total > 0 ? `${downloadedMB}MB / ${totalMB}MB` : `${downloadedMB}MB`
                        const speedLabel = speedMB ? `${speedMB} MB/s` : ''

                        // 更新下载中任务Card的进度条
                        const downloadingProgressBar = document.getElementById(`progress-${taskId}`) as any
                        const downloadingProgressText = document.getElementById(`progress-text-${taskId}`)

                        if (downloadingProgressBar) {
                            if (total > 0) {
                                downloadingProgressBar.value = percent
                            } else {
                                downloadingProgressBar.removeAttribute('value')
                            }
                        }

                        if (downloadingProgressText) {
                            downloadingProgressText.textContent = speedLabel
                                ? `${percentLabel} (${sizeLabel}) - ${speedLabel}`
                                : `${percentLabel} (${sizeLabel})`
                        }

                        // 同时更新已缓存镜像列表中的进度条（如果存在）
                        const cachedProgressBar = document.getElementById(`progress-${taskId}`) as any
                        const cachedProgressText = document.getElementById(`progress-text-${taskId}`)

                        if (cachedProgressBar && progress.status === 'downloading') {
                            if (total > 0) {
                                cachedProgressBar.value = percent
                            } else {
                                cachedProgressBar.removeAttribute('value')
                            }

                            if (cachedProgressText) {
                                cachedProgressText.textContent = speedLabel
                                    ? `${percentLabel} (${sizeLabel}) - ${speedLabel}`
                                    : `${percentLabel} (${sizeLabel})`
                            }
                        }
                    } else if (progress.status === 'completed') {
                        // 下载完成，移除任务并刷新列表
                        const task = this.state.downloadTasks.get(taskId)

                        // 如果是重新下载任务，移除镜像数据中的redownloading标记
                        if (task?.isRedownload && task?.image) {
                            const imageIndex = this.state.imageList.findIndex((img: any) => img.url === task.image.url)
                            if (imageIndex !== -1) {
                                delete this.state.imageList[imageIndex].redownloading
                                this.updateImageList()
                            }
                        }

                        this.state.downloadTasks.delete(taskId)
                        this.updateDownloadingTasks()
                        // 延迟刷新，确保文件已重命名
                        setTimeout(async () => {
                            await this.loadImageList()
                        }, 1000)
                    } else if (progress.status === 'failed' || progress.error) {
                        // 下载失败，更新任务状态为失败（不删除，显示在列表中）
                        const task = this.state.downloadTasks.get(taskId)
                        if (task) {
                            task.status = 'failed'
                            task.error = progress.error || '下载失败'
                            task.isFailed = true
                            this.state.downloadTasks.set(taskId, task)
                        }

                        // 如果是重新下载任务，移除镜像数据中的redownloading标记
                        if (task?.isRedownload && task?.image) {
                            const imageIndex = this.state.imageList.findIndex((img: any) => img.url === task.image.url)
                            if (imageIndex !== -1) {
                                delete this.state.imageList[imageIndex].redownloading
                                this.updateImageList()
                            }
                        }

                        this.updateDownloadingTasks()
                        await this.loadImageList()
                    } else if (progress.status === 'cancelled') {
                        // 下载被取消，移除任务
                        const task = this.state.downloadTasks.get(taskId)

                        // 如果是重新下载任务，移除镜像数据中的redownloading标记
                        if (task?.isRedownload && task?.image) {
                            const imageIndex = this.state.imageList.findIndex((img: any) => img.url === task.image.url)
                            if (imageIndex !== -1) {
                                delete this.state.imageList[imageIndex].redownloading
                                this.updateImageList()
                            }
                        }

                        this.state.downloadTasks.delete(taskId)
                        this.updateDownloadingTasks()
                        await this.loadImageList()
                    }
                } catch (error) {
                    console.error(`获取下载进度失败 (${taskId}):`, error)
                }
            }
        }, 1000) // 每秒轮询一次
    }
}

// 初始化函数
let isoCacheWorkspace: IsoCacheWorkspace | null = null

export function initIsoCache() {
    if (!isoCacheWorkspace) {
        isoCacheWorkspace = new IsoCacheWorkspace()
        isoCacheWorkspace.init()
    }
}

