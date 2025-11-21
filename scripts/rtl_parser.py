# rtl_group_mode.py
# Pure-Python Verilog(.v) hierarchy analyzer & batch grouping JSON generator
# - No PyVerilog/iverilog dependency
# - Ascend to 'RTL' folder (case-insensitive) from a given path, collect .v files
# - Parse modules/ports/instances (Verilog-2005 지향, best-effort)
# - Find all instantiations of a target module; let user group them (all/ranges/indices)
# - Save per-group JSON with shared ports + selected Paths/Instances only
# - Console prints: formal Korean; logs: English

import sys
import logging
from pathlib import Path
import re
import json
from typing import List, Dict, Any, Optional, Tuple, Set

LOG = logging.getLogger("rtl_group_mode")

# ============================================================
# 분류 패턴 후보(수정·추가 가능, 대소문자 무시)
# ============================================================
CLOCK_PATTERNS = [
    r"^(i_)?clk$", r"^(i_)?sclk$", r"^(i_)?clock(\b|_)", r"^clk(_\w+)?$",
]
RESET_PATTERNS = [
    r"^(i_)?rst(n)?$", r"^(i_)?reset(n)?$", r"^.*_rst(n)?$",
]
PARAM_PATTERNS = [
    r"^p_[A-Za-z0-9_]+$", r"^P_[A-Za-z0-9_]+$",
]

GLOBAL_DEFINES = {}

def is_match_any(name: str, patterns: List[str]) -> bool:
    for p in patterns:
        if re.search(p, name, flags=re.IGNORECASE):
            return True
    return False

def classify_name(name: str) -> str:
    if is_match_any(name, CLOCK_PATTERNS):
        return "clock"
    if is_match_any(name, RESET_PATTERNS):
        return "reset"
    if is_match_any(name, PARAM_PATTERNS):
        return "parameter"
    return "other"

# -----------------------------
# File discovery and RTL root
# -----------------------------
def discover_files(root: Path, exts: List[str]) -> List[Path]:
    extset = set(e if e.startswith(".") else f".{e}" for e in exts)
    files = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in extset:
            files.append(p)
    return files

def find_rtl_root_from(start: Path) -> Tuple[Path, bool]:
    # 변경: 더 이상 상향 탐색을 하지 않습니다.
    # 사용자가 제공한 경로(start)가 디렉터리이면 그 디렉터리 자체를, 파일이면 그 파일의 부모 디렉터리를
    # RTL 루트로 간주합니다. 상위 디렉터리로 올라가서 'RTL' 폴더를 찾지 않습니다.
    cur = start if start.is_dir() else start.parent
    return cur.resolve(), True

# -----------------------------
# Preprocess: strip comments & attributes
# -----------------------------
_re_line_comment = re.compile(r"//.*?$", re.MULTILINE)
_re_block_comment = re.compile(r"/\*.*?\*/", re.DOTALL)
_re_attr = re.compile(r"\(\*.*?\*\)", re.DOTALL)

def preprocess(text: str) -> str:
    text = _re_block_comment.sub("", text)
    text = _re_line_comment.sub("", text)
    text = _re_attr.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text

# -----------------------------
# Helpers
# -----------------------------
def skip_spaces(text: str, i: int) -> int:
    n = len(text)
    while i < n and text[i].isspace():
        i += 1
    return i

def extract_balanced(text: str, start: int, open_ch: str, close_ch: str) -> Tuple[str, int]:
    assert text[start] == open_ch
    depth = 0
    i = start
    n = len(text)
    buf = []
    while i < n:
        ch = text[i]
        if ch == open_ch:
            depth += 1
            if depth > 1:
                buf.append(ch)
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return ("".join(buf), i + 1)
            else:
                buf.append(ch)
        else:
            buf.append(ch)
        i += 1
    raise ValueError("Unbalanced parentheses while parsing")

# -----------------------------
# Module/Port/Instance parsing
# -----------------------------
_module_decl_re = re.compile(r"\bmodule\s+([A-Za-z_]\w*)", re.MULTILINE)
_endmodule_re = re.compile(r"\bendmodule\b", re.MULTILINE)
_dir_kw = ("input", "output", "inout")
_ws_collapse = re.compile(r"\s+")

def collapse_ws(s: str) -> str:
    return _ws_collapse.sub(" ", s).strip()

def parse_widths(part: str) -> str:
    # [A-1:0][B-1:0] 형태 연속 폭도 인식
    widths = re.findall(r"\[[^\]]+\]", part)
    return "".join(widths) if widths else ""

def _split_dot_path(s: str) -> List[str]:
    return [seg for seg in s.split(".") if seg]

def trim_path_by_top(full_path: str, top_path: str) -> str:
    if not top_path:
        return full_path
    fp, tp = _split_dot_path(full_path), _split_dot_path(top_path)
    if len(tp) > len(fp): return full_path
    for i in range(len(tp)):
        if fp[i] != tp[i]:
            return full_path
    return ".".join(fp[len(tp):])

def split_top_level_commas(s: str) -> List[str]:
    out, buf = [], []
    depth = {"()": 0, "[]": 0, "{}": 0}
    for ch in s:
        if ch == "(":
            depth["()"] += 1
        elif ch == ")":
            depth["()"] -= 1
        elif ch == "[":
            depth["[]"] += 1
        elif ch == "]":
            depth["[]"] -= 1
        elif ch == "{":
            depth["{}"] += 1
        elif ch == "}":
            depth["{}"] -= 1
        if ch == "," and all(v == 0 for v in depth.values()):
            out.append("".join(buf)); buf = []
        else:
            buf.append(ch)
    if buf: out.append("".join(buf))
    return out

