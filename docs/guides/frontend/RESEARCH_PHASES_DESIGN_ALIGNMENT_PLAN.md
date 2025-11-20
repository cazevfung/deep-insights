# 研究阶段页面设计语言对齐计划

**Date:** 2025-01-XX  
**Status:** Planning  
**Priority:** Medium

## 概述

将研究阶段页面（内容收集、研究规划、深度研究、研究报告等）的设计语言与"研究指导"和"添加链接"页面对齐，在保持现有良好布局设计的基础上，统一视觉风格和用户体验。

---

## 设计语言核心要素（从 UserGuidancePage/LinkInputPage 提取）

### 视觉元素
1. **大标题区域**
   - 样式：`text-2xl md:text-3xl font-semibold text-center text-gray-900 leading-relaxed`
   - 间距：`pt-8 pb-8`
   - 宽度：`max-w-3xl mx-auto`

2. **对话框气泡容器**
   - 样式：`bg-white rounded-2xl shadow-lg p-6 border border-gray-100`
   - 用途：主要内容区域、输入区域、重要信息展示

3. **圆形操作按钮**
   - 样式：`w-16 h-16 rounded-full text-white shadow-xl hover:scale-110`
   - 颜色：`#FEC74A`（自定义黄色）
   - 用途：主要操作按钮

4. **布局容器**
   - 主容器：`max-w-4xl mx-auto`
   - 内容容器：`max-w-2xl mx-auto`（对话框气泡）
   - 宽内容：`max-w-5xl` 或 `max-w-6xl`（适用于复杂内容）

5. **圆角和边框**
   - 主容器：`rounded-2xl`（替代 `rounded-lg`）
   - 次要容器：`rounded-xl` 或 `rounded-lg`（根据重要性）
   - 边框：`border-gray-100`（替代 `border-neutral-300`）

6. **阴影效果**
   - 主容器：`shadow-lg`
   - 按钮：`shadow-xl`
   - 悬停：`hover:shadow-md`

7. **间距规范**
   - 标题区域：`pt-8 pb-8`
   - 内容区域：`mb-8`
   - 内部间距：`p-6`（主容器），`p-4`（次要容器）

---

## 对齐原则

1. **保持现有布局结构**：不改变页面的功能布局和内容组织方式
2. **渐进式增强**：仅调整视觉样式，不改变交互逻辑
3. **一致性优先**：统一使用相同的设计语言元素
4. **上下文适配**：根据页面内容特点调整应用程度
5. **功能保留**：确保所有现有功能完全保留

---

## 页面 1：内容收集（ScrapingProgressPage）

### 当前状态
- **布局**：使用 `Card` 组件包装
- **容器**：`max-w-6xl mx-auto`
- **标题**：`Card` 组件的 `title` prop（"抓取进度"）
- **状态指示器**：多种颜色的状态框（`bg-yellow-50`, `bg-green-50`, `bg-blue-50`）
- **进度条**：自定义 `ProgressBar` 组件
- **取消按钮**：红色矩形按钮

### 对齐计划

#### 1. 标题区域（新增）
**位置**：Card 组件之前，页面顶部

**实现**：
```tsx
{/* Page Title Section */}
<div className="pt-8 pb-6">
  <h1 className="text-2xl md:text-3xl font-semibold text-center text-gray-900 leading-relaxed max-w-3xl mx-auto">
    内容收集进度
  </h1>
  {batchId && (
    <p className="text-center text-sm text-gray-500 mt-3">
      批次ID: {batchId}
    </p>
  )}
</div>
```

**变更**：
- 添加大标题区域
- 将 Card 的 `subtitle`（批次ID）移动到标题区域下方
- 保持 Card 的 `title` 为空或移除

#### 2. Card 组件调整
**选项 A（推荐）**：保留 Card 但调整样式
- 移除 Card 的 `title`（标题移到外部）
- 调整 Card 内部样式，使用 `rounded-2xl`
- 保持 Card 的功能性边框和阴影

**选项 B**：完全移除 Card，使用对话框气泡
- 将整个内容区域用对话框气泡容器包裹
- 更激进的对齐，但可能影响复杂布局

**推荐：选项 A**（渐进式，保持现有结构）

#### 3. 状态指示器样式调整
**当前**：`bg-yellow-50 border border-yellow-300 rounded-lg p-3`

**目标**：
```tsx
<div className="bg-yellow-50 border border-yellow-300 rounded-2xl p-4">
```

