import React from 'react'
import { Icon } from '../common/Icon'
import {
  Phase3StepContentModel,
  Phase3StepEvidence,
  Phase3StepKeyClaim,
} from '../../hooks/usePhase3Steps'

interface Phase3StepContentProps {
  content: Phase3StepContentModel
  confidence?: number | null
  showRawData: boolean
  onToggleRawData: () => void
  rawStep?: unknown
}

const baseSectionClass = 'bg-neutral-50 rounded-lg p-4'
const subSectionClass = 'bg-neutral-100 rounded-lg p-4'

const renderFormattedText = (text: string) => {
  const nodes: React.ReactNode[] = []
  const tokens = text.split(/(\*\*[^*]+\*\*)/g)

  tokens.forEach((token, tokenIndex) => {
    if (!token) {
      return
    }

    const isBoldToken = token.startsWith('**') && token.endsWith('**') && token.length > 4

    if (isBoldToken) {
      nodes.push(
        <strong key={`bold-${tokenIndex}`} className="font-semibold text-neutral-900">
          {token.slice(2, -2)}
        </strong>,
      )
      return
    }

    const lines = token.split('\n')
    lines.forEach((line, lineIndex) => {
      nodes.push(
        <React.Fragment key={`text-${tokenIndex}-${lineIndex}`}>
          {line}
          {lineIndex < lines.length - 1 && <br />}
        </React.Fragment>,
      )
    })
  })

  return nodes
}

const ConfidenceBar: React.FC<{ confidence: number }> = ({ confidence }) => {
  const getConfidenceColor = () => {
    if (confidence >= 0.8) {
      return 'bg-green-500'
    }
    if (confidence >= 0.6) {
      return 'bg-yellow-500'
    }
    return 'bg-red-500'
  }

  return (
    <div className="flex items-center space-x-4">
      <span className="font-medium text-neutral-700">可信度：</span>
      <div className="flex-1 bg-neutral-200 rounded-full h-2.5">
        <div className={`h-2.5 rounded-full ${getConfidenceColor()}`} style={{ width: `${confidence * 100}%` }} />
      </div>
      <span className="text-sm font-medium text-neutral-700">{(confidence * 100).toFixed(1)}%</span>
    </div>
  )
}

