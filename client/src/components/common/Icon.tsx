import React from 'react'
import {
  Link,
  Download,
  Search,
  BarChart2,
  FileText,
  BookOpen,
  Check,
  X,
  AlertTriangle,
  Info,
  Clock,
  Edit,
  Key,
  Zap,
  RefreshCw,
  Circle,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
} from 'react-feather'

/**
 * Icon name type for type-safe icon usage
 */
export type IconName =
  | 'link'
  | 'download'
  | 'search'
  | 'research'
  | 'chart'
  | 'file'
  | 'book'
  | 'check'
  | 'x'
  | 'warning'
  | 'info'
  | 'clock'
  | 'edit'
  | 'key'
  | 'lightbulb'
  | 'refresh'
  | 'circle'
  | 'check-circle'
  | 'x-circle'
  | 'chevron-down'
  | 'chevron-up'

/**
 * Icon mapping from names to components
 */
const iconMap: Record<IconName, React.ComponentType<any>> = {
  link: Link,
  download: Download,
  search: Search,
  research: Search, // Using Search as alternative for 🔬
  chart: BarChart2,
  file: FileText,
  book: BookOpen,
  check: Check,
  x: X,
  warning: AlertTriangle,
  info: Info,
  clock: Clock,
  edit: Edit,
  key: Key,
  lightbulb: Zap, // Using Zap as alternative for Lightbulb (not available in react-feather)
  refresh: RefreshCw,
  circle: Circle,
  'check-circle': CheckCircle,
  'x-circle': XCircle,
  'chevron-down': ChevronDown,
  'chevron-up': ChevronUp,
}

/**
 * Icon component props
 */
export interface IconProps {
  name: IconName
  size?: number | string
  className?: string
  strokeWidth?: number
  color?: string
}

/**
 * Consistent icon component wrapper for Feather Icons
 * Replaces emoji usage with consistent SVG icons
 */
export const Icon: React.FC<IconProps> = ({
  name,
  size = 20,
  className = '',
  strokeWidth = 2,
  color,
}) => {
  const IconComponent = iconMap[name]
  
  if (!IconComponent) {
    console.warn(`Icon "${name}" not found in iconMap`)
    return null
  }

  const style = color ? { color } : undefined

  return (
    <IconComponent
      size={size}
      className={className}
      strokeWidth={strokeWidth}
      style={style}
    />
  )
}

/**
 * Helper function to get icon component directly (for use in arrays/objects)
 */
export const getIconComponent = (name: IconName): React.ComponentType<any> => {
  return iconMap[name] || iconMap.search // Fallback to search icon
}