**变更**：
- `rounded-lg` → `rounded-2xl`
- `p-3` → `p-4`（更宽松的内边距）
- 保持颜色方案不变（功能性的颜色区分）

**应用范围**：
- 工作流状态指示器（黄色、绿色、蓝色、灰色）
- 取消通知框
- 新项目通知框

#### 4. 取消按钮调整（可选）
**当前**：红色矩形按钮（`bg-red-500 hover:bg-red-600`）

**选项**：
- **保持矩形**：如果红色表示危险操作，可以保持矩形以强调
- **圆形调整**：如果需要完全对齐，可以改为圆形，但不太推荐（危险操作通常用矩形）

**推荐**：保持矩形按钮，但调整样式以匹配设计语言
- 添加 `rounded-xl`（更圆润但保持矩形）
- 保持红色配色（功能性的颜色）

#### 5. 链接列表容器调整
**当前**：直接显示在 Card 内

**目标**：
- 如果链接列表较长，可以考虑添加对话框气泡样式的容器
- 或者保持现有样式，仅调整圆角（`rounded-lg` → `rounded-xl`）

### 实施优先级
1. ✅ **高优先级**：标题区域、状态指示器样式
2. ⚠️ **中优先级**：Card 组件调整、链接列表容器
3. ⚪ **低优先级**：取消按钮调整（可保持现状）

---

## 页面 2：研究规划（ResearchAgentPage）

### 当前状态
- **布局**：使用 `Card` 组件包装
- **容器**：`max-w-5xl mx-auto`
- **标题**：`Card` 组件的 `title` prop（"研究规划"）
- **快速重新运行按钮**：多个 `Button` 组件（secondary 变体）
- **综合主题展示**：大号文本区域（`bg-primary-50 p-8 rounded-xl`）
- **研究目标列表**：`ResearchGoalList` 组件

### 对齐计划

#### 1. 标题区域（新增）
**位置**：Card 组件之前

**实现**：
```tsx
{/* Page Title Section */}
<div className="pt-8 pb-6">
  <h1 className="text-2xl md:text-3xl font-semibold text-center text-gray-900 leading-relaxed max-w-3xl mx-auto">
    研究规划
  </h1>
  <p className="text-center text-sm text-gray-500 mt-3">
    当前阶段: {researchAgentStatus.phase || '准备中'}
  </p>
</div>
```

**变更**：
- 添加大标题区域
- 将 Card 的 `subtitle`（当前阶段）移动到标题区域下方

#### 2. Card 组件调整
**实现**：
- 移除 Card 的 `title` 和 `subtitle`
- 保持 Card 的容器功能
- 调整 Card 样式为 `rounded-2xl`（如果 Card 组件支持）

#### 3. 快速重新运行区域调整
**当前**：`bg-neutral-light-bg border border-neutral-300 rounded-lg p-4`

**目标**：
```tsx
<div className="bg-white border border-gray-100 rounded-2xl shadow-md p-6">
```

**变更**：
- `rounded-lg` → `rounded-2xl`
- `border-neutral-300` → `border-gray-100`（更柔和的边框）
- `bg-neutral-light-bg` → `bg-white`（更干净）
- 添加 `shadow-md`（轻微阴影）
- `p-4` → `p-6`（更宽松的内边距）

#### 4. 综合主题展示区域调整
**当前**：`bg-primary-50 p-8 rounded-xl border border-primary-200`

**目标**：
```tsx
<div className="bg-primary-50 p-8 rounded-2xl border border-primary-200 shadow-lg">
```

**变更**：
- `rounded-xl` → `rounded-2xl`（与设计语言一致）
- 添加 `shadow-lg`（提升视觉层次）

#### 5. 研究目标列表容器调整
**当前**：`bg-neutral-light-bg p-6 rounded-lg border border-neutral-300`

**目标**：
```tsx
<div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-md">
```

**变更**：
- `rounded-lg` → `rounded-2xl`
- `border-neutral-300` → `border-gray-100`
- `bg-neutral-light-bg` → `bg-white`
- 添加 `shadow-md`

#### 6. 按钮样式调整（可选）
**当前**：`Button` 组件（secondary 变体）

**选项**：
- **保持现状**：如果按钮是次要操作，可以保持现有样式
- **调整圆角**：如果 Button 组件支持，添加 `rounded-xl`

**推荐**：保持 Button 组件，但确保与设计语言协调

