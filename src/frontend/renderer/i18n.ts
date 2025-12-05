/**
 * 国际化（i18n）模块
 * 使用 i18next 实现多语言支持
 */

import i18next from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
// 使用相对路径导入 JSON 文件
import en from '../i18n/en.json'
import zhCN from '../i18n/zh-CN.json'

// 语言切换事件监听器
type LanguageChangeListener = (lng: string) => void
const languageChangeListeners: LanguageChangeListener[] = []

// 初始化 i18next（异步）
let i18nInitialized = false
const initPromise = i18next
  .use(LanguageDetector)
  .init({
    resources: {
      en: { translation: en },
      'zh-CN': { translation: zhCN }
    },
    fallbackLng: 'en',
    supportedLngs: ['en', 'zh-CN'],
    detection: {
      // 优先从 localStorage 读取
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng'
    },
    interpolation: {
      escapeValue: false // React 已经处理了 XSS
    }
  })
  .then(() => {
    i18nInitialized = true
    console.log('i18n initialized with language:', i18next.language)

    // 监听语言变化
    i18next.on('languageChanged', (lng) => {
      console.log('Language changed to:', lng)
      languageChangeListeners.forEach(listener => listener(lng))
    })
  })

/**
 * 翻译函数
 * @param key 翻译键
 * @param options 插值选项
 * @returns 翻译后的文本
 */
export function t(key: string, options?: any): string {
  if (!i18nInitialized) {
    console.warn('i18n not initialized yet, returning key:', key)
    return key
  }
  return i18next.t(key, options) as string
}

/**
 * 等待 i18n 初始化完成
 */
export async function waitForI18nInit(): Promise<void> {
  await initPromise
}

/**
 * 切换语言
 * @param lng 语言代码（'en' 或 'zh-CN'）
 */
export async function changeLanguage(lng: string): Promise<void> {
  await i18next.changeLanguage(lng)
}

/**
 * 获取当前语言
 * @returns 当前语言代码
 */
export function getCurrentLanguage(): string {
  return i18next.language || 'en'
}

/**
 * 添加语言切换监听器
 * @param listener 监听器函数
 */
export function addLanguageChangeListener(listener: LanguageChangeListener): void {
  languageChangeListeners.push(listener)
}

/**
 * 移除语言切换监听器
 * @param listener 监听器函数
 */
export function removeLanguageChangeListener(listener: LanguageChangeListener): void {
  const index = languageChangeListeners.indexOf(listener)
  if (index > -1) {
    languageChangeListeners.splice(index, 1)
  }
}

// 导出 i18next 实例（供高级用法）
export { i18next as i18n }

