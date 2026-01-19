import ffmpeg from 'fluent-ffmpeg';
import path from 'path';
import fs from 'fs';
import os from 'os';
import { Project, GumloopMatch } from '../models/Project';
import { downloadFromS3, uploadFileToS3, generateFinalVideoKey } from '../s3';
import { parseTimestamp } from './gumloop';

// Dynamically import ffmpeg-static only on the server side
if (typeof window === 'undefined') {
  try {
    const ffmpegStatic = require('ffmpeg-static');
    if (ffmpegStatic) {
      ffmpeg.setFfmpegPath(ffmpegStatic);
    }
  } catch (error) {
    console.warn('ffmpeg-static not available, using system ffmpeg');
  }
}

/**
 * Cut a video clip from start to end time
 * @param inputPath - Path to input video file
 * @param outputPath - Path to save output video file
 * @param startTime - Start time in seconds
 * @param endTime - End time in seconds
 * @returns Promise that resolves when cutting is complete
 */
export function cutClip(
  inputPath: string,
  outputPath: string,
  startTime: number,
  endTime: number
): Promise<void> {
  return new Promise((resolve, reject) => {
    const duration = endTime - startTime;

    ffmpeg(inputPath)
      .setStartTime(startTime)
      .setDuration(duration)
      .output(outputPath)
      .videoCodec('libx264') // Re-encode with H.264
      .audioCodec('aac')
      .on('end', () => {
        console.log(`Clip cut successfully: ${outputPath}`);
        resolve();
      })
      .on('error', (err) => {
        console.error(`Error cutting clip: ${err.message}`);
        reject(err);
      })
      .run();
  });
}

/**
 * Concatenate multiple video clips into one video
 * @param clipPaths - Array of paths to video clips (in order)
 * @param outputPath - Path to save final assembled video
 * @returns Promise that resolves when assembly is complete
 */
export function assembleVideo(clipPaths: string[], outputPath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (clipPaths.length === 0) {
      reject(new Error('No clips to assemble'));
      return;
    }

    // Create a temporary file list for FFmpeg concat
    const tempDir = os.tmpdir();
    const listFilePath = path.join(tempDir, `concat-list-${Date.now()}.txt`);

    // Write file paths to concat list
    // FFmpeg concat format: file '/path/to/file.mp4'
    const fileList = clipPaths.map((p) => `file '${p}'`).join('\n');
    fs.writeFileSync(listFilePath, fileList);

    ffmpeg()
      .input(listFilePath)
      .inputOptions(['-f concat', '-safe 0'])
      .videoCodec('libx264')
      .audioCodec('aac')
      .output(outputPath)
      .on('end', () => {
        // Clean up temp list file
        fs.unlinkSync(listFilePath);
        console.log(`Video assembled successfully: ${outputPath}`);
        resolve();
      })
      .on('error', (err) => {
        // Clean up temp list file
        try {
          fs.unlinkSync(listFilePath);
        } catch (cleanupError) {
          console.error('Error cleaning up temp file:', cleanupError);
        }
        console.error(`Error assembling video: ${err.message}`);
        reject(err);
      })
      .run();
  });
}

/**
 * Find the S3 key for a matched clip based on the filename
 * @param matchedClipName - Name from Gumloop (e.g., "rea_test_4.mp4")
 * @param project - Project object with all clips
 * @returns S3 key of the matched clip
 */
function findClipS3Key(matchedClipName: string, project: Project): string {
  // Extract the clip number from the matched clip name
  // Expected format: username_projectname_number.mp4
  const match = matchedClipName.match(/_(\d+)\.mp4$/);

  if (!match) {
    throw new Error(`Invalid matched clip name format: ${matchedClipName}`);
  }

  const clipNumber = parseInt(match[1], 10);

  // Find the clip in the project
  const clip = project.clips.find((c) => c.clipNumber === clipNumber);

  if (!clip) {
    throw new Error(`Clip not found in project: ${matchedClipName} (clip #${clipNumber})`);
  }

  return clip.s3Key;
}

/**
 * Main function to process a project's video
 * Downloads clips, cuts them according to Gumloop matches, assembles final video
 * @param project - Project object with Gumloop matches
 * @returns S3 URL of the final video
 */
export async function processProjectVideo(project: Project): Promise<string> {
  if (!project.gumloopOutput || project.gumloopOutput.length === 0) {
    throw new Error('No Gumloop output found for project');
  }

  const tempDir = path.join(os.tmpdir(), `xpresso-${project._id?.toString()}`);

  try {
    // Create temp directory
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    console.log(`Processing project: ${project.projectName}`);
    console.log(`Temp directory: ${tempDir}`);

    // Step 1: Download all required clips from S3
    const downloadedClips = new Map<string, string>(); // Map of S3 key to local path

    for (const match of project.gumloopOutput) {
      const s3Key = findClipS3Key(match.matched_clip, project);

      if (!downloadedClips.has(s3Key)) {
        const localPath = path.join(tempDir, path.basename(s3Key));
        console.log(`Downloading ${s3Key} to ${localPath}`);
        await downloadFromS3(s3Key, localPath);
        downloadedClips.set(s3Key, localPath);
      }
    }

    // Step 2: Cut each clip according to Gumloop timestamps
    const cutClipPaths: string[] = [];

    for (let i = 0; i < project.gumloopOutput.length; i++) {
      const match = project.gumloopOutput[i];
      const s3Key = findClipS3Key(match.matched_clip, project);
      const inputPath = downloadedClips.get(s3Key)!;

      // Parse clip timestamp
      const { start, end } = parseTimestamp(match.clip_timestamp);

      if (end === undefined) {
        throw new Error(`Invalid clip timestamp (no end time): ${match.clip_timestamp}`);
      }

      // Output path for cut clip
      const cutOutputPath = path.join(tempDir, `cut-segment-${i + 1}.mp4`);

      console.log(
        `Cutting segment ${i + 1}: ${inputPath} from ${start}s to ${end}s -> ${cutOutputPath}`
      );

      await cutClip(inputPath, cutOutputPath, start, end);
      cutClipPaths.push(cutOutputPath);
    }

    // Step 3: Concatenate all cut clips
    const finalVideoPath = path.join(tempDir, 'final-video.mp4');

    console.log(`Assembling ${cutClipPaths.length} clips into final video`);
    await assembleVideo(cutClipPaths, finalVideoPath);

    // Step 4: Upload final video to S3
    const finalS3Key = generateFinalVideoKey(project.username, project.projectName);

    console.log(`Uploading final video to S3: ${finalS3Key}`);
    const finalVideoUrl = await uploadFileToS3(finalVideoPath, finalS3Key);

    console.log(`Final video URL: ${finalVideoUrl}`);

    // Step 5: Clean up temp directory
    console.log(`Cleaning up temp directory: ${tempDir}`);
    fs.rmSync(tempDir, { recursive: true, force: true });

    return finalVideoUrl;
  } catch (error) {
    // Clean up on error
    console.error('Error processing video:', error);

    try {
      if (fs.existsSync(tempDir)) {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    } catch (cleanupError) {
      console.error('Error cleaning up after failure:', cleanupError);
    }

    throw error;
  }
}
