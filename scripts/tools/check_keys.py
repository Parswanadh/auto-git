import dotenv; dotenv.load_dotenv()
import os
for k in ['GROQ_API_KEY','OPENROUTER_API_KEY','OPENAI_API_KEY','GITHUB_TOKEN']:
    v = os.getenv(k, '')
    print(f"{k}: {'YES ('+v[:8]+'...)' if v else 'NO'}")
