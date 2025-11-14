# Parameter & MS Signal Update - 구현 완료

## 개요 (Overview)

파라미터와 MS 시그널의 사용성을 개선했습니다:

### 주요 변경사항

1. **파라미터 가시성 향상** ✨
   - Assertion 생성 시 파라미터가 signal 선택 목록에 표시됨
   - `[P]` 마커로 파라미터 식별 (파란색)
   - VBP, HBP 등 모든 assertion 타입에서 사용 가능

2. **param 중복 시 업데이트** 🔄
   - 기존: 중복 에러 발생
   - 개선: **값이 자동으로 업데이트**됨
   - 예: `param WIDTH=8` → `param WIDTH=16` (8→16으로 변경)

3. **ms 중복 시 업데이트** 🔄
   - 기존: 중복 에러 발생
   - 개선: **표현식이 자동으로 업데이트**됨
   - 예: `ms valid = i_clk` → `ms valid = i_clk & i_en` (표현식 변경)

---

## 1. 파라미터 가시성 (Parameter Visibility)

### 이전 (Before)
```
Assertion 생성 시 signal 선택:
[0] [*] <Custom Expression>
[1] [I] i_clk
[2] [I] i_valid
[3] [O] o_ready
[4] [M] valid_sig

❌ 파라미터가 목록에 없음!
```

### 개선 (After)
```
Assertion 생성 시 signal 선택:
[0] [*] <Custom Expression>
[1] [I] i_clk
[2] [I] i_valid
[3] [O] o_ready
[4] [P] WIDTH        ← 파라미터 추가!
[5] [P] DEPTH        ← 파라미터 추가!
[6] [M] valid_sig

✓ 파라미터가 [P] 마커(파란색)로 표시됨
```

### 구현 위치
**scripts/cli_tui.py** Line ~5432

```python
# Parameters - ALL of them
if state.module_info and state.module_info.parameters:
    for param in state.module_info.parameters:
        param_name = param.get('name', '')
        all_signals.append((idx, param_name, 'parameter', param))
        idx += 1

# MS Signals (user-defined) - ALL of them
if state.conditions:
    ...
```

### 색상 코드 추가
**scripts/cli_tui.py** Line ~5476

```python
# Color by signal type
if sig_type == 'input':
    color = _PAIR_BY_NAME.get("cyan", 0)
    prefix = "[I]"
elif sig_type == 'output':
    color = _PAIR_BY_NAME.get("yellow", 0)
    prefix = "[O]"
elif sig_type == 'parameter':
    color = _PAIR_BY_NAME.get("blue", 0)
    prefix = "[P]"  # ← 파라미터 추가
elif sig_type == 'special':
    ...
```

---

## 2. param 중복 업데이트 (Parameter Update)

### 이전 동작 (Before)
```bash
> param WIDTH=8
✓ Parameter added: WIDTH=8

> param WIDTH=16
ERROR: Parameter 'WIDTH' already exists
```

### 개선 동작 (After)
```bash
> param WIDTH=8
✓ Parameter added: WIDTH=8

> param WIDTH=16
✓ Parameter updated from 8 to 16 - Define sheet updated
```

### 구현 위치
**scripts/cli_tui.py** Line ~2935

```python
# Check for duplicate parameter - update if exists
existing_param = None
for idx, param in enumerate(state.module_info.parameters):
    if param.get('name', '') == name:
        existing_param = idx
        break

if existing_param is not None:
    # Update existing parameter
    old_val = state.module_info.parameters[existing_param].get('default', '?')
    state.module_info.parameters[existing_param]['default'] = default_val
    action_msg = f"updated from {old_val} to {default_val}"
else:
    # Add new parameter
    state.module_info.parameters.append({
        'name': name,
        'default': default_val,
        'width': None
    })
    action_msg = f"added: {name}={default_val}"
```

### 사용 예시

