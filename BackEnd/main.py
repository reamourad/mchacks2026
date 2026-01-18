from dotenv import load_dotenv
import os
import sys
from google import genai
from google.genai import types
from audio_transcriber import *

# Load environment variables from .env file
load_dotenv()

# Set up Gemini API
# api_key = os.getenv('GEMINI_API_KEY')

if __name__ == "__main__":
    # audio = "./BackEnd/voiceover.m4a"

    prompt_path = "./BackEnd/system_prompt.txt"
    # client = genai.Client()

    context = ''
    with open(prompt_path, "r", encoding="utf-8") as f:
        context = f.read()

    # config=types.GenerateContentConfig(
    #     system_instruction=context, 
    #     temperature=0.0,
    #     )

    # # transcribe_audio(audio,config)

    # script_path = "./BackEnd/voice_script.txt"
    # voice_w_script = "./BackEnd/voice.m4a"

    # data = transcribe_audio(client,voice_w_script,config, script_path)
    # # transcribe_audio(client,voice_w_script,config)

    # # voice_2_speakers = "./BackEnd/voice_2_speakers.m4a"

    # # data = transcribe_audio(client,voice_2_speakers,config)

    # script_to_json(data)

    # response = client.models.generate_content(
    # model="gemini-3-flash",
    # contents=[
    #     "Transcribe this audio word-for-word with speaker labels and timestamps.",
    #     voice_w_script
    # ]
    # )

    client = genai.Client()

    # Setup your system instruction and other configs
    config = types.GenerateContentConfig(
        system_instruction=context,
        temperature=0.2, # Low temperature is better for accurate transcription
    )

    # Upload your audio
    myfile = client.files.upload(file='./BackEnd/10sec.m4a')

    # Call the model with the config
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=['Transcribe this audio.', myfile],
        config=config # Pass the config here
    )

    print(response.text)
    data = script_to_json(response.text)
    