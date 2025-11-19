# Counter Trigger 완벽 가이드

## 개요

"Counter Trigger"와 "Trigger Signal"은 assertion 타입에 따라 다른 의미를 가집니다.
이 문서는 각 assertion 타입별로 trigger 개념을 명확히 설명합니다.

---

## 핵심 개념 요약

### 1️⃣ Counter Trigger (참조 클럭)
**목적**: 카운팅의 기준이 되는 클럭/신호

- 각 rising edge마다 내부 카운터가 1씩 증가
- "몇 개의 이벤트가 발생했는가?"를 셀 때 사용
- 주로 시스템 클럭이나 주기적 신호

**예시**:
- `i_clk` → 시스템 클럭 사이클 수 카운트
- `i_hsync` → 수평 라인 수 카운트
- `i_frame_start` → 프레임 수 카운트

### 2️⃣ Trigger Signal (이벤트 검출)
**목적**: 특정 이벤트를 감지하는 신호

- Rising edge: 이벤트 시작
- Falling edge: 이벤트 종료
- "언제 무언가가 발생하는가?"를 감지할 때 사용
- 주로 제어 신호나 이벤트 마커

**예시**:
- `i_frame_end` → 프레임이 끝날 때 카운터 확인
- `i_line_valid` → 라인이 유효할 때 체크
- `i_data_valid` → 데이터가 유효할 때 측정 시작

---

## Assertion 타입별 상세 설명

### 🎯 Counter Assertion

#### Trigger Signal: `trigger_con` (Check Condition)

**의미**: "카운터 값을 언제 확인할 것인가?"

**동작 방식**:
```
1. target 신호가 변화할 때마다 카운터 증가
2. trigger_con의 rising edge에서 카운터 값 확인
3. 예상값(exp_cnt_val)과 일치하는지 검증
```

**실제 예시**:

#### 예시 1: 프레임당 라인 수 카운트
```yaml
target:       i_line_valid     # 라인이 유효할 때마다 +1
plus_con:     (항상 1)          # 항상 증가
reset_con:    i_frame_start    # 프레임 시작 시 리셋
trigger_con:  i_frame_end      # 프레임 끝날 때 확인 ⭐
exp_cnt_val:  1080              # 1080 라인이어야 함

설명:
- 각 라인마다 카운터 증가
- 프레임이 끝날 때 (i_frame_end rising edge) 카운터 확인
- 카운터가 1080인지 검증 (1080p의 경우)
```

#### 예시 2: 액티브 픽셀 수 카운트
```yaml
target:       i_de              # 데이터 enable 시마다 +1
plus_con:     (항상 1)
reset_con:    i_hsync           # 라인 시작 시 리셋
trigger_con:  i_line_end        # 라인 끝날 때 확인 ⭐
exp_cnt_val:  1920              # 1920 픽셀이어야 함

설명:
- 각 픽셀(i_de active)마다 카운터 증가
- 라인이 끝날 때 (i_line_end rising edge) 카운터 확인
- 카운터가 1920인지 검증 (Full HD 가로 해상도)
```

#### 예시 3: 버스 트랜잭션 수 카운트
```yaml
target:       i_valid & i_ready  # 핸드셰이크 완료 시마다 +1
plus_con:     (항상 1)
reset_con:    i_packet_start    # 패킷 시작 시 리셋
trigger_con:  i_packet_end      # 패킷 끝날 때 확인 ⭐
exp_cnt_val:  64                 # 64개 트랜잭션이어야 함

설명:
- 유효한 트랜잭션마다 카운터 증가
- 패킷이 끝날 때 카운터 확인
- 패킷당 정확히 64개의 트랜잭션이 있는지 검증
```

**잘못된 이해 vs 올바른 이해**:

❌ **잘못된 이해**:
"trigger_con이 카운팅을 시작시킨다"

✅ **올바른 이해**:
"trigger_con은 카운터 값을 확인하는 시점을 결정한다"
- 카운팅은 target 신호에 의해 계속 진행
- trigger_con은 "지금 확인해!"라고 말하는 신호

---

### 📏 HSW (Horizontal Sync Width) Assertion

#### Counter Trigger: `count_trigger` (참조 클럭)

**의미**: "무엇을 기준으로 수를 셀 것인가?"

**동작 방식**:
```
1. count_trigger의 각 rising edge마다 카운터 증가
2. target_pulse가 HIGH인 동안 카운터 동작
3. target_pulse가 LOW가 되면 카운터 값 확인
```

**실제 예시**:

