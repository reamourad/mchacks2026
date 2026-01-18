from dotenv import load_dotenv
import os
from google import genai
from google.genai import types
import json

def transcribe_audio(client,audio: str, config: types.GenerateContentConfig, init_transript: str = None) -> str:
    
    audio_file = client.files.upload(file=audio)

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        config=config,
        contents=[
            audio_file,
            "transcribe the above audio file into text"
        ],
    
    )

    output = response.text
    print(output)
    return output

def script_to_json(script: str):
    filename = "output_json.json"

    cleaned_str = (script
                   .replace("```json", "")
                   .replace("```", "")
                   .replace("'''json", "")
                   .replace("'''", "")
                   .strip())
    
    try:
        data = json.loads(cleaned_str)
        # Open the file in write mode ('w') and use json.dump()
        with open(filename, 'w') as json_file:
            json.dump(data, json_file, indent=4)
        return data
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        # If the LLM output was cut off (like your snippet), 
        # it might need manual closing brackets to be valid.
        return None


