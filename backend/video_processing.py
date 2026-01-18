from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioClip
import os
import numpy as np

def cut_clip(input_path: str, output_path: str, start_time: float, end_time: float):
    """
    Cut a video clip from start to end time using MoviePy.
    Always ensures audio stream is present (adds silent audio if missing) to prevent concat issues.
    """
    print(f"Cutting clip: {input_path} from {start_time}s to {end_time}s")

    try:
        # Load the video
        video = VideoFileClip(input_path)

        # Cut the clip
        clip = video.subclip(start_time, end_time)

        # Check if clip has audio
        has_audio = clip.audio is not None
        print(f"Input audio detected: {has_audio}")

        if not has_audio:
            # Add silent audio track for concat compatibility
            print("No audio detected - adding silent audio track...")
            duration = clip.duration

            # Create silent audio
            def make_frame(t):
                return np.array([0, 0])  # Stereo silence

            silent_audio = AudioClip(make_frame, duration=duration, fps=44100)
            clip = clip.set_audio(silent_audio)

        # Write the output
        clip.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            logger=None  # Suppress MoviePy's verbose output
        )

        # Clean up
        clip.close()
        video.close()

        file_size = os.path.getsize(output_path)
        print(f"✓ Clip cut successfully: {output_path} ({file_size} bytes)")

    except Exception as e:
        print(f"✗ Error cutting clip: {e}")
        raise Exception(f"MoviePy error cutting clip: {e}")

def assemble_video(clip_paths: list[str], output_path: str):
    """
    Concatenate multiple video clips into one video using MoviePy.
    Assumes all clips have been normalized with audio (by cut_clip).
    """
    if not clip_paths:
        raise ValueError("No clips to assemble")

    print(f"\n=== Assembling {len(clip_paths)} clips ===")

    try:
        # Load all clips
        clips = []
        for i, clip_path in enumerate(clip_paths, 1):
            abs_path = os.path.abspath(clip_path)

            # Verify file exists and has size
            if not os.path.exists(abs_path):
                raise ValueError(f"Clip file does not exist: {abs_path}")

            file_size = os.path.getsize(abs_path)
            if file_size == 0:
                raise ValueError(f"Clip file is empty: {abs_path}")

            print(f"  Loading clip {i}: {os.path.basename(abs_path)} ({file_size} bytes)")

            # Load the clip
            clip = VideoFileClip(abs_path)
            clips.append(clip)

            # Print clip info
            has_audio = clip.audio is not None
            print(f"    Duration: {clip.duration:.2f}s, Size: {clip.size}, Audio: {has_audio}")

        # Concatenate all clips
        print("\nConcatenating clips...")
        final_clip = concatenate_videoclips(clips, method="compose")

        # Write the final video
        print("Writing final video...")
        final_clip.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio-final.m4a',
            remove_temp=True,
            logger=None
        )

        # Clean up
        final_clip.close()
        for clip in clips:
            clip.close()

        final_size = os.path.getsize(output_path)
        print(f"\n✓ Video assembled successfully: {output_path}")
        print(f"  Final size: {final_size} bytes ({final_size / 1024 / 1024:.2f} MB)")

    except Exception as e:
        print(f'\n✗ MoviePy error during assembly: {e}')
        # Clean up clips if error occurs
        try:
            if 'clips' in locals():
                for clip in clips:
                    clip.close()
        except:
            pass
        raise Exception(f"MoviePy concat failed: {e}")
