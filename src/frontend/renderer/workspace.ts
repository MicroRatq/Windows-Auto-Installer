/**
 * 工作区可复用控件
 * 提供Radio容器和Combo容器的创建和事件处理函数
 */

import { t } from './i18n'

// ========================================
// 类型定义
// ========================================

export interface RadioContainerOption {
    value: string
    label: string
    description?: string
    nestedCards?: (ComboCardConfig | TextCardConfig | { type: 'multiColumnCheckbox', config: MultiColumnCheckboxConfig } | { type: 'radioContainer', config: RadioContainerConfig })[] // 嵌套的卡片，支持 ComboCard、TextCard、多列Checkbox容器或 RadioContainer
}

export interface RadioContainerConfig {
    id: string
    name: string
    title: string
    description?: string
    icon: string // 图标必填
    options: RadioContainerOption[]
    selectedValue: string
    expanded?: boolean
}

// Combo容器选项类型
export type ComboControlType = 'checkbox' | 'select' | 'switch' | 'text'

export interface ComboSelectOption {
    value: string
    label: string
}

export interface ComboContainerOption {
    value: string
    label: string
    description?: string
    controlType: ComboControlType
    // 当controlType为'select'时，必须提供selectOptions
    selectOptions?: ComboSelectOption[]
}

export interface ComboContainerConfig {
    id: string
    name: string
    title: string
    description?: string
    icon: string // 图标必填
    nestedCards?: (ComboCardConfig | TextCardConfig | { type: 'multiColumnCheckbox', config: MultiColumnCheckboxConfig })[] // 嵌套的卡片，支持 ComboCard、TextCard 或多列Checkbox容器
    expanded?: boolean
    showHeader?: boolean // 是否显示头部（默认true）
    borderless?: boolean // 是否无边框模式（默认false）
}

// ========================================
// ComboCard容器控件（单个card，右侧控件）
// ========================================

export interface ComboCardConfig {
    id: string
    title: string
    description?: string
    icon?: string // 图标改为可选
    controlType: ComboControlType
    // 当controlType为'select'时，必须提供options
    options?: ComboSelectOption[]
    // 当前值：boolean (checkbox/switch) 或 string (select/text)
    value: boolean | string
    borderless?: boolean // 是否无边框模式（仅保留内容）
    placeholder?: string // 文本输入框的占位符（用于text类型）
}

// ========================================
// TextCard 容器控件（多行文本输入，带导入导出）
// ========================================

export interface TextCardConfig {
    id: string
    title: string
    description?: string
    icon?: string // 图标可选
    value: string
    placeholder?: string
    rows?: number // 文本区域行数，默认5
    borderless?: boolean // 是否无边框模式
    showImportExport?: boolean // 是否显示导入导出按钮，默认true
}

// ========================================
// 多列Checkbox容器控件（用于数量多、文本短的场景）
// ========================================

export interface MultiColumnCheckboxOption {
    value: string
    label: string
}

export interface MultiColumnCheckboxConfig {
    id: string
    name: string
    title?: string // 标题可选（用于嵌入场景）
    description?: string
    icon?: string // 图标可选（用于嵌入场景）
    options: MultiColumnCheckboxOption[]
    values: Record<string, boolean> // 值映射：value -> boolean
    expanded?: boolean // 是否默认展开
    showHeader?: boolean // 是否显示头部（标题、图标、折叠按钮），默认true
    minColumnWidth?: number // 最小列宽（px），用于自适应计算，默认120
    maxColumns?: number // 最大列数，用于限制列数确保文本完整显示，默认不限制
}

// ========================================
// 可变列表容器控件（支持动态增删相同类型的card）
// ========================================

export type ListItemCardType = 'comboCard' | 'textCard' | 'comboContainer'

export interface DynamicListItem {
    id: string // UUID
    cardType: ListItemCardType
    cardConfig: ComboCardConfig | TextCardConfig | ComboContainerConfig
    nestedCard?: ComboCardConfig | TextCardConfig | ComboContainerConfig // 可选的嵌套card（用于组合card场景）
}

export interface DynamicListContainerConfig {
    id: string
    name: string
    title?: string
    description?: string
    icon?: string
    itemCardType: ListItemCardType
    defaultCardConfig: () => ComboCardConfig | TextCardConfig | ComboContainerConfig
    items: DynamicListItem[]
    expanded?: boolean
    showHeader?: boolean // 是否显示容器头部（嵌入模式），默认true
    embedded?: boolean // 是否为嵌入模式，默认false
}

// ========================================
// Radio容器控件
// ========================================

/**
 * 创建Radio容器HTML
 */
