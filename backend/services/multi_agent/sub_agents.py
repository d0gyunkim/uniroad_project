"""
Sub Agents
- 대학별 Agent: Supabase에서 해당 대학 해시태그 문서 검색
- 컨설팅 Agent: 임시 DB에서 입결/환산점수 데이터 조회
- 선생님 Agent: 학습 계획 및 멘탈 관리 조언
"""

import google.generativeai as genai
from typing import Dict, Any, List
import json
import os
import re
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from token_logger import log_token_usage

from services.supabase_client import supabase_service
from services.gemini_service import gemini_service
from services.score_converter import ScoreConverter
from services.data_standard import (
    korean_std_score_table,
    math_std_score_table,
    social_studies_data,
    science_inquiry_data,
    major_subjects_grade_cuts,
    english_grade_data,
    history_grade_data
)
from .mock_database import (
    get_admission_data_by_grade,
    get_jeongsi_data_by_percentile,
    get_score_conversion_info,
    get_all_universities_data,
    ADMISSION_DATA_SUSI,
    ADMISSION_DATA_JEONGSI
)

# 로그 콜백 (실시간 스트리밍용)
_log_callback = None

def set_log_callback(callback):
    """로그 콜백 설정"""
    global _log_callback
    _log_callback = callback

def _log(msg: str):
    """로그 출력 및 콜백 호출"""
    if _log_callback:
        _log_callback(msg)
    else:
        print(msg)

load_dotenv()

# Gemini API 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


class SubAgentBase:
    """Sub Agent 기본 클래스"""

    def __init__(self, name: str, description: str, custom_system_prompt: str = None):
        self.name = name
        self.description = description
        self.custom_system_prompt = custom_system_prompt
        self.model = genai.GenerativeModel(
            model_name="gemini-3-flash-preview",
        )

    async def execute(self, query: str) -> Dict[str, Any]:
        """쿼리 실행 (하위 클래스에서 구현)"""
        raise NotImplementedError