#### 7. 报告过期警告调整
**当前**：`bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-lg p-3`

**目标**：
```tsx
<div className="bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-2xl p-4">
```

**变更**：
- `rounded-lg` → `rounded-2xl`
- `p-3` → `p-4`

### 实施优先级
1. ✅ **高优先级**：标题区域、综合主题区域、研究目标列表容器
2. ⚠️ **中优先级**：快速重新运行区域、Card 组件调整
3. ⚪ **低优先级**：按钮样式调整、警告框调整

---

## 页面 3：深度研究（Phase3SessionPage）

### 当前状态
- **布局**：使用 `Card` 组件包装
- **容器**：`max-w-5xl mx-auto`
- **标题**：`Card` 组件的 `title` prop（"深度研究 - 分析步骤"）
- **状态横幅**：`Phase3StatusBanner` 组件
- **聚焦步骤指示器**：`rounded-xl border border-primary-200 bg-primary-50/60`
- **步骤列表**：`Phase3StepList` 组件

### 对齐计划

#### 1. 标题区域（新增）
**位置**：Card 组件之前

**实现**：
```tsx
{/* Page Title Section */}
<div className="pt-8 pb-6">
  <h1 className="text-2xl md:text-3xl font-semibold text-center text-gray-900 leading-relaxed max-w-3xl mx-auto">
    深度研究
  </h1>
  <p className="text-center text-sm text-gray-500 mt-3">
    分析步骤与研究过程
  </p>
</div>
```

**变更**：
- 添加大标题区域
- 移除 Card 的 `title`

#### 2. Card 组件调整
**实现**：
- 移除 Card 的 `title`
- 保持 Card 的容器功能

#### 3. 聚焦步骤指示器调整
**当前**：`rounded-xl border border-primary-200 bg-primary-50/60`

**目标**：
```tsx
<div className="rounded-2xl border border-primary-200 bg-primary-50/60 px-4 py-3 shadow-md">
```

**变更**：
- `rounded-xl` → `rounded-2xl`
- 添加 `shadow-md`（增强视觉层次）

#### 4. 空状态文本调整
**当前**：直接显示文本

**目标**：保持现状（简单文本不需要容器）

#### 5. Phase3StepList 组件内部样式（需要检查组件）
**说明**：需要查看 `Phase3StepList` 组件内部，确保子组件的样式也符合设计语言。

**建议检查点**：
- 步骤项容器的圆角
- 步骤项容器的边框颜色
- 步骤项容器的阴影

### 实施优先级
1. ✅ **高优先级**：标题区域、聚焦步骤指示器
2. ⚠️ **中优先级**：Card 组件调整
3. ⚪ **低优先级**：Phase3StepList 内部样式（需要检查组件实现）

---

## 页面 4：研究报告（FinalReportPage）

### 当前状态
- **布局**：自定义 `card` 类（非 Card 组件）
- **容器**：`max-w-4xl mx-auto h-full flex flex-col`
- **标题**：在 sticky 头部（`text-xl font-bold`）
- **导出按钮**：`rounded-full`（已经是圆形）
- **内容区域**：Markdown 渲染，使用 prose 样式

### 对齐计划

#### 1. 标题区域（调整现有）
**当前**：在 sticky 头部内，`text-xl font-bold`

**目标**：
```tsx
{/* Page Title Section - Outside sticky header */}
<div className="pt-8 pb-6">
  <h1 className="text-2xl md:text-3xl font-semibold text-center text-gray-900 leading-relaxed max-w-3xl mx-auto">
    研究报告
  </h1>
</div>

{/* Card with sticky header */}
<div className="card h-full flex flex-col p-0">
  <div className="sticky top-0 bg-neutral-white pb-4 border-b border-neutral-300 mb-4 z-10 px-6 pt-6 rounded-t-lg">
    {/* ... existing header content without h2 title ... */}
    {reportStale && (
      <p className="text-sm text-secondary-500 mt-2">
        提示：最终报告已过期，请重新运行阶段 4 以获取最新结果。
      </p>
    )}
    {/* Export button */}
  </div>
  {/* ... content ... */}
</div>
```

**变更**：
- 将标题移到 Card 外部，作为大标题区域
- 移除 sticky 头部内的 `h2` 标题
- 保持 sticky 头部的功能（导出按钮、警告文本）

#### 2. Card 容器样式调整
**当前**：使用 `.card` 类