def extract_modules_from_text(text: str) -> List[Dict[str, Any]]:
    mods = []
    pos = 0
    n = len(text)
    while True:
        m = _module_decl_re.search(text, pos)
        if not m:
            break
        name = m.group(1)
        i = m.end()
        i = skip_spaces(text, i)

        # Optional parameter port list: # ( ... )
        param_ports = ""
        if i < n and text[i] == "#":
            i += 1
            i = skip_spaces(text, i)
            if i < n and text[i] == "(":
                try:
                    content, j = extract_balanced(text, i, "(", ")")
                    param_ports = content
                    i = j
                    i = skip_spaces(text, i)
                except ValueError:
                    # Unbalanced parentheses in parameter list: warn and skip param_ports
                    LOG.warning("Unbalanced parentheses while parsing parameter list for module %s; skipping parameter block", name)
                    # try to recover by moving forward to the next semicolon or opening paren
                    # advance one char to avoid infinite loop
                    i = i + 1

        # Mandatory port list: ( ... )
        ports_header = ""
        if i < n and text[i] == "(":
            try:
                ports_header, j = extract_balanced(text, i, "(", ")")
                i = j
                i = skip_spaces(text, i)
                if i < n and text[i] == ";":
                    i += 1
                else:
                    LOG.warning("Expected ';' after module port list: %s", name)
            except ValueError:
                # Unbalanced parentheses in port list: warn and attempt to locate endmodule
                LOG.warning("Unbalanced parentheses while parsing port list for module %s; attempting to skip module body", name)
                # Try to find corresponding 'endmodule' to skip this module
                endm = _endmodule_re.search(text, i)
                if not endm:
                    LOG.warning("endmodule not found after malformed port list for module: %s", name)
                    body = text[i:]
                    pos = n
                else:
                    body = text[i:endm.start()]
                    pos = endm.end()
                mods.append({"name": name, "param_ports": param_ports, "ports_header": ports_header, "body": body})
                # continue outer loop from updated pos
                continue
        else:
            # No port list - treat as module with no ports
            # This is valid in SystemVerilog (e.g., testbench modules)
            if i < n and text[i] == ";":
                i += 1
            else:
                LOG.warning("Expected ';' after module name (no port list): %s", name)

        endm = _endmodule_re.search(text, i)
        if not endm:
            LOG.warning("endmodule not found for module: %s", name)
            body = text[i:]
            pos = n
        else:
            body = text[i:endm.start()]
            pos = endm.end()

        mods.append({"name": name, "param_ports": param_ports, "ports_header": ports_header, "body": body})
    return mods

def parse_ports_header(ports_header: str) -> List[Dict[str, str]]:
    entries = split_top_level_commas(ports_header)
    ports = []
    for e in entries:
        e = collapse_ws(e)
        if not e or e == "...":
            continue
        dir_ = "unknown"
        width = ""
        name = None
        for dk in _dir_kw:
            if re.search(rf"\b{dk}\b", e):
                dir_ = dk
                break
        w = parse_widths(e)
        if w: width = w
        ids = re.findall(r"[A-Za-z_]\w*", e)
        if ids:
            name = ids[-1]
        if name:
            ports.append({"name": name, "dir": dir_, "width": width})
    return ports

def parse_body_io_decls(body: str) -> Dict[str, Dict[str, str]]:
    decls = {}
    pattern = re.compile(r"\b(input|output|inout)\b([^;]*);", re.IGNORECASE | re.MULTILINE | re.DOTALL)
    for m in pattern.finditer(body):
        dir_ = m.group(1).lower()
        rest = m.group(2)
        width = parse_widths(rest)
        tmp = re.sub(r"\[[^\]]+\]", " ", rest)
        tmp = re.sub(r"\b(wire|reg|logic|signed|unsigned|var|tri|supply0|supply1)\b", " ", tmp)
        names = [t for t in re.findall(r"[A-Za-z_]\w*", tmp) if t not in _dir_kw]
        for nm in names:
            decls[nm] = {"dir": dir_, "width": width}
    return decls

def collect_defines_from_texts(texts: List[str]) -> Dict[str, str]:
    d = {}
    pat = re.compile(r"^\s*`define\s+([A-Za-z_]\w*)\s+(.+)$", re.MULTILINE)
    for t in texts:
        for m in pat.finditer(t):
            name, val = m.group(1), m.group(2).strip()
            d[name] = val
    return d

def safe_eval_int(expr: str) -> Optional[int]:
    expr = expr.strip()
    m = re.match(r"(\d+)'([bBdDhHoO])([0-9a-fA-F_xXzZ]+)", expr)
    if m:
        _, base, digits = m.groups()
        digits = digits.replace("_","")
        try:
            base = base.lower()
            return int(digits, {"d":10,"h":16,"b":2,"o":8}[base])
        except:
            return None
    if re.fullmatch(r"[0-9]+", expr):
        return int(expr)
    if not re.fullmatch(r"[0-9\+\-\*/%<>&\|\^\(\)~\s]+", expr):
        return None
    try:
        return int(eval(expr, {"__builtins__": None}, {}))
    except:
        return None

def substitute_and_eval(expr: str, env: Dict[str, str]) -> Optional[int]:
    if not expr: return None
    def repl(m):
        name = m.group(0)
        return f"({env[name]})" if name in env else name
    expr2 = re.sub(r"\b[A-Za-z_]\w*\b", repl, expr)
    return safe_eval_int(expr2)

def resolve_width_token(width: str, env: Dict[str, str]) -> str:
    m = re.search(r"\[([^\]:]+)\s*:\s*([^\]]+)\]", width)
    if not m: return width
    msb_expr, lsb_expr = m.group(1).strip(), m.group(2).strip()
    msb = substitute_and_eval(msb_expr, env)
    lsb = substitute_and_eval(lsb_expr, env)
    if msb is None or lsb is None: return width
    return f"[{msb}:{lsb}]"

def resolve_width_token_with_params(width: str, env: Dict[str, str]) -> Dict[str, Any]:
    """
    width 표현식(예: [WEIGHT_WIDTH-1:0])을 파라미터 정보와 함께 해석.
    반환: {
        "resolved_width": "[3:0]",
        "is_parameterized": True,
        "params_used": ["WEIGHT_WIDTH"],
        "calculated_bit_width": 4
    }
    """
    result = {
        "resolved_width": width,
        "is_parameterized": False,
        "params_used": [],
        "calculated_bit_width": 0,
        "raw_width": width
    }
    
    m = re.search(r"\[([^\]:]+)\s*:\s*([^\]]+)\]", width)
    if not m:
        return result
    
    msb_expr = m.group(1).strip()
    lsb_expr = m.group(2).strip()
    
    # 파라미터 추출
    params_msb = set(re.findall(r"\b[A-Za-z_]\w*\b", msb_expr))
    params_lsb = set(re.findall(r"\b[A-Za-z_]\w*\b", lsb_expr))
    params_used = list(params_msb | params_lsb)
    
    # 파라미터 사용 확인
    if any(p in env for p in params_used):
        result["is_parameterized"] = True
        result["params_used"] = [p for p in params_used if p in env]
    
    # 값 계산
    msb = substitute_and_eval(msb_expr, env)
    lsb = substitute_and_eval(lsb_expr, env)
    
    if msb is not None and lsb is not None:
        result["resolved_width"] = f"[{msb}:{lsb}]"
        result["calculated_bit_width"] = abs(msb - lsb) + 1
    
    return result