class UniversityAgent(SubAgentBase):
    """
    대학별 Agent - Supabase에서 해당 대학 해시태그 문서 검색
    
    검색 로직:
    1. 해시태그로 1차 탐색 (#{대학명})
    2. 요약본(500자) 분석으로 적합한 문서 선별
    3. 선별된 문서의 전체 내용 로드
    4. 정보 추출 후 출처와 함께 반환
    """

    SUPPORTED_UNIVERSITIES = ["서울대", "연세대", "고려대", "성균관대", "경희대"]

    def __init__(self, university_name: str, custom_system_prompt: str = None):
        self.university_name = university_name
        super().__init__(
            name=f"{university_name} agent",
            description=f"{university_name} 입시 정보(입결, 모집요강, 전형별 정보)를 Supabase에서 검색하는 에이전트",
            custom_system_prompt=custom_system_prompt
        )

    async def execute(self, query: str) -> Dict[str, Any]:
        """대학 정보 검색 및 정리"""
        _log("")
        _log("="*60)
        _log(f"🏫 {self.name} 실행")
        _log("="*60)
        _log(f"쿼리: {query}")

        try:
            client = supabase_service.get_client()

            # ============================================================
            # 1단계: 해시태그로 1차 탐색
            # ============================================================
            _log("")
            _log(f"📋 [1단계] 해시태그 검색: #{self.university_name}")
            
            metadata_response = client.table('documents_metadata').select('*').execute()
            
            if not metadata_response.data:
                return {
                    "agent": self.name,
                    "status": "no_data",
                    "result": f"{self.university_name} 관련 문서가 없습니다.",
                    "sources": [],
                    "source_urls": [],
                    "citations": []
                }

            # 해시태그 필터링
            required_univ_tag = f"#{self.university_name}"
            
            # 추가 해시태그 추출 (연도, 전형 등)
            optional_tags = []
            year_match = re.search(r'(2024|2025|2026|2027|2028)', query)
            if year_match:
                optional_tags.append(f"#{year_match.group()}")
            
            if '수시' in query:
                optional_tags.append('#수시')
            if '정시' in query:
                optional_tags.append('#정시')
            if any(word in query for word in ['요강', '모집']):
                optional_tags.append('#모집요강')
            if any(word in query for word in ['입결', '경쟁률', '커트']):
                optional_tags.append('#입결통계')

            # 필터링
            relevant_docs = []
            for doc in metadata_response.data:
                doc_hashtags = doc.get('hashtags', []) or []
                
                # 필수 조건: 대학 태그 포함
                if required_univ_tag not in doc_hashtags:
                    continue
                
                # 점수 계산
                score = 10  # 대학 태그 일치 기본 점수
                for tag in optional_tags:
                    if tag in doc_hashtags:
                        score += 5
                
                relevant_docs.append((score, doc))
            
            # 점수순 정렬
            relevant_docs.sort(key=lambda x: x[0], reverse=True)
            relevant_docs = [doc for score, doc in relevant_docs]
            
            _log(f"   {self.university_name} 관련 문서: {len(relevant_docs)}개")
            
            if not relevant_docs:
                return {
                    "agent": self.name,
                    "status": "no_match",
                    "result": f"{self.university_name} 관련 문서를 찾지 못했습니다.",
                    "sources": [],
                    "source_urls": [],
                    "citations": []
                }

            # ============================================================
            # 2단계: 요약본 분석 (500자 이내)
            # ============================================================
            _log("")
            _log(f"📋 [2단계] 요약본 분석")
            
            docs_summary_list = []
            for idx, doc in enumerate(relevant_docs[:10], 1):  # 최대 10개
                title = doc.get('title', '제목 없음')
                summary = doc.get('summary', '요약 없음')[:500]
                hashtags = doc.get('hashtags', [])
                docs_summary_list.append(
                    f"{idx}. 제목: {title}\n   해시태그: {', '.join(hashtags) if hashtags else '없음'}\n   요약: {summary}"
                )
            
            docs_summary_text = "\n\n".join(docs_summary_list)
            
            filter_prompt = f"""다음 문서들의 요약본을 읽고, 질문에 답변하는데 필요한 문서만 선택하세요.

질문: "{query}"

문서 목록:
{docs_summary_text}

선택 기준:
1. 질문에 답변하는데 필요한 정보가 포함된 문서만 선택
2. 최대 3개까지만 선택

답변 형식:
관련 문서가 있으면: 번호만 쉼표로 구분 (예: 1, 3)
관련 문서가 없으면: 없음"""

            try:
                filter_result = await gemini_service.generate(
                    filter_prompt,
                    "문서 필터링 전문가"
                )
                
                if not filter_result.strip() or "없음" in filter_result.lower():
                    # 필터링 실패시 상위 2개 사용
                    selected_docs = relevant_docs[:2]
                else:
                    selected_indices = [int(n.strip())-1 for n in re.findall(r'\d+', filter_result)]
                    selected_docs = [relevant_docs[i] for i in selected_indices if i < len(relevant_docs)]
                    if not selected_docs:
                        selected_docs = relevant_docs[:2]
                        
            except Exception as e:
                _log(f"   ⚠️ 요약본 분석 실패: {e}")
                selected_docs = relevant_docs[:2]
            
            _log(f"   선별된 문서: {len(selected_docs)}개")

            # ============================================================
            # 3단계: 전체 내용 로드
            # ============================================================
            _log("")
            _log(f"📋 [3단계] 문서 내용 로드")
            
            full_content = ""
            sources = []
            source_urls = []
            citations = []
            
            for doc in selected_docs:
                filename = doc['file_name']
                title = doc['title']
                file_url = doc.get('file_url') or ''
                
                sources.append(title)
                source_urls.append(file_url)
                
                _log(f"   📄 {title}")
                
                # 청크 가져오기
                chunks_response = client.table('policy_documents')\
                    .select('id, content, metadata')\
                    .eq('metadata->>fileName', filename)\
                    .execute()
                
                if chunks_response.data:
                    sorted_chunks = sorted(
                        chunks_response.data,
                        key=lambda x: x.get('metadata', {}).get('chunkIndex', 0)
                    )
                    
                    full_content += f"\n\n{'='*60}\n"
                    full_content += f"📄 {title}\n"
                    full_content += f"{'='*60}\n\n"
                    
                    # 청크 정보 저장 (답변 추적용)
                    for chunk in sorted_chunks:
                        chunk_content = chunk['content']
                        full_content += chunk_content
                        full_content += "\n\n"
                        
                        # 각 청크 정보를 citations에 저장 (chunk 키로)
                        # citations는 나중에 final_agent에서 추출됨
                        chunk_info = {
                            "id": chunk.get('id'),
                            "content": chunk_content,
                            "title": title,
                            "source": doc.get('source', ''),
                            "file_url": file_url,
                            "metadata": chunk.get('metadata', {})
                        }
                        citations.append({
                            "chunk": chunk_info,
                            "source": title,  # 기존 형식 유지
                            "url": file_url
                        })

            # ============================================================
            # 4단계: 정보 추출
            # ============================================================
            _log("")
            _log(f"📋 [4단계] 정보 추출")

            # 사용 가능한 출처 목록 생성
            sources_list = "\n".join([f"- {s}" for s in sources])

            extract_prompt = f"""다음 문서에서 질문에 답변하는데 필요한 핵심 정보만 추출하세요.

질문: {query}

사용 가능한 출처 목록:
{sources_list}

문서 내용:
{full_content[:15000]}

출력 규칙:
1. 핵심 정보만 간결하게 추출
2. 수치 데이터는 정확하게 유지
3. 각 정보가 어느 문서에서 왔는지 [출처: 문서명] 형식으로 반드시 표시
4. 여러 문서에서 정보를 가져왔다면, 각 정보마다 해당 출처를 표시
5. 마지막에 "출처: 문서1, 문서2, ..." 형태로 요약하지 말고, 정보마다 개별 표시
6. JSON이 아닌 자연어로 작성"""

            try:
                extracted_info = await gemini_service.generate(
                    extract_prompt,
                    "문서 정보 추출 전문가"
                )

                # citations는 이미 청크 정보와 함께 추가되었으므로 추가 작업 불필요

            except Exception as e:
                extracted_info = f"정보 추출 실패: {e}"
            
            _log(f"   추출된 정보 길이: {len(extracted_info)}자")
            _log("="*60)

            return {
                "agent": self.name,
                "status": "success",
                "query": query,
                "result": extracted_info,
                "sources": sources,
                "source_urls": source_urls,
                "citations": citations
            }

        except Exception as e:
            _log(f"❌ {self.name} 오류: {e}")
            return {
                "agent": self.name,
                "status": "error",
                "result": str(e),
                "sources": [],
                "source_urls": [],
                "citations": []
            }


