"""Configure Perplexica with Groq + OpenRouter and public SearxNG."""
import json
import os
import uuid

config_path = r"D:\Projects\perplexica\data\config.json"
config = json.load(open(config_path))

groq_key = os.getenv("GROQ_API_KEY", "")
or_key = os.getenv("OPENROUTER_API_KEY", "")

# Add Groq provider
groq_provider = {
    "id": str(uuid.uuid4()),
    "name": "Groq",
    "type": "groq",
    "chatModels": [],
    "embeddingModels": [],
    "config": {"apiKey": groq_key},
    "hash": "",
}

# Add OpenRouter via OpenAI provider
or_provider = {
    "id": str(uuid.uuid4()),
    "name": "OpenRouter",
    "type": "openai",
    "chatModels": [
        {"name": "grok-4.1-fast", "key": "x-ai/grok-4.1-fast"},
    ],
    "embeddingModels": [],
    "config": {
        "apiKey": or_key,
        "baseURL": "https://openrouter.ai/api/v1",
    },
    "hash": "",
}

# Check if already added
existing_types = [p.get("type", "") for p in config.get("modelProviders", [])]
if "groq" not in existing_types and groq_key:
    config["modelProviders"].append(groq_provider)
    print("Added Groq provider")
elif "groq" not in existing_types:
    print("Skipped Groq provider (missing GROQ_API_KEY)")
else:
    print("Groq already present")

if "openai" not in existing_types and or_key:
    config["modelProviders"].append(or_provider)
    print("Added OpenRouter (OpenAI-compatible) provider")
elif "openai" not in existing_types:
    print("Skipped OpenRouter provider (missing OPENROUTER_API_KEY)")
else:
    print("OpenAI/OpenRouter already present")

config["search"]["searxngURL"] = "https://search.sapti.me"
config["setupComplete"] = True

json.dump(config, open(config_path, "w"), indent=2)
print("Config updated. SearxNG URL set. setupComplete=True")

names = [p["name"] for p in config["modelProviders"]]
print(f"Providers: {names}")
