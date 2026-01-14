import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadDocument, getDocuments, deleteDocument, updateDocument, Document } from '../api/client'

export default function AdminPage() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState('')
  const [documents, setDocuments] = useState<Document[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [editSource, setEditSource] = useState('')
  const [selectedHashtags, setSelectedHashtags] = useState<string[]>([])
  
  // 모든 문서에서 고유 해시태그 추출
  const allHashtags = Array.from(
    new Set(documents.flatMap((doc) => doc.hashtags || []))
  ).sort()
  
  // 필터링된 문서
  const filteredDocuments = selectedHashtags.length === 0
    ? documents
    : documents.filter((doc) =>
        selectedHashtags.some((tag) => doc.hashtags?.includes(tag))
      )

  useEffect(() => {
    loadDocuments()
  }, [])

  const loadDocuments = async () => {
    try {
      const docs = await getDocuments()
      setDocuments(docs)
    } catch (error) {
      console.error('문서 목록 로드 오류:', error)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile && droppedFile.type === 'application/pdf') {
      setFile(droppedFile)
    } else {
      alert('PDF 파일만 업로드 가능합니다.')
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file) {
      alert('파일을 선택해주세요.')
      return
    }

    setIsUploading(true)
    setUploadStatus('⏳ 업로드 중... (제목과 출처는 자동 추출됩니다)')

    try {
      const result = await uploadDocument(file)
      setUploadStatus(`✅ 업로드 완료! (${result.stats.processingTime})`)
      
      // 폼 초기화
      setFile(null)
      
      // 문서 목록 새로고침
      await loadDocuments()
      
      // 3초 후 상태 메시지 제거
      setTimeout(() => setUploadStatus(''), 3000)
    } catch (error: any) {
      console.error('업로드 오류:', error)
      setUploadStatus(`❌ 업로드 실패: ${error.response?.data?.detail || error.message}`)
    } finally {
      setIsUploading(false)
    }
  }

  const handleEdit = (doc: Document) => {
    setEditingId(doc.id)
    setEditTitle(doc.title)
    setEditSource(doc.source)
  }

  const handleSaveEdit = async (id: string) => {
    try {
      await updateDocument(id, editTitle, editSource)
      setEditingId(null)
      await loadDocuments()
    } catch (error) {
      console.error('수정 오류:', error)
      alert('수정에 실패했습니다.')
    }
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setEditTitle('')
    setEditSource('')
  }

  const handleDelete = async (id: string) => {
    if (!confirm('정말 삭제하시겠습니까?')) return

    try {
      await deleteDocument(id)
      await loadDocuments()
    } catch (error) {
      console.error('삭제 오류:', error)
      alert('삭제에 실패했습니다.')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      {/* 헤더 */}
      <header className="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">📚 관리자 페이지</h1>
            <p className="text-sm text-gray-600">문서 업로드 및 관리</p>
          </div>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            ← 채팅으로
          </button>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* 업로드 섹션 */}
        <div className="bg-white rounded-2xl shadow-xl p-8 mb-8 border border-gray-100">
          <h2 className="text-xl font-bold text-gray-900 mb-6">📤 문서 업로드</h2>

          {/* 파일 드래그 앤 드롭 */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-8 mb-6 text-center transition-all ${
              isDragging
                ? 'border-blue-500 bg-blue-50'
                : file
                ? 'border-green-500 bg-green-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            {file ? (
              <div>
                <div className="text-6xl mb-2">✅</div>
                <p className="text-lg font-semibold text-green-700">{file.name}</p>
                <p className="text-sm text-gray-600">{(file.size / 1024 / 1024).toFixed(2)}MB</p>
                <button
                  onClick={() => setFile(null)}
                  className="mt-3 text-red-600 hover:text-red-700 text-sm font-medium"
                >
                  ✕ 제거
                </button>
              </div>
            ) : (
              <div>
                <div className="text-6xl mb-2">📄</div>
                <p className="text-lg font-semibold text-gray-700 mb-2">
                  PDF 파일을 드래그하거나 클릭하여 선택
                </p>
                <label className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700 transition-colors">
                  파일 선택
                  <input
                    type="file"
                    accept="application/pdf"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                </label>
              </div>
            )}
          </div>

          {/* 안내 메시지 */}
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-800">
              💡 <strong>자동 처리:</strong> 제목은 파일명에서 추출되고, 출처는 AI가 문서를 읽고 자동으로 찾습니다. 업로드 후 수정할 수 있습니다.
            </p>
          </div>

          {/* 업로드 버튼 */}
          <button
            onClick={handleUpload}
            disabled={isUploading || !file}
            className="w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg font-semibold hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-400 disabled:cursor-not-allowed transition-all transform hover:scale-[1.02] shadow-lg"
          >
            {isUploading ? '⏳ 처리 중...' : '🚀 업로드 시작'}
          </button>

          {/* 상태 메시지 */}
          {uploadStatus && (
            <div className={`mt-4 p-4 rounded-lg ${
              uploadStatus.startsWith('✅') ? 'bg-green-50 text-green-800' : 
              uploadStatus.startsWith('❌') ? 'bg-red-50 text-red-800' :
              'bg-blue-50 text-blue-800'
            }`}>
              {uploadStatus}
            </div>
          )}
        </div>

        {/* 문서 목록 */}
        <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-gray-900">📋 업로드된 문서</h2>
            <span className="text-sm text-gray-600">
              총 {documents.length}개 문서
              {selectedHashtags.length > 0 && ` (필터: ${filteredDocuments.length}개)`}
            </span>
          </div>

          {/* 해시태그 필터 */}
          {allHashtags.length > 0 && (
            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-sm font-semibold text-gray-700">🏷️ 해시태그 필터:</span>
                {selectedHashtags.length > 0 && (
                  <button
                    onClick={() => setSelectedHashtags([])}
                    className="text-xs text-red-600 hover:text-red-700 font-medium"
                  >
                    ✕ 필터 초기화
                  </button>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                {allHashtags.map((tag) => {
                  const isSelected = selectedHashtags.includes(tag)
                  return (
                    <button
                      key={tag}
                      onClick={() => {
                        if (isSelected) {
                          setSelectedHashtags(selectedHashtags.filter((t) => t !== tag))
                        } else {
                          setSelectedHashtags([...selectedHashtags, tag])
                        }
                      }}
                      className={`px-3 py-1 rounded-full text-sm font-medium transition-all ${
                        isSelected
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                      }`}
                    >
                      {tag}
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {documents.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p className="text-lg">업로드된 문서가 없습니다.</p>
              <p className="text-sm mt-2">위에서 PDF 파일을 업로드해주세요.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredDocuments.map((doc) => (
                <div
                  key={doc.id}
                  className="p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  {editingId === doc.id ? (
                    // 수정 모드
                    <div className="space-y-3">
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="제목"
                      />
                      <input
                        type="text"
                        value={editSource}
                        onChange={(e) => setEditSource(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="출처"
                      />
                      <div className="flex gap-2 justify-end">
                        <button
                          onClick={handleCancelEdit}
                          className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium"
                        >
                          취소
                        </button>
                        <button
                          onClick={() => handleSaveEdit(doc.id)}
                          className="px-4 py-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors font-medium"
                        >
                          ✓ 저장
                        </button>
                      </div>
                    </div>
                  ) : (
                    // 보기 모드
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900">{doc.title}</h3>
                        <p className="text-sm text-gray-600">
                          출처: {doc.source} | {doc.category}
                        </p>
                        {/* 해시태그 표시 */}
                        {doc.hashtags && doc.hashtags.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {doc.hashtags.map((tag) => (
                              <span
                                key={tag}
                                className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(doc.uploadedAt).toLocaleDateString('ko-KR')}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        {doc.fileUrl && (
                          <a
                            href={doc.fileUrl}
                            download={doc.fileName}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors font-medium"
                          >
                            📥 다운로드
                          </a>
                        )}
                        <button
                          onClick={() => handleEdit(doc)}
                          className="px-4 py-2 bg-yellow-100 text-yellow-700 rounded-lg hover:bg-yellow-200 transition-colors font-medium"
                        >
                          ✏️ 수정
                        </button>
                        <button
                          onClick={() => handleDelete(doc.id)}
                          className="px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors font-medium"
                        >
                          🗑️ 삭제
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

