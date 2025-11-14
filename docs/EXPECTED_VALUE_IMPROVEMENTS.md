# Expected Value Improvements - 구현 완료

## 개요 (Overview)

Expected Min/Max Value 입력 시 사용성을 대폭 개선했습니다:

### 주요 변경사항

1. **파라미터 값 표시** 💡
   - Signal 선택 시 파라미터 값이 함께 표시됨
   - 예: `[P] HBP_MIN (=148)`
   - 사용자가 파라미터의 현재 값을 즉시 확인 가능

2. **Expected Value 입력 방식 확장** 🎯
   - 기존: 숫자만 직접 입력
   - 개선: **파라미터, 포트, MS 신호, 숫자 모두 선택 가능**
   - 리스트에서 선택하거나 직접 입력 가능

3. **0 입력으로 커스텀 표현식** ✍️
   - 0을 입력하면 커스텀 표현식 입력 모드로 전환
   - 파라미터 이름, 숫자, 표현식 모두 입력 가능
   - 예: `HBP_MIN`, `148`, `WIDTH*2`, `PARAM+10`

4. **적용 범위** 📋
   - HACT, HSW, HBP, HFP, VBP, VFP, VSW 모든 타입
   - 총 7개 assertion 타입의 14개 필드 개선

---

## 1. 파라미터 값 표시

### 이전 (Before)
```
Step 3/4: Expected Min Value
  [0] [*] Custom Expression
  [1] [I] i_clk
  [2] [I] i_hsync
  [3] [O] o_data
  [4] [P] WIDTH           ← 값을 알 수 없음!
  [5] [P] HBP_MIN         ← 값을 알 수 없음!
  [6] [P] HBP_MAX         ← 값을 알 수 없음!
```

### 개선 (After)
```
Step 3/4: Expected Min Value
  [0] [*] Custom Expression
  [1] [I] i_clk
  [2] [I] i_hsync
  [3] [O] o_data
  [4] [P] WIDTH (=8)      ← 값을 바로 확인!
  [5] [P] HBP_MIN (=148)  ← 값을 바로 확인!
  [6] [P] HBP_MAX (=220)  ← 값을 바로 확인!
```

### 구현 위치
**scripts/cli_tui.py** Line ~5506

```python
elif sig_type == 'parameter':
    color = _PAIR_BY_NAME.get("blue", 0)
    prefix = "[P]"
    # Add parameter value if available
    param_val = port_dict.get('default', '')
    if param_val:
        name = f"{name} (={param_val})"
```

### 장점
- ✅ 파라미터 값을 즉시 확인 가능
- ✅ 올바른 파라미터 선택 가능
- ✅ 값을 기억할 필요 없음
- ✅ 실수 방지

---

## 2. Expected Value 입력 방식 확장

### 이전 (Before)
```yaml
expected_min_value:
  type: 'string'
  description: 'Enter minimum expected value'
  example: '148'
```

입력 방식:
- ❌ 숫자만 직접 타이핑
- ❌ 파라미터 이름 직접 타이핑 (값 확인 불가)
- ❌ 리스트에서 선택 불가

### 개선 (After)
```yaml
expected_min_value:
  type: 'signal'
  description: 'Select signal/parameter or enter number (0 for custom expression)'
  example: 'Select signal, parameter, or enter number like 148'
```

입력 방식:
- ✅ **리스트에서 파라미터 선택** (값 확인하며 선택)
- ✅ **리스트에서 포트 선택** (필요시)
- ✅ **리스트에서 MS 신호 선택** (필요시)
- ✅ 숫자 직접 입력
- ✅ 0 입력하여 커스텀 표현식 입력

### 구현 위치
**scripts/cli_tui.py** Line ~4909, 4947, 4985, 5023, 5061, 5099, 5137

각 assertion 타입의 expected_min_value와 expected_max_value 필드:

