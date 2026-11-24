"""Test data generator: reads an OpenAPI 3 spec and produces equivalence classes (EP) and
3-point boundary values (BVA) for every JSON request field.

How the cases are derived (one invalid value per case, every other field stays valid):
  required field      -> class "missing" (invalid) and "valid"
  string, min/maxLength -> BVA: limit-1, limit, limit+1 for each limit (length 0 is skipped
                         below the minimum 0), plus "blank" (whitespace only) when x-trimmed
  integer, minimum/maximum -> BVA: limit-1, limit, limit+1 for each limit
  enum                -> each member (valid) and one value outside the enum (invalid)
  any type            -> wrong types ("wrong_type_integer", "wrong_type_null")
  x-lookup            -> refers to existing data: only unknown value, blank, wrong type
A value is valid when it satisfies the schema. x-expect on the operation gives the status and
the JSON subset to assert for valid and for invalid requests.

Usage:
    python scripts/testdatagen.py docs/api/openapi.yaml                 # print a summary
    python scripts/testdatagen.py docs/api/openapi.yaml --out cases.json
    python scripts/testdatagen.py --diff old.json new.json              # show what changed
"""
import argparse
import copy
import json
import sys
from pathlib import Path

import yaml


def load_spec(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _json_schema(operation):
    return operation["requestBody"]["content"]["application/json"]["schema"]


def _text(length, example=""):
    """A string of exactly `length` characters that survives strip() and is not whitespace."""
    if length <= 0:
        return ""
    base = (example or "x")
    return (base * (length // len(base) + 1))[:length]


def _string_values(name, prop, example):
    """Yield (value, class label, is_valid) for a string property."""
    lo = prop.get("minLength")
    hi = prop.get("maxLength")
    mid = None
    if lo is not None and hi is not None:
        mid = (lo + hi) // 2
    elif lo is not None:
        mid = lo + 5
    elif hi is not None:
        mid = max(1, hi // 2)
    if mid is not None:
        yield _text(mid, "A"), "valid_mid", True
    if lo is not None:
        for n, label in ((lo - 1, "below_min"), (lo, "at_min"), (lo + 1, "above_min")):
            if n < 0:
                continue
            yield _text(n, "A"), f"bva_{label}", n >= lo and (hi is None or n <= hi)
    if hi is not None:
        for n, label in ((hi - 1, "below_max"), (hi, "at_max"), (hi + 1, "above_max")):
            if n < 0:
                continue
            yield _text(n, "A"), f"bva_{label}", (lo is None or n >= lo) and n <= hi
    if prop.get("x-trimmed") and (lo or 0) >= 1:
        yield "   ", "blank", False


def _integer_values(prop):
    lo, hi = prop.get("minimum"), prop.get("maximum")
    if lo is not None and hi is not None:
        yield (lo + hi) // 2, "valid_mid", True
    for limit, kind in ((lo, "min"), (hi, "max")):
        if limit is None:
            continue
        for n, label in ((limit - 1, f"below_{kind}"), (limit, f"at_{kind}"), (limit + 1, f"above_{kind}")):
            ok = (lo is None or n >= lo) and (hi is None or n <= hi)
            yield n, f"bva_{label}", ok


def field_cases(name, prop, required):
    """All (value, class, valid) candidates for one field. Value MISSING means omit the key."""
    out = []
    typ = prop.get("type")
    example = prop.get("example")
    if prop.get("x-lookup"):
        out.append((example, "valid_known", True))
        out.append(("ZZZZ99", "unknown", False))
        out.append(("   ", "blank", False))
    elif typ == "string":
        if "enum" in prop:
            out += [(v, "enum_member", True) for v in prop["enum"]]
            out.append(("not-in-enum", "enum_outside", False))
        else:
            if prop.get("minLength") is None and prop.get("maxLength") is None:
                out.append((example, "valid", True))
                out.append(("", "empty_optional", True))
            out += list(_string_values(name, prop, example))
    elif typ == "integer":
        out += list(_integer_values(prop))
    elif typ == "boolean":
        out += [(True, "valid_true", True), (False, "valid_false", True)]
    if not required:
        out.append((MISSING, "optional_omitted", True))
    else:
        out.append((MISSING, "missing_required", False))
    if typ == "string":
        out.append((12345, "wrong_type_integer", False))
    elif typ in ("integer", "boolean"):
        out.append(("text", "wrong_type_string", False))
    out.append((None, "wrong_type_null", False))
    return out


class _Missing:
    def __repr__(self):
        return "MISSING"


MISSING = _Missing()


def generate(spec):
    """Return a list of case dicts, sorted and de-duplicated, for every JSON operation."""
    cases = []
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            if "requestBody" not in op:
                continue
            schema = _json_schema(op)
            props = schema["properties"]
            required = set(schema.get("required", []))
            base = {k: v.get("example") for k, v in props.items() if k in required}
            expect = op.get("x-expect", {})
            seen = {}
            for name, prop in props.items():
                for value, label, valid in field_cases(name, prop, name in required):
                    key = (name, "MISSING" if value is MISSING else json.dumps(value))
                    if key in seen:
                        seen[key]["class"] += "+" + label
                        continue
                    body = copy.deepcopy(base)
                    if value is MISSING:
                        body.pop(name, None)
                    else:
                        body[name] = value
                    case = {
                        "operation": op.get("operationId", f"{method}_{path}"),
                        "method": method.upper(),
                        "path": path,
                        "field": name,
                        "class": label,
                        "valid": valid,
                        "value": None if value is MISSING else value,
                        "omitted": value is MISSING,
                        "body": body,
                        "expect": expect.get("valid" if valid else "invalid", {}),
                    }
                    case["id"] = f"{case['operation']}:{name}:{label}:{len(seen)}"
                    seen[key] = case
                    cases.append(case)
    return cases


def case_id(c):
    return c["id"].replace("+", "_")


def summarise(cases):
    lines = []
    by_op = {}
    for c in cases:
        by_op.setdefault(c["operation"], []).append(c)
    for op, items in by_op.items():
        valid = sum(1 for c in items if c["valid"])
        lines.append(f"{op}: {len(items)} cases ({valid} valid, {len(items) - valid} invalid)")
        fields = {}
        for c in items:
            fields.setdefault(c["field"], []).append(c)
        for f, fc in fields.items():
            lens = sorted({len(c["value"]) for c in fc if isinstance(c["value"], str) and c["class"].startswith(("bva", "valid_mid"))})
            lines.append(f"  {f}: {len(fc)} cases" + (f", string lengths {lens}" if lens else ""))
    return "\n".join(lines)


def diff(old, new):
    key = lambda c: (c["operation"], c["field"], json.dumps(c["value"], sort_keys=True), c["omitted"])
    o = {key(c): c for c in old}
    n = {key(c): c for c in new}
    lines = []
    for k in sorted(set(n) - set(o), key=str):
        c = n[k]
        lines.append(f"+ {c['operation']}.{c['field']} {c['class']} valid={c['valid']} len={_len(c)}")
    for k in sorted(set(o) - set(n), key=str):
        c = o[k]
        lines.append(f"- {c['operation']}.{c['field']} {c['class']} valid={c['valid']} len={_len(c)}")
    for k in sorted(set(o) & set(n), key=str):
        if o[k]["valid"] != n[k]["valid"]:
            lines.append(f"~ {n[k]['operation']}.{n[k]['field']} len={_len(n[k])} valid {o[k]['valid']} -> {n[k]['valid']}")
    return lines


def _len(c):
    return len(c["value"]) if isinstance(c["value"], str) else c["value"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--diff", nargs=2, metavar=("OLD", "NEW"))
    args = ap.parse_args(argv)
    if args.diff:
        old, new = (json.loads(Path(p).read_text(encoding="utf-8")) for p in args.diff)
        lines = diff(old, new)
        print("\n".join(lines) if lines else "no differences")
        return 0
    if not args.spec:
        ap.error("spec path required")
    cases = generate(load_spec(args.spec))
    if args.out:
        Path(args.out).write_text(json.dumps(cases, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(summarise(cases))
    return 0


if __name__ == "__main__":
    sys.exit(main())
