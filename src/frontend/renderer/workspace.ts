/**
 * 工作区可复用控件
 * 提供Radio容器和Combo容器的创建和事件处理函数
 */

// ========================================
// 类型定义
// ========================================

export interface RadioContainerOption {
    value: string
    label: string
    description?: string
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
export type ComboControlType = 'checkbox' | 'select' | 'switch'

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
    options: ComboContainerOption[]
    // 值映射：value -> boolean (checkbox/switch) 或 string (select)
    values: Record<string, boolean | string>
    expanded?: boolean
}

// ========================================
// ComboCard容器控件（单个card，右侧控件）
// ========================================

export interface ComboCardConfig {
    id: string
    title: string
    description?: string
    icon: string // 图标必填
    controlType: ComboControlType
    // 当controlType为'select'时，必须提供selectOptions
    selectOptions?: ComboSelectOption[]
    // 当前值：boolean (checkbox/switch) 或 string (select)
    value: boolean | string
}

// ========================================
// ComboCard容器控件（单个card，右侧控件）
// ========================================

export interface ComboCardConfig {
    id: string
    title: string
    description?: string
    icon: string // 图标必填
    controlType: ComboControlType
    // 当controlType为'select'时，必须提供selectOptions
    selectOptions?: ComboSelectOption[]
    // 当前值：boolean (checkbox/switch) 或 string (select)
    value: boolean | string
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

