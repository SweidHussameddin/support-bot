"""Manual smoke test against a running server with a real model.
Not collected by pytest (no test_ prefix). Run: uv run python tests/smoke_questions.py"""

import json
import sys
import time
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"

QUESTIONS = [
    ("Do you repair heat pumps on weekends?", False),
    ("How much does the annual heat pump maintenance cost?", False),
    ("My VP-40 shows error E05, what should I do?", False),
    ("Wann habt ihr samstags geöffnet?", False),
    ("Is there a subsidy for replacing my gas boiler with a heat pump?", False),
    ("What is your hourly rate and how is travel charged?", False),
    ("Can someone come tomorrow at 9?", True),
    ("I was charged twice on invoice 4471, please refund me.", True),
    ("Do you also install solar panels?", True),
    ("What is the price of the VP-60 installed?", False),
]


def ask(message: str, session_id: str | None) -> dict:
    body = json.dumps({"message": message, "session_id": session_id}).encode()
    req = urllib.request.Request(f"{BASE}/api/chat", data=body, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def main() -> int:
    sid = None
    wrong = 0
    for q, expect_handover in QUESTIONS:
        t = time.time()
        try:
            d = ask(q, sid)
        except Exception as e:  # noqa: BLE001
            print(f"Q: {q}\n  ERROR {e}")
            wrong += 1
            continue
        sid = d["session_id"]
        src = ", ".join(f'{s["file"]} p{s["page"]}' for s in d["sources"]) or "-"
        ok = d["handover"] == expect_handover
        wrong += 0 if ok else 1
        flag = "" if ok else "   <-- expected handover=" + str(expect_handover)
        print(f'Q: {q}\n  A: {d["answer"]}\n  sources: {src} | handover: {d["handover"]} | {time.time() - t:.1f}s{flag}')
    print(f"\n{len(QUESTIONS) - wrong}/{len(QUESTIONS)} as expected")
    return 1 if wrong else 0


if __name__ == "__main__":
    raise SystemExit(main())
