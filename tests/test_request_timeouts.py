"""이슈 #16: 타임아웃 없는 requests.get/post 호출이 저장소에 남아 있지 않다."""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "__pycache__", "tests"}
CALL = re.compile(r"requests\.(get|post)\(")


def _call_has_timeout(src, start):
    depth, j, instr, esc = 0, start, None, False
    while j < len(src):
        c = src[j]
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == instr:
                instr = None
        elif c in "\"'":
            instr = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return "timeout" in src[start:j]
        j += 1
    return False


def test_every_requests_call_has_timeout():
    offenders = []
    for path in sorted(REPO.rglob("*.py")):
        if any(d in path.parts for d in SKIP_DIRS):
            continue
        if path.name.startswith("test_"):
            continue
        src = path.read_text(encoding="utf-8")
        for m in CALL.finditer(src):
            if not _call_has_timeout(src, m.end() - 1):
                offenders.append(f"{path.relative_to(REPO)}:{src[:m.start()].count(chr(10)) + 1}")
    assert offenders == [], f"timeout 없는 호출: {offenders}"
