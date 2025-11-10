# Excel Writing Fix - Summary

## 문제 분석 (Problem Analysis)

### 발견된 문제들 (Issues Found)
1. **대소문자 불일치**: Excel 시트 이름이 `handshake`, `pulseWidth` (소문자)인데, 코드는 `Handshake`, `PulseWidth` (대문자 혼합)를 찾고 있었음
2. **샘플 데이터**: 각 시트에 샘플 데이터가 7~8번째 행부터 존재하여 새 데이터 작성에 방해
3. **병합 셀 문제**: Excel 시트에 병합된 셀이 있어 직접 삭제 시도 시 에러 발생
4. **열 매핑 오류**: 각 시트의 실제 열 구조와 코드의 열 매핑이 일치하지 않음
5. **중복 삭제 문제**: 매번 쓸 때마다 샘플 데이터를 삭제하여 이전에 작성한 assertion도 함께 삭제됨

### 시트 구조 분석 (Sheet Structure)

#### Counter Sheet
- 헤더 행: Row 7
- 데이터 시작: Row 8
- 열 구조: (Col B) Target | (Col C) Plus Condition | (Col D) Reset Condition | (Col E) Trigger Condition | (Col F) Expect Count Value

#### handshake Sheet (소문자)
- 헤더 행: Row 6
- 데이터 시작: Row 7
- 열 구조: (Col C) Type | (Col D) Sender | (Col E) Receiver

#### pulseWidth Sheet (소문자)
- 헤더 행: Row 6
- 데이터 시작: Row 7
- 열 구조: (Col C) Type | (Col D) Count_Trigger | (Col E) Target_Pulse | (Col F) Expected_Min_Value | (Col G) Expected_Max_Value

## 해결 방법 (Solution)

### 1. 대소문자 무시 시트 검색
```python
def find_sheet_ci(target_name: str) -> Optional[str]:
    """Find sheet by name (case-insensitive). Returns actual sheet name or None."""
    target_lower = target_name.lower()
    for name in wb.sheetnames:
        if name.lower() == target_lower:
            return name
    return None
```

### 2. 스마트한 샘플 데이터 삭제
샘플 데이터인지 판별하여 **첫 번째 쓰기 시에만** 삭제:
```python
# Check if this is sample data
first_target = ws.cell(row=8, column=target_col).value
is_sample_data = (first_target and str(first_target).strip() in ['cnt', 'counter', 'sample'])

if is_sample_data:
    # Clear only on first write
    from openpyxl.cell import MergedCell
    for row in range(8, ws.max_row + 1):
        for col in range(1, 15):
            cell = ws.cell(row=row, column=col)
            if not isinstance(cell, MergedCell):
                cell.value = None
else:
    # Find next empty row (append mode)
    while ws.cell(row=next_row, column=target_col).value:
        next_row += 1
```

### 3. 정확한 열 매핑

#### Counter Sheet
- Row 8부터 데이터 작성
- Column 2 (B): Target
- Column 3 (C): Plus Condition
- Column 4 (D): Reset Condition
- Column 5 (E): Trigger Condition
- Column 6 (F): Expected Count Value

#### Handshake Sheet
- Row 7부터 데이터 작성
- Column 3 (C): Phase Type
- Column 4 (D): Sender
- Column 5 (E): Receiver

#### PulseWidth Sheet
- Row 7부터 데이터 작성
- Column 3 (C): Type (hpulse/vpulse)
- Column 4 (D): Count Trigger
- Column 5 (E): Target Pulse
- Column 6 (F): Min Value
- Column 7 (G): Max Value

## 수정된 파일 (Modified Files)

### `scripts/cli_tui.py`
- `_write_assertion_to_excel()` 함수 수정
  - 대소문자 무시 시트 검색 추가
  - 병합 셀 안전 처리
  - 정확한 행/열 위치 지정
  - 샘플 데이터 자동 삭제

## 검증 (Verification)

### 테스트 스크립트
- `dev/check_excel_sheets.py`: Excel 시트 구조 확인
- `dev/check_counter_detail.py`: 상세 시트 내용 확인
- `dev/test_excel_writing.py`: Excel 쓰기 기능 테스트
- `dev/final_verification.py`: 최종 검증

### 테스트 결과
```
✅ Counter sheet has data
✅ Handshake sheet has data  
✅ PulseWidth sheet has data
```

## 사용 방법 (Usage)

### TUI에서 assertion 생성
```bash
python scripts/cli_tui.py
```

1. 기존 세션 로드 또는 새 세션 생성
2. `new` 명령어로 assertion 생성 시작
3. assertion 타입 선택 (counter/handshake/pulseWidth)
4. 필요한 정보 입력
5. 생성 완료 시 자동으로 Excel 파일에 저장됨

### 결과 확인
```bash
python dev/final_verification.py
```

## 검증 결과 (Test Results)

### 포괄적 테스트 통과 ✅
- **Counter 시트**: 3개 assertion 작성 및 검증 성공
- **Handshake 시트**: 3개 assertion 작성 및 검증 성공  
- **PulseWidth 시트**: 3개 assertion 작성 및 검증 성공

### 테스트 스크립트
```bash
# 모든 기능 테스트
python dev/final_comprehensive_test.py

# 개별 테스트
python dev/test_fresh_excel.py       # 샘플 데이터 삭제 및 추가 테스트
python dev/test_handshake.py         # Handshake 전용 테스트
python dev/integration_test.py       # 통합 테스트
```

## 주요 개선 사항 (Key Improvements)

1. ✅ **대소문자 무관 시트 검색**: 시트 이름의 대소문자와 관계없이 올바른 시트 찾기
2. ✅ **스마트 샘플 데이터 삭제**: 샘플 데이터 감지 후 첫 번째 쓰기 시에만 삭제
3. ✅ **추가 모드 (Append)**: 이후 assertion은 기존 데이터 유지하며 추가
4. ✅ **병합 셀 안전 처리**: 병합된 셀 건너뛰고 일반 셀만 수정
5. ✅ **정확한 열 매핑**: 각 시트의 실제 구조에 맞는 정확한 열 위치 사용
6. ✅ **구문 경고 수정**: ASCII 아트의 이스케이프 시퀀스 경고 해결

## 다음 단계 (Next Steps)

assertion을 만들고 Excel에 저장되는 것을 확인하려면:

1. TUI 실행: `python scripts/cli_tui.py`
2. 세션 선택 또는 새로 생성
3. `new` 명령으로 assertion 생성
4. Excel 파일 확인: `out/sessions/<session-name>/<module>.xlsx`

각 assertion 타입별로 정확한 시트에 데이터가 기록되는 것을 확인할 수 있습니다.