```python
# HACT
{
    'name': 'expected_min_value',
    'type': 'signal',  # 'string'에서 변경
    'step': 3,
    'title': 'Expected Min Value',
    'description': 'Select signal/parameter or enter number (0 for custom expression)',
    'example': 'Select signal, parameter, or enter number like 1920',
    'required': True,
},

# HSW, HBP, HFP, VBP, VFP, VSW도 동일하게 변경
```

---

## 3. 0 입력으로 커스텀 표현식

### 동작 방식

#### 이전 (Before)
```
Step 3/4: Expected Min Value
User enters: 148
✓ Saved as "148"
```

한 가지 방법만 가능 (직접 타이핑)

#### 개선 (After)

**방법 1: 리스트에서 선택**
```
Step 3/4: Expected Min Value
  [5] [P] HBP_MIN (=148)
User enters: 5
✓ Saved as "HBP_MIN"
```

**방법 2: 숫자 직접 입력**
```
Step 3/4: Expected Min Value
User enters: 148
✓ Saved as "148"
```

**방법 3: 0 입력 → 커스텀 표현식**
```
Step 3/4: Expected Min Value
User enters: 0

Prompt: Enter custom value (number, parameter name, or expression like 'PARAM+10'):

User can type:
  - HBP_MIN         (parameter name)
  - 148             (number)
  - WIDTH*2         (expression)
  - PARAM+10        (expression)
  - HBP_MIN-5       (expression)
```

### 구현 위치
**scripts/cli_tui.py** Line ~6975

```python
# Special handling for fields that expect numbers: [0] = Custom Number/Expression Input
# exp_cnt_val, expected_min_value, expected_max_value use custom number/expression
if field_name in ('exp_cnt_val', 'expected_min_value', 'expected_max_value') and idx == 0:
    state.assertion_waiting_custom_expr = True
    return "Enter custom value (number, parameter name, or expression like 'PARAM+10'):", False

# Special handling for ALL other signal fields: [0] = Custom Expression Input
if field_name not in ('exp_cnt_val', 'expected_min_value', 'expected_max_value') and idx == 0:
    _set_error_message("")  # Clear any previous error
    state.assertion_waiting_custom_expr = True
    return "Enter custom expression using actual signal names (e.g., '(i_sram_rd1 && i_sram_rd2) | i_sram_rd3'):", False
```

---

## 4. 적용된 Assertion 타입

### 개선된 타입 목록

| 타입 | Expected Min/Max 사용 | 개선 완료 |
|------|------------------------|-----------|
| **HACT** | ✓ (픽셀 수) | ✅ |
| **HSW** | ✓ (Sync 폭) | ✅ |
| **HBP** | ✓ (Back Porch) | ✅ |
| **HFP** | ✓ (Front Porch) | ✅ |
| **VBP** | ✓ (Vertical BP) | ✅ |
| **VFP** | ✓ (Vertical FP) | ✅ |
| **VSW** | ✓ (Vertical SW) | ✅ |
| counter | ❌ (다른 방식) | N/A |
| handshake | ❌ | N/A |
| pulseWidth | ✓ (min/max_width 별도) | 기존 유지 |

### 필드 변경 요약
- **총 7개 assertion 타입**
- **각 타입당 2개 필드 (min, max)**
- **총 14개 필드 개선**

---

## 사용 예시

### 예시 1: HBP Assertion with Parameters

#### Step-by-Step 워크플로우

