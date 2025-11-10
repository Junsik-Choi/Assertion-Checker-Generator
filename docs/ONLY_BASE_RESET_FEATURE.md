# Counter Assertion: "Only Base Reset" 옵션 추가

## 개선 사항

Reset Condition 선택 단계에 **"Only Base Reset"** 옵션을 추가했습니다.

### 기능 설명

Counter assertion 생성 시 **Step 3: Reset Condition**에서:
- **[0] [*] <Only Base Reset>** : Base reset만 사용 (추가 reset 신호 없음)
- **[1-N]** : 일반 신호 리스트 (기존과 동일)

### 사용 예시

#### TUI 화면
```
Step 3/5: Reset Condition

Select signal/condition for when counter resets

  [0] [*] <Only Base Reset>    <-- 새로 추가된 옵션
  [1] [I] i_blur_mode_cap
  [2] [I] i_den
  [3] [I] i_hsync
  ...

Enter signal [0-N] (0=Only Base Reset) | n/N page | 'prev'/'p' | 'q' to cancel
```

#### 선택 결과

**[0] 선택 시** (Only Base Reset):
- Counter가 base reset (예: I_RSTN)에만 반응
- 추가 reset 조건 없음
- Excel에 빈 문자열로 저장

**[1-N] 선택 시** (일반 신호):
- 선택한 신호를 reset 조건으로 사용
- Base reset + 선택한 신호 모두 counter를 리셋
- Excel에 신호명 저장

## 코드 변경 사항

### 1. Signal 리스트 생성 (`_render_field_input_step`)

**위치**: Line ~4905

```python
# Special option for reset_con field: "Only Base Reset"
if field_name == 'reset_con':
    all_signals.append((0, '<Only Base Reset>', 'special', {}))
    idx = 1  # Start other signals from 1
```

- reset_con 필드일 때만 특별히 인덱스 0에 `<Only Base Reset>` 추가
- 일반 신호는 인덱스 1부터 시작

### 2. Signal 표시 (`_render_field_input_step`)

**위치**: Line ~4965

```python
# Color by signal type
if sig_type == 'special':
    color = _PAIR_BY_NAME.get("green", 0)
    prefix = "[*]"
elif sig_type == 'input':
    # ... (기존 코드)
```

- `special` 타입 신호는 녹색 `[*]` 표시

### 3. Instruction 메시지 (`_render_field_input_step`)

**위치**: Line ~5073

```python
elif current_field['type'] == 'signal':
    if field_name == 'reset_con':
        inst = "Enter signal [0-N] (0=Only Base Reset) | n/N page | 'prev'/'p' | 'q' to cancel"
    else:
        inst = "Enter signal [1-N] | n/N page | 'prev'/'p' for previous | 'q' to cancel"
```

- reset_con 필드일 때만 "[0-N]" 및 설명 표시

### 4. Excel 쓰기 (`_write_assertion_to_excel`)

**위치**: Line ~6160

```python
# Special handling for "<Only Base Reset>" - write empty string
reset_val = data.get('reset_con', '')
if reset_val == '<Only Base Reset>':
    reset_val = ''

ws.cell(row=next_row, column=2, value=target_name)
ws.cell(row=next_row, column=3, value=data.get('plus_con', ''))
ws.cell(row=next_row, column=4, value=reset_val)  # Empty if Only Base Reset
```

- `<Only Base Reset>` 선택 시 Excel에 빈 문자열 저장
- Counter assertion 생성 시 reset 조건이 없다는 의미

## Excel 구조

### Counter Sheet

| Column | Name | Example |
|--------|------|---------|
| B (2) | Target | cnt |
| C (3) | Plus | o_den |
| D (4) | Reset | (empty) or i_reset_sig |
| E (5) | Trigger | i_trigger |
| F (6) | Expect | 5 |

- **Reset 컬럼이 비어있으면** : Only Base Reset 사용
- **Reset 컬럼에 신호명 있으면** : 해당 신호를 reset 조건으로 사용

## Preview 표시

```
============================================================
COUNTER ASSERTION
============================================================

Counter Signal: cnt
Increments when: o_den
Resets when: <Only Base Reset>    <-- 또는 실제 신호명
Checked at: i_trigger
Expected value: 5
Base Clock: I_CLK
Base Reset: I_RSTN

Timing Diagram:
------------------------------------------------------------

Clock cycles: 0   1   2   3   4   5   6   7
         clk |___|‾‾‾|___|‾‾‾|___|‾‾‾|___|‾‾‾|

 cnt (counter) 0   0   1   1   1   0   0   0
o_den (increment) └─────┘   └─────┘   └─────┘
    ? (reset) └───────────────┘       └───────┘
  ? (trigger) └─────┘       └─────┘   └─────┘

Pass:
  ?=1 -> cnt=?

Fail:
  ?=1 -> cnt!=?
```

## 검증 완료

### 테스트 결과 (`test_only_base_reset.py`)

```
✅ ALL TESTS PASSED!

Summary:
  ✅ Reset field is signal type (allows special option)
  ✅ <Only Base Reset> saves as empty string in Excel
  ✅ Regular reset signals save normally
  ✅ Signal list will show [0] <Only Base Reset> option in TUI
```

## 사용 방법

### TUI에서 Counter Assertion 생성

1. Main page → `n` (new) → `1` (counter)
2. Step 1: Counter target signal 입력
3. Step 2: Increment condition 선택
4. **Step 3: Reset Condition**
   - **`0` 입력** → Only Base Reset 사용
   - **`1-N` 입력** → 해당 신호를 reset 조건으로 사용
5. Step 4: Trigger condition 선택
6. Step 5: Expected count value 입력
7. Review & Create

### 예시 시나리오

#### 시나리오 1: Base Reset만 사용
```
Counter: cnt
Increment: o_den
Reset: 0        <-- Only Base Reset
Trigger: valid
Expected: 5

→ cnt는 I_RSTN에만 반응하여 reset됨
```

#### 시나리오 2: 추가 Reset 신호 사용
```
Counter: cnt
Increment: o_den
Reset: 10       <-- i_error_reset 신호
Trigger: valid
Expected: 5

→ cnt는 I_RSTN 또는 i_error_reset 발생 시 reset됨
```

## 주의사항

1. **[0] 옵션은 reset_con 필드에만 표시**
   - 다른 signal 필드(plus_con, trigger_con 등)에는 표시되지 않음
   
2. **Excel에는 빈 문자열로 저장**
   - 복원 시 빈 문자열이면 base reset만 사용한다는 의미
   
3. **Index 0부터 시작**
   - 일반 신호는 index 1부터 시작
   - Pagination도 정상 작동

## 개선 완료 ✅

모든 요구사항 구현 및 테스트 완료:
- ✅ Reset Condition 단계에 [0] <Only Base Reset> 옵션 추가
- ✅ 녹색 [*] 표시로 구분
- ✅ Instruction에 "(0=Only Base Reset)" 설명 추가
- ✅ Excel에 빈 문자열로 저장
- ✅ 일반 reset 신호와 구분하여 처리