#### 예시 1: Hsync 펄스 폭 확인 (클럭 사이클 기준)
```yaml
count_trigger:  i_clk          # 시스템 클럭 ⭐
target_pulse:   i_hsync        # 측정할 펄스
min:            44             # 최소 44 클럭
max:            44             # 최대 44 클럭

동작:
━━━━┓     ┏━━━━    i_clk (count_trigger)
    ┗━━━━━┛
    1  2  3  4     ← 클럭마다 카운트 증가
    
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
                                              ┗━━━  i_hsync
├──── 44 cycles ────┤

설명:
- i_hsync가 HIGH인 동안 i_clk 엣지를 센다
- 44개의 클럭 엣지가 발생하는지 검증
```

#### 예시 2: 라인 단위로 Vsync 폭 확인
```yaml
count_trigger:  i_hsync        # 라인 클럭 ⭐
target_pulse:   i_vsync        # 측정할 펄스
min:            5              # 최소 5 라인
max:            5              # 최대 5 라인

동작:
━━┓   ┏━┓   ┏━┓   ┏━┓   ┏━┓   ┏━━    i_hsync (count_trigger)
  ┗━━━┛ ┗━━━┛ ┗━━━┛ ┗━━━┛ ┗━━━┛
  1     2     3     4     5         ← 라인마다 카운트 증가

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
                                      ┗━━━  i_vsync
├────── 5 lines ──────┤

설명:
- i_vsync가 HIGH인 동안 i_hsync 엣지를 센다
- 5개의 라인 동안 지속되는지 검증
```

#### 예시 3: 데이터 버스트 길이 확인
```yaml
count_trigger:  i_valid        # 유효 데이터 신호 ⭐
target_pulse:   i_burst        # 버스트 기간
min:            16             # 최소 16 데이터
max:            64             # 최대 64 데이터

설명:
- i_burst가 HIGH인 동안 i_valid 엣지를 센다
- 버스트당 16~64개의 유효 데이터가 있는지 검증
```

**잘못된 이해 vs 올바른 이해**:

❌ **잘못된 이해**:
"count_trigger가 HIGH일 때만 측정한다"

✅ **올바른 이해**:
"count_trigger의 rising edge를 센다"
- target_pulse가 HIGH인 동안
- count_trigger의 rising edge 개수를 카운트
- 이것이 펄스의 "폭"

---

### 📊 PulseWidth Assertion

#### hpulse vs vpulse

PulseWidth는 두 가지 모드가 있으며, Count_Trigger의 의미가 다릅니다:

---

### 🔵 hpulse (Clock-based Pulse Width)

#### Count_Trigger: `base_clock` (기준 클럭)

**의미**: "클럭 사이클로 펄스 폭 측정"

**동작 방식**:
```
1. target_signal이 HIGH가 되면 측정 시작
2. base_clock의 rising edge마다 카운터 증가
3. target_signal이 LOW가 되면 측정 종료
4. 카운터 값이 min~max 범위인지 확인
```

**실제 예시**:

#### 예시 1: Hsync 펄스 폭 (1080p@60Hz)
```yaml
pulse_type:     hpulse
base_clock:     I_CLK          # 148.5MHz 픽셀 클럭 ⭐
target_signal:  o_hsync        # Hsync 펄스
min:            44             # 44 클럭 사이클
max:            44             # 44 클럭 사이클 (정확히)

타이밍:
I_CLK:    ┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓┏┓
          ┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛┗┛
o_hsync:  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
                                                                ┗━━━━━━━━
          ├────────────── 44 cycles ──────────────┤

설명: 
- o_hsync가 HIGH인 동안 I_CLK 엣지를 센다
- 44개의 클럭 사이클이어야 함
- 1080p 표준 타이밍 검증
```

#### 예시 2: Enable 신호 지속 시간
```yaml
pulse_type:     hpulse
base_clock:     sys_clk        # 100MHz 시스템 클럭 ⭐
target_signal:  chip_enable    # 칩 enable 신호
min:            100            # 최소 100 사이클 (1us)
max:            1000           # 최대 1000 사이클 (10us)

설명:
- chip_enable이 HIGH로 유지되는 시간을 클럭으로 측정
- 1us ~ 10us 사이여야 함 (100MHz 클럭 기준)
```

---

### 🟢 vpulse (Event-based Pulse Width)

#### Count_Trigger: `trigger_signal` (이벤트 감지)

**의미**: "특정 이벤트 사이의 펄스 폭 측정"

**동작 방식**:
```
1. trigger_signal rising edge: 측정 시작
2. target_signal의 HIGH 기간을 카운트
3. trigger_signal falling edge: 측정 종료
4. 카운터 값이 min~max 범위인지 확인
```

**실제 예시**:

#### 예시 1: 프레임당 액티브 라인 수
```yaml
pulse_type:      vpulse
trigger_signal:  i_frame_valid  # 프레임 유효 기간 ⭐
target_signal:   i_line_valid   # 라인 유효 신호
min:             1080            # 최소 1080 라인
max:             1080            # 최대 1080 라인

타이밍:
i_frame_valid:  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  (trigger)                                   ┗━━━━━━━━━━━━
                ↑ 측정 시작                  ↑ 측정 종료

i_line_valid:   ━┓ ┏━┓ ┏━┓ ┏━┓ ... ┏━┓ ┏━┓
  (target)       ┗━┛ ┗━┛ ┗━┛ ┗━┛     ┗━┛ ┗━┛
                 1   2   3   4  ...  1079 1080
                 ├─── 1080 pulses ────┤

설명:
- 프레임이 유효한 동안 (i_frame_valid HIGH)
- 라인 펄스(i_line_valid)가 몇 개 발생하는지 센다
- 정확히 1080개 라인이어야 함
```

#### 예시 2: 패킷당 데이터 워드 수
```yaml
pulse_type:      vpulse
trigger_signal:  i_packet_active  # 패킷 전송 중 ⭐
target_signal:   i_data_valid     # 데이터 유효
min:             64                # 최소 64 워드
max:             256               # 최대 256 워드

설명:
- 패킷이 전송되는 동안 (i_packet_active HIGH)
- 유효한 데이터 워드(i_data_valid)가 몇 개인지 센다
- 64~256개 사이여야 함
```

#### 예시 3: 버스트 전송 길이 측정
```yaml
pulse_type:      vpulse
trigger_signal:  i_burst_req      # 버스트 요청 ⭐
target_signal:   i_ack            # 응답 신호
min:             4                 # 최소 4 응답
max:             16                # 최대 16 응답

설명:
- 버스트 요청이 활성화된 동안
- 몇 개의 응답(i_ack)이 오는지 센다
- 4~16개 사이여야 함
```

**hpulse vs vpulse 비교**:

| 항목 | hpulse | vpulse |
|------|--------|--------|
| **측정 기준** | 클럭 사이클 | 이벤트 개수 |
| **Count_Trigger** | 기준 클럭 (base_clock) | 이벤트 신호 (trigger_signal) |
| **용도** | 절대 시간 측정<br>(몇 클럭 동안?) | 상대 카운트<br>(몇 번 발생?) |
| **예시** | "44 클럭 사이클" | "1080 라인" |
| **비디오 활용** | Hsync/Vsync 펄스 폭 | 프레임당 라인 수 |

---

## 실전 예제 모음

### 📺 비디오 타이밍 검증

#### 1080p@60Hz 완전한 검증

```yaml
# 1. Horizontal Active Period (HACT)
count_trigger:  i_hsync          # 라인 카운트용
target:         i_de             # 데이터 enable
min:            1920             # 1920 픽셀
max:            1920

# 2. Horizontal Sync Width (HSW)
count_trigger:  i_clk            # 픽셀 클럭
target_pulse:   i_hsync
min:            44               # 44 클럭
max:            44

# 3. Horizontal Back Porch (HBP)
hsync_signal:   i_hsync
data_enable:    i_de
min:            148              # 148 클럭
max:            148

# 4. Vertical Sync Width (VSW)
count_trigger:  i_hsync          # 라인 카운트용
target_pulse:   i_vsync
min:            5                # 5 라인
max:            5
```

### 🔄 데이터 트랜잭션 검증

#### AXI 버스 트랜잭션

```yaml
# Burst Length Check
count_trigger:  i_valid & i_ready  # 유효 트랜잭션
target_pulse:   i_burst_active     # 버스트 기간
min:            4                   # 최소 4 beats
max:            256                 # 최대 256 beats

# Response Timing
pulse_type:     hpulse
base_clock:     axi_clk            # AXI 클럭
target_signal:  i_resp_valid       # 응답 유효
min:            1                   # 최소 1 클럭
max:            10                  # 최대 10 클럭
```

### 📨 패킷 프로세싱

```yaml
# Packet Size Verification
pulse_type:     vpulse
trigger_signal: i_packet_start     # 패킷 시작/끝
target_signal:  i_byte_valid       # 바이트 유효
min:            64                  # 최소 64 바이트
max:            1518                # 최대 1518 바이트 (Ethernet)

# Inter-packet Gap
pulse_type:     hpulse
base_clock:     eth_clk            # 이더넷 클럭
target_signal:  i_idle             # 아이들 기간
min:            12                  # 최소 12 클럭 (96ns @ 125MHz)
max:            1000                # 최대
```

---

## 자주 하는 실수와 해결책

### ❌ 실수 1: Counter Trigger를 트리거 이벤트로 착각

**잘못된 이해**:
```yaml
# Counter assertion에서
trigger_con: i_clk    # "클럭마다 체크한다?"
```