export function createRadioContainer(config: RadioContainerConfig): string {
    const { id, name, title, description, icon, options, selectedValue, expanded = false } = config

    // 获取当前选中项的标签
    const selectedOption = options.find(opt => opt.value === selectedValue)
    const selectedLabel = selectedOption?.label || ''

    // 图标HTML（必填）
    const iconHtml = `<i data-lucide="${icon}" class="card-expandable-header-icon"></i>`

    // 描述HTML
    const descriptionHtml = description
        ? `<div class="radio-container-header-description ${description ? '' : 'hidden'}">${description}</div>`
        : ''

    // 选项列表HTML
    const optionsHtml = options.map(opt => {
        const isSelected = opt.value === selectedValue
        const optDescriptionHtml = opt.description
            ? `<div class="radio-container-item-description ${opt.description ? '' : 'hidden'}">${opt.description}</div>`
            : ''

        // 嵌套的 ComboCard/TextCard/MultiColumnCheckbox/RadioContainer HTML
        const nestedCardsHtml = (opt.nestedCards && opt.nestedCards.length > 0)
            ? `<div class="radio-container-nested-cards">
                ${opt.nestedCards.map(cardConfig => {
                // 检查是否为 MultiColumnCheckbox 配置
                if (typeof cardConfig === 'object' && 'type' in cardConfig && (cardConfig as any).type === 'multiColumnCheckbox') {
                    return createMultiColumnCheckboxContainer((cardConfig as any).config)
                }
                // 检查是否为 RadioContainer 配置
                if (typeof cardConfig === 'object' && 'type' in cardConfig && (cardConfig as any).type === 'radioContainer') {
                    return createRadioContainer((cardConfig as any).config)
                }
                // 检查是否为 TextCard 配置（根据特有属性判断）
                const cardConfigAny = cardConfig as any
                if ('rows' in cardConfigAny || 'showImportExport' in cardConfigAny) {
                    return createTextCard(cardConfigAny)
                }
                // 默认为 ComboCard 配置
                return createComboCard(cardConfigAny)
            }).join('<div class="radio-container-nested-divider"></div>')}
               </div>`
            : ''

        return `
      <div class="radio-container-item" data-value="${opt.value}" data-selected="${isSelected ? 'true' : 'false'}">
        <fluent-radio name="${name}" value="${opt.value}" ${isSelected ? 'checked' : ''}></fluent-radio>
        <div class="radio-container-item-content">
          <div class="radio-container-item-title">${opt.label}</div>
          ${optDescriptionHtml}
          ${nestedCardsHtml}
        </div>
      </div>
    `
    }).join('')

    return `
    <div class="card-expandable radio-container ${expanded ? 'expanded' : ''}" id="${id}">
      <div class="card-expandable-header radio-container-header">
        <div class="card-expandable-header-left radio-container-header-left">
          ${iconHtml}
          <div class="radio-container-header-title-group">
            <div class="card-expandable-title radio-container-header-title">${title}</div>
            ${descriptionHtml}
          </div>
        </div>
        <div class="radio-container-header-value">${selectedLabel}</div>
        <div class="card-expandable-arrow radio-container-header-arrow">
          <i data-lucide="chevron-down"></i>
        </div>
      </div>
      <div class="card-expandable-content radio-container-content">
        <div class="radio-container-list">
          ${optionsHtml}
        </div>
      </div>
    </div>
  `
}

/**
 * 设置Radio容器事件监听
 */
export function setupRadioContainer(
    containerId: string,
    radioName: string,
    onValueChange: (value: string) => void,
    updateHeaderValue: boolean = true
): void {
    const container = document.querySelector(`#${containerId}`) as HTMLElement
    if (!container) return

    // 注意：展开/折叠功能由父容器的事件委托处理，这里不需要单独绑定

    // Radio选择事件
    container.querySelectorAll(`fluent-radio[name="${radioName}"]`).forEach(radio => {
        (radio as any).addEventListener('change', (e: any) => {
            const target = e.target as any
            if (target.checked) {
                // 取消选中同组的其他radio
                container.querySelectorAll(`fluent-radio[name="${radioName}"]`).forEach((r: any) => {
                    if (r !== target) {
                        r.checked = false
                    }
                })

                // 更新选中状态
                container.querySelectorAll('.radio-container-item').forEach((item: any) => {
                    item.setAttribute('data-selected', item.dataset.value === target.value ? 'true' : 'false')
                })

                // 更新头部显示值
                if (updateHeaderValue) {
                    const selectedItem = container.querySelector(`.radio-container-item[data-value="${target.value}"]`) as HTMLElement
                    const titleEl = selectedItem?.querySelector('.radio-container-item-title')
                    if (titleEl) {
                        const valueEl = container.querySelector('.radio-container-header-value') as HTMLElement
                        if (valueEl) {
                            valueEl.textContent = titleEl.textContent || ''
                        }
                    }
                }

                // 调用回调
                onValueChange(target.value)
            }
        })
    })

    // 点击列表项也可以选择
    container.querySelectorAll('.radio-container-item').forEach((item: any) => {
        item.addEventListener('click', (e: any) => {
            // 如果点击的是radio本身，不处理（避免重复触发）
            if (e.target.closest('fluent-radio')) return

            // 如果点击的是嵌套卡片内部（输入框、按钮等），不处理
            if (e.target.closest('.radio-container-nested-cards')) return
            if (e.target.closest('.combo-card-borderless')) return
            if (e.target.closest('.text-card-borderless')) return
            if (e.target.closest('.multi-column-checkbox-container')) return
            if (e.target.closest('.radio-container')) return // 嵌套的 RadioContainer

            const radio = item.querySelector('fluent-radio') as any
            if (radio) {
                radio.checked = true
                radio.dispatchEvent(new Event('change', { bubbles: true }))
            }
        })
    })
}

// ========================================
// Combo容器控件（支持Checkbox/Select/Switch）
// ========================================

/**
 * 创建Combo容器HTML
 */