        return `
      <div class="radio-container-item" data-value="${opt.value}" data-selected="${isSelected ? 'true' : 'false'}">
        <fluent-radio name="${name}" value="${opt.value}" ${isSelected ? 'checked' : ''}></fluent-radio>
        <div class="radio-container-item-content">
          <div class="radio-container-item-title">${opt.label}</div>
          ${optDescriptionHtml}
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
    const { id, name, title, description, icon, options, values, expanded = false } = config

    // 计算头部显示值
    const selectedCount = options.filter(opt => {
        const val = values[opt.value]
        if (opt.controlType === 'select') {
            return typeof val === 'string' && val !== ''
        } else {
            return typeof val === 'boolean' && val === true
        }
    }).length

    const selectedLabel = selectedCount > 0
        ? `${selectedCount} ${selectedCount === 1 ? 'item' : 'items'} selected`
        : 'No items selected'

    // 图标HTML（必填）
    const iconHtml = `<i data-lucide="${icon}" class="card-expandable-header-icon"></i>`

    // 描述HTML
    const descriptionHtml = description
        ? `<div class="combo-container-header-description ${description ? '' : 'hidden'}">${description}</div>`
        : ''

    // 选项列表HTML
    const optionsHtml = options.map(opt => {
        const val = values[opt.value]
        const optDescriptionHtml = opt.description
            ? `<div class="combo-container-item-description ${opt.description ? '' : 'hidden'}">${opt.description}</div>`
            : ''

        let controlHtml = ''
        let isSelected = false

        if (opt.controlType === 'checkbox') {
            isSelected = typeof val === 'boolean' && val === true
            controlHtml = `<fluent-checkbox name="${name}-${opt.value}" value="${opt.value}" ${isSelected ? 'checked' : ''}></fluent-checkbox>`
        } else if (opt.controlType === 'switch') {
            isSelected = typeof val === 'boolean' && val === true
            controlHtml = `<fluent-switch name="${name}-${opt.value}" value="${opt.value}" ${isSelected ? 'checked' : ''}></fluent-switch>`
        } else if (opt.controlType === 'select') {
            const selectedVal = typeof val === 'string' ? val : ''
            isSelected = selectedVal !== ''
            const selectOptionsHtml = (opt.selectOptions || []).map(selOpt =>
                `<fluent-option value="${selOpt.value}" ${selectedVal === selOpt.value ? 'selected' : ''}>${selOpt.label}</fluent-option>`
            ).join('')
            controlHtml = `<fluent-select name="${name}-${opt.value}" id="${name}-${opt.value}-select" style="width: 200px; min-width: 150px;">${selectOptionsHtml}</fluent-select>`
        }

        return `
      <div class="combo-container-item" data-value="${opt.value}" data-control-type="${opt.controlType}" data-selected="${isSelected ? 'true' : 'false'}">
        ${controlHtml}
        <div class="combo-container-item-content">
          <div class="combo-container-item-title">${opt.label}</div>
          ${optDescriptionHtml}
        </div>
      </div>
    `
    }).join('')

    return `
    <div class="card-expandable combo-container ${expanded ? 'expanded' : ''}" id="${id}">
      <div class="card-expandable-header combo-container-header">
        <div class="card-expandable-header-left combo-container-header-left">
          ${iconHtml}
          <div class="combo-container-header-title-group">
            <div class="card-expandable-title combo-container-header-title">${title}</div>
            ${descriptionHtml}
          </div>
        </div>
        <div class="combo-container-header-value">${selectedLabel}</div>
        <div class="card-expandable-arrow combo-container-header-arrow">
          <i data-lucide="chevron-down"></i>
        </div>
      </div>
      <div class="card-expandable-content combo-container-content">
        <div class="combo-container-list">
          ${optionsHtml}
        </div>
      </div>
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
    updateHeaderValue: boolean = true
): void {
    const container = document.querySelector(`#${containerId}`) as HTMLElement
    if (!container) return

    // 注意：展开/折叠功能由父容器的事件委托处理，这里不需要单独绑定

    // 更新头部显示值
    const updateHeader = () => {
        if (!updateHeaderValue) return

        const items = container.querySelectorAll('.combo-container-item') as NodeListOf<HTMLElement>
        let selectedCount = 0

        items.forEach(item => {
            const controlType = item.dataset.controlType
            const value = item.dataset.value
            if (!value) return

            if (controlType === 'checkbox') {
                const checkbox = item.querySelector('fluent-checkbox') as any
                if (checkbox && checkbox.checked) {
                    selectedCount++
                }
            } else if (controlType === 'switch') {
                const switchEl = item.querySelector('fluent-switch') as any
                if (switchEl && switchEl.checked) {
                    selectedCount++
                }
            } else if (controlType === 'select') {
                const select = item.querySelector('fluent-select') as any
                if (select && select.value && select.value !== '') {
                    selectedCount++
                }
            }
        })

        const valueEl = container.querySelector('.combo-container-header-value') as HTMLElement
        if (valueEl) {
            valueEl.textContent = selectedCount > 0
                ? `${selectedCount} ${selectedCount === 1 ? 'item' : 'items'} selected`
                : 'No items selected'
        }
    }

    // 获取所有当前值
    const getAllValues = (): Record<string, boolean | string> => {
        const result: Record<string, boolean | string> = {}
        const items = container.querySelectorAll('.combo-container-item') as NodeListOf<HTMLElement>

        items.forEach(item => {
            const controlType = item.dataset.controlType
            const value = item.dataset.value
            if (!value) return

            if (controlType === 'checkbox') {
                const checkbox = item.querySelector('fluent-checkbox') as any
                result[value] = checkbox ? checkbox.checked : false
            } else if (controlType === 'switch') {
                const switchEl = item.querySelector('fluent-switch') as any
                result[value] = switchEl ? switchEl.checked : false
            } else if (controlType === 'select') {
                const select = item.querySelector('fluent-select') as any
                result[value] = select ? (select.value || '') : ''
            }
        })

        return result
    }

    // Checkbox选择事件
    container.querySelectorAll('fluent-checkbox').forEach(checkbox => {
        (checkbox as any).addEventListener('change', (e: any) => {
            const target = e.target as any
            const item = target.closest('.combo-container-item') as HTMLElement

            if (item) {
                item.setAttribute('data-selected', target.checked ? 'true' : 'false')
            }

            // 更新头部显示值
            updateHeader()

            // 调用回调
            onValueChange(getAllValues())
        })
    })

    // Switch选择事件
    container.querySelectorAll('fluent-switch').forEach(switchEl => {
        (switchEl as any).addEventListener('change', (e: any) => {
            const target = e.target as any
            const item = target.closest('.combo-container-item') as HTMLElement

            if (item) {
                item.setAttribute('data-selected', target.checked ? 'true' : 'false')
            }

            // 更新头部显示值
            updateHeader()

            // 调用回调
            onValueChange(getAllValues())
        })
    })

    // Select选择事件
    container.querySelectorAll('fluent-select').forEach(select => {
        (select as any).addEventListener('change', (e: any) => {
            const target = e.target as any
            const item = target.closest('.combo-container-item') as HTMLElement

            if (item) {
                const hasValue = target.value && target.value !== ''
                item.setAttribute('data-selected', hasValue ? 'true' : 'false')
            }

            // 更新头部显示值
            updateHeader()

            // 调用回调
            onValueChange(getAllValues())
        })
    })

    // 点击列表项也可以切换（仅对checkbox/switch有效）
    container.querySelectorAll('.combo-container-item').forEach((item: any) => {
        item.addEventListener('click', (e: any) => {
            const controlType = item.dataset.controlType

            // 如果点击的是控件本身，不处理（避免重复触发）
            if (e.target.closest('fluent-checkbox') || e.target.closest('fluent-select')) return

            // 只对checkbox/switch支持点击切换
            if (controlType === 'checkbox') {
                const checkbox = item.querySelector('fluent-checkbox') as any
                if (checkbox) {
                    checkbox.checked = !checkbox.checked
                    checkbox.dispatchEvent(new Event('change', { bubbles: true }))
                }
            } else if (controlType === 'switch') {
                const switchEl = item.querySelector('fluent-switch') as any
                if (switchEl) {
                    switchEl.checked = !switchEl.checked
                    switchEl.dispatchEvent(new Event('change', { bubbles: true }))
                }
            }
        })
    })
}

// ========================================
// ComboCard容器控件（单个card，右侧控件）
// ========================================

/**
 * 创建ComboCard HTML
 */
export function createComboCard(config: ComboCardConfig): string {
    const { id, title, description, icon, controlType, selectOptions, value } = config

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
        const selectOptionsHtml = (selectOptions || []).map(selOpt =>
            `<fluent-option value="${selOpt.value}" ${selectedVal === selOpt.value ? 'selected' : ''}>${selOpt.label}</fluent-option>`
        ).join('')
        controlHtml = `<fluent-select id="${id}-control" style="min-width: 150px; max-width: none; width: auto;">${selectOptionsHtml}</fluent-select>`
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
    }
}

