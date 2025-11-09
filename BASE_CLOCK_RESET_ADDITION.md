# Base Clock/Reset 추가 - 변경 사항 정리

## 📋 변경 내용

### 1. Counter Assertion 설정 요약

**이전:**
```
============================================================
COUNTER ASSERTION
============================================================

Counter Signal: cnt_signal
Increments when: i_signal
Resets when: o_signal_sync
Checked at: i_valid
Expected value: 5
```

**변경 후:**
```
============================================================
COUNTER ASSERTION
============================================================

Counter Signal: cnt_signal
Increments when: i_signal
Resets when: o_signal_sync
Checked at: i_valid
Expected value: 5
Base Clock: i_clk          ← 추가됨
Base Reset: i_rst_n        ← 추가됨
```

### 2. Handshake Assertion 설정 요약

**이전:**
```
============================================================
2PHASE HANDSHAKE ASSERTION
============================================================

Protocol Type: 2phase
Sender Signal: sender_req
Receiver Signal: receiver_ack
```

**변경 후:**
```
============================================================
2PHASE HANDSHAKE ASSERTION
============================================================

Protocol Type: 2phase
Sender Signal: sender_req
Receiver Signal: receiver_ack
Base Clock: i_clk          ← 추가됨
Base Reset: i_rst_n        ← 추가됨
```

## 🔧 기술 변경

### 함수 서명 수정
- `_generate_assertion_preview()` 함수에 `state` 파라미터 추가
- 모듈의 Base Clock/Reset 정보에 접근 가능하도록 함

### 데이터 소스
- `state.module_info.clocks[0].get('name')` - Base Clock
- `state.module_info.resets[0].get('name')` - Base Reset
- 정보가 없으면 `'?'`로 표시

## ✅ 검증 완료
- Syntax: py_compile PASS
- Preview 출력: 정상 작동
- Clock/Reset 데이터: 정확히 표시됨

## 📍 영향받는 파일
- `scripts/cli_tui.py`
  - Line 4203: 함수 호출 시 `state` 추가
  - Line 4424: 함수 서명에 `state` 파라미터 추가
  - Line 4445-4463: Counter assertion에 Base Clock/Reset 추가
  - Line 4490-4507: Handshake assertion에 Base Clock/Reset 추가