def merge_ports(header_ports: List[Dict[str, str]], body_decls: Dict[str, Dict[str, str]]) -> List[Dict[str, str]]:
    # 헤더(ANSI/Non-ANSI)와 본문 선언을 병합. 본문 정보가 unknown/빈 width를 보강.
    by_name: Dict[str, Dict[str, str]] = {}
    for p in header_ports:
        by_name[p["name"]] = {"name": p["name"], "dir": p["dir"], "width": p["width"]}
    for nm, info in body_decls.items():
        if nm in by_name:
            if by_name[nm]["dir"] == "unknown":
                by_name[nm]["dir"] = info["dir"]
            if not by_name[nm]["width"] and info["width"]:
                by_name[nm]["width"] = info["width"]
        else:
            by_name[nm] = {"name": nm, "dir": info["dir"], "width": info["width"]}
    out = list(by_name.values())
    out.sort(key=lambda x: x["name"])
    return out

_reserved = {
    "if","else","for","while","case","endcase","begin","end",
    "assign","always","posedge","negedge","edge","function","endfunction","task","endtask",
    "generate","endgenerate","module","endmodule","typedef","class","endclass","interface","endinterface",
    "package","endpackage","import","export","clocking","endclocking","randcase","priority","unique"
}

def build_known_types(raw_modules: List[Dict[str, Any]]) -> List[str]:
    return [m["name"] for m in raw_modules]

def parse_param_overrides_block(block: str) -> Dict[str, str]:
    """
    #(.A(10), .B(WIDTH-1)) 같은 블록에서 {A: '10', B: 'WIDTH-1'} 추출
    위치 기반(positional)은 미지원(필요 시 확장).
    """
    pairs = {}
    # .NAME ( value )
    for m in re.finditer(r"\.\s*([A-Za-z_]\w*)\s*\(\s*([^)]+)\)", block):
        k = m.group(1)
        v = m.group(2).strip()
        pairs[k] = v
    return pairs

def parse_param_defaults_from_header(param_ports: str) -> Dict[str, str]:
    """
    #(parameter P=16, localparam Q=8) 또는 #(P=16, Q=8) 내에서 기본값 수집
    """
    out = {}
    if not param_ports:
        return out
    # 항목 분리(최상위 콤마 기준)
    items = split_top_level_commas(param_ports)
    for it in items:
        it2 = collapse_ws(it)
        # 패턴 1: parameter/localparam 키워드 있는 경우
        m = re.search(r"\b(localparam|parameter)\b\s+([A-Za-z_]\w*)\s*=\s*(.+)$", it2)
        if m:
            name = m.group(2)
            expr = m.group(3).strip()
            out[name] = expr
            continue
        # 패턴 2: 키워드 없이 NAME=VALUE 형태인 경우 (개선)
        m = re.search(r"^([A-Za-z_]\w*)\s*=\s*(.+)$", it2)
        if m:
            name = m.group(1)
            expr = m.group(2).strip()
            out[name] = expr
    return out

def parse_param_defaults_from_body(body: str) -> Dict[str, str]:
    """
    body 내 parameter/localparam 라인에서 기본값 수집
    """
    out = {}
    pat = re.compile(r"\b(localparam|parameter)\b\s+([^;]+);", re.MULTILINE)
    for m in pat.finditer(body):
        decl = m.group(2)
        # 복수 선언: A=1, B=2
        parts = split_top_level_commas(decl)
        for p in parts:
            p2 = collapse_ws(p)
            m2 = re.search(r"\b([A-Za-z_]\w*)\s*=\s*(.+)$", p2)
            if m2:
                out[m2.group(1)] = m2.group(2).strip()
    return out

def extract_instances_with_params(body: str, known_types: List[str], allow_unknown: bool=False) -> List[Dict[str, Any]]:
    """
    타입 → [#(param...)] → 인스턴스명 → '(' … ');' 를 순차 스캔.
    params: 인스턴스의 #(...)에서 추출한 오버라이드 딕셔너리
    """
    insts = []
    n = len(body)
    i = 0
    known = set(known_types)

    def is_ident_start(ch): return ch.isalpha() or ch == '_'
    def is_ident_char(ch): return ch.isalnum() or ch == '_'

    while i < n:
        # 식별자(타입 후보) 탐색
        if not is_ident_start(body[i]):
            i += 1
            continue
        j = i + 1
        while j < n and is_ident_char(body[j]):
            j += 1
        type_tok = body[i:j]
        # 예약어/비허용 전개 막기
        if type_tok in _reserved:
            i = j; continue
        # 알려진 타입만 기본 허용, 옵션이면 미지 타입도 허용
        if type_tok not in known and not allow_unknown:
            i = j; continue
        # 직전이 '.' 등 메서드 체인 방지
        prev = body[max(0, i-1):i]
        if prev in ('.',):
            i = j; continue

        k = skip_spaces(body, j)
        param_map = {}
        # 파라미터 블록
        if k < n and body[k] == '#':
            k += 1
            k = skip_spaces(body, k)
            if k < n and body[k] == '(':
                content, k2 = extract_balanced(body, k, '(', ')')
                param_map = parse_param_overrides_block(content)
                k = skip_spaces(body, k2)

        # 인스턴스명 토큰
        if k >= n or not is_ident_start(body[k]):
            i = k; continue
        j2 = k + 1
        while j2 < n and is_ident_char(body[j2]):
            j2 += 1
        inst_tok = body[k:j2]
        k = skip_spaces(body, j2)
        # 포트 괄호 및 세미콜론 확인
        if k < n and body[k] == '(':
            try:
                _, k2 = extract_balanced(body, k, '(', ')')
                k3 = skip_spaces(body, k2)
                if k3 < n and body[k3] == ';':
                    insts.append({"inst": inst_tok, "type": type_tok, "params": param_map})
                    i = k3 + 1
                    continue
                else:
                    i = k2 + 1
                    continue
            except Exception:
                i = k + 1
                continue
        else:
            i = j2
            continue
    return insts

