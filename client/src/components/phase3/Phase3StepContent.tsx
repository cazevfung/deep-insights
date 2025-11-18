import React from 'react'
import ReactMarkdown from 'react-markdown'
import { Icon } from '../common/Icon'
import {
  Phase3StepContentModel,
  Phase3StepKeyClaim,
} from '../../hooks/usePhase3Steps'

interface Phase3StepContentProps {
  content: Phase3StepContentModel
  confidence?: number | null
}

const baseSectionClass = 'bg-neutral-50 rounded-lg p-4'
const subSectionClass = 'bg-neutral-100 rounded-lg p-4'

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
            <div className="font-medium text-neutral-800 mb-2">
              <ReactMarkdown>{claim.claim}</ReactMarkdown>
            </div>
            {claim.supportingEvidence && (
              <div className="text-sm text-neutral-500">
                <span className="font-medium">论据：</span>
                {/* Render markdown inline to avoid a line break after the label */}
                <ReactMarkdown
                  components={{ p: 'span' }}
                >
                  {(claim.supportingEvidence || '').trim()}
                </ReactMarkdown>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

const AnalysisSection: React.FC<{ content: Phase3StepContentModel['analysis'] }> = ({ content }) => {
  const hasContent =
    content.fiveWhys.length > 0 || content.assumptions.length > 0 || content.uncertainties.length > 0

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
        {!!content.fiveWhys.length && (
          <div className={subSectionClass}>
            <h5 className="font-medium text-neutral-800 mb-3">Five Whys</h5>
            <div className="overflow-x-auto rounded-lg overflow-hidden">
              <table className="w-full border-separate border-spacing-0 bg-white">
                <tbody>
              {content.fiveWhys.map((item, index) => {
                    const isFirst = index === 0
                    const isLast = index === content.fiveWhys.length - 1
                    return (
                    <tr 
                      key={index} 
                      className="hover:bg-neutral-50"
                    >
                      <td className={`py-3 px-3 text-sm text-neutral-700 font-medium align-top whitespace-pre-wrap border-b border-neutral-200 ${
                        isFirst ? 'rounded-tl-lg' : ''
                      } ${isLast ? 'rounded-bl-lg border-b-0' : ''}`}>
                        <ReactMarkdown>{item.question}</ReactMarkdown>
                      </td>
                      <td className={`py-3 px-3 text-sm text-neutral-700 align-top whitespace-pre-wrap border-b border-neutral-200 ${
                        isFirst ? 'rounded-tr-lg' : ''
                      } ${isLast ? 'rounded-br-lg border-b-0' : ''}`}>
                        <ReactMarkdown>{item.answer}</ReactMarkdown>
                      </td>
                    </tr>
              )})}
                </tbody>
              </table>
            </div>
          </div>
        )}
        {!!content.assumptions.length && (
          <div className={subSectionClass}>
            <h5 className="font-medium text-neutral-800 mb-2">本分析有何假设？</h5>
            <ul className="list-disc list-inside space-y-1 text-neutral-700">
              {content.assumptions.map((item, index) => (
                <li key={index} className="whitespace-normal">
                  <ReactMarkdown components={{ p: 'span' }}>
                    {(item || '').trim()}
                  </ReactMarkdown>
                </li>
              ))}
            </ul>
          </div>
        )}
        {!!content.uncertainties.length && (
          <div className={subSectionClass}>
            <h5 className="font-medium text-neutral-800 mb-2">有什么未能确定？</h5>
            <ul className="list-disc list-inside space-y-1 text-neutral-700">
              {content.uncertainties.map((item, index) => (
                <li key={index} className="whitespace-normal">
                  <ReactMarkdown components={{ p: 'span' }}>
                    {(item || '').trim()}
                  </ReactMarkdown>
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
}) => (
  <div className="space-y-6">
    {content.summary && (
      <div className={baseSectionClass}>
        <h4 className="font-semibold text-neutral-800 mb-2 flex items-center">
          <Icon name="edit" size={18} strokeWidth={2} className="mr-2" />
          摘要
        </h4>
        <div className="text-neutral-700 whitespace-pre-wrap">
          <ReactMarkdown>{content.summary}</ReactMarkdown>
        </div>
      </div>
    )}

    <KeyClaims claims={content.keyClaims} />

    {content.article && (
      <div className={baseSectionClass}>
        <h4 className="font-semibold text-neutral-800 mb-2 flex items-center">
          <Icon name="file" size={18} strokeWidth={2} className="mr-2" />
          深度文章
        </h4>
        <div className="text-neutral-700 whitespace-pre-wrap">
          <ReactMarkdown>{content.article}</ReactMarkdown>
        </div>
      </div>
    )}

    <AnalysisSection content={content.analysis} />

    {content.insights && (
      <div className="bg-yellow-50 rounded-lg p-4 border-l-4 border-yellow-500">
        <h4 className="font-semibold text-neutral-800 mb-2 flex items-center">
          <Icon name="lightbulb" size={18} strokeWidth={2} className="mr-2" />
          洞察
        </h4>
        <div className="text-neutral-700 whitespace-pre-wrap">
          <ReactMarkdown>{content.insights}</ReactMarkdown>
        </div>
      </div>
    )}

    {typeof confidence === 'number' && !Number.isNaN(confidence) && (
      <ConfidenceBar confidence={confidence} />
    )}
  </div>
)

export default Phase3StepContent


