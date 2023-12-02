from flask import Flask, jsonify, request
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from moviepy.editor import VideoFileClip
import os
import whisper
import torch
from gtts import gTTS

app = Flask(__name__)
model = whisper.load_model("base")

def translate_text(text, target_lang):
    # Load the target language model dynamically
    target_model = torch.hub.load('pytorch/fairseq', f'transformer.wmt16.en-{target_lang}', tokenizer='moses',
                                  bpe='subword_nmt')
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
    video_file_path = video.download(output_path=os.path.join(base_path, '../cs370-project/api/videos'))

    # Define the path for the caption file in the 'transcripts' directory
    caption_file_name = os.path.basename(video_file_path)[:-4]
    caption_file_path = os.path.join(base_path, '../cs370-project/api/transcripts', caption_file_name)

    # Download transcripts
    srt = YouTubeTranscriptApi.get_transcript(request.args.get('url')[-11:])
    with open(caption_file_path + '.srt', 'w') as file:
        file.write(str(srt))

    # Return download file paths
    return jsonify({
        'video_path': video_file_path,
        'caption_path': caption_file_path + ".srt"
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
        return jsonify({'error': 'mp4 file does not exist'}), 404

    # Construct mp3 path
    audio_path = os.path.join('audios', f"{mp4Name}.mp3")

    # Convert mp4 to mp3 and transcribe
    try:
        video_clip = VideoFileClip(mp4_path)
        video_clip.audio.write_audiofile(audio_path)
        video_clip.close()

        # Transcribe the audio file
        result = model.transcribe(audio_path)

        # Path for the transcripts file
        transcript_path = os.path.join('whisperTranscripts', f"{mp4Name}.txt")

        # Write the transcripts to a file
        with open(transcript_path, "w") as transcript_file:
            transcript_file.write(result["text"])

    except Exception as e:
        # Handle the exception and return an error message
        return jsonify({'error': str(e)}), 500

    # Return the path to the transcripts file
    return jsonify({
        'whisperTranscript_path': transcript_path,
    })

# POST /translate?transcription=:transciptionName&target_lang=targetLanguage
@app.route('/translate', methods=['POST'])
def translate_text():
    transcription = request.args.get('transcription')
    target_lang = request.args.get('target_lang')

    try:
        data = transcription.get_json()

        # Process the provided .srt-like data
        translated_data = process_srt(data, target_lang)

        # Save the translated data to a new .srt file
        translated_transcript_path = os.path.join('translatedTranscripts',
                                                  '{transcription}.{target_lang}.translated.srt')

        # Write the translated transcripts to a file
        with open(translated_transcript_path, "w") as transcript_file:
            transcript_file.write(translated_data)

    except Exception as e:
        return jsonify({'error': str(e)})

    return jsonify({
        'translatedTranscripts_path': translated_transcript_path,
    })

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
    app.run()