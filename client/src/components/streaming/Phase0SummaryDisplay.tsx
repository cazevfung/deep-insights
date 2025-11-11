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

  // Check if this is transcript summary
  const isTranscriptSummary = 
    data.key_facts || data.key_opinions || data.key_datapoints || data.topic_areas

  // Check if this is comments summary
  const isCommentsSummary = 
    data.key_facts_from_comments || data.key_opinions_from_comments || data.major_themes

  if (!isTranscriptSummary && !isCommentsSummary) {
    // Not a Phase 0 summary, return null to show default JSON view
    return null
  }

  return (
    <div className="space-y-4 text-sm">
      {/* Transcript Summary */}
      {isTranscriptSummary && (
        <div className="space-y-3">
          <div className="flex items-baseline justify-between border-b border-neutral-200 pb-2">
            <h4 className="font-semibold text-neutral-800">转录摘要</h4>
            {data.word_count && (
              <span className="text-xs text-neutral-500">{data.word_count} 字</span>
            )}
          </div>

          {data.key_facts && data.key_facts.length > 0 && (
            <div>
              <h5 className="font-medium text-neutral-700 mb-2">关键事实 ({data.key_facts.length})</h5>
              <ul className="list-disc list-inside space-y-1 text-neutral-600 pl-2">
                {data.key_facts.map((fact: string, idx: number) => (
                  <li key={idx} className="leading-relaxed">{fact}</li>
                ))}
              </ul>
            </div>
          )}

          {data.key_opinions && data.key_opinions.length > 0 && (
            <div>
              <h5 className="font-medium text-neutral-700 mb-2">关键观点 ({data.key_opinions.length})</h5>
              <ul className="list-disc list-inside space-y-1 text-neutral-600 pl-2">
                {data.key_opinions.map((opinion: string, idx: number) => (
                  <li key={idx} className="leading-relaxed">{opinion}</li>
                ))}
              </ul>
            </div>
          )}

          {data.key_datapoints && data.key_datapoints.length > 0 && (
            <div>
              <h5 className="font-medium text-neutral-700 mb-2">关键数据 ({data.key_datapoints.length})</h5>
              <ul className="list-disc list-inside space-y-1 text-neutral-600 pl-2">
                {data.key_datapoints.map((datapoint: string, idx: number) => (
                  <li key={idx} className="leading-relaxed">{datapoint}</li>
                ))}
              </ul>
            </div>
          )}

          {data.topic_areas && data.topic_areas.length > 0 && (
            <div>
              <h5 className="font-medium text-neutral-700 mb-2">主题领域 ({data.topic_areas.length})</h5>
              <div className="flex flex-wrap gap-2">
                {data.topic_areas.map((topic: string, idx: number) => (
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

          {data.total_markers !== undefined && (
            <div className="text-xs text-neutral-500 pt-2 border-t border-neutral-200">
              共 {data.total_markers} 个标记
            </div>
          )}
        </div>
      )}

      {/* Comments Summary */}
      {isCommentsSummary && (
        <div className="space-y-3">
          <div className="flex items-baseline justify-between border-b border-neutral-200 pb-2">
            <h4 className="font-semibold text-neutral-800">评论摘要</h4>
            {data.total_comments && (
              <span className="text-xs text-neutral-500">{data.total_comments} 条评论</span>
            )}
          </div>

          {data.sentiment_overview && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-neutral-600">整体情感:</span>
              <span className={`text-xs px-2 py-1 rounded ${
                data.sentiment_overview === 'mostly_positive' 
                  ? 'bg-green-50 text-green-700'
                  : data.sentiment_overview === 'mostly_negative'
                  ? 'bg-red-50 text-red-700'
                  : 'bg-neutral-100 text-neutral-600'
              }`}>
                {data.sentiment_overview === 'mostly_positive' ? '积极' : 
                 data.sentiment_overview === 'mostly_negative' ? '消极' : '混合'}
              </span>
            </div>
          )}

          {data.major_themes && data.major_themes.length > 0 && (
            <div>
              <h5 className="font-medium text-neutral-700 mb-2">主要主题 ({data.major_themes.length})</h5>
              <div className="flex flex-wrap gap-2">
                {data.major_themes.map((theme: string, idx: number) => (
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

          {data.key_facts_from_comments && data.key_facts_from_comments.length > 0 && (
            <div>
              <h5 className="font-medium text-neutral-700 mb-2">评论中的事实 ({data.key_facts_from_comments.length})</h5>
              <ul className="list-disc list-inside space-y-1 text-neutral-600 pl-2">
                {data.key_facts_from_comments.map((fact: string, idx: number) => (
                  <li key={idx} className="leading-relaxed">{fact}</li>
                ))}
              </ul>
            </div>
          )}

          {data.key_opinions_from_comments && data.key_opinions_from_comments.length > 0 && (
            <div>
              <h5 className="font-medium text-neutral-700 mb-2">评论中的观点 ({data.key_opinions_from_comments.length})</h5>
              <ul className="list-disc list-inside space-y-1 text-neutral-600 pl-2">
                {data.key_opinions_from_comments.map((opinion: string, idx: number) => (
                  <li key={idx} className="leading-relaxed">{opinion}</li>
                ))}
              </ul>
            </div>
          )}

          {data.key_datapoints_from_comments && data.key_datapoints_from_comments.length > 0 && (
            <div>
              <h5 className="font-medium text-neutral-700 mb-2">评论中的数据 ({data.key_datapoints_from_comments.length})</h5>
              <ul className="list-disc list-inside space-y-1 text-neutral-600 pl-2">
                {data.key_datapoints_from_comments.map((datapoint: string, idx: number) => (
                  <li key={idx} className="leading-relaxed">{datapoint}</li>
                ))}
              </ul>
            </div>
          )}

          {data.top_engagement_markers && data.top_engagement_markers.length > 0 && (
            <div>
              <h5 className="font-medium text-neutral-700 mb-2">高参与度标记 ({data.top_engagement_markers.length})</h5>
              <ul className="list-disc list-inside space-y-1 text-neutral-600 pl-2">
                {data.top_engagement_markers.map((marker: string, idx: number) => (
                  <li key={idx} className="leading-relaxed">{marker}</li>
                ))}
              </ul>
            </div>
          )}

          {data.total_markers !== undefined && (
            <div className="text-xs text-neutral-500 pt-2 border-t border-neutral-200">
              共 {data.total_markers} 个标记
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default Phase0SummaryDisplay

