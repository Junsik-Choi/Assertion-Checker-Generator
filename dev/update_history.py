import argparse
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone


class NavigationBack(Exception):
    pass


def run_command(command_args):
    try:
        completed = subprocess.run(
            command_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            text=True,
            encoding="utf-8",
        )
        return completed.stdout.strip()
    except Exception:
        return ""


def get_git_config_value(key):
    return run_command(["git", "config", key])


def get_current_branch():
    name = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"]) or ""
    return name


def get_last_commit_short_hash():
    return run_command(["git", "rev-parse", "--short", "HEAD"]) or ""


def get_last_commit_subject():
    return run_command(["git", "log", "-1", "--pretty=%s"]) or ""


def parse_github_login_from_remote_url(url):
    # Examples:
    # git@github.com:owner/repo.git
    # https://github.com/owner/repo.git
    # https://github.com/owner/repo
    if not url:
        return ""
    m = re.search(r"github\.com[:/]+([^/]+)/", url)
    if m:
        return m.group(1)
    return ""


def get_github_login():
    # Try GitHub CLI first
    if shutil.which("gh"):
        login = run_command(["gh", "api", "user", "-q", ".login"])
        if login:
            return login
    # Fallback: parse from origin URL
    origin = run_command(["git", "remote", "get-url", "origin"]) or ""
    parsed = parse_github_login_from_remote_url(origin)
    return parsed


def read_last_progress(history_path):
    if not os.path.exists(history_path):
        return None
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return None
    # Search from bottom for a progress line
    progress_pattern = re.compile(r"(?i)progress\s*:\s*(\d+)\s*%\s*->\s*(\d+)\s*%")
    for line in reversed(lines):
        m = progress_pattern.search(line)
        if m:
            try:
                prev_from = int(m.group(1))
                prev_to = int(m.group(2))
                return {"from": prev_from, "to": prev_to}
            except ValueError:
                return None
    return None


def format_timestamp():
    # Use local timezone offset
    now = datetime.now().astimezone()
    return now.strftime("%Y-%m-%d %H:%M:%S %Z%z")


def compute_progress_values(args, last_progress):
    base_from = None
    base_to = None
    if args.from_percent is not None:
        base_from = args.from_percent
    elif last_progress is not None:
        base_from = last_progress.get("to")
    else:
        base_from = 0

    if args.to_percent is not None and args.delta_percent is not None:
        raise SystemExit("--to와 --delta는 동시에 사용할 수 없습니다.")

    if args.to_percent is not None:
        base_to = args.to_percent
    elif args.delta_percent is not None:
        base_to = base_from + args.delta_percent
    else:
        # This branch will be handled by interactive flow in main()
        raise NavigationBack()

    # Clamp to [0, 100]
    base_from = max(0, min(100, base_from))
    base_to = max(0, min(100, base_to))
    return base_from, base_to


