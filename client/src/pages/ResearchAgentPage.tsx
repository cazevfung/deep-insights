import React, { useMemo } from 'react'
import Card from '../components/common/Card'
import { useWorkflowStore, LiveGoal } from '../stores/workflowStore'
import ResearchGoalList from '../components/research/ResearchGoalList'

const ResearchAgentPage: React.FC = () => {
  const researchAgentStatus = useWorkflowStore((state) => state.researchAgentStatus)
  const reportStale = useWorkflowStore((state) => state.reportStale)

  const goalItems = useMemo(() => {
    const orderedIds = researchAgentStatus.goalOrder
    if (orderedIds.length > 0) {
      const liveGoals = orderedIds
        .map((id) => researchAgentStatus.liveGoals[id])
        .filter((goal): goal is NonNullable<typeof goal> => Boolean(goal))
      if (liveGoals.length > 0) {
        return liveGoals
      }
    }

    if (researchAgentStatus.goals && researchAgentStatus.goals.length > 0) {
      return researchAgentStatus.goals.map((goal, index) => ({
        id: goal.id ?? index + 1,
        goal_text: goal.goal_text,
        uses: goal.uses,
        status: 'ready' as LiveGoal['status'],
      }))
    }

    return []
  }, [researchAgentStatus.goalOrder, researchAgentStatus.liveGoals, researchAgentStatus.goals])

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Page Title Section */}
      <div className="pt-8 pb-6">
        <h1 className="text-2xl md:text-3xl font-semibold text-center text-gray-900 leading-relaxed max-w-3xl mx-auto">
          研究规划
        </h1>
      </div>

      <Card className="!rounded-2xl !shadow-lg !border-gray-100">
        <div className="space-y-6">
          {reportStale && (
            <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-2xl p-4 text-sm">
              最终报告基于旧的分析结果，请重新生成阶段 4 以获取最新的综合报告。
            </div>
          )}

          {researchAgentStatus.synthesizedGoal && (
            <div className="bg-primary-50 p-8 rounded-2xl border border-primary-200 shadow-lg">
              <p className="text-2xl text-primary-800 font-semibold leading-relaxed">
                {researchAgentStatus.synthesizedGoal.comprehensive_topic}
              </p>
              {researchAgentStatus.synthesizedGoal.unifying_theme && (
                <p className="text-lg text-primary-700 mt-4 leading-relaxed">
                  <span className="font-semibold text-primary-900">核心主题:</span> {researchAgentStatus.synthesizedGoal.unifying_theme}
                </p>
              )}
            </div>
          )}

          {goalItems.length > 0 && (
            <div className="p-6 rounded-xl bg-gray-50">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-neutral-900 shiny-text-hover">研究目标</h3>
                <span className="text-sm text-neutral-500">一次性浏览所有目标，提升审阅效率</span>
              </div>

              <ResearchGoalList goals={goalItems} />
            </div>
          )}

          {researchAgentStatus.currentAction && (
            <div className="text-sm text-neutral-600 shiny-text-pulse">
              {researchAgentStatus.currentAction}
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}

export default ResearchAgentPage


