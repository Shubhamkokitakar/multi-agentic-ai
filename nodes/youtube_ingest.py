# youtube_ingest.py

import os
import shutil

# ==========================================
# ADD FFMPEG TO PATH
# ==========================================

os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"

print("FFMPEG PATH:", shutil.which("ffmpeg"))
print("FFPROBE PATH:", shutil.which("ffprobe"))

# ==========================================
# IMPORTS
# ==========================================

import yt_dlp

from faster_whisper import WhisperModel


# ==========================================
# DOWNLOAD AUDIO
# ==========================================

def download_audio(url: str):

    ydl_opts = {

        "format": "bestaudio/best",

        "outtmpl": "audio.%(ext)s",

        "noplaylist": True,

        # avoids ffmpeg post-processing
        "quiet": False
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(
            url,
            download=True
        )

        file_name = ydl.prepare_filename(info)

    return file_name


# ==========================================
# TRANSCRIBE AUDIO
# ==========================================

def transcribe_audio(audio_file: str):

    print("\nLoading Faster Whisper Model...\n")

    model = WhisperModel(

        "small",

        device="cpu",

        compute_type="int8"
    )

    print("Transcribing Audio...\n")

    segments, info = model.transcribe(

        audio_file,

        beam_size=5
    )

    transcript = ""

    for segment in segments:

        transcript += segment.text + " "

    return transcript.strip()


# ==========================================
# MAIN FUNCTION
# ==========================================

def youtube_to_text(url: str):

    print("\nDownloading Audio...\n")

    audio_file = download_audio(url)

    print(f"\nDownloaded File: {audio_file}")

    transcript = transcribe_audio(audio_file)

    return transcript


# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":

    url = input("Enter YouTube URL: ")

    transcript = youtube_to_text(url)

    print("\n" + "=" * 60)
    print("TRANSCRIPT")
    print("=" * 60)

    print(transcript)