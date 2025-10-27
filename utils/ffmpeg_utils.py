import subprocess
import logging
import os
from typing import List, Tuple

logger = logging.getLogger(__name__)


def video_has_audio(video_path: str) -> bool:
    """
    Check if a video file has an audio stream using ffprobe

    Args:
        video_path: Path to video file

    Returns:
        True if video has audio, False otherwise
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_type",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        has_audio = result.stdout.strip() == "audio"
        logger.info(f"Video {video_path} has audio: {has_audio}")
        return has_audio
    except Exception as e:
        logger.warning(f"Could not check audio in {video_path}: {e}")
        return False


def get_video_duration(video_path: str) -> float:
    """
    Get the duration of a video file using ffprobe

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds, or 5.0 as fallback
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        logger.info(f"Video duration for {video_path}: {duration}s")
        return duration
    except Exception as e:
        logger.warning(f"Could not get duration for {video_path}: {e}")
        return 5.0


def format_time(seconds: float) -> str:
    """
    Format time in seconds to SRT timestamp format (HH:MM:SS,mmm)

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string
    """
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    milliseconds = int((secs - int(secs)) * 1000)

    return f"{int(hours):02}:{int(minutes):02}:{int(secs):02},{milliseconds:03}"


def write_srt(subtitles, max_words_per_line: int = 3) -> str:
    """
    Convert Whisper segments to SRT format with word limiting
    Args:
        subtitles: List of subtitle segments from Whisper
        max_words_per_line: Maximum words per subtitle line
    Returns:
        SRT formatted string
    """
    srt_output = []
    counter = 1
    for seg in subtitles:
        start = seg["start"]
        end = seg["end"]
        text = seg["text"].strip()
        words = text.split()
        duration = end - start
        if len(words) <= max_words_per_line:
            chunks = [text]
        else:
            chunks = []
            for i in range(0, len(words), max_words_per_line):
                chunk = " ".join(words[i:i + max_words_per_line])
                chunks.append(chunk)
        chunk_duration = duration / len(chunks)
        for idx, chunk in enumerate(chunks):
            chunk_start = start + (idx * chunk_duration)
            chunk_end = start + ((idx + 1) * chunk_duration)
            srt_output.append(
                f"{counter}\n{format_time(chunk_start)} --> {format_time(chunk_end)}\n{chunk}\n"
            )
            counter += 1
    return "\n".join(srt_output)


