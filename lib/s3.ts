import { PutObjectCommand, S3Client } from "@aws-sdk/client-s3"
import { getSignedUrl } from "@aws-sdk/s3-request-presigner"

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