```bash
# 1. 파라미터 정의
> param HBP_MIN=148
✓ Parameter added: HBP_MIN=148

> param HBP_MAX=220
✓ Parameter added: HBP_MAX=220

# 2. Assertion 생성 시작
> new
Select Assertion Type:
  [1] COUNTER
  [2] HANDSHAKE
  [3] PULSEWIDTH
  [4] HACT
  [5] HSW
  [6] HBP      ← 선택
  ...

> 6

# 3. Step 1/4: Hsync Signal
Select hsync signal:
  [0] [*] Custom Expression
  [1] [I] i_clk
  [2] [I] i_hsync      ← 선택
  [3] [O] o_data
  [4] [P] WIDTH (=8)
  [5] [P] HBP_MIN (=148)
  [6] [P] HBP_MAX (=220)

> 2

# 4. Step 2/4: Data Enable Signal
> 3

# 5. Step 3/4: Expected Min Value
Select or enter min value:
  [0] [*] Custom Expression
  [1] [I] i_clk
  [2] [I] i_hsync
  [3] [O] o_data
  [4] [P] WIDTH (=8)
  [5] [P] HBP_MIN (=148)    ← 선택 (값 확인 가능!)
  [6] [P] HBP_MAX (=220)

> 5
✓ Set to: HBP_MIN

# 6. Step 4/4: Expected Max Value
> 6
✓ Set to: HBP_MAX

# 7. Confirm
Press Enter to create
> [Enter]
✓ Assertion created
```

### 예시 2: 직접 숫자 입력

```bash
> new
> 6  # HBP
> 2  # i_hsync
> 3  # i_de

# Min value: 숫자 직접 입력
> 148
✓ Set to: 148

# Max value: 숫자 직접 입력
> 220
✓ Set to: 220

> [Enter]
✓ Assertion created
```

### 예시 3: 커스텀 표현식 사용

```bash
> new
> 6  # HBP
> 2  # i_hsync
> 3  # i_de

# Min value: 커스텀 입력 모드
> 0
Enter custom value (number, parameter name, or expression like 'PARAM+10'):
> HBP_MIN
✓ Set to: HBP_MIN

# Max value: 커스텀 표현식
> 0
Enter custom value:
> HBP_MIN+72
✓ Set to: HBP_MIN+72

> [Enter]
✓ Assertion created
```

### 예시 4: 해상도별 파라미터 활용

```bash
# 1080p 설정
> param HACT_1080P=1920
> param VBP_1080P=36
> param HBP_1080P=148

# Assertion 생성 (리스트에서 선택)
> new
> 6  # HBP
> 2  # i_hsync
> 3  # i_de
> 7  # [P] HBP_1080P (=148) 선택
> 7  # [P] HBP_1080P (=148) 선택
> [Enter]

# 나중에 720p로 변경
> param HBP_1080P=220
✓ Parameter updated from 148 to 220

# 새로운 assertion은 자동으로 220 사용
```

---

## 입력 방법 비교

### 시나리오: HBP Min Value = 148 입력

| 방법 | 입력 | 장점 | 단점 |
|------|------|------|------|
| **리스트 선택** | `5` | • 값 확인 가능<br>• 빠름<br>• 오타 없음 | • 파라미터가 미리 정의되어야 함 |
| **직접 숫자** | `148` | • 빠름<br>• 파라미터 불필요 | • 값을 기억해야 함<br>• 하드코딩 |
| **0 + 파라미터명** | `0` → `HBP_MIN` | • 유연함<br>• 나중에 변경 가능 | • 두 단계 필요 |
| **0 + 표현식** | `0` → `HBP_MIN+10` | • 계산 가능<br>• 매우 유연함 | • 복잡함 |

---

## 비교: Before vs After

### 파라미터 선택

| 항목 | Before | After |
|------|--------|-------|
| **파라미터 값 확인** | 불가능 (param 명령으로 따로 확인) | 가능 ([P] HBP_MIN (=148)) |
| **선택 방법** | 이름 직접 타이핑 | 리스트에서 선택 가능 |
| **오타 가능성** | 높음 (직접 입력만 가능) | 낮음 (리스트 선택 가능) |

### Expected Value 입력

| 기능 | Before | After |
|------|--------|-------|
| **필드 타입** | `string` | `signal` |
| **파라미터 선택** | 이름 타이핑만 | 리스트 선택 or 타이핑 |
| **포트 선택** | 불가능 | 가능 |
| **MS 신호 선택** | 불가능 | 가능 |
| **숫자 입력** | 직접 타이핑 | 직접 타이핑 or 리스트 |
| **표현식 입력** | 불가능 | 0 입력 후 가능 |

### 사용자 경험

