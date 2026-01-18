import ffmpeg
import os
import tempfile

def cut_clip(input_path: str, output_path: str, start_time: float, end_time: float):
    """
    Cut a video clip from start to end time.
    Always ensures audio stream is present (adds silent audio if missing) to prevent concat issues.
    """
    duration = end_time - start_time

    # First, check if input has audio
    has_audio = False
    try:
        probe = ffmpeg.probe(input_path)
        has_audio = any(stream['codec_type'] == 'audio' for stream in probe['streams'])
        print(f"Input audio detected: {has_audio}")
    except Exception as probe_error:
        print(f"Could not probe input, assuming no audio: {probe_error}")

    try:
        if has_audio:
            # Has audio - try fast stream copy first
            try:
                ffmpeg.input(input_path, ss=start_time, t=duration).output(
                    output_path,
                    c='copy'
                ).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
                print(f"Clip cut successfully (stream copy): {output_path}")
                return
            except ffmpeg.Error as e:
                print("Stream copy failed, will re-encode...")
                # Fall through to re-encode

        # Either no audio OR stream copy failed - re-encode and normalize audio
        if has_audio:
            # Has audio - re-encode normally
            print("Re-encoding with existing audio...")
            ffmpeg.input(input_path, ss=start_time, t=duration).output(
                output_path,
                vcodec='libx264',
                acodec='aac',
                preset='ultrafast',
                pix_fmt='yuv420p'
            ).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
        else:
            # No audio - add silent audio track for concat compatibility
            print("No audio detected - adding silent audio track...")
            video_input = ffmpeg.input(input_path, ss=start_time, t=duration)
            silent_audio = ffmpeg.input('anullsrc=channel_layout=stereo:sample_rate=44100',
                                       f='lavfi',
                                       t=duration)

            ffmpeg.output(
                video_input,
                silent_audio,
                output_path,
                vcodec='libx264',
                acodec='aac',
                preset='ultrafast',
                pix_fmt='yuv420p',
                shortest=None  # -shortest flag
            ).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)

        print(f"Clip cut successfully (re-encoded with audio): {output_path}")

    except ffmpeg.Error as e:
        print('FFmpeg error during cut:')
        print('stdout:', e.stdout.decode('utf8'))
        print('stderr:', e.stderr.decode('utf8'))
        raise Exception(f"ffmpeg error cutting clip: see stderr output for detail")

def assemble_video(clip_paths: list[str], output_path: str):
    """
    Concatenate multiple video clips into one video.
    Assumes all clips have been normalized with audio (by cut_clip).
    Always re-encodes to ensure compatibility across all segments.
    """
    if not clip_paths:
        raise ValueError("No clips to assemble")

    print(f"\n=== Assembling {len(clip_paths)} clips ===")

    # Create a temporary file list for FFmpeg concat
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt") as temp_file:
        for i, p in enumerate(clip_paths, 1):
            abs_path = os.path.abspath(p)

            # Verify file exists and has size
            if not os.path.exists(abs_path):
                raise ValueError(f"Clip file does not exist: {abs_path}")

            file_size = os.path.getsize(abs_path)
            if file_size == 0:
                raise ValueError(f"Clip file is empty: {abs_path}")

            # Probe the clip for stream info
            try:
                probe = ffmpeg.probe(abs_path)
                streams_info = []
                for stream in probe['streams']:
                    codec_type = stream.get('codec_type', 'unknown')
                    codec_name = stream.get('codec_name', 'unknown')
                    streams_info.append(f"{codec_type}:{codec_name}")

                print(f"  Clip {i}: {os.path.basename(abs_path)}")
                print(f"    Size: {file_size} bytes")
                print(f"    Streams: {', '.join(streams_info)}")
            except Exception as probe_err:
                print(f"  Clip {i}: {os.path.basename(abs_path)} ({file_size} bytes) - probe failed: {probe_err}")

            temp_file.write(f"file '{abs_path}'\n")

        list_file_path = temp_file.name

    print(f"\nConcat list: {list_file_path}")

    try:
        # All clips should have audio now (normalized by cut_clip)
        # Always encode with audio
        print("Concatenating with re-encode...")

        ffmpeg.input(list_file_path, format='concat', safe=0).output(
            output_path,
            vcodec='libx264',
            acodec='aac',
            preset='medium',
            crf=23,
            pix_fmt='yuv420p',
            movflags='+faststart'
        ).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)

        final_size = os.path.getsize(output_path)
        print(f"\n✓ Video assembled successfully: {output_path}")
        print(f"  Final size: {final_size} bytes ({final_size / 1024 / 1024:.2f} MB)")

    except ffmpeg.Error as e:
        print('\n✗ FFmpeg concat error:')
        print(f'  Exit code: {e.returncode if hasattr(e, "returncode") else "unknown"}')
        print(f'  Concat list: {list_file_path}')
        print('\nSTDOUT:')
        print(e.stdout.decode('utf8'))
        print('\nSTDERR:')
        print(e.stderr.decode('utf8'))
        raise Exception(f"FFmpeg concat failed - see detailed error output above")
    finally:
        # Clean up temp concat list
        if os.path.exists(list_file_path):
            os.unlink(list_file_path)
