import React, { useState, useEffect, useRef } from 'react'
import { Icon } from '../common/Icon'
import LinkProgressItem from './LinkProgressItem'
import { GroupedItems, getItemId } from '../../utils/progressUtils'

interface ProgressGroupProps {
  group: GroupedItems
  newItemIds: Set<string>
  onItemAnimationComplete: (itemId: string) => void
}

const ProgressGroup: React.FC<ProgressGroupProps> = ({
  group,
  newItemIds,
  onItemAnimationComplete,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(group.defaultCollapsed)
  const [visibleNewItems, setVisibleNewItems] = useState<Set<string>>(new Set())
  const processedItemsRef = useRef<Set<string>>(new Set())

  // Track new items and mark them for animation
  useEffect(() => {
    const newItems = group.items.filter((item) => {
      const itemId = getItemId(item)
      return newItemIds.has(itemId) && !processedItemsRef.current.has(itemId)
    })

    if (newItems.length === 0) return

    const timeouts: number[] = []

    // Add new items to visible set with staggered timing
    newItems.forEach((item, index) => {
      const itemId = getItemId(item)
      const timeout1 = window.setTimeout(() => {
        setVisibleNewItems((prev) => {
          const updated = new Set(prev)
          updated.add(itemId)
          return updated
        })
        processedItemsRef.current.add(itemId)

        // Remove highlight after animation completes
        const timeout2 = window.setTimeout(() => {
          setVisibleNewItems((prev) => {
            const updated = new Set(prev)
            updated.delete(itemId)
            return updated
          })
          // Call parent callback after state update (deferred to avoid render-phase update)
          setTimeout(() => {
            onItemAnimationComplete(itemId)
          }, 0)
        }, 2000) // Remove highlight after 2 seconds
        timeouts.push(timeout2)
      }, index * 80) // Stagger by 80ms
      timeouts.push(timeout1)
    })

    return () => {
      timeouts.forEach((timeout) => clearTimeout(timeout))
    }
  }, [group.items, newItemIds, onItemAnimationComplete])

  const toggleCollapse = () => {
    setIsCollapsed(!isCollapsed)
  }

  const getIconComponent = () => {
    switch (group.icon) {
      case 'refresh':
        return <Icon name="refresh" size={18} strokeWidth={2.5} className="text-primary-400 animate-spin" />
      case 'clock':
        return <Icon name="clock" size={18} strokeWidth={2.5} className="text-neutral-400" />
      case 'check-circle':
        return <Icon name="check-circle" size={18} strokeWidth={2.5} className="text-supportive-green" />
      case 'x-circle':
        return <Icon name="x-circle" size={18} strokeWidth={2.5} className="text-secondary-500" />
      default:
        return <Icon name="circle" size={18} strokeWidth={2.5} className="text-neutral-400" />
    }
  }

  return (
    <div className="border border-neutral-border rounded-lg overflow-hidden">
      {/* Group Header */}
      <button
        onClick={toggleCollapse}
        className="w-full flex items-center justify-between px-4 py-3 bg-neutral-light-bg hover:bg-neutral-hover-bg transition-colors cursor-pointer"
      >
        <div className="flex items-center space-x-2">
          {getIconComponent()}
          <span className="font-semibold text-neutral-black">{group.label}</span>
          <span className="text-sm text-neutral-secondary">({group.items.length})</span>
        </div>
        <Icon
          name={isCollapsed ? 'chevron-down' : 'chevron-up'}
          size={18}
          strokeWidth={2.5}
          className="text-neutral-secondary"
        />
      </button>

      {/* Group Items */}
      {!isCollapsed && (
        <div className="space-y-2 p-3 bg-white">
          {group.items.map((item, index) => {
            const itemId = getItemId(item)
            const isNew = visibleNewItems.has(itemId)

            return (
              <div
                key={itemId || index}
                className={isNew ? 'new-item-animate' : ''}
              >
                <LinkProgressItem item={item} isNew={isNew} />
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default ProgressGroup