#### 시나리오 1: 파라미터 값 조정
```bash
# 초기 설정
> param WIDTH=8
✓ Parameter added: WIDTH=8

> param DEPTH=1024
✓ Parameter added: DEPTH=1024

# 값 변경 (업데이트)
> param WIDTH=16
✓ Parameter updated from 8 to 16

> param DEPTH=2048
✓ Parameter updated from 1024 to 2048
```

#### 시나리오 2: 테스트 중 파라미터 변경
```bash
# 테스트 케이스 1
> param DATA_WIDTH=32
✓ Parameter added: DATA_WIDTH=32

> new counter
[assertion 생성...]

# 테스트 케이스 2 - 파라미터만 변경
> param DATA_WIDTH=64
✓ Parameter updated from 32 to 64

> new counter
[다른 DATA_WIDTH로 assertion 생성]
```

---

## 3. ms 중복 업데이트 (MS Signal Update)

### 이전 동작 (Before)
```bash
> ms valid = i_clk & i_en
✓ Condition added: valid (1bits)

> ms valid = i_clk & i_valid & i_ready
ERROR: MS signal 'valid' already exists. 
Use a different name or delete it first with: del ms valid
```

### 개선 동작 (After)
```bash
> ms valid = i_clk & i_en
✓ MS signal added: valid (1bits)

> ms valid = i_clk & i_valid & i_ready
✓ MS signal updated: valid (1bits) -> (1bits) - Define sheet updated
```

### 구현 위치
**scripts/cli_tui.py** Line ~2825

```python
# Check for duplicate MS signal name - if exists, we'll update it later
existing_ms_idx = None
for idx, cond in enumerate(state.conditions):
    if cond.get("name", "") == name:
        existing_ms_idx = idx
        break

# ... validation ...

# Store or update MS signal
if existing_ms_idx is not None:
    # Update existing MS signal
    old_expr = state.conditions[existing_ms_idx].get('expr', '?')
    old_width = state.conditions[existing_ms_idx].get('width', '?')
    state.conditions[existing_ms_idx]['expr'] = expr_cleaned
    state.conditions[existing_ms_idx]['width'] = width
    action_msg = f"updated: {name} ({old_width}bits) -> ({width}bits)"
else:
    # Add new MS signal
    state.conditions.append({"name": name, "expr": expr_cleaned, "width": width})
    action_msg = f"added: {name} ({width}bits)"
```

### 사용 예시

#### 시나리오 1: MS 표현식 개선
```bash
# 초기 버전
> ms valid = i_clk
✓ MS signal added: valid (1bits)

# 조건 추가 (업데이트)
> ms valid = i_clk & i_en
✓ MS signal updated: valid (1bits) -> (1bits)

# 더 많은 조건 추가
> ms valid = (i_clk & i_en) | i_force_valid
✓ MS signal updated: valid (1bits) -> (1bits)
```

#### 시나리오 2: 비트 폭 변경
```bash
# 1비트 신호
> ms status = i_ready
✓ MS signal added: status (1bits)

# 다중 비트 신호로 변경
> ms status = i_status[3:0] 4
✓ MS signal updated: status (1bits) -> (4bits)
```

---

## 4. 모든 Assertion 타입에 적용

### 지원되는 Assertion 타입

파라미터가 signal 목록에 표시되는 모든 assertion 타입:

| 타입 | 사용 예시 |
|------|----------|
| **counter** | 카운터 값으로 파라미터 사용 |
| **handshake** | 타임아웃 값으로 파라미터 사용 |
| **pulseWidth** | 최소/최대 폭으로 파라미터 사용 |
| **HACT** | 예상 픽셀 수로 파라미터 사용 |
| **HSW** | Sync 폭으로 파라미터 사용 |
| **HBP** | Back Porch 값으로 파라미터 사용 ✨ |
| **HFP** | Front Porch 값으로 파라미터 사용 |
| **VBP** | Vertical Back Porch 값으로 파라미터 사용 ✨ |
| **VFP** | Vertical Front Porch 값으로 파라미터 사용 |
| **VSW** | Vertical Sync 폭으로 파라미터 사용 |

