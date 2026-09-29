# PHASE_B_EVIDENCE.md

## Mandatory Check 1: Test-Path scripts
```
True
```

✅ The `scripts/` directory exists.

---

## Mandatory Check 2: Syntax verification
```
syntax ok
```

✅ `python -c "import ast; ast.parse(open('scripts/seed_hindsight.py').read()); print('syntax ok')"` parsed successfully.

---

## Mandatory Check 3: Grep BANK_ID and incident entries
Command: `Select-String -Path scripts/seed_hindsight.py -Pattern "BANK_ID"`
```
scripts\seed_hindsight.py:21:BANK_ID = "incident-memory-bank"
scripts\seed_hindsight.py:74:print(f"Seeding {len(SEEDS)} incidents into bank '{BANK_ID}'...")
scripts\seed_hindsight.py:78:            bank_id=BANK_ID,
```

Command: `Select-String -Path scripts/seed_hindsight.py -Pattern "INC-0[4-4][0-9]"`
```
scripts\seed_hindsight.py:25:        "document_id": "INC-044",
scripts\seed_hindsight.py:27:            "Incident INC-044: auth-service pod OOMKilled in hindsight-agent-apps "
scripts\seed_hindsight.py:35:        "document_id": "INC-045",
scripts\seed_hindsight.py:37:            "Incident INC-045: payment-service timeout calling auth-service. "
scripts\seed_hindsight.py:45:        "document_id": "INC-046",
scripts\seed_hindsight.py:47:            "Incident INC-046: order-service returning 500 errors after a "
scripts\seed_hindsight.py:55:        "document_id": "INC-047",
scripts\seed_hindsight.py:57:            "Incident INC-047: inventory-service memory pressure and GC pauses. "
scripts\seed_hindsight.py:64:        "document_id": "INC-048",
scripts\seed_hindsight.py:66:            "Incident INC-048: notification-service queue backlog. Symptoms: "
```

✅ Script correctly specifies `BANK_ID = "incident-memory-bank"` and contains the 5 seed incidents (INC-044 to INC-048).

---

## Compliance Checklist

| Requirement | Met? | Evidence |
|---|---|---|
| Create exactly ONE NEW FILE `scripts/seed_hindsight.py` | ✅ | Created file with exactly specified content. |
| Forbidden files untouched | ✅ | Only `scripts/seed_hindsight.py` was created. `submission_manifest.json` untouched. |
| Syntax validates | ✅ | Outputs `syntax ok`. |
