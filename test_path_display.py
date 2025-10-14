#!/usr/bin/env python3
"""
한글 경로 표시 테스트
"""

def _sanitize_path_for_display(p: str) -> str:
    """
    Replace non-ASCII characters (e.g., Korean) with ASCII replacements for terminal display.
    This prevents display corruption in terminals that don't handle multibyte characters well.
    """
    result = []
    for char in str(p):
        # Keep ASCII characters (0-127), backslash, forward slash, colon, dot, etc.
        if ord(char) < 128:
            result.append(char)
        else:
            # Replace non-ASCII with underscore or other safe character
            result.append('_')
    return ''.join(result)


# 테스트
test_paths = [
    r"C:\Users\JunsChoi\OneDrive - HARMAN\문서\TF자료\Assertion TF\Assertion Script",
    r"C:\Users\JunsChoi\문서\프로젝트\test.xlsx",
    r"C:\Program Files\Python39\python.exe",
    "out/sessions/module-20241014_150030/module.xlsx",
]

print("=" * 80)
print("한글 경로 sanitization 테스트")
print("=" * 80)

for path in test_paths:
    print(f"\n원본 경로:")
    print(f"  {path}")
    print(f"  길이: {len(path)}")
    
    sanitized = _sanitize_path_for_display(path)
    print(f"\nSanitized 경로:")
    print(f"  {sanitized}")
    print(f"  길이: {len(sanitized)}")
    
    # 문자별 분석
    non_ascii = [c for c in path if ord(c) >= 128]
    if non_ascii:
        print(f"\n제거된 non-ASCII 문자: {len(non_ascii)}개")
        print(f"  {' '.join(non_ascii)}")

print("\n" + "=" * 80)
print("✓ 테스트 완료!")
print("=" * 80)
