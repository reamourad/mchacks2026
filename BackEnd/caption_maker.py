import json
import os
from moviepy import VideoFileClip, TextClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
from PIL import ImageFont, ImageDraw, Image  # For measuring text width
import subprocess
import logging

# Disable MoviePy logging for faster processing
logging.getLogger('moviepy').setLevel(logging.CRITICAL)


def time_to_seconds(time_str):
    """Converts HH:MM:SS to total seconds."""
    h, m, s = map(int, time_str.split(':'))
    return h * 3600 + m * 60 + s

def get_styles():
    EMOTION_STYLES = {
    "neutral":    {"color": "yellow",       "font": "BackEnd/fonts/Playwrite_NG_Modern/static/PlaywriteNGModern-Regular.ttf"},
    "confident":  {"color": "blue",        "font": "BackEnd/fonts/Limelight/Limelight-Regular.ttf"},
    "excited":    {"color": "yellow",      "font": "BackEnd/fonts/Bowlby_One_SC/BowlbyOneSC-Regular.ttf"},
    "happy":      {"color": "lightpink",   "font": "BackEnd/fonts/Monsieur_La_Doulaise/MonsieurLaDoulaise-Regular.ttf"},
    "serious":    {"color": "grey",        "font": "BackEnd/fonts/Playfair_Display/static/PlayfairDisplay-Regular.ttf"},
    "concerned":  {"color": "lightblue",    "font": "BackEnd/fonts/Playwrite_NG_Modern/static/PlaywriteNGModern-Light.ttf"},
    "empathetic": {"color": "lightgreen",   "font": "BackEnd/fonts/Limelight/Limelight-Regular.ttf"},
    "persuasive": {"color": "yellowgreen",  "font": "BackEnd/fonts/Bowlby_One_SC/BowlbyOneSC-Regular.ttf"},
    "reflective": {"color": "lavender",     "font": "BackEnd/fonts/Monsieur_La_Doulaise/MonsieurLaDoulaise-Regular.ttf"},
    "frustrated": {"color": "orange",       "font": "BackEnd/fonts/Playfair_Display/static/PlayfairDisplay-Bold.ttf"},
    "urgent":     {"color": "orangered",    "font": "BackEnd/fonts/Playwrite_NG_Modern/static/PlaywriteNGModern-Thin.ttf"},
    "sad":        {"color": "steelblue",    "font": "BackEnd/fonts/Limelight/Limelight-Regular.ttf"}
    }
    return EMOTION_STYLES

def get_text_width(text, font_size=50, font_path=None):
    if font_path is None:
        font_path = "BackEnd/fonts/Playwrite_NG_Modern/static/PlaywriteNGModern-Regular.ttf"  # Default font for measuring
    font = ImageFont.truetype(font_path, font_size)
    img = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]

def concatenate_clips(*clips, target_width=1080, target_height=1920):
    """
    Concatenates 2 or more video clips sequentially (start to finish).
    Resizes all clips to the same target size for compatibility, then uses 'compose' method.
    
    Args:
        *clips: Variable number of VideoFileClip, TextClip, or other moviepy clips.
        target_width: Target width for resizing (default 1080).
        target_height: Target height for resizing (default 1920).
    
    Returns:
        A single concatenated video clip.
    """
    if len(clips) < 2:
        raise ValueError("At least 2 clips are required for concatenation.")
    
    # Resize all clips to target size
    resized_clips = []
    for clip in clips:
        if clip.w != target_width or clip.h != target_height:
            # Resize maintaining aspect ratio, then crop/pad if necessary
            clip = clip.resized(height=target_height) if clip.w / clip.h > target_width / target_height else clip.resized(width=target_width)
            # Crop to exact size
            if clip.w > target_width:
                clip = clip.cropped(x1=(clip.w - target_width)/2, x2=(clip.w + target_width)/2)
            if clip.h > target_height:
                clip = clip.cropped(y1=(clip.h - target_height)/2, y2=(clip.h + target_height)/2)
        resized_clips.append(clip)
    
    return concatenate_videoclips(resized_clips, method="chain")

def fast_concatenate_videos(video_paths, output_path):
    """
    Fast concatenation using ffmpeg without re-encoding.
    Assumes videos have compatible codecs, resolution, etc.
    
    Args:
        video_paths: List of video file paths to concatenate.
        output_path: Output video file path.
    """
    # Create a temporary file list for ffmpeg
    list_file = "temp_concat_list.txt"
    with open(list_file, 'w') as f:
        for path in video_paths:
            f.write(f"file '{path}'\n")
    
    # Run ffmpeg concat
    cmd = [
        'ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_file, 
        '-c', 'copy', '-y', output_path
    ]
    subprocess.run(cmd, check=True)
    
    # Clean up
    os.remove(list_file)

