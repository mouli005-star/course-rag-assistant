from openai import OpenAI

from config import get_openai_api_key, warn_python_compatibility

warn_python_compatibility()
client = OpenAI(api_key=get_openai_api_key(required=True))

response = client.responses.create(
    model="gpt-4.1-mini",
    input="age of the india man who lived in himalayas"
)

print(response.output_text)