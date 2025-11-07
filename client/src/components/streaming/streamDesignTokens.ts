export const streamDesignTokens = {
  colors: {
    containerBg: 'bg-neutral-white',
    containerBorder: 'border-neutral-300',
    textPrimary: 'text-neutral-800',
    textSecondary: 'text-neutral-500',
    indicatorActive: 'bg-supportive-green',
    indicatorIdle: 'bg-neutral-300',
  },
  spacing: {
    containerPadding: 'p-6',
    headerGap: 'gap-2',
    toolbarGap: 'gap-3',
  },
  typography: {
    mono: 'font-mono',
    body: 'text-sm',
    title: 'text-base font-semibold',
  },
  sizing: {
    minHeight: 'min-h-64',
    maxHeight: 'max-h-96',
    compactMinHeight: 'min-h-40',
    compactMaxHeight: 'max-h-64',
    expandedMinHeight: 'min-h-[28rem]',
    expandedMaxHeight: 'max-h-[38rem]',
  },
  borders: {
    container: 'rounded-lg border border-neutral-300 shadow-sm',
    highlighted: 'rounded-lg border-2 border-primary-300 shadow-md',
  },
  animations: {
    pulse: 'stream-pulse',
    fadeIn: 'stream-fade-in',
  },
} as const

export const streamVariants = {
  default: {
    minHeight: streamDesignTokens.sizing.minHeight,
    maxHeight: streamDesignTokens.sizing.maxHeight,
    showCopyButton: true,
    collapsible: false,
  },
  compact: {
    minHeight: streamDesignTokens.sizing.compactMinHeight,
    maxHeight: streamDesignTokens.sizing.compactMaxHeight,
    showCopyButton: true,
    collapsible: true,
  },
  expanded: {
    minHeight: streamDesignTokens.sizing.expandedMinHeight,
    maxHeight: streamDesignTokens.sizing.expandedMaxHeight,
    showCopyButton: true,
    collapsible: true,
  },
  inline: {
    minHeight: 'min-h-32',
    maxHeight: 'max-h-48',
    showCopyButton: false,
    collapsible: false,
  },
} as const

export type StreamVariant = keyof typeof streamVariants