def burn_subtitles(video_path: str, srt_text: str, output_path: str, settings: dict = None) -> None:
    """
    Burn subtitles into video using FFmpeg with custom styling
    Args:
        video_path: Path to input video
        srt_text: SRT formatted subtitles
        output_path: Path for output video
        settings: Caption styling settings
    Raises:
        subprocess.CalledProcessError: If FFmpeg fails
    """
    # Default settings
    if settings is None:
        settings = {
            "shadow-color": "#000000",
            "max-words-per-line": 3,
            "font-size": 10,
            "shadow-offset": 0.3,
            "outline-color": "#000000",
            "word-color": "#FFFFFF",
            "outline-width": 0.5,
                "y": 50,  # vertical distance from bottom
            "font-family": "Montserrat-Bold",
            "bold": True
        }
    
    srt_path = video_path.replace(".mp4", "_temp.srt")
    try:
        with open(srt_path, "w", encoding="utf-8") as srt_file:
            srt_file.write(srt_text)
        logger.info(f"Burning subtitles into video: {video_path}")
        srt_path_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
        
        # Convert hex colors to ASS format (&H00BBGGRR)
        def hex_to_ass_color(hex_color):
            hex_color = hex_color.lstrip('#')
            r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
            return f"&H00{b}{g}{r}"
        
        primary_color = hex_to_ass_color(settings["word-color"])
        outline_color = hex_to_ass_color(settings["outline-color"])
        shadow_color = hex_to_ass_color(settings["shadow-color"])
        
        # Build subtitle filter with custom styling
        subtitle_filter = (
            f"subtitles={srt_path_escaped}:force_style='"
            f"FontName={settings['font-family']},"
            f"FontSize={settings['font-size']},"
            f"Bold=1,"
            f"PrimaryColour={primary_color},"
            f"OutlineColour={outline_color},"
            f"BackColour={shadow_color},"
            f"BorderStyle=1,"
            f"Outline={settings['outline-width']},"
            f"Shadow={settings['shadow-offset']},"
            f"Alignment=2,"  # bottom centre
            f"MarginV={int(settings['y'])}'" 
        )
        
        cmd = [
            "ffmpeg",
            "-y",
            "-threads", "0",
            "-i", video_path,
            "-vf", subtitle_filter,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-c:a", "copy",
            output_path
        ]
        logger.info(f"Running FFmpeg subtitle burn command...")
        logger.info(f"Subtitle filter: {subtitle_filter[:100]}...")
        logger.info(f"Full command: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        logger.info(f"FFmpeg completed with return code: {result.returncode}")
        logger.info(f"Subtitles burned successfully: {output_path}")

        if os.path.exists(output_path):
            output_size = os.path.getsize(output_path) / (1024 * 1024)
            logger.info(f"Output file size: {output_size:.2f}MB")
        else:
            logger.error(f"Output file does not exist: {output_path}")

        if result.stderr:
            logger.info(f"FFmpeg stderr output: {result.stderr[-1000:]}")
        if result.stdout:
            logger.info(f"FFmpeg stdout output: {result.stdout[-500:]}")
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        raise
    finally:
        if os.path.exists(srt_path):
            os.remove(srt_path)

def merge_video_audio(
    video_path: str,
    audio_path: str,
    output_path: str,
    video_volume: float = 0.2,
    audio_volume: float = 2.0,
    duration: float = 5.0,
    width: int = 1080,
    height: int = 1920,
    resize_mode: str = "cover"
) -> None:
    """
    Merge video with audio using FFmpeg

    Args:
        video_path: Path to video file
        audio_path: Path to audio file
        output_path: Path for output file
        video_volume: Volume level for video audio
        audio_volume: Volume level for added audio
        duration: Duration to trim
        width: Output width
        height: Output height
        resize_mode: "cover" or "contain"

    Raises:
        subprocess.CalledProcessError: If FFmpeg fails
    """
    try:
        logger.info(f"Merging video {video_path} with audio {audio_path}")

        if resize_mode == "cover":
            scale_filter = f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}[v]"
        else:
            scale_filter = f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2[v]"

        # Check if video has audio
        has_audio = video_has_audio(video_path)

        if has_audio:
            # Video has audio - mix it with the new audio
            filter_complex = (
                f"{scale_filter};"
                f"[0:a]volume={video_volume}[va];"
                f"[1:a]volume={audio_volume},atrim=duration={duration},asetpts=PTS-STARTPTS[aa];"
                f"[va][aa]amix=inputs=2:duration=first[a]"
            )
        else:
            # Video has no audio - just use the new audio
            logger.info("Video has no audio stream, using only voiceover audio")
            filter_complex = (
                f"{scale_filter};"
                f"[1:a]volume={audio_volume},atrim=duration={duration},asetpts=PTS-STARTPTS[a]"
            )

        cmd = [
            "ffmpeg", "-y",
            "-threads", "0",
            "-i", video_path,
            "-i", audio_path,
            "-t", str(duration),
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "48000",
            "-ac", "2",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"Video and audio merged: {output_path}")

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg merge error: {e.stderr}")
        raise


def concat_videos(video_list_path: str, output_path: str) -> None:
    """
    Concatenate multiple videos using FFmpeg concat demuxer

    Args:
        video_list_path: Path to text file with list of videos
        output_path: Path for output video

    Raises:
        subprocess.CalledProcessError: If FFmpeg fails
    """
    try:
        logger.info(f"Concatenating videos from list: {video_list_path}")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", video_list_path,
            "-c", "copy",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"Videos concatenated: {output_path}")

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg concat error: {e.stderr}")
        raise


