import React, { useState, useEffect, useRef } from 'react'

interface ThinkingProcessProps {
  logs: string[]
}

interface ThinkingStep {
  id: string
  title: string
  status: 'active' | 'completed' | 'waiting'
  details: string[]
}

export default function ThinkingProcess({ logs }: ThinkingProcessProps) {
  const [steps, setSteps] = useState<ThinkingStep[]>([])
  const [currentDetail, setCurrentDetail] = useState<string>('')
  const [showHistory, setShowHistory] = useState(false)
  const [pulseText, setPulseText] = useState<string>('')
  const processedLogsRef = useRef<Set<string>>(new Set())
  const stepIdCounter = useRef(0)
  const pulseTexts = ['생각하고 있어요', '정보를 찾고 있어요', '분석 중이에요', '거의 다 됐어요']
  const pulseIndex = useRef(0)

  // 펄스 텍스트 애니메이션
  useEffect(() => {
    const interval = setInterval(() => {
      pulseIndex.current = (pulseIndex.current + 1) % pulseTexts.length
      setPulseText(pulseTexts[pulseIndex.current])
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (logs.length === 0) {
      setSteps([])
      setCurrentDetail('')
      setShowHistory(false)
      processedLogsRef.current.clear()
      stepIdCounter.current = 0
      return
    }

    logs.forEach((log, index) => {
      const logKey = `${index}-${log.substring(0, 100)}`
      if (processedLogsRef.current.has(logKey)) return
      processedLogsRef.current.add(logKey)

      const parsed = parseLog(log)
      if (parsed) {
        if (parsed.type === 'step') {
          const newStepId = `step-${stepIdCounter.current++}`
          setSteps(prev => {
            const updated = prev.map(s => ({ ...s, status: 'completed' as const }))
            return [...updated, {
              id: newStepId,
              title: parsed.title!,
              status: 'active' as const,
              details: parsed.detail ? [parsed.detail] : []
            }]
          })
          if (parsed.detail) setCurrentDetail(parsed.detail)
        } else if (parsed.type === 'detail') {
          setCurrentDetail(parsed.detail!)
          setSteps(prev => {
            if (prev.length === 0) {
              return [{
                id: `step-${stepIdCounter.current++}`,
                title: '분석 중',
                status: 'active' as const,
                details: [parsed.detail!]
              }]
            }
            const updated = [...prev]
            const lastIdx = updated.length - 1
            if (!updated[lastIdx].details.includes(parsed.detail!)) {
              updated[lastIdx].details = [...updated[lastIdx].details, parsed.detail!].slice(-6)
            }
            return updated
          })
        } else if (parsed.type === 'complete') {
          setSteps(prev => prev.map(s => ({ ...s, status: 'completed' as const })))
          setCurrentDetail('답변 준비 완료!')
        }
      }
    })
  }, [logs])

  // 로그 파싱 함수 - 실제 값을 보여줌
  const parseLog = (log: string): { type: 'step' | 'detail' | 'complete', title?: string, detail?: string } | null => {
    if (log.includes('1단계') || log.includes('Orchestration Agent 실행')) {
      return { type: 'step', title: '질문 이해하기', detail: '질문을 분석하고 있어요' }
    }
    
    // 받은 질문 표시 (실제 질문 내용)
    if (log.includes('📝 받은 질문:')) {
      const match = log.match(/📝 받은 질문:\s*"(.+)"/)
      if (match) {
        const question = match[1].trim()
        const shortQ = question.length > 35 ? question.substring(0, 35) + '...' : question
        return { type: 'detail', detail: `"${shortQ}" 분석 중` }
      }
    }
    
    // 키워드 발견 (실제 키워드)
    if (log.includes('키워드 발견:')) {
      const match = log.match(/키워드 발견:\s*(.+)/)
      if (match) {
        const keywords = match[1].trim()
        return { type: 'detail', detail: `키워드: ${keywords}` }
      }
    }
    
    // 성적 정보 감지
    if (log.includes('성적 정보 감지됨')) {
      return { type: 'detail', detail: '성적 정보 발견 → 합격 분석 준비' }
    }
    
    // 답변 전략 수립
    if (log.includes('최적의 답변 전략')) {
      return { type: 'detail', detail: '최적의 답변 전략 수립 중...' }
    }
    
    if (log.includes('질문 분석을 시작') || log.includes('🔍 질문 분석')) {
      return { type: 'detail', detail: '질문의 의도를 파악하고 있어요' }
    }
    
    // 사용자 의도 (실제 의도)
    if (log.includes('사용자 의도') || log.includes('💡 사용자 의도 파악')) {
      const match = log.match(/(?:사용자 의도|💡 사용자 의도 파악):\s*(.+)/)
      if (match) {
        const intent = match[1].trim()
        if (intent && intent !== 'N/A' && intent.length > 3) {
          const shortIntent = intent.length > 40 ? intent.substring(0, 40) + '...' : intent
          return { type: 'detail', detail: `의도 파악: "${shortIntent}"` }
        }
      }
    }
    
    // 실행 계획 (실제 단계 수)
    if (log.includes('실행 계획') && log.includes('step')) {
      const match = log.match(/(\d+)개\s*step/)
      if (match) return { type: 'detail', detail: `${match[1]}단계 실행 계획 완료` }
    }
    
    // 성적 분석 (실제 성적)
    if (log.includes('전처리된 성적 감지') || log.includes('성적 추출')) {
      return { type: 'detail', detail: '입력된 성적을 분석하고 있어요' }
    }
    if (log.includes('인식된 성적') || log.includes('→ 인식된 성적')) {
      const match = log.match(/(?:→\s*)?인식된 성적:\s*(.+)/)
      if (match) {
        const scores = match[1].trim()
        const shortScores = scores.length > 35 ? scores.substring(0, 35) + '...' : scores
        return { type: 'detail', detail: `성적: ${shortScores}` }
      }
    }
    if (log.includes('과목별_성적') || log.includes('파싱된 과목 수')) {
      const match = log.match(/(\d+)개/)
      if (match) return { type: 'detail', detail: `${match[1]}개 과목 성적 인식 완료` }
    }
    if (log.includes('2단계') || log.includes('Sub Agents 실행')) {
      return { type: 'step', title: '정보 수집하기', detail: '관련 정보를 찾고 있어요' }
    }
    
    // 대학별 Agent (더 상세하게)
    if (log.includes('서울대') && (log.includes('Agent') || log.includes('실행'))) {
      return { type: 'detail', detail: '🏫 서울대학교 입시 정보 검색 중' }
    }
    if (log.includes('연세대') && (log.includes('Agent') || log.includes('실행'))) {
      return { type: 'detail', detail: '🏫 연세대학교 입시 정보 검색 중' }
    }
    if (log.includes('고려대') && (log.includes('Agent') || log.includes('실행'))) {
      return { type: 'detail', detail: '🏫 고려대학교 입시 정보 검색 중' }
    }
    if (log.includes('성균관대') && (log.includes('Agent') || log.includes('실행'))) {
      return { type: 'detail', detail: '🏫 성균관대학교 입시 정보 검색 중' }
    }
    if (log.includes('경희대') && (log.includes('Agent') || log.includes('실행'))) {
      return { type: 'detail', detail: '🏫 경희대학교 입시 정보 검색 중' }
    }
    if (log.includes('컨설팅') && (log.includes('Agent') || log.includes('실행'))) {
      return { type: 'step', title: '합격 가능성 분석', detail: '성적 기반으로 분석하고 있어요' }
    }
    if (log.includes('선생님') && (log.includes('Agent') || log.includes('실행'))) {
      return { type: 'detail', detail: '👨‍🏫 맞춤형 학습 조언 준비 중' }
    }
    
    // 점수 계산 (실제 점수 표시)
    if (log.includes('환산 점수 계산 완료')) {
      const match = log.match(/(서울대|연세대|고려대|성균관대|경희대|서강대)/)
      if (match) return { type: 'detail', detail: `📊 ${match[1]} 환산 점수 계산 완료` }
    }
    
    // 실제 점수 값 표시
    if (log.includes('최종점수') || (log.includes('점') && log.includes('/'))) {
      const scoreMatch = log.match(/(\d+(?:\.\d+)?)\s*점/)
      const univMatch = log.match(/(서울대|연세대|고려대|성균관대|경희대|서강대)/)
      if (scoreMatch && univMatch) {
        return { type: 'detail', detail: `📊 ${univMatch[1]}: ${scoreMatch[1]}점` }
      }
    }
    
    // 문서 검색 (실제 쿼리 표시)
    if (log.includes('Query:') || log.includes('📝 Query:')) {
      const match = log.match(/(?:📝\s*)?Query:\s*(.+)/)
      if (match) {
        const query = match[1].trim()
        if (query && query.length > 5) {
          const shortQ = query.length > 30 ? query.substring(0, 30) + '...' : query
          return { type: 'detail', detail: `🔍 "${shortQ}" 검색 중` }
        }
      }
    }
    
    // 문서 발견 (실제 개수)
    if (log.includes('발견된 문서') || log.includes('선별된 문서')) {
      const match = log.match(/(\d+)개/)
      if (match) return { type: 'detail', detail: `📄 관련 자료 ${match[1]}개 발견!` }
    }
    
    if (log.includes('전형결과 조회') || log.includes('입결 데이터 검색')) {
      return { type: 'detail', detail: '📈 과거 입결 데이터 조회 중' }
    }
    
    // 3단계: 답변 작성
    if (log.includes('3단계') || log.includes('Final Agent 실행')) {
      return { type: 'step', title: '답변 작성하기', detail: '수집한 정보를 정리하고 있어요' }
    }
    if (log.includes('답변 생성') || log.includes('최종 답변')) {
      return { type: 'detail', detail: '✍️ 맞춤형 답변 작성 중' }
    }
    if (log.includes('스트리밍') || log.includes('streaming')) {
      return { type: 'detail', detail: '📤 답변 전송 중' }
    }
    
    // 즉시 응답
    if (log.includes('즉시 응답') || log.includes('direct_response')) {
      return { type: 'step', title: '답변 준비 완료', detail: '바로 답변해 드릴게요!' }
    }
    
    // 완료
    if (log.includes('파이프라인 완료') || log.includes('✅ 멀티에이전트 파이프라인 완료')) {
      return { type: 'complete' }
    }
    return null
  }

  const isCompleted = steps.every(s => s.status === 'completed') && steps.length > 0 && currentDetail.includes('완료')
  const activeStep = steps.find(s => s.status === 'active')
  const completedSteps = steps.filter(s => s.status === 'completed')
  const currentStepIndex = steps.findIndex(s => s.status === 'active')

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-100 max-w-[95%] sm:max-w-[85%] overflow-hidden">
      {/* 이전 단계 드롭다운 (완료된 단계가 있을 때만) */}
      {completedSteps.length > 0 && (
        <div className="border-b border-gray-100">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="w-full px-4 py-2 flex items-center justify-between text-xs text-gray-500 hover:bg-gray-50 transition-colors"
          >
            <span className="flex items-center gap-2">
              <span className="flex -space-x-1">
                {completedSteps.slice(0, 3).map((_, i) => (
                  <span key={i} className="w-4 h-4 bg-green-500 rounded-full border-2 border-white flex items-center justify-center">
                    <svg className="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </span>
                ))}
              </span>
              <span>{completedSteps.length}개 단계 완료</span>
            </span>
            <svg 
              className={`w-4 h-4 transition-transform duration-300 ${showHistory ? 'rotate-180' : ''}`}
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {/* 이전 단계 목록 (펼쳐졌을 때) */}
          <div className={`overflow-hidden transition-all duration-400 ease-out ${
            showHistory ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'
          }`}>
            <div className="px-4 py-3 bg-gray-50 space-y-3">
              {completedSteps.map((step, idx) => (
                <div key={step.id} className="animate-slideDown" style={{ animationDelay: `${idx * 80}ms` }}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center">
                      <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    </span>
                    <span className="text-sm font-medium text-green-700">{step.title}</span>
                  </div>
                  <div className="ml-7 space-y-1">
                    {step.details.slice(-3).map((detail, dIdx) => (
                      <div key={dIdx} className="text-xs text-gray-500 flex items-center gap-1.5">
                        <span className="w-1 h-1 bg-gray-300 rounded-full"></span>
                        <span>{detail}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 현재 활성 단계 (메인 표시) */}
      <div className="p-4">
        {activeStep ? (
          <div className="animate-fadeIn">
            {/* 현재 단계 헤더 */}
            <div className="flex items-center gap-3 mb-3">
              <div className="relative">
                <div className="absolute inset-0 bg-blue-400 rounded-full animate-ping opacity-30"></div>
                <div className="relative w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center shadow-lg">
                  <span className="text-white font-bold text-sm">{currentStepIndex + 1}</span>
                </div>
              </div>
              <div className="flex-1">
                <div className="text-base font-semibold text-gray-800">{activeStep.title}</div>
                <div className="text-xs text-gray-500">{pulseText || '진행 중...'}</div>
              </div>
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>

            {/* 현재 작업 내용 (가장 최근 detail) */}
            {activeStep.details.length > 0 && (
              <div className="ml-[52px] mb-3 p-3 bg-blue-50 rounded-lg border border-blue-100 animate-fadeIn">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                  <span className="text-sm text-blue-700 font-medium">
                    {activeStep.details[activeStep.details.length - 1]}
                  </span>
                </div>
              </div>
            )}

            {/* 이전 세부 내용들 (최근 것 제외) */}
            {activeStep.details.length > 1 && (
              <div className="ml-[52px] space-y-1.5">
                {activeStep.details.slice(0, -1).map((detail, idx) => (
                  <div 
                    key={idx}
                    className="text-xs text-gray-400 flex items-center gap-2 animate-slideIn"
                    style={{ animationDelay: `${idx * 60}ms` }}
                  >
                    <span className="w-1 h-1 bg-gray-300 rounded-full flex-shrink-0"></span>
                    <span>{detail}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : isCompleted ? (
          /* 완료 상태 */
          <div className="flex items-center gap-3 animate-fadeIn">
            <div className="w-10 h-10 bg-gradient-to-br from-green-400 to-green-600 rounded-full flex items-center justify-center shadow-lg">
              <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            </div>
            <div>
              <div className="text-base font-semibold text-green-700">분석 완료!</div>
              <div className="text-xs text-green-600">답변이 준비되었어요</div>
            </div>
          </div>
        ) : (
          /* 초기 상태 */
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="absolute inset-0 bg-blue-400 rounded-full animate-ping opacity-30"></div>
              <div className="relative w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center">
                <div className="w-3 h-3 bg-white rounded-full"></div>
              </div>
            </div>
            <div>
              <div className="text-base font-semibold text-gray-800">분석 중</div>
              <div className="text-xs text-blue-600 animate-pulse">질문을 분석하고 있어요...</div>
            </div>
          </div>
        )}
      </div>

      {/* CSS 애니메이션 */}
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: scale(0.95); }
          to { opacity: 1; transform: scale(1); }
        }
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(-12px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes slideDown {
          from { opacity: 0; transform: translateY(-8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn {
          animation: fadeIn 0.4s ease-out;
        }
        .animate-slideIn {
          animation: slideIn 0.3s ease-out forwards;
        }
        .animate-slideDown {
          animation: slideDown 0.3s ease-out forwards;
        }
      `}</style>
    </div>
  )
}
