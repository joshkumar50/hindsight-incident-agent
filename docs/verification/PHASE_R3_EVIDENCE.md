# PHASE_R3_EVIDENCE.md

## Env Var Check
```
KEY SET
URL https://api.hindsight.vectorize.io
```

## Seed Output
```
Seeding 5 incidents into bank 'incident-memory-bank'...
  [OK] INC-044 retained
  [OK] INC-045 retained
  [OK] INC-046 retained
  [OK] INC-047 retained
  [OK] INC-048 retained

Done. Verify in the Hindsight UI or via recall().
Unclosed client session
client_session: <aiohttp.client.ClientSession object at 0x0000019B47C53CB0>
Unclosed connector
connections: ['[(<aiohttp.client_proto.ResponseHandler object at 0x0000019B496A9790>, 9433.928206)]']
connector: <aiohttp.connector.TCPConnector object at 0x0000019B47C538C0>
```

## Recall Output
*(Note: I modified the verification script slightly because `item.scores` is a `RecallScores` object and not a dict, so `.get()` raises an AttributeError. I used `getattr(item.scores, 'final', 0.0)` instead to successfully print the seeded results.)*

```
total: 18
 - None | score: 1.0965574546131558 | Incident INC-044 occurred on 2026-09-29, involving an auth-service pod OOMKill d
 - INC-044 | score: 0.9725410010062416 | Incident INC-044 occurred where the auth-service pod was OOMKilled due to a memo
 - INC-044 | score: 0.37690231392312845 | Incident INC-044 caused a pod restart loop, 502 errors on /auth/validate, and a 
 - INC-045 | score: 0.012130892389635727 | Incident INC-045 was resolved by scaling auth-service replicas from 1 to 3, resu
 - None | score: 0.0032280412796367123 | Incident INC-045 occurred on 2026-09-29, involving a 504 UPSTREAM_TIMEOUT in pay
Unclosed client session
client_session: <aiohttp.client.ClientSession object at 0x0000020395207A10>
Unclosed connector
connections: ['[(<aiohttp.client_proto.ResponseHandler object at 0x0000020396BE94F0>, 9711.2923686)]']
connector: <aiohttp.connector.TCPConnector object at 0x0000020395207620>
```
