/**
 * 设置页面管理
 * 实现语言切换和其他设置功能
 */

import { t, changeLanguage, getCurrentLanguage, addLanguageChangeListener } from './i18n'
import { createRadioContainer, setupRadioContainer } from './workspace'

/**
 * 设置页面管理类
 */
export class SettingsManager {
  private panel: HTMLElement | null = null

  constructor() {
    // 监听语言切换事件
    addLanguageChangeListener((lng) => {
      console.log('Language changed in SettingsManager:', lng)
      this.render() // 重新渲染设置页面
    })
  }

  /**
   * 初始化设置页面
   */
  init() {
    this.panel = document.querySelector('.workspace-settings')
    if (!this.panel) {
      console.error('Settings panel not found')
      return
    }

    this.render()
  }

  /**
   * 渲染设置页面
   */
  render() {
    if (!this.panel) return

    const currentLang = getCurrentLanguage()

    // 创建语言选择 RadioContainer
    const languageRadioHtml = createRadioContainer({
      id: 'settings-language-container',
      name: 'settings-language',
      title: t('settings.language'),
      description: t('settings.selectLanguage'),
      icon: 'globe',
      options: [
        {
          value: 'en',
          label: t('settings.english'),
          description: ''
        },
        {
          value: 'zh-CN',
          label: t('settings.chineseSimplified'),
          description: ''
        }
      ],
      selectedValue: currentLang,
      expanded: true
    })

    this.panel.innerHTML = `
      <div class="workspace-content">
        <div class="workspace-header">
          <h2 class="workspace-title">
            <i data-lucide="settings"></i>
            ${t('settings.title')}
          </h2>
        </div>
        <div class="workspace-body">
          ${languageRadioHtml}
        </div>
      </div>
    `

    // 设置语言选择事件监听
    setupRadioContainer(
      'settings-language-container',
      'settings-language',
      (value) => {
        this.handleLanguageChange(value as string)
      },
      true
    )

    // 初始化图标
    if (window.lucide) {
      window.lucide.createIcons()
    }
  }

  /**
   * 处理语言切换
   */
  private async handleLanguageChange(lng: string) {
    console.log('Changing language to:', lng)
    try {
      await changeLanguage(lng)
      // 语言切换成功，不需要手动重新渲染，因为监听器会触发
      console.log('Language changed successfully to:', lng)

      // 触发全局刷新事件，让其他模块重新渲染
      window.dispatchEvent(new CustomEvent('language-changed', { detail: { language: lng } }))
    } catch (error) {
      console.error('Failed to change language:', error)
    }
  }

  /**
   * 显示设置页面
   */
  show() {
    if (!this.panel) return
    this.panel.style.display = 'block'
  }

  /**
   * 隐藏设置页面
   */
  hide() {
    if (!this.panel) return
    this.panel.style.display = 'none'
  }
}

// 导出单例实例
export const settingsManager = new SettingsManager()