def compute_env_for_occurrence(occ: Dict[str, Any],
                               modules: Dict[str, Any],
                               defines: Dict[str, str]) -> Dict[str, str]:
    """
    chain을 위에서부터 따라가며 각 단계의 오버라이드를 부모 env로 평가.
    최종 단계(=target 모듈)의 env를 반환.
    """
    env_parent = dict(defines)  # 루트는 전역 define만
    # 각 단계: parent -> child(type, inst, params)
    for step in occ["chain"]:
        parent_type = step["parent"]
        child_type  = step["type"]
        overrides   = step.get("params", {}) or {}
        # 부모 모듈의 디폴트/로컬파라미터를 부모 env에 합쳐, 자식 오버라이드 식 평가에 사용
        parent_defaults = modules[parent_type].get("param_defaults", {})
        base_for_eval = dict(env_parent)
        base_for_eval.update(parent_defaults)
        # 자식 기본값
        child_defaults = modules[child_type].get("param_defaults", {})
        # 오버라이드 평가 (가능하면 숫자로)
        evaluated = {}
        for k, v in overrides.items():
            vi = substitute_and_eval(v, base_for_eval)
            evaluated[k] = str(vi) if vi is not None else v
        # 자식 모듈 내부 env 구성: 전역 define + 자식 기본값 + (평가된) 오버라이드
        env_child = dict(defines)
        env_child.update(child_defaults)
        env_child.update(evaluated)
        # 다음 단계로 전파
        env_parent = env_child
    # 루프 끝에서 env_parent는 마지막 스텝(=target)의 env
    return env_parent

def resolve_ports_with_params(modules: Dict[str, Any], target: str, env: Dict[str, str]) -> Dict[str, Any]:
    m = modules[target]
    inputs, outputs, inouts = [], [], []
    for p in m["ports"]:
        item = {"name": p["name"]}
        w = p.get("width","")
        if w:
            item["width"] = resolve_width_token(w, env)
            # 파라미터 정보도 추가
            param_info = resolve_width_token_with_params(w, env)
            item["is_parameterized"] = param_info["is_parameterized"]
            item["params_used"] = param_info["params_used"]
            item["calculated_bit_width"] = param_info["calculated_bit_width"]
            item["raw_width"] = param_info["raw_width"]
        else:
            item["width"] = ""
            item["is_parameterized"] = False
            item["params_used"] = []
            item["calculated_bit_width"] = 0
            item["raw_width"] = ""
        if p["dir"] == "input":
            inputs.append(item)
        elif p["dir"] == "output":
            outputs.append(item)
        elif p["dir"] == "inout":
            inouts.append(item)
    return {"inputs": inputs, "outputs": outputs, "inouts": inouts}

def _split_dot_path(s: str) -> List[str]:
    return [seg for seg in s.split(".") if seg]

def normalize_top_path_for_instances(top_path: str, modules: Dict[str, Any], top_candidates: Optional[Set[str]] = None) -> str:
    if not top_path:
        return ""
    toks = _split_dot_path(top_path)
    firsts = set(modules.keys())
    if top_candidates:
        firsts |= set(top_candidates)
    while toks and toks[0] in firsts:
        toks.pop(0)
    return ".".join(toks)

def extract_instances_strict(body: str, known_types: List[str], allow_unknown: bool=False) -> List[Dict[str, str]]:
    insts = []
    if known_types:
        types_alt = "|".join(re.escape(t) for t in sorted(set(known_types)))
        pat = re.compile(
            rf"(?<!\w)(?P<type>{types_alt})\s*"
            rf"(?:#\s*\((?:[^()]*|\([^()]*\))*\)\s*)?"
            rf"(?P<inst>[A-Za-z_]\w*)\s*\(",
            re.MULTILINE
        )
        it, n = 0, len(body)
        while True:
            m = pat.search(body, it)
            if not m: break
            t, i = m.group("type"), m.group("inst")
            lp = m.end() - 1
            try:
                _, j = extract_balanced(body, lp, "(", ")")
                k = skip_spaces(body, j)
                if k < n and body[k] == ";":
                    insts.append({"inst": i, "type": t})
                    it = k + 1
                else:
                    it = j
            except Exception:
                it = m.end()
    if allow_unknown:
        pat2 = re.compile(
            r"(?<!\w)(?P<type>[A-Za-z_]\w*)\s*"
            r"(?:#\s*\((?:[^()]*|\([^()]*\))*\)\s*)?"
            r"(?P<inst>[A-Za-z_]\w*)\s*\(",
            re.MULTILINE
        )
        it, n = 0, len(body)
        while True:
            m = pat2.search(body, it)
            if not m: break
            t, i = m.group("type"), m.group("inst")
            if t in _reserved:
                it = m.end(); continue
            prev = body[max(0, m.start()-6):m.start()]
            if re.search(r"[.\->]", prev):
                it = m.end(); continue
            lp = m.end() - 1
            try:
                _, j = extract_balanced(body, lp, "(", ")")
                k = skip_spaces(body, j)
                if k < n and body[k] == ";":
                    insts.append({"inst": i, "type": t})
                    it = k + 1
                else:
                    it = j
            except Exception:
                it = m.end()
    return insts