def add_background_music(
    video_path: str,
    music_path: str,
    output_path: str,
    music_volume: float = 2.0,  # Changed default to 2.0 (200%)
    video_volume: float = 1.0   # Changed default to 1.0 (100%)
) -> None:
    """
    Add background music to a video
    Args:
        video_path: Path to video file
        music_path: Path to music file
        output_path: Path for output video
        music_volume: Volume multiplier for background music (1.0 = original, 2.0 = double)
        video_volume: Volume multiplier for video audio (1.0 = original)
    Raises:
        subprocess.CalledProcessError: If FFmpeg fails
    """
    try:
        video_duration = get_video_duration(video_path)
        logger.info(f"Adding background music to video (duration: {video_duration}s)")
        logger.info(f"Settings: music_volume={music_volume}, video_volume={video_volume}")

        # Use loudnorm filter to normalize audio first, then apply volume
        filter_complex = (
            f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,volume={music_volume},"
            f"aloop=loop=-1:size=2e+09,atrim=duration={video_duration}[ma];"
            f"[0:a]volume={video_volume}[va];"
            f"[va][ma]amix=inputs=2:duration=first:dropout_transition=2[a]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", music_path,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-shortest",
            output_path
        ]

        logger.info(f"Running FFmpeg background music command...")
        logger.info(f"Full command: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        logger.info(f"FFmpeg completed with return code: {result.returncode}")
        logger.info(f"Background music added: {output_path}")

        if os.path.exists(output_path):
            output_size = os.path.getsize(output_path) / (1024 * 1024)
            logger.info(f"Output file size: {output_size:.2f}MB")
        else:
            logger.error(f"Output file does not exist: {output_path}")

        if result.stderr:
            logger.info(f"FFmpeg stderr output: {result.stderr[-1000:]}")

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg background music error: {e.stderr}")
        raise


def insert_brolls_ffmpeg(
    main_video_path: str,
    broll_paths: List[str],
    broll_timings: List[Tuple[float, float]],
    output_path: str
) -> None:
    """
    Overlay B-roll clips on top of main video at specified timestamps using FFmpeg

    Args:
        main_video_path: Path to main video file
        broll_paths: List of paths to B-roll video files
        broll_timings: List of (start, end) tuples indicating when to show each B-roll
        output_path: Path for output video

    Raises:
        subprocess.CalledProcessError: If FFmpeg fails
    """
    try:
        logger.info(f"Overlaying {len(broll_paths)} B-rolls onto main video")
        logger.info(f"B-roll timings: {broll_timings}")

        if len(broll_paths) != len(broll_timings):
            raise ValueError(
                f"Number of B-rolls ({len(broll_paths)}) must match number of timings ({len(broll_timings)})"
            )

        cmd = ["ffmpeg", "-y", "-i", main_video_path]

        for broll_path in broll_paths:
            cmd.extend(["-i", broll_path])

        filter_parts = []

        for i in range(len(broll_paths)):
            start_time, end_time = broll_timings[i]
            duration = end_time - start_time

            filter_parts.append(
                f"[{i+1}:v]scale=1080:1920:force_original_aspect_ratio=increase,"
                f"crop=1080:1920,setpts=PTS-STARTPTS+{start_time}/TB[vb{i+1}]"
            )

        current_label = "[0:v]"

        for i in range(len(broll_paths)):
            start_time, end_time = broll_timings[i]

            if i == len(broll_paths) - 1:
                filter_parts.append(
                    f"{current_label}[vb{i+1}]overlay=enable='between(t,{start_time},{end_time})'[outv]"
                )
            else:
                filter_parts.append(
                    f"{current_label}[vb{i+1}]overlay=enable='between(t,{start_time},{end_time})'[v{i+1}]"
                )
                current_label = f"[v{i+1}]"

        filter_parts.append("[0:a]acopy[outa]")

        filter_complex = ";\n".join(filter_parts)

        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path
        ])

        logger.info("=" * 60)
        logger.info("FFmpeg Command:")
        logger.info(" ".join(cmd))
        logger.info("=" * 60)
        logger.info("Filter Complex:")
        logger.info(filter_complex)
        logger.info("=" * 60)

        logger.info("Running FFmpeg...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        logger.info(f"B-rolls overlaid successfully: {output_path}")

        if os.path.exists(output_path):
            output_size = os.path.getsize(output_path) / (1024 * 1024)
            logger.info(f"Output file size: {output_size:.2f}MB")

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        raise
