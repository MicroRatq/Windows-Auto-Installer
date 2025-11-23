// 窗口控制
if (window.electronAPI) {
    document.getElementById('minimize-btn')?.addEventListener('click', () => {
        window.electronAPI.windowMinimize();
    });

    document.getElementById('maximize-btn')?.addEventListener('click', () => {
        window.electronAPI.windowMaximize();
    });

    document.getElementById('close-btn')?.addEventListener('click', () => {
        window.electronAPI.windowClose();
    });

    // 更新最大化按钮图标
    window.electronAPI.windowIsMaximized().then(isMaximized => {
        updateMaximizeButton(isMaximized);
    });

    // 监听窗口最大化状态变化
    window.electronAPI.onWindowMaximized((isMaximized) => {
        updateMaximizeButton(isMaximized);
    });
}

function updateMaximizeButton(isMaximized) {
    const btn = document.getElementById('maximize-btn');
    if (!btn) return;
    
    if (isMaximized) {
        btn.innerHTML = `
            <svg width="12" height="12" viewBox="0 0 12 12">
                <rect x="2" y="2" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1"/>
                <rect x="4" y="0" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1"/>
            </svg>
        `;
        btn.title = '还原';
    } else {
        btn.innerHTML = `
            <svg width="12" height="12" viewBox="0 0 12 12">
                <rect x="1" y="1" width="10" height="10" fill="none" stroke="currentColor" stroke-width="1"/>
            </svg>
        `;
        btn.title = '最大化';
    }
}

// 主菜单切换
document.querySelectorAll('.menu-item').forEach(item => {
    item.addEventListener('click', () => {
        const category = item.getAttribute('data-category');
        
        // 更新主菜单活动状态
        document.querySelectorAll('.menu-item').forEach(btn => btn.classList.remove('active'));
        item.classList.add('active');
        
        // 显示对应的二级菜单
        document.querySelectorAll('.submenu').forEach(submenu => {
            submenu.style.display = 'none';
        });
        const targetSubmenu = document.querySelector(`.submenu[data-category="${category}"]`);
        if (targetSubmenu) {
            targetSubmenu.style.display = 'flex';
            // 激活第一个二级菜单项
            const firstItem = targetSubmenu.querySelector('.submenu-item');
            if (firstItem) {
                document.querySelectorAll('.submenu-item').forEach(i => i.classList.remove('active'));
                firstItem.classList.add('active');
                const pageId = firstItem.getAttribute('data-page');
                switchPage(pageId);
            }
        }
    });
});

// 二级菜单切换
document.querySelectorAll('.submenu-item').forEach(item => {
    item.addEventListener('click', () => {
        const pageId = item.getAttribute('data-page');
        
        // 更新二级菜单活动状态
        const submenu = item.closest('.submenu');
        if (submenu) {
            submenu.querySelectorAll('.submenu-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
        }
        
        // 切换页面
        switchPage(pageId);
    });
});

// 页面切换
function switchPage(pageId) {
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    const targetPage = document.getElementById(`page-${pageId}`);
    if (targetPage) {
        targetPage.classList.add('active');
    }
}

// 侧边栏拖动调整
let isResizing = false;
let sidebarWidth = 240;
const sidebar = document.getElementById('sidebar');
const resizer = document.getElementById('sidebar-resizer');
const workArea = document.getElementById('work-area');

if (resizer && sidebar) {
    resizer.addEventListener('mousedown', (e) => {
        isResizing = true;
        resizer.classList.add('dragging');
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        
        const rect = sidebar.getBoundingClientRect();
        const newWidth = e.clientX - rect.left;
        const minWidth = 200;
        const maxWidth = 400;
        
        if (newWidth >= minWidth && newWidth <= maxWidth) {
            sidebarWidth = newWidth;
            sidebar.style.width = `${sidebarWidth}px`;
        }
    });

    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            resizer.classList.remove('dragging');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        }
    });
}

// ISO镜像来源切换
document.querySelectorAll('input[name="iso-source"]').forEach(radio => {
    radio.addEventListener('change', () => {
        const source = radio.value;
        const downloadOptions = document.getElementById('iso-download-options');
        const localOptions = document.getElementById('iso-local-options');
        
        if (source === 'download') {
            downloadOptions.style.display = 'block';
            localOptions.style.display = 'none';
        } else {
            downloadOptions.style.display = 'none';
            localOptions.style.display = 'block';
        }
    });
});

// 激活方式切换
document.querySelectorAll('input[name="activation-method"]').forEach(radio => {
    radio.addEventListener('change', () => {
        const method = radio.value;
        const kmsOptions = document.getElementById('kms-options');
        
        if (method === 'kms') {
            kmsOptions.style.display = 'block';
        } else {
            kmsOptions.style.display = 'none';
        }
    });
});

// 状态更新函数
function updateStatus(message) {
    console.log('Status:', message);
}

// 错误处理
function showError(message) {
    console.error(message);
    // 可以添加UI错误提示
}

// Python后端通信
async function sendToPython(action, data = {}) {
    try {
        if (window.electronAPI) {
            const response = await window.electronAPI.sendToPython(action, data);
            return response;
        } else {
            throw new Error('Electron API not available');
        }
    } catch (error) {
        showError(error.message);
        throw error;
    }
}