export function createComboContainer(config: ComboContainerConfig): string {
    const { id, title, description, icon, nestedCards, expanded = false, showHeader = true, borderless = false } = config

    // 图标HTML（必填）
    const iconHtml = `<i data-lucide="${icon}" class="card-expandable-header-icon"></i>`

    // 描述HTML
    const descriptionHtml = description
        ? `<div class="combo-container-header-description ${description ? '' : 'hidden'}">${description}</div>`
        : ''

    // 嵌套卡片HTML（参考 RadioContainer 的实现）
    const nestedCardsHtml = (nestedCards && nestedCards.length > 0)
        ? `<div class="combo-container-nested-cards">
            ${nestedCards.map(cardConfig => {
            // 检查是否为 MultiColumnCheckbox 配置
            if (typeof cardConfig === 'object' && 'type' in cardConfig && (cardConfig as any).type === 'multiColumnCheckbox') {
                return createMultiColumnCheckboxContainer((cardConfig as any).config)
            }
            // 检查是否为 TextCard 配置（根据特有属性判断）
            const cardConfigAny = cardConfig as any
            if ('rows' in cardConfigAny || 'showImportExport' in cardConfigAny) {
                return createTextCard(cardConfigAny)
            }
            // 默认为 ComboCard 配置
            return createComboCard(cardConfigAny)
        }).join('<div class="combo-container-nested-divider"></div>')}
           </div>`
        : ''

    // 头部HTML（当showHeader=true时显示）
    const headerHtml = showHeader
        ? `
      <div class="card-expandable-header combo-container-header">
        <div class="card-expandable-header-left combo-container-header-left">
          ${iconHtml}
          <div class="combo-container-header-title-group">
            <div class="card-expandable-title combo-container-header-title">${title}</div>
            ${descriptionHtml}
          </div>
        </div>
        <div class="card-expandable-arrow combo-container-header-arrow">
          <i data-lucide="chevron-down"></i>
        </div>
      </div>
    `
        : ''

    // 内容区域HTML
    const contentHtml = `
      <div class="card-expandable-content combo-container-content">
        ${nestedCardsHtml}
      </div>
    `

    // 根据showHeader和borderless决定容器结构
    if (!showHeader) {
        // 无头模式：直接返回内容区域，不包含card-expandable包装
        const borderlessClass = borderless ? 'combo-container-borderless' : ''
        return `
      <div class="combo-container ${borderlessClass}" id="${id}">
        ${contentHtml}
      </div>
    `
    }

    // 有头模式：使用card-expandable结构
    const borderlessClass = borderless ? 'combo-container-borderless' : ''
    return `
    <div class="card-expandable combo-container ${borderlessClass} ${expanded ? 'expanded' : ''}" id="${id}">
      ${headerHtml}
      ${contentHtml}
    </div>
  `
}

/**
 * 设置Combo容器事件监听
 */
export function setupComboContainer(
    containerId: string,
    _comboName: string, // 保留参数以保持API兼容性，但当前未使用
    onValueChange: (values: Record<string, boolean | string>) => void,
    _updateHeaderValue: boolean = true, // 保留参数以保持API兼容性，但当前未使用
    config?: ComboContainerConfig // 可选配置，用于获取嵌套卡片信息
): void {
    const container = document.querySelector(`#${containerId}`) as HTMLElement
    if (!container) return

    // 注意：展开/折叠功能由父容器的事件委托处理，这里不需要单独绑定

    // 从嵌套卡片中收集所有值
    const getAllValues = (): Record<string, boolean | string> => {
        const result: Record<string, boolean | string> = {}

        if (!config || !config.nestedCards) {
            return result
        }

        // 遍历嵌套卡片，从每个卡片中获取值
        config.nestedCards.forEach(cardConfig => {
            // 检查是否为 MultiColumnCheckbox 配置
            if (typeof cardConfig === 'object' && 'type' in cardConfig && (cardConfig as any).type === 'multiColumnCheckbox') {
                const multiColumnConfig = (cardConfig as any).config as MultiColumnCheckboxConfig
                const multiColumnContainer = container.querySelector(`#${multiColumnConfig.id}`) as HTMLElement
                if (multiColumnContainer) {
                    // 从 MultiColumnCheckboxContainer 中获取值
                    const items = multiColumnContainer.querySelectorAll('.multi-column-checkbox-item') as NodeListOf<HTMLElement>
                    items.forEach(item => {
                        const checkbox = item.querySelector('fluent-checkbox') as any
                        const value = item.dataset.value
                        if (value && checkbox) {
                            result[value] = checkbox.checked || false
                        }
                    })
                }
            } else {
                // 检查是否为 TextCard 配置
                const cardConfigAny = cardConfig as any
                if ('rows' in cardConfigAny || 'showImportExport' in cardConfigAny) {
                    // TextCard
                    const textCardId = cardConfigAny.id
                    const value = getTextCardValue(textCardId, false)
                    // 使用 card id 的最后部分作为 key（例如：script-content-xxx -> content）
                    const key = textCardId.split('-').slice(-2).join('_') // 取最后两部分，如 script_content_xxx
                    result[key] = value
                } else {
                    // ComboCard
                    const comboCardId = cardConfigAny.id
                    const comboCard = container.querySelector(`#${comboCardId}`) as HTMLElement
                    if (comboCard) {
                        const controlType = cardConfigAny.controlType
                        let value: boolean | string = ''

                        if (controlType === 'checkbox' || controlType === 'switch') {
                            const control = comboCard.querySelector(`#${comboCardId}-control`) as any
                            value = control ? control.checked : false
                        } else if (controlType === 'select') {
                            const select = comboCard.querySelector(`#${comboCardId}-control`) as any
                            value = select ? (select.value || '') : ''
                        } else if (controlType === 'text') {
                            const textField = comboCard.querySelector(`#${comboCardId}-control`) as any
                            value = textField ? (textField.value || '') : ''
                        }

                        // 使用 card id 的最后部分作为 key（例如：script-type-xxx -> type）
                        // 或者使用完整 id 作为 key
                        const key = comboCardId.split('-').slice(-2).join('_') // 取最后两部分，如 script_type_xxx
                        result[key] = value
                    }
                }
            }
        })

        return result
    }

    // 为嵌套卡片设置事件监听
    if (config && config.nestedCards) {
        config.nestedCards.forEach(cardConfig => {
            // 检查是否为 MultiColumnCheckbox 配置
            if (typeof cardConfig === 'object' && 'type' in cardConfig && (cardConfig as any).type === 'multiColumnCheckbox') {
                const multiColumnConfig = (cardConfig as any).config as MultiColumnCheckboxConfig
                setupMultiColumnCheckboxContainer(
                    multiColumnConfig.id,
                    multiColumnConfig.name,
                    (_values: Record<string, boolean>) => {
                        // 当 MultiColumnCheckbox 的值变化时，收集所有值并调用回调
                        onValueChange(getAllValues())
                    },
                    false // 不更新头部值（由父容器处理）
                )
            } else {
                // 检查是否为 TextCard 配置
                const cardConfigAny = cardConfig as any
                if ('rows' in cardConfigAny || 'showImportExport' in cardConfigAny) {
                    // TextCard
                    setupTextCard(
                        cardConfigAny.id,
                        (_value: string) => {
                            // 当 TextCard 的值变化时，收集所有值并调用回调
                            onValueChange(getAllValues())
                        },
                        undefined, // 导入功能（如果需要可以传递）
                        undefined  // 导出功能（如果需要可以传递）
                    )
                } else {
                    // ComboCard
                    setupComboCard(
                        cardConfigAny.id,
                        (_value: boolean | string) => {
                            // 当 ComboCard 的值变化时，收集所有值并调用回调
                            onValueChange(getAllValues())
                        }
                    )
                }
            }
        })
    }
}

