from dotenv import load_dotenv
import os
from google import genai
from google.genai import types
# Load environment variables from .env file
load_dotenv()

# Set up Gemini API
api_key = os.getenv('GEMINI_2_0_FLASH_API_KEY')




def transcribe_audio(audio: str, config: types.GenerateContentConfig, init_transript: str = None) -> str:
    
    audio_file = client.files.upload(file=audio)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=config,
        contents=[
            audio_file,
            "transcribe the above audio file into text"
        ],
    
    )

    output = response.text
    print(output)
    return output

if __name__ == "__main__":
    audio = "./BackEnd/voiceover.m4a"

    prompt_path = "./BackEnd/system_prompt.txt"
    client = genai.Client()


    context = ''
    with open(prompt_path, "r", encoding="utf-8") as f:
        context = f.read()

    config=types.GenerateContentConfig(
                # This "sets up" the prompt at initiation
        system_instruction=context, 
        temperature=0.0,
        )

    transcribe_audio(audio,config)