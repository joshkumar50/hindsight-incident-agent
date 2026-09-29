import os
from hindsight_client import Hindsight

c = Hindsight(
    base_url='https://memory.hindsight.vectorize.io',
    api_key=os.environ['HINDSIGHT_API_KEY']
)
r = c.recall(bank_id='incident-memory-bank', query='auth-service OOMKilled pod restart')
print(f'Got {len(r)} results')
for x in r[:3]:
    print(f'- {getattr(x, "content", x)[:120]}')
