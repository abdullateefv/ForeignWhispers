import traceback
from gtts import gTTS
from flask import Flask, jsonify, request
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from moviepy.editor import VideoFileClip, AudioFileClip
import os
import whisper
import argostranslate.package
import argostranslate.translate
import chardet
import re

app = Flask(__name__)
model = whisper.load_model("base")

@app.route('/downloadVideo', methods=['GET'])
def download_video():
    # Get URL arg
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    # Create video obj
    yt = YouTube(url)
    video = yt.streams.filter(progressive=True, file_extension='mp4').first()

    if not video:
        return jsonify({'error': 'No video found'}), 404

    # Set up paths
    base_path = os.path.dirname(os.path.abspath(__file__))
    video_file_path = video.download(output_path=os.path.join(base_path, 'videos'))

    # Define the path for the caption file in the 'srts' directory
    caption_file_name = os.path.basename(video_file_path)[:-4]
    caption_file_path = os.path.join(base_path, 'srts', caption_file_name)

    # Download srts
    srt = YouTubeTranscriptApi.get_transcript(request.args.get('url')[-11:])
    with open(caption_file_path + '.srt', 'w') as file:
        file.write(str(srt))

    # Return download file paths
    return jsonify({
        'video_name': video.title,
        'video_path': video_file_path,
        'caption_path': caption_file_path + ".srt"
    })

def translate(transcript_path, target_lang):
    with open(transcript_path, 'rb') as file:
        binary_data = file.read()

    # handle errors
    text = binary_data.decode("utf-8", errors="replace")

    # Download and install Argos Translate package
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    package_to_install = next(
        filter(
            lambda x: x.from_code == "en" and x.to_code == target_lang, available_packages
        )
    )
    argostranslate.package.install_from_path(package_to_install.download())

    # Translate the input text using the target language model
    translated_text = argostranslate.translate.translate(text, "en", target_lang)
    return translated_text

def translate_srt(transcript_srt_path, target_lang):
    # Read the input SRT file
    with open(transcript_srt_path, 'rb') as file:
        binary_data = file.read()

    # handle errors
    srt_data = eval(binary_data.decode("utf-8", errors="replace"))

    # Download and install Argos Translate package
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    package_to_install = next(
        filter(
            lambda x: x.from_code == "en" and x.to_code == target_lang, available_packages
        )
    )
    argostranslate.package.install_from_path(package_to_install.download())

    # Translate each subtitle text
    for subtitle in srt_data:
        text = subtitle['text']
        translated_text = argostranslate.translate.translate(text, "en", target_lang)
        subtitle['text'] = translated_text

    # Convert the translated SRT data to a string
    translated_srt = str(srt_data)

    return translated_srt