const KeyClaims: React.FC<{ claims: Phase3StepKeyClaim[] }> = ({ claims }) => {
  if (!claims.length) {
    return null
  }

  return (
    <div className={baseSectionClass}>
      <h4 className="font-semibold text-neutral-800 mb-3 flex items-center">
        <Icon name="key" size={18} strokeWidth={2} className="mr-2" />
        主要观点
      </h4>
      <div className="space-y-3">
        {claims.map((claim, index) => (
          <div key={index} className="bg-white rounded-lg p-4 border border-neutral-200">
            <div className="font-medium text-neutral-800 mb-2 whitespace-pre-wrap">
              {renderFormattedText(claim.claim)}
            </div>
            {claim.supportingEvidence && (
              <div className="text-sm text-neutral-600 mt-2">
                <span className="font-medium">证据支持：</span>
                <span className="whitespace-pre-wrap">
                  {renderFormattedText(claim.supportingEvidence)}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

const NotableEvidence: React.FC<{ evidence?: Phase3StepEvidence[] }> = ({ evidence }) => {
  if (!evidence || evidence.length === 0) {
    return null
  }

  return (
    <div className={baseSectionClass}>
      <h4 className="font-semibold text-neutral-800 mb-3 flex items-center">
        <Icon name="chart" size={18} strokeWidth={2} className="mr-2" />
        重要发现
      </h4>
      <div className="space-y-3">
        {evidence.map((item, index) => (
          <div key={index} className="bg-white rounded-lg p-4 border border-neutral-200">
            <div className="flex items-start">
              <span className="inline-block bg-yellow-100 text-yellow-800 text-xs font-medium px-2.5 py-0.5 rounded mr-3 mt-1">
                {item.evidenceType || `发现 ${index + 1}`}
              </span>
              <p className="text-neutral-700 flex-1 whitespace-pre-wrap">
                {renderFormattedText(item.description)}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

const AnalysisSection: React.FC<{ content?: Phase3StepContentModel['analysis'] }> = ({ content }) => {
  if (!content) {
    return null
  }

  const hasContent =
    (content.fiveWhys?.length ?? 0) > 0 ||
    (content.assumptions?.length ?? 0) > 0 ||
    (content.uncertainties?.length ?? 0) > 0

  if (!hasContent) {
    return null
  }

  return (
    <div className={baseSectionClass}>
      <h4 className="font-semibold text-neutral-800 mb-3 flex items-center">
        <Icon name="search" size={18} strokeWidth={2} className="mr-2" />
        Q&A
      </h4>
      <div className="space-y-4">
        {!!content.fiveWhys?.length && (
          <div className={subSectionClass}>
            <h5 className="font-medium text-neutral-800 mb-2">Five Whys</h5>
            <ul className="space-y-3">
              {content.fiveWhys?.map((item, index) => (
                <li key={`${item.level ?? index}-${index}`} className="bg-white rounded-lg p-3 border border-neutral-200">
                  <div className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">
                    第 {item.level ?? index + 1} 轮
                  </div>
                  {item.question && (
                    <p className="text-sm font-medium text-neutral-800 whitespace-pre-wrap mb-1">
                      Q：{renderFormattedText(item.question)}
                    </p>
                  )}
                  {item.answer && (
                    <p className="text-sm text-neutral-700 whitespace-pre-wrap">
                      A：{renderFormattedText(item.answer)}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
        {!!content.assumptions?.length && (
          <div className={subSectionClass}>
            <h5 className="font-medium text-neutral-800 mb-2">本分析有何假设？</h5>
            <ul className="list-disc list-inside space-y-1 text-neutral-700">
              {content.assumptions?.map((item, index) => (
                <li key={index} className="whitespace-pre-wrap">
                  {renderFormattedText(item)}
                </li>
              ))}
            </ul>
          </div>
        )}
        {!!content.uncertainties?.length && (
          <div className={subSectionClass}>
            <h5 className="font-medium text-neutral-800 mb-2">有什么未能确定？</h5>
            <ul className="list-disc list-inside space-y-1 text-neutral-700">
              {content.uncertainties?.map((item, index) => (
                <li key={index} className="whitespace-pre-wrap">
                  {renderFormattedText(item)}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}

const Phase3StepContent: React.FC<Phase3StepContentProps> = ({
  content,
  confidence,
  showRawData,
  onToggleRawData,
  rawStep,
}) => (
  <div className="space-y-6">
    {content.summary && (
      <div className={baseSectionClass}>
        <h4 className="font-semibold text-neutral-800 mb-2 flex items-center">
          <Icon name="edit" size={18} strokeWidth={2} className="mr-2" />
          摘要
        </h4>
        <p className="text-neutral-700 whitespace-pre-wrap">{renderFormattedText(content.summary)}</p>
      </div>
    )}

    <KeyClaims claims={content.keyClaims} />
    <NotableEvidence evidence={content.notableEvidence} />

    {content.article && (
      <div className={baseSectionClass}>
        <h4 className="font-semibold text-neutral-800 mb-2 flex items-center">
          <Icon name="file" size={18} strokeWidth={2} className="mr-2" />
          深度文章
        </h4>
        <p className="text-neutral-700 whitespace-pre-wrap">{renderFormattedText(content.article)}</p>
      </div>
    )}

    <AnalysisSection content={content.analysis} />

    {content.insights && (
      <div className="bg-yellow-50 rounded-lg p-4 border-l-4 border-yellow-500">
        <h4 className="font-semibold text-neutral-800 mb-2 flex items-center">
          <Icon name="lightbulb" size={18} strokeWidth={2} className="mr-2" />
          洞察
        </h4>
        <p className="text-neutral-700 whitespace-pre-wrap">{renderFormattedText(content.insights)}</p>
      </div>
    )}

    {typeof confidence === 'number' && !Number.isNaN(confidence) && (
      <ConfidenceBar confidence={confidence} />
    )}

    {rawStep !== undefined && rawStep !== null && (
      <div className="border-t pt-4">
        <button
          onClick={onToggleRawData}
          className="text-sm text-neutral-500 hover:text-neutral-700 flex items-center"
        >
          <span className="mr-2">{showRawData ? '▼' : '▶'}</span>
          {showRawData ? '收起原始数据' : '查看原始数据'}
        </button>
        {showRawData && (
          <pre className="mt-2 text-xs bg-neutral-100 p-4 rounded overflow-auto max-h-96 border">
            {JSON.stringify(rawStep, null, 2)}
          </pre>
        )}
      </div>
    )}
  </div>
)

export default Phase3StepContent


