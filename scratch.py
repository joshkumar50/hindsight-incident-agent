import re

file_path = 'platform/dashboard-bff/main.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'_fallback_memory\s*=\s*\[[\s\S]*?\]\n+', '', content)

new_func = '''@app.get("/api/memory/bank")
async def get_memory_bank():
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.get(f"{BACKEND_BASE_URL}/memory/bank")
            if resp.status_code == 200:
                return resp.json()
            return {"bank_id": "hindsight-incident-agent", 
                    "total_memories": 0, "memories": []}
        except Exception as e:
            logger.error(f"memory_bank_unreachable: {e}")
            return {"bank_id": "hindsight-incident-agent",
                    "total_memories": 0, "memories": []}'''

content = re.sub(r'@app\.get\("/api/memory/bank"\)\s*async def get_memory_bank\(\):[\s\S]*?return {"bank_id": "error", "total_memories": 0, "memories": \[\]}', new_func, content)

with open(file_path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)
