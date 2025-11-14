# Custom Expression Input - Improvements

## 개요 (Overview)

커스텀 표현식 입력 기능이 다음과 같이 개선되었습니다:

### 주요 변경사항 (Key Changes)

1. **실제 시그널 이름 사용**
   - ~~기존: `i1 & i2`, `o1 | rst`~~ (숫자 별칭)
   - **신규: `(i_sram_rd1 && i_sram_rd2) | i_sram_rd3`** (실제 시그널 이름)

2. **에러 메시지 개선**
   - 잘못된 시그널 입력 시 **빨간색**으로 에러 표시
   - 사용 가능한 시그널 목록 힌트 제공
   - 명확한 에러 원인 표시

3. **사용자 경험 향상**
   - 성공 시 이전 에러 자동 초기화
   - 구체적인 입력 예시 제공
   - 더 직관적인 프롬프트 메시지

---

## 사용 예시 (Usage Examples)

### ✅ 올바른 입력

```verilog
// 1. 논리 AND/OR 조합
(i_sram_rd1 && i_sram_rd2) | i_sram_rd3

// 2. 비트 연산
i_data[7:0] & i_mask

// 3. 복잡한 중첩 표현식
((i_req1 & i_valid1) | (i_req2 & i_valid2)) & i_enable

// 4. XOR 및 NOT 연산
i_signal1 ^ i_signal2 | ~i_reset_n

// 5. 여러 조건 조합
(i_hsync & i_vsync & i_de) | i_force_active
```

### ❌ 잘못된 입력 (에러 발생)

```verilog
// 존재하지 않는 시그널 사용
i_invalid_signal | i_data
→ Error: Signal 'i_invalid_signal' not found. 
   Available signals: i_clk, i_rst_n, i_data, i_valid, ...

// 괄호 불균형
((i_signal1 & i_signal2) | i_signal3
→ Error: Unclosed '(' parenthesis

// 잘못된 토큰
i_signal1 @@ i_signal2
→ Error: Unexpected token '@@'
```

---

## 에러 메시지 예시

### 1. 시그널을 찾을 수 없음

```
입력: i_wrong_name & i_data

에러 (빨간색 표시):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Error: Signal 'i_wrong_name' not found. 
Available signals: i_clk, i_rst_n, i_data, i_valid, 
i_ready, i_hsync, i_vsync, i_de, o_done, o_error, 
... (total 25 signals available)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

프롬프트:
Invalid expression. Please re-enter:
```

### 2. 문법 오류

```
입력: ((i_signal1 & i_signal2) | i_signal3

에러 (빨간색 표시):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Error: Unclosed '(' parenthesis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

프롬프트:
Invalid expression. Please re-enter:
```

### 3. 성공 시

```
입력: (i_sram_rd1 && i_sram_rd2) | i_sram_rd3

✓ 표현식 검증 성공
(이전 에러 메시지 자동 초기화)

프롬프트:
Step 2/4: Select Target Signal
...
```

---

## 기술 세부사항 (Technical Details)

### 1. 수정된 파일
- `scripts/cli_tui.py`

### 2. 변경된 함수

#### `_validate_condition_expr()` (Line ~4362)
```python
# Before:
if name not in refs:
    return False, f"unknown signal '{name}'"

# After:
if name not in refs:
    available_signals = list(refs.keys())[:10]
    signal_hint = ", ".join(available_signals)
    if len(refs) > 10:
        signal_hint += f", ... (total {len(refs)} signals available)"
    return False, f"Signal '{name}' not found. Available signals: {signal_hint}"
```

#### Assertion Wizard - Custom Expression Handler (Line ~6507)
```python
# Before:
is_valid, err_msg = _validate_condition_expr(cmd, state)
if not is_valid:
    return f"Invalid expression: {err_msg}. Please re-enter.", False

# After:
is_valid, err_msg = _validate_condition_expr(cmd, state)
if not is_valid:
    _set_error_message(f"Error: {err_msg}")  # Red color display
    return "Invalid expression. Please re-enter:", False

# Clear error on success
_set_error_message("")
```

#### Prompt Messages
```python
# Before:
"Enter custom expression (e.g., 'i1 & i2', 'o1 | rst', '(a & b) | c'):"

# After:
"Enter custom expression using actual signal names (e.g., '(i_sram_rd1 && i_sram_rd2) | i_sram_rd3'):"
```

### 3. Display Example Options
```python
# Before:
'<Custom Expression (e.g., "i1 & i2", "o1 | rst")>'

# After:
'<Custom Expression (e.g., "(i_sram_rd1 && i_sram_rd2) | i_sram_rd3")>'
```

---

## 워크플로우 (Workflow)

### 1. 커스텀 표현식 선택

```
Step 1/4: Select Hsync Signal
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[0] [*] <Custom Expression (e.g., "(i_sram_rd1 && i_sram_rd2) | i_sram_rd3")>
[1] [I] i_hsync
[2] [I] i_vsync
[3] [I] i_de
...

> 0
```

### 2. 표현식 입력

```
Enter custom expression using actual signal names 
(e.g., '(i_sram_rd1 && i_sram_rd2) | i_sram_rd3'):

> (i_hsync & i_de) | i_force_active
```

### 3. 검증 및 처리

#### Case A: 성공
```
✓ Expression validated successfully

Step 2/4: Select Target Signal
...
```

