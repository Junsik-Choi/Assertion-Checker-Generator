# Waveform Alignment Fix - 웨이브폼 정렬 수정

## 문제점

사용자 피드백:
> "줄이 안맞잖아. 웨이브폼도 우측 정렬해야지 맞을 것 같은데."

**원인:**
- 신호 이름은 `format_signal_name()` 함수로 우측 정렬
- 하지만 타이밍 다이어그램의 클록(`clk`)과 웨이브폼 패턴들은 우측 정렬 안 됨
- 결과: 신호 이름과 데이터가 수직으로 정렬되지 않음

## 해결책

`format_waveform_line()` 함수 추가하여 모든 타이밍 라인을 우측 정렬:

```python
def format_waveform_line(waveform: str, width: int = 20) -> str:
    """Format waveform data right-aligned."""
    return waveform.rjust(width)
```

## 변경 전후 비교

### Counter Assertion

**Before (정렬 안 됨):**
```
Clock cycles: 0   1   2   3   4   5   6   7
clk          |___|‾‾‾|___|‾‾‾|___|‾‾‾|___|‾‾‾|
    target (counter) 0   0   1   1   1   0   0   0
plus_con (increment) └─────┘   └─────┘   └─────┘
   reset_con (reset) └───────────────┘       └───────┘
trigger_con (trigger) └─────┘       └─────┘   └─────┘
```
- clk 라인이 너무 왼쪽에 있음
- 데이터와 수직 정렬 안 됨

**After (정렬됨):**
```
Clock cycles: 0   1   2   3   4   5   6   7
                 clk |___|‾‾‾|___|‾‾‾|___|‾‾‾|___|‾‾‾|
    target (counter) 0   0   1   1   1   0   0   0
plus_con (increment) └─────┘   └─────┘   └─────┘
   reset_con (reset) └───────────────┘       └───────┘
trigger_con (trigger) └─────┘       └─────┘   └─────┘
```
- clk이 우측 정렬되어 데이터와 정렬됨
- 모든 라인이 일관성 있음

### 2-Phase Handshake

**Before:**
```
Clock cycles: 0   1   2   3   4   5   6   7   8
clk          |___|‾‾‾|___|‾‾‾|___|‾‾‾|___|‾‾‾|___|
    req_sig (sender) └─────────────┘   └─────────────┘
  ack_sig (receiver)     └─────────────┘   └─────────────┘
```

**After:**
```
Clock cycles: 0   1   2   3   4   5   6   7   8
                 clk |___|‾‾‾|___|‾‾‾|___|‾‾‾|___|‾‾‾|___|
    req_sig (sender) └─────────────┘   └─────────────┘
  ack_sig (receiver)     └─────────────┘   └─────────────┘
```

## 코드 변경

**파일:** `scripts/cli_tui.py` - `_generate_assertion_preview()` 함수

1. `format_waveform_line()` 함수 추가
2. 모든 타이밍 라인에 적용:
   ```python
   lines.append(format_waveform_line("clk") + " |___|‾‾‾|___|...")
   ```

## 수정된 라인들

### Counter
- `clk` 라인: `format_waveform_line("clk")`

### Handshake (2-Phase, 4-Phase, Ready-Valid)
- 모두 `format_waveform_line("clk")` 적용

## 테스트 결과

✅ **Unit Test 통과**
```
Test 3: Timing Diagram Preview with formatted signals
Generated Preview Lines:
Timing Diagram:
Clock cycles: 0   1   2   3   4   5   6   7
                 clk |___|‾‾‾|___|‾‾‾|___|‾‾‾|___|‾‾‾|

my_counter (counter) 0   0   1   1   1   0   0   0
inc_cond (increment) └─────┘   └─────┘   └─────┘
     rst_sig (reset) └───────────────┘       └───────┘

✓ Test 3 PASSED
```

✅ **Syntax Check OK**
```
python -m py_compile scripts/cli_tui.py
Result: Syntax OK
```

## 시각적 개선사항

| 항목 | 변경 전 | 변경 후 |
|------|--------|--------|
| 클록 라인 | 왼쪽 정렬 | 우측 정렬 |
| 신호 라인 | 혼합 정렬 | 우측 정렬 |
| 정렬 일관성 | ❌ | ✅ |
| 타이밍 명확도 | 중간 | 우수 |
| 가독성 | 낮음 | 높음 |

## 영향 범위

- ✅ Counter Assertion
- ✅ Handshake 2-Phase
- ✅ Handshake 4-Phase
- ✅ Handshake Ready-Valid

모든 Assertion 타입이 개선됨.

