_fallback_memory = {
    "INC-1": {
        "incident_id": "INC-1",
        "symptoms": "High CPU utilization on auth-service",
        "root_cause": "Hash calculation loop bug under concurrent load",
        "playbook": ["Scale up auth-service replicas", "Rollback to previous stable image"],
        "success_rate": 0.95,
        "outcome": "success",
        "human_approved": True
    },
    "INC-2": {
        "incident_id": "INC-2",
        "symptoms": "500 errors from payment-service",
        "root_cause": "Database connection pool exhaustion",
        "playbook": ["Increase connection pool size to 50", "Restart payment-service pods"],
        "success_rate": 0.88,
        "outcome": "human_modified",
        "human_approved": True
    },
    "INC-3": {
        "incident_id": "INC-3",
        "symptoms": "Inventory service timeouts",
        "root_cause": "Redis cache eviction policy causing thrashing",
        "playbook": ["Change maxmemory-policy to allkeys-lru", "Flush Redis cache"],
        "success_rate": 0.76,
        "outcome": "success",
        "human_approved": False
    },
    "INC-4": {
        "incident_id": "INC-4",
        "symptoms": "Order service missing events",
        "root_cause": "Kafka consumer group rebalancing constantly",
        "playbook": ["Increase session.timeout.ms", "Check network stability"],
        "success_rate": 0.92,
        "outcome": "success",
        "human_approved": True
    },
    "INC-5": {
        "incident_id": "INC-5",
        "symptoms": "Frontend loading slow",
        "root_cause": "Large uncompressed assets deployed",
        "playbook": ["Enable gzip compression on Nginx", "Re-run asset optimization pipeline"],
        "success_rate": 0.99,
        "outcome": "human_validated",
        "human_approved": True
    }
}

def get_all_memories() -> list[dict]:
    return list(_fallback_memory.values())
