# Delete Command (del) - 사용 가이드

## 개요 (Overview)

`del` 명령어를 사용하여 생성된 MS 시그널과 assertion을 삭제할 수 있습니다.
또한 MS 시그널은 중복된 이름으로 생성할 수 없도록 보호됩니다.

---

## 주요 기능

### 1. MS 시그널 삭제
- **명령어**: `del ms <name>`
- **설명**: 이름으로 MS 시그널 삭제
- **자동 업데이트**: Define sheet도 함께 업데이트

### 2. Assertion 삭제
- **명령어**: `del assertion <index>`
- **설명**: 인덱스 번호로 assertion 삭제
- **자동 재정렬**: 삭제 후 시트 번호 자동 재배열

### 3. MS 시그널 중복 방지
- 같은 이름의 MS 시그널 생성 시도 시 에러 발생
- 명확한 에러 메시지와 함께 기존 시그널 보호

---

## 사용 방법

### MS 시그널 삭제

#### 기본 사용법
```bash
# MS 시그널 생성
> ms valid_signal = i_clk & i_valid
✓ Condition added: valid_signal (1bits)

# MS 시그널 삭제
> del ms valid_signal
✓ MS signal 'valid_signal' deleted - Define sheet updated
```

#### 존재하지 않는 시그널 삭제 시도
```bash
> del ms nonexistent
ERROR: MS signal 'nonexistent' not found
```

#### 여러 MS 시그널 관리
```bash
# 여러 시그널 생성
> ms sig1 = i_clk
> ms sig2 = i_valid
> ms sig3 = i_ready

# 특정 시그널만 삭제
> del ms sig2
✓ MS signal 'sig2' deleted

# 남은 시그널: sig1, sig3
```

---

### Assertion 삭제

#### 기본 사용법
```bash
# Assertion 목록 확인 (메인 화면에서)
Assertions:
  1. counter - my_counter
  2. handshake - my_handshake
  3. pulseWidth - my_pulse
  4. hact - my_hact

# Assertion 삭제 (3번 삭제)
> del assertion 3
✓ Assertion #3 deleted (pulseWidth: my_pulse)

# 자동 재정렬 후:
Assertions:
  1. counter - my_counter
  2. handshake - my_handshake
  3. hact - my_hact
```

#### 인덱스 범위 확인
```bash
# 범위 밖의 인덱스
> del assertion 10
ERROR: Index out of range. Valid range: 1-4

# 잘못된 입력
> del assertion abc
ERROR: Index must be a number
```

#### 첫 번째/마지막 Assertion 삭제
```bash
# 첫 번째 삭제
> del assertion 1
✓ Assertion #1 deleted (counter: my_counter)

# 마지막 삭제 (현재 3개 남음)
> del assertion 3
✓ Assertion #3 deleted (hact: my_hact)
```

---

### MS 시그널 중복 방지

#### 중복 생성 시도
```bash
# 첫 번째 시그널 생성
> ms valid_signal = i_clk & i_valid
✓ Condition added: valid_signal (1bits)

# 같은 이름으로 다시 생성 시도
> ms valid_signal = i_ready
ERROR: MS signal 'valid_signal' already exists

에러 메시지 (빨간색 표시):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MS signal 'valid_signal' already exists. 
Use a different name or delete it first with: 
del ms valid_signal
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### 해결 방법
```bash
# 옵션 1: 다른 이름 사용
> ms valid_signal2 = i_ready
✓ Condition added: valid_signal2 (1bits)

# 옵션 2: 기존 시그널 삭제 후 재생성
> del ms valid_signal
✓ MS signal 'valid_signal' deleted

> ms valid_signal = i_ready
✓ Condition added: valid_signal (1bits)
```

---

## 사용 시나리오

### 시나리오 1: MS 시그널 교체

```bash
# 1. 기존 시그널 확인
MS Signals:
  - old_valid = i_clk & i_en

# 2. 새로운 표현식으로 교체하고 싶음
> ms old_valid = i_clk & i_valid & i_ready
ERROR: MS signal 'old_valid' already exists

# 3. 기존 시그널 삭제
> del ms old_valid
✓ MS signal 'old_valid' deleted

