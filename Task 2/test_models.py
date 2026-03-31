import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("Dostępne modele wspierające generateContent:\n")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
