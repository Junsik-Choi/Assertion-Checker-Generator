# 신호 선택 및 필드 입력 고쳐짐 (Auto-Advance Fix)

## 문제점
사용자가 신호나 값을 입력하면:
1. ✓ 체크박스가 생김 (값이 선택됨)
2. ❌ Enter를 눌러도 다음 필드로 진행 안 함
3. ❌ 계속 같은 필드에 갇혀있음

## 해결 방법

### 변경 사항

**1. 힌트 메시지 현대화** (Line 963-970)
```
BEFORE: "field# | set # value | b: back | done: finish | q: quit"
AFTER:  "Enter value | [Enter] to advance | 'prev' or 'p' to go back | 'q' to quit"
```

**2. 필드 자동 진행 (Auto-advance)** 
- choice 필드 (Line ~4710)
- signal 필드 (Line ~4731)  
- string 필드 (Line ~4768)

**변경 전:** 값 입력 → "OK: ..." 메시지 반환 → 사용자가 다시 Enter → (진행 안 됨)

**변경 후:** 값 입력 → 즉시 다음 필드로 자동 진행

### 새로운 동작 흐름

```
Step 1: 어셋션 타입 선택
  입력: 1 (COUNTER)
  → 자동으로 필드 입력 단계로 진행

Step 2a: 신호 선택 (signal 필드)
  입력: 1 (첫 번째 신호)
  → 자동으로 다음 필드로 진행 ✓

Step 2b: 숫자 값 입력 (string 필드)
  입력: 10 (최소값)
  → 자동으로 다음 필드로 진행 ✓

Step 2c: 또 다른 값 입력
  입력: 20 (최대값)
  → 자동으로 확인 단계로 진행 ✓

Step 3: 최종 확인
  입력: [Enter]
  → 어셋션 생성!
```

## 사용 방법

### 일반 입력
```
신호 번호: 1 [Enter]
→ 즉시 다음 필드로 진행 (더 이상 Enter를 두 번 누를 필요 없음)
```

### 네비게이션 명령
어느 필드에서든 사용 가능:
- `prev` 또는 `p` → 이전 필드로 돌아가기
- `b` 또는 `back` → 이전 필드로 돌아가기 (별칭)
- `q` 또는 `quit` → 마법사 취소

## 예제: Pulse Width 어셋션

```
Step 1/3: Pulse Signal
  신호를 선택하세요:
  ✓ [1] [I] i_signal
    [2] [I] o_signal_sync

입력: 1 [Enter]
→ i_signal 저장 후 자동 진행

Step 2/3: Minimum Pulse Width (clocks)
  최소 펄스 너비(클록 사이클)를 입력하세요
  예: 10

입력: 10 [Enter]
→ 10 저장 후 자동 진행

Step 3/3: Maximum Pulse Width (clocks)
  최대 펄스 너비(클록 사이클)를 입력하세요
  예: 20

입력: 20 [Enter]
→ 20 저장 후 확인 단계로 진행

Confirm:
  모든 단계가 완료되었습니다. 검토 후 [Enter]를 눌러 생성하세요.
  
  Configuration:
    Assertion Type: pulseWidth
    target_signal: i_signal
    min_width: 10
    max_width: 20

입력: [Enter]
→ 어셋션 생성됨! ✓
```

## 기술 세부사항

### 수정된 파일
- `scripts/cli_tui.py`

### 변경된 함수
- `_handle_assertion_wizard_command()` - 필드 처리 로직 수정
- 힌트 메시지 표시 로직 업데이트

### 필드 타입별 변경

#### choice 필드
값을 선택하면 다음 필드로 자동 진행
```python
# 값 저장 후 자동으로 다음 필드로
if state.assertion_current_field_idx < len(fields) - 1:
    state.assertion_current_field_idx += 1
    # 다음 필드 정보 반환
else:
    # 모든 필드 완료 → 확인 단계로
```

#### signal 필드
신호를 선택하면 다음 필드로 자동 진행

#### string 필드
값을 입력하면 다음 필드로 자동 진행

## 장점

✓ **더 빠른 어셋션 생성**
✓ **더 직관적인 흐름** (Enter 두 번 누를 필요 없음)
✓ **명확한 사용자 경험**
✓ **동일한 네비게이션** (prev, q 여전히 작동)
✓ **일관된 동작** (모든 필드 타입에서 동일)

## 테스트

```bash
python scripts/cli_tui.py
```

1. 어셋션 타입 선택: `1` (COUNTER)
2. 신호 선택: `1` (첫 번째 신호)
   → 자동으로 다음 필드로 진행 ✓
3. 값 입력: `5`
   → 자동으로 다음 필드로 진행 ✓
4. 값 입력: `10`
   → 자동으로 확인 단계로 진행 ✓
5. 확인: `[Enter]`
   → 어셋션 생성됨 ✓

## 상태
✅ **수정 완료** - 신호 선택 및 필드 입력이 이제 제대로 작동합니다!
