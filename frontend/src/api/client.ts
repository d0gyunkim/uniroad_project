import axios from 'axios'

const API_BASE_URL = '/api'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 120초 (업로드는 30-40초 소요)
})

export interface ChatRequest {
  message: string
  session_id?: string
}

export interface ChatResponse {
  response: string
  sources: string[]
  source_urls: string[]  // 다운로드 URL
}

export interface UploadResponse {
  success: boolean
  message: string
  stats: {
    totalPages: number
    chunksTotal: number
    chunksSuccess: number
    chunksFailed: number
    processingTime: string
    markdownSize: string
  }
  preview: {
    firstChunk: string
  }
}

export interface Document {
  id: string
  title: string
  source: string
  fileName: string
  fileUrl?: string  // 다운로드 URL
  category: string
  uploadedAt: string
  hashtags?: string[]  // 해시태그
}

// 채팅 API
export const sendMessage = async (
  message: string,
  sessionId?: string
): Promise<ChatResponse> => {
  const response = await api.post<ChatResponse>('/chat', {
    message,
    session_id: sessionId,
  })
  return response.data
}

// 업로드 API (제목/출처 자동 추출)
export const uploadDocument = async (
  file: File
): Promise<UploadResponse> => {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post<UploadResponse>('/upload/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 180000, // 3분 (큰 파일 대비)
  })
  return response.data
}

// 문서 수정 API
export const updateDocument = async (
  id: string,
  title: string,
  source: string,
  hashtags?: string[]
): Promise<void> => {
  await api.patch(`/documents/${id}`, {
    title,
    source,
    hashtags,
  })
}

// 문서 목록 API
export const getDocuments = async (): Promise<Document[]> => {
  const response = await api.get<{ documents: Document[] }>('/documents')
  return response.data.documents
}

// 문서 삭제 API
export const deleteDocument = async (id: string): Promise<void> => {
  await api.delete(`/documents/${id}`)
}

