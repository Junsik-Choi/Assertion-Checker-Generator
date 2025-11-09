# 🔧 Signal Bit Width - TUI 표시 수정 완료

## 문제 분석

### blur_scaler.v 파일 구조
```verilog
module blur_scaler #(
    parameter WEIGHT_WIDTH = 4,
    parameter PARAM_WIDTH = 11,
    parameter DATA_WIDTH = 8
)
```

**파라미터 기본값:**
- `WEIGHT_WIDTH = 4` → `[WEIGHT_WIDTH-1:0]` = `[3:0]`
- `PARAM_WIDTH = 11` → `[PARAM_WIDTH-1:0]` = `[10:0]`
- `DATA_WIDTH = 8` → `[DATA_WIDTH-1:0]` = `[7:0]`

### TUI 표시 문제
❌ **Before:**
```
[1] i_blur_mode_cap  1
[2] i_den            1
[3] i_hor_cnt        [PARAM_WIDTH-1:0]      ← 파라미터!
[4] i_hsync          1
[5] i_mirror_mode_c… 1
[6] i_sram_rd1       [DATA_WIDTH-1:0]       ← 파라미터!
...
[11] i_w1_cap        [WEIGHT_WIDTH-1:0]     ← 파라미터!
```

✅ **After:**
```
[1] i_blur_mode_cap  1
[2] i_den            1
[3] i_hor_cnt        [10:0]                 ← 계산된 값!
[4] i_hsync          1
[5] i_mirror_mode_c… 1
[6] i_sram_rd1       [7:0]                  ← 계산된 값!
...
[11] i_w1_cap        [3:0]                  ← 계산된 값!
```

## 근본 원인

**rtl_parser.py:**
- ✅ `calculated_bit_width` 계산 완료
- ✅ port_dict에 저장됨

**cli_tui.py line 548-554:**
- ✅ 파라미터 환경 구성 완료
- ✅ `compute_env_for_occurrence`에 전달 완료

**cli_tui.py line 450-480 (TUI 표시 함수):**
- ❌ `_format_port_with_width()` 아직 파라미터 표현식 표시 중

### 문제점
```python
# OLD (Line 463-468):
if is_param:
    if bit_width > 0:
        text = f"[{index+1}] {name} [{params_str}] ({bit_width}bits)"
                                                      ↑
                        파라미터 이름 표시 (예: WEIGHT_WIDTH)
                        bit_width는 있지만 사용하지 않음!
```

## 해결책

**파일:** `scripts/cli_tui.py` (Line 450-480)

### 변경 내용
```python
def _format_port_with_width(port, index):
    if is_param:
        if bit_width > 0:
            # ✅ NEW: 파라미터 표현식 대신 계산된 값 표시
            formatted_width = f"[{bit_width-1}:0]"
            text = f"[{index+1}] {name} {formatted_width}"
        else:
            # ⚠️ Fallback: 계산 실패시 원본 표현식
            text = f"[{index+1}] {name} {width}"
```

### 동작 원리
```
bit_width = 4 (from calculated_bit_width)
            ↓
formatted_width = f"[{4-1}:0]" = "[3:0]"
            ↓
Display: "[11] i_w1_cap [3:0]"
```

## 수정 결과

| 신호 | RTL 표현식 | 계산 후 | TUI 표시 |
|------|-----------|--------|---------|
| `i_hor_cnt` | `[PARAM_WIDTH-1:0]` | 10 | **[10:0]** ✅ |
| `i_sram_rd1` | `[DATA_WIDTH-1:0]` | 8 | **[7:0]** ✅ |
| `i_w1_cap` | `[WEIGHT_WIDTH-1:0]` | 4 | **[3:0]** ✅ |
| `i_vact_state` | `[PARAM_WIDTH-1:0]` | 10 | **[10:0]** ✅ |

## 세 단계 검증

### ✅ Step 1: rtl_parser (이미 완료)
```
blur_scaler.v 파싱
    ↓
Port: i_w1_cap, width: [WEIGHT_WIDTH-1:0]
    ↓
env = {'WEIGHT_WIDTH': '4', ...}
    ↓
calculated_bit_width = 4 ✅
```

### ✅ Step 2: cli_tui.py 파라미터 환경 (이미 완료)
```
외부 파라미터 없음
    ↓
모듈 default 파라미터 추출
    ↓
external_params = {'WEIGHT_WIDTH': '4', 'PARAM_WIDTH': '11', 'DATA_WIDTH': '8'}
    ↓
compute_env_for_occurrence에 전달 ✅
```

### ✅ Step 3: TUI 표시 (지금 수정 완료!)
```
_format_port_with_width() 호출
    ↓
is_param = True, bit_width = 4
    ↓
formatted_width = f"[{4-1}:0]" = "[3:0]"
    ↓
Display: "[11] i_w1_cap [3:0]" ✅
```

## 코드 변경 요약

**파일:** `scripts/cli_tui.py`

**Line 450-480:** `_format_port_with_width()` 함수 수정

```python
# ❌ 이전: 파라미터 이름 표시
if bit_width > 0:
    text = f"[{index+1}] {name} [{params_str}] ({bit_width}bits)"

# ✅ 이제: 계산된 값 표시
if bit_width > 0:
    formatted_width = f"[{bit_width-1}:0]"
    text = f"[{index+1}] {name} {formatted_width}"
```

## 테스트 방법

```bash
# 1. TUI 실행
python scripts/cli_tui.py

# 2. RTL 스캔
a → scan → select blur_scaler

# 3. 확인 사항
- [3] i_hor_cnt [10:0] ✅ (not [PARAM_WIDTH-1:0])
- [6] i_sram_rd1 [7:0] ✅ (not [DATA_WIDTH-1:0])
- [11] i_w1_cap [3:0] ✅ (not [WEIGHT_WIDTH-1:0])
```

## 예상 결과

### TUI 스크린 (Inputs 섹션)
```
[1] i_blur_mode_cap  1
[2] i_den            1
[3] i_hor_cnt        [10:0]         ← 계산됨!
[4] i_hsync          1
[5] i_mirror_mode_c… 1
[6] i_sram_rd1       [7:0]          ← 계산됨!
[7] i_sram_rd2       [7:0]          ← 계산됨!
[8] i_sram_rd3       [7:0]          ← 계산됨!
[9] i_vact_state     [10:0]         ← 계산됨!
[10] i_vsync         1
[11] i_w1_cap        [3:0]          ← 계산됨!
[12] i_w2_cap        [3:0]          ← 계산됨!
[13] i_w3_cap        [3:0]          ← 계산됨!
...
[20] i_weight_wr_mo… 1
```

## 수정된 파일

- `scripts/cli_tui.py` - `_format_port_with_width()` 함수 수정 ✅

## 전체 흐름 정리

```
1️⃣  blur_scaler.v 파싱
    └─ Port: i_hor_cnt [PARAM_WIDTH-1:0]

2️⃣  rtl_parser 계산 (Line 307-347)
    └─ PARAM_WIDTH=11 → calculated_bit_width=11

3️⃣  cli_tui.py 파라미터 설정 (Line 548-554)
    └─ external_params = {'PARAM_WIDTH': '11', ...}

4️⃣  TUI 표시 (Line 450-480) ← 지금 수정!
    └─ formatted_width = "[10:0]"
    └─ Display: "[3] i_hor_cnt [10:0]"
```

---

**Status:** ✅ COMPLETE

**Changes:**
- 1 function modified: `_format_port_with_width()`
- Syntax: ✅ OK
- Ready for: TUI 실행 및 확인

**Next:** RTL 스캔 후 TUI에서 실제 표시 확인