def convert_to_srt(input_file_path, output_file_path):
    # Read the input file
    with open(input_file_path, 'r', encoding='ISO-8859-1') as file:
        content = file.read()

    # Function to convert time in seconds to SRT time format
    def seconds_to_srt_time(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        return f"{hours:02}:{minutes:02}:{int(seconds):02},{milliseconds:03}"

    # Parse each subtitle entry
    entries = re.findall(r"\{.*?\}", content)
    subtitles = []
    for entry in entries:
        text_match = re.search(r"'text': '(.*?)'", entry)
        start_match = re.search(r"'start': (\d+\.\d+)", entry)
        duration_match = re.search(r"'duration': (\d+\.\d+)", entry)
        if text_match and start_match and duration_match:
            subtitles.append({
                'text': text_match.group(1),
                'start': float(start_match.group(1)),
                'duration': float(duration_match.group(1))
            })

    # Convert to standard SRT format
    srt_formatted = ""
    for i, subtitle in enumerate(subtitles):
        start_time = seconds_to_srt_time(subtitle['start'])
        end_time = seconds_to_srt_time(subtitle['start'] + subtitle['duration'])
        srt_formatted += f"{i+1}\n{start_time} --> {end_time}\n{subtitle['text']}\n\n"

    # Write to file or return as string
    if output_file_path:
        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.write(srt_formatted)
    else:
        return srt_formatted

@app.route('/translate-srt', methods=['POST'])
def translate_srt_handler():
    transcript_fname = request.args.get('transcript_srt_file')
    target_lang = request.args.get('target_lang')

    try:
        transcript_path = os.path.join('srts', f'{transcript_fname}.srt')
        translated_srt_transcript = translate_srt(transcript_path, target_lang)
        translated_srt_transcript_path = os.path.join('translatedSrts', f'{transcript_fname}.{target_lang}.translated.srt')

        with open(translated_srt_transcript_path, "w") as translated_transcript_fname:
            translated_transcript_fname.write(translated_srt_transcript)

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

    return jsonify({
        'translated_srt_transcript_path': translated_srt_transcript_path,
    })

@app.route('/whisperTranscribe', methods=['POST'])
def whisper_transcribe():
    # Get URL arg
    mp4Name = request.args.get('mp4Name')

    if not mp4Name:
        return jsonify({'error': 'mp4Name is required'}), 400

    # Construct mp4 path
    mp4_path = os.path.join('videos', f"{mp4Name}.mp4")

    # Check if mp4 file exists
    if not os.path.exists(mp4_path):
        return jsonify({'error': 'mp4 file does not exist at ' + mp4_path}), 404

    # Construct mp3 path
    audio_path = os.path.join('audios', f"{mp4Name}.mp3")

    try:
        video_clip = VideoFileClip(mp4_path)
        video_clip.audio.write_audiofile(audio_path)
        video_clip.close()

        # Transcribe the audio file
        if not os.path.exists(audio_path):
            return jsonify({'error': 'mp3 file does not exist at ' + audio_path}), 404
        else:
            print("mp3 file does exist at " + audio_path)
        result = model.transcribe(audio_path)

        # Path for the srts file
        transcript_path = os.path.join('whisperTranscripts', f"{mp4Name}.txt")

        # Write the srts to a file
        with open(transcript_path, "w") as transcript_file:
            transcript_file.write(result["text"])

    except Exception as e:
        error_string = traceback.format_exc()
        print(error_string)
        return jsonify({'error': str(e)}), 500

    # Return the path to the srts file
    return jsonify({
        'whisperTranscript_path': transcript_path,
    })

@app.route('/translate', methods=['POST'])
def translate_text():
    transcript_fname = request.args.get('transcript_file')
    target_lang = request.args.get('target_lang')

    try:
        transcript_path = os.path.join('whisperTranscripts', f'{transcript_fname}.txt')
        translated_transcript = translate(transcript_path, target_lang)
        translated_transcript_path = os.path.join('translatedWhisperTranscripts', f'{transcript_fname}.{target_lang}.translated.txt')

        with open(translated_transcript_path, "w") as translated_transcript_fname:
            translated_transcript_fname.write(translated_transcript)

    except Exception as e:
        error_string = traceback.format_exc()
        print(error_string)
        return jsonify({'error': str(e)}), 500

    return jsonify({
        'translated_transcript_path': translated_transcript_path,
    })


@app.route('/text-to-speech', methods=['POST'])
def text_to_speech():
    transcription = request.args.get('transcription')
    target_lang = request.args.get('target_lang')

    # Construct file path for the transcript
    translated_transcript_path = os.path.join('translatedWhisperTranscripts', f'{transcription}.{target_lang}.translated.txt')

    # Check if the transcript file exists
    if not os.path.exists(translated_transcript_path):
        return "Transcript file not found at: " + translated_transcript_path, 404

    with open(translated_transcript_path, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']

    with open(translated_transcript_path, 'r', encoding=encoding) as file:
        text = file.read()

    # Convert text to speech
    tts = gTTS(text=text, lang=target_lang)

    # Create tts directory if it doesn't exist
    tts_dir = 'tts'
    if not os.path.exists(tts_dir):
        os.makedirs(tts_dir)

    # Save the speech file in tts directory
    output_file = os.path.join(tts_dir, f'{transcription}.{target_lang}.translated.mp3')
    tts.save(output_file)

    # Return the path to the speech file
    return jsonify({
        'tts_path': output_file,
    })

@app.route('/generateVideo', methods=['GET'])
def generate_video():
    # Get Args
    base_name = request.args.get('baseName')
    language = request.args.get('language')

    # Validate Args
    if not base_name:
        return jsonify({'error': 'baseName is required'}), 400
    elif not language:
        return jsonify({'error': 'language is required'}), 400
    print("Passed Validate Args")

    # Get input file handles
    video_path = os.path.join('videos', f'{base_name}.mp4')
    translated_audio_path = os.path.join('tts', f'{base_name}.{language}.translated.mp3')
    translated_srt_path = os.path.join('translatedSrts', f'{base_name}.{language}.translated.srt')
    print("Passed Get Input File Handles")

    # Get output file handle
    output_path = os.path.join('outputVideos', f'{base_name}.{language}.translated.mp4')
    print("Passed Get Output File Handle")

    # Check if input files exist at handles
    if not os.path.exists(video_path):
        return jsonify({'error': 'Video file does not exist'}), 404

    # Check if audio file exists
    if not os.path.exists(translated_audio_path):
        return jsonify({'error': 'Audio file does not exist'}), 404

    # Check if SRT file exists
    if not os.path.exists(translated_srt_path):
        return jsonify({'error': 'SRT file does not exist'}), 404

    print("Passed Check if Exists")

    try:
        # Replace audio
        video_clip = VideoFileClip(video_path)
        audio_clip = AudioFileClip(translated_audio_path)
        video_clip = video_clip.set_audio(audio_clip)
        video_clip.write_videofile(output_path, codec='libx264', audio_codec='aac')
        print("Passed write video file")

        # Convert SRT
        converted_srt_path = os.path.join('convertedSrts', f'{base_name}.{language}.translated.converted.srt')
        convert_to_srt(translated_srt_path, converted_srt_path)
        print("Passed convert SRT")

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

    current_directory = os.path.dirname(os.path.abspath(__file__))

    return jsonify({
        'output_video_path': os.path.join(current_directory, output_path),
        'output_srt_path': os.path.join(current_directory, converted_srt_path),
    })

if __name__ == "__main__":
    app.run(port=7864)