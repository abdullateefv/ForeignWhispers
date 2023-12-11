import os
import streamlit as st
import requests
import subprocess
import sys

def main():
    st.title("YouTube Video Translator")
    with st.sidebar:
        youtube_link = st.text_input("Enter YouTube Video Link")
        language_map = {
            "English": "en",
            "Spanish": "es",
            "French": "fr",
            "German": "de",
            "Japanese": "ja",
            "Chinese": "zh"
        }
        languages = list(language_map.keys())
        selected_language_name = st.selectbox("Select Language", languages)
        selected_language_code = language_map[selected_language_name]
        submit = st.button("Submit")

    if submit:
        selected_language = selected_language_code
        st.write(f"Selected Language Code: {selected_language}")

        # /downloadVideo
        st.write("Downloading Video...")
        response = getDownloadVideoService(youtube_link)
        if response.status_code == 200:
            title = response.json()['video_name'].replace(":", "")
            st.write(f"Downloading Video completed Successfully")
        else:
            st.error(f"\n****Error:****\n{response.json().get('error')}\n****Error:****\n")
            exit(1)

        # /translate-srt
        st.write("Translating .srt captions...")
        response = postTranslateSrtService(title, selected_language)
        if response.status_code == 200:
            st.write(f"Translating .srt captions completed Successfully")
        else:
            st.error(f"\n****Error:****\n{response.json().get('error')}\n****Error:****\n")
            exit(1)

        # /whisperTranscribe
        st.write("Transcribing audio using whisper")
        response = postWhisperTranscribeService(title)
        if response.status_code == 200:
            st.write(f"Transcribing audio using whisper completed Successfully")
        else:
            st.error(f"\n****Error:****\n{response.json().get('error')}\n****Error:****\n")
            exit(1)

        # /translate
        st.write("Translating transcription")
        response = postTranslateService(title, selected_language)
        if response.status_code == 200:
            st.write(f"Translating transcription completed successfully")
        else:
            st.error(f"\n****Error:****\n{response.json().get('error')}\n****Error:****\n")
            exit(1)

        # /text-to-speech
        st.write("Text to speeching")
        response = postTTSService(title, selected_language)
        if response.status_code == 200:
            st.write(f"Text to speeching completed successfully")
        else:
            st.error(f"\n****Error:****\n{response.json().get('error')}\n****Error:****\n")
            exit(1)

        # /generateVideo
        st.write("Generating video")
        response = getGenerateVideoService(title, selected_language)
        if response.status_code == 200:
            videoPath = response.json()['output_video_path']
            srtPath = response.json()['output_srt_path']
            st.write(f"Generating video completed successfully")

            # Display the video and subtitles
            st.video(videoPath)
            try:
                with open(srtPath, 'r') as file:
                    subtitles = file.read()
                    st.text_area("Subtitles", subtitles, height=300)
            except Exception as e:
                st.error(f"Error reading subtitle file: {e}")

        else:
            st.error(f"\n****Error:****\n{response.json().get('error')}\n****Error:****\n")
            exit(1)

def getDownloadVideoService(youtube_link):
    endpoint = "http://127.0.0.1:7864/downloadVideo"
    params = {"url": youtube_link}
    return requests.get(endpoint, params=params)

def postTranslateSrtService(title, target_lang):
    endpoint = "http://127.0.0.1:7864/translate-srt"
    params = {"transcript_srt_file": title,
              "target_lang": target_lang}
    return requests.post(endpoint, params=params)

def postWhisperTranscribeService(title):
    endpoint = "http://127.0.0.1:7864/whisperTranscribe"
    params = {"mp4Name": title}
    return requests.post(endpoint, params=params)

def postTranslateService(title, target_lang):
    endpoint = "http://127.0.0.1:7864/translate"
    params = {"transcript_file": title,
              "target_lang": target_lang}
    return requests.post(endpoint, params=params)

def postTTSService(title, target_lang):
    endpoint = "http://127.0.0.1:7864/text-to-speech"
    params = {"transcription": title,
              "target_lang": target_lang}
    return requests.post(endpoint, params=params)

def getGenerateVideoService(title, target_lang):
    endpoint = "http://127.0.0.1:7864/generateVideo"
    params = {"baseName": title,
              "language": target_lang}
    return requests.get(endpoint, params=params)

if __name__ == "__main__":
    current_directory = os.path.dirname(os.path.abspath(__file__))
    api_directory = os.path.join(current_directory, 'api')
    subprocess.Popen([sys.executable, "api.py"], cwd=api_directory)
    main()