class ConsultingAgent(SubAgentBase):
    """
    컨설팅 Agent - 임시 DB에서 입결/환산점수 데이터 조회
    5개 대학(서울대/연세대/고려대/성균관대/경희대) 데이터 사용
    
    점수 변환 기능:
    - 등급/표준점수/백분위/원점수 -> 등급-표준점수-백분위 정규화
    - 2026 수능 데이터 기준
    """

    def __init__(self, custom_system_prompt: str = None):
        super().__init__(
            name="컨설팅 agent",
            description="5개 대학 합격 데이터 비교 분석, 합격 가능성 평가",
            custom_system_prompt=custom_system_prompt
        )
        # ScoreConverter 초기화
        self.score_converter = ScoreConverter()
        
        # 2026 수능 데이터 준비
        self.score_data = {
            "국어": {
                "표준점수_테이블": {str(k): v for k, v in korean_std_score_table.items()},
                "선택과목_등급컷": major_subjects_grade_cuts.get("국어", {})
            },
            "수학": {
                "표준점수_테이블": {str(k): v for k, v in math_std_score_table.items()},
                "선택과목_등급컷": major_subjects_grade_cuts.get("수학", {})
            },
            "영어": english_grade_data,
            "한국사": history_grade_data,
            "사회탐구": social_studies_data,
            "과학탐구": science_inquiry_data
        }

    async def execute(self, query: str) -> Dict[str, Any]:
        """성적 기반 합격 가능 대학 분석"""
        _log("")
        _log("="*60)
        _log(f"📊 컨설팅 Agent 실행")
        _log("="*60)
        _log(f"쿼리: {query}")

        # 쿼리에서 성적 정보 추출 및 정규화
        raw_grade_info = self._extract_grade_from_query(query)
        _log(f"   추출된 원본 성적: {raw_grade_info}")
        
        # 점수 정규화 (등급-표준점수-백분위)
        normalized_scores = self._normalize_scores(raw_grade_info)
        _log(f"   정규화된 성적: {json.dumps(normalized_scores, ensure_ascii=False, indent=2)}")

        # DB에서 데이터 조회
        susi_data = None
        jeongsi_data = None

        if raw_grade_info.get("내신"):
            susi_data = get_admission_data_by_grade(raw_grade_info["내신"])

        # 정규화된 백분위로 정시 데이터 조회
        avg_percentile = self._calculate_average_percentile(normalized_scores)
        if avg_percentile:
            jeongsi_data = get_jeongsi_data_by_percentile(avg_percentile)
            _log(f"   평균 백분위: {avg_percentile}")

        # 전체 데이터 포함
        all_data = get_all_universities_data()
        
        # 정규화된 학생 성적 추가
        all_data["학생_정규화_성적"] = normalized_scores
        all_data["학생_성적분석"] = {
            "수시": susi_data,
            "정시": jeongsi_data
        } if (susi_data or jeongsi_data) else None

        # Gemini로 분석
        if self.custom_system_prompt:
            system_prompt = self.custom_system_prompt.format(
                all_data=json.dumps(all_data, ensure_ascii=False, indent=2)[:8000]
            )
            print(f"🎨 Using custom system prompt for consulting agent")
        else:
            # 정규화된 성적 정보 포맷팅
            normalized_scores_text = self._format_normalized_scores(normalized_scores)
            
            system_prompt = f"""당신은 대학 입시 데이터 분석 전문가입니다.
사용자의 성적을 '2026 수능 데이터' 기준으로 표준화하여 분석하고, 팩트 기반의 분석 결과만 제공하세요.

## 학생의 정규화된 성적 (등급-표준점수-백분위)
{normalized_scores_text}

## 가용 입결 데이터
{json.dumps(all_data, ensure_ascii=False, indent=2)[:6000]}

## 출력 규칙 (필수)
1. **성적 정규화 결과 먼저 제시**: 학생의 입력을 등급-표준점수-백분위로 변환한 결과를 명시
2. 추정된 과목이 있으면 "(추정)" 표시
3. 질문에 필요한 핵심 데이터만 간결하게 제시
4. 수치 데이터는 정확하게 표기
5. 각 정보 뒤에 [출처: 컨설팅DB] 형식으로 출처 표시
6. JSON이 아닌 자연어로 출력
7. 격려나 조언은 하지 말고 오직 데이터만 제공
8. "합격가능", "도전가능" 같은 판단은 하지 말고 사실만 나열
9. 마크다운 문법(**, *, #, ##, ###) 절대 사용 금지
10. 글머리 기호는 - 또는 • 만 사용

## 출력 형식 예시
【학생 성적 정규화】
- 국어(언어와매체): 1등급 / 표준점수 140 / 백분위 98
- 수학(미적분): 2등급 / 표준점수 128 / 백분위 92
- 영어: 2등급 (추정)
[출처: 2026 수능 데이터]

【입결 데이터 비교】
- 2024학년도 서울대 기계공학부 수시 일반전형 70% 커트라인: 내신 1.5등급 [출처: 컨설팅DB]
- 2024학년도 연세대 기계공학부 정시 70% 커트라인: 백분위 95.2 [출처: 컨설팅DB]"""

        try:
            response = self.model.generate_content(
                f"{system_prompt}\n\n질문: {query}\n\n위 데이터에서 질문에 답변하는데 필요한 정보만 추출하세요.",
                generation_config={"temperature": 0.1, "max_output_tokens": 1024},
                request_options=genai.types.RequestOptions(
                    retry=None,
                    timeout=120.0  # 멀티에이전트 파이프라인을 위해 120초로 증가
                )
            )

            # 토큰 사용량 기록
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                print(f"💰 토큰 사용량 ({self.name}): {usage}")
                
                log_token_usage(
                    operation="입결비교에이전트",
                    prompt_tokens=getattr(usage, 'prompt_token_count', 0),
                    output_tokens=getattr(usage, 'candidates_token_count', 0),
                    total_tokens=getattr(usage, 'total_token_count', 0),
                    model="gemini-3-flash-preview",
                    details=self.name
                )

            result_text = response.text
            
            # citations 구성
            citations = [
                {
                    "text": "5개 대학 입결 데이터 분석",
                    "source": "컨설팅 DB (서울대/연세대/고려대/성균관대/경희대)",
                    "url": ""
                }
            ]
            
            # 점수 변환이 실제로 이루어진 경우에만 산출방식 문서 추가
            if normalized_scores and normalized_scores.get("과목별_성적"):
                citations.append({
                    "text": "표준점수·백분위 산출 방식",
                    "source": "유니로드 2026 수능 표준점수 및 백분위 산출 방식 문서",
                    "url": "https://rnitmphvahpkosvxjshw.supabase.co/storage/v1/object/public/document/pdfs/5d5c4455-bf58-4ef5-9e7f-a82d602aaa51.pdf"
                })

            _log(f"   분석 완료")
            _log("="*60)

            # sources 목록 구성
            sources = ["컨설팅 DB"]
            if normalized_scores and normalized_scores.get("과목별_성적"):
                sources.append("표준점수·백분위 산출 방식")
            
            return {
                "agent": self.name,
                "status": "success",
                "query": query,
                "result": result_text,
                "grade_info": raw_grade_info,
                "normalized_scores": normalized_scores,  # 정규화된 성적 추가
                "sources": sources,
                "source_urls": [],
                "citations": citations
            }

        except Exception as e:
            _log(f"   ❌ 컨설팅 Agent 오류: {e}")
            return {
                "agent": self.name,
                "status": "error",
                "result": str(e),
                "grade_info": raw_grade_info,
                "normalized_scores": normalized_scores,
                "sources": [],
                "source_urls": [],
                "citations": []
            }

    def _extract_grade_from_query(self, query: str) -> Dict[str, Any]:
        """
        쿼리에서 성적 정보 추출
        
        지원 형식:
        - "등급 132" -> 국어 1등급, 영어 3등급, 수학 2등급
        - "국어 90점 수학 미적분 85점"
        - "국어 1등급 수학 표준점수 130"
        - "국어 언어와매체 92점"
        """
        result = {
            "raw_input": query,
            "subjects": {},
            "내신": None,
            "선택과목_추론": {}
        }

        # 1. "등급 XXX" 패턴 처리 (예: "등급 132", "13425", "나 13425야")
        # 숫자만 3~5자리인 패턴 찾기
        compact_pattern = r'등급\s*(\d{3,5})|(\d{3,5})\s*등급|(?:나|저)\s*(\d{3,5})|(\d{3,5})(?:야|이야|입니다|요)'
        match = re.search(compact_pattern, query)
        if match:
            grade_str = match.group(1) or match.group(2) or match.group(3) or match.group(4)
            if grade_str and len(grade_str) >= 3:
                # 국/수/영 또는 국/수/영/탐1/탐2
                subjects_order = ["국어", "수학", "영어", "탐구1", "탐구2"]
                for i, char in enumerate(grade_str):
                    if i < len(subjects_order):
                        result["subjects"][subjects_order[i]] = {
                            "type": "등급",
                            "value": int(char)
                        }
        
        # 숫자만 있는 경우도 처리 (예: 메시지에서 "13425" 같은 숫자만)
        # 단, 표준점수/백분위 키워드가 없는 경우에만
        if not result["subjects"] and "표준점수" not in query and "백분위" not in query and "점" not in query:
            standalone_pattern = r'\b(\d{3,5})\b'
            matches = re.findall(standalone_pattern, query)
            for grade_str in matches:
                # 연도가 아닌지 확인 (2024, 2025, 2026 등)
                # 그리고 100 이상인 숫자는 표준점수일 가능성이 높으므로 제외
                if not (2020 <= int(grade_str) <= 2030) and int(grade_str) < 100:
                    subjects_order = ["국어", "수학", "영어", "탐구1", "탐구2"]
                    for i, char in enumerate(grade_str):
                        if i < len(subjects_order):
                            result["subjects"][subjects_order[i]] = {
                                "type": "등급",
                                "value": int(char)
                            }
                    break

        # 2. 과목별 성적 추출
        subject_keywords = {
            "국어": ["국어", "국"],
            "수학": ["수학", "수"],
            "영어": ["영어", "영"],
            "한국사": ["한국사", "한사"],
            "탐구1": ["탐구1"],
            "탐구2": ["탐구2"],
            # 탐구 과목
            "사회문화": ["사회문화", "사문"],
            "생활과윤리": ["생활과윤리", "생윤"],
            "윤리와사상": ["윤리와사상", "윤사"],
            "한국지리": ["한국지리", "한지"],
            "세계지리": ["세계지리", "세지"],
            "동아시아사": ["동아시아사", "동아시아"],
            "세계사": ["세계사"],
            "정치와법": ["정치와법", "정법"],
            "경제": ["경제"],
            "물리학1": ["물리학1", "물리1", "물1"],
            "물리학2": ["물리학2", "물리2", "물2"],
            "화학1": ["화학1", "화1"],
            "화학2": ["화학2", "화2"],
            "생명과학1": ["생명과학1", "생명1", "생1"],
            "생명과학2": ["생명과학2", "생명2", "생2"],
            "지구과학1": ["지구과학1", "지구1", "지1"],
            "지구과학2": ["지구과학2", "지구2", "지2"],
        }

        # 선택과목 키워드
        elective_keywords = {
            "화법과작문": ["화법과작문", "화작"],
            "언어와매체": ["언어와매체", "언매"],
            "확률과통계": ["확률과통계", "확통"],
            "미적분": ["미적분", "미적"],
            "기하": ["기하"],
        }

        # 선택과목 추출
        detected_electives = {}
        for elective, keywords in elective_keywords.items():
            for kw in keywords:
                if kw in query:
                    if elective in ["화법과작문", "언어와매체"]:
                        detected_electives["국어"] = elective
                    else:
                        detected_electives["수학"] = elective
                    break
        
        result["선택과목_추론"] = detected_electives

        # 각 과목별 점수 추출
        for subject, keywords in subject_keywords.items():
            if subject in result["subjects"]:
                continue  # 이미 추출된 과목은 스킵
                
            for kw in keywords:
                # 등급 패턴 (먼저 체크)
                grade_pattern = rf'{kw}\s*(\d)\s*등급|{kw}\s*등급\s*(\d)'
                match = re.search(grade_pattern, query)
                if match and subject not in result["subjects"]:
                    grade = match.group(1) or match.group(2)
                    result["subjects"][subject] = {
                        "type": "등급",
                        "value": int(grade)
                    }
                    break
                
                # 표준점수 패턴 (표준점수, 표점 명시)
                std_pattern = rf'{kw}\s*(?:표준점수|표점)\s*(\d{{2,3}})'
                match = re.search(std_pattern, query)
                if match and subject not in result["subjects"]:
                    value = int(match.group(1))
                    result["subjects"][subject] = {"type": "표준점수", "value": value}
                    break
                
                # 백분위 패턴
                pct_pattern = rf'{kw}\s*백분위\s*(\d{{1,3}})'
                match = re.search(pct_pattern, query)
                if match and subject not in result["subjects"]:
                    result["subjects"][subject] = {
                        "type": "백분위",
                        "value": int(match.group(1))
                    }
                    break
                
                # 원점수 패턴 (XX점)
                raw_pattern = rf'{kw}\s+(?:\w+\s+)?(\d{{2,3}})\s*점'
                match = re.search(raw_pattern, query)
                if match and subject not in result["subjects"]:
                    value = int(match.group(1))
                    result["subjects"][subject] = {"type": "원점수", "value": value}
                    break

        # 3. "탐구 X등급" 패턴 추가 처리 (탐구1, 탐구2가 아직 추출되지 않은 경우)
        if "탐구1" not in result["subjects"] or "탐구2" not in result["subjects"]:
            # "탐구" 키워드 뒤에 등급이 오는 패턴을 모두 찾기
            inquiry_pattern = r'탐구\s*(\d)\s*등급|탐구\s*등급\s*(\d)'
            inquiry_matches = re.finditer(inquiry_pattern, query)
            
            inquiry_grades = []
            for match in inquiry_matches:
                grade_val = match.group(1) or match.group(2)
                inquiry_grades.append(int(grade_val))
            
            # 발견된 탐구 등급을 순서대로 탐구1, 탐구2에 할당
            if len(inquiry_grades) >= 1 and "탐구1" not in result["subjects"]:
                result["subjects"]["탐구1"] = {
                    "type": "등급",
                    "value": inquiry_grades[0]
                }
            if len(inquiry_grades) >= 2 and "탐구2" not in result["subjects"]:
                result["subjects"]["탐구2"] = {
                    "type": "등급",
                    "value": inquiry_grades[1]
                }

        # 4. 내신 등급 추출
        grade_pattern = r'내신\s*(\d+\.?\d*)\s*등급?|(\d+\.?\d*)\s*등급\s*내신'
        match = re.search(grade_pattern, query)
        if match:
            grade = match.group(1) or match.group(2)
            result["내신"] = float(grade)

        # 5. 선택과목 기본값 추론
        if "국어" not in result.get("선택과목_추론", {}):
            result["선택과목_추론"]["국어"] = "화법과작문"  # 기본값
        if "수학" not in result.get("선택과목_추론", {}):
            result["선택과목_추론"]["수학"] = "확률과통계"  # 기본값
        
        # 수학 선택과목에 따른 탐구 추론
        math_elective = result["선택과목_추론"].get("수학", "확률과통계")
        if math_elective == "확률과통계":
            result["선택과목_추론"]["탐구_추론"] = "인문계 (사회문화/생활과윤리)"
        else:
            result["선택과목_추론"]["탐구_추론"] = "자연계 (지구과학1/생명과학1)"

        return result
    
    def _normalize_scores(self, raw_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        추출된 성적을 등급-표준점수-백분위로 정규화
        
        Args:
            raw_info: _extract_grade_from_query에서 추출한 정보
            
        Returns:
            정규화된 성적 정보
        """
        normalized = {
            "과목별_성적": {},
            "추정_과목": [],
            "선택과목": raw_info.get("선택과목_추론", {})
        }
        
        subjects_data = raw_info.get("subjects", {})
        electives = raw_info.get("선택과목_추론", {})
        
        for subject, score_info in subjects_data.items():
            score_type = score_info.get("type")
            value = score_info.get("value")
            
            converted = None
            
            try:
                if subject in ["국어", "수학"]:
                    elective = electives.get(subject)
                    
                    if score_type == "등급":
                        # 등급 -> 해당 등급 중간 백분위의 표준점수 사용
                        converted = self._convert_grade_to_scores(subject, value)
                    elif score_type == "표준점수":
                        converted = self.score_converter.convert_score(subject, standard_score=value)
                        if converted:
                            _log(f"   {subject} 표준점수 {value} -> 등급 {converted.get('grade')}, 백분위 {converted.get('percentile')}")
                    elif score_type == "백분위":
                        converted = self.score_converter.convert_score(subject, percentile=value)
                    elif score_type == "원점수" and elective:
                        converted = self.score_converter.convert_score(
                            subject, raw_score=value, elective=elective
                        )
                        if converted:
                            _log(f"   {subject}({elective}) 원점수 {value} -> 표준점수 {converted.get('standard_score')}, 등급 {converted.get('grade')}")
                
                elif subject == "영어":
                    # 영어는 절대평가
                    if score_type == "등급":
                        grade_data = english_grade_data.get(value, {})
                        converted = {
                            "standard_score": None,
                            "percentile": 100 - grade_data.get("ratio", 50),
                            "grade": value
                        }
                    elif score_type == "원점수":
                        # 원점수 -> 등급 변환
                        for grade, data in english_grade_data.items():
                            if value >= data.get("raw_cut", 0):
                                converted = {
                                    "standard_score": None,
                                    "percentile": 100 - data.get("ratio", 50),
                                    "grade": grade
                                }
                                break
                
                elif subject in self.score_converter.social_data:
                    if score_type == "등급":
                        converted = self._convert_grade_to_scores(subject, value)
                    elif score_type == "표준점수":
                        converted = self.score_converter.convert_score(subject, standard_score=value)
                    elif score_type == "백분위":
                        converted = self.score_converter.convert_score(subject, percentile=value)
                
                elif subject in self.score_converter.science_data:
                    if score_type == "등급":
                        converted = self._convert_grade_to_scores(subject, value)
                    elif score_type == "표준점수":
                        converted = self.score_converter.convert_score(subject, standard_score=value)
                    elif score_type == "백분위":
                        converted = self.score_converter.convert_score(subject, percentile=value)
                
                elif subject in ["탐구1", "탐구2"]:
                    # 탐구 과목이 특정되지 않은 경우
                    if score_type == "등급":
                        converted = self._convert_grade_to_scores("탐구_기본", value)
                
            except Exception as e:
                _log(f"   ⚠️ {subject} 변환 오류: {e}")
                converted = None
            
            if converted:
                normalized["과목별_성적"][subject] = {
                    "원본_입력": score_info,
                    "등급": converted.get("grade"),
                    "표준점수": converted.get("standard_score"),
                    "백분위": converted.get("percentile"),
                    "선택과목": electives.get(subject) if subject in ["국어", "수학"] else None
                }
            else:
                # 변환 실패 시 원본 저장
                normalized["과목별_성적"][subject] = {
                    "원본_입력": score_info,
                    "등급": value if score_type == "등급" else None,
                    "표준점수": value if score_type == "표준점수" else None,
                    "백분위": value if score_type == "백분위" else None,
                    "변환_실패": True
                }
        
        # 미입력 과목 추정 (다른 과목들의 평균 백분위 기준)
        normalized = self._estimate_missing_subjects(normalized)
        
        return normalized
    
    def _convert_grade_to_scores(self, subject: str, grade: int) -> Dict[str, Any]:
        """
        등급을 표준점수/백분위로 변환 (보수적 접근 - 해당 등급 중간값 사용)
        
        등급별 백분위 기준:
        - 1등급: 96~100% -> 중간 98%
        - 2등급: 89~96% -> 중간 92.5%
        - 3등급: 77~89% -> 중간 83%
        - 4등급: 60~77% -> 중간 68.5%
        - 5등급: 40~60% -> 중간 50%
        - 6등급: 23~40% -> 중간 31.5%
        - 7등급: 11~23% -> 중간 17%
        - 8등급: 4~11% -> 중간 7.5%
        - 9등급: 0~4% -> 중간 2%
        """
        grade_to_mid_percentile = {
            1: 98,
            2: 92,
            3: 83,
            4: 68,
            5: 50,
            6: 31,
            7: 17,
            8: 7,
            9: 2
        }
        
        mid_percentile = grade_to_mid_percentile.get(grade, 50)
        
        # 해당 백분위에서 가장 가까운 표준점수 찾기
        result = self.score_converter.find_closest_by_percentile(subject, mid_percentile)
        
        if result:
            result["grade"] = grade  # 원래 등급 유지
            return result
        
        # 탐구 기본값
        if subject == "탐구_기본":
            # 사회탐구 기본값 (사회문화 기준)
            std_estimate = 50 + (mid_percentile - 50) * 0.2  # 대략적 추정
            return {
                "grade": grade,
                "standard_score": round(std_estimate),
                "percentile": mid_percentile
            }
        
        return {
            "grade": grade,
            "standard_score": None,
            "percentile": mid_percentile
        }
    
    def _estimate_missing_subjects(self, normalized: Dict[str, Any]) -> Dict[str, Any]:
        """
        미입력 과목을 다른 과목들의 평균 백분위로 추정
        """
        subjects = normalized.get("과목별_성적", {})
        
        # 입력된 과목들의 평균 백분위 계산
        percentiles = []
        for subj, data in subjects.items():
            pct = data.get("백분위")
            if pct is not None:
                percentiles.append(pct)
        
        if not percentiles:
            return normalized
        
        avg_percentile = sum(percentiles) / len(percentiles)
        
        # 필수 과목 확인
        required = ["국어", "수학", "영어"]
        for subj in required:
            if subj not in subjects:
                # 평균 백분위로 추정
                if subj in ["국어", "수학"]:
                    estimated = self.score_converter.find_closest_by_percentile(subj, int(avg_percentile))
                    if estimated:
                        normalized["과목별_성적"][subj] = {
                            "원본_입력": None,
                            "등급": estimated.get("grade"),
                            "표준점수": estimated.get("standard_score"),
                            "백분위": estimated.get("percentile"),
                            "추정됨": True
                        }
                        normalized["추정_과목"].append(subj)
                elif subj == "영어":
                    # 영어 등급 추정
                    if avg_percentile >= 97:
                        est_grade = 1
                    elif avg_percentile >= 83:
                        est_grade = 2
                    elif avg_percentile >= 56:
                        est_grade = 3
                    elif avg_percentile >= 32:
                        est_grade = 4
                    else:
                        est_grade = 5
                    
                    normalized["과목별_성적"][subj] = {
                        "원본_입력": None,
                        "등급": est_grade,
                        "표준점수": None,
                        "백분위": avg_percentile,
                        "추정됨": True
                    }
                    normalized["추정_과목"].append(subj)
        
        return normalized
    
    def _calculate_average_percentile(self, normalized: Dict[str, Any]) -> float:
        """정규화된 성적에서 평균 백분위 계산"""
        subjects = normalized.get("과목별_성적", {})
        
        percentiles = []
        for subj, data in subjects.items():
            pct = data.get("백분위")
            if pct is not None:
                percentiles.append(pct)
        
        if not percentiles:
            return None
        
        return sum(percentiles) / len(percentiles)
    
    def _format_normalized_scores(self, normalized: Dict[str, Any]) -> str:
        """정규화된 성적을 텍스트로 포맷팅"""
        lines = []
        
        subjects = normalized.get("과목별_성적", {})
        electives = normalized.get("선택과목", {})
        estimated = normalized.get("추정_과목", [])
        
        for subj, data in subjects.items():
            grade = data.get("등급")
            std = data.get("표준점수")
            pct = data.get("백분위")
            elective = data.get("선택과목") or electives.get(subj)
            is_estimated = data.get("추정됨", False) or subj in estimated
            
            # 과목명 포맷
            if elective:
                subj_name = f"{subj}({elective})"
            else:
                subj_name = subj
            
            # 점수 포맷
            parts = []
            if grade is not None:
                parts.append(f"{grade}등급")
            if std is not None:
                parts.append(f"표준점수 {std}")
            elif subj == "영어":
                parts.append("표준점수 없음(절대평가)")
            if pct is not None:
                parts.append(f"백분위 {round(pct, 1)}")
            
            score_text = " / ".join(parts) if parts else "정보 없음"
            
            if is_estimated:
                score_text += " (추정)"
            
            lines.append(f"- {subj_name}: {score_text}")
        
        if not lines:
            return "성적 정보가 입력되지 않았습니다."
        
        return "\n".join(lines)


class TeacherAgent(SubAgentBase):
    """선생님 Agent - 학습 계획 및 멘탈 관리 조언"""

    def __init__(self, custom_system_prompt: str = None):
        super().__init__(
            name="선생님 agent",
            description="현실적인 목표 설정 및 공부 계획 수립, 멘탈 관리",
            custom_system_prompt=custom_system_prompt
        )

    async def execute(self, query: str) -> Dict[str, Any]:
        """학습 계획 및 조언 제공"""
        _log("")
        _log("="*60)
        _log(f"👨‍🏫 선생님 Agent 실행")
        _log("="*60)
        _log(f"쿼리: {query}")

        if self.custom_system_prompt:
            system_prompt = self.custom_system_prompt
            print(f"🎨 Using custom system prompt for teacher agent")
        else:
            system_prompt = """당신은 20년 경력의 입시 전문 선생님입니다.
학생의 상황을 파악하고 현실적이면서도 희망을 잃지 않는 조언을 해주세요.

## 조언 원칙
1. 현실적인 목표 설정 (무리한 목표는 지적)
2. 구체적인 시간표와 계획 제시
3. 멘탈 관리 조언 포함
4. 단기/중기/장기 목표 구분
5. 포기하지 않도록 격려하되, 거짓 희망은 주지 않기

## 출력 형식
- 자연어로 친근하게 작성
- 필요시 리스트나 표 사용
- 존댓말 사용"""

        try:
            response = self.model.generate_content(
                f"{system_prompt}\n\n학생 질문: {query}\n\n선생님으로서 조언해주세요.",
                generation_config={"temperature": 0.7},
                request_options=genai.types.RequestOptions(
                    retry=None,
                    timeout=120.0  # 멀티에이전트 파이프라인을 위해 120초로 증가
                )
            )

            # 토큰 사용량 기록
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                print(f"💰 토큰 사용량 ({self.name}): {usage}")
                
                log_token_usage(
                    operation="선생님에이전트",
                    prompt_tokens=getattr(usage, 'prompt_token_count', 0),
                    output_tokens=getattr(usage, 'candidates_token_count', 0),
                    total_tokens=getattr(usage, 'total_token_count', 0),
                    model="gemini-3-flash-preview",
                    details=self.name
                )

            _log(f"   조언 완료")
            _log("="*60)

            return {
                "agent": self.name,
                "status": "success",
                "query": query,
                "result": response.text,
                "sources": [],
                "source_urls": [],
                "citations": []
            }

        except Exception as e:
            return {
                "agent": self.name,
                "status": "error",
                "result": str(e),
                "sources": [],
                "source_urls": [],
                "citations": []
            }


# ============================================================
# Agent Factory
# ============================================================

def get_agent(agent_name: str) -> SubAgentBase:
    """에이전트 이름으로 에이전트 인스턴스 반환"""
    agent_name_lower = agent_name.lower()

    # 대학별 Agent
    for univ in UniversityAgent.SUPPORTED_UNIVERSITIES:
        if univ in agent_name:
            return UniversityAgent(univ)

    # 컨설팅 Agent
    if "컨설팅" in agent_name or "컨설턴트" in agent_name:
        return ConsultingAgent()

    # 선생님 Agent
    if "선생님" in agent_name or "선생" in agent_name:
        return TeacherAgent()

    raise ValueError(f"알 수 없는 에이전트: {agent_name}")


async def execute_sub_agents(execution_plan: list) -> Dict[str, Any]:
    """
    Execution Plan에 따라 Sub Agent들 실행
    
    Args:
        execution_plan: Orchestration Agent가 생성한 실행 계획
        
    Returns:
        {
            "Step1_Result": {...},
            "Step2_Result": {...},
            ...
        }
    """
    results = {}

    for step in execution_plan:
        step_num = step.get("step")
        agent_name = step.get("agent")
        query = step.get("query")

        _log(f"   Step {step_num}: {agent_name}")
        _log(f"   Query: {query}")

        try:
            agent = get_agent(agent_name)
            result = await agent.execute(query)
            results[f"Step{step_num}_Result"] = result
            
            status_icon = "✅" if result.get('status') == 'success' else "❌"
            _log(f"   {status_icon} Status: {result.get('status')}")
            sources_count = len(result.get('sources', []))
            if sources_count > 0:
                _log(f"   출처: {sources_count}개")
            
        except Exception as e:
            _log(f"   ❌ Error: {e}")
            results[f"Step{step_num}_Result"] = {
                "agent": agent_name,
                "status": "error",
                "result": str(e),
                "sources": [],
                "source_urls": [],
                "citations": []
            }

    return results
