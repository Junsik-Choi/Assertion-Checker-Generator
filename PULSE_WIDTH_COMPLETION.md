# PulseWidth Assertion 설정 완성 - 변경 사항

## 📋 변경 내용

### 1. PulseWidth 필드 설명 단순화

**이전:**
```
'description': 'Enter the minimum pulse width (in clock cycles).
              Example: If signal should be high for at least 5 clocks, enter 5'
```

**변경 후:**
```
'description': 'Enter minimum clocks signal should be high (example: 10)'
```

### 2. PulseWidth 설정 요약 화면 추가 (오른쪽 패널)

**이전:** Generic 표시만 가능

**변경 후:**
```
============================================================
PULSE WIDTH ASSERTION
============================================================

Signal to Monitor: i_signal
Minimum Pulse Width: 10 clocks
Maximum Pulse Width: 20 clocks
Base Clock: i_clk
Base Reset: i_rst_n

Timing Diagram:
Clock cycles: 0   1   2   3   4   5   6   7   8   9
                 clk |___|‾‾‾|___|‾‾‾|___|‾‾‾|___|‾‾‾|___|‾‾‾|

   i_signal (signal) └─────────────────────────┘
                          pulse width = 4 clocks

Pass Condition:
  min_width (10) <= pulse_width <= max_width (20)

Fail Condition:
  pulse_width < 10 or pulse_width > 20
```

## 🔧 기술 변경

### 1. 필드 설명 단순화
- 복잡한 예시 제거
- 한국인도 쉽게 이해할 수 있는 표현 사용
- 중복되는 "in clock cycles" 제거

### 2. _generate_assertion_preview 함수 확장
- `elif plugin_name == 'pulseWidth':` 섹션 추가
- Counter/Handshake와 동일한 구조
- Base Clock/Reset 포함
- 타이밍 다이어그램 포함
- Pass/Fail 조건 명확하게 표시

## ✅ 검증 완료

```
✓ Syntax: py_compile PASS
✓ Counter preview: 정상 작동
✓ Handshake preview: 정상 작동
✓ PulseWidth preview: 정상 작동 (NEW)
✓ 모두 Base Clock/Reset 표시
```

## 📍 변경 파일
- `scripts/cli_tui.py`
  - Line 3946-3970: PulseWidth 필드 설명 단순화
  - Line 4583-4625: PulseWidth preview 섹션 추가

## 🎯 결과

이제 세 가지 Assertion 타입이 **일관된 형식**으로 표시됩니다:

| Assertion | 표시 정보 |
|-----------|---------|
| Counter | Signal, Conditions, Clock, Reset, Timing |
| Handshake | Type, Signals, Clock, Reset, Timing |
| PulseWidth | Signal, Min/Max, Clock, Reset, Timing |

모두 기술 정보가 명확하게 표시되고, 사용자가 설정한 값을 확인할 수 있습니다!