| 상황 | Before | After |
|------|--------|-------|
| **값 확인** | 다른 터미널에서 확인 | 리스트에서 즉시 확인 |
| **파라미터 사용** | 이름 외우고 타이핑 | 리스트에서 선택 |
| **복잡한 값** | 수동 계산 후 입력 | 표현식으로 입력 (예: WIDTH*2) |

---

## 테스트 결과

### Test Suite: `dev/test_expected_value_improvements.py`

```
✅ Test 1: Parameters display with values [P] WIDTH (=8)
✅ Test 2: Expected value fields are 'signal' type
✅ Test 3: 0 input triggers custom expression mode
✅ Test 4: Example workflow demonstrated
✅ Test 5: Field descriptions are comprehensive

ALL TESTS PASSED! 🎉
```

### 테스트 세부 내용

**Test 1: 파라미터 값 표시**
```
Signal list display:
  [0] [*] <Custom Expression>
  [1] [I] i_clk
  [2] [I] i_hsync
  [3] [O] o_data
  [4] [P] WIDTH (=8)
  [5] [P] HBP_MIN (=148)
  [6] [P] HBP_MAX (=220)
✓ All parameters display their values correctly
```

**Test 2: 필드 타입 검증**
```
HACT: expected_min_value type: signal ✓
HSW:  expected_min_value type: signal ✓
HBP:  expected_min_value type: signal ✓
HFP:  expected_min_value type: signal ✓
VBP:  expected_min_value type: signal ✓
VFP:  expected_min_value type: signal ✓
VSW:  expected_min_value type: signal ✓
```

**Test 3: 커스텀 모드 전환**
```
exp_cnt_val:         0 → custom value/expression ✓
expected_min_value:  0 → custom value/expression ✓
expected_max_value:  0 → custom value/expression ✓
target_signal:       0 → signal expression ✓
```

---

## 실제 사용 사례

### 사례 1: 비디오 타이밍 검증

```bash
# 1080p 타이밍 파라미터 정의
> param HACT_1080P=1920
> param HBP_1080P=148
> param HFP_1080P=88
> param HSW_1080P=44
> param VACT_1080P=1080
> param VBP_1080P=36
> param VFP_1080P=4
> param VSW_1080P=5

# HBP Assertion 생성 (리스트에서 바로 선택)
> new
> 6  # HBP
> 2  # i_hsync
> 3  # i_de
> 5  # [P] HBP_1080P (=148) ← 값 확인하며 선택!
> 5  # [P] HBP_1080P (=148)
> [Enter]

# 720p 전환 (파라미터만 변경)
> param HBP_1080P=220
✓ Updated from 148 to 220

# 새 assertion 생성 시 자동으로 220 반영
```

### 사례 2: 동적 값 계산

```bash
# 기본 파라미터
> param BASE_WIDTH=100
> param MARGIN=10

# Min value = BASE_WIDTH
# Max value = BASE_WIDTH + MARGIN
> new
> 5  # HSW
> 2  # count_trigger
> 3  # target_pulse
> 0  # custom input
> BASE_WIDTH
> 0  # custom input
> BASE_WIDTH+MARGIN
> [Enter]

# 결과: Min=100, Max=110 (표현식 자동 계산)
```

### 사례 3: 여러 해상도 테스트

```bash
# 해상도별 파라미터 세트
> param HBP_480P=60
> param HBP_720P=220
> param HBP_1080P=148
> param HBP_4K=296

# Assertion 생성 시 리스트에서 선택
Step 3/4: Expected Min Value
  [4] [P] HBP_480P (=60)
  [5] [P] HBP_720P (=220)
  [6] [P] HBP_1080P (=148)   ← 선택
  [7] [P] HBP_4K (=296)

# 값을 보면서 올바른 해상도 선택 가능!
```

---

## FAQ

### Q1: 파라미터 값이 표시되지 않으면?
**A:** `param` 명령으로 파라미터를 먼저 정의해야 합니다.
```bash
> param HBP_MIN=148
> param HBP_MAX=220
```

