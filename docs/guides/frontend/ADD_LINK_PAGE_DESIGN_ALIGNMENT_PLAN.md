# 添加链接页面设计语言对齐计划

**Date:** 2025-11-14
**Status:** Planning  
**Priority:** Medium

## 概述

将"添加链接"（LinkInputPage）页面的设计语言与"研究指导"（UserGuidancePage）页面对齐，保持统一的视觉风格和用户体验。

---

## 当前设计对比

### 研究指导页面（目标设计语言）

**布局特点：**
1. **大标题区域**：
   - 大型、居中的问题标题（`text-2xl md:text-3xl`）
   - 最大宽度约束（`max-w-3xl mx-auto`）
   - 宽松的行高（`leading-relaxed`）
   - 垂直间距（`pt-8 pb-8`）

2. **输入区域**：
   - 对话框气泡风格容器（`bg-white rounded-2xl shadow-lg p-6 border border-gray-100`）
   - 透明背景的文本区域（`border-0 bg-transparent`）
   - 无边框视觉效果，极简设计
   - 示例占位符文本（使用项目符号列表格式）
   - 内边距充足（`p-4`）

3. **操作按钮**：
   - 圆形按钮（`w-16 h-16 rounded-full`）
   - 自定义黄色（`#FEC74A`）
   - 居中对齐（`flex justify-center`）
   - 阴影效果（`shadow-xl`）
   - 悬停缩放动画（`hover:scale-110`）
   - React Feather 箭头图标（`ArrowRight`）
   - 加载状态：旋转动画的边框圆圈

4. **布局容器**：
   - 最大宽度（`max-w-4xl mx-auto`）
   - 垂直间距控制

5. **错误处理**：
   - 简单的文本错误显示（`text-sm text-red-600`）
   - 不使用复杂的错误组件

---

### 添加链接页面（当前设计）

**布局特点：**
1. **卡片容器**：
   - 使用 `Card` 组件
   - 带标题和副标题（"输入链接"、"请输入要研究的URL链接，每行一个"）
   - 标准卡片边框样式

2. **表单元素**：
   - 使用 `Textarea` 组件（带标签）
   - 标准输入边框样式
   - 辅助文本（helperText）显示
   - 标签为"URL链接"

3. **操作按钮**：
   - 使用 `Button` 组件（矩形）
   - 标准按钮变体（primary/secondary）
   - 右对齐（`justify-end`）
   - 多个按钮（"清除会话并开始新研究" + "开始研究"）

4. **警告区域**：
   - 黄色警告框（`bg-yellow-50 border border-yellow-300`）
   - 用于显示现有会话提示

---

## 对齐计划

### 1. 页面布局结构重构

**变更：**
- 移除 `Card` 组件包装
- 采用与研究指导页面相同的容器结构
- 使用 `max-w-4xl mx-auto` 作为主容器

**实现：**
```tsx
<div className="max-w-4xl mx-auto">
  {/* 大标题区域 */}
  {/* 输入区域 */}
  {/* 操作按钮 */}
</div>
```

---

### 2. 大标题区域

**变更：**
- 添加与研究指导页面类似的醒目标题区域
- 标题应清晰说明页面目的

**建议标题：**
- 主标题：`"你想研究哪些内容？"`
- 或：`"请添加你要研究的链接"`
- 样式：`text-2xl md:text-3xl font-semibold text-center text-gray-900 leading-relaxed max-w-3xl mx-auto`
- 间距：`pt-8 pb-8`

**可选副标题：**
- 如果需要更多上下文，可以在主标题下方添加较小的副标题
- 样式：`text-base text-gray-600 text-center mt-4`

---

### 3. 输入区域对话框气泡化

**变更：**
- 替换 `Textarea` 组件的使用方式
- 创建对话框气泡风格的容器
- 移除标签和辅助文本的标准显示方式

**样式：**
```tsx
<div className="max-w-2xl mx-auto mb-8">
  <div className="bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
    {/* 错误显示（如果需要） */}
    <textarea
      className="w-full min-h-[200px] p-4 border-0 bg-transparent text-base leading-relaxed placeholder:text-gray-400 focus:outline-none focus:ring-0 resize-none"
      placeholder="例如：&#10;https://www.youtube.com/watch?v=...&#10;https://www.bilibili.com/video/...&#10;https://example.com/article"
      rows={10}
    />
  </div>
</div>
```

**占位符文本改进：**
- 使用多行示例格式
- 包含支持的平台示例（YouTube, Bilibili, 文章等）

**错误处理：**
- 在对话框气泡内部显示错误
- 样式：`mb-4 text-sm text-red-600`（与研究指导页面一致）

**辅助信息（可选）：**
- 如果需要在对话框气泡外显示支持的平台信息
- 可以添加一个小提示文本，放在对话框气泡下方
- 样式：`text-xs text-gray-500 text-center mt-2`

---

### 4. 操作按钮圆形化

**变更：**
- 移除 `Button` 组件的使用
- 创建圆形操作按钮
- 使用与研究指导页面相同的样式

**样式：**
```tsx
<div className="flex justify-center">
  <button
    type="submit"
    disabled={isLoading || !urls.trim()}
    className="w-16 h-16 rounded-full text-white shadow-xl hover:scale-110 transition-all duration-200 flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
    style={{ backgroundColor: '#FEC74A' }}
    aria-label="开始研究"
  >
    {isLoading ? (
      <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
    ) : (
      <ArrowRight size={24} strokeWidth={2.5} />
    )}
  </button>
</div>
```

**需要导入：**
- `import { ArrowRight } from 'react-feather'`

---

### 5. 现有会话警告处理