### 사용 예시: VBP Assertion with Parameter

```bash
# 1. 파라미터 정의
> param VBP_MIN=36
✓ Parameter added: VBP_MIN=36

> param VBP_MAX=36
✓ Parameter added: VBP_MAX=36

# 2. VBP Assertion 생성
> new
> 6                          # VBP 선택

# Step 1/4: Select Vsync Signal
[0] [*] <Custom Expression>
[1] [I] i_vsync
[2] [I] i_hsync
[3] [O] o_data
[4] [P] VBP_MIN              ← 파라미터 보임!
[5] [P] VBP_MAX              ← 파라미터 보임!
[6] [M] valid_sig
> 1                          # i_vsync 선택

# Step 2/4: Select Data Enable
> 3                          # o_data 선택

# Step 3/4: Enter Min Value
> VBP_MIN                    # 파라미터 이름 입력
✓ Set to: VBP_MIN

# Step 4/4: Enter Max Value
> VBP_MAX                    # 파라미터 이름 입력
✓ Set to: VBP_MAX

# Confirm
✓ Assertion created

# 3. 나중에 값 변경 가능
> param VBP_MIN=32
✓ Parameter updated from 36 to 32

> param VBP_MAX=40
✓ Parameter updated from 36 to 40
```

---

## Signal 선택 목록 순서

모든 assertion 타입에서 동일한 순서로 표시:

```
[0] [*] <Custom Expression>     (항상 맨 위)
────────────────────────────────
[1] [I] i_clk                   (Inputs)
[2] [I] i_valid
[3] [I] i_ready
────────────────────────────────
[4] [O] o_data                  (Outputs)
[5] [O] o_done
────────────────────────────────
[6] [P] WIDTH                   (Parameters) ✨ 새로 추가
[7] [P] DEPTH
[8] [P] VBP_MIN
────────────────────────────────
[9] [M] valid_sig               (MS Signals)
[10] [M] ready_sig
```

---

## 테스트 결과

### Test Suite: `dev/test_param_ms_update.py`

```
✓ Test 1: Parameter Visibility
  - Parameters appear in signal list
  - Correct [P] marker and blue color
  
✓ Test 2: Parameter Update
  - Duplicate param updates value
  - WIDTH: 8 → 16
  - Count remains 1 (no duplicate)
  
✓ Test 3: MS Signal Update
  - Duplicate ms updates expression
  - valid: "i_clk & i_en" → "i_clk & i_valid & i_ready"
  - Count remains 1 (no duplicate)

ALL TESTS PASSED!
```

---

## 비교: Before vs After

### param 명령어

| 상황 | Before | After |
|------|--------|-------|
| **신규 생성** | `✓ added: WIDTH=8` | `✓ added: WIDTH=8` |
| **중복 시도** | `❌ ERROR: already exists` | `✓ updated from 8 to 16` |
| **결과** | 에러로 차단 | 값 자동 업데이트 |

### ms 명령어

| 상황 | Before | After |
|------|--------|-------|
| **신규 생성** | `✓ added: valid (1bits)` | `✓ added: valid (1bits)` |
| **중복 시도** | `❌ ERROR: already exists` | `✓ updated: valid (1bits) -> (1bits)` |
| **결과** | 에러로 차단 | 표현식 자동 업데이트 |

### Assertion 생성

| 항목 | Before | After |
|------|--------|-------|
| **파라미터 표시** | 없음 | [P] 마커로 표시 |
| **선택 가능** | 불가능 | 가능 |
| **사용 방법** | 직접 타이핑만 | 리스트에서 선택 또는 타이핑 |

---

## 사용 시나리오

### 시나리오 1: 비디오 타이밍 Assertion 생성

