# Assertion Types Complete Guide

이 문서는 TUI의 `new` 명령으로 생성 가능한 모든 assertion 타입에 대한 상세 가이드입니다.

---

## 📋 목차

1. [Counter Assertion](#1-counter-assertion)
2. [Handshake Assertion](#2-handshake-assertion)
3. [Pulse Width Assertion](#3-pulse-width-assertion)
4. [Video Timing Assertions](#4-video-timing-assertions)
   - HACT, HSW, HBP, HFP
   - VACT, VSW, VBP, VFP
5. [Clock Divider](#5-clock-divider)
6. [Clock Gate](#6-clock-gate)
7. [Synchronizer](#7-synchronizer)
8. [Basic Assertion](#8-basic-assertion)
9. [Delay Condition](#9-delay-condition)
10. [Video Sync All](#10-video-sync-all)

---

## 1. Counter Assertion

### 목적
내부 카운터의 증가/감소/리셋 동작이 올바른지 검증합니다.

### 필요 필드
- **Target**: 카운터 신호 이름 (e.g., `cnt`, `counter`)
- **Increment Condition**: 카운터 증가 조건 신호
- **Reset Condition**: 카운터 리셋 조건 신호
- **Check Condition (Trigger)**: 카운터 값 확인 시점
- **Expected Count Value**: 예상 카운터 값

### 사용 예시
```systemverilog
// 프레임 내 라인 수 검증
Target: line_cnt
Increment Condition: i_hsync (horizontal sync 상승 엣지마다 증가)
Reset Condition: i_vsync (vertical sync에서 리셋)
Check Condition: i_frame_end (프레임 끝에서 확인)
Expected Count Value: 1080 (1080p의 경우)
```

### 동작 설명
1. `Reset Condition`이 활성화되면 카운터가 0으로 리셋
2. `Increment Condition`의 상승 엣지마다 카운터 증가
3. `Check Condition`이 활성화될 때 카운터 값이 `Expected Count Value`와 같은지 확인

### 실패 케이스
- 카운터 증가 조건이 누락되어 값이 부족
- 카운터 리셋이 제대로 동작하지 않아 누적
- 예상치 못한 노이즈로 인한 카운터 증가

---

## 2. Handshake Assertion

### 목적
2-phase, 4-phase, ready-valid 핸드셰이크 프로토콜의 정확성을 검증합니다.

### 필요 필드
- **Protocol Type**: 2phase / 4phase / ready_valid
- **Sender Signal**: 송신자/요청 신호
- **Receiver Signal**: 수신자/응답 신호

### 프로토콜별 동작

#### 2-Phase Handshake
```
Sender:   _____┌─────┐_____┌─────┐_____
Receiver: _________┌─────┐_____┌─────┐_
```
- Sender 활성화 → Receiver 응답 → 둘 다 비활성화
- 신호가 HIGH로 유지되는 동안 다중 사이클 허용

#### 4-Phase Handshake
```
Sender:   _____┌──┐_____┌──┐_____
Receiver: _________┌──┐_____┌──┐_
```
- Sender 펄스 → Receiver 펄스 → 완전 동기화
- 각 신호가 펄스 형태 (0→1→0)

#### Ready-Valid
```
Valid:    _____┌───────────┐_____
Ready:    _________┌───┐_________
Transfer: _________┌───┐_________ (valid && ready)
```
- Valid 활성화 후 Ready 대기
- 둘 다 HIGH일 때 데이터 전송
- Valid는 Ready가 올 때까지 유지

### 사용 예시
```systemverilog
// AXI4 Write Address Channel
Protocol Type: ready_valid
Sender Signal: awvalid
Receiver Signal: awready
```

---

## 3. Pulse Width Assertion

### 목적
신호의 펄스 폭이 지정된 min/max 범위 내에 있는지 검증합니다.

### 필요 필드
- **Pulse Type**: hpulse (clock 기반) / vpulse (event 기반)
- **Base Clock** (hpulse만): 사이클 카운트용 클럭
- **Trigger Signal** (vpulse만): 이벤트 카운트용 트리거
- **Target Signal**: 펄스 폭을 검증할 신호
- **Min Width**: 최소 폭
- **Max Width**: 최대 폭

### hpulse vs vpulse

#### hpulse (Clock-based)
```
Base Clock:  __|‾|__|‾|__|‾|__|‾|__|‾|__|‾|__
Target:      ________┌─────────────┐_________
Count:       0  1  2  3  4  5  6  7  (clock cycles)
```
- Base Clock의 사이클 수를 카운트
- 사용 예: Hsync 펄스가 44 clock cycles인지 확인

#### vpulse (Event-based)
```
Trigger:     __|‾|__|‾|__|‾|__|‾|__|‾|__|‾|__
Target:      ________┌─────────────┐_________
Count:       0  1  2  3  4  5  6  7  (events)
```
- Trigger 신호의 이벤트 수를 카운트
- 사용 예: Vsync 펄스 동안 5 horizontal lines인지 확인

### 사용 예시
```systemverilog
// hpulse 예시: Hsync 펄스 폭 검증
Pulse Type: hpulse
Base Clock: i_clk
Target Signal: i_hsync
Min Width: 40
Max Width: 48

// vpulse 예시: Vsync 동안 라인 수 검증
Pulse Type: vpulse
Trigger Signal: i_hsync
Target Signal: i_vsync
Min Width: 3
Max Width: 7
```

---

## 4. Video Timing Assertions

### 4.1 HACT (Horizontal Active Pixel Count)

**목적**: 각 라인의 활성 픽셀 수 검증

**필드**:
- Hsync Signal: 라인 카운트용 (i_hsync)
- Data Enable Signal: 활성 픽셀 구간 (i_de)
- Expected Min/Max Value: 예상 픽셀 수 (e.g., 1920)

**타이밍 다이어그램**:
```
Hsync:  ___|‾‾‾|_______________________
DE:     ___________|‾‾‾‾‾‾‾‾‾‾‾‾‾|______
Pixels:            [1920 pixels]
```

### 4.2 HSW (Horizontal Sync Width)

**목적**: Horizontal Sync 펄스 폭 검증

**필드**:
- Count Trigger: 카운트용 기준 클럭 (i_clk 또는 i_hsync)
- Target Pulse: 모니터링할 펄스 (i_hsync)
- Expected Min/Max Value: 예상 폭 (clock cycles 또는 events)

### 4.3 HBP (Horizontal Back Porch)

**목적**: Hsync에서 Data Enable 시작까지의 타이밍 검증

**타이밍**:
```
Hsync: __|‾‾‾‾|_______________________
DE:    ___________|‾‾‾‾‾‾‾‾‾‾‾‾‾|_____
       <---HBP--->
```

### 4.4 HFP (Horizontal Front Porch)

**목적**: Data Enable 끝에서 Hsync까지의 타이밍 검증

**타이밍**:
```
DE:    ___|‾‾‾‾‾‾‾‾‾‾‾‾‾|____________
Hsync: ______________________|‾‾‾‾|___
                     <---HFP--->
```

### 4.5 VACT (Vertical Active Line Count)

**목적**: 프레임당 활성 라인 수 검증

**필드**:
- Hsync Signal: 라인 카운트용
- Vsync Signal: 프레임 구분
- Data Enable Signal: 활성 라인 구간
- Expected Min/Max Value: 예상 라인 수 (e.g., 1080)

### 4.6 VSW (Vertical Sync Width)

**목적**: Vertical Sync 펄스 폭을 라인 단위로 검증

**필드**:
- Hsync Signal: 라인 카운트용
- Vsync Signal: 모니터링 대상
- Expected Min/Max Value: 예상 라인 수 (e.g., 3-5 lines)

### 4.7 VBP (Vertical Back Porch)

**목적**: Vsync에서 첫 활성 라인까지의 라인 수 검증

### 4.8 VFP (Vertical Front Porch)

**목적**: 마지막 활성 라인에서 Vsync까지의 라인 수 검증

---

## 5. Clock Divider

### 목적
클럭 분주기의 비율과 출력을 검증합니다.

### 필요 필드
- **Reference Clock**: 기준 클럭 (분주 전)
- **MAX Value**: 최대 분주 비율
- **DIVRATIO**: 분주 비율 제어 신호
- **CLKOUT**: 분주된 클럭 출력
- **START FLAG**: 검증 시작 플래그
- **DISABLE**: 검증 비활성화 신호

### 동작 설명
```
Ref Clock: __|‾|__|‾|__|‾|__|‾|__|‾|__|‾|__|‾|__|‾|__
DIVRATIO:  3 (divide by 3)
CLKOUT:    ________|‾‾‾‾‾‾‾|________|‾‾‾‾‾‾‾|________
           <-3 cycles->
```

분주 비율이 `DIVRATIO`일 때:
- HIGH 구간: (DIVRATIO + 1) reference clock cycles
- LOW 구간: (DIVRATIO + 1) reference clock cycles
- 총 주기: 2 × (DIVRATIO + 1) cycles

### 사용 예시
```systemverilog
Reference Clock: i_ref_clk
MAX Value: 100
DIVRATIO: div_ratio[7:0]
CLKOUT: clk_divided
START FLAG: div_start
DISABLE: div_disable
```

---

## 6. Clock Gate

### 목적
클럭 게이팅 로직의 enable/disable 동작을 검증합니다.

### 필요 필드
- **Depth Sync**: 게이팅 적용까지의 딜레이 사이클 수
- **Enable Signal**: 클럭 게이트 활성화 신호
- **Clock Output**: 게이트된 클럭 출력

### 동작 설명
```
Clock In:   __|‾|__|‾|__|‾|__|‾|__|‾|__|‾|__|‾|__
Enable:     ________┌────────────────────────────
Depth Sync: 2
Clock Out:  __|‾|__|‾|_________________ (2 cycles 후 gating)
```

**Enable = 0 (Gating Off)**:
- Depth Sync 사이클 후 Clock Out = Clock In

**Enable = 1 (Gating On)**:
- Depth Sync 사이클 후 Clock Out = 0

### 사용 예시
```systemverilog
Depth Sync: depth_cnt
Enable Signal: cg_enable
Clock Output: clk_gated
```

---

## 7. Synchronizer

### 목적
CDC (Clock Domain Crossing) 동기화 회로의 동작을 검증합니다.

### 필요 필드
- **Depth Sync Value**: 동기화 스테이지 수 (e.g., 2, 3)
- **Enable Signal**: 동기화 활성화 신호
- **Input Signal**: 동기화할 입력 신호
- **Output Signal**: 동기화된 출력 신호

### 동작 설명
```
2-Stage Synchronizer:

Clock:  __|‾|__|‾|__|‾|__|‾|__|‾|__
Enable: ____┌─────────────────────
Input:  ____┌────────────┐________
FF1:    ________┌────────────┐____
FF2:    ____________┌────────────┐ (Output)
        <--2 cycles-->
```

**검증 로직**:
```systemverilog
Enable이 활성화되면:
  Output == $past(Input, DEPTH_SYNC)
```

### 사용 예시
```systemverilog
// 2-stage CDC synchronizer
Depth Sync Value: 2
Enable Signal: sync_enable
Input Signal: async_data_in
Output Signal: sync_data_out
```

---

## 8. Basic Assertion

### 목적
사용자 정의 Property 또는 Sequence를 직접 작성합니다.

### Property vs Sequence

#### Property (완전한 Assertion)
```systemverilog
property p_data_valid();
    @(posedge clk) disable iff(!rst_n)
    valid && ready
    |-> ##1 data == expected_data;
endproperty
```

**필드**:
- Property Name
- Clock Condition: `posedge clk`
- Disable Condition: `!rst_n`
- Trigger Condition: `valid && ready`
- Expected Result: `##1 data == expected_data`

#### Sequence (재사용 가능한 패턴)
```systemverilog
sequence s_handshake();
    @(posedge clk)
    valid ##1 ready ##1 done
endsequence
```

**필드**:
- Sequence Name
- Sequence Clock: `posedge clk`
- Sequence Definition: `valid ##1 ready ##1 done`

### 사용 예시

#### Example 1: FIFO Write Check
```systemverilog
Property Name: p_fifo_write
Clock Condition: posedge clk
Disable Condition: !rst_n || full
Trigger Condition: wr_en && !full
Expected Result: ##1 !empty && (wr_ptr == $past(wr_ptr) + 1)
```

#### Example 2: Bus Transaction Sequence
```systemverilog
Sequence Name: s_bus_transaction
Sequence Clock: posedge clk
Sequence Definition: req ##[1:3] gnt ##1 ack ##1 done
```

### Temporal Operators
- `##n`: n 사이클 지연
- `##[m:n]`: m~n 사이클 지연
- `##[1:$]`: 1~무한대 사이클
- `|->`: implication (조건부 검증)
- `|=>`: implication with 1-cycle delay

---

## 9. Delay Condition

### 목적
트리거 후 특정 사이클 지연 후의 조건을 검증합니다.

### 필요 필드
- **Trigger Signal**: 트리거 신호
- **Delay Cycles**: 지연 사이클 수
- **Expected Signal**: 지연 후 확인할 신호

### 동작 설명
```
Clock:   __|‾|__|‾|__|‾|__|‾|__|‾|__|‾|__
Trigger: ____┌──┐_______________________
         0   1   2   3   4   5   6   (cycles)
Expected:__________________┌──┐________ (Delay=3일 때)
```

**검증 로직**:
```systemverilog
Trigger의 상승 엣지 감지
→ Delay Cycles 후
→ Expected Signal이 예상 값인지 확인
```

### 사용 예시
```systemverilog
Trigger Signal: start_req
Delay Cycles: 5
Expected Signal: done && (status == SUCCESS)
```

---

## 10. Video Sync All

### 목적
모든 비디오 타이밍 파라미터를 종합적으로 검증합니다.

### 포함 내용
하나의 assertion으로 다음 모든 항목 검증:
- HACT (Horizontal Active Pixels)
- HSW (Horizontal Sync Width)
- HBP (Horizontal Back Porch)
- HFP (Horizontal Front Porch)
- VACT (Vertical Active Lines)
- VSW (Vertical Sync Width)
- VBP (Vertical Back Porch)
- VFP (Vertical Front Porch)

### 필요 필드
- **Hsync Signal**: 수평 동기 신호
- **Vsync Signal**: 수직 동기 신호
- **Data Enable Signal**: 데이터 활성화 신호

### 사용 시나리오
1080p 비디오 타이밍을 한 번에 검증:
```systemverilog
Hsync Signal: i_hsync
Vsync Signal: i_vsync
Data Enable Signal: i_de

자동으로 검증되는 값:
- HACT: 1920 pixels
- VACT: 1080 lines
- HSW, HBP, HFP, VSW, VBP, VFP: 설정된 타이밍
```

---

## 📊 Assertion Type 선택 가이드

| Use Case | Assertion Type | 난이도 |
|----------|---------------|--------|
| 카운터 검증 | Counter | ⭐ |
| 프로토콜 검증 | Handshake | ⭐⭐ |
| 펄스 폭 검증 | Pulse Width | ⭐⭐ |
| 비디오 타이밍 | Video Timing | ⭐⭐ |
| 클럭 분주 | Clock Divider | ⭐⭐⭐ |
| 클럭 게이팅 | Clock Gate | ⭐⭐⭐ |
| CDC 동기화 | Synchronizer | ⭐⭐⭐ |
| 커스텀 로직 | Basic Assertion | ⭐⭐⭐⭐ |
| 지연 조건 | Delay Condition | ⭐⭐ |
| 종합 비디오 | Video Sync All | ⭐⭐⭐ |

---

## 🚀 Quick Start Examples

### 1. 간단한 카운터 검증
```
TUI> new
Select Type: 1 (Counter)
Target: cnt
Increment: i_tick
Reset: i_rst
Trigger: i_frame_end
Expected: 1920
```

### 2. AXI4 핸드셰이크
```
TUI> new
Select Type: 2 (Handshake)
Protocol: 3 (ready_valid)
Sender: awvalid
Receiver: awready
```

### 3. HDMI 비디오 타이밍
```
TUI> new
Select Type: 4 (HACT)
Hsync: i_hsync
Data Enable: i_de
Min: 1920
Max: 1920
```

---

## ⚠️ Common Mistakes

### 1. Counter Assertion
❌ **잘못된 예**: Trigger Condition을 Increment Condition과 동일하게 설정
```
Increment: i_hsync
Trigger: i_hsync  // 잘못됨!
```
✅ **올바른 예**: 확인 시점을 명확히 구분
```
Increment: i_hsync
Trigger: i_frame_end  // 프레임 끝에서 확인
```

### 2. Pulse Width
❌ **잘못된 예**: hpulse와 vpulse 혼동
```
Pulse Type: hpulse
Trigger Signal: i_hsync  // hpulse에는 trigger 불필요!
```
✅ **올바른 예**:
```
Pulse Type: hpulse
Base Clock: i_clk  // clock 기반 카운트
```

### 3. Handshake
❌ **잘못된 예**: 프로토콜 타입 오선택
```
Protocol: 2phase
실제 동작: ready-valid (신호가 HIGH 유지)
```
✅ **올바른 예**: 실제 프로토콜에 맞게 선택

---

## 📝 Notes

- 모든 assertion은 Base Clock과 Base Reset이 필요합니다 (Define 시트에서 자동 참조)
- 신호 이름은 RTL에서 파싱된 실제 포트 이름을 사용해야 합니다
- Parameters를 사용하여 Min/Max 값을 동적으로 설정할 수 있습니다
- Custom Expression (`<Custom Expression>` 옵션)을 통해 복잡한 조건 작성 가능

---

## 🔗 Related Documents

- [COUNTER_TRIGGER_GUIDE.md](COUNTER_TRIGGER_GUIDE.md) - Counter Trigger 상세 설명
- [PULSE_WIDTH_COMPLETION.md](PULSE_WIDTH_COMPLETION.md) - Pulse Width 완전 가이드
- [TUI_TEST_GUIDE.md](TUI_TEST_GUIDE.md) - TUI 테스트 가이드
- [QUICK_START_VIDEO_ASSERTIONS.md](QUICK_START_VIDEO_ASSERTIONS.md) - 비디오 assertion 빠른 시작
