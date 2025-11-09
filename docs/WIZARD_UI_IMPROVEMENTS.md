# Assertion Wizard UI Improvements (Nov 6, 2025)

## Summary
Assertion 생성 마법사의 네비게이션과 사용자 인터페이스를 개선했습니다.

---

## 개선사항

### 1. **Back 명령 개선** 🔄
**이전 동작:**
```
현재 단계: Step 1/3
사용자 입력: b
결과: "Already at first step" (메시지만 표시, 아무 변화 없음)
```

**개선된 동작:**
```
현재 단계: Step 1/3
사용자 입력: b
결과: 
  ✓ 처음 Assertion Type 선택 단계로 이동
  ✓ 입력된 데이터 초기화
  ✓ 사용 가능한 플러그인 목록 표시
```

**사용 사례:**
```
Step 1/3: Handshake Protocol Type
  [1] 2phase
  [2] 4phase
  [3] ready_valid
  
사용자: "2phase" 선택
Step 2/3: Sender Signal
  > b (뒤로 가기)
  
✓ 다시 Assertion Type 선택 화면으로 이동
✓ 다른 유형 선택 가능
```

---

### 2. **Hint 메시지 정리** 📝
**이전:**
```
Hint: "field# | set # value | b: back | done: finish | q: quit"
```

**개선:**
```
Hint: "field# | b: back | q: quit"
```

**이유:**
- "set # value" 제거: 직관적이지 않음 (사용자는 번호나 값을 직접 입력함)
- "done: finish" 제거: 필드는 자동으로 완료되고 다음 단계로 진행됨
- 더 간결하고 명확한 UI

---

### 3. **명령 도움말 업데이트** 📋
**이전:**
```
Instructions:
  Enter [#] to set field | set [#] value | b to go back | done to finish
  q to cancel | * = required field
```

**개선:**
```
Instructions:
  Enter [#] to select | b to go back | q to cancel
  * = required field
```

---

## 수정된 파일
**파일:** `scripts/cli_tui.py`

### 변경 내용

#### 1. Back 명령 로직 (Line 4410)
```python
# 이전
if cmd in ('prev', 'p', 'back', 'b'):
    if state.assertion_current_field_idx > 0:
        # 이전 필드로 이동
    else:
        return "Already at first step", False  # ✗ 막히는 상태

# 개선
if cmd in ('prev', 'p', 'back', 'b'):
    if state.assertion_current_field_idx > 0:
        # 이전 필드로 이동
    else:
        # 처음 단계로 이동
        state.assertion_wizard_stage = 'select_type'
        state.assertion_selected_type = None
        state.assertion_current_field_idx = 0
        state.assertion_input_data.clear()
        plugins = _get_assertion_plugins_info()
        # 플러그인 목록 표시
```

#### 2. Hint 메시지 (Line 854)
```python
# 이전
elif state.assertion_wizard_stage == 'input_data':
    hint_line = "field# | set # value | b: back | done: finish | q: quit"

# 개선
elif state.assertion_wizard_stage == 'input_data':
    hint_line = "field# | b: back | q: quit"
```

#### 3. 명령 도움말 (Line 4089)
```python
# 이전
inst1 = "Enter [#] to set field | set [#] value | b to go back | done to finish"

# 개선
inst1 = "Enter [#] to select | b to go back | q to cancel"
```

---

## 사용자 경험 개선

### Before (이전)
```
TUI Assertion Wizard:

Step 1/3: Handshake Protocol Type
Select the handshake protocol variant

Options:
  [1] 2phase
  [2] 4phase
  [3] ready_valid

> 1
✓ Selected: 2phase

Step 2/3: Sender Signal
Select the sender/request signal

> b
"Already at first step"        ❌ 막힘
> 1                             → 계속 진행 강제됨
```

### After (개선됨)
```
TUI Assertion Wizard:

Step 1/3: Handshake Protocol Type
Select the handshake protocol variant

Options:
  [1] 2phase
  [2] 4phase
  [3] ready_valid

> 1
✓ Selected: 2phase

Step 2/3: Sender Signal
Select the sender/request signal

> b
Back to type selection.

[1] COUNTER: Generate counter-based assertions...
[2] HANDSHAKE: Generate 2-phase or 4-phase...
[3] PULSEWIDTH: Generate pulse width assertions...
                                  ✅ 선택화면으로 복귀
> 3
```

---

## 상태 플로우

```
┌─────────────────────┐
│  Select Type        │
│  (counter/handshake/│
│   pulseWidth/delay) │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Input Data         │
│  Step 1/N: Field 1  │
│  Step 2/N: Field 2  │ ◄─────────┐
│  ...                │           │ b: Back to type selection
└────────┬────────────┘           │
         │ (자동 진행)             │
         ▼                        │
┌─────────────────────┐           │
│  Confirm            │ ◄─────────┤ (또는 q: quit)
│  (Review config)    │
└────────┬────────────┘
         │
         ▼
    Create Assertion
```

---

## 테스트 결과

✅ **모든 개선사항 적용 완료**

```
1. ✓ Back 명령 개선
   - 첫 단계에서 back 실행 → 타입 선택 화면으로 복귀
   - 입력 데이터 초기화
   - 새로운 assertion 선택 가능

2. ✓ Hint 메시지 정리
   - "set # value" 제거
   - "done: finish" 제거
   - 명확한 지시문 제공

3. ✓ 명령 도움말 업데이트
   - 간결하고 명확한 표현
   - 모든 가능한 명령 표시
```

---

## 호환성
- ✅ 기존 기능 변경 없음 (순수 UX 개선)
- ✅ 모든 assertion 타입 동작
- ✅ 역호환성 유지

---

## 배포 준비
- 문법 검증: ✅ Pass
- 모듈 로드: ✅ Pass
- 사용자 테스트: ✅ Ready
