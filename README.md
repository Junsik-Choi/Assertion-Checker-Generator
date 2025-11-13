# Assertion-Checker-Generator# Assertion-Checker-Generator

[Harman] Assertion Checker Generator with Interactive TUI[Harman] Assertion Checker Generator



SystemVerilog Assertion 자동 생성 도구 - RTL 파싱부터 Assertion 생성까지 완벽 지원RTL Auto Parsing & Excel Editing

-------------------------

---

<img width="1118" height="326" alt="Image" src="https://github.com/user-attachments/assets/ea501a9a-45a3-43d9-93bc-8caf7922bd50" />

## 📋 목차<br>

- [개요](#개요)<div align=center>

- [주요 기능](#주요-기능)RTL Auto Parsing 실행 예시

- [시작하기](#시작하기)</div>

- [TUI 사용법](#tui-사용법)

- [Assertion Builder](#assertion-builder)<br><br>

- [플러그인 시스템](#플러그인-시스템)검증 대상이 될 RTL을 물리면 상위 폴더로 올라가면서 .v파일들을 탐색하고 계층 분석을 통해 검증될 Target Block의 Instanse 정보를 JSON으로 저장한다.

- [Gen 명령어](#gen-명령어)저장되는 정보는

- [프로젝트 구조](#프로젝트-구조)**Top path, module, instance name, clock, reset, input, output, inout, parameter**가 있다.

- [문서](#문서)<br>

  

---**TOP Path :** Parsing 이외에 사용자가 입력해 주는 Path이다. 

예를들어 SVA검증 대상 경로가 top.dut.WRAPPER_BLK_ABC.blk_abc.u_module_a.u_sub_module_b 라고 했을 때, parsing의 결과가 blk_abc.u_module_a.u_sub_module_b인 경우 TOP Path입력을top.dut.WRAPPER_BLK_ABC.blk_abc.u_module_a와 같이 입력한다면, top.dut.WRAPPER_BLK_ABC.blk_abc.u_module_a는 `TOP_PATH 로 local define되고 Checker Interface 내부에는 `TOP_PATH.u_sub_module_b나 `TOP_PATH.u_sub_module_b.i_clk 와 같이 짧은 경로가 사용되어 가독성을 향상 시킬 수 있다.

## 개요<br><br>

**module :** 검증 대상이 된 instance의 module name 원형이다.

Assertion-Checker-Generator는 RTL 설계 검증을 위한 SystemVerilog Assertion(SVA)을 자동으로 생성하는 도구입니다. 

**paths :** 검증 대상이 된 instance의 TOP_PATH 부분을 제외한 RTL Path이다. 만약 한 module안에 검증해야할 같은 구조의 module들이 있다면 한꺼번에 SVA Checker생성이 가능하도록 여러 path를 list로 받아 저장할 수 있도록 하였다. 여러개의 instance를 받은 경우 같은 내부 포트 정보를 공유하므로 path 정보만 교체하면서 각각의 input에 대해 같은 목적의 Checker를 활용하여 검증이 가능하도록 구현 할 예정이다.

### 핵심 특징

- **자동 RTL 파싱**: Verilog/SystemVerilog 파일의 계층 구조, 포트, 파라미터를 자동 추출**instances :** 검증 대상이 된 instance들의 이름들을 list형식으로 나타낸다.

- **Excel 기반 워크플로우**: 비엔지니어도 쉽게 assertion 사양을 작성 가능

- **플러그인 아키텍처**: 새로운 assertion 타입을 쉽게 추가할 수 있는 확장 가능한 구조**clocks :** i_clk, i_sclk, i_aclk, i_CLK, I_CLK, i_clock... 등 여러가지 일반적인 clock naming rule을 따라 clock이라 예상되는 input을 받아 저장한다.

- **인터랙티브 TUI**: 직관적인 터미널 UI로 세션 기반 작업 지원

- **실전 검증 준비**: 생성된 SV 코드는 UVM 테스트벤치에 바로 통합 가능**resets :** i_rst, i_rstn, i_reset, I_RST, i_GRESETn... 등 여러가지 일반적인 reset naming rule을 따라 reset이라 예상되는 input을 받아 저장한다.



---**input :** clock과 reset, parameter를 제외한 input들의 이름과 width 정보를 저장한다.



## 주요 기능**output :** output port들의 이름과 width 정보를 저장한다.



### 1. RTL 자동 파싱 & 계층 분석**inout :** inout port들의 이름과 width 정보를 저장한다.



<div align=center>**parameter :** p_* 인 parameter나 SFR, Register setting 등의 input port를 저장한다.

<img width="1118" height="326" alt="RTL Parsing Example" src="https://github.com/user-attachments/assets/ea501a9a-45a3-43d9-93bc-8caf7922bd50" />

<br>+ `BIT_WIDTH 와 같은 local param이나 define되어있는 정보는 마찬가지로 목표 instance 내부와 외부에서 탐색하여 현재 설정된 값으로 대체하여 활용한다.

RTL Auto Parsing 실행 예시+ 또한, excel로 가져올 때는 bit가 총 몇 비트인지가 중요하기 때문에 [15:0] 같은 값은 16 bits 라고 간소화 하여 불러온다.

</div>

<div align=center>

검증 대상 RTL 파일을 지정하면 상위 폴더를 탐색하여 모든 .v/.sv 파일을 찾고, 계층 구조를 분석하여 검증할 타겟 블록의 정보를 JSON으로 저장합니다.<br><br> 

<center> <img width="485" height="636" alt="Image" src="https://github.com/user-attachments/assets/f456ae8c-8279-4ce7-9314-1a4b70e52475" /> </center>

#### 추출되는 정보<br>

- **TOP Path**: 사용자 지정 최상위 경로 (예: `top.dut.WRAPPER_BLK_ABC`)출력된 JSON파일

- **Module**: 검증 대상 인스턴스의 모듈명<br> <br>

- **Paths**: TOP_PATH를 제외한 RTL 경로 (여러 인스턴스 일괄 처리 지원)<img width="447" height="444" alt="Image" src="https://github.com/user-attachments/assets/6d71d4a5-e82d-4200-a6c1-98174c18a8ce" />

- **Instances**: 검증 대상 인스턴스 이름들<br>엑셀 출력 log

- **Clocks**: `i_clk`, `i_sclk` 등 일반적인 clock naming 패턴 자동 인식<br> <br>

- **Resets**: `i_rst`, `i_rstn`, `i_reset` 등 reset 신호 자동 인식<img width="1447" height="515" alt="Image" src="https://github.com/user-attachments/assets/7d286dc7-58b5-451a-8483-86d5abdc341c" />

- **Input/Output/Inout**: 포트 이름과 비트 폭 정보<br>

- **Parameters**: `p_*` 파라미터 및 SFR/Register 설정 입력최종 결과물

<br><br>

#### 스마트 파싱</div>

- **Local Parameter 치환**: `` `BIT_WIDTH `` 같은 로컬 파라미터나 define을 실제 값으로 자동 치환

- **비트 폭 간소화**: `[15:0]`을 `16 bits`로 표현하여 Excel에서 직관적으로 표시모듈형 Assertion Builder (scripts/assertion_builder.py)

-----------------------------------------------

<div align=center>본 도구는 RTL을 자동으로 분석하여 모듈의 포트/클럭/리셋/파라미터 정보를 수집하고, Excel 시트의 내용을 바탕으로 Assertion Checker(SV)를 자동 생성한다. 각 시트 타입은 플러그인으로 분리되어 있으며, 새로운 시트가 추가되더라도 해당 시트에 대응하는 플러그인만 추가하면 쉽게 확장할 수 있도록 구성하였다.

<img width="485" height="636" alt="JSON Output" src="https://github.com/user-attachments/assets/f456ae8c-8279-4ce7-9314-1a4b70e52475" />

<br>구성 요약

출력된 JSON 파일본 기능은 `scripts/rtl_parser.py`로 .v/.sv 파일을 분석하고, `scripts/fill_define.py`와 JSON 연동으로 Excel의 Define 시트를 자동으로 채우며, `scripts/assertions/*` 하위 플러그인을 통해 시트별 SV 생성 로직을 수행한다.

<br><br>

<img width="447" height="444" alt="Excel Log" src="https://github.com/user-attachments/assets/6d71d4a5-e82d-4200-a6c1-98174c18a8ce" /><div align=center>

<br><img width="1100" height="320" alt="Image" src="https://github.com/user-attachments/assets/TODO_interactive_01" />

Excel 출력 로그<br>

<br><br>모듈형 Assertion Builder 개요(추가 예정)

<img width="1447" height="515" alt="Final Result" src="https://github.com/user-attachments/assets/7d286dc7-58b5-451a-8483-86d5abdc341c" /></div>

<br>

최종 결과물: Define 시트가 채워진 Excel주요 파일

</div>- `scripts/assertion_builder.py` : 통합 오케스트레이터(인터랙티브/CLI)

- `scripts/assertions/base.py` : 플러그인 베이스 인터페이스

---- `scripts/assertions/registry.py` : 플러그인 등록/조회

- `scripts/assertions/counter.py` : `counter_gen` 시트 플러그인 예시

### 2. 인터랙티브 TUI (Terminal User Interface)

---

**실행:**

```bash인터랙티브 모드 (무옵션 실행)

python scripts/cli_tui.py-------------------------

```아무 옵션 없이 실행하면 사용자 친화적인 마법사가 실행된다. 한 번에 여러 모드를 함께 선택하여 수행할 수 있다(예: Define 채움 + JSON 출력 + SV 생성).



#### TUI 주요 기능```

- **세션 관리**: 작업 내용을 저장하고 나중에 다시 로드python scripts/assertion_builder.py

- **마법사 기반 온보딩**: RTL → 모듈 → 계층 → Excel 순서로 단계별 설정```

- **실시간 포트 정보 표시**: Dashboard에서 clock, reset, input/output 확인

- **Assertion 생성 마법사**: `new` 명령어로 다양한 타입의 assertion 생성마법사 흐름

- **파일 생성**: `gen` 명령어로 완성된 SystemVerilog 파일 생성1) RTL 시작 경로 선택: 기본 후보(예: `EDA/RTL`)를 먼저 제시하며, 필요 시 직접 입력할 수 있다.

2) 타깃 모듈 선택: 파싱된 모듈 목록에서 번호로 선택한다(Top 후보는 상단에 배치된다).

#### TUI 명령어3) Excel 파일 선택: `Data/` 폴더 내 `.xlsx`를 자동 탐색하여 리스트를 보여주고, 번호 선택 또는 직접 입력할 수 있다.

```4) 출력 폴더 지정: 기본값은 `out/assertions`이며 자유롭게 변경할 수 있다.

Commands:5) 모드 선택(복수 선택 가능): Define 시트 채우기 / 입력 JSON 출력 / SV 생성 중 원하는 조합을 선택한다.

  help [command]  - 도움말 표시6) 플러그인 선택(복수 선택 또는 All): 예) `counter`(기본 제공). 플러그인 추가 시 목록에 자동 반영된다.

  new             - 새 assertion 생성 마법사

  gen             - SystemVerilog 파일 생성 마법사<div align=center>

  show            - 현재 세션 정보 표시<img width="1100" height="320" alt="Image" src="https://github.com/user-attachments/assets/TODO_interactive_02" />

  save [path]     - 세션 저장<br>

  load <path>     - 세션 로드인터랙티브 마법사 예시 화면(추가 예정)

  export          - Excel로 내보내기</div>

  quit / exit     - 종료

```실행 결과

- 선택한 모드에 따라 Define 시트가 업데이트되고, 입력 JSON과 SV 파일이 출력됩니다.

---- 오류/경고 메시지는 콘솔에 표시되며, 필요한 경우 조치 안내를 제공합니다.



### 3. Assertion Builder (scripts/assertion_builder.py)---



RTL을 자동으로 분석하여 모듈 정보를 수집하고, Excel 시트 내용을 바탕으로 Assertion Checker(SV)를 자동 생성합니다.CLI 모드(비대화형)

-----------------

#### 구성 요소기존 방식도 그대로 지원한다. 자동화 스크립트/CI 환경에서 사용하기에 적합하다.

- **`scripts/rtl_parser.py`**: Verilog/SystemVerilog 파서

- **`scripts/fill_define.py`**: Excel Define 시트 자동 채움```

- **`scripts/assertions/*`**: 플러그인 기반 SV 생성 로직python scripts/assertion_builder.py \

  --rtl-start EDA/RTL \

#### 인터랙티브 모드  --target-module blur_scaler \

  --excel Data/Assertion_TF.xlsx \

```bash  --auto-define-fill \

python scripts/assertion_builder.py  --json \

```  --out out/assertions

```

**마법사 흐름:**

1. **RTL 경로 선택**: 기본 후보(`EDA/RTL`) 제시 또는 직접 입력옵션 요약

2. **타겟 모듈 선택**: 파싱된 모듈 목록에서 선택 (Top 후보 우선 표시)- `--rtl-start <path>` : RTL 시작 경로(파일/디렉터리)

3. **Excel 파일 선택**: `Data/` 폴더 내 `.xlsx` 자동 탐색- `--target-module <name>` : 대상 모듈명(미지정 시 자동 추정)

4. **출력 폴더 지정**: 기본값 `out/assertions`- `--excel <path>` : 참조 Excel 경로

5. **모드 선택 (복수 가능)**:- `--use-default-excel` : `Data/Assertion_TF.xlsx` 강제 사용

   - Define 시트 채우기- `--auto-define-fill` : Define 시트 자동 채움 실행

   - 입력 JSON 출력- `--enable <name>` : 사용할 플러그인만 선택(복수 지정 가능)

   - SV 생성- `--json` : 포트/시트 파싱 결과를 통합 JSON으로 출력

6. **플러그인 선택**: 사용할 assertion 타입 선택 (또는 All)- `--out <dir>` : 결과 출력 디렉터리(기본: `out/assertions`)



#### CLI 모드 (자동화/CI 환경)---



```bashDefine 시트 자동 채움 흐름

python scripts/assertion_builder.py \---------------------

  --rtl-start EDA/RTL \1) 모듈의 `clocks/resets/inputs/outputs/inouts/parameters` 정보를 취합한다.

  --target-module blur_scaler \2) 이를 `module_define.json`으로 저장한다.

  --excel Data/Assertion_TF.xlsx \3) `scripts/fill_define.py`를 호출하여 지정 Excel의 Define 시트를 자동으로 채운다.

  --auto-define-fill \

  --json \<div align=center>

  --out out/assertions<img width="1100" height="320" alt="Image" src="https://github.com/user-attachments/assets/TODO_define_log" />

```<br>

Define 채움 로그 화면(추가 예정)

**옵션:**<br><br>

- `--rtl-start <path>`: RTL 시작 경로<img width="1100" height="320" alt="Image" src="https://github.com/user-attachments/assets/TODO_define_excel_result" />

- `--target-module <name>`: 대상 모듈명<br>

- `--excel <path>`: Excel 파일 경로Excel Define 시트 결과(추가 예정)

- `--auto-define-fill`: Define 시트 자동 채움</div>

- `--enable <name>`: 특정 플러그인만 사용

- `--json`: 통합 JSON 출력수동 실행 예시(필요 시)

- `--out <dir>`: 출력 디렉터리```

python scripts/fill_define.py Data/Assertion_TF.xlsx out/assertions/module_define.json

---```



### 4. 플러그인 시스템---



#### 지원되는 Assertion 타입플러그인 아키텍처로 시트별 확장

-------------------------

| 플러그인 | Excel 시트 | 모듈명 | 설명 |위치 및 구조

|---------|-----------|--------|------|- 플러그인 위치: `scripts/assertions/`

| **counter** | `counter_gen` | `assertion_counter` | 카운터 로직 및 임계값 체크 |- 베이스 클래스: `BaseAssertionPlugin`

| **handshake** | `handshake` | `assertion_gen` | 핸드셰이크 프로토콜 (2phase/4phase/ready_valid) |  - `plugin_name` : 플러그인 이름(e.g., `counter`)

| **delayCondition** | `delayCondition` | `assertion_delayCondition` | 시간 지연 조건 assertion (다중 세트 지원) |  - `sheet_name` : Excel 시트 이름(e.g., `counter_gen`)

| **pulseWidth** | `pulseWidth` | `assertion_hpulse`<br>`assertion_vpulse` | 펄스 폭 체크 (horizontal/vertical) |  - `parse(xls_path) -> dict` : 시트를 구조화하여 반환한다.

| **HACT** | `HACT` | `assertion_HACT` | 디스플레이 Horizontal Active 검증 |  - `generate_sv(parsed, context) -> List[str]` : SV 섹션 문자열 목록을 생성한다.

| **HBP** | `HBP` | `assertion_HBP` | 디스플레이 Horizontal Back Porch 검증 |- 등록: 새 파일의 플러그인 클래스 정의 위에 `@register` 데코레이터를 추가하면 자동 등록된다.

| **HSW** | `HSW` | `assertion_HSW` | 디스플레이 Horizontal Sync Width 검증 |

| **VFP** | `VFP` | `assertion_VFP` | 디스플레이 Vertical Front Porch 검증 |확장 작업 예시(프롬프트 가이드)

- “시트 `my_new_gen`의 헤더 A,B,C를 사용하여 property 패턴 P를 생성하는 플러그인을 추가해줘.”

#### 플러그인 구조- 기대 동작: `scripts/assertions/my_new.py`에 `BaseAssertionPlugin`을 상속한 클래스를 만들고 `sheet_name`을 `my_new_gen`으로 설정한 뒤, `parse`/`generate_sv`를 구현한다. 이후 빌더가 자동으로 인식한다.



플러그인은 `scripts/assertions/` 디렉터리에 위치하며, `BaseAssertionPlugin`을 상속합니다.<div align=center>

<img width="1100" height="320" alt="Image" src="https://github.com/user-attachments/assets/TODO_plugin_layout" />

```python<br>

from assertions.base import BaseAssertionPlugin플러그인 폴더 구조(추가 예정)

from assertions.registry import register</div>



@register---

class MyAssertionPlugin(BaseAssertionPlugin):

    plugin_name = "my_assertion"카운터 시트 플러그인(`counter_gen`) 상세

    sheet_name = "MySheet"------------------------------

    참조: `scripts/assertions/counter.py`

    def parse(self, xls_path: Path) -> Dict[str, Any]:

        """Excel 시트를 파싱하여 구조화된 데이터 반환"""시트 구성(예시)

        return {"blocks": [...]}- 좌측 테이블(기본 정보): [Name] [Edge Types] [Base Clock] [Reset Edge] [Reset Signal]

    - 우측 테이블(조건/동작): [Name] [Step(If/Else If/Else)] [Condition] [Action]

    def generate_sv(self, parsed: Dict, context: Dict) -> List[str]:

        """SystemVerilog 코드 생성"""헤더 매핑(요약)

        sv_module = "module assertion_my(...) ... endmodule"| Excel Header | 사용처 |

        sv_inst = "assign u_assertion.port = top.dut.port;"| --- | --- |

        return [sv_module, sv_inst]| Name | 카운터 블록 이름 및 오른쪽 테이블 그룹핑 키 |

```| Edge Types, Base Clock | `always @(posedge/negedge clk)` 감지 리스트 구성 |

| Reset Edge, Reset Signal | `or negedge rst` 등 비동기 감지 구성 |

**자동 등록**: `@register` 데코레이터를 사용하면 자동으로 플러그인이 등록되어 TUI와 Builder에서 사용 가능합니다.| Step | if/else if/else 단계 구분 |

| Condition | if/else if 조건식 |

#### 플러그인 추가하기| Action | 해당 블록 내부 수행 문장 |



새로운 assertion 타입 추가는 매우 간단합니다:생성 결과

- 각 Name에 대해 `always @(...) begin ... end` 블록을 생성하여 SV 섹션을 만든다.

1. `scripts/assertions/my_new.py` 파일 생성- 기존 `scripts/assertion_gen.py`의 카운터 생성 로직을 반영하여 호환성을 유지하였다.

2. `BaseAssertionPlugin` 상속 클래스 작성

3. `@register` 데코레이터 추가<div align=center>

4. `parse()` 및 `generate_sv()` 메서드 구현<img width="1100" height="320" alt="Image" src="https://github.com/user-attachments/assets/TODO_counter_sheet" />

<br>

자동으로 TUI의 `new` 명령어와 `gen` 명령어에서 사용 가능!Counter 시트 예시(추가 예정)

<br><br>

---<img width="1100" height="320" alt="Image" src="https://github.com/user-attachments/assets/TODO_counter_sv" />

<br>

### 5. Gen 명령어 (SystemVerilog 파일 생성)생성된 SV 섹션 예시(추가 예정)

</div>

TUI에서 `gen` 명령어를 사용하면 Excel에 작성된 assertion 사양으로부터 완성된 SystemVerilog 파일을 생성합니다.

---

#### Gen 명령어 특징

### 출력물

✅ **모든 플러그인 자동 통합**: 등록된 모든 플러그인의 assertion을 하나의 파일로 통합  - SV: `out/assertions/auto_assertion_checker.sv`

✅ **다중 데이터 포맷 지원**: `blocks`, `sets`, 직접 딕셔너리 등 다양한 플러그인 출력 포맷 자동 처리  - 통합 입력 JSON: `out/assertions/assertion_inputs.json`(옵션 `--json` 사용 시)

✅ **스마트 포트 집계**: 여러 플러그인의 input 포트를 자동으로 합쳐 중복 제거  - Define용 JSON: `out/assertions/module_define.json`(Define 채움 선택 시)

✅ **인스턴스 파일 생성**: 테스트벤치 통합을 위한 inst 파일 자동 생성  

✅ **에러 핸들링**: 플러그인 실패 시에도 다른 플러그인 계속 처리---



#### 사용 방법### 팁 및 문제 해결

- Excel 파일이 열려 있으면 쓰기 실패할 수 있습니다. Excel을 닫고 다시 시도하세요.

```- RTL 스캔 범위가 너무 넓거나 파일 인코딩이 특이한 경우 시간이 걸릴 수 있습니다.

> gen- 새로운 시트를 도입할 때는 작은 샘플로 먼저 플러그인을 개발/검증 후에 실제 TF에 적용하세요.
Enter filename: my_assertions
File type: [1] Interface [2] Instance [3] Both
> 3
Data source: [1] Assertions [2] Signals [3] Both
> 1
```

**미리보기**: 생성될 파일 내용을 확인한 후 `y`로 확정

#### 출력 파일

**Interface 파일** (`<filename>.if.sv`):
```systemverilog
`include "uvm_macros.svh"
import uvm_pkg::*;

interface assertion_intf
(
    input logic [0:0] i_clk,
    input logic [0:0] i_rstn,
    input logic [7:0] i_data,
    input logic [0:0] i_valid
    // ... 모든 플러그인의 input 포트 집계
);

// counter
reg [31:0] cnt;
always @(posedge i_clk or negedge i_rstn) begin
    if(!i_rstn) cnt <= 0;
    else if(i_valid) cnt <= cnt+1;
end
assert property (p_counter_check) else $error("Counter check failed");

// ===== Next plugin section =====

// handshake
property p_2phase_check(req, ack);
    @(posedge i_clk) disable iff(!i_rstn)
    (~req & ~ack) |-> ##1 ((req & ~ack) or (req & ack) or (~req & ~ack));
endproperty
assert property (p_2phase_check(req, ack)) else $error("Handshake failed");

// ===== Next plugin section =====

// delayCondition - 다중 세트 지원
property p_delayCondition_check1(trigger, result);
    @(posedge i_clk) disable iff(!i_rstn)
    $rose(trigger) |-> ##[1:5] $rose(result);
endproperty
assert property (p_delayCondition_check1(i_trigger1, i_result1));

// ===== Next plugin section =====

// pulseWidth
property p_hpulse;
    int value_count;
    @(posedge i_clk) disable iff(!i_rstn)
    (i_signal) |-> (1, value_count = 0)
    ##1 (i_signal, value_count++)[*0:$]
    ##1 (!i_signal, value_count++)
    ##0 (i_min <= value_count && value_count <= i_max);
endproperty
assert property (p_hpulse) else $error("Pulse width check failed");

endinterface
```

**Instance 파일** (`<filename>.inst.sv`):
```systemverilog
`include "uvm_macros.svh"
import uvm_pkg::*;

assertion_counter
      u_assertion_counter();

assertion_gen
      u_assertion_gen();

assertion_delayCondition
      u_assertion_delayCondition();

assertion_hpulse
      u_assertion_hpulse();

// Port assignments
assign u_assertion_counter.i_clk = top.dut.i_clk;
assign u_assertion_counter.i_rstn = top.dut.i_rstn;
assign u_assertion_counter.i_data = top.dut.i_data;
assign u_assertion_gen.req = top.dut.req;
assign u_assertion_gen.ack = top.dut.ack;
// ... 모든 포트 자동 연결
```

#### Gen 명령어 내부 동작

1. **플러그인 탐색**: `get_registered_plugins()`로 모든 등록된 플러그인 가져오기
2. **데이터 파싱**: 각 플러그인의 `parse()` 메서드로 Excel 시트 읽기
3. **SV 생성**: 각 플러그인의 `generate_sv()` 메서드로 코드 생성
4. **포트 집계**: 모든 플러그인의 input 선언 추출 및 중복 제거
5. **인터페이스 구축**: 통합 `interface assertion_intf` 생성
6. **인스턴스 구축**: 모듈 인스턴스 및 assign 문 생성

---

## 시작하기

### 필수 요구사항
- Python 3.7 이상
- openpyxl (Excel 처리)
- 기타 의존성: `requirements.txt` 참조

### 설치

```bash
git clone https://github.com/Junsik-Choi/Assertion-Checker-Generator.git
cd Assertion-Checker-Generator
pip install -r requirements.txt
```

### 빠른 시작

#### 1. TUI로 시작하기
```bash
python scripts/cli_tui.py
```
- 마법사를 따라 RTL 파일, 모듈, Excel 설정
- `new` 명령어로 assertion 추가
- `gen` 명령어로 SV 파일 생성

#### 2. Assertion Builder로 시작하기
```bash
python scripts/assertion_builder.py
```
- 인터랙티브 모드로 Define 시트 채우기
- 플러그인 선택하여 SV 생성

---

## TUI 사용법

### 온보딩 (첫 실행)

1. **RTL 파일 지정**
   ```
   Step 1/4 - RTL: Enter path to .v or .sv file
   > EDA/RTL/sync_signal.v
   ```

2. **모듈 선택**
   ```
   Step 2/4 - Module: number+Enter
   [1] u0_sync_signal
   [2] u1_sync_signal
   > 1
   ```

3. **계층 선택**
   ```
   Step 3/4 - Hierarchy: Enter/number/custom
   > <Enter>  (기본값 사용)
   ```

4. **Excel 설정**
   ```
   Step 4/4 - Excel: path or Enter for default
   > <Enter>  (Data/Assertion_TF.xlsx 사용)
   ```

### Dashboard

온보딩 완료 후 대시보드가 표시됩니다:

```
=== Session Info ===
Module: sync_signal
Hierarchy: u0_sync_signal
Excel: Data/Assertion_TF.xlsx

=== Module Ports ===
Clocks: i_clk (1 bit)
Resets: i_rstn (1 bit)
Inputs: i_data (8 bits), i_valid (1 bit)
Outputs: o_data (8 bits), o_valid (1 bit)

Commands: help, new, gen, show, save, load, export, quit
>
```

### Assertion 생성

```
> new
Select assertion type:
[1] counter
[2] handshake
[3] delayCondition
[4] pulseWidth
> 4

Enter signal name: i_hsw
Enter minimum pulse width (clocks): 10
Enter maximum pulse width (clocks): 20

✓ Pulse width assertion created for i_hsw (10-20 clocks)
```

### 파일 생성

```
> gen
Enter filename: my_verification
File type: [1] Interface [2] Instance [3] Both
> 3
Data source: [1] Assertions [2] Signals [3] Both
> 1

Preview: (press 'n' for next page, 'p' for previous, 'y' to confirm)
[... 미리보기 표시 ...]
Confirm generation? (y/n): y

✓ Generated: my_verification.if.sv
✓ Generated: my_verification.inst.sv
```

---

## 프로젝트 구조

```
Assertion-Checker-Generator/
├── scripts/
│   ├── cli_tui.py              # 인터랙티브 TUI (메인 인터페이스)
│   ├── assertion_builder.py    # Assertion 빌더 (인터랙티브/CLI)
│   ├── rtl_parser.py            # RTL 파서
│   ├── fill_define.py           # Excel Define 시트 채우기
│   └── assertions/              # 플러그인 디렉터리
│       ├── base.py              # 베이스 플러그인 클래스
│       ├── registry.py          # 플러그인 레지스트리
│       ├── counter.py           # Counter assertion 플러그인
│       ├── handshake.py         # Handshake assertion 플러그인
│       ├── delayCondition.py    # Delay condition assertion 플러그인
│       ├── pulseWidth.py        # Pulse width assertion 플러그인
│       ├── HACT.py              # 디스플레이 타이밍 assertion 플러그인
│       ├── HBP.py
│       ├── HSW.py
│       └── VFP.py
├── dev/                         # 개발 및 테스트 스크립트
│   ├── test_gen_functionality.py         # Gen 기능 테스트
│   ├── test_gen_updated_plugins.py       # 플러그인 호환성 테스트
│   └── ... (기타 개발 도구)
├── tests/                       # 단위 테스트
├── docs/                        # 문서
│   ├── GEN_COMMAND_FIX.md                      # Gen 명령어 수정 내역
│   ├── GEN_COMMAND_PLUGIN_COMPATIBILITY.md     # 플러그인 호환성 문서
│   └── ... (기타 문서)
├── Data/                        # Excel 템플릿 및 데이터
├── EDA/                         # 예제 RTL 파일
├── logs/                        # 로그 파일
└── README.md                    # 이 파일
```

---

## 문서

### 핵심 문서
- **[GEN_COMMAND_FIX.md](docs/GEN_COMMAND_FIX.md)**: Gen 명령어 플러그인 시스템 통합
- **[GEN_COMMAND_PLUGIN_COMPATIBILITY.md](docs/GEN_COMMAND_PLUGIN_COMPATIBILITY.md)**: 업데이트된 플러그인 호환성
- **[TUI_TEST_GUIDE.md](docs/TUI_TEST_GUIDE.md)**: TUI 수동 테스트 가이드

### 추가 문서
- `docs/`: 개발 과정 및 수정 이력 문서들
- `tests/README.md`: 테스트 가이드

---

## 팁 및 문제 해결

### 일반적인 문제

**Excel 쓰기 실패**
- 원인: Excel 파일이 열려 있음
- 해결: Excel을 닫고 다시 시도

**RTL 파싱 느림**
- 원인: 스캔 범위가 너무 넓거나 파일 인코딩 문제
- 해결: RTL 경로를 더 구체적으로 지정

**플러그인 오류**
- 원인: Excel 시트 형식 불일치
- 해결: 콘솔 경고 메시지 확인 후 시트 형식 수정

### 개발 팁

- **새 플러그인 개발 시**: 작은 샘플 Excel로 먼저 테스트
- **디버깅**: `dev/` 디렉터리의 테스트 스크립트 활용
- **세션 저장**: TUI에서 `save` 명령어로 작업 내용 저장

---

## 기여

버그 리포트, 기능 제안, Pull Request 환영합니다!

---

## 라이선스

이 프로젝트는 Harman의 내부 도구입니다.

---

## 변경 이력

### 최신 업데이트 (2025-11-12)
- ✅ TUI `gen` 명령어 플러그인 시스템 완전 통합
- ✅ 다중 플러그인 데이터 포맷 지원 (`blocks`, `sets`, 직접 dict)
- ✅ DelayCondition 플러그인 다중 세트 지원
- ✅ PulseWidth 플러그인 hpulse/vpulse 모듈 분리
- ✅ 향상된 에러 핸들링 (KeyError vs Exception 구분)
- ✅ 유연한 모듈 인스턴스 추출 regex
- ✅ 포괄적 테스트 스위트 (6/6 테스트 통과)

---


