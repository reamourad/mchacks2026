export async function createVideoWithBackend(
  username: string,
  projectName: string,
  gumloopMatches: unknown[]
): Promise<{ videoUrl: string; s3Key: string }> {
  const endpoint = process.env.NEXT_PUBLIC_BACKEND_VIDEO_ENDPOINT

  if (!endpoint) {
    throw new Error(
      "Missing NEXT_PUBLIC_BACKEND_VIDEO_ENDPOINT. Configure it to point to the backend service that renders the final video."
    )
  }

  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, projectName, gumloopMatches }),
  })

  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(`Backend video processing failed (${res.status}): ${text}`)
  }

  const data = (await res.json()) as Partial<{ videoUrl: string; s3Key: string }>

  if (!data.videoUrl || !data.s3Key) {
    throw new Error("Backend response missing videoUrl or s3Key")
  }

  return { videoUrl: data.videoUrl, s3Key: data.s3Key }
}
