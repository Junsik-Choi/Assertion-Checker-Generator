# Assertion-Checker-Generator
[Harman] Assertion Checker Generator

RTL Auto Parsing & Excel Editing
-------------------------

<img width="1118" height="326" alt="Image" src="https://github.com/user-attachments/assets/ea501a9a-45a3-43d9-93bc-8caf7922bd50" />
<br>
<div align=center>
RTL Auto Parsing 실행 예시
</div>

<br><br>
검증 대상이 될 RTL을 물리면 상위 폴더로 올라가면서 .v파일들을 탐색하고 계층 분석을 통해 검증될 Target Block의 Instanse 정보를 JSON으로 저장한다.
저장되는 정보는
**Top path, module, instance name, clock, reset, input, output, inout, parameter**가 있다.
<br>
  
**TOP Path :** Parsing 이외에 사용자가 입력해 주는 Path이다. 
예를들어 SVA검증 대상 경로가 top.dut.WRAPPER_BLK_ABC.blk_abc.u_module_a.u_sub_module_b 라고 했을 때, parsing의 결과가 blk_abc.u_module_a.u_sub_module_b인 경우 TOP Path입력을top.dut.WRAPPER_BLK_ABC.blk_abc.u_module_a와 같이 입력한다면, top.dut.WRAPPER_BLK_ABC.blk_abc.u_module_a는 `TOP_PATH 로 local define되고 Checker Interface 내부에는 `TOP_PATH.u_sub_module_b나 `TOP_PATH.u_sub_module_b.i_clk 와 같이 짧은 경로가 사용되어 가독성을 향상 시킬 수 있다.
<br><br>
**module :** 검증 대상이 된 instance의 module name 원형이다.

**paths :** 검증 대상이 된 instance의 TOP_PATH 부분을 제외한 RTL Path이다. 만약 한 module안에 검증해야할 같은 구조의 module들이 있다면 한꺼번에 SVA Checker생성이 가능하도록 여러 path를 list로 받아 저장할 수 있도록 하였다. 여러개의 instance를 받은 경우 같은 내부 포트 정보를 공유하므로 path 정보만 교체하면서 각각의 input에 대해 같은 목적의 Checker를 활용하여 검증이 가능하도록 구현 할 예정이다.

**instances :** 검증 대상이 된 instance들의 이름들을 list형식으로 나타낸다.

**clocks :** i_clk, i_sclk, i_aclk, i_CLK, I_CLK, i_clock... 등 여러가지 일반적인 clock naming rule을 따라 clock이라 예상되는 input을 받아 저장한다.

**resets :** i_rst, i_rstn, i_reset, I_RST, i_GRESETn... 등 여러가지 일반적인 reset naming rule을 따라 reset이라 예상되는 input을 받아 저장한다.

**input :** clock과 reset, parameter를 제외한 input들의 이름과 width 정보를 저장한다.

**output :** output port들의 이름과 width 정보를 저장한다.

**inout :** inout port들의 이름과 width 정보를 저장한다.

**parameter :** p_* 인 parameter나 SFR, Register setting 등의 input port를 저장한다.

+ `BIT_WIDTH 와 같은 local param이나 define되어있는 정보는 마찬가지로 목표 instance 내부와 외부에서 탐색하여 현재 설정된 값으로 대체하여 활용한다.
+ 또한, excel로 가져올 때는 bit가 총 몇 비트인지가 중요하기 때문에 [15:0] 같은 값은 16 bits 라고 간소화 하여 불러온다.

<div align=center>
<br><br> 
<center> <img width="485" height="636" alt="Image" src="https://github.com/user-attachments/assets/f456ae8c-8279-4ce7-9314-1a4b70e52475" /> </center>
<br>
출력된 JSON파일
<br> <br>
<img width="447" height="444" alt="Image" src="https://github.com/user-attachments/assets/6d71d4a5-e82d-4200-a6c1-98174c18a8ce" />
<br>엑셀 출력 log
<br> <br>
<img width="1447" height="515" alt="Image" src="https://github.com/user-attachments/assets/7d286dc7-58b5-451a-8483-86d5abdc341c" />
<br>
최종 결과물
<br><br>
</div>