**目标**：
- 调整 `.card` 类的样式以匹配 `rounded-2xl`
- 或者添加自定义样式：`rounded-2xl shadow-lg border border-gray-100`

**变更**：
- `rounded-lg` → `rounded-2xl`（在 CSS 中或内联）

#### 3. 导出按钮调整
**当前**：`rounded-full`（已经是圆形）

**目标**：
- 如果按钮是次要操作，可以保持现状
- 如果希望与主操作按钮对齐，可以调整为黄色（`#FEC74A`）

**选项 A（推荐）**：保持现有样式（导出是次要操作，不需要黄色强调）
**选项 B**：调整为黄色圆形按钮（与设计语言完全对齐）

**推荐：选项 A**

#### 4. 加载/错误状态调整
**当前**：直接显示文本

**目标**：
- 可以考虑使用对话框气泡样式包装错误信息
- 或者保持现状（简单状态不需要复杂容器）

**推荐**：保持现状（加载/错误状态应该简洁）

#### 5. Markdown 内容区域
**当前**：使用 prose 样式

**目标**：
- 保持 prose 样式（内容展示的最佳实践）
- 确保内容区域的背景和边框符合设计语言

**变更**：
- 确保内容区域的容器使用 `rounded-2xl` 和适当的阴影

### 实施优先级
1. ✅ **高优先级**：标题区域、Card 容器样式
2. ⚠️ **中优先级**：导出按钮调整（可选）
3. ⚪ **低优先级**：加载/错误状态调整（可保持现状）

---

## 页面 5：历史记录（HistoryPage）

### 当前状态
- **布局**：使用 `Card` 组件包装
- **容器**：`max-w-6xl mx-auto`
- **标题**：`Card` 组件的 `title` prop（"研究历史"）
- **搜索和过滤**：输入框和下拉选择
- **会话列表**：多个会话卡片（`rounded-lg`）
- **操作按钮**：`Button` 组件（导出、查看、继续）

### 对齐计划

#### 1. 标题区域（新增）
**位置**：Card 组件之前

**实现**：
```tsx
{/* Page Title Section */}
<div className="pt-8 pb-6">
  <h1 className="text-2xl md:text-3xl font-semibold text-center text-gray-900 leading-relaxed max-w-3xl mx-auto">
    研究历史
  </h1>
  <p className="text-center text-sm text-gray-500 mt-3">
    查看和管理之前的研究会话
  </p>
</div>
```

**变更**：
- 添加大标题区域
- 将 Card 的 `subtitle` 移动到标题区域下方

#### 2. Card 组件调整
**实现**：
- 移除 Card 的 `title` 和 `subtitle`
- 保持 Card 的容器功能

#### 3. 搜索和过滤区域调整
**当前**：`border-b border-neutral-300`（分隔线）

**目标**：
```tsx
<div className="bg-white border border-gray-100 rounded-2xl shadow-md p-6 mb-6">
  {/* Search and filter inputs */}
</div>
```

**变更**：
- 将搜索和过滤区域包装在对话框气泡容器中
- `rounded-2xl`、`shadow-md`、`border-gray-100`
- 更大的内边距 `p-6`

#### 4. 会话卡片样式调整
**当前**：`bg-neutral-white border border-neutral-300 rounded-lg p-4`

**目标**：
```tsx
<div className="bg-white border border-gray-100 rounded-2xl p-6 hover:shadow-md transition-shadow">
```

**变更**：
- `rounded-lg` → `rounded-2xl`
- `border-neutral-300` → `border-gray-100`
- `bg-neutral-white` → `bg-white`
- `p-4` → `p-6`（更宽松的内边距）
- 保持 `hover:shadow-md`（交互反馈）

#### 5. 按钮样式调整（可选）
**当前**：`Button` 组件

**推荐**：保持 Button 组件（功能按钮不需要圆形样式）

#### 6. 空状态和错误状态调整
**当前**：直接显示文本

**推荐**：保持现状（简单状态不需要复杂容器）

### 实施优先级
1. ✅ **高优先级**：标题区域、会话卡片样式
2. ⚠️ **中优先级**：搜索和过滤区域、Card 组件调整
3. ⚪ **低优先级**：按钮样式调整（可保持现状）

---

## 页面 6：报告导出（ReportExportPage）

### 当前状态
- **布局**：打印优化的专用页面
- **用途**：导出为 PDF 的视图
- **样式**：大量打印样式（`@media print`）

### 对齐计划

#### 说明
这是一个打印优化的页面，主要用途是导出 PDF。对齐设计语言的重要性较低。