# 4. 새로운 표현식으로 재생성
> ms old_valid = i_clk & i_valid & i_ready
✓ Condition added: old_valid (1bits)
```

### 시나리오 2: Assertion 재작성

```bash
# 1. 잘못 만든 assertion 확인
Assertions:
  1. counter - wrong_counter (잘못된 설정)
  2. handshake - correct_handshake

# 2. 삭제
> del assertion 1
✓ Assertion #1 deleted (counter: wrong_counter)

# 3. 올바르게 재생성
> new
> [counter 선택 및 올바른 설정으로 생성]
✓ Assertion created
```

### 시나리오 3: 정리 작업

```bash
# 불필요한 MS 시그널 여러 개 삭제
> del ms temp1
✓ MS signal 'temp1' deleted

> del ms temp2
✓ MS signal 'temp2' deleted

> del ms debug_sig
✓ MS signal 'debug_sig' deleted

# 테스트용 assertion 삭제
> del assertion 5
✓ Assertion #5 deleted (counter: test_assertion)

> del assertion 4
✓ Assertion #4 deleted (handshake: test_handshake)
```

---

## 에러 메시지

### MS 시그널 관련

| 에러 메시지 | 원인 | 해결 방법 |
|------------|------|----------|
| `MS signal '<name>' already exists` | 중복된 이름 사용 | 다른 이름 사용 또는 기존 시그널 삭제 |
| `MS signal '<name>' not found` | 존재하지 않는 시그널 삭제 시도 | 시그널 이름 확인 |
| `Usage: del ms <name>` | 시그널 이름 누락 | `del ms <name>` 형식으로 입력 |

### Assertion 관련

| 에러 메시지 | 원인 | 해결 방법 |
|------------|------|----------|
| `Index must be a number` | 숫자가 아닌 값 입력 | 숫자로 입력 (예: `del assertion 3`) |
| `Index out of range. Valid range: 1-N` | 범위 밖 인덱스 | 유효한 범위 내 인덱스 사용 |
| `No assertions found in session Excel` | Assertion이 없음 | `new` 명령어로 assertion 생성 |
| `No session Excel found` | 세션이 없음 | 온보딩 완료 또는 세션 로드 |

---

## 기술 세부사항

### MS 시그널 삭제 프로세스

1. **검증**: 시그널 이름이 존재하는지 확인
2. **삭제**: `state.conditions` 리스트에서 제거
3. **저장**: 세션 스냅샷 저장
4. **업데이트**: Excel Define sheet 업데이트
5. **확인**: 성공 메시지 표시

```python
# 내부 구현 로직
signal_name = "valid_signal"
original_count = len(state.conditions)
state.conditions = [cond for cond in state.conditions 
                    if cond.get("name", "") != signal_name]

if len(state.conditions) == original_count:
    # 시그널을 찾지 못함
    return "ERROR: MS signal not found"

# 세션 저장 및 Excel 업데이트
_save_session_snapshot(state)
_update_define_sheet(state)
```

### Assertion 삭제 프로세스

1. **검증**: 인덱스 유효성 확인
2. **로드**: Excel 파일에서 assertion sheets 목록 조회
3. **삭제**: 해당 인덱스의 sheet 삭제
4. **재정렬**: 남은 sheets를 1부터 순차적으로 재번호
5. **저장**: Excel 파일 저장
6. **확인**: 성공 메시지 표시 (타입과 이름 포함)

```python
# 내부 구현 로직
idx = 3  # 삭제할 assertion 인덱스

# 1. Assertion sheets 목록 (숫자 이름만)
assertion_sheets = [(1, "1"), (2, "2"), (3, "3"), (4, "4")]

# 2. 삭제할 sheet
sheet_num, sheet_name = assertion_sheets[idx - 1]  # (3, "3")

# 3. Sheet 삭제
del wb[sheet_name]

# 4. 재정렬 (3번 이후의 sheets를 하나씩 앞으로)
for new_idx, (old_num, old_name) in enumerate(remaining_sheets, start=1):
    if old_num > sheet_num:
        ws = wb[old_name]
        ws.title = str(new_idx)

# 결과: [1, 2, 3, 4] -> [1, 2, 3]
```

### 중복 방지 체크

```python
# MS 시그널 생성 시 중복 확인
name = "valid_signal"
existing_names = [cond.get("name", "") for cond in state.conditions]