#### Case B: 실패 (빨간색 에러 표시)
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Error: Signal 'i_force_active' not found. 
Available signals: i_hsync, i_vsync, i_de, i_clk, 
i_rst_n, ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Invalid expression. Please re-enter:

> (i_hsync & i_de) | i_valid  ← 수정된 입력
✓ Success!
```

---

## 지원하는 연산자

| 연산자 | 설명 | 예시 |
|--------|------|------|
| `&&` | 논리 AND | `i_req && i_valid` |
| `\|\|` | 논리 OR | `i_err1 \|\| i_err2` |
| `&` | 비트 AND | `i_data & 8'hFF` |
| `\|` | 비트 OR | `i_flag1 \| i_flag2` |
| `^` | 비트 XOR | `i_a ^ i_b` |
| `~` | 비트 NOT | `~i_reset_n` |
| `!` | 논리 NOT | `!i_enable` |
| `()` | 그룹화 | `(i_a & i_b) \| i_c` |
| `[]` | 비트 선택 | `i_data[7:0]` |

---

## 비교: Before vs After

| 항목 | Before | After |
|------|--------|-------|
| **입력 방식** | 숫자 별칭 (`i1`, `i2`) | 실제 시그널 이름 |
| **예시** | `i1 & i2` | `i_sram_rd1 & i_sram_rd2` |
| **에러 표시** | 일반 텍스트 | 빨간색 강조 |
| **에러 정보** | 간단한 메시지 | 사용 가능한 시그널 힌트 포함 |
| **사용자 경험** | 혼란스러울 수 있음 | 명확하고 직관적 |

---

## 테스트 결과

### Test Suite: `dev/test_custom_expression_fix.py`

```
✓ Test 1: Valid expression
  - (i_sram_rd1 && i_sram_rd2) | i_sram_rd3
  
✓ Test 2: Invalid signal name
  - Error message shows available signals
  
✓ Test 3: Bit selection
  - i_data[7:0] & 8'hFF
  
✓ Test 4: Complex nested expression
  - ((i_sram_rd1 & i_sram_rd2) | (i_sram_rd3 & i_valid)) & i_rst_n
  
✓ Test 5: Unmatched parentheses
  - Proper error detection
  
✓ Test 6: Various operators
  - XOR, NOT, OR combinations
  
✓ Test 7: Signal resolution
  - All signals properly available

ALL TESTS PASSED!
```

---

## 마이그레이션 가이드

### 기존 사용자를 위한 안내

#### 이전 방식 (더 이상 사용 불가)
```
> 0                    # Custom expression 선택
Enter expression:
> i1 & i2              # ❌ 작동하지 않음
```

#### 새로운 방식 (필수)
```
> 0                    # Custom expression 선택
Enter custom expression using actual signal names:
> i_sram_rd1 & i_sram_rd2  # ✓ 올바른 방식
```

### 변환 예시

| 이전 (Old) | 새로운 (New) |
|-----------|-------------|
| `i1 & i2` | `i_clk & i_enable` |
| `o1 \| rst` | `o_ready \| i_rst_n` |
| `(i1 \| i2) & i3` | `(i_req1 \| i_req2) & i_valid` |

---

## FAQ

### Q1: 숫자 별칭 (i1, i2)를 여전히 사용할 수 있나요?
**A:** 아니요. 이제 실제 시그널 이름만 사용해야 합니다. 이는 더 명확하고 오류를 줄입니다.

### Q2: 사용 가능한 시그널 목록을 어떻게 확인하나요?
**A:** 
1. 시그널 선택 화면에서 [0] 이외의 옵션들이 모두 사용 가능한 시그널입니다
2. 잘못된 시그널을 입력하면 에러 메시지에 힌트가 표시됩니다

### Q3: 에러 메시지가 빨간색으로 표시되지 않아요
**A:** 터미널이 색상을 지원하지 않을 수 있습니다. 내용은 동일하게 표시됩니다.

### Q4: 복잡한 표현식의 최대 길이는?
**A:** 기술적 제한은 없지만, 가독성을 위해 한 줄에 수십 개 이내의 시그널을 권장합니다.

### Q5: 표현식에서 파라미터를 사용할 수 있나요?
**A:** 네, `param` 명령으로 정의한 파라미터는 표현식에서 사용 가능합니다.

---

## 추가 개선 사항

### 향후 고려사항
- [ ] 자동완성 기능 (Tab completion)
- [ ] 표현식 히스토리 (이전 입력 불러오기)
- [ ] 표현식 라이브러리 (자주 사용하는 패턴 저장)
- [ ] 실시간 구문 강조 (Syntax highlighting)

---

## 관련 문서

- `docs/CUSTOM_EXPRESSION_FEATURE.md` - 커스텀 표현식 기능 전체 설명
- `docs/NEW_ASSERTION_TYPES_IMPLEMENTATION.md` - 새로운 assertion 타입
- `docs/QUICK_START_VIDEO_ASSERTIONS.md` - 비디오 타이밍 assertion 빠른 시작

---

## 변경 이력

### 2025-01-14
- ✨ 실제 시그널 이름 사용으로 변경
- ✨ 에러 메시지 빨간색 표시
- ✨ 사용 가능한 시그널 힌트 추가
- ✨ 프롬프트 메시지 개선
- ✅ 테스트 스위트 추가

---

**요약:** 커스텀 표현식 입력이 더 직관적이고 안전하게 개선되었습니다. 실제 시그널 이름을 사용하고, 에러 발생 시 명확한 안내를 받을 수 있습니다.