// ========================================
// ComboCard容器控件（单个card，右侧控件）
// ========================================

/**
 * 创建ComboCard HTML
 */
export function createComboCard(config: ComboCardConfig): string {
    const { id, title, description, icon, controlType, options, value, borderless = false, placeholder = '' } = config

    // 图标HTML（可选）
    const iconHtml = icon ? `<i data-lucide="${icon}" class="card-icon"></i>` : ''

    // 描述HTML
    const descriptionHtml = description
        ? `<div class="card-description">${description}</div>`
        : ''

    // 控件HTML
    let controlHtml = ''
    if (controlType === 'checkbox') {
        const isChecked = typeof value === 'boolean' && value === true
        controlHtml = `<fluent-checkbox id="${id}-control" ${isChecked ? 'checked' : ''}></fluent-checkbox>`
    } else if (controlType === 'switch') {
        const isChecked = typeof value === 'boolean' && value === true
        controlHtml = `<fluent-switch id="${id}-control" ${isChecked ? 'checked' : ''}></fluent-switch>`
    } else if (controlType === 'select') {
        const selectedVal = typeof value === 'string' ? value : ''
        const selectOptionsHtml = (options || []).map(selOpt =>
            `<fluent-option value="${selOpt.value}" ${selectedVal === selOpt.value ? 'selected' : ''}>${selOpt.label}</fluent-option>`
        ).join('')
        controlHtml = `<fluent-select id="${id}-control" style="min-width: 150px; max-width: none; width: auto;">${selectOptionsHtml}</fluent-select>`
    } else if (controlType === 'text') {
        const textVal = typeof value === 'string' ? value : ''
        controlHtml = `<fluent-text-field id="${id}-control" value="${textVal}" placeholder="${placeholder}" style="min-width: 150px; max-width: 300px; width: auto;"></fluent-text-field>`
    }

    // 无边框模式
    if (borderless) {
        return `
        <div class="combo-card-borderless" id="${id}">
          <div class="card-left">
            ${iconHtml}
            <div class="card-content">
              <div class="card-title">${title}</div>
              ${descriptionHtml}
            </div>
          </div>
          <div class="card-right">
            ${controlHtml}
          </div>
        </div>
      `
    }

    return `
    <div class="card combo-card" id="${id}">
      <div class="card-left">
        ${iconHtml}
        <div class="card-content">
          <div class="card-title">${title}</div>
          ${descriptionHtml}
        </div>
      </div>
      <div class="card-right">
        ${controlHtml}
      </div>
    </div>
  `
}

/**
 * 设置ComboCard事件监听
 */
