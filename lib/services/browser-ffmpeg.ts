import { FFmpeg } from '@ffmpeg/ffmpeg';
import { fetchFile, toBlobURL } from '@ffmpeg/util';
import { GumloopMatch } from '../models/Project';
import { parseTimestamp } from './gumloop';

let ffmpegInstance: FFmpeg | null = null;
let isLoading = false;
let isLoaded = false;

/**
 * Load FFmpeg WASM (only once)
 */
export async function loadFFmpeg(onProgress?: (progress: number) => void): Promise<FFmpeg> {
  if (ffmpegInstance && isLoaded) {
    return ffmpegInstance;
  }

  if (isLoading) {
    // Wait for loading to complete
    while (isLoading) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    if (ffmpegInstance) return ffmpegInstance;
  }

  isLoading = true;

  try {
    ffmpegInstance = new FFmpeg();

    // Set up progress logging
    if (onProgress) {
      ffmpegInstance.on('progress', ({ progress }) => {
        onProgress(Math.round(progress * 100));
      });
    }

    ffmpegInstance.on('log', ({ message }) => {
      console.log('[FFmpeg]', message);
    });

    // Load FFmpeg core
    const baseURL = 'https://unpkg.com/@ffmpeg/core@0.12.6/dist/umd';
    await ffmpegInstance.load({
      coreURL: await toBlobURL(`${baseURL}/ffmpeg-core.js`, 'text/javascript'),
      wasmURL: await toBlobURL(`${baseURL}/ffmpeg-core.wasm`, 'application/wasm'),
    });

    isLoaded = true;
    isLoading = false;

    return ffmpegInstance;
  } catch (error) {
    isLoading = false;
    throw error;
  }
}

/**
 * Cut a video clip from start to end time (in browser)
 */
export async function cutClipBrowser(
  videoFile: File,
  startTime: number,
  endTime: number,
  outputFilename: string,
  onProgress?: (progress: number) => void
): Promise<Blob> {
  const ffmpeg = await loadFFmpeg(onProgress);

  const duration = endTime - startTime;
  const inputName = `input_${Date.now()}.mp4`;

  // Write input file to FFmpeg virtual filesystem
  await ffmpeg.writeFile(inputName, await fetchFile(videoFile));

  // Execute FFmpeg command to cut video
  // Place -ss BEFORE -i for faster, more accurate input seeking
  await ffmpeg.exec([
    '-ss', startTime.toString(),
    '-i', inputName,
    '-t', duration.toString(),
    '-c', 'copy', // Copy codec (faster, no re-encoding)
    outputFilename
  ]);

  // Read output file
  const data = await ffmpeg.readFile(outputFilename);

  // Clean up
  await ffmpeg.deleteFile(inputName);
  await ffmpeg.deleteFile(outputFilename);

  // Convert to Blob (create new Uint8Array to ensure proper typing)
  const buffer = new Uint8Array(data as Uint8Array).buffer;
  return new Blob([buffer], { type: 'video/mp4' });
}

/**
 * Concatenate multiple video clips (in browser)
 */
export async function assembleVideoBrowser(
  clipBlobs: Blob[],
  onProgress?: (progress: number) => void
): Promise<Blob> {
  const ffmpeg = await loadFFmpeg(onProgress);

  // Write all clips to virtual filesystem
  const clipFiles: string[] = [];
  for (let i = 0; i < clipBlobs.length; i++) {
    const filename = `clip_${i}.mp4`;
    await ffmpeg.writeFile(filename, await fetchFile(clipBlobs[i]));
    clipFiles.push(filename);
  }

  // Create concat demuxer file list
  const concatList = clipFiles.map(f => `file '${f}'`).join('\n');
  await ffmpeg.writeFile('concat_list.txt', concatList);

  // Concatenate videos
  await ffmpeg.exec([
    '-f', 'concat',
    '-safe', '0',
    '-i', 'concat_list.txt',
    '-c', 'copy',
    'output.mp4'
  ]);

  // Read output
  const data = await ffmpeg.readFile('output.mp4');

  // Clean up
  await ffmpeg.deleteFile('concat_list.txt');
  await ffmpeg.deleteFile('output.mp4');
  for (const file of clipFiles) {
    await ffmpeg.deleteFile(file);
  }

  // Convert to Blob (create new Uint8Array to ensure proper typing)
  const buffer = new Uint8Array(data as Uint8Array).buffer;
  return new Blob([buffer], { type: 'video/mp4' });
}

/**
 * Download a video from URL as File object
 */
export async function downloadVideoFile(url: string): Promise<File> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to download video: ${response.statusText}`);
  }
  const blob = await response.blob();
  const filename = url.split('/').pop() || 'video.mp4';
  return new File([blob], filename, { type: 'video/mp4' });
}

/**
 * Process video project entirely in browser
 */
export async function processProjectVideoBrowser(
  clips: { s3Url: string; filename: string }[],
  gumloopMatches: GumloopMatch[],
  onProgress?: (stage: string, progress: number) => void
): Promise<Blob> {
  try {
    onProgress?.('Loading FFmpeg', 0);
    await loadFFmpeg();

    // Step 1: Download all required clips
    onProgress?.('Downloading clips', 10);
    const clipFiles = new Map<string, File>();

    for (const clip of clips) {
      const file = await downloadVideoFile(clip.s3Url);
      clipFiles.set(clip.filename, file);
    }

    // Step 2: Cut each clip according to Gumloop timestamps
    onProgress?.('Cutting clips', 30);
    const cutClips: Blob[] = [];

    for (let i = 0; i < gumloopMatches.length; i++) {
      const match = gumloopMatches[i];

      // Find the source clip file
      const sourceFilename = match.matched_clip;
      const sourceFile = clipFiles.get(sourceFilename);

      if (!sourceFile) {
        throw new Error(`Source clip not found: ${sourceFilename}`);
      }

      // Parse timestamps
      const { start, end } = parseTimestamp(match.clip_timestamp);

      if (end === undefined) {
        throw new Error(`Invalid timestamp: ${match.clip_timestamp}`);
      }

      // Cut the clip
      const progress = 30 + ((i / gumloopMatches.length) * 40);
      onProgress?.(`Cutting segment ${i + 1}/${gumloopMatches.length}`, progress);

      const cutBlob = await cutClipBrowser(
        sourceFile,
        start,
        end,
        `segment_${i}.mp4`
      );

      cutClips.push(cutBlob);
    }

    // Step 3: Concatenate all clips
    onProgress?.('Assembling final video', 80);
    const finalVideo = await assembleVideoBrowser(cutClips);

    onProgress?.('Complete', 100);

    return finalVideo;
  } catch (error) {
    console.error('Error processing video in browser:', error);
    throw error;
  }
}
