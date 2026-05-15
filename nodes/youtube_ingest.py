import yt_dlp
import whisper


def download_audio(url: str, output_path="audio.mp3"):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
        }]
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return output_path


def transcribe_audio(file_path: str):
    model = whisper.load_model("base")  # tiny/base/small/medium/large
    result = model.transcribe(file_path)
    return result["text"]


def youtube_to_text(url: str):
    audio_file = download_audio(url)
    text = transcribe_audio(audio_file)
    return text


if __name__ == "__main__":
    url = 'https://www.youtube.com/watch?v=sM7cWlX1yvQ'
    transcript = youtube_to_text(url)
    print(transcript[:1000])