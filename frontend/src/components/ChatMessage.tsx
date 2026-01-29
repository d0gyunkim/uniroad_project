import { useState } from 'react'

interface ChatMessageProps {
  message: string
  isUser: boolean
  sources?: string[]
  source_urls?: string[]  // 다운로드 URL (기존 방식용)
  userQuery?: string  // AI 답변일 때 연결된 사용자 질문
}

export default function ChatMessage({ message, isUser, sources, source_urls, userQuery }: ChatMessageProps) {
  const [showFactCheck, setShowFactCheck] = useState(false)
  
  // ChatGPT에서 같은 질문하기
  const openChatGPT = () => {
    if (userQuery) {
      const encodedQuery = encodeURIComponent(userQuery)
      window.open(`https://chatgpt.com/?q=${encodedQuery}`, '_blank')
    }
  }
  // **텍스트** 형식을 볼드체로 파싱하는 헬퍼 함수
  const parseBold = (text: string | React.ReactNode): React.ReactNode => {
    if (typeof text !== 'string') return text

    const parts: React.ReactNode[] = []
    const boldRegex = /\*\*([^*]+)\*\*/g
    let lastIndex = 0
    let match
    let keyIndex = 0

    while ((match = boldRegex.exec(text)) !== null) {
      // 볼드 이전 텍스트
      if (match.index > lastIndex) {
        parts.push(
          <span key={`text-${keyIndex++}`}>
            {text.substring(lastIndex, match.index)}
          </span>
        )
      }

      // 볼드 부분
      parts.push(
        <strong key={`bold-${keyIndex++}`} className="font-semibold">
          {match[1]}
        </strong>
      )

      lastIndex = boldRegex.lastIndex
    }

    // 마지막 남은 텍스트
    if (lastIndex < text.length) {
      parts.push(
        <span key={`text-${keyIndex++}`}>
          {text.substring(lastIndex)}
        </span>
      )
    }

    return parts.length > 0 ? parts : text
  }

  // 【】로 감싸진 타이틀을 파싱하는 헬퍼 함수
  const parseTitles = (text: string) => {
    const parts: React.ReactNode[] = []
    const titleRegex = /【([^】]+)】/g
    let lastIndex = 0
    let match
    let keyIndex = 0

    while ((match = titleRegex.exec(text)) !== null) {
      // 타이틀 이전 텍스트 (볼드 파싱 적용)
      if (match.index > lastIndex) {
        parts.push(
          <span key={`text-${keyIndex++}`}>
            {parseBold(text.substring(lastIndex, match.index))}
          </span>
        )
      }

      // 타이틀 부분 (18.5px, 볼드, 대괄호 제거)
      parts.push(
        <span key={`title-${keyIndex++}`} className="text-[18.5px] font-bold">
          {match[1]}
        </span>
      )

      lastIndex = titleRegex.lastIndex
    }

    // 마지막 남은 텍스트 (볼드 파싱 적용)
    if (lastIndex < text.length) {
      parts.push(
        <span key={`text-${keyIndex++}`}>
          {parseBold(text.substring(lastIndex))}
        </span>
      )
    }

    return parts.length > 0 ? parts : parseBold(text)
  }

  // <cite> 태그를 파싱해서 희미한 밑줄 + 출처 표시
  const renderMessage = () => {
    if (isUser) {
      return <div className="whitespace-pre-wrap">{message}</div>
    }

    // 1. 섹션 마커 제거 (백엔드에서 처리하지만, 혹시 남아있는 경우 대비)
    let cleanedMessage = message.replace(/===SECTION_(START|END)(:\w+)?===/g, '')
    
    // 연속 줄바꿈 정리
    cleanedMessage = cleanedMessage.replace(/\n{3,}/g, '\n\n').trim()

    // JSON 형식인지 확인 ({ 로 시작하고 } 로 끝남)
    const trimmed = cleanedMessage.trim()
    if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
      try {
        // JSON 파싱 가능한지 확인
        const parsed = JSON.parse(trimmed)
        // 파싱 성공하면 보기 좋게 표시
        const formatted = JSON.stringify(parsed, null, 2)
        return (
          <pre className="whitespace-pre-wrap font-mono text-sm bg-gray-50 p-3 rounded-lg overflow-x-auto">
            {formatted}
          </pre>
        )
      } catch {
        // JSON 아니면 일반 처리
      }
    }

    // 2. 새로운 cite 형식 파싱: <cite data-source="..." data-url="...">...</cite>
    const parts: React.ReactNode[] = []
    let lastIndex = 0
    
    // 새로운 형식: <cite data-source="..." data-url="...">...</cite>
    const newCiteRegex = /<cite\s+data-source="([^"]*)"(?:\s+data-url="([^"]*)")?\s*>([\s\S]*?)<\/cite>/g
    // 기존 형식: <cite>...</cite>
    const oldCiteRegex = /<cite>(.*?)<\/cite>/g
    
    // 새 형식이 있는지 먼저 확인
    const hasNewFormat = newCiteRegex.test(cleanedMessage)
    newCiteRegex.lastIndex = 0 // reset regex
    
    if (hasNewFormat) {
      // 새로운 형식으로 파싱
      let match
      while ((match = newCiteRegex.exec(cleanedMessage)) !== null) {
        // cite 이전 텍스트
        if (match.index > lastIndex) {
          const textBefore = cleanedMessage.substring(lastIndex, match.index)
          parts.push(
            <span key={`text-${lastIndex}`}>
              {parseTitles(textBefore)}
            </span>
          )
        }

        const sourceText = match[1]  // data-source 값 (문서명 + 페이지)
        const sourceUrl = match[2]   // data-url 값 (PDF URL)
        const citedContent = match[3] // 인용 내용

        parts.push(
          <span key={`cite-${match.index}`}>
            <span className={showFactCheck ? "bg-yellow-200/60 px-0.5" : ""}>
              {parseBold(citedContent)}
            </span>
            {showFactCheck && (sourceUrl && sourceUrl.length > 0 ? (
              <a
                href={sourceUrl}
                download
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-1.5 py-0.5 text-[10px] bg-blue-50 text-blue-600 rounded-md whitespace-nowrap hover:bg-blue-100 cursor-pointer transition-colors ml-1"
                title="클릭하면 원본 PDF를 다운로드합니다"
              >
                📄 {sourceText}
              </a>
            ) : sourceText ? (
              <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] bg-blue-50 text-blue-600 rounded-md whitespace-nowrap ml-1">
                📄 {sourceText}
              </span>
            ) : null)}
          </span>
        )

        lastIndex = newCiteRegex.lastIndex
      }

      // 마지막 남은 텍스트
      if (lastIndex < cleanedMessage.length) {
        const remainingText = cleanedMessage.substring(lastIndex)
        parts.push(
          <span key={`text-${lastIndex}`}>
            {parseTitles(remainingText)}
          </span>
        )
      }

      return <div className="whitespace-pre-wrap">{parts.length > 0 ? parts : parseTitles(cleanedMessage)}</div>
    }

    // 기존 형식 처리 (하위 호환성)
    const citeMatches = cleanedMessage.match(oldCiteRegex)
    const citeCount = citeMatches ? citeMatches.length : 0
    const sourcesCount = sources ? sources.length : 0

    // cite 태그와 sources가 매칭되지 않으면 cite 무시하고 일반 텍스트로 표시
    if (citeCount > 0 && sourcesCount === 0) {
      // cite 태그 제거하고 일반 텍스트로
      const finalClean = cleanedMessage.replace(/<\/?cite>/g, '')
      return <div className="whitespace-pre-wrap">{parseTitles(finalClean)}</div>
    }

    // 기존 <cite>...</cite> 패턴 찾기
    let match
    let citeIndex = 0

    while ((match = oldCiteRegex.exec(cleanedMessage)) !== null) {
      // <cite> 이전 텍스트
      if (match.index > lastIndex) {
        const textBefore = cleanedMessage.substring(lastIndex, match.index)
        parts.push(
          <span key={`text-${lastIndex}`}>
            {parseTitles(textBefore)}
          </span>
        )
      }

      // 출처가 있는지 확인
      const sourceText = sources && citeIndex < sources.length ? sources[citeIndex] : null
      const sourceUrl = source_urls && citeIndex < source_urls.length ? source_urls[citeIndex] : null
      
      if (sourceText) {
        // 출처가 있으면 형광펜 + 다운로드 가능한 출처 버블
        parts.push(
          <span key={`cite-${match.index}`}>
            <span className={showFactCheck ? "bg-yellow-200/60 px-0.5" : ""}>
              {parseBold(match[1])}
            </span>
            {showFactCheck && (sourceUrl ? (
              <a
                href={sourceUrl}
                download
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-1.5 py-0.5 text-[10px] bg-blue-50 text-blue-600 rounded-md whitespace-nowrap hover:bg-blue-100 cursor-pointer transition-colors ml-1"
                title="클릭하면 원본 PDF를 다운로드합니다"
              >
                {sourceText}
              </a>
            ) : (
              <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] bg-blue-50 text-blue-600 rounded-md whitespace-nowrap ml-1">
                {sourceText}
              </span>
            ))}
          </span>
        )
      } else {
        // 출처가 없으면 일반 텍스트로
        parts.push(
          <span key={`cite-${match.index}`}>
            {parseTitles(match[1])}
          </span>
        )
      }

      citeIndex++
      lastIndex = oldCiteRegex.lastIndex
    }

    // 마지막 남은 텍스트
    if (lastIndex < cleanedMessage.length) {
      const remainingText = cleanedMessage.substring(lastIndex)
      parts.push(
        <span key={`text-${lastIndex}`}>
          {parseTitles(remainingText)}
        </span>
      )
    }

    return <div className="whitespace-pre-wrap">{parts.length > 0 ? parts : parseTitles(cleanedMessage)}</div>
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      {isUser ? (
        // 사용자 메시지: 말풍선 스타일 유지
        <div className="max-w-[70%] rounded-2xl px-4 py-3 bg-blue-600 text-white">
          {renderMessage()}
        </div>
      ) : (
        // AI 답변: Gemini 스타일 (말풍선 없이, 폰트/간격 조정)
        <div className="w-full">
          <div className="text-gray-900 ai-response mb-4">
            {renderMessage()}
          </div>
          
          {/* 버튼 영역 */}
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => setShowFactCheck(!showFactCheck)}
              className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 border rounded-lg text-sm font-medium transition-all ${
                showFactCheck
                  ? 'border-green-500 bg-green-50 text-green-700 hover:bg-green-100'
                  : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50 hover:border-gray-300'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              팩트체크
            </button>
            
            <button
              onClick={openChatGPT}
              disabled={!userQuery}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 border border-gray-200 bg-white text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 hover:border-gray-300 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              ChatGPT 답변 비교하기
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

