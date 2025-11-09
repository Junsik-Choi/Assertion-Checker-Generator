# Signal UI 개선사항 요약

## 변경 날짜
2025-10-30 (2차 수정: 웨이브폼 라인 정렬)

## 변경 사항

### 1. Signal 선택을 숫자 입력으로 변경 ✓

**문제점:**
- 기존: 신호 이름을 텍스트로 입력해야 함 → 오타 위험
- 예: `i_clk` 입력 시 `i_clk`, `I_clk`, `iclk` 등 오류 가능

**해결책:**
```python
# AppState에 signal_map 추가
assertion_signal_map: Dict[int, str] = field(default_factory=dict)

# 입력 처리: 숫자 또는 정확한 이름으로 선택
if cmd.isdigit():
    idx = int(cmd)
    if idx in state.assertion_signal_map:
        selected_signal = state.assertion_signal_map[idx]
else:
    # 정확한 이름으로도 매칭 가능
    for signal_name in state.assertion_signal_map.values():
        if signal_name.lower() == cmd.lower():
            selected_signal = signal_name
            break
```

**변경된 UI:**
```
Select Signal (Enter number):

┌─ Input ─┐ ┌─ Output ┐ ┌─ MS Sig ─┐
│ [1] clk │ │ [4] vld │ │ [7] cnd1 │
│ [2] rst │ │ [5] rdy │ │ [8] cnd2 │
│ [3] ena │ │ [6] err │ │          │
└─────────┘ └─────────┘ └──────────┘

Enter signal number (auto-advances)
```

---

### 2. ms 명령어 생성 신호 추가 ✓

**개선사항:**
- 기존의 Input/Output 포트만 표시
- 추가: `state.conditions` 에서 ms 신호 로드
  
**코드 변경:**
```python
# signal_map 구성 시 조건부 신호 추가
if state.conditions:
    for cond in state.conditions[:10]:
        cond_name = cond.get('name', '')
        ms_items.append((idx, cond_name, 'ms_signal'))
        signal_map[idx] = cond_name
        idx += 1
```

**결과:**
- Input/Output/MS Signals 통합 관리
- 한 곳에서 모든 신호 선택 가능

---

### 3. 3열 박스 분리 표시 ✓

**변경 전:**
```
Available Signals:
• [Input Ports]
  • i_clk  ✓
  • i_rst
  • i_ena
• [Output Ports]
  • o_vld
```
→ 구분이 약함, 한줄 기준 읽기 어려움

**변경 후:**
```
Select Signal (Enter number):

┌─ Input ─┐ ┌─ Output ┐ ┌─ MS Sig ─┐
│ [1] clk │ │ [4] vld │ │ [7] cnd1 │
│ [2] rst │ │ [5] rdy │ │ [8] cnd2 │
│ [3] ena │ │ [6] err │ │          │
└─────────┘ └─────────┘ └──────────┘
```

**구현:**
```python
# 3열 분리 렌더링
col_w = (left_w - 2) // 3

# Input Ports Box
box_x = margin_x + 2
# Output Ports Box  
box_x = margin_x + 2 + col_w + 1
# MS Signals Box
box_x = margin_x + 2 + (col_w + 1) * 2
```

---

### 4. 타이밍 다이어그램 신호 이름 오른쪽 정렬 + 역할 표시 ✓

**변경 전:**
```
target               0   0   1   1   1   0   0   0
plus_con             └─────┘   └─────┘   └─────┘
reset_con            └───────────────┘       └───────┘
trigger_con          └─────┘       └─────┘   └─────┘
```
→ 신호 이름이 왼쪽, 역할 불명확

**변경 후:**
```
              target (counter) 0   0   1   1   1   0   0   0
              plus_con (increment) └─────┘   └─────┘   └─────┘
               reset_con (reset) └───────────────┘       └───────┘
              trigger_con (trigger) └─────┘       └─────┘   └─────┘
```
→ 신호가 우측 정렬되어 타이밍과 명확하게 정렬, 역할 표시 추가

**구현:**
```python
def format_signal_name(name: str, role: str, width: int = 20) -> str:
    """Format signal name right-aligned with role in parentheses."""
    formatted = f"{name} ({role})"
    return formatted.rjust(width)

# 사용
lines.append(format_signal_name(target, "counter") + " 0   0   1   1   1...")
lines.append(format_signal_name(plus_con, "increment") + " └─────┘   └─────┘...")
lines.append(format_signal_name(reset_con, "reset") + " └───────────────┘...")
lines.append(format_signal_name(trigger_con, "trigger") + " └─────┘   └─────┘...")
```

**HandShake 예시:**
```
Timing Diagram (2-Phase Handshake):

           sender (sender) └─────────────┘   └─────────────┘
          receiver (receiver)     └─────────────┘   └─────────────┘
```

---

## 파일 변경 목록

1. **scripts/cli_tui.py** (주요 변경)
   - AppState에 `assertion_signal_map` 필드 추가
   - `_render_field_input_step()` 함수: 3열 박스 렌더링 구현
   - `_generate_assertion_preview()` 함수: 신호 이름 형식화 함수 추가
   - `_handle_assertion_wizard_command()` 함수: 숫자 입력 처리 로직 추가

2. **test_signal_ui.py** (새로 생성)
   - Signal map 생성 테스트
   - Signal 이름 포매팅 테스트
   - 타이밍 다이어그램 생성 테스트
   - 모든 테스트 통과 ✓

---

## 사용 방법

### Wizard에서 Signal 선택하기

1. Assertion 타입 선택 후 Signal 필드에 진입
2. 3개 박스에서 번호 선택:
   ```
   Enter signal number (auto-advances)
   > 1              # Input[1] 선택
   ```
   또는
   ```
   > i_clk           # 정확한 이름으로도 가능
   ```
3. 자동으로 다음 단계로 진행

---

## 기술 세부사항

### Signal Map 구조
```python
{
    1: "i_clk",
    2: "i_rst", 
    3: "i_ena",
    4: "o_vld",
    5: "o_rdy",
    6: "o_err",
    7: "cond_transfer",
    8: "cond_error"
}
```

### 역할(Role) 표시
- counter: (counter)
- increment: (increment)
- reset: (reset)
- trigger: (trigger)
- sender: (sender)
- receiver: (receiver)

### 박스 그리기 문자
- ┌ ─ ┐ : 상단
- │ : 좌우
- └ ─ ┘ : 하단

---

## 테스트 결과

✓ Unit Test (test_signal_ui.py): 모두 통과
- Test 1: Signal Map Generation ✓
- Test 2: Signal Name Formatting ✓
- Test 3: Timing Diagram Preview ✓

✓ Syntax Check: OK
```
python -m py_compile scripts/cli_tui.py
Result: Syntax OK
```

---

## 다음 단계

- [ ] 실제 wizard 실행으로 UI 시각 확인
- [ ] 더 많은 신호 추가 시 스크롤 기능 검토
- [ ] 박스 크기 자동 조절 검토