모듈형 Assertion Builder (scripts/assertion_builder.py)
-----------------------------------------------
본 도구는 RTL을 자동으로 분석하여 모듈의 포트/클럭/리셋/파라미터 정보를 수집하고, Excel 시트의 내용을 바탕으로 Assertion Checker(SV)를 자동 생성한다. 각 시트 타입은 플러그인으로 분리되어 있으며, 새로운 시트가 추가되더라도 해당 시트에 대응하는 플러그인만 추가하면 쉽게 확장할 수 있도록 구성하였다.

구성 요약
본 기능은 `scripts/rtl_parser.py`로 .v/.sv 파일을 분석하고, `scripts/fill_define.py`와 JSON 연동으로 Excel의 Define 시트를 자동으로 채우며, `scripts/assertions/*` 하위 플러그인을 통해 시트별 SV 생성 로직을 수행한다.

<div align=center>
<img width="1100" height="320" alt="Image" src="https://github.com/user-attachments/assets/TODO_interactive_01" />
<br>
모듈형 Assertion Builder 개요(추가 예정)
</div>

주요 파일
- `scripts/assertion_builder.py` : 통합 오케스트레이터(인터랙티브/CLI)
- `scripts/assertions/base.py` : 플러그인 베이스 인터페이스
- `scripts/assertions/registry.py` : 플러그인 등록/조회
- `scripts/assertions/counter.py` : `counter_gen` 시트 플러그인 예시

---

인터랙티브 모드 (무옵션 실행)
-------------------------
아무 옵션 없이 실행하면 사용자 친화적인 마법사가 실행된다. 한 번에 여러 모드를 함께 선택하여 수행할 수 있다(예: Define 채움 + JSON 출력 + SV 생성).

```
python scripts/assertion_builder.py
```

마법사 흐름
1) RTL 시작 경로 선택: 기본 후보(예: `EDA/RTL`)를 먼저 제시하며, 필요 시 직접 입력할 수 있다.
2) 타깃 모듈 선택: 파싱된 모듈 목록에서 번호로 선택한다(Top 후보는 상단에 배치된다).
3) Excel 파일 선택: `Data/` 폴더 내 `.xlsx`를 자동 탐색하여 리스트를 보여주고, 번호 선택 또는 직접 입력할 수 있다.
4) 출력 폴더 지정: 기본값은 `out/assertions`이며 자유롭게 변경할 수 있다.
5) 모드 선택(복수 선택 가능): Define 시트 채우기 / 입력 JSON 출력 / SV 생성 중 원하는 조합을 선택한다.
6) 플러그인 선택(복수 선택 또는 All): 예) `counter`(기본 제공). 플러그인 추가 시 목록에 자동 반영된다.

<div align=center>
<img width="1100" height="320" alt="Image" src="https://github.com/user-attachments/assets/TODO_interactive_02" />
<br>
인터랙티브 마법사 예시 화면(추가 예정)
</div>

실행 결과
- 선택한 모드에 따라 Define 시트가 업데이트되고, 입력 JSON과 SV 파일이 출력됩니다.
- 오류/경고 메시지는 콘솔에 표시되며, 필요한 경우 조치 안내를 제공합니다.

---

CLI 모드(비대화형)
-----------------
기존 방식도 그대로 지원한다. 자동화 스크립트/CI 환경에서 사용하기에 적합하다.

```
python scripts/assertion_builder.py \
  --rtl-start EDA/RTL \
  --target-module blur_scaler \
  --excel Data/Assertion_TF.xlsx \
  --auto-define-fill \
  --json \
  --out out/assertions
```

옵션 요약
- `--rtl-start <path>` : RTL 시작 경로(파일/디렉터리)
- `--target-module <name>` : 대상 모듈명(미지정 시 자동 추정)
- `--excel <path>` : 참조 Excel 경로
- `--use-default-excel` : `Data/Assertion_TF.xlsx` 강제 사용
- `--auto-define-fill` : Define 시트 자동 채움 실행
- `--enable <name>` : 사용할 플러그인만 선택(복수 지정 가능)
- `--json` : 포트/시트 파싱 결과를 통합 JSON으로 출력
- `--out <dir>` : 결과 출력 디렉터리(기본: `out/assertions`)

---

Define 시트 자동 채움 흐름
---------------------
1) 모듈의 `clocks/resets/inputs/outputs/inouts/parameters` 정보를 취합한다.
2) 이를 `module_define.json`으로 저장한다.
3) `scripts/fill_define.py`를 호출하여 지정 Excel의 Define 시트를 자동으로 채운다.

