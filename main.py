import os
from google.cloud import speech, translate_v2 as translate, storage, texttospeech
from pydub import AudioSegment

# Set up Google Cloud credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'agile-sanctum-442220-v0-9a3a1e83611f.json'

# Initialize clients for speech recognition, translation, text-to-speech, and storage
speech_client = speech.SpeechClient()
translate_client = translate.Client()
tts_client = texttospeech.TextToSpeechClient()
storage_client = storage.Client()

# Function to preprocess audio
def preprocess_audio(gcs_uri, output_path="processed_audio.wav"):
    try:
        # Parse the GCS URI
        if gcs_uri.startswith("gs://"):
            bucket_name, file_path = gcs_uri[5:].split("/", 1)
        else:
            raise ValueError("Invalid GCS URI format")

        # Download the audio file locally
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        local_file_path = "temp_audio.wav"
        blob.download_to_filename(local_file_path)
        print(f"Audio downloaded from GCS: {local_file_path}")

        # Load the audio file with pydub
        audio = AudioSegment.from_file(local_file_path)
        
        # Convert to LINEAR16, 16 kHz, mono
        audio = audio.set_frame_rate(16000).set_channels(1)

        # Export processed audio
        audio.export(output_path, format="wav", codec="pcm_s16le")
        print(f"Audio processed and saved as: {output_path}")

        # Clean up the temporary file
        os.remove(local_file_path)
        return output_path

    except Exception as e:
        print(f"Error in preprocessing: {e}")
        raise

# Main workflow
def main():
    # Input GCS URI
    audio_uri = "gs://audiofilesbuckethahaha/OSR_in_000_0062_16k.wav"

    # Preprocess the audio
    print("Preprocessing audio...")
    processed_audio_path = preprocess_audio(audio_uri)

    # Create the RecognitionAudio object from the preprocessed file
    with open(processed_audio_path, "rb") as audio_file:
        content = audio_file.read()
    audio = speech.RecognitionAudio(content=content)

    # Audio configuration for speech recognition
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="hi-IN",
    )

    print("Starting audio processing...")
    try:
        # Perform speech-to-text
        operation = speech_client.long_running_recognize(config=config, audio=audio)
        print("Processing... Please wait.")
        response = operation.result(timeout=90)

        # Extract transcript
        transcript = ""
        for result in response.results:
            sentence = result.alternatives[0].transcript
            print("Original Transcript: ", sentence)
            transcript += sentence + ". "

        # Save original transcript
        with open("original_transcript.txt", "w", encoding="utf-8") as f:
            f.write(transcript)
        print("Original transcript saved as 'original_transcript.txt'.")

        # Translate to English
        translation = translate_client.translate(transcript, target_language='en')
        translated_text = translation['translatedText']
        print("Translated Text: ", translated_text)

        # Save translated transcript
        with open("translated_transcript.txt", "w", encoding="utf-8") as f:
            f.write(translated_text)
        print("Translated transcript saved as 'translated_transcript.txt'.")

        # Perform text-to-speech
        synthesis_input = texttospeech.SynthesisInput(text=translated_text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

        tts_response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # Save translated audio
        with open("translated_audio.mp3", "wb") as out:
            out.write(tts_response.audio_content)
        print("Generated audio saved as 'translated_audio.mp3'.")

    except Exception as e:
        print(f"Error occurred: {e}")

    finally:
        # Clean up the processed audio file
        if os.path.exists(processed_audio_path):
            os.remove(processed_audio_path)
            print(f"Cleaned up temporary file: {processed_audio_path}")

# Run the main function
if __name__ == "__main__":
    main()
