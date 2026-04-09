import os
from dotenv import load_dotenv
load_dotenv()

or_key = bool(os.environ.get('OPENROUTER_API_KEY',''))
paid = os.environ.get('OPENROUTER_PAID','')
openai_key = bool(os.environ.get('OPENAI_API_KEY',''))

groq_count = 0
primary = os.environ.get('GROQ_API_KEY','').strip()
if primary:
    groq_count += 1
for i in range(1, 8):
    k = os.environ.get(f'GROQ_API_KEY_{i}','').strip()
    if k:
        groq_count += 1

print(f'OpenRouter key : {or_key}')
print(f'Groq keys      : {groq_count}')
print(f'OPENROUTER_PAID: "{paid}" ({"ENABLED" if paid.lower() in ("true","1","yes") else "DISABLED"})')
print(f'OpenAI key     : {openai_key}')
print()
print('==> Free models ONLY' if paid.lower() not in ('true','1','yes') else '==> PAID models enabled')
