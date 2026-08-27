import os
from dotenv import load_dotenv

# Load from .env file explicitly
env_path = os.path.join(os.getcwd(), '.env')
loaded = load_dotenv(env_path)

print(f".env loaded from {env_path}: {loaded}")
client_id = os.environ.get("CDSE_CLIENT_ID", "")
client_secret = os.environ.get("CDSE_CLIENT_SECRET", "")

print(f"CDSE_CLIENT_ID is present: {bool(client_id)}")
print(f"CDSE_CLIENT_ID length: {len(client_id)}")
print(f"CDSE_CLIENT_SECRET is present: {bool(client_secret)}")
print(f"CDSE_CLIENT_SECRET length: {len(client_secret)}")
