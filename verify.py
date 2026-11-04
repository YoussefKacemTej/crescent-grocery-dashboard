"""Run:  python verify.py   -> checks all 40 Question-Book answers."""
from engine import load_data, compute_answers, EXPECTED, check, TOL_OVERRIDE
A = compute_answers(load_data())
bad = 0
for q, (title, exp) in EXPECTED.items():
    ok = check(A[q], exp, TOL_OVERRIDE.get(q, 0.0101)); bad += not ok
    print(f"Q{q:02d} {'OK ' if ok else 'FAIL'} {title}" + ("" if ok else f"\n     got {A[q]}\n     exp {exp}"))
print(f"\n{40-bad}/40 match")
