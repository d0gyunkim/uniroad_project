# 2026 수능 점수 변환기

2026학년도 수능 표준점수와 백분위를 상호 변환하는 파이썬 유틸리티입니다.

## 기능

- 표준점수 입력 → 백분위, 등급 조회
- 백분위 입력 → 표준점수, 등급 조회
- **원점수 입력 → 표준점수, 백분위, 등급 조회 (국어/수학 선택과목)**
- 정확한 값이 없을 때 가장 가까운 값 자동 검색
- 등급컷 사이의 원점수는 선형 보간으로 자동 추정
- 국어, 수학, 사회탐구 9과목, 과학탐구 8과목 지원

## 지원 과목

### 국어/수학
- 국어
- 수학

### 사회탐구 (9과목)
- 경제
- 동아시아사
- 사회문화
- 생활과윤리
- 세계사
- 세계지리
- 정치와법
- 한국지리
- 윤리와사상

### 과학탐구 (8과목)
- 물리학1, 물리학2
- 화학1, 화학2
- 생명과학1, 생명과학2
- 지구과학1, 지구과학2

## 사용 방법

### 기본 사용법

```python
from backend.services.score_converter import ScoreConverter

# 인스턴스 생성
converter = ScoreConverter()

# 1. 표준점수로 조회
result = converter.convert_score("국어", standard_score=140)
print(result)
# {'standard_score': 140, 'percentile': 99, 'grade': 1}

# 2. 백분위로 조회
result = converter.convert_score("수학", percentile=95)
print(result)
# {'standard_score': 132, 'percentile': 95, 'grade': 2}

# 3. 탐구 과목 (원점수 정보 포함)
result = converter.convert_score("생명과학1", standard_score=70)
print(result)
# {'standard_score': 70, 'percentile': 99, 'grade': 1, 'raw_score': 45}

# 4. 원점수로 조회 (국어/수학만 지원, 선택과목 필수)
result = converter.convert_score("국어", raw_score=92, elective="언어와매체")
print(result)
# {'standard_score': 139, 'percentile': 91, 'grade': 1}

result = converter.convert_score("수학", raw_score=75, elective="미적분")
print(result)
# {'standard_score': 128, 'percentile': 96, 'grade': 2}
```

### 지원하는 선택과목

**국어:**
- 화법과작문
- 언어와매체

**수학:**
- 확률과통계
- 미적분
- 기하

```python
# 예시: 국어 화법과작문 88점
result = converter.convert_score("국어", raw_score=88, elective="화법과작문")

# 예시: 수학 기하 70점
result = converter.convert_score("수학", raw_score=70, elective="기하")
```

### 가장 가까운 값 찾기

정확한 표준점수나 백분위가 데이터에 없을 때, 가장 가까운 값을 자동으로 찾아줍니다.

```python
# use_closest=True (기본값)
result = converter.convert_score("물리학1", standard_score=64, use_closest=True)
print(result)
# 64가 정확히 없으면 가장 가까운 값(예: 63 또는 65)을 반환

# use_closest=False로 설정하면 정확한 값이 없을 때 None 반환
result = converter.convert_score("물리학1", standard_score=64, use_closest=False)
# None
```

### 개별 메서드 사용

```python
# 표준점수로만 조회
result = converter.get_score_by_standard("국어", 140)

# 백분위로만 조회
result = converter.get_score_by_percentile("수학", 95)

# 가장 가까운 표준점수 찾기
result = converter.find_closest_by_standard("생명과학1", 64)

# 가장 가까운 백분위 찾기
result = converter.find_closest_by_percentile("사회문화", 85)
```

### 사용 가능한 과목 목록

```python
subjects = converter.get_available_subjects()
print(subjects)
# {
#     "국수영": ["국어", "수학"],
#     "사회탐구": ["경제", "동아시아사", ...],
#     "과학탐구": ["물리학1", "물리학2", ...]
# }
```

## API 레퍼런스

### `ScoreConverter` 클래스

#### `convert_score(subject, standard_score=None, percentile=None, raw_score=None, elective=None, use_closest=True)`

표준점수, 백분위 또는 원점수를 입력받아 모든 정보를 반환합니다.

**Parameters:**
- `subject` (str): 과목명
- `standard_score` (int, optional): 표준점수
- `percentile` (int, optional): 백분위
- `raw_score` (int, optional): 원점수 (국어/수학만 지원)
- `elective` (str, optional): 선택과목 (raw_score 사용 시 필수)
- `use_closest` (bool): 정확한 값이 없을 때 가장 가까운 값 사용 여부 (기본값: True)

**Returns:**
- `dict`: `{"standard_score": int, "percentile": int, "grade": int, "raw_score": int (탐구 과목만)}`
- `None`: 값을 찾을 수 없을 때

**Raises:**
- `ValueError`: 입력값이 잘못된 경우 (셋 중 하나만 입력해야 함)

**원점수 사용 시 주의사항:**
- 등급컷에 정확히 맞지 않는 점수는 선형 보간으로 추정됩니다
- 최하위 등급컷보다 낮은 점수는 최하위 등급으로 처리됩니다

#### `get_score_by_standard(subject, standard_score)`

표준점수로 백분위와 등급을 조회합니다.

**Returns:**
- `dict` or `None`

#### `get_score_by_percentile(subject, percentile)`

백분위로 표준점수와 등급을 조회합니다.

**Returns:**
- `dict` or `None`

#### `find_closest_by_standard(subject, standard_score)`

가장 가까운 표준점수의 정보를 반환합니다.

**Returns:**
- `dict` or `None`

#### `find_closest_by_percentile(subject, percentile)`

가장 가까운 백분위의 정보를 반환합니다.

**Returns:**
- `dict` or `None`

#### `get_available_subjects()`

사용 가능한 과목 목록을 반환합니다.

**Returns:**
- `dict`: 과목 분류별 목록

## 실행 예제

```bash
# 기본 예제 실행
python3 score_converter.py

# 사용 예제 실행
python3 score_converter_example.py
```

## 데이터 출처

- 2026학년도 수능 표준점수 도수분포 (국어, 수학)
- 크럭스 테이블 계산기 2026 수능 실채점 기반 (탐구 과목)

## 주의사항

1. 영어와 한국사는 절대평가 과목으로 표준점수가 없습니다.
2. 탐구 과목의 경우 일부 원점수 구간이 데이터에 없을 수 있습니다.
3. `use_closest=True`일 때 반환되는 값은 근사값일 수 있습니다.
4. 백분위는 정수로만 제공됩니다.
5. **원점수 조회는 국어/수학만 지원하며, 선택과목을 반드시 입력해야 합니다.**
6. **등급컷 사이의 원점수는 선형 보간으로 추정되므로 실제 값과 약간 다를 수 있습니다.**

## 라이선스

이 프로젝트는 교육 목적으로 제공됩니다.