<div align=center>
<img width="1100" height="320" alt="Image" src="https://github.com/user-attachments/assets/TODO_define_log" />
<br>
Define 채움 로그 화면(추가 예정)
<br><br>
<img width="1100" height="320" alt="Image" src="https://github.com/user-attachments/assets/TODO_define_excel_result" />
<br>
Excel Define 시트 결과(추가 예정)
</div>

수동 실행 예시(필요 시)
```
python scripts/fill_define.py Data/Assertion_TF.xlsx out/assertions/module_define.json
```

---

플러그인 아키텍처로 시트별 확장
-------------------------
위치 및 구조
- 플러그인 위치: `scripts/assertions/`
- 베이스 클래스: `BaseAssertionPlugin`
  - `plugin_name` : 플러그인 이름(e.g., `counter`)
  - `sheet_name` : Excel 시트 이름(e.g., `counter_gen`)
  - `parse(xls_path) -> dict` : 시트를 구조화하여 반환한다.
  - `generate_sv(parsed, context) -> List[str]` : SV 섹션 문자열 목록을 생성한다.
- 등록: 새 파일의 플러그인 클래스 정의 위에 `@register` 데코레이터를 추가하면 자동 등록된다.

확장 작업 예시(프롬프트 가이드)
- “시트 `my_new_gen`의 헤더 A,B,C를 사용하여 property 패턴 P를 생성하는 플러그인을 추가해줘.”
- 기대 동작: `scripts/assertions/my_new.py`에 `BaseAssertionPlugin`을 상속한 클래스를 만들고 `sheet_name`을 `my_new_gen`으로 설정한 뒤, `parse`/`generate_sv`를 구현한다. 이후 빌더가 자동으로 인식한다.

<div align=center>
<img width="1100" height="320" alt="Image" src="https://github.com/user-attachments/assets/TODO_plugin_layout" />
<br>
플러그인 폴더 구조(추가 예정)
</div>

---

카운터 시트 플러그인(`counter_gen`) 상세
------------------------------
참조: `scripts/assertions/counter.py`

시트 구성(예시)
- 좌측 테이블(기본 정보): [Name] [Edge Types] [Base Clock] [Reset Edge] [Reset Signal]
- 우측 테이블(조건/동작): [Name] [Step(If/Else If/Else)] [Condition] [Action]

헤더 매핑(요약)
| Excel Header | 사용처 |
| --- | --- |
| Name | 카운터 블록 이름 및 오른쪽 테이블 그룹핑 키 |
| Edge Types, Base Clock | `always @(posedge/negedge clk)` 감지 리스트 구성 |
| Reset Edge, Reset Signal | `or negedge rst` 등 비동기 감지 구성 |
| Step | if/else if/else 단계 구분 |
| Condition | if/else if 조건식 |
| Action | 해당 블록 내부 수행 문장 |

생성 결과
- 각 Name에 대해 `always @(...) begin ... end` 블록을 생성하여 SV 섹션을 만든다.
- 기존 `scripts/assertion_gen.py`의 카운터 생성 로직을 반영하여 호환성을 유지하였다.

<div align=center>
<img width="1100" height="320" alt="Image" src="https://github.com/user-attachments/assets/TODO_counter_sheet" />
<br>
Counter 시트 예시(추가 예정)
<br><br>
<img width="1100" height="320" alt="Image" src="https://github.com/user-attachments/assets/TODO_counter_sv" />
<br>
생성된 SV 섹션 예시(추가 예정)
</div>

---

### 출력물
- SV: `out/assertions/auto_assertion_checker.sv`
- 통합 입력 JSON: `out/assertions/assertion_inputs.json`(옵션 `--json` 사용 시)
- Define용 JSON: `out/assertions/module_define.json`(Define 채움 선택 시)

---

### 팁 및 문제 해결
- Excel 파일이 열려 있으면 쓰기 실패할 수 있습니다. Excel을 닫고 다시 시도하세요.
- RTL 스캔 범위가 너무 넓거나 파일 인코딩이 특이한 경우 시간이 걸릴 수 있습니다.
- 새로운 시트를 도입할 때는 작은 샘플로 먼저 플러그인을 개발/검증 후에 실제 TF에 적용하세요.