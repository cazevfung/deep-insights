import React from 'react'
import { JSONTree } from 'react-json-tree'
import { useStreamParser } from '../../hooks/useStreamParser'
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
  const { root, status, error } = useStreamParser({ enableRepair, streamId })

  if (status === 'error') {
    return <p className="text-xs text-supportive-orange">解析失败: {error}</p>
  }

  if (status !== 'valid' || !root) {
    return <p className="text-sm text-neutral-400">{emptyMessage}</p>
  }

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
        <Phase0SummaryDisplay data={root} />
      </div>
    )
  }

  // Fallback to JSON tree display for other phases
  return (
    <div className="stream-structured-view">
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