**올바른 이해**:
```yaml
trigger_con: i_frame_end    # "프레임 끝날 때 카운터를 체크한다"
# i_clk은 카운팅 기준이 아니라 체크 시점!
```

**해결책**: 
- Counter assertion의 trigger_con = "언제 확인할까?"
- HSW의 count_trigger = "무엇으로 셀까?"
- 목적이 다름!

---

### ❌ 실수 2: hpulse와 vpulse 혼동

**잘못된 설정**:
```yaml
# 라인 수를 세고 싶은데...
pulse_type:     hpulse
base_clock:     i_hsync    # ❌ 틀림!
target_signal:  i_frame_valid
```

**올바른 설정**:
```yaml
# 라인 수는 이벤트 카운팅이므로 vpulse!
pulse_type:     vpulse
trigger_signal: i_frame_valid    # ✅ 맞음!
target_signal:  i_hsync
```

**해결책**:
- 시간 측정 (몇 클럭?) → hpulse
- 개수 세기 (몇 번?) → vpulse

---

### ❌ 실수 3: Count Trigger를 Target과 혼동

**잘못된 이해**:
```yaml
# HSW에서
count_trigger: i_hsync    # "Hsync를 측정한다?"
target_pulse:  i_clk      # "클럭을 센다?"
```

**올바른 이해**:
```yaml
count_trigger: i_clk      # "클럭으로 센다" (ruler)
target_pulse:  i_hsync    # "Hsync를 측정한다" (target)
```

**해결책**:
- count_trigger = 자 (측정 도구)
- target_pulse = 측정 대상

---

## 빠른 참조표

### Counter Assertion

| 필드 | 역할 | 예시 |
|------|------|------|
| target | 무엇을 셀까? | i_line_valid (라인) |
| plus_con | 언제 증가? | 1 (항상) |
| reset_con | 언제 리셋? | i_frame_start (프레임 시작) |
| **trigger_con** | **언제 확인?** | **i_frame_end (프레임 끝)** |
| exp_cnt_val | 예상 값? | 1080 (라인 수) |

### HSW Assertion

| 필드 | 역할 | 예시 |
|------|------|------|
| **count_trigger** | **무엇으로 셀까?** | **i_clk (클럭)** |
| target_pulse | 무엇을 측정? | i_hsync (Hsync 펄스) |
| min | 최소? | 44 (클럭) |
| max | 최대? | 44 (클럭) |

### PulseWidth hpulse

| 필드 | 역할 | 예시 |
|------|------|------|
| pulse_type | 모드 | hpulse (클럭 기반) |
| **base_clock** | **무엇으로 셀까?** | **I_CLK (픽셀 클럭)** |
| target_signal | 무엇을 측정? | o_hsync |
| min | 최소? | 10 (클럭) |
| max | 최대? | 20 (클럭) |

### PulseWidth vpulse

| 필드 | 역할 | 예시 |
|------|------|------|
| pulse_type | 모드 | vpulse (이벤트 기반) |
| **trigger_signal** | **언제 측정?** | **i_frame_valid (프레임 동안)** |
| target_signal | 무엇을 측정? | i_line_valid (라인) |
| min | 최소? | 1080 (라인) |
| max | 최대? | 1080 (라인) |

---

## 마치며

### 핵심 기억할 점

1. **Counter Trigger ≠ Trigger Signal**
   - 같은 "trigger"라는 단어지만 의미가 다름
   - 문맥에 따라 "참조", "확인 시점", "이벤트 감지" 등으로 해석

2. **항상 질문하기**
   - "무엇을" 셀 것인가? → target / target_pulse
   - "무엇으로" 셀 것인가? → count_trigger / base_clock
   - "언제" 확인할 것인가? → trigger_con / trigger_signal

3. **타입별 목적 이해**
   - Counter: 정확한 개수 세기
   - HSW/HBP/etc: 타이밍 범위 검증
   - PulseWidth: 펄스 폭 측정 (절대/상대)

4. **비디오는 계층적**
   - Pixel level: 클럭 사이클
   - Line level: 픽셀 수 또는 라인 펄스
   - Frame level: 라인 수 또는 프레임 펄스

### 추가 리소스

- `docs/PULSEWIDTH_IMPROVEMENTS.md` - PulseWidth 상세 가이드
- `docs/QUICK_START_VIDEO_ASSERTIONS.md` - 비디오 assertion 빠른 시작
- `docs/EXPECTED_VALUE_IMPROVEMENTS.md` - 파라미터 사용법

---

**작성일**: 2025-11-18  
**버전**: 1.0  
**문의**: 이 문서에 대한 질문이나 추가 예시가 필요하면 요청하세요!
