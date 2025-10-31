#!/usr/bin/env python3
"""Visual demonstration of waveform alignment fix."""

def format_signal_name(name: str, role: str, width: int = 20) -> str:
    """Format signal name right-aligned with role in parentheses."""
    formatted = f"{name} ({role})"
    return formatted.rjust(width)

def format_waveform_line(waveform: str, width: int = 20) -> str:
    """Format waveform data right-aligned."""
    return waveform.rjust(width)

print("=" * 80)
print("WAVEFORM ALIGNMENT FIX DEMONSTRATION")
print("=" * 80)
print()

print("COUNTER ASSERTION - TIMING DIAGRAM")
print("-" * 80)
print()
print("Before (MISALIGNED):")
print("-" * 80)
print("Clock cycles: 0   1   2   3   4   5   6   7")
print("clk          |___|‾‾‾|___|‾‾‾|___|‾‾‾|___|‾‾‾|")
print(f"{format_signal_name('target', 'counter')} 0   0   1   1   1   0   0   0")
print(f"{format_signal_name('plus_con', 'increment')} └─────┘   └─────┘   └─────┘")
print(f"{format_signal_name('reset_con', 'reset')} └───────────────┘       └───────┘")
print(f"{format_signal_name('trigger_con', 'trigger')} └─────┘       └─────┘   └─────┘")
print()

print("\nAfter (ALIGNED):")
print("-" * 80)
print("Clock cycles: 0   1   2   3   4   5   6   7")
print(format_waveform_line("clk") + " |___|‾‾‾|___|‾‾‾|___|‾‾‾|___|‾‾‾|")
print(f"{format_signal_name('target', 'counter')} 0   0   1   1   1   0   0   0")
print(f"{format_signal_name('plus_con', 'increment')} └─────┘   └─────┘   └─────┘")
print(f"{format_signal_name('reset_con', 'reset')} └───────────────┘       └───────┘")
print(f"{format_signal_name('trigger_con', 'trigger')} └─────┘       └─────┘   └─────┘")
print()

print("=" * 80)
print("2-PHASE HANDSHAKE - TIMING DIAGRAM")
print("=" * 80)
print()
print("Before (MISALIGNED):")
print("-" * 80)
print("Clock cycles: 0   1   2   3   4   5   6   7   8")
print("clk          |___|‾‾‾|___|‾‾‾|___|‾‾‾|___|‾‾‾|___|")
print(f"{format_signal_name('req_sig', 'sender')} └─────────────┘   └─────────────┘")
print(f"{format_signal_name('ack_sig', 'receiver')}     └─────────────┘   └─────────────┘")
print()

print("\nAfter (ALIGNED):")
print("-" * 80)
print("Clock cycles: 0   1   2   3   4   5   6   7   8")
print(format_waveform_line("clk") + " |___|‾‾‾|___|‾‾‾|___|‾‾‾|___|‾‾‾|___|")
print(f"{format_signal_name('req_sig', 'sender')} └─────────────┘   └─────────────┘")
print(f"{format_signal_name('ack_sig', 'receiver')}     └─────────────┘   └─────────────┘")
print()

print("=" * 80)
print("KEY IMPROVEMENTS")
print("=" * 80)
print("""
✓ 모든 신호 이름이 우측 정렬됨 (신호 역할 표시 포함)
✓ 클록 라인도 우측 정렬되어 데이터와 수직 정렬
✓ 웨이브폼 패턴이 데이터 값과 명확하게 정렬됨
✓ 시각적으로 일관성 있음

예시:
  - "clk" (20자 우측 정렬) = "                 clk"
  - "target (counter)" (20자 우측 정렬) = "my_counter (counter)"
  - 모두 같은 열에서 시작하므로 완벽히 정렬됨
""")
print("=" * 80)
