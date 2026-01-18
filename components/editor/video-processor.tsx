'use client'

import { useState } from 'react'
import { processProjectVideoBrowser } from '@/lib/services/browser-ffmpeg'
import { uploadToS3, generateFinalVideoKey } from '@/lib/s3'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'

interface VideoProcessorProps {
  projectId: string
  projectName: string
  username: string
  clips: Array<{ s3Url: string; filename: string; clipNumber: number }>
  gumloopMatches: any[]
  onComplete: (finalVideoUrl: string) => void
  onError: (error: string) => void
}

export default function VideoProcessor({
  projectId,
  projectName,
  username,
  clips,
  gumloopMatches,
  onComplete,
  onError,
}: VideoProcessorProps) {
  const [processing, setProcessing] = useState(false)
  const [stage, setStage] = useState('')
  const [progress, setProgress] = useState(0)

  const processVideo = async () => {
    setProcessing(true)
    setStage('Starting...')
    setProgress(0)

    try {
      // Process video in browser
      const finalVideoBlob = await processProjectVideoBrowser(
        clips,
        gumloopMatches,
        (currentStage, currentProgress) => {
          setStage(currentStage)
          setProgress(currentProgress)
        }
      )

      // Upload to S3
      setStage('Uploading to S3...')
      setProgress(95)

      const s3Key = generateFinalVideoKey(username, projectName)
      const finalVideoUrl = await uploadToS3(
        Buffer.from(await finalVideoBlob.arrayBuffer()),
        s3Key,
        'video/mp4'
      )

      setStage('Complete!')
      setProgress(100)

      // Update project in database
      await fetch(`/api/project/${projectId}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ finalVideoUrl, finalVideoS3Key: s3Key }),
      })

      onComplete(finalVideoUrl)
    } catch (error) {
      console.error('Error processing video:', error)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      onError(errorMessage)

      // Update project status to failed
      await fetch(`/api/project/${projectId}/fail`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error: errorMessage }),
      })
    } finally {
      setProcessing(false)
    }
  }

  if (!processing) {
    return (
      <Button onClick={processVideo} className="w-full">
        Process Video (Browser)
      </Button>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <div className="mb-2 flex justify-between text-sm">
          <span className="font-medium">{stage}</span>
          <span className="text-muted-foreground">{progress}%</span>
        </div>
        <Progress value={progress} />
      </div>
      <p className="text-xs text-muted-foreground">
        Processing in your browser... Please keep this tab open.
      </p>
    </div>
  )
}
