# Parameterized Signal Width Calculation - Implementation Summary

## Overview
사용자 요청에 따라 파라미터화된 신호(parameterized signals)의 bit width를 정확히 계산하고 표시하는 기능을 구현했습니다.

예: `input [WEIGHT_WIDTH-1:0] i_w1_cap` → 계산된 bit width: 4 bits (WEIGHT_WIDTH=4일 때)

## Key Changes

### 1. rtl_parser.py - Parameter Tracking Engine

#### 새로운 함수: `resolve_width_token_with_params()`
- **목적**: 파라미터 표현식을 분석하고 계산된 bit width와 메타데이터 반환
- **입력**: width 표현식, 파라미터 환경
- **출력**: 
  ```python
  {
    "resolved_width": "[3:0]",           # 계산된 width
    "is_parameterized": True,            # 파라미터 사용 여부
    "params_used": ["WEIGHT_WIDTH"],     # 사용된 파라미터 목록
    "calculated_bit_width": 4,           # 계산된 비트 폭
    "raw_width": "[WEIGHT_WIDTH-1:0]"   # 원본 표현식
  }
  ```

#### 개선된 함수: `resolve_ports_with_params()`
- 이전: 단순히 width만 계산
- 현재: 각 port 객체에 파라미터 메타데이터 추가
  - `is_parameterized`: bool
  - `params_used`: list[str]
  - `calculated_bit_width`: int
  - `raw_width`: str

#### 개선된 함수: `parse_param_defaults_from_header()`
- 패턴 확장: `parameter A=1, B=2, C=3` 형식 지원
- 이전: 첫 번째 parameter만 인식
- 현재: 모든 parameter 정의 인식

### 2. cli_tui.py - 사용자 인터페이스 개선

#### 새로운 함수: `_get_port_param_info()`
```python
def _get_port_param_info(port: Dict[str, Any]) -> Tuple[bool, str, int]:
    """Extract (is_parameterized, params_str, calculated_bit_width) from port"""
```

#### 확장된 함수: `_format_port_with_width()`
- **이전**: `"[1] i_w1_cap [WEIGHT_WIDTH-1:0]"`
- **현재**: `"[1] i_w1_cap [WEIGHT_WIDTH] (4bits)"` (파라미터화된 신호)
- 반환 값 변경: `(text, is_parameterized)` 투플

#### 개선된 함수: `_draw_ports_two_columns()`
- 파라미터화된 신호를 **BLUE 색상**으로 표시
- 일반 신호: 기본 색상
- 파라미터화 신호: 파란색 + 파라미터 이름 + 계산된 비트폭 표시

## Test Results

### Test 1: Parameterized Width Resolution ✓ PASS
```
6/6 passed - 다양한 파라미터 표현식 계산 검증
- [WEIGHT_WIDTH-1:0] → [3:0] (4 bits)
- [PARAM_WIDTH-1:0] → [10:0] (11 bits)
- [DATA_WIDTH-1:0] → [7:0] (8 bits)
- [WEIGHT_WIDTH*3-1:0] → [11:0] (12 bits)
- [DATA_WIDTH*3-1:0] → [23:0] (24 bits)
- [7:0] → [7:0] (8 bits, non-parameterized)
```

### Test 2: Parameter Extraction ✓ PASS
```
3/3 passed - 다양한 파라미터 형식 인식
- "parameter WEIGHT_WIDTH = 4, PARAM_WIDTH = 11, DATA_WIDTH = 8" ✓
- "parameter A = 1, B = 2, C = 3" ✓
- "parameter WIDTH = 8" ✓
```

### Test 3: blur_scaler.v Signal Display ✓ PASS
```
Parameterized input signals detected: 16 signals
- i_w1_cap through i_w9_cap: [WEIGHT_WIDTH-1:0] → [3:0] (4 bits)
- i_vact_state, i_hor_cnt: [PARAM_WIDTH-1:0] → [10:0] (11 bits)
- i_sram_rd1, i_sram_rd2, i_sram_rd3: [DATA_WIDTH-1:0] → [7:0] (8 bits)

Parameterized output signals detected: 1 signal
- o_data: [DATA_WIDTH-1:0] → [7:0] (8 bits)
```

