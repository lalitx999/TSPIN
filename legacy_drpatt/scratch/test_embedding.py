import urllib.request
import json
import os
import ssl

env_path = '/Users/tanchonl/Downloads/drpatt/backend/.env'
api_key = ""
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith("GOOGLE_AI_API_KEY="):
                api_key = line.split("=", 1)[1].strip()

def test_model(model_name):
    print(f"Testing model: {model_name}...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:embedContent?key={api_key}"
    payload = {
        "model": f"models/{model_name}",
        "content": {"parts": [{"text": "Hello world"}]}
    }
    headers = {"Content-Type": "application/json"}
    context = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, context=context) as res:
            res_data = json.loads(res.read().decode('utf-8'))
            dims = len(res_data.get('embedding', {}).get('values', []))
            print(f"✅ Success! Dimensions: {dims}")
            return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

test_model("text-embedding-004")
test_model("gemini-embedding-001")