// ISO下载
document.getElementById('download-iso-btn')?.addEventListener('click', async () => {
    const source = document.querySelector('input[name="iso-source"]:checked').value;
    const config = {
        source: source,
        version: source === 'download' ? document.getElementById('windows-version').value : undefined
    };

    try {
        updateStatus('正在下载ISO镜像...');
        await sendToPython('generate-iso', config);
        updateStatus('ISO镜像下载完成');
    } catch (error) {
        showError('ISO下载失败: ' + error.message);
    }
});

// ISO生成
document.getElementById('generate-iso-btn')?.addEventListener('click', async () => {
    const config = {
        username: document.getElementById('username').value,
        password: document.getElementById('password').value,
        timezone: document.getElementById('timezone').value,
        options: {
            disableHibernation: document.getElementById('disable-hibernation').checked,
            kmsActivate: document.getElementById('kms-activate').checked,
            pauseUpdates: document.getElementById('pause-updates').checked,
            setPowerPlan: document.getElementById('set-power-plan').checked,
            removeDefaultUser: document.getElementById('remove-defaultuser').checked,
            removeQuickAccess: document.getElementById('remove-quick-access').checked
        }
    };

    try {
        updateStatus('正在生成ISO镜像...');
        await sendToPython('generate-iso', config);
        updateStatus('ISO镜像生成完成');
    } catch (error) {
        showError('ISO生成失败: ' + error.message);
    }
});

// pagefile迁移
document.getElementById('migrate-pagefile-btn')?.addEventListener('click', async () => {
    const target = document.getElementById('pagefile-target').value;
    if (!target) {
        showError('请输入目标位置');
        return;
    }

    try {
        updateStatus('正在迁移pagefile.sys...');
        await sendToPython('migrate-pagefile', { target });
        updateStatus('pagefile.sys迁移完成');
    } catch (error) {
        showError('迁移失败: ' + error.message);
    }
});

// Users文件夹迁移
document.getElementById('migrate-users-btn')?.addEventListener('click', async () => {
    const target = document.getElementById('users-target').value;
    if (!target) {
        showError('请输入目标位置');
        return;
    }

    if (!confirm('Users文件夹迁移需要重启系统，是否继续？')) {
        return;
    }

    try {
        updateStatus('正在准备Users文件夹迁移...');
        await sendToPython('migrate-users', { target });
        updateStatus('系统将在5秒后重启...');
    } catch (error) {
        showError('迁移失败: ' + error.message);
    }
});

// Office安装
document.getElementById('install-office-btn')?.addEventListener('click', async () => {
    const version = document.getElementById('office-version').value;
    const installPath = document.getElementById('office-path').value;

    try {
        updateStatus('正在安装Office...');
        const progressDiv = document.getElementById('office-progress');
        const progressBar = document.getElementById('office-progress-bar');
        const progressText = document.getElementById('office-progress-text');
        
        progressDiv.style.display = 'block';
        progressBar.value = 0;
        progressText.textContent = '准备中...';

        await sendToPython('install-office', { version, installPath });
        
        progressBar.value = 100;
        progressText.textContent = '完成！';
        updateStatus('Office安装完成');
    } catch (error) {
        showError('Office安装失败: ' + error.message);
    }
});

// 激活
document.getElementById('activate-btn')?.addEventListener('click', async () => {
    const method = document.querySelector('input[name="activation-method"]:checked').value;
    const config = { method };

    if (method === 'kms') {
        config.server = document.getElementById('kms-server').value;
        config.port = document.getElementById('kms-port').value;
        config.key = document.getElementById('kms-key').value;
    }

    try {
        updateStatus('正在激活...');
        await sendToPython('activate', config);
        updateStatus('激活完成');
        const statusDiv = document.getElementById('activation-status');
        if (statusDiv) {
            statusDiv.textContent = '激活成功';
            statusDiv.style.color = 'var(--color-accent)';
        }
    } catch (error) {
        showError('激活失败: ' + error.message);
        const statusDiv = document.getElementById('activation-status');
        if (statusDiv) {
            statusDiv.textContent = '激活失败: ' + error.message;
            statusDiv.style.color = 'rgb(232, 17, 35)';
        }
    }
});

// 监听Python后端响应
if (window.electronAPI) {
    window.electronAPI.onPythonResponse((data) => {
        console.log('Python response:', data);
    });

    window.electronAPI.onPythonError((error) => {
        showError(error.error || 'Python后端错误');
    });
}

// 主题切换
let currentTheme = 'light';
const themeToggleBtn = document.getElementById('theme-toggle-btn');

function toggleTheme() {
    currentTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', currentTheme);
    // 保存主题偏好
    localStorage.setItem('theme', currentTheme);
}

themeToggleBtn?.addEventListener('click', toggleTheme);

// 加载保存的主题
const savedTheme = localStorage.getItem('theme');
if (savedTheme) {
    currentTheme = savedTheme;
    document.documentElement.setAttribute('data-theme', currentTheme);
}

// 初始化 - 激活第一个菜单项
document.addEventListener('DOMContentLoaded', () => {
    const firstMenuItem = document.querySelector('.menu-item');
    if (firstMenuItem) {
        firstMenuItem.click();
    }
    
    // 初始化侧边栏宽度
    if (sidebar) {
        sidebar.style.width = `${sidebarWidth}px`;
    }
});
