from flask import Flask, jsonify, request
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from moviepy.editor import VideoFileClip
import os
import whisper
import torch
from gtts import gTTS
import json

app = Flask(__name__)
model = whisper.load_model("base")

def translate_text(text, target_lang):
    # Load the target language model dynamically
    target_model = torch.hub.load('pytorch/fairseq', f'transformer.wmt16.en-{target_lang}', tokenizer='moses',bpe='subword_nmt')
    target_model.eval()
    target_model.cuda()

    # Translate the input text using the target language model
    translated_text = target_model.translate(text)
    return translated_text

def process_srt(data, target_lang):
    translated_data = []
    for item in data:
        text = item['text']
        translated_text = translate_text(text, target_lang)
        translated_item = {
            'text': translated_text,
            'start': item['start'],
            'duration': item['duration']
        }
        translated_data.append(translated_item)
    return translated_data

@app.route('/translate', methods=['GET'])
def translate():
    base_filename = request.args.get('base_filename')
    target_lang = request.args.get('target_lang')

    transcript_path = os.path.join('transcripts', f'{base_filename}.srt')
    translated_transcript_path = os.path.join('translatedTranscripts', f'{base_filename}.{target_lang}.translated.srt')


    # Read the transcript file
    with open(transcript_path, 'r') as file:
        data = json.load(file)

    # Process and translate the data
    translated_data = process_srt(data, target_lang)

    # Write the translated transcripts to a file
    with open(translated_transcript_path, "w") as transcript_file:
        for item in translated_data:
            transcript_file.write(f"{item['text']}\n")  # Adjust the format as needed for .srt files


    return jsonify({
        'translatedTranscriptPath': translated_transcript_path,
    })

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

    caption_file_name = os.path.basename(video_file_path)[:-4]
    caption_file_path = os.path.join(base_path, 'transcripts', caption_file_name)

    try:
        srt = YouTubeTranscriptApi.get_transcript(request.args.get('url')[-11:])
        transcript_content = str(srt)
        transcript_available = True
    except Exception as e:
        transcript_content = "Unavailable"
        transcript_available = False

    # Write to the caption file
    with open(caption_file_path + '.srt', 'w') as file:
        file.write(transcript_content)

    # Return download file paths
    return jsonify({
        'video_name': caption_file_name,
        'video_path': video_file_path,
        'caption_path': caption_file_path + ".srt",
        'transcript_available': transcript_available
    })

@app.route('/whisperTranscribe', methods=['GET'])
def transcribe():
    # Get the base filename from request
    base_filename = request.args.get('mp4Name')

    # Define file paths
    video_path = os.path.join('videos', f'{base_filename}.mp4')
    audio_path = os.path.join('audios', f'{base_filename}.mp3')
    transcript_path = os.path.join('whisperTranscripts', f'{base_filename}.txt')

    # Check if the video file exists
    if not os.path.exists(video_path):
        return jsonify({"error": "File not found"}), 404

    # Convert video to audio
    clip = VideoFileClip(video_path)
    clip.audio.write_audiofile(audio_path)

    # Transcribe the audio file
    model = whisper.load_model("base")  # You may choose a different model size
    result = model.transcribe(audio_path)

    # Save the transcript
    with open(transcript_path, 'w') as file:
        file.write(result["text"])

    # Return the path of the transcribed file
    return jsonify({"transcript_path": transcript_path})

@app.route('/text-to-speech', methods=['POST'])
def text_to_speech():
    transcription = request.args.get('transcription')
    target_lang = request.args.get('target_lang')

    # Construct file path for the transcript
    translated_transcript_path = os.path.join('translatedTranscripts', f'{transcription}.{target_lang}.translated.srt')

    # Check if the transcript file exists
    if not os.path.exists(translated_transcript_path):
        return "Transcript file not found", 404

    # Read the content of the transcript file
    with open(translated_transcript_path, 'r', encoding='utf-8') as file:
        text = file.read()

    # Convert text to speech
    tts = gTTS(text=text, lang=target_lang)

    # Create tts directory if it doesn't exist
    tts_dir = 'tts'
    if not os.path.exists(tts_dir):
        os.makedirs(tts_dir)

    # Save the speech file in tts directory
    output_file = os.path.join(tts_dir, f'{transcription}.{target_lang}.mp3')
    tts.save(output_file)

    # Return the path to the speech file
    return jsonify({
        'tts_path': output_file,
    })

if __name__ == "__main__":
    app.run(port=7864, debug=True)