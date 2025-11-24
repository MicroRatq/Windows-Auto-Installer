// Electron API 类型定义
interface ElectronAPI {
  sendToBackend: (message: any) => Promise<any>
  onBackendResponse: (callback: (data: any) => void) => void
  windowMinimize: () => Promise<void>
  windowMaximize: () => Promise<void>
  windowClose: () => Promise<void>
  windowIsMaximized: () => Promise<boolean>
  platform: string
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI
  }
}

export {}