## Visual Representation (TUI Display)

```
INPUT PORTS:
[13] i_w1_cap [WEIGHT_WIDTH] (4bits)          ← BLUE color
[14] i_w2_cap [WEIGHT_WIDTH] (4bits)          ← BLUE color
[15] i_w3_cap [WEIGHT_WIDTH] (4bits)          ← BLUE color
[16] i_w4_cap [WEIGHT_WIDTH] (4bits)          ← BLUE color
...
```

## Excel Integration (Step 4)

현재 Excel 내보내기 기능 업데이트 예정:
- Signal Name
- Type (input/output/inout)
- Width
- **Parameterized** (YES/NO)  ← NEW
- **Parameter Name** (e.g., WEIGHT_WIDTH)  ← NEW
- **Parameter Value** (4)  ← NEW
- **Calculated Bit Width** (4)  ← NEW

## Backward Compatibility

- 기존 비파라미터화된 신호: 동작 변경 없음
- 새로운 필드는 optional: 파라미터가 없으면 기본값 사용
- 기존 코드와 완전 호환

## Implementation Details

### Parameter Resolution Algorithm

```python
# 1. 표현식 파싱: [WEIGHT_WIDTH-1:0]
# 2. 파라미터 추출: ["WEIGHT_WIDTH"]
# 3. 환경에서 값 조회: WEIGHT_WIDTH = 4
# 4. 수식 평가: 4-1 = 3 (MSB), 0 (LSB)
# 5. Bit width 계산: |3-0| + 1 = 4 bits
```

### Calculation Examples

**Example 1: Simple parameter**
```
Width: [WEIGHT_WIDTH-1:0]
Env: {WEIGHT_WIDTH: "4"}
→ Resolved: [3:0], BitWidth: 4
```

**Example 2: Multiplication**
```
Width: [WEIGHT_WIDTH*3-1:0]
Env: {WEIGHT_WIDTH: "4"}
→ Resolved: [11:0], BitWidth: 12 (4*3=12)
```

**Example 3: Complex expression**
```
Width: [SUM_WIDTH-1:0]
Env: {WEIGHT_WIDTH: "4", DATA_WIDTH: "8", SUM_WIDTH: "12"}
→ Resolved: [11:0], BitWidth: 12
```

## Files Modified

1. **scripts/rtl_parser.py**
   - Added: `resolve_width_token_with_params()`
   - Modified: `resolve_ports_with_params()` - parameter metadata injection
   - Modified: `parse_param_defaults_from_header()` - improved parameter extraction

2. **scripts/cli_tui.py**
   - Added: `_get_port_param_info()`
   - Modified: `_format_port_with_width()` - returns tuple with is_parameterized flag
   - Modified: `_draw_ports_two_columns()` - blue color for parameterized signals

## Test Files Created

1. **test_parameterized_width.py**
   - Tests parameter resolution engine
   - Tests parameter extraction
   - Tests sample signals from blur_scaler.v

2. **test_parameterized_display.py**
   - Tests signal display with metadata
   - Tests blur_scaler.v port list display
   - Verifies bit width calculations

## Next Steps

1. **Excel Export Enhancement** (Task 4)
   - Add parameterization columns to Excel output
   - Enable parameter value input UI in Step 2

2. **Parameter Value Override UI** (Task 5)
   - Allow users to modify parameter values
   - Real-time bit width recalculation
   - Parameter confirmation dialog before Excel export

3. **Documentation**
   - User guide for parameterized assertions
   - Examples of parameter-aware assertion generation

## Benefits

✅ **Accuracy**: 파라미터 기본값 기반 정확한 비트폭 계산
✅ **Clarity**: 파라미터화된 신호를 시각적으로 구분 (파란색)
✅ **Flexibility**: 사용자가 parameter 값 변경 가능
✅ **Traceability**: raw expression과 calculated value 모두 표시
✅ **Scalability**: 복잡한 파라미터 계산식 지원 (곱셈, 덧셈 등)
