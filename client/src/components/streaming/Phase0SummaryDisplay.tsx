import React from 'react'

interface Phase0TranscriptSummary {
  key_facts?: string[]
  key_opinions?: string[]
  key_datapoints?: string[]
  topic_areas?: string[]
  word_count?: number
  total_markers?: number
}

interface Phase0CommentsSummary {
  total_comments?: number
  key_facts_from_comments?: string[]
  key_opinions_from_comments?: string[]
  key_datapoints_from_comments?: string[]
  major_themes?: string[]
  sentiment_overview?: string
  top_engagement_markers?: string[]
  total_markers?: number
}

interface Phase0SummaryDisplayProps {
  data: any
}

const Phase0SummaryDisplay: React.FC<Phase0SummaryDisplayProps> = ({ data }) => {
  if (!data) {
    return <p className="text-sm text-neutral-400">等待摘要数据...</p>
  }

  // Handle nested structure (from backend) or flat structure (from stream)
  // If data has transcript_summary or comments_summary, extract them
  let transcriptData = data
  let commentsData = data
  
  if (data.transcript_summary) {
    transcriptData = data.transcript_summary
  }
  if (data.comments_summary) {
    commentsData = data.comments_summary
  }
  
  // If summary_type is in metadata, use that to determine which data to use
  // For transcript summaries, data will have key_facts, key_opinions, etc.
  // For comments summaries, data will have key_facts_from_comments, etc.
  const summaryType = data.summary_type || data.type
  
  // Check if this is transcript summary
  const isTranscriptSummary = 
    summaryType === 'transcript' ||
    transcriptData.key_facts || 
    transcriptData.key_opinions || 
    transcriptData.key_datapoints || 
    transcriptData.topic_areas

  // Check if this is comments summary
  const isCommentsSummary = 
    summaryType === 'comments' ||
    commentsData.key_facts_from_comments || 
    commentsData.key_opinions_from_comments || 
    commentsData.major_themes

  if (!isTranscriptSummary && !isCommentsSummary) {
    // Not a Phase 0 summary, return null to show default JSON view
    return null
  }
  
  // Use the appropriate data based on what we detected
  const displayData = isTranscriptSummary ? transcriptData : commentsData

  return (
    <div className="space-y-4 text-sm">
      {/* Transcript Summary */}
      {isTranscriptSummary && (
        <div className="space-y-3">
          <div className="flex items-baseline justify-between border-b border-neutral-200 pb-2">
            <h4 className="font-semibold text-neutral-800">转录摘要</h4>
            {displayData.word_count && (
              <span className="text-xs text-neutral-500">{displayData.word_count} 字</span>
            )}
          </div>

          {displayData.key_facts && displayData.key_facts.length > 0 && (
            <div>
              <h5 className="font-medium text-neutral-700 mb-2">关键事实 ({displayData.key_facts.length})</h5>
              <ul className="list-disc list-inside space-y-1 text-neutral-600 pl-2">
                {displayData.key_facts.map((fact: string, idx: number) => (
                  <li key={idx} className="leading-relaxed">{fact}</li>
                ))}
              </ul>
            </div>
          )}

          {displayData.key_opinions && displayData.key_opinions.length > 0 && (
            <div>
              <h5 className="font-medium text-neutral-700 mb-2">关键观点 ({displayData.key_opinions.length})</h5>
              <ul className="list-disc list-inside space-y-1 text-neutral-600 pl-2">
                {displayData.key_opinions.map((opinion: string, idx: number) => (
                  <li key={idx} className="leading-relaxed">{opinion}</li>
                ))}
              </ul>
            </div>
          )}

          {displayData.key_datapoints && displayData.key_datapoints.length > 0 && (
            <div>
              <h5 className="font-medium text-neutral-700 mb-2">关键数据 ({displayData.key_datapoints.length})</h5>
              <ul className="list-disc list-inside space-y-1 text-neutral-600 pl-2">
                {displayData.key_datapoints.map((datapoint: string, idx: number) => (
                  <li key={idx} className="leading-relaxed">{datapoint}</li>
                ))}
              </ul>
            </div>
          )}

          {displayData.topic_areas && displayData.topic_areas.length > 0 && (
            <div>
              <h5 className="font-medium text-neutral-700 mb-2">主题领域 ({displayData.topic_areas.length})</h5>
              <div className="flex flex-wrap gap-2">
                {displayData.topic_areas.map((topic: string, idx: number) => (
                  <span 
                    key={idx} 
                    className="px-2 py-1 bg-primary-50 text-primary-700 rounded-md text-xs font-medium"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            </div>
          )}

          {displayData.total_markers !== undefined && (
            <div className="text-xs text-neutral-500 pt-2 border-t border-neutral-200">
              共 {displayData.total_markers} 个标记
            </div>
          )}
        </div>
      )}

      {/* Comments Summary */}
      {isCommentsSummary && (
        <div className="space-y-3">
          <div className="flex items-baseline justify-between border-b border-neutral-200 pb-2">
            <h4 className="font-semibold text-neutral-800">评论摘要</h4>
            {displayData.total_comments && (
              <span className="text-xs text-neutral-500">{displayData.total_comments} 条评论</span>
            )}
          </div>

          {displayData.sentiment_overview && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-neutral-600">整体情感:</span>
              <span className={`text-xs px-2 py-1 rounded ${
                displayData.sentiment_overview === 'mostly_positive' 
                  ? 'bg-green-50 text-green-700'
                  : displayData.sentiment_overview === 'mostly_negative'
                  ? 'bg-red-50 text-red-700'
                  : 'bg-neutral-100 text-neutral-600'
              }`}>
                {displayData.sentiment_overview === 'mostly_positive' ? '积极' : 
                 displayData.sentiment_overview === 'mostly_negative' ? '消极' : '混合'}
              </span>
            </div>
          )}

          {displayData.major_themes && displayData.major_themes.length > 0 && (
            <div>
              <h5 className="font-medium text-neutral-700 mb-2">主要主题 ({displayData.major_themes.length})</h5>
              <div className="flex flex-wrap gap-2">
                {displayData.major_themes.map((theme: string, idx: number) => (
                  <span 
                    key={idx} 
                    className="px-2 py-1 bg-purple-50 text-purple-700 rounded-md text-xs font-medium"
                  >
                    {theme}
                  </span>
                ))}
              </div>
            </div>
          )}

          {displayData.key_facts_from_comments && displayData.key_facts_from_comments.length > 0 && (
            <div>
              <h5 className="font-medium text-neutral-700 mb-2">评论中的事实 ({displayData.key_facts_from_comments.length})</h5>
              <ul className="list-disc list-inside space-y-1 text-neutral-600 pl-2">
                {displayData.key_facts_from_comments.map((fact: string, idx: number) => (
                  <li key={idx} className="leading-relaxed">{fact}</li>
                ))}
              </ul>
            </div>
          )}

          {displayData.key_opinions_from_comments && displayData.key_opinions_from_comments.length > 0 && (
            <div>
              <h5 className="font-medium text-neutral-700 mb-2">评论中的观点 ({displayData.key_opinions_from_comments.length})</h5>
              <ul className="list-disc list-inside space-y-1 text-neutral-600 pl-2">
                {displayData.key_opinions_from_comments.map((opinion: string, idx: number) => (
                  <li key={idx} className="leading-relaxed">{opinion}</li>
                ))}
              </ul>
            </div>
          )}

          {displayData.key_datapoints_from_comments && displayData.key_datapoints_from_comments.length > 0 && (
            <div>
              <h5 className="font-medium text-neutral-700 mb-2">评论中的数据 ({displayData.key_datapoints_from_comments.length})</h5>
              <ul className="list-disc list-inside space-y-1 text-neutral-600 pl-2">
                {displayData.key_datapoints_from_comments.map((datapoint: string, idx: number) => (
                  <li key={idx} className="leading-relaxed">{datapoint}</li>
                ))}
              </ul>
            </div>
          )}

          {displayData.top_engagement_markers && displayData.top_engagement_markers.length > 0 && (
            <div>
              <h5 className="font-medium text-neutral-700 mb-2">高参与度标记 ({displayData.top_engagement_markers.length})</h5>
              <ul className="list-disc list-inside space-y-1 text-neutral-600 pl-2">
                {displayData.top_engagement_markers.map((marker: string, idx: number) => (
                  <li key={idx} className="leading-relaxed">{marker}</li>
                ))}
              </ul>
            </div>
          )}

          {displayData.total_markers !== undefined && (
            <div className="text-xs text-neutral-500 pt-2 border-t border-neutral-200">
              共 {displayData.total_markers} 个标记
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default Phase0SummaryDisplay