def add_subtitles_to_video(video_path, json_path, output_path,audio_path=None):
    video = VideoFileClip(video_path)
    
    target_width = 1080
    target_height = 1920
    target_ratio = target_width / target_height
    current_ratio = video.w / video.h
    
    if abs(current_ratio - target_ratio) > 0.01:
        if current_ratio > target_ratio:
            video = video.resized(height=target_height)
            crop_x1 = (video.w - target_width) / 2
            crop_x2 = crop_x1 + target_width
            video = video.cropped(x1=crop_x1, y1=0, x2=crop_x2, y2=target_height)
        else:
            video = video.resized(width=target_width)
            crop_y1 = (video.h - target_height) / 2
            crop_y2 = crop_y1 + target_height
            video = video.cropped(x1=0, y1=crop_y1, x2=target_width, y2=crop_y2)
    
    with open(json_path, 'r') as f:
        transcript_data = json.load(f)
    
    styles = get_styles()

    subtitle_clips = []
    max_width_ratio = 0.7
    max_height_ratio = 0.2
    font_size = 75
    
    for entry in transcript_data:
        start_s = time_to_seconds(entry['start'])
        end_s = time_to_seconds(entry['end'])
        total_duration = end_s - start_s
        
        if total_duration <= 0:
            total_duration = 0.5  # Minimum duration for short entries
        
        words = entry['text'].split()
        if not words:
            continue

        emotion = entry.get('emotion', 'neutral')
        style = styles.get(emotion, styles['neutral'])
        text_color = style['color']
        font_path = style['font']
        
        # Dynamic chunking
        chunks = []
        current_chunk = []
        max_width = video.w * max_width_ratio
        
        for word in words:
            test_text = ' '.join(current_chunk + [word])
            if get_text_width(test_text, font_size, font_path) <= max_width:
                current_chunk.append(word)
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = [word]
        
        if current_chunk:
            chunks.append(current_chunk)
        
        num_chunks = len(chunks)
        if num_chunks == 0:
            continue
        
        chunk_duration = total_duration / num_chunks
        
        for i, chunk in enumerate(chunks):
            chunk_text = ' '.join(chunk)
            chunk_start = start_s + i * chunk_duration
            
            txt_clip = TextClip(
                text=chunk_text,
                font_size=font_size,
                font=font_path,
                color=text_color,
                stroke_color='black',
                stroke_width=1.5,
                method='caption',
                size=(int(video.w * max_width_ratio), int(video.h * max_height_ratio))
            ).with_start(chunk_start).with_duration(chunk_duration).with_position(('center', 0.85), relative=True)
            
            subtitle_clips.append(txt_clip)
    
    # Composite and write
    final_video = CompositeVideoClip([video] + subtitle_clips)

    if audio_path:
        audio = AudioFileClip(audio_path)
        final_video = final_video.with_audio(audio)


    final_video.write_videofile(output_path, fps=video.fps, threads=8, preset="ultrafast")


# Example usage
# add_subtitles_to_video("./BackEnd/mutedVid.mp4", "output_json.json", "output_with_subtitles.mp4", audio_path="./BackEnd/10sec.m4a")

# For videos with different properties, resize each to common size and write to temp files, then fast concat
import tempfile
import os

target_width, target_height = 1080, 1920
temp_files = []

for i, path in enumerate(["./BackEnd/coding_18s.mp4", "./BackEnd/browsing_15s.mp4"]):
    clip = VideoFileClip(path)
    # Resize logic
    current_ratio = clip.w / clip.h
    target_ratio = target_width / target_height
    if abs(current_ratio - target_ratio) > 0.01:
        if current_ratio > target_ratio:
            clip = clip.resized(height=target_height)
            crop_x1 = (clip.w - target_width) / 2
            clip = clip.cropped(x1=crop_x1, y1=0, x2=crop_x1 + target_width, y2=target_height)
        else:
            clip = clip.resized(width=target_width)
            crop_y1 = (clip.h - target_height) / 2
            clip = clip.cropped(x1=0, y1=crop_y1, x2=target_width, y2=crop_y1 + target_height)
    
    temp_file = f"./BackEnd/temp_{i}.mp4"
    clip.write_videofile(temp_file, fps=clip.fps, threads=8, preset="ultrafast")
    temp_files.append(temp_file)
    clip.close()

# Fast concatenate the resized videos
fast_concatenate_videos(temp_files, "./BackEnd/combined_video.mp4")

# Clean up temp files
for temp in temp_files:
    os.remove(temp)