#### 可选调整
1. **屏幕视图样式**（非打印时）
   - 如果页面在非打印模式下显示，可以应用设计语言
   - 添加标题区域（如果需要在打印前预览）
   - 调整容器的圆角和边框

2. **打印样式**（保持不变）
   - 保持所有打印样式不变（打印优化的重点）

**推荐**：**最小化调整**，或跳过此页面（打印页面不需要严格对齐）

---

## 通用组件样式调整

### Card 组件
**当前**：使用 `.card` 类，可能有固定的圆角

**建议调整**：
- 在 Card 组件中支持 `rounded-2xl`（通过 className prop 或默认样式）
- 或者创建新的变体（`variant="dialog"`）使用对话框气泡样式

**实现选项**：
1. **修改 Card 组件默认样式**：将 `.card` 类的 `rounded-lg` 改为 `rounded-2xl`
2. **添加 className 支持**：允许传入自定义圆角类
3. **创建新变体**：`variant="dialog"` 使用对话框气泡样式

### Button 组件
**当前**：使用 `rounded-lg`

**建议调整**：
- **主按钮**（primary）：可以考虑 `rounded-xl`
- **次要按钮**（secondary）：保持 `rounded-lg` 或 `rounded-xl`
- **圆形按钮**：仅在特定场景使用（如 UserGuidancePage/LinkInputPage）

**推荐**：保持 Button 组件现状，不强制圆形（圆形按钮是特定场景的设计）

---

## 实施检查清单

### 每个页面的通用检查点
- [ ] 添加大标题区域（`pt-8 pb-8`）
- [ ] 标题样式：`text-2xl md:text-3xl font-semibold text-center text-gray-900`
- [ ] 主容器圆角：`rounded-2xl`
- [ ] 主容器边框：`border-gray-100`
- [ ] 主容器阴影：`shadow-lg`
- [ ] 状态指示器圆角：`rounded-2xl`
- [ ] 状态指示器内边距：`p-4` 或 `p-6`
- [ ] 移除或调整 Card 组件的 `title`（移到外部）

### 功能验证
- [ ] 所有交互功能正常
- [ ] 所有按钮和链接正常工作
- [ ] 响应式布局正常
- [ ] 加载状态正常
- [ ] 错误状态正常
- [ ] 数据展示正常

### 视觉验证
- [ ] 与 UserGuidancePage/LinkInputPage 视觉一致
- [ ] 圆角样式统一
- [ ] 边框颜色统一
- [ ] 阴影效果统一
- [ ] 间距规范统一
- [ ] 颜色方案协调

---

## 实施顺序建议

### 阶段 1：核心对齐（高优先级）
1. ScrapingProgressPage - 标题区域、状态指示器
2. ResearchAgentPage - 标题区域、主要容器
3. Phase3SessionPage - 标题区域、指示器

### 阶段 2：内容对齐（中优先级）
4. FinalReportPage - 标题区域、容器样式
5. HistoryPage - 标题区域、会话卡片

### 阶段 3：细节优化（低优先级）
6. 通用组件样式调整（Card、Button）
7. 细节样式统一（边框、圆角、阴影）
8. ReportExportPage（如需要）

---

## 注意事项

1. **渐进式实施**：可以逐个页面实施，不需要一次性完成所有页面
2. **测试充分**：每个页面实施后，充分测试功能
3. **保持一致**：确保所有页面使用相同的设计语言元素
4. **保持功能**：所有现有功能必须完全保留
5. **响应式考虑**：确保所有调整在不同屏幕尺寸下正常显示
6. **可访问性**：确保设计调整不影响可访问性

---

## 设计语言总结

对齐后的设计语言核心要素：
- **大标题**：醒目、居中、清晰（所有页面顶部）
- **对话框气泡容器**：主要内容区域（`rounded-2xl shadow-lg`）
- **统一的圆角**：`rounded-2xl`（主容器）、`rounded-xl`（次要容器）
- **柔和的边框**：`border-gray-100`（替代 `border-neutral-300`）
- **一致的阴影**：`shadow-lg`（容器）、`shadow-xl`（按钮）
- **宽松的内边距**：`p-6`（主容器）、`p-4`（次要容器）
- **统一的间距**：`pt-8 pb-8`（标题区域）、`mb-8`（内容区域）
- **圆形按钮**：仅在特定场景使用（主要操作，黄色 `#FEC74A`）