def build_entry_text(
    timestamp,
    user_name,
    user_email,
    github_login,
    branch,
    commit_hash,
    commit_subject,
    from_percent,
    to_percent,
    summary,
    issue,
):
    delta = to_percent - from_percent
    lines = []
    lines.append("----------------------------------------\n")
    lines.append(f"[{timestamp}]\n")
    id_line = f"User: {user_name} <{user_email}>"
    if github_login:
        id_line += f" (GitHub: {github_login})"
    lines.append(id_line + "\n")
    branch_line = "Branch: " + (branch or "")
    if commit_hash:
        branch_line += f" @ {commit_hash}"
    if commit_subject:
        branch_line += f" - {commit_subject}"
    lines.append(branch_line + "\n")
    lines.append(
        f"Progress: {from_percent}% -> {to_percent}% ({'+' if delta >= 0 else ''}{delta}%)\n"
    )
    if issue:
        lines.append(f"Issue: {issue}\n")
    if summary:
        lines.append("Summary:\n")
        # Preserve original line breaks
        lines.append(summary.strip() + "\n")
    lines.append("\n")
    return "".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="History.txt를 업데이트하여 작업 내용과 진행률을 기록합니다.",
    )
    parser.add_argument(
        "--summary",
        "-s",
        type=str,
        help="무엇을 했는지 요약 (미지정 시 인터랙티브 입력)",
    )
    parser.add_argument(
        "--issue",
        "-i",
        type=str,
        help="관련 이슈 ID 또는 링크 (선택)",
    )
    parser.add_argument(
        "--from",
        dest="from_percent",
        type=int,
        help="이전 진행률 % (미지정 시 파일에서 자동 추정, 없으면 0)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--to",
        dest="to_percent",
        type=int,
        help="최종 진행률 %",
    )
    group.add_argument(
        "--delta",
        dest="delta_percent",
        type=int,
        help="증가한 진행률 %",
    )
    args = parser.parse_args()

    repo_root = os.path.dirname(os.path.abspath(__file__))
    history_path = os.path.join(repo_root, "History.txt")

    # Git / GitHub identity
    user_name = get_git_config_value("user.name") or ""
    user_email = get_git_config_value("user.email") or ""
    github_login = get_github_login()
    branch = get_current_branch()
    commit_hash = get_last_commit_short_hash()
    commit_subject = get_last_commit_subject()

    # Last progress
    last_progress = read_last_progress(history_path)

    # Interactive flow with back navigation when needed
    summary = args.summary
    issue = args.issue

    step = 1  # 1: summary, 2: issue, 3: progress
    while True:
        # Step 1: Summary (multiline; preserve newlines)
        if step == 1 and not summary:
            print("무엇을 했는지 간단히 요약하세요. 여러 줄 입력 가능. 빈 줄로 종료.")
            print("예) 테스트 커버리지 향상, 버그 수정 등")
            collected = []
            while True:
                line = input()
                if line == "":
                    break
                collected.append(line)
            summary = "\n".join(collected).strip()
            step = 2

        # Step 2: Issue (single line)
        if step == 2 and issue is None:
            typed = input("관련 이슈 ID/링크가 있으면 입력 (없으면 엔터, 뒤로: b): ").strip()
            if typed.lower() in {"b", "back"}:
                # Go back to summary re-entry
                summary = None
                step = 1
                continue
            issue = typed
            step = 3

        # Step 3: Progress
        if step == 3:
            try:
                from_percent, to_percent = compute_progress_values(args, last_progress)
            except NavigationBack:
                # Run interactive progress prompt with back support
                base_from = (
                    args.from_percent
                    if args.from_percent is not None
                    else (last_progress.get("to") if last_progress else 0)
                )
                print("진행률 입력 모드 (엔터로 기본값 수락, 뒤로가기: b)")
                print(f"이전 진행률(자동 감지됨): {base_from}%")
                while True:
                    choice = input(
                        "증가분 % 또는 최종 %를 입력하세요 (예: 10 또는 50): "
                    ).strip().lower()
                    if choice in {"b", "back"}:
                        # Go back to issue
                        issue = None
                        step = 2
                        break
                    if choice == "":
                        base_to = base_from
                        from_percent, to_percent = base_from, base_to
                        break
                    try:
                        value = int(choice)
                    except ValueError:
                        print("숫자를 입력해야 합니다. 다시 시도하세요.")
                        continue
                    mode = input(
                        "입력값이 증가분이면 D, 최종 퍼센트면 T 입력 (뒤로: B) [D/T/B]: "
                    ).strip().lower()
                    if mode in {"b", "back"}:
                        # Go back to issue
                        issue = None
                        step = 2
                        break
                    if mode == "t":
                        base_to = value
                    else:
                        base_to = base_from + value
                    # Clamp to [0, 100]
                    base_from = max(0, min(100, base_from))
                    base_to = max(0, min(100, base_to))
                    from_percent, to_percent = base_from, base_to
                    break

            # If we changed step, continue loop
            if step != 3:
                continue

            # Progress resolved; exit loop
            break

    timestamp = format_timestamp()
    entry_text = build_entry_text(
        timestamp,
        user_name,
        user_email,
        github_login,
        branch,
        commit_hash,
        commit_subject,
        from_percent,
        to_percent,
        summary,
        issue,
    )

    # Ensure History.txt exists; if new, keep existing header if any isn't present
    file_exists = os.path.exists(history_path)
    if not file_exists:
        with open(history_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("===============================\n")
            f.write("Assertion TF History\n\n")
            f.write("===============================\n\n")

    with open(history_path, "a", encoding="utf-8", newline="\n") as f:
        f.write(entry_text)

    print("History.txt에 항목이 추가되었습니다.")


if __name__ == "__main__":
    main()