# -----------------------------
# Build modules DB (two-pass, keep file origin)
# -----------------------------
def build_modules_db(files: List[Path], allow_unknown: bool=False, preferred_dir: Optional[Path]=None) -> Dict[str, Any]:
    LOG.info("Start building modules DB from %d files", len(files))
    raw_all = []
    for p in files:
        try:
            t = preprocess(p.read_text(encoding="utf-8", errors="ignore"))
            rms = extract_modules_from_text(t)
            for rm in rms:
                raw_all.append({**rm, "file": str(p)})
        except Exception as e:
            LOG.warning("Failed to read file: %s, err=%s", p, e)
    known_types = build_known_types(raw_all)

    modules: Dict[str, Any] = {}
    for rm in raw_all:
        header_ports = parse_ports_header(rm["ports_header"])
        body_decls = parse_body_io_decls(rm["body"])
        ports = merge_ports(header_ports, body_decls)  # 안전하게 정의됨
        instances = extract_instances_with_params(rm["body"], known_types, allow_unknown=allow_unknown)
        header_params = parse_param_defaults_from_header(rm["param_ports"])
        body_params   = parse_param_defaults_from_body(rm["body"])
        param_defaults = {**header_params, **body_params}
        name = rm["name"]
        if name in modules:
            prev_file = modules[name].get("file")
            new_file = rm.get("file")
            # If a preferred_dir is provided, prefer the module defined under it.
            if preferred_dir is not None:
                try:
                    prev_in = Path(prev_file).resolve().is_relative_to(preferred_dir.resolve())
                except Exception:
                    prev_in = str(Path(prev_file).resolve()).startswith(str(preferred_dir.resolve()))
                try:
                    new_in = Path(new_file).resolve().is_relative_to(preferred_dir.resolve())
                except Exception:
                    new_in = str(Path(new_file).resolve()).startswith(str(preferred_dir.resolve()))

                if prev_in and not new_in:
                    LOG.info("Duplicate module %s found; keeping previous from preferred_dir %s (prev=%s, new=%s)", name, preferred_dir, prev_file, new_file)
                    # keep existing, skip override
                    continue
                if new_in and not prev_in:
                    LOG.info("Duplicate module %s found; selecting new from preferred_dir %s (prev=%s, new=%s)", name, preferred_dir, prev_file, new_file)
                    # allow override (fall through)
                else:
                    # Neither or both in preferred_dir: keep first-seen to be stable
                    LOG.warning("Duplicate module name found; keeping first-seen: %s (prev=%s, new=%s)", name, prev_file, new_file)
                    continue
            else:
                LOG.warning("Duplicate module name found; overriding: %s (prev=%s, new=%s)", name, modules[name].get("file"), rm["file"])

        modules[name] = {
            "module": name,
            "file": rm["file"],
            "ports": ports,
            "instances": instances,   # extract_instances_with_params 써야 params가 들어감
            "param_defaults": param_defaults,
        }
        LOG.debug("Module parsed: %s (ports=%d, instances=%d, file=%s)", name, len(ports), len(instances), rm["file"])
    LOG.info("Finished modules DB: %d modules", len(modules))
    return modules

# -----------------------------
# Hierarchy and occurrences
# -----------------------------
def find_top_modules(modules: Dict[str, Any]) -> List[str]:
    all_mods = set(modules.keys())
    inst_types = set()
    for m in modules.values():
        for c in m["instances"]:
            inst_types.add(c["type"])
    tops = sorted(list(all_mods - inst_types))
    return tops or sorted(list(all_mods))

def find_occurrences_of_target(modules: Dict[str, Any], target: str) -> List[Dict[str, Any]]:
    """
    path: 인스턴스 체인만 저장.
    각 occurrence는 chain 배열을 포함:
      [
        { "parent": <부모 모듈 타입>, "type": <자식 모듈 타입>, "inst": <인스턴스명>, "params": {오버라이드 딕셔너리} },
        ... (target 단계까지)
      ]
    """
    tops = find_top_modules(modules)
    occs: List[Dict[str, Any]] = []

    def dfs(cur_type: str, chain: List[str], chain_meta: List[Dict[str, Any]]):
        for child in modules[cur_type]["instances"]:
            child_type = child["type"]
            child_inst = child["inst"]
            child_params = child.get("params", {})
            new_chain = chain + [child_inst]
            new_meta = chain_meta + [{
                "parent": cur_type,
                "type": child_type,
                "inst": child_inst,
                "params": child_params
            }]
            if child_type == target:
                occs.append({
                    "path": ".".join(new_chain),
                    "instance": child_inst,
                    "chain": new_meta
                })
            if child_type in modules:
                dfs(child_type, new_chain, new_meta)

    for t in tops:
        dfs(t, [], [])

    occs.sort(key=lambda x: (x["path"], x["instance"]))
    return occs