export function setupComboCard(
    cardId: string,
    onValueChange: (value: boolean | string) => void
): void {
    const card = document.querySelector(`#${cardId}`) as HTMLElement
    if (!card) return

    const control = card.querySelector(`#${cardId}-control`) as any
    if (!control) return

    const controlType = control.tagName.toLowerCase()

    if (controlType === 'fluent-checkbox' || controlType === 'fluent-switch') {
        control.addEventListener('change', (e: any) => {
            const target = e.target as any
            onValueChange(target.checked)
        })
    } else if (controlType === 'fluent-select') {
        control.addEventListener('change', (e: any) => {
            const target = e.target as any
            onValueChange(target.value || '')
        })
    } else if (controlType === 'fluent-text-field') {
        control.addEventListener('input', (e: any) => {
            const target = e.target as any
            onValueChange(target.value || '')
        })
    }
}

// ========================================
// TextCard 容器控件（多行文本输入，带导入导出）
// ========================================

/**
 * 创建TextCard HTML
 */
export function createTextCard(config: TextCardConfig): string {
    const { id, title, description, icon, value, placeholder = '', rows = 5, borderless = false, showImportExport = true } = config

    // 图标HTML（可选）
    const iconHtml = icon ? `<i data-lucide="${icon}" class="card-icon"></i>` : ''

    // 描述HTML
    const descriptionHtml = description
        ? `<div class="card-description">${description}</div>`
        : ''

    // 导入导出按钮HTML
    const importExportHtml = showImportExport
        ? `<div class="text-card-actions">
            <fluent-button id="${id}-import-btn" appearance="accent">${t('common.importFile')}</fluent-button>
            <fluent-button id="${id}-export-btn" appearance="accent">${t('common.exportFile')}</fluent-button>
          </div>`
        : ''

    // 文本区域HTML (placeholder 需要转义换行符)
    const escapedPlaceholder = placeholder.replace(/\n/g, '&#10;').replace(/"/g, '&quot;')
    const textareaHtml = `<fluent-text-area id="${id}-textarea" placeholder="${escapedPlaceholder}" rows="${rows}" style="width: 100%; min-height: ${rows * 24}px;">${value || ''}</fluent-text-area>`

    // 无边框模式
    if (borderless) {
        return `
        <div class="text-card-borderless" id="${id}">
          <div class="text-card-header">
            <div class="text-card-header-left">
              ${iconHtml}
              <div class="text-card-header-content">
                <div class="card-title">${title}</div>
                ${descriptionHtml}
              </div>
            </div>
            ${importExportHtml}
          </div>
          <div class="text-card-body">
            ${textareaHtml}
          </div>
        </div>
      `
    }

    return `
    <div class="card text-card" id="${id}">
      <div class="text-card-header">
        <div class="text-card-header-left">
          ${iconHtml}
          <div class="text-card-header-content">
            <div class="card-title">${title}</div>
            ${descriptionHtml}
          </div>
        </div>
        ${importExportHtml}
      </div>
      <div class="text-card-body">
        ${textareaHtml}
      </div>
    </div>
  `
}

/**
 * 设置TextCard事件监听
 */
export function setupTextCard(
    cardId: string,
    onValueChange: (value: string) => void,
    onImport?: () => void,
    onExport?: () => void
): void {
    const card = document.querySelector(`#${cardId}`) as HTMLElement
    if (!card) return

    const textarea = card.querySelector(`#${cardId}-textarea`) as any
    if (textarea) {
        textarea.addEventListener('input', (e: any) => {
            const target = e.target as any
            onValueChange(target.value || '')
        })
    }

    // 导入按钮
    const importBtn = card.querySelector(`#${cardId}-import-btn`) as HTMLElement
    if (importBtn && onImport) {
        importBtn.addEventListener('click', onImport)
    }

    // 导出按钮
    const exportBtn = card.querySelector(`#${cardId}-export-btn`) as HTMLElement
    if (exportBtn && onExport) {
        exportBtn.addEventListener('click', onExport)
    }
}

/**
 * 获取TextCard的当前值，如果为空则返回placeholder
 */
export function getTextCardValue(cardId: string, usePlaceholderIfEmpty: boolean = false): string {
    const card = document.querySelector(`#${cardId}`) as HTMLElement
    if (!card) return ''

    const textarea = card.querySelector(`#${cardId}-textarea`) as any
    if (!textarea) return ''

    const value = textarea.value || ''

    // 如果值为空且需要使用placeholder作为默认值
    if (usePlaceholderIfEmpty && !value && textarea.placeholder) {
        // placeholder中的HTML实体需要解码
        const placeholder = textarea.placeholder
        return placeholder.replace(/&#10;/g, '\n').replace(/&quot;/g, '"')
    }

    return value
}

/**
 * 设置TextCard的值
 */
export function setTextCardValue(cardId: string, value: string): void {
    const card = document.querySelector(`#${cardId}`) as HTMLElement
    if (!card) return

    const textarea = card.querySelector(`#${cardId}-textarea`) as any
    if (textarea) {
        textarea.value = value
    }
}

// ========================================
// 多列Checkbox容器控件（用于数量多、文本短的场景）
// ========================================

/**
 * 创建多列Checkbox容器HTML
 */
export function createMultiColumnCheckboxContainer(config: MultiColumnCheckboxConfig): string {
    const {
        id,
        name,
        title,
        description,
        icon,
        options,
        values,
        expanded = false,
        showHeader = true,
        minColumnWidth = 120,
        maxColumns
    } = config

    // 计算选中数量
    const selectedCount = options.filter(opt => values[opt.value] === true).length
    const selectedLabel = selectedCount > 0
        ? `${selectedCount} ${selectedCount === 1 ? 'item' : 'items'} selected`
        : 'No items selected'

    // 头部HTML（可选）
    let headerHtml = ''
    if (showHeader) {
        const iconHtml = icon ? `<i data-lucide="${icon}" class="card-expandable-header-icon"></i>` : ''
        const descriptionHtml = description
            ? `<div class="multi-column-checkbox-header-description ${description ? '' : 'hidden'}">${description}</div>`
            : ''
        const titleHtml = title || ''

        headerHtml = `
      <div class="card-expandable-header multi-column-checkbox-header">
        <div class="card-expandable-header-left multi-column-checkbox-header-left">
          ${iconHtml}
          <div class="multi-column-checkbox-header-title-group">
            ${titleHtml ? `<div class="card-expandable-title multi-column-checkbox-header-title">${titleHtml}</div>` : ''}
            ${descriptionHtml}
          </div>
        </div>
        <div class="multi-column-checkbox-header-value">${selectedLabel}</div>
        <div class="card-expandable-arrow multi-column-checkbox-header-arrow">
          <i data-lucide="chevron-down"></i>
        </div>
      </div>
    `
    }

    // Checkbox选项HTML（使用Grid布局实现多列）
    const optionsHtml = options.map(opt => {
        const isChecked = values[opt.value] === true
        return `
      <div class="multi-column-checkbox-item" data-value="${opt.value}" data-selected="${isChecked ? 'true' : 'false'}">
        <fluent-checkbox name="${name}-${opt.value}" value="${opt.value}" ${isChecked ? 'checked' : ''}></fluent-checkbox>
        <label class="multi-column-checkbox-label" for="${name}-${opt.value}">${opt.label}</label>
      </div>
    `
    }).join('')

    // 使用CSS Grid实现自适应列数
    // 如果设置了 maxColumns，通过调整 minmax 的最小值来间接限制列数
    // 使用 calc(100% / maxColumns) 作为最小列宽，确保不会超过 maxColumns 列
    // 如果没有设置 maxColumns，使用 minColumnWidth 作为最小列宽
    let gridStyle: string
    if (maxColumns && maxColumns > 0) {
        // 使用 max() 函数确保最小列宽不小于 minColumnWidth，同时通过 calc(100% / maxColumns) 限制最大列数
        // 这样 auto-fit 会根据容器宽度自动调整，但不会超过 maxColumns 列
        gridStyle = `grid-template-columns: repeat(auto-fit, minmax(max(${minColumnWidth}px, calc((100% - ${(maxColumns - 1) * 16}px) / ${maxColumns})), max-content));`
    } else {
        // 没有限制时，使用 minColumnWidth 作为最小列宽
        gridStyle = `grid-template-columns: repeat(auto-fit, minmax(${minColumnWidth}px, max-content));`
    }

    // 全选/取消全选按钮HTML
    const actionButtonsHtml = `
      <div class="multi-column-checkbox-actions">
        <fluent-button id="${id}-select-all" appearance="outline">${t('common.selectAll')}</fluent-button>
        <fluent-button id="${id}-deselect-all" appearance="outline">${t('common.deselectAll')}</fluent-button>
      </div>
    `

    const contentHtml = `
      <div class="card-expandable-content multi-column-checkbox-content">
        <div class="multi-column-checkbox-grid" style="${gridStyle}">
          ${optionsHtml}
        </div>
        ${actionButtonsHtml}
      </div>
    `

    // 如果隐藏头部，直接返回内容区域
    if (!showHeader) {
        return `
      <div class="multi-column-checkbox-container" id="${id}">
        ${contentHtml}
      </div>
    `
    }

    return `
    <div class="card-expandable multi-column-checkbox-container ${expanded ? 'expanded' : ''}" id="${id}">
      ${headerHtml}
      ${contentHtml}
    </div>
  `
}

/**
 * 设置多列Checkbox容器事件监听
 */
export function setupMultiColumnCheckboxContainer(
    containerId: string,
    _checkboxName: string, // 保留参数以保持API兼容性
    onValueChange: (values: Record<string, boolean>) => void,
    updateHeaderValue: boolean = true
): void {
    const container = document.querySelector(`#${containerId}`) as HTMLElement
    if (!container) return

    // 更新头部显示值
    const updateHeader = () => {
        if (!updateHeaderValue) return

        const headerValueEl = container.querySelector('.multi-column-checkbox-header-value') as HTMLElement
        if (!headerValueEl) return

        const items = container.querySelectorAll('.multi-column-checkbox-item') as NodeListOf<HTMLElement>
        let selectedCount = 0

        items.forEach(item => {
            const checkbox = item.querySelector('fluent-checkbox') as any
            if (checkbox && checkbox.checked) {
                selectedCount++
            }
        })

        headerValueEl.textContent = selectedCount > 0
            ? `${selectedCount} ${selectedCount === 1 ? 'item' : 'items'} selected`
            : 'No items selected'
    }

    // 获取所有当前值
    const getAllValues = (): Record<string, boolean> => {
        const result: Record<string, boolean> = {}
        const items = container.querySelectorAll('.multi-column-checkbox-item') as NodeListOf<HTMLElement>

        items.forEach(item => {
            const value = item.dataset.value
            if (!value) return

            const checkbox = item.querySelector('fluent-checkbox') as any
            result[value] = checkbox ? checkbox.checked : false
        })

        return result
    }

    // Checkbox选择事件
    container.querySelectorAll('fluent-checkbox').forEach(checkbox => {
        (checkbox as any).addEventListener('change', (e: any) => {
            const target = e.target as any
            const item = target.closest('.multi-column-checkbox-item') as HTMLElement

            if (item) {
                item.setAttribute('data-selected', target.checked ? 'true' : 'false')
            }

            // 更新头部显示值
            updateHeader()

            // 调用回调
            onValueChange(getAllValues())
        })
    })

    // 点击标签也可以切换checkbox
    container.querySelectorAll('.multi-column-checkbox-label').forEach(label => {
        label.addEventListener('click', (e: any) => {
            e.preventDefault()
            const item = label.closest('.multi-column-checkbox-item') as HTMLElement
            if (!item) return

            const checkbox = item.querySelector('fluent-checkbox') as any
            if (checkbox) {
                checkbox.checked = !checkbox.checked
                checkbox.dispatchEvent(new Event('change', { bubbles: true }))
            }
        })
    })

    // 点击列表项也可以切换（如果点击的不是checkbox本身）
    container.querySelectorAll('.multi-column-checkbox-item').forEach((item: any) => {
        item.addEventListener('click', (e: any) => {
            // 如果点击的是checkbox本身，不处理（避免重复触发）
            if (e.target.closest('fluent-checkbox')) return
            // 如果点击的是label，不处理（已单独处理）
            if (e.target.closest('.multi-column-checkbox-label')) return

            const checkbox = item.querySelector('fluent-checkbox') as any
            if (checkbox) {
                checkbox.checked = !checkbox.checked
                checkbox.dispatchEvent(new Event('change', { bubbles: true }))
            }
        })
    })

    // 全选按钮事件
    const selectAllBtn = container.querySelector(`#${containerId}-select-all`) as HTMLElement
    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', () => {
            const items = container.querySelectorAll('.multi-column-checkbox-item') as NodeListOf<HTMLElement>
            items.forEach(item => {
                const checkbox = item.querySelector('fluent-checkbox') as any
                if (checkbox && !checkbox.checked) {
                    checkbox.checked = true
                    item.setAttribute('data-selected', 'true')
                    checkbox.dispatchEvent(new Event('change', { bubbles: true }))
                }
            })
        })
    }

    // 取消全选按钮事件
    const deselectAllBtn = container.querySelector(`#${containerId}-deselect-all`) as HTMLElement
    if (deselectAllBtn) {
        deselectAllBtn.addEventListener('click', () => {
            const items = container.querySelectorAll('.multi-column-checkbox-item') as NodeListOf<HTMLElement>
            items.forEach(item => {
                const checkbox = item.querySelector('fluent-checkbox') as any
                if (checkbox && checkbox.checked) {
                    checkbox.checked = false
                    item.setAttribute('data-selected', 'false')
                    checkbox.dispatchEvent(new Event('change', { bubbles: true }))
                }
            })
        })
    }
}

