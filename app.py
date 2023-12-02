import streamlit as st
import requests
import subprocess
import sys

def main():
    st.title("YouTube Video Translator")

    with st.sidebar:
        youtube_link = st.text_input("Enter YouTube Video Link")
        languages = ["English", "Spanish", "French", "German", "Japanese", "Chinese"]
        selected_language = st.selectbox("Select Language", languages)
        submit = st.button("Submit")

    if submit:
        response = getVideoService(youtube_link)
        if response.status_code == 200:
            data = response.json()
            st.write("### Results")
            st.write("**YouTube Video Name:**", data['video_name'])
            st.write("**YouTube Video Link:**", youtube_link)
            st.write("**Selected Language:**", selected_language)
            st.write("**Transcript**")
            st.write(open(data['caption_path'], 'r').read())
        else:
            st.error(f"\n****Error:****\n{response.json().get('error')}\n****Error:****\n")



def getVideoService(youtube_link):
    endpoint = "http://127.0.0.1:7864/downloadVideo"
    params = {"url": youtube_link}
    return requests.get(endpoint, params=params)

def postWhisperTranscribe(mp4Name):
    endpoint = "http://127.0.0.1:7864/whisperTranscribe"
    params = {"mp4Name": mp4Name}
    return requests.post(endpoint, params=params)

if __name__ == "__main__":
    subprocess.Popen([sys.executable, "api/api.py"])
    main()
