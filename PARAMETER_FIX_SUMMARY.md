# 🔧 Signal Bit Width - Parameter Resolution Fix

## 문제 분석 결과

### ❌ 문제점
**Excel에 파라미터가 그대로 저장되는 문제:**
```
Input:  o_data [DATA_WIDTH-1:0]
Output: [DATA_WIDTH-1:0]  (파라미터 그대로!)

Expected: [7:0]  (계산된 값)
```

### 🔍 원인 분석

**rtl_parser.py 작동 방식:**
```python
def resolve_ports_with_params(modules, target, env):
    # env는 "파라미터 환경" 딕셔너리
    # 예: env = {'DATA_WIDTH': '8', 'PARAM_WIDTH': '10', ...}
    
    # 이 env가 없으면 calculated_bit_width = 0
    # 결과: fallback으로 파라미터 표현식 그대로 저장
```

**cli_tui.py의 버그:**
```python
# Line 552 - 버그!
env = compute_env_for_occurrence(occs[0], modules, {})  # ← {} 비어있음!
```

### ✅ 해결 방법

**1단계: 모듈의 default 파라미터 추출**
```python
# Line 548-554
external_params = {}
if target_module in modules:
    target_mod = modules[target_module]
    if "param_defaults" in target_mod:
        external_params = dict(target_mod["param_defaults"])
        # 예: {'DATA_WIDTH': '8', 'PARAM_WIDTH': '10', 'WEIGHT_WIDTH': '6'}

env = compute_env_for_occurrence(occs[0], modules, external_params)
```

**2단계: 파라미터 계산 로직**
```python
# rtl_parser.py resolve_width_token_with_params()
msb = substitute_and_eval('DATA_WIDTH-1', env)  # 8-1 = 7
lsb = substitute_and_eval('0', env)             # 0
calculated_bit_width = abs(7 - 0) + 1           # 8
```

**3단계: 파라미터 감지 로직**
```python
def get_signal_width(field_name: str) -> Tuple[str, bool]:
    # Returns: (width_str, has_unresolved_params)
    
    # 경우 1: calculated_bit_width > 0 → 계산됨
    if calculated_width > 0:
        return ("[7:0]", False)  # 해결됨!
    
    # 경우 2: 파라미터 표현식인지 확인
    if re.search(r'[A-Za-z_]\w*', width_expr):
        return ("[DATA_WIDTH-1:0]", True)  # 미해결
    
    return ("", False)
```

## 코드 변경 사항

### 파일: scripts/cli_tui.py

#### Change 1: 파라미터 환경 구성 (Line 548-554)
```python
# OLD:
env = compute_env_for_occurrence(occs[0], modules, {}) if occs else {}

# NEW:
external_params = {}
if target_module in modules:
    target_mod = modules[target_module]
    if "param_defaults" in target_mod:
        external_params = dict(target_mod["param_defaults"])

env = compute_env_for_occurrence(occs[0], modules, external_params) if occs else external_params
```

#### Change 2: 파라미터 감지 로직 (Line 5193-5220)
```python
def get_signal_width(field_name: str) -> Tuple[str, bool]:
    """
    Returns: (width_str, has_unresolved_params)
    - ("[7:0]", False) - 계산된 너비
    - ("[DATA_WIDTH-1:0]", True) - 미해결 파라미터
    - ("", False) - 너비 정보 없음
    """
    ...
```

#### Change 3: Excel Export에서 tuple 처리
- Counter, Handshake, PulseWidth 모두 업데이트
- `width, has_unresolved = get_signal_width(field_name)` 패턴 적용

## 예상 결과

### Before (버그)
```
Excel Column B:
├─ i_data: "[DATA_WIDTH-1:0]"
├─ i_hor_cnt: "[PARAM_WIDTH-1:0]"
├─ i_w1_cap: "[WEIGHT_WIDTH-1:0]"
└─ o_data: "[DATA_WIDTH-1:0]"
```