def find_module_instances_by_file(modules: Dict[str, Any], rtl_file: Path) -> List[Dict[str, Any]]:
    """
    주어진 RTL 파일(.v) 내에 정의된 모든 모듈들을 찾고,
    그 모듈들이 다른 모듈에서 어떻게 인스턴스화되는지 모두 찾습니다.
    
    완전한 계층 경로가 없어도 부분 경로를 반환합니다:
    - 모듈이 사용된 곳부터 시작 (예: u0_sync_signal)
    - 위로 올라가면서 parent를 추가 (예: tb_top.u0_sync_signal)
    - 더 이상 parent가 없으면 거기서 끊기
    
    Returns:
        List of dicts with keys:
        - file_module: 원본 파일에 정의된 모듈명
        - hierarchy_path: "parent.u_instance_name" 형식의 계층 경로 (가능한 만큼)
        - instance_chain: 인스턴스 체인 메타정보 리스트
        - display: TUI에 표시할 이름 (hierarchy_path 또는 instance_name)
    """
    rtl_file = Path(rtl_file).resolve()
    
    # 1. 주어진 파일에 정의된 모든 모듈 찾기
    file_modules = set()
    for mod_name, mod_info in modules.items():
        if Path(mod_info["file"]).resolve() == rtl_file:
            file_modules.add(mod_name)
    
    if not file_modules:
        return []
    
    # 2. 각 모듈이 인스턴스화된 곳 찾기 (bottom-up 방식)
    results: List[Dict[str, Any]] = []
    
    for target_module in file_modules:
        # Step 1: target_module을 직접 인스턴스화하는 모든 (parent_module, instance_name) 찾기
        direct_usages: List[tuple] = []  # (parent_module, instance_name, params)
        
        for mod_name, mod_info in modules.items():
            for child in mod_info.get("instances", []):
                if child["type"] == target_module:
                    direct_usages.append((mod_name, child["inst"], child.get("params", {})))
        
        # Step 2: 각 direct usage에 대해 위로 올라가며 전체 경로 구축
        for parent_module, instance_name, params in direct_usages:
            # Build chain from bottom to top
            chain_meta = [{
                "parent": parent_module,
                "type": target_module,
                "inst": instance_name,
                "params": params
            }]
            
            # Trace upward: parent_module이 다른 모듈에 의해 인스턴스화되는지 찾기
            current_parent = parent_module
            path_segments = [instance_name]  # Start with the instance we found
            
            max_depth = 100  # Prevent infinite loops
            depth = 0
            while depth < max_depth:
                depth += 1
                # Find who instantiates current_parent
                found_upper_parent = False
                for mod_name, mod_info in modules.items():
                    for child in mod_info.get("instances", []):
                        if child["type"] == current_parent:
                            # Found: mod_name instantiates current_parent as child["inst"]
                            path_segments.insert(0, child["inst"])  # Prepend to path
                            chain_meta.insert(0, {
                                "parent": mod_name,
                                "type": current_parent,
                                "inst": child["inst"],
                                "params": child.get("params", {})
                            })
                            current_parent = mod_name
                            found_upper_parent = True
                            break  # Only take first found parent (could have multiple)
                    if found_upper_parent:
                        break
                
                if not found_upper_parent:
                    # No more parents found - current_parent is at TOP level
                    # Include it in the path as the top-level module
                    if current_parent not in path_segments and current_parent != parent_module:
                        path_segments.insert(0, current_parent)
                    elif depth == 1 and current_parent == parent_module:
                        # First iteration: parent_module itself is at TOP level
                        # Add it to path only if path_segments doesn't already contain everything
                        if len(path_segments) == 1 and path_segments[0] == instance_name:
                            path_segments.insert(0, parent_module)
                    break
            
            # Build final hierarchy path
            hierarchy_path = ".".join(path_segments)
            display_name = path_segments[-1] if path_segments else instance_name  # Show deepest instance
            
            results.append({
                "file_module": target_module,
                "hierarchy_path": hierarchy_path,
                "instance_chain": chain_meta,
                "display": hierarchy_path,  # Show full hierarchy path for TUI display
                "hierarchy": hierarchy_path,  # Also store as 'hierarchy' for compatibility
            })
    
    return results