### Q2: 숫자를 직접 입력하고 싶은데 리스트만 나와요?
**A:** 그냥 숫자를 입력하면 됩니다! 리스트는 참고용이고, 숫자를 바로 타이핑할 수 있습니다.
```bash
> 148  # 그냥 입력!
```

### Q3: 표현식은 어떻게 입력하나요?
**A:** 0을 입력하면 커스텀 입력 모드로 전환됩니다.
```bash
> 0
Enter custom value:
> WIDTH*2
# 또는
> HBP_MIN+10
# 또는
> (WIDTH+MARGIN)*2
```

### Q4: 파라미터 이름과 숫자 중 무엇을 사용해야 하나요?
**A:** 
- **파라미터 사용 권장**: 나중에 값을 변경할 수 있음
- **숫자 사용**: 고정된 값이거나 테스트용

```bash
# 권장: 파라미터 사용 (유연함)
> param HBP_MIN=148
> new
> 5  # 파라미터 선택

# 또는: 숫자 사용 (간단함)
> new
> 148  # 직접 입력
```

### Q5: 0을 값으로 사용하고 싶은데요?
**A:** 0을 입력하면 커스텀 모드로 전환되므로, 리스트에서 0 값을 가진 파라미터를 선택하거나, 커스텀 모드에서 0을 입력하세요.
```bash
# 방법 1: 파라미터 선택
> param MIN_VAL=0
> new
> 5  # [P] MIN_VAL (=0) 선택

# 방법 2: 커스텀 모드
> 0
Enter custom value:
> 0
```

### Q6: 기존 assertion은 어떻게 되나요?
**A:** 기존 assertion은 영향받지 않습니다. 새로 생성하는 assertion부터 개선된 방식을 사용할 수 있습니다.

---

## 수정 사항 요약

| 파일 | 라인 | 변경 내용 |
|------|------|----------|
| `cli_tui.py` | ~5506 | 파라미터 값 표시 로직 추가 |
| `cli_tui.py` | ~4909, 4947, 4985, 5023, 5061, 5099, 5137 | expected_min/max_value 필드 타입 변경 (string → signal) |
| `cli_tui.py` | ~6975 | 0 입력 시 커스텀 모드 전환 로직 수정 |

**총 수정 라인**: ~30 lines  
**영향받는 assertion 타입**: 7개 (HACT, HSW, HBP, HFP, VBP, VFP, VSW)  
**테스트 파일**: `dev/test_expected_value_improvements.py`

---

## 완료 ✅

- ✅ 파라미터 값이 리스트에 표시됨: `[P] HBP_MIN (=148)`
- ✅ Expected min/max value 필드가 'signal' 타입으로 변경됨
- ✅ 파라미터를 리스트에서 선택 가능
- ✅ 포트와 MS 신호도 선택 가능
- ✅ 숫자 직접 입력 가능
- ✅ 0 입력으로 커스텀 표현식 모드 전환
- ✅ 표현식 입력 가능 (예: `WIDTH*2`, `PARAM+10`)
- ✅ 7개 assertion 타입 모두 적용
- ✅ 테스트 완료 및 통과

**이제 Expected Value 입력이 훨씬 편리하고 유연해졌습니다!** 🎉

## 핵심 개선점

1. **가시성**: 파라미터 값을 보면서 선택
2. **편의성**: 리스트 선택 + 직접 입력 + 표현식 모두 가능
3. **유연성**: 파라미터, 숫자, 표현식 자유롭게 사용
4. **정확성**: 값을 확인하며 선택하여 오류 감소
5. **재사용성**: 파라미터 사용으로 값 변경 용이

사용자는 이제:
- 🔍 값을 **보면서** 선택할 수 있고
- 🖱️ 마우스 없이 **키보드로** 빠르게 입력하고
- 📝 **표현식**으로 복잡한 값을 계산하고
- 🔄 **파라미터**로 값을 쉽게 변경할 수 있습니다!