### After (수정)
```
Excel Column B:
├─ i_data: "[7:0]"              (calculated: 8)
├─ i_hor_cnt: "[9:0]"           (calculated: 10)
├─ i_w1_cap: "[5:0]"            (calculated: 6)
└─ o_data: "[7:0]"              (calculated: 8)
```

## 테스트 결과

✅ **Parameter Resolution Test** - PASS (5/5)
- Plain numeric range: `[7:0]` ✅
- Parameter expressions detected: `[DATA_WIDTH-1:0]` ✅

✅ **Parameter Extraction Test** - PASS (1/1)
- Default params extracted: 3/3 ✅

✅ **Width Calculation Test** - PASS (3/3)
- DATA_WIDTH=8 → `[7:0]` ✅
- PARAM_WIDTH=10 → `[9:0]` ✅
- WEIGHT_WIDTH=6 → `[5:0]` ✅

## 기술 상세

### rtl_parser.py의 파라미터 계산 과정

1. **파라미터 추출** (Line 330-340)
   ```python
   # i_data [DATA_WIDTH-1:0]에서:
   params_msb = {'DATA_WIDTH'}
   params_lsb = set()
   params_used = ['DATA_WIDTH']
   ```

2. **값 계산** (Line 342-347)
   ```python
   # env = {'DATA_WIDTH': '8', ...}
   msb = substitute_and_eval('DATA_WIDTH-1', env)  # 7
   lsb = substitute_and_eval('0', env)             # 0
   calculated_bit_width = abs(7-0)+1               # 8
   ```

3. **결과 저장** (Line 347)
   ```python
   result["calculated_bit_width"] = 8  # ← 핵심!
   ```

### cli_tui.py의 신규 flow

```
RTL 파일 로드
    ↓
모듈 파싱 (build_modules_db)
    ↓
대상 모듈 선택 (target_module)
    ↓
Default 파라미터 추출 ← NEW!
    external_params = {'DATA_WIDTH': '8', ...}
    ↓
compute_env_for_occurrence(..., external_params) ← FIXED!
    ↓
resolve_ports_with_params(..., env)
    ↓
calculated_bit_width 계산 ← 이제 작동!
    ↓
Excel Export에 저장
    column B: "[7:0]" ← 파라미터 대신 계산된 값!
```

## 주요 포인트

| 항목 | 설명 |
|------|------|
| **Root Cause** | cli_tui.py가 빈 `{}` 대신 파라미터 환경을 전달하지 않음 |
| **Fix** | 모듈의 default 파라미터 추출 후 `compute_env_for_occurrence`에 전달 |
| **Impact** | Excel에 파라미터 계산값 저장, 파라미터 감지 로직 추가 |
| **Backward Compat** | 완전 호환 (파라미터가 없으면 이전처럼 작동) |
| **Performance** | 무시할 수준 (dict copy, regex 한 번) |

## Verification Commands

```bash
# 1. Syntax 검증
python -m py_compile scripts/cli_tui.py

# 2. 파라미터 계산 테스트
python test_parameter_fix.py

# 3. 실제 실행 (blur_scaler 예제)
# - TUI에서: scan, select blur_scaler, check Excel output
```

## 통합 테스트 계획

```
1. RTL Scan
   └─ blur_scaler 모듈 선택
      ├─ DATA_WIDTH=8 (default)
      ├─ PARAM_WIDTH=10 (default)
      └─ WEIGHT_WIDTH=6 (default)

2. Signal Selection
   └─ o_data [DATA_WIDTH-1:0] 선택
      └─ calculated_bit_width = 8 ← 저장됨

3. Excel Export
   └─ Column B: "[7:0]" ← 파라미터 대신 계산값!
```

---

**Status**: ✅ 코드 수정 완료, 테스트 통과
**Next**: RTL 스캔 후 실제 Excel 확인