```bash
# 1. 해상도별 파라미터 정의
> param HACT_1080P=1920
> param VBP_1080P=36
> param HBP_1080P=148

# 2. HBP Assertion 생성
> new
> 3                          # HBP 선택

# 파라미터가 목록에 보임!
[0] [*] <Custom Expression>
...
[6] [P] HACT_1080P
[7] [P] VBP_1080P
[8] [P] HBP_1080P           ← 선택!

# 3. 다른 해상도 테스트 - 파라미터만 변경
> param HBP_1080P=220       # 720p로 변경
✓ Parameter updated from 148 to 220
```

### 시나리오 2: MS 표현식 점진적 개선

```bash
# 1. 간단한 표현식으로 시작
> ms frame_valid = i_vsync
✓ MS signal added: frame_valid (1bits)

# 2. 조건 추가
> ms frame_valid = i_vsync & i_hsync
✓ MS signal updated: frame_valid (1bits) -> (1bits)

# 3. 더 복잡한 조건
> ms frame_valid = (i_vsync & i_hsync & i_de) | i_force_enable
✓ MS signal updated: frame_valid (1bits) -> (1bits)

# 4. 최종 assertion에서 사용
> new counter
[frame_valid를 조건으로 사용]
```

### 시나리오 3: 반복 테스트

```bash
# 테스트 루프
for i in [8, 16, 32, 64]:
    > param DATA_WIDTH={i}
    ✓ Parameter updated from {old} to {i}
    
    > new counter
    [assertion 생성]
    
    > gen
    [파일 생성 및 시뮬레이션]
```

---

## 수정 사항 요약

| 파일 | 라인 | 변경 내용 |
|------|------|----------|
| `cli_tui.py` | ~5432 | 파라미터를 signal 목록에 추가 |
| `cli_tui.py` | ~5476 | 파라미터 색상 코드 ([P] 파란색) |
| `cli_tui.py` | ~2935 | param 중복 시 업데이트 로직 |
| `cli_tui.py` | ~2825 | ms 중복 시 업데이트 로직 |

**총 추가 코드**: ~50 lines  
**테스트 파일**: `dev/test_param_ms_update.py`

---

## 주의사항

### param 업데이트
- ✅ 값만 변경됨 (이름은 변경 불가)
- ✅ Define sheet 자동 업데이트
- ✅ 세션 자동 저장

### ms 업데이트
- ✅ 표현식과 width 모두 변경 가능
- ✅ Define sheet 자동 업데이트
- ✅ 세션 자동 저장
- ⚠️ 다른 MS나 assertion에서 참조 중이면 영향받을 수 있음

### 파라미터 선택
- ✅ 모든 assertion 타입에서 사용 가능
- ✅ [P] 마커로 쉽게 식별
- ✅ Custom Expression에서도 사용 가능

---

## FAQ

### Q1: 파라미터를 삭제하려면?
**A:** 현재는 수동으로 Define sheet에서 삭제해야 합니다. `del param <name>` 기능은 향후 추가 예정입니다.

### Q2: MS 업데이트 시 이전 값으로 되돌릴 수 있나요?
**A:** 직접적인 undo는 없습니다. 이전 표현식을 다시 입력하면 됩니다.

### Q3: 파라미터 이름을 변경할 수 있나요?
**A:** 불가능합니다. 삭제 후 새로 생성해야 합니다.

### Q4: param/ms 업데이트 시 확인 메시지가 나오나요?
**A:** 별도 확인 없이 즉시 업데이트됩니다. "updated from X to Y" 메시지로 확인 가능합니다.

---

## 완료 ✅

- ✅ 파라미터가 signal 선택 목록에 표시됨 ([P] 파란색)
- ✅ param 중복 시 값 자동 업데이트
- ✅ ms 중복 시 표현식 자동 업데이트
- ✅ 모든 assertion 타입에서 동일하게 작동
- ✅ VBP, HBP 등 비디오 타이밍 assertion에서 파라미터 사용 가능
- ✅ Define sheet 자동 업데이트
- ✅ 테스트 완료

**이제 파라미터를 assertion 생성 시 쉽게 선택하고, param/ms를 유연하게 수정할 수 있습니다!** 🎉
