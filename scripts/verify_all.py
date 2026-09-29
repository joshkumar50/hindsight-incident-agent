import urllib.request, json

print("========== DASHBOARD ==========")
d = json.loads(urllib.request.urlopen("http://localhost:58663/api/dashboard").read().decode())
print(json.dumps(d, indent=2))

print()
print("========== INCIDENTS ==========")
d = json.loads(urllib.request.urlopen("http://localhost:58663/api/incidents").read().decode())
for inc in d:
    print(f"  {inc['id']} | {inc['root_cause']:20s} | {inc['status']:15s} | severity={inc['severity']}")
print(f"  Total: {len(d)} incidents")

print()
print("========== RECOVERY ==========")
d = json.loads(urllib.request.urlopen("http://localhost:58663/api/recovery").read().decode())
print(json.dumps(d, indent=2))

print()
print("========== AUDIT ==========")
d = json.loads(urllib.request.urlopen("http://localhost:58663/api/audit").read().decode())
print(f"  Total audit logs: {len(d)}")
if d:
    for log in d[:3]:
        print(f"  {log.get('timestamp')} | {log.get('event_type')} | {log.get('incident_id')} | decision={log.get('decision')}")

print()
print("========== OBSERVABILITY ==========")
d = json.loads(urllib.request.urlopen("http://localhost:58663/api/observability").read().decode())
print(f"  RPS={d.get('requests_per_second')}, Latency={d.get('avg_latency_ms')}ms, Error Rate={d.get('error_rate')}")
print(f"  Services: {len(d.get('services',[]))}")

print()
print("========== CLUSTER ==========")
d = json.loads(urllib.request.urlopen("http://localhost:58663/api/cluster").read().decode())
print(f"  Nodes={d.get('total_nodes')}, Pods={d.get('total_pods')}, Deployments={d.get('deployments')}")