// ========================================
// 可变列表容器控件（支持动态增删相同类型的card）
// ========================================

/**
 * 生成UUID
 */
function generateUUID(): string {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        const r = Math.random() * 16 | 0
        const v = c === 'x' ? r : (r & 0x3 | 0x8)
        return v.toString(16)
    })
}

/**
 * 创建可变列表容器HTML
 */
export function createDynamicListContainer(config: DynamicListContainerConfig): string {
    const {
        id,
        title,
        description,
        icon,
        items,
        expanded = false,
        showHeader = true,
        embedded = false
    } = config

    // 头部HTML（当showHeader=true时显示）
    let headerHtml = ''
    if (showHeader) {
        const iconHtml = icon ? `<i data-lucide="${icon}" class="card-expandable-header-icon"></i>` : ''
        const descriptionHtml = description
            ? `<div class="dynamic-list-header-description ${description ? '' : 'hidden'}">${description}</div>`
            : ''
        const titleHtml = title || ''

        headerHtml = `
      <div class="card-expandable-header dynamic-list-header">
        <div class="card-expandable-header-left dynamic-list-header-left">
          ${iconHtml}
          <div class="dynamic-list-header-title-group">
            ${titleHtml ? `<div class="card-expandable-title dynamic-list-header-title">${titleHtml}</div>` : ''}
            ${descriptionHtml}
          </div>
        </div>
        <div class="dynamic-list-header-count">${items.length} ${items.length === 1 ? 'item' : 'items'}</div>
        <div class="card-expandable-arrow dynamic-list-header-arrow">
          <i data-lucide="chevron-down"></i>
        </div>
      </div>
    `
    }

    // 列表项HTML
    const itemsHtml = items.map(item => {
        let cardHtml = ''
        let nestedCardHtml = ''

        // 根据card类型生成相应的HTML
        if (item.cardType === 'comboCard') {
            cardHtml = createComboCard(item.cardConfig as ComboCardConfig)
        } else if (item.cardType === 'textCard') {
            cardHtml = createTextCard(item.cardConfig as TextCardConfig)
        } else if (item.cardType === 'comboContainer') {
            cardHtml = createComboContainer(item.cardConfig as ComboContainerConfig)
        }

        // 如果有嵌套card，也生成其HTML
        if (item.nestedCard) {
            if ('rows' in item.nestedCard || 'showImportExport' in item.nestedCard) {
                // TextCard
                nestedCardHtml = createTextCard(item.nestedCard as TextCardConfig)
            } else if ('nestedCards' in item.nestedCard || ('name' in item.nestedCard && 'icon' in item.nestedCard)) {
                // ComboContainer (新版本使用 nestedCards，旧版本有 name 和 icon)
                nestedCardHtml = createComboContainer(item.nestedCard as ComboContainerConfig)
            } else {
                // ComboCard
                nestedCardHtml = createComboCard(item.nestedCard as ComboCardConfig)
            }
        }

        // 删除按钮HTML
        const deleteButtonHtml = `
      <button class="dynamic-list-item-delete" data-item-id="${item.id}" title="${t('common.removeItem')}">
        <i data-lucide="x"></i>
      </button>
    `

        return `
      <div class="dynamic-list-item" data-item-id="${item.id}">
        <div class="dynamic-list-item-cards">
          ${cardHtml}
          ${nestedCardHtml}
        </div>
        ${deleteButtonHtml}
      </div>
    `
    }).join('')

    // 添加按钮HTML（位于左下角）
    const addButtonHtml = `
      <button class="dynamic-list-add-button" id="${id}-add-btn" title="${t('common.addItem')}">
        <i data-lucide="plus"></i>
      </button>
    `

    // 内容区域HTML
    const contentHtml = `
      <div class="card-expandable-content dynamic-list-content">
        <div class="dynamic-list-items">
          ${itemsHtml}
        </div>
        ${addButtonHtml}
      </div>
    `

    // 根据showHeader和embedded决定容器结构
    if (!showHeader || embedded) {
        // 嵌入模式或无头模式：直接返回内容区域
        return `
      <div class="dynamic-list-container ${embedded ? 'dynamic-list-embedded' : ''}" id="${id}">
        ${contentHtml}
      </div>
    `
    }

    // 有头模式：使用card-expandable结构
    return `
    <div class="card-expandable dynamic-list-container ${expanded ? 'expanded' : ''}" id="${id}">
      ${headerHtml}
      ${contentHtml}
    </div>
  `
}

