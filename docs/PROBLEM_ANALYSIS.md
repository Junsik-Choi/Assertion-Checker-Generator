# 문제 분석 및 해결 내역

## 원인 분석

### 1차 문제: 이모지로 인한 TUI 깨짐
**원인:**
- cli_tui.py에서 에러 메시지에 이모지(❌, ✅ 등) 사용
- Windows Terminal의 PowerShell에서 이모지가 제대로 렌더링되지 않음
- 한글도 마찬가지로 curses 환경에서 문제 발생 가능

**해결:**
- 모든 이모지를 ASCII 텍스트로 변경
- "❌ Error" → "ERROR"
- 10개 위치에서 이모지 제거 완료

### 2차 문제: Step 2에서 "ERROR: No instances found" 표시
**원인:**
- `state.onboarding_modules`가 비어있음
- Line 1758+의 RTL 처리 코드가 실행되지 않음
- Line 1191의 오래된 코드가 먼저 실행되어 stage를 'module'로 변경
- 결과적으로 새로운 인스턴스 탐색 로직이 스킵됨

**근본 원인:**
1. **메인 루프(Line 1191)**에서 RTL 입력을 처리하여 `build_context_from_rtl()` 호출
2. 이 함수는 모듈 타입만 반환 (예: sync_signal)
3. `state.onboarding_modules`에 모듈 타입 저장
4. **그 후** Line 1758+의 `_handle_command`로 가지만 이미 stage가 'module'이 되어 스킵
5. **Onboarding input handler(Line 5156)**에서도 같은 문제 발생

**해결:**
- Line 1191의 RTL 처리 제거, `_handle_command`로 라우팅
- Line 5156의 `build_context_from_rtl()` 호출 제거
- RTL 처리를 Line 1758+의 통합된 로직으로만 수행

### 3차 문제: find_module_instances_by_file()이 빈 결과 반환
**원인:**
- 기존 로직: Top-down DFS (상위 모듈에서 하향 탐색)
- tb_top 모듈이 파싱되지 않음 (Malformed module header)
- 결과: sync_signal을 사용하는 경로를 찾지 못함

**사용자 요구사항:**
> "일단 모든 경로가 완성되지 않아도 현재 자신의 모듈이 사용된 것들을 찾아서
> 거기서부터 하나씩 위로 올라가다가 더 없으면 끊어야지"

**해결:**
- **Bottom-up 방식으로 재구현**:
  1. target_module을 직접 인스턴스화하는 모든 (parent, instance_name) 찾기
  2. 각 인스턴스에 대해 parent를 위로 추적
  3. 더 이상 parent가 없으면 거기서 끊기
  4. 부분 경로라도 반환 (예: u0_sync_signal만이라도 표시)

**코드 변경:**
```python
# 기존: Top-down DFS
def dfs_find_instances(parent_type, chain, chain_meta):
    # parent에서 child 찾기 (하향식)
    
# 신규: Bottom-up 추적
direct_usages = []  # target_module을 사용하는 모든 곳 찾기
for parent_module, instance_name, params in direct_usages:
    # 위로 올라가며 경로 구축
    while depth < max_depth:
        found_upper_parent = False
        # parent_module을 인스턴스화하는 상위 모듈 찾기
```

## 최종 수정 사항

### cli_tui.py
1. **Line 1178-1191**: RTL stage 처리를 `_handle_command`로 라우팅
2. **Line 5156**: `build_context_from_rtl()` 호출 제거
3. **10개 위치**: 이모지 → ASCII 텍스트 변경

### rtl_parser.py
1. **Line 659-755**: `find_module_instances_by_file()` 완전히 재작성
   - Top-down → Bottom-up 방식
   - 부분 경로도 반환
   - display 필드 추가 (TUI 표시용)

## 검증 결과

### 자동화 테스트 (test_tui_automation.py)
```
TEST 1: RTL Parsing - PASS
  - Files discovered: 53
  - Modules parsed: 14
  - Instances found: 4
  - Expected: ['u0_sync_signal', 'u1_sync_signal', 'u2_sync_signal', 'u3_sync_signal']
  - Got: ['u0_sync_signal', 'u1_sync_signal', 'u2_sync_signal', 'u3_sync_signal']
  ✓ MATCH

TEST 2: Module Selection - PASS
TEST 3: Hierarchy Discovery - PASS

ALL TESTS PASSED!
```

### 독립 테스트 (test_step1_direct.py)
```
Instances found: 4
state.onboarding_modules set to: ['u0_sync_signal', 'u1_sync_signal', 'u2_sync_signal', 'u3_sync_signal']

RESULT: Step 2 would display:
[1] u0_sync_signal
[2] u1_sync_signal
[3] u2_sync_signal
[4] u3_sync_signal
```

## 다음 단계

### 수동 TUI 테스트 필요
사용자가 직접 TUI를 실행하여 확인:
```powershell
python scripts/cli_tui.py
```

**예상 결과:**
1. Step 1: `EDA/RTL/sync_signal.v` 입력
2. Step 2: 4개의 인스턴스 표시 (u0~u3_sync_signal)
3. Step 3: Hierarchy 선택
4. Step 4: Excel 경로 설정
5. Dashboard에서 `new` 명령으로 assertion 생성

### Pulse Width Assertion 생성
1. `new` 명령 실행
2. pulse_width 타입 선택
3. Signal: `i_hsw`
4. Min: `10` clocks
5. Max: `20` clocks
6. `generate` 명령으로 파일 생성

## 기술적 통찰

### 왜 기존 방식이 실패했는가?

**Top-down DFS의 한계:**
- 완전한 계층 구조가 필요
- Top module이 파싱되지 않으면 전체 탐색 실패
- Testbench 파일 파싱 실패 시 모든 하위 모듈 찾기 불가

**Bottom-up 방식의 장점:**
- 직접 사용처부터 시작 → 항상 최소한의 결과 보장
- 위로 올라가다가 막히면 거기서 끊음 → 부분 경로라도 유효
- Testbench 파싱 실패와 무관하게 동작
- 사용자 요구사항과 정확히 일치

### 코드 경로 문제
TUI에서 여러 곳에서 RTL 입력을 처리하려고 시도:
1. Line 1191: 메인 루프의 직접 처리
2. Line 1758+: Command handler의 통합 처리
3. Line 5156: Onboarding input handler

**해결:** 모든 처리를 Line 1758+의 통합된 위치로 집중
→ 코드 중복 제거, 일관된 동작 보장

## 성공 기준 달성 여부

✓ 이모지 제거 완료
✓ 인스턴스 탐색 로직 수정 완료 (Bottom-up)
✓ 코드 경로 통합 완료
✓ 자동화 테스트 통과
✓ 부분 경로 반환 지원 (testbench 파싱 실패에도 동작)

⏳ 수동 TUI 테스트 대기 (사용자 확인 필요)
⏳ Pulse width assertion 생성 테스트 대기
⏳ Assertion interface 파일 생성 확인 대기
