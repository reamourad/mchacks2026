import ffmpeg
import os
import tempfile

def cut_clip(input_path: str, output_path: str, start_time: float, end_time: float):
    """
    Cut a video clip from start to end time
    """
    duration = end_time - start_time
    try:
        # Use stream copy for much faster processing (no re-encoding)
        # Place ss before input for faster, more accurate seeking
        # This avoids the hanging issue with libx264
        (
            ffmpeg
            .input(input_path, ss=start_time, t=duration)
            .output(output_path, c='copy')
            .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
        )
        print(f"Clip cut successfully: {output_path}")
    except ffmpeg.Error as e:
        print('stdout:', e.stdout.decode('utf8'))
        print('stderr:', e.stderr.decode('utf8'))
        # If stream copy fails, try re-encoding as fallback
        try:
            print("Stream copy failed, trying re-encode...")
            (
                ffmpeg
                .input(input_path)
                .output(output_path, ss=start_time, t=duration, vcodec='libx264', preset='ultrafast')
                .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
            )
            print(f"Clip cut successfully with re-encode: {output_path}")
        except ffmpeg.Error as e2:
            print('Re-encode stdout:', e2.stdout.decode('utf8'))
            print('Re-encode stderr:', e2.stderr.decode('utf8'))
            raise Exception("ffmpeg error (see stderr output for detail)")

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
        # Try stream copy first for fast concatenation (no re-encoding)
        try:
            print("Attempting concat with stream copy...")
            (
                ffmpeg
                .input(list_file_path, format='concat', safe=0)
                .output(output_path, c='copy')
                .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
            )
            print(f"Video assembled successfully with stream copy: {output_path}")
        except ffmpeg.Error as e:
            print('Stream copy concat failed, trying with re-encode...')
            print('stdout:', e.stdout.decode('utf8'))
            print('stderr:', e.stderr.decode('utf8'))

            # Fallback: re-encode to ensure all clips are compatible
            # This normalizes codec, resolution, and frame rate
            (
                ffmpeg
                .input(list_file_path, format='concat', safe=0)
                .output(
                    output_path,
                    vcodec='libx264',
                    acodec='aac',
                    preset='medium',
                    crf=23,
                    pix_fmt='yuv420p',
                    **{'movflags': '+faststart'}  # Optimize for streaming
                )
                .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
            )
            print(f"Video assembled successfully with re-encode: {output_path}")
    except ffmpeg.Error as e:
        print('Final concat error:')
        print('stdout:', e.stdout.decode('utf8'))
        print('stderr:', e.stderr.decode('utf8'))
        raise Exception("ffmpeg error (see stderr output for detail)")
    finally:
        os.unlink(list_file_path)