if name in existing_names:
    _set_error_message(f"MS signal '{name}' already exists. "
                      f"Use a different name or delete it first with: "
                      f"del ms {name}")
    return f"ERROR: MS signal '{name}' already exists", False
```

---

## 명령어 요약

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `del ms <name>` | MS 시그널 삭제 | `del ms valid_signal` |
| `del assertion <index>` | Assertion 삭제 | `del assertion 3` |
| `ms <name> = <expr>` | MS 시그널 생성 (중복 방지) | `ms sig = i_clk & i_en` |

---

## 참고 사항

### 삭제 시 주의사항

1. **MS 시그널 삭제**
   - 다른 MS 시그널이나 assertion에서 참조 중인 시그널 삭제 시 오류 발생 가능
   - 삭제 전 의존성 확인 권장

2. **Assertion 삭제**
   - 삭제된 assertion은 복구할 수 없음
   - Excel 파일에서 영구적으로 제거됨
   - Sheet 번호가 자동으로 재정렬됨

3. **세션 저장**
   - 모든 삭제 작업은 즉시 세션에 저장됨
   - Excel 파일도 자동으로 업데이트됨

### 권장 워크플로우

```bash
# 1. 현재 상태 확인
[메인 화면에서 MS Signals와 Assertions 패널 확인]

# 2. 삭제할 항목 선택
> del ms old_signal
또는
> del assertion 2

# 3. 결과 확인
[메인 화면에서 삭제 확인]

# 4. 필요시 재생성
> ms new_signal = ...
또는
> new
```

---

## FAQ

### Q1: MS 시그널을 삭제하면 Define sheet는 어떻게 되나요?
**A:** 자동으로 업데이트되어 삭제된 시그널이 제거됩니다.

### Q2: Assertion 삭제 후 번호가 어떻게 바뀌나요?
**A:** 자동으로 1부터 순차적으로 재정렬됩니다.
- 예: [1, 2, 3, 4, 5]에서 3 삭제 → [1, 2, 3, 4]

### Q3: 삭제한 것을 복구할 수 있나요?
**A:** 불가능합니다. 삭제 전 신중하게 확인하세요.

### Q4: 여러 개를 한 번에 삭제할 수 있나요?
**A:** 현재는 개별 삭제만 지원합니다. 여러 개 삭제 시 반복 실행하세요.

### Q5: MS 시그널 이름을 변경할 수 있나요?
**A:** 직접 변경은 불가능합니다. 삭제 후 새 이름으로 재생성하세요.
```bash
> del ms old_name
> ms new_name = <same_expression>
```

---

## 테스트 결과

### Test Suite: `dev/test_del_command.py`

```
✓ Test 1: MS signal duplicate prevention
  - 중복 이름 감지 성공
  
✓ Test 2: Delete existing MS signal
  - 시그널 삭제 성공
  - Define sheet 업데이트 확인
  
✓ Test 3: Delete non-existent MS signal
  - 적절한 에러 메시지
  
✓ Test 4: Delete assertion
  - Assertion 삭제 성공
  - Sheet 재정렬 확인
  
✓ Test 5: Delete assertion out of range
  - 범위 검증 성공

ALL TESTS PASSED!
```

---

## 관련 문서

- `docs/CUSTOM_EXPRESSION_FIX.md` - 커스텀 표현식 개선
- `docs/NEW_ASSERTION_TYPES_IMPLEMENTATION.md` - 새로운 assertion 타입
- `scripts/help_config.json` - Help 명령어 레퍼런스

---

## 변경 이력

### 2025-01-14
- ✨ `del ms <name>` 명령어 추가
- ✨ `del assertion <index>` 명령어 추가
- ✨ MS 시그널 중복 이름 방지 기능 추가
- ✨ Assertion sheet 자동 재정렬 구현
- ✨ Help 문서에 del 명령어 추가
- ✅ 테스트 스위트 추가 및 검증 완료

---

**요약:** `del` 명령어로 MS 시그널과 assertion을 안전하게 삭제할 수 있으며, MS 시그널 중복 생성이 자동으로 방지됩니다.
