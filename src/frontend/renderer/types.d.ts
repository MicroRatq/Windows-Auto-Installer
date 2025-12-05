// Electron API 类型定义
interface ElectronAPI {
  sendToBackend: (message: any) => Promise<any>
  onBackendResponse: (callback: (data: any) => void) => void
  windowMinimize: () => Promise<void>
  windowMaximize: () => Promise<void>
  windowClose: () => Promise<void>
  windowIsMaximized: () => Promise<boolean>
  platform: string
  showOpenDialog: (options: any) => Promise<{ canceled: boolean; filePaths?: string[] }>
  showSaveDialog: (options: any) => Promise<{ canceled: boolean; filePath?: string }>
  readFile: (path: string) => Promise<string>
  writeFile: (path: string, content: string) => Promise<void>
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI
    lucide?: {
      createIcons: () => void
    }
  }
}

export {}

