import csv
import math
import os
import shutil
import subprocess
import tempfile
import yt_dlp
path= r"videos"
path2=r"audio"


def ffmpeg_available():
    return shutil.which("ffmpeg") is not None


def cookie_options():
    cookie_file = os.environ.get(
        "YTDLP_COOKIE_FILE",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt"),
    )
    if os.path.isfile(cookie_file):
        return {'cookiefile': cookie_file}
    if "YTDLP_COOKIE_FILE" in os.environ:
        raise FileNotFoundError(f"Cookie file not found: {cookie_file}")
    return {}


def download_video(url,path):
    has_ffmpeg = ffmpeg_available()
    os.makedirs(path, exist_ok=True)
    if not has_ffmpeg:
        print("FFmpeg not found; using a single-file video and saving the thumbnail separately.")

    ydl_opts = {
        # output title s ext s -> '%(title)s.%(ext)s'

        'outtmpl': os.path.join(path, '%(title)s.%(ext)s'),

        'format': (
            'bestvideo[height<=2160][vcodec^=avc1]+bestaudio[ext=m4a]/best[height<=2160]'
            if has_ffmpeg else 'best[height<=720][ext=mp4]/best[height<=720]/best'
        ),

        **cookie_options(),

        'writethumbnail': True,

        'postprocessors': [
            {
                'key': 'FFmpegMetadata',
                'add_metadata': True,
            },
            {
                'key': 'EmbedThumbnail',
                'already_have_thumbnail': False,
            },
        ] if has_ffmpeg else [],
    }
    if has_ffmpeg:
        ydl_opts['merge_output_format'] = 'mp4'

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def trim_audio_from_start(audio_path, seconds):
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError("FFmpeg is required to trim audio.")
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError("Trim duration must be a finite, non-negative number.")
    if seconds == 0:
        return

    directory = os.path.dirname(audio_path)
    temp_file = tempfile.NamedTemporaryFile(
        suffix=".mp3",
        dir=directory or None,
        delete=False,
    )
    temp_path = temp_file.name
    temp_file.close()

    try:
        subprocess.run(
            [
                ffmpeg_path,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                audio_path,
                "-ss",
                str(seconds),
                "-map",
                "0:a:0",
                "-map",
                "0:v?",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "320k",
                "-c:v",
                "copy",
                "-map_metadata",
                "0",
                temp_path,
            ],
            check=True,
        )
        os.replace(temp_path, audio_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def download_audio(url, paths, embed_thumbnail=True, trim_start_seconds=None):
    has_ffmpeg = ffmpeg_available()
    if trim_start_seconds is not None:
        if not has_ffmpeg:
            raise RuntimeError("FFmpeg is required to trim audio.")
        if not math.isfinite(trim_start_seconds) or trim_start_seconds < 0:
            raise ValueError("Trim duration must be a finite, non-negative number.")

    os.makedirs(paths, exist_ok=True)
    postprocessors = []
    if has_ffmpeg:
        postprocessors.extend([
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            },
            {
                'key': 'FFmpegMetadata',
                'add_metadata': True,
            },
        ])
        if embed_thumbnail:
            postprocessors.append({
                'key': 'EmbedThumbnail',
                'already_have_thumbnail': False,
            })
    else:
        print("FFmpeg not found; keeping the original audio format and saving the thumbnail separately.")

    ydl_opts = {
        # 設定輸出路徑與檔名格式
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        },
        **cookie_options(),

        'outtmpl': os.path.join(paths, '%(title)s.%(ext)s'),

        # Convert to MP3 when FFmpeg is installed; otherwise keep the source audio format.
        'format': 'bestaudio/best',

        'writethumbnail': embed_thumbnail,

        'postprocessors': postprocessors,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    if trim_start_seconds is not None and trim_start_seconds > 0:
        audio_path = dict(info).get("filepath")
        if not audio_path:
            raise RuntimeError("yt-dlp did not report the downloaded audio file path.")
        trim_audio_from_start(audio_path, trim_start_seconds)


def remove_line(file_path, line_to_remove):
    with open(file_path, "r", encoding="utf-8-sig") as file:
        lines = file.readlines()

    for index, line in enumerate(lines):
        if line.strip() == line_to_remove.strip():
            del lines[index]
            with open(file_path, "w", encoding="utf-8") as file:
                file.writelines(lines)
            return

    raise ValueError(f"Line not found in {file_path}: {line_to_remove}")


opt=input('opt')

if opt=='1':
    video_url = input("Enter the video URL: ")
    download_video(video_url, path)
#https://www.youtube.com/watch?v=pytdWKT-NV4&list=PLRBp0Fe2GpgkDw2aMG2lM5heA8cbLvOoN

elif opt=='2':
    audio_url = input("Enter the audio URL: ")
    download_audio(audio_url, path2)
elif opt=='3':
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ls.txt")

    with open(file_path, "r", encoding="utf-8-sig") as file:
        lines = file.readlines()

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue

        row = next(csv.reader([line]))
        if [column.strip().lower() for column in row] == ["link", "seconds"]:
            continue
        if len(row) not in (1, 2):
            raise ValueError(
                f"Invalid ls.txt row {line_number}: expected link or link,seconds."
            )

        audio_url = row[0].strip()
        if not audio_url:
            raise ValueError(f"Invalid ls.txt row {line_number}: link is empty.")
        trim_seconds = None
        if len(row) == 2:
            seconds_text = row[1].strip()
            try:
                trim_seconds = float(seconds_text)
            except ValueError as error:
                raise ValueError(
                    f"Invalid seconds value on ls.txt row {line_number}: "
                    f"{seconds_text!r}"
                ) from error
            if not math.isfinite(trim_seconds) or trim_seconds < 0:
                raise ValueError(
                    f"Invalid seconds value on ls.txt row {line_number}: "
                    "expected a finite, non-negative number."
                )

        download_audio(
            audio_url,
            path2,
            embed_thumbnail=True,
            trim_start_seconds=trim_seconds,
        )
        remove_line(file_path, line)