**当前状态：**
- 警告框使用黄色背景（`bg-yellow-50 border border-yellow-300`）
- 包含"清除会话"按钮

**对齐选项：**

**选项 A：保持警告框但在新布局中调整位置**
- 将警告框放在大标题上方或输入区域上方
- 保持黄色警告样式，但可能需要调整圆角和间距以匹配新设计语言
- 样式调整：`rounded-2xl` 代替 `rounded-lg`，更大的内边距

**选项 B：精简警告为简单文本提示**
- 将警告简化为更轻量的文本提示
- 放在输入区域上方或下方
- 使用较小的文本样式

**选项 C：移除警告，依赖确认对话框**
- 移除警告框
- 完全依赖现有的 `window.confirm` 对话框
- 更简洁的界面

**推荐：选项 A（调整样式）**
- 保持功能可见性
- 调整样式以匹配新的设计语言
- 位置：放在输入区域对话框气泡上方

---

### 6. 清除会话按钮处理

**当前状态：**
- 有两个按钮："清除会话并开始新研究"和"开始研究"

**对齐选项：**

**选项 A：移除单独的清除按钮**
- 如果用户想清除会话，可以通过确认对话框自动处理
- 只保留一个主要的圆形操作按钮

**选项 B：添加清除按钮作为次要操作**
- 如果需要，可以添加一个小的文本链接或图标按钮
- 放在主圆形按钮附近，但不突出
- 样式：`text-sm text-gray-500 hover:text-gray-700 underline`

**推荐：选项 A**
- 与研究指导页面的单按钮设计保持一致
- 简化界面
- 通过确认对话框处理清除逻辑

---

### 7. 表单提交处理

**变更：**
- 将 `form` 的 `onSubmit` 处理保留
- 圆形按钮应该是 `type="submit"`
- 保留所有现有的验证和错误处理逻辑

**键盘快捷键：**
- 可以考虑添加 Ctrl/Cmd + Enter 提交功能（与研究指导页面一致）

---

### 8. 响应式设计

**确保：**
- 大标题在不同屏幕尺寸下正确缩放（`text-2xl md:text-3xl`）
- 对话框气泡在不同屏幕宽度下保持合适的最大宽度（`max-w-2xl`）
- 圆形按钮在所有屏幕尺寸下保持可见和可点击

---

### 9. 视觉一致性细节

**间距：**
- 标题区域：`pt-8 pb-8`
- 输入区域与标题：`mb-8`
- 输入区域与按钮：适当的垂直间距

**颜色：**
- 主要操作按钮：`#FEC74A`（黄色）
- 文本颜色：`text-gray-900`（标题）、`text-gray-400`（占位符）
- 边框颜色：`border-gray-100`（对话框气泡）

**圆角：**
- 对话框气泡：`rounded-2xl`
- 按钮：`rounded-full`

**阴影：**
- 对话框气泡：`shadow-lg`
- 按钮：`shadow-xl`

---

## 实现步骤

### 阶段 1：基础布局重构
1. 移除 `Card` 组件包装
2. 添加大标题区域
3. 调整容器结构

### 阶段 2：输入区域重构
1. 创建对话框气泡容器
2. 重构 `textarea` 样式
3. 更新占位符文本
4. 调整错误显示位置

### 阶段 3：按钮重构
1. 移除 `Button` 组件
2. 创建圆形按钮
3. 添加 `ArrowRight` 图标
4. 实现加载状态

### 阶段 4：警告区域调整
1. 调整警告框样式（如果需要）
2. 确定警告框位置
3. 处理清除按钮（如果需要）

### 阶段 5：细节优化
1. 添加键盘快捷键支持
2. 调整间距和响应式行为
3. 测试所有功能
4. 确保视觉一致性

---

## 代码变更概览

### 移除的组件/导入
- `Card` 组件
- `Button` 组件（可能）
- `Textarea` 组件（作为包装器）

### 新增的导入
- `ArrowRight` from `react-feather`

### 样式变更
- 从组件样式转为内联 Tailwind 类
- 添加对话框气泡容器
- 添加圆形按钮样式

### 保留的功能
- 所有表单验证逻辑
- 错误处理逻辑
- 现有会话检测
- 确认对话框
- API 调用逻辑
- 导航逻辑

---

## 预期效果

对齐后的"添加链接"页面应该：
1. 与研究指导页面具有一致的视觉风格
2. 使用相同的对话框气泡输入样式
3. 使用相同的圆形操作按钮
4. 保持清晰的层次结构（大标题 → 输入 → 操作）
5. 提供流畅的用户体验
6. 在所有功能保持不变的情况下，视觉效果更加统一

---

## 注意事项

1. **功能完整性**：确保所有现有功能（会话检测、错误处理、API 调用等）在重构后仍然正常工作

2. **可访问性**：圆形按钮应包含适当的 `aria-label`，确保屏幕阅读器可以正确识别

3. **错误状态**：确保错误消息在新的布局中仍然清晰可见

4. **加载状态**：圆形按钮的加载状态（旋转动画）应清晰可见

5. **响应式**：确保所有新样式在不同屏幕尺寸下都能正常工作

6. **测试**：在实现后，充分测试所有功能，特别是：
   - 表单提交
   - 错误显示
   - 现有会话检测
   - 导航流程

---

## 设计语言总结

对齐后的设计语言核心要素：
- **大标题**：醒目、居中、清晰
- **对话框气泡输入**：圆角、阴影、无边框文本区域
- **圆形操作按钮**：黄色、居中、悬停动画
- **简洁布局**：足够的间距、清晰的层次
- **一致的颜色和样式**：统一的视觉语言

