import streamlit as st
import subprocess
import sys

def main():
    # Title of the app
    st.title("Youtube Video Language Selector")

    # Sidebar for input and options
    with st.sidebar:
        # Input for YouTube link
        youtube_link = st.text_input("Enter YouTube Video Link")

        # Dropdown for language selection
        languages = ["English", "Spanish", "French", "German", "Japanese", "Chinese"]
        selected_language = st.selectbox("Select Language", languages)

        # Submit button
        submit = st.button("Submit")

    # Displaying selected values on the right-hand side pane
    if submit:
        st.write("### Selected Values")
        st.write("YouTube Video Link: ", youtube_link)
        st.write("Selected Language: ", selected_language)

if __name__ == '__main__':
    subprocess.Popen([sys.executable, "api/api.py"])
    main()