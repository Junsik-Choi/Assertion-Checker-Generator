"""
Show what's in the sessions folder in a clear format
"""
from pathlib import Path

sessions_dir = Path("out/sessions")

print("=" * 80)
print("SESSION FOLDERS AND FILES")
print("=" * 80)

if not sessions_dir.exists():
    print("❌ Sessions directory does not exist!")
    exit(1)

items = sorted(sessions_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)

print(f"\nTotal items in {sessions_dir}: {len(items)}\n")

folders = []
files = []

for item in items:
    if item.is_dir():
        folders.append(item)
    else:
        files.append(item)

if folders:
    print(f"📁 SESSION FOLDERS ({len(folders)}):")
    print("-" * 80)
    for folder in folders:
        print(f"\n  📂 {folder.name}/")
        sub_items = sorted(folder.iterdir())
        for sub in sub_items:
            size = sub.stat().st_size if sub.is_file() else 0
            size_str = f"{size:,} bytes" if size > 0 else ""
            icon = "📄" if sub.is_file() else "📁"
            print(f"     {icon} {sub.name:50s} {size_str}")
else:
    print("📁 SESSION FOLDERS: None")

if files:
    print(f"\n\n📄 SESSION SNAPSHOTS ({len(files)}) - These are app state files, NOT session folders:")
    print("-" * 80)
    for file in files:
        size = file.stat().st_size
        print(f"  📄 {file.name:50s} {size:,} bytes")
else:
    print("\n\n📄 SESSION SNAPSHOTS: None")

print("\n" + "=" * 80)
print("✅ Session folders contain your working Excel files and data")
print("ℹ️  Session snapshots (JSON) are just app state saves")
print("=" * 80)
