# prescription_processing.py (Updated Version)
from openai import OpenAI
import base64
import requests
import json
import wave

def extract_prescription(image_file, api_key):
    client = OpenAI(api_key=api_key)
    # Read and encode the image
    encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

    # Extract details using OpenAI
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "You are a helpful chemist. Think of it as you are conversing with the user. Do NOT mention any details about the patient or the doctor. The user has just clicked a picture of the prescription and is now asking for advice on what all medicines do they have to take and when. When the user uploads a picture of their medical prescription you are to guide them on what all medicines have been prescribed to them and how they should be taking the medicines, as written in the prescription. For this you will 1. begin with the condition (if it mentioned) otherwise skip this step 2. begin explaining a) each of the medicines prescribed b) in what form (is it a syrup, tablet, powder, injection or something else) they need to be taken c) why this medicine was this recommended d) how does this medicine help e) dosage and frequency of dosage. In case any dosage is not clear let the user know and then suggest the best dosage practice for the condition of the patient as mentioned in the prescription. f) any precautions that the patient has been prescribed to take. Note: Also I want to use the output of this exercise and pass it along for text to speech conversion. Share the response in such a way that is a flowing conversation wherein each sentence flows into the next meaningfully and effortlessly and not abruptly. Construct your response to meet all of the above conditions. Important: As an example, if the prescription says use a medicine for 5-7 days mention it like so: 5 to 7 days instead of 5-7 days. Summarise within 1000 characters but do NOT leave out medicine related information."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_image}"}},
                ],
            }
        ],
    )
    extracted_text = response.choices[0].message.content
    print (extracted_text)

    # Clean the extracted text
    extracted_text_cleaned = extracted_text.replace("**", "").replace("#", "").replace("-", "").replace("\n", " ")
    extracted_text_cleaned = " ".join(extracted_text_cleaned.split())
    extracted_text_truncated = extracted_text_cleaned[:500]
    return extracted_text_truncated

def translate_to_hindi(text, api_key):
    SARVAM_TRANSLATE_URL = "https://api.sarvam.ai/translate"
    translate_payload = {
        "enable_preprocessing": True,
        "input": text,
        "source_language_code": "en-IN",
        "target_language_code": "hi-IN",
        "mode": "classic-colloquial"
    }
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }
    translate_response = requests.post(SARVAM_TRANSLATE_URL, json=translate_payload, headers=headers)
    hindi_text = translate_response.json().get("translated_text", "Translation failed")
    print (hindi_text)
    return hindi_text

def split_text_meaningfully(text, max_length=500):
    chunks = []
    current_chunk = ""
    sentences = text.split(". ")  # Split by sentence (period + space)

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_length:
            if current_chunk:
                current_chunk += ". " + sentence
            else:
                current_chunk = sentence
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


"""
def text_to_speech(text, api_key, output_file="output.wav"):
    # Clean the text
    text_cleaned = text.replace("**", "").replace("#", "").replace("-", "").replace("\n", " ")
    text_cleaned = " ".join(text_cleaned.split())
    with open("cleaned_prescription_hindi.txt", "w", encoding="utf-8") as file:
        file.write(text_cleaned)

    # Split the text into chunks
    text_chunks = split_text_meaningfully(text_cleaned, max_length=500)
    print(f"Text chunks: {text_chunks}")  # Debug: Check input

    # API call
    url = "https://api.sarvam.ai/text-to-speech"
    payload = {
        "speaker": "meera",
        "loudness": 1,
        "speech_sample_rate": 22050,
        "enable_preprocessing": True,
        "override_triplets": {},
        "target_language_code": "hi-IN",
        "inputs": text_chunks,
        "pitch": 0.5,
        "pace": 1,
        "model": "bulbul:v1"
    }
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")  # Debug: HTTP status
        print(f"Response Text: {response.text}")      # Debug: Full response
        response.raise_for_status()  # Raises exception for 4xx/5xx
        response_data = json.loads(response.text)
    except requests.RequestException as e:
        return False, f"Request failed: {str(e)}"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON response: {str(e)}"

    if "audios" not in response_data:
        return False, f"API response missing audio data: {response.text}"

    audio_base64_list = response_data["audios"]
    print(f"Audio base64 list length: {len(audio_base64_list)}")  # Debug: Check audio data
    audio_data_list = []
    for i, audio_base64 in enumerate(audio_base64_list):
        audio_base64 = audio_base64.strip()
        missing_padding = len(audio_base64) % 4
        if missing_padding:
            audio_base64 += "=" * (4 - missing_padding)
        audio_data = base64.b64decode(audio_base64)
        audio_data_list.append(audio_data)

    combined_audio_data = b"".join(audio_data_list)
    with wave.open(output_file, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(combined_audio_data)

    return True, "Audio generated successfully"
"""


def text_to_speech(text, api_key, output_file="output.wav"):
    # Clean the text
    text_cleaned = text.replace("**", "").replace("#", "").replace("-", "").replace("\n", " ")
    text_cleaned = " ".join(text_cleaned.split())

    # Save the cleaned text for debugging
    with open("cleaned_prescription_hindi.txt", "w", encoding="utf-8") as file:
        file.write(text_cleaned)

    # Split the text into chunks for TTS
    text_chunks = split_text_meaningfully(text_cleaned, max_length=500)

    # Generate audio using Sarvam TTS
    url = "https://api.sarvam.ai/text-to-speech"
    payload = {
        "speaker": "meera",
        "loudness": 1,
        "speech_sample_rate": 22050,
        "enable_preprocessing": True,
        "override_triplets": {},
        "target_language_code": "hi-IN",
        "inputs": text_chunks,
        "pitch": 0.5,
        "pace": 1,
        "model": "bulbul:v1"
    }
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    response_data = json.loads(response.text)

    if response.status_code != 200:
        return False, f"TTS API call failed: {response_data.get('message', 'No message')}"
    
    audio_base64_list = response_data["audios"]
    audio_data_list = []
    for i, audio_base64 in enumerate(audio_base64_list):
        audio_base64 = audio_base64.strip()
        missing_padding = len(audio_base64) % 4
        if missing_padding:
            audio_base64 += "=" * (4 - missing_padding)
        audio_data = base64.b64decode(audio_base64)
        audio_data_list.append(audio_data)

    # Combine audio data
    combined_audio_data = b"".join(audio_data_list)
    with wave.open(output_file, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(combined_audio_data)

    return True, "Audio generated successfully."