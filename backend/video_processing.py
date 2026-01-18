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
    IMPORTANT: Always re-encodes to ensure compatibility across all segments
    """
    if not clip_paths:
        raise ValueError("No clips to assemble")

    print(f"Assembling {len(clip_paths)} clips:")
    for i, p in enumerate(clip_paths, 1):
        print(f"  Clip {i}: {p}")

    # Create a temporary file list for FFmpeg concat
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt") as temp_file:
        for p in clip_paths:
            abs_path = os.path.abspath(p)
            temp_file.write(f"file '{abs_path}'\n")
            # Verify file exists and has size
            if not os.path.exists(abs_path):
                raise ValueError(f"Clip file does not exist: {abs_path}")
            file_size = os.path.getsize(abs_path)
            print(f"  - {os.path.basename(abs_path)}: {file_size} bytes")
        list_file_path = temp_file.name

    print(f"Concat list file: {list_file_path}")

    try:
        # Always re-encode to ensure all clips are compatible
        # This normalizes codec, resolution, frame rate, and ensures proper concatenation
        print("Concatenating with re-encode (ensures compatibility)...")

        # Check if first clip has audio
        has_audio = False
        try:
            probe = ffmpeg.probe(clip_paths[0])
            has_audio = any(stream['codec_type'] == 'audio' for stream in probe['streams'])
            if has_audio:
                print("Audio detected - encoding with AAC")
            else:
                print("No audio detected - video only")
        except Exception as probe_error:
            print(f"Could not probe audio, assuming no audio: {probe_error}")

        # Build FFmpeg command based on whether audio is present
        if has_audio:
            # With audio - encode both video and audio
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
                    **{'movflags': '+faststart'}
                )
                .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
            )
        else:
            # Video only - disable audio with 'an'
            (
                ffmpeg
                .input(list_file_path, format='concat', safe=0)
                .output(
                    output_path,
                    vcodec='libx264',
                    preset='medium',
                    crf=23,
                    pix_fmt='yuv420p',
                    an=True,  # Disable audio
                    **{'movflags': '+faststart'}
                )
                .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
            )

        final_size = os.path.getsize(output_path)
        print(f"Video assembled successfully: {output_path} ({final_size} bytes)")
    except ffmpeg.Error as e:
        print('Concat error:')
        print('stdout:', e.stdout.decode('utf8'))
        print('stderr:', e.stderr.decode('utf8'))
        raise Exception("ffmpeg error (see stderr output for detail)")
    finally:
        os.unlink(list_file_path)
