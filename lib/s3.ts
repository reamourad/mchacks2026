import { PutObjectCommand, GetObjectCommand, S3Client } from "@aws-sdk/client-s3"
import { getSignedUrl } from "@aws-sdk/s3-request-presigner"
import fs from 'fs'
import { Readable } from 'stream'

function getS3Client() {
  const region = process.env.AWS_REGION
  const accessKeyId = process.env.AWS_ACCESS_KEY_ID
  const secretAccessKey = process.env.AWS_SECRET_ACCESS_KEY

  if (!region || !accessKeyId || !secretAccessKey) {
    throw new Error("Missing AWS env vars (AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)")
  }

  return new S3Client({
    region,
    credentials: { accessKeyId, secretAccessKey },
  })
}

function getBucketName() {
  const bucket = process.env.S3_BUCKET_NAME
  if (!bucket) {
    throw new Error("Missing S3_BUCKET_NAME env var")
  }
  return bucket
}

export function generateS3Key(username: string, projectName: string, clipNumber: number) {
  const safeUser = username.replace(/[^a-zA-Z0-9-_]/g, "_")
  const safeProject = projectName.replace(/[^a-zA-Z0-9-_]/g, "_")
  return `${safeUser}/${safeProject}/clips/${clipNumber}.mp4`
}

export async function uploadToS3(buffer: Buffer, key: string, contentType: string) {
  const client = getS3Client()
  const bucket = getBucketName()

  await client.send(
    new PutObjectCommand({
      Bucket: bucket,
      Key: key,
      Body: buffer,
      ContentType: contentType,
    })
  )

  return `s3://${bucket}/${key}`
}

export async function getPresignedUrl(key: string) {
  const client = getS3Client()
  const bucket = getBucketName()

  const command = new PutObjectCommand({
    Bucket: bucket,
    Key: key,
  })

  return getSignedUrl(client, command, { expiresIn: 3600 })
}

/**
 * Download a file from S3 to local path
 */
export async function downloadFromS3(s3Key: string, localPath: string): Promise<void> {
  const client = getS3Client()
  const bucket = getBucketName()

  const command = new GetObjectCommand({
    Bucket: bucket,
    Key: s3Key,
  })

  const response = await client.send(command)

  if (!response.Body) {
    throw new Error(`No data returned from S3 for key: ${s3Key}`)
  }

  // Convert body to stream and write to file
  const stream = response.Body as Readable
  const writeStream = fs.createWriteStream(localPath)

  return new Promise((resolve, reject) => {
    stream.pipe(writeStream)
    writeStream.on('finish', resolve)
    writeStream.on('error', reject)
  })
}

/**
 * Upload a file from local path to S3
 */
export async function uploadFileToS3(localPath: string, s3Key: string): Promise<string> {
  const client = getS3Client()
  const bucket = getBucketName()

  const fileContent = fs.readFileSync(localPath)

  await client.send(
    new PutObjectCommand({
      Bucket: bucket,
      Key: s3Key,
      Body: fileContent,
      ContentType: 'video/mp4',
    })
  )

  // Return public URL
  const region = process.env.AWS_REGION
  return `https://${bucket}.s3.${region}.amazonaws.com/${s3Key}`
}

/**
 * Generate S3 key for final video
 */
export function generateFinalVideoKey(username: string, projectName: string): string {
  const safeUser = username.replace(/[^a-zA-Z0-9-_]/g, "_")
  const safeProject = projectName.replace(/[^a-zA-Z0-9-_]/g, "_")
  return `${safeUser}/${safeProject}/final-video.mp4`
}

/**
 * Get public S3 URL for a key
 */
export function getS3Url(s3Key: string): string {
  const bucket = getBucketName()
  const region = process.env.AWS_REGION || 'us-east-1'
  return `https://${bucket}.s3.${region}.amazonaws.com/${s3Key}`
}
