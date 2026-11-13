#!/usr/bin/env python3
"""Summarize TFRES C++ logs; no TensorFlow installation needed."""

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

EVENT = re.compile(r"TFRES\s+([A-Z_]+)\b(.*)$")
FIELD = re.compile(r"(\w+)=([^\s]+)")


def main(path):
    counts = Counter()
    groups = defaultdict(Counter)
    rows = []
    eof = 0
    for lineno, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if "OUT_OF_RANGE: End of sequence" in line:
            eof += 1
        m = EVENT.search(line)
        if not m:
            continue
        op, field_text = m.groups()
        f = dict(FIELD.findall(field_text))
        counts[op] += 1
        rows.append((lineno, op, f))
        if op in ("CREATE_END", "DELETE_END"):
            key = (f.get("name", "?"), f.get("sc", "?"), f.get("rm", "?"))
            label = op + ("_OK" if f.get("ok") == "1" else "_FAIL")
            groups[key][label] += 1
            counts[label] += 1
    print("EOF messages:", eof)
    for label in ("CREATE_END_OK", "DELETE_END_OK", "CREATE_END_FAIL"):
        print(f"{label}: {counts[label]}")
    print("Eager EndStep:", counts["EAGER_END"], "StepContainer cleanup:", counts["SC_CLEANUP_BEGIN"])
    for (name, sc, rm), c in sorted(groups.items()):
        print(
            f"RESOURCE name={name} sc={sc} rm={rm} "
            f"create_ok={c['CREATE_END_OK']} delete_ok={c['DELETE_END_OK']} "
            f"create_failed={c['CREATE_END_FAIL']}"
        )
    for idx, (line_no, op, f) in enumerate(rows):
        if op == "CREATE_END" and f.get("ok") == "0":
            matching = (f.get("name"), f.get("sc"), f.get("rm"))
            earlier = [(n, t, x) for n, t, x in rows[:idx] if (x.get("name"), x.get("sc"), x.get("rm")) == matching]
            last = next(((n, x) for n, t, x in reversed(earlier) if t == "CREATE_END" and x.get("ok") == "1"), None)
            if last:
                last_line, x = last
                deleted = any(
                    t == "DELETE_END" and y.get("ok") == "1"
                    for _, t, y in rows
                    if last_line < _ < line_no and (y.get("name"), y.get("sc"), y.get("rm")) == matching
                )
                cleaned = any(
                    t == "SC_CLEANUP_BEGIN" and y.get("sc") == f.get("sc")
                    for n, t, y in rows
                    if last_line < n < line_no
                )
                print(
                    f"COLLISION at L{line_no}: prior CREATE_OK at L{last_line}; "
                    f"matching Delete after Create={deleted}, "
                    f"matching StepContainer cleanup={cleaned}"
                )
            else:
                print(f"CREATE_FAILED at L{line_no}: no prior matching successful Create in log")
    print("NOTE: TMPVAR_DTOR is not proof of Delete: a failed Create also destructs its new object.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 diagnostics/analyze.py <run.log>")
    main(Path(sys.argv[1]))
