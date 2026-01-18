import ffmpeg
import os
import tempfile

def cut_clip(input_path: str, output_path: str, start_time: float, end_time: float):
    """
    Cut a video clip from start to end time
    """
    duration = end_time - start_time
    try:
        (
            ffmpeg
            .input(input_path, ss=start_time)
            .output(output_path, t=duration, vcodec='libx264', acodec='aac')
            .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
        )
        print(f"Clip cut successfully: {output_path}")
    except ffmpeg.Error as e:
        print('stdout:', e.stdout.decode('utf8'))
        print('stderr:', e.stderr.decode('utf8'))
        raise e

def assemble_video(clip_paths: list[str], output_path: str):
    """
    Concatenate multiple video clips into one video
    """
    if not clip_paths:
        raise ValueError("No clips to assemble")

    # Create a temporary file list for FFmpeg concat
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt") as temp_file:
        for p in clip_paths:
            temp_file.write(f"file '{os.path.abspath(p)}'\n")
        list_file_path = temp_file.name

    try:
        (
            ffmpeg
            .input(list_file_path, format='concat', safe=0)
            .output(output_path, vcodec='libx264', acodec='aac')
            .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
        )
        print(f"Video assembled successfully: {output_path}")
    except ffmpeg.Error as e:
        print('stdout:', e.stdout.decode('utf8'))
        print('stderr:', e.stderr.decode('utf8'))
        raise e
    finally:
        os.unlink(list_file_path)
