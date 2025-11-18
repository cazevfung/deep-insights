import React from 'react'
import { JSONTree } from 'react-json-tree'
import { useStreamParser } from '../../hooks/useStreamParser'
import { useWorkflowStore } from '../../stores/workflowStore'
import Phase0SummaryDisplay from './Phase0SummaryDisplay'

const jsonTheme = {
  base00: '#FFFFFF',
  base01: '#F8F7F9',
  base02: '#DFE7EC',
  base03: '#9EB7C7',
  base04: '#5D87A1',
  base05: '#031C34',
  base06: '#031C34',
  base07: '#031C34',
  base08: '#AF2A47',
  base09: '#D4A03D',
  base0A: '#FEC74A',
  base0B: '#2FB66A',
  base0C: '#00B7F1',
  base0D: '#7592C1',
  base0E: '#B37AB5',
  base0F: '#E9853C',
}

interface StreamStructuredViewProps {
  enableRepair?: boolean
  emptyMessage?: string
  streamId?: string
}

const StreamStructuredView: React.FC<StreamStructuredViewProps> = ({
  enableRepair = true,
  emptyMessage = '等待完整 JSON…',
  streamId,
}) => {
  // Get real-time JSON data from store if available
  const researchAgentStatus = useWorkflowStore((state) => state.researchAgentStatus)
  const resolvedStreamId = streamId ?? researchAgentStatus.streams.activeStreamId ?? researchAgentStatus.streams.order[0] ?? null
  const streamBuffer = resolvedStreamId
    ? researchAgentStatus.streams.buffers[resolvedStreamId]
    : null
  
  // Prefer real-time JSON data over parsed raw content
  const realTimeJsonData = streamBuffer?.jsonData
  const isJsonComplete = streamBuffer?.jsonComplete ?? false
  
  // Fallback to parser if no real-time JSON data
  const { root: parsedRoot, status, error } = useStreamParser({ enableRepair, streamId })
  
  // Use real-time JSON data if available, otherwise use parsed root
  const root = realTimeJsonData ?? parsedRoot

  // Show error only if we don't have real-time JSON data
  if (!realTimeJsonData && status === 'error') {
    return <p className="text-xs text-supportive-orange">解析失败: {error}</p>
  }

  // Show loading/empty message if no data available
  if (!root) {
    const loadingMessage = realTimeJsonData ? '正在解析 JSON…' : emptyMessage
    return <p className="text-sm text-neutral-400">{loadingMessage}</p>
  }
  
  // Show indicator if JSON is not complete yet
  const showIncompleteIndicator = realTimeJsonData && !isJsonComplete

  // Check if this is Phase 0 summary data
  // Handle both flat structure (from stream) and nested structure (from backend)
  const transcriptSummary = root.transcript_summary || root
  const commentsSummary = root.comments_summary || root
  const summaryType = root.summary_type || root.type
  
  const isPhase0Summary = 
    summaryType === 'transcript' ||
    summaryType === 'comments' ||
    transcriptSummary.key_facts || 
    transcriptSummary.key_opinions || 
    transcriptSummary.key_datapoints || 
    transcriptSummary.topic_areas ||
    commentsSummary.key_facts_from_comments || 
    commentsSummary.key_opinions_from_comments || 
    commentsSummary.major_themes

  // Render specialized Phase 0 display if detected
  if (isPhase0Summary) {
    // Pass the appropriate data based on structure
    // Phase0SummaryDisplay will handle both nested and flat structures
    return (
      <div className="stream-structured-view p-4">
        {showIncompleteIndicator && (
          <div className="mb-2 rounded-md bg-yellow-50 px-3 py-2 text-xs text-yellow-800">
            ⏳ JSON 解析中（部分数据）
          </div>
        )}
        <Phase0SummaryDisplay data={root} />
      </div>
    )
  }

  // Fallback to JSON tree display for other phases
  return (
    <div className="stream-structured-view">
      {showIncompleteIndicator && (
        <div className="mb-2 rounded-md bg-yellow-50 px-3 py-2 text-xs text-yellow-800">
          ⏳ JSON 解析中（部分数据）
        </div>
      )}
      <JSONTree
        data={root}
        theme={jsonTheme}
        invertTheme={false}
        hideRoot={false}
        shouldExpandNodeInitially={(_keyPath, _data, level) => level < 2}
      />
    </div>
  )
}

export default StreamStructuredView