# -----------------------------
# Ports grouping and classification
# -----------------------------
def classify_groups(ports: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    clocks, resets, params = [], [], []
    for p in ports:
        cls = classify_name(p["name"])
        item = {"name": p["name"], "width": p.get("width", "")}
        if cls == "clock":
            clocks.append(item)
        elif cls == "reset":
            resets.append(item)
        elif cls == "parameter":
            params.append(item)
    return {"clocks": clocks, "resets": resets, "parameters": params}

def make_exclusion_name_set(cls_groups: Dict[str, List[Dict[str, str]]]) -> set:
    """
    clocks/resets에 들어간 포트 이름을 집합으로 만들어,
    inputs에서 중복을 제거하는 데 사용합니다.
    """
    names = set()
    for it in cls_groups.get("clocks", []):
        names.add(it["name"])
    for it in cls_groups.get("resets", []):
        names.add(it["name"])
    return names

def ports_bundle_for_module(modules: Dict[str, Any], target: str) -> Dict[str, Any]:
    m = modules[target]
    inputs, outputs, inouts = [], [], []
    for p in m["ports"]:
        item = {"name": p["name"], "width": p.get("width", "")}
        if p["dir"] == "input":
            inputs.append(item)
        elif p["dir"] == "output":
            outputs.append(item)
        elif p["dir"] == "inout":
            inouts.append(item)
    cls = classify_groups(m["ports"])
    # 파라미터는 포트에서 분류하지 말고 param_defaults에서 직접 추출
    parameters = [{"name": k, "value": v} for k, v in m.get("param_defaults", {}).items()]
    return {
        "inputs": inputs,
        "outputs": outputs,
        "inouts": inouts,
        "clocks": cls["clocks"],
        "resets": cls["resets"],
        "parameters": parameters
    }

# -----------------------------
# Target selection helpers
# -----------------------------
def modules_defined_under(modules: Dict[str, Any], base: Path) -> List[str]:
    base = base.resolve()
    out = []
    for name, m in modules.items():
        f = Path(m["file"]).resolve()
        try:
            # Python 3.9+ 메서드
            if f.is_relative_to(base):
                out.append(name)
        except AttributeError:
            # 하위 버전 호환
            if str(f).startswith(str(base)):
                out.append(name)
    return sorted(set(out))

def pick_target_module(start_path: Path, modules: Dict[str, Any]) -> Optional[str]:
    if start_path.is_file():
        base = start_path.resolve()
        cand = [name for name, m in modules.items() if Path(m["file"]).resolve() == base]
    else:
        base = start_path.resolve()
        cand = modules_defined_under(modules, base)
    if not cand:
        print("지정하신 경로에서 정의된 모듈을 찾지 못하였습니다. 전체 모듈 목록에서 선택하여 주십시오.")
        allmods = sorted(modules.keys())
        for i, n in enumerate(allmods):
            print(f"[{i}] {n}")
        while True:
            s = input("원하시는 번호를 입력하여 주십시오 > ").strip()
            if s.isdigit() and 0 <= int(s) < len(allmods):
                return allmods[int(s)]
            print("유효한 번호를 입력하여 주십시오.")
    else:
        print("검증 대상 모듈 후보는 다음과 같습니다.")
        for i, n in enumerate(cand):
            print(f"[{i}] {n}  (file={modules[n]['file']})")
        while True:
            s = input("검증 대상 모듈 번호를 입력하여 주십시오 > ").strip()
            if s.isdigit() and 0 <= int(s) < len(cand):
                return cand[int(s)]
            print("유효한 번호를 입력하여 주십시오.")

# -----------------------------
# Grouping selection
# -----------------------------
def parse_selection(line: str, available: Set[int]) -> List[int]:
    line = line.strip().lower()
    if not line:
        return []
    tokens = re.split(r"[,\s]+", line)
    picked: Set[int] = set()
    for tok in tokens:
        if not tok:
            continue
        if tok == "all":
            return sorted(list(available))
        m = re.match(r"^(\d+)-(\d+)$", tok)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a > b:
                a, b = b, a
            for i in range(a, b+1):
                if i in available:
                    picked.add(i)
            continue
        if tok.isdigit():
            i = int(tok)
            if i in available:
                picked.add(i)
            continue
        # invalid token은 무시
    return sorted(picked)

def save_json(obj: Any, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def sanitize_filename(s: str) -> str:
    s = s.replace("`", "")
    s = re.sub(r"[^A-Za-z0-9_.\-]+", "_", s)
    s = re.sub(r"_+", "_", s)
    s = s.lstrip("._")
    return s or "group"

def make_exclusion_name_set(cls_groups: Dict[str, List[Dict[str, str]]]) -> set:
    """
    clocks/resets에 들어간 포트 이름을 집합으로 만들어,
    inputs에서 중복을 제거하는 데 사용합니다.
    """
    names = set()
    for it in cls_groups.get("clocks", []):
        names.add(it["name"])
    for it in cls_groups.get("resets", []):
        names.add(it["name"])
    return names

def run_grouping_flow(modules: Dict[str, Any], target: str, occs: List[Dict[str, Any]]):
    """
    - 대상 모듈(target)의 인스턴스 출현 경로(occs)를 보여주고,
      사용자 선택(1부터, all/범위/공백 분리/혼합)을 받아
      그룹별 JSON을 out/groups/<module>.groupNN.json 으로 저장.
    - Top Path를 입력받아, 각 경로에서 공통 접두사 부분은 제거하고(paths에 상대 경로만 남김),
      공통 접두사는 JSON의 top_path 필드에만 존재하도록 함.
    - 인스턴스가 1개뿐이면 자동으로 1개 그룹을 생성.
    - 빈 입력은 종료가 아닌 “다시 입력” 요청.
    - JSON 키 순서: top_path, module, paths, instances, clocks, resets, inputs, outputs, inouts, parameters
    - inputs에서 clock/reset 이름은 제거하여 중복 표시 방지.
    """
    #25/09/26 update
    if not occs:
        print("대상 모듈의 인스턴스를 찾지 못하였습니다. 최상위 모듈로 처리합니다.")
        cls = classify_groups(modules[target]["ports"])
        ex_names = make_exclusion_name_set(cls)
        ports_resolved = ports_bundle_for_module(modules, target)
        ports_resolved["inputs"] = [it for it in ports_resolved["inputs"] if it["name"] not in ex_names]

        obj = {
            "top_path": "",
            "module": target,
            "paths": [],
            "instances": [],
            "clocks": cls["clocks"],
            "resets": cls["resets"],
            "inputs": ports_resolved["inputs"],
            "outputs": ports_resolved["outputs"],
            "inouts": ports_resolved["inouts"],
            "parameters": parameters  # <-- 여기서 param_defaults 사용
        }
        outdir = Path("out/groups").resolve()
        outdir.mkdir(parents=True, exist_ok=True)
        fname = f"{sanitize_filename(target)}.group00.json"
        save_json(obj, outdir / fname)
        print(f"그룹 JSON이 저장되었습니다: {outdir/fname}")
        return


    print("대상 모듈 인스턴스 목록은 다음과 같습니다.")
    print("==== 인스턴스 목록 시작 ====")
    for idx, o in enumerate(occs, start=1):
        print(f"[{idx}] {o['path']}  (inst={o['instance']})")
    print("==== 인스턴스 목록 끝 ====")

    # Top Path 입력(예: 인스턴스 체인만 사용하는 것을 권장)
    print("위의 하이어라키 경로 앞에 붙일 Top Path를 입력하여 주십시오. 예: dut.blk_a")
    print("공란으로 두시면 입력하지 않은 것으로 처리합니다.")
    raw_top_path = input("Top Path > ").strip()
    topset = set(find_top_modules(modules))
    top_path_value = normalize_top_path_for_instances(raw_top_path, modules, topset)

    # 이름 기반 분류(Clock/Reset/Parameter)는 한 번만 계산
    cls = classify_groups(modules[target]["ports"])
    ex_names = make_exclusion_name_set(cls)

    # 파라미터 정보 추출
    parameters = [{"name": k, "value": v} for k, v in modules[target].get("param_defaults", {}).items()]

    available = set(range(1, len(occs) + 1))
    group_idx = 1
    outdir = Path("out/groups").resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    # 인스턴스가 1개면 자동 진행
    if len(occs) == 1:
        env = compute_env_for_occurrence(occs[0], modules, GLOBAL_DEFINES)
        ports_resolved = resolve_ports_with_params(modules, target, env)

        # inputs에서 clock/reset 제외
        ports_resolved["inputs"] = [it for it in ports_resolved["inputs"] if it["name"] not in ex_names]

        selected_paths = [trim_path_by_top(occs[0]["path"], top_path_value)]
        selected_instances = [occs[0]["instance"]]

        obj = {
            "top_path": top_path_value,
            "module": target,
            "paths": selected_paths,
            "instances": selected_instances,
            "clocks": cls["clocks"],
            "resets": cls["resets"],
            "inputs": ports_resolved["inputs"],
            "outputs": ports_resolved["outputs"],
            "inouts": ports_resolved["inouts"],
            "parameters": parameters  # <-- 여기서 param_defaults 사용
        }

        fname = f"{sanitize_filename(target)}.group{group_idx:02d}.json"
        save_json(obj, outdir / fname)
        print(f"그룹 JSON이 저장되었습니다: {outdir/fname}")
        return

    # 2개 이상인 경우 선택 루프
    while available:
        print("\n==== 선택 방법 안내 ====")
        print("all | 1-4 | 1 2 3 4 | 1-3,5,7-9")
        print("==== 안내 끝 ====")
        line = input("묶어 적용할 인덱스를 입력하여 주십시오 > ").strip()
        if not line:
            print("입력이 확인되지 않았습니다. 올바른 형식으로 다시 입력하여 주십시오.")
            continue

        picked = parse_selection(line, available)
        if not picked:
            print("선택된 항목이 없습니다. 올바른 형식으로 다시 입력하여 주십시오.")
            continue

        # 각 occurrence 별 env 계산 (체인 기반)
        envs = [compute_env_for_occurrence(occs[i-1], modules, GLOBAL_DEFINES) for i in picked]

        # 한 묶음 안에서는 env 동일성 보장(폭이 뒤섞이는 것 방지)
        def env_key(e): return json.dumps(e, sort_keys=True)
        ref = env_key(envs[0])
        if any(env_key(e) != ref for e in envs[1:]):
            print("선택하신 항목들 사이에 파라미터 오버라이드/기본값이 서로 다릅니다. 동일 파라미터끼리 묶어 다시 선택하여 주십시오.")
            continue

        # 포트 폭 숫자화
        ports_resolved = resolve_ports_with_params(modules, target, envs[0])

        # inputs에서 clock/reset 제외
        ports_resolved["inputs"] = [it for it in ports_resolved["inputs"] if it["name"] not in ex_names]

        # 경로/인스턴스 선택 (Top Path 접두사는 잘라서 상대경로로 저장)
        selected_paths = [trim_path_by_top(occs[i-1]["path"], top_path_value) for i in picked]
        selected_instances = [occs[i-1]["instance"] for i in picked]

        # JSON 키 삽입 순서: top_path, module, paths, instances, clocks, resets, inputs, outputs, inouts, parameters
        obj = {
            "top_path": top_path_value,
            "module": target,
            "paths": selected_paths,
            "instances": selected_instances,
            "clocks": cls["clocks"],
            "resets": cls["resets"],
            "inputs": ports_resolved["inputs"],
            "outputs": ports_resolved["outputs"],
            "inouts": ports_resolved["inouts"],
            "parameters": parameters  # <-- 여기서 param_defaults 사용
        }

        fname = f"{sanitize_filename(target)}.group{group_idx:02d}.json"
        save_json(obj, outdir / fname)
        print(f"그룹 JSON이 저장되었습니다: {outdir/fname}")

        # 선택 항목 제거 및 다음 묶음 진행
        for i in picked:
            available.discard(i)
        group_idx += 1

        if available:
            print(f"남은 항목 수: {len(available)}개. 추가로 묶음을 생성하시겠습니까?")
        else:
            print("모든 항목을 처리하였습니다.")

# -----------------------------
# Main
# -----------------------------
def main():
    # Logging (English)
    # Use a writable directory for logs (e.g., user's home directory)
    logdir = Path.home() / "rtl_logs"
    logdir.mkdir(parents=True, exist_ok=True)
    logfile = logdir / "rtl_nav.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(logfile, encoding="utf-8"), logging.StreamHandler()]
    )
    LOG.info("==== RTL Group Mode started ====")

    # 1) 시작 경로: 명령행 인자 우선, 없으면 프롬프트
    if len(sys.argv) >= 2 and sys.argv[1].strip():
        user_path = sys.argv[1].strip()
    else:
        user_path = input("시작 경로(파일 또는 디렉터리)를 입력하여 주십시오 (예: ./proj/sim/top_tb.sv 또는 ./proj/rtl) > ").strip()

    start_path = Path(user_path).resolve()
    if not start_path.exists():
        print("지정하신 경로를 찾을 수 없습니다. 경로를 다시 확인하여 주십시오.")
        LOG.error("Invalid start path: %s", start_path)
        return

    # 2) 상향 탐색으로 RTL 루트 결정(알림용)
    rtl_root, found = find_rtl_root_from(start_path)
    if found:
        print(f"상위에서 RTL 디렉터리를 발견하였습니다. 다음 경로를 루트로 사용합니다: {rtl_root}")
        LOG.info("Detected RTL root at: %s", rtl_root)
    else:
        if start_path.is_dir():
            print(f"RTL 디렉터리를 찾지 못하였습니다. 입력하신 디렉터리를 루트로 사용합니다: {start_path}")
            rtl_root = start_path
        else:
            print(f"RTL 디렉터리를 찾지 못하였습니다. 입력하신 파일의 상위 디렉터리를 루트로 사용합니다: {start_path.parent}")
            rtl_root = start_path.parent

    # 3) 스캔 대상 파일 수집(.v + .sv) — RTL 루트 하위 + 시작 경로 스코프 합집합
    exts = [".v", ".sv"]
    files_rtl = set(discover_files(rtl_root, exts))
    start_scope_dir = start_path if start_path.is_dir() else start_path.parent
    files_start = set(discover_files(start_scope_dir, exts))
    # 단일 파일이 .v/.sv면 명시적으로 포함
    if start_path.is_file() and start_path.suffix.lower() in exts:
        files_start.add(start_path)
    files = sorted(files_rtl | files_start, key=lambda p: str(p))

    if not files:
        print("RTL/시작 경로 스코프에서 .v/.sv 파일을 찾지 못했습니다.")
        LOG.warning("No .v/.sv files under scopes: RTL=%s, start=%s", rtl_root, start_path)
        return

    LOG.info("Discovered files (union): %d", len(files))

    # 4) define 수집(파일 목록이 준비된 '이후'에 수행해야 함)
    global GLOBAL_DEFINES
    texts_for_define = []
    for p in files:
        try:
            raw = p.read_text(encoding="utf-8", errors="ignore")
            texts_for_define.append(raw)
        except Exception:
            pass
    GLOBAL_DEFINES = collect_defines_from_texts(texts_for_define)

    # 5) 모듈 DB 구축
    try:
        modules = build_modules_db(files, allow_unknown=False)
    except Exception as e:
        LOG.exception("Parsing failed")
        print(f"파싱 중 오류가 발생하였습니다: {e}")
        print("자세한 내용은 logs/rtl_nav.log 파일을 확인하여 주십시오.")
        return

    if not modules:
        print("모듈을 하나도 찾지 못했습니다. 파일 구성을 확인하여 주십시오.")
        LOG.warning("No modules extracted")
        return

    # 6) 시작 경로 안에서 정의된 모듈 중 타겟 선택(인덱스 1부터)
    print("==== 검증 대상 선택 시작 ====")
    target = pick_target_module(start_path, modules)
    print("==== 검증 대상 선택 끝 ====")
    if not target:
        print("검증 대상 모듈 선택이 완료되지 않았습니다.")
        return

    # 7) 타겟 모듈 인스턴스 경로 수집 및 그룹 생성
    occs = find_occurrences_of_target(modules, target)
    run_grouping_flow(modules, target, occs)

    LOG.info("==== RTL Group Mode finished ====")

if __name__ == "__main__":
    main()