/**
 * 设置可变列表容器事件监听
 */
export function setupDynamicListContainer(
    containerId: string,
    config: DynamicListContainerConfig,
    onItemAdd: (newItem: DynamicListItem) => void,
    onItemRemove: (itemId: string) => void,
    onItemChange: (itemId: string, value: any) => void
): void {
    const container = document.querySelector(`#${containerId}`) as HTMLElement
    if (!container) return

    // 更新头部计数
    const updateHeaderCount = () => {
        const headerCountEl = container.querySelector('.dynamic-list-header-count') as HTMLElement
        if (headerCountEl) {
            const items = container.querySelectorAll('.dynamic-list-item') as NodeListOf<HTMLElement>
            const count = items.length
            headerCountEl.textContent = `${count} ${count === 1 ? 'item' : 'items'}`
        }
    }

    // 为每个列表项设置card事件监听
    config.items.forEach(item => {
        const itemElement = container.querySelector(`.dynamic-list-item[data-item-id="${item.id}"]`) as HTMLElement
        if (!itemElement) return

        // 根据card类型设置相应的事件监听（主card）
        if (item.cardType === 'comboCard') {
            const cardConfig = item.cardConfig as ComboCardConfig
            setupComboCard(cardConfig.id, (value) => {
                onItemChange(item.id, { main: value })
            })
        } else if (item.cardType === 'textCard') {
            const cardConfig = item.cardConfig as TextCardConfig
            setupTextCard(cardConfig.id, (value) => {
                onItemChange(item.id, { main: value })
            })
        } else if (item.cardType === 'comboContainer') {
            const cardConfig = item.cardConfig as ComboContainerConfig
            setupComboContainer(cardConfig.id, cardConfig.name, (values) => {
                onItemChange(item.id, values)
            }, false, cardConfig) // 传递 config 以便正确收集嵌套卡片的值
        }

        // 注意：新的 ComboContainer 使用 nestedCards 数组，不再需要单独处理 nestedCard
    })

    // 删除按钮事件监听
    container.querySelectorAll('.dynamic-list-item-delete').forEach(deleteBtn => {
        deleteBtn.addEventListener('click', (e: any) => {
            e.stopPropagation()
            const itemId = e.target.closest('.dynamic-list-item-delete')?.getAttribute('data-item-id')
            if (itemId) {
                onItemRemove(itemId)
                updateHeaderCount()
            }
        })
    })

    // 添加按钮事件监听
    const addBtn = container.querySelector(`#${containerId}-add-btn`) as HTMLElement
    if (addBtn) {
        addBtn.addEventListener('click', () => {
            // 生成新的UUID
            const newId = generateUUID()
            // 创建默认配置
            const defaultConfig = config.defaultCardConfig()
            // 为新配置设置唯一的ID
            defaultConfig.id = `${defaultConfig.id}-${newId}`

            // 创建新项
            const newItem: DynamicListItem = {
                id: newId,
                cardType: config.itemCardType,
                cardConfig: defaultConfig
            }

            onItemAdd(newItem)
            updateHeaderCount()
        })
    }
}

