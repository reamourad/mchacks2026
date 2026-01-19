'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"

interface TimelineProps {
  status: 'uploading' | 'processing' | 'completed' | 'failed'
  gumloopMatches?: any[]
  finalVideoUrl?: string
  error?: string
}

export default function Timeline({
  status,
  gumloopMatches,
  finalVideoUrl,
  error,
}: TimelineProps) {
  const getStatusDisplay = () => {
    switch (status) {
      case 'uploading':
        return { text: 'Ready to upload clips', progress: 0, color: 'bg-blue-500' }
      case 'processing':
        return { text: 'Processing video...', progress: 50, color: 'bg-yellow-500' }
      case 'completed':
        return { text: 'Video completed!', progress: 100, color: 'bg-green-500' }
      case 'failed':
        return { text: 'Processing failed', progress: 0, color: 'bg-red-500' }
      default:
        return { text: 'Unknown status', progress: 0, color: 'bg-gray-500' }
    }
  }

  const statusInfo = getStatusDisplay()

  const handleDownload = () => {
    if (finalVideoUrl) {
      window.open(finalVideoUrl, '_blank')
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Processing Status</CardTitle>
        <CardDescription>Track your video processing progress</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Status Progress */}
          <div>
            <div className="mb-2 flex justify-between items-center text-sm">
              <span className="font-medium">{statusInfo.text}</span>
              <span className="text-muted-foreground">{statusInfo.progress}%</span>
            </div>
            <Progress value={statusInfo.progress} className={statusInfo.color} />
          </div>

          {/* Status Badge */}
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${statusInfo.color}`} />
            <span className="text-sm capitalize">{status}</span>
          </div>

          {/* Error Message */}
          {status === 'failed' && error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
              <p className="text-sm text-red-800 dark:text-red-200 font-medium">Error:</p>
              <p className="text-sm text-red-700 dark:text-red-300 mt-1">{error}</p>
            </div>
          )}

          {/* Processing Info */}
          {status === 'processing' && (
            <div className="p-3 bg-muted rounded-md">
              <p className="text-sm text-muted-foreground">
                Your video is being processed. This may take a few minutes depending on the
                number and length of clips.
              </p>
            </div>
          )}

          {/* Gumloop Matches */}
          {gumloopMatches && gumloopMatches.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium">Video Segments ({gumloopMatches.length})</h3>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {gumloopMatches.map((match, index) => (
                  <div
                    key={index}
                    className="p-3 border rounded-md text-sm space-y-1"
                  >
                    <div className="flex justify-between items-start">
                      <span className="font-medium">Segment {match.segment_id}</span>
                      <span className="text-xs text-muted-foreground">{match.segment_time}</span>
                    </div>
                    <p className="text-muted-foreground text-xs">{match.segment_description}</p>
                    <p className="text-muted-foreground text-xs italic">
                      Reason: {match.reason}
                    </p>
                    <div className="flex justify-between items-center pt-1">
                      <span className="text-xs">
                        Clip: <span className="font-medium">{match.matched_clip}</span>
                      </span>
                      <span className="text-xs text-muted-foreground">{match.clip_timestamp}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Final Video */}
          {status === 'completed' && finalVideoUrl && (
            <div className="space-y-4">
              <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md">
                <p className="text-sm text-green-800 dark:text-green-200 font-medium mb-2">
                  Video processing complete!
                </p>
                <p className="text-xs text-green-700 dark:text-green-300">
                  Your video has been successfully processed and is ready to download.
                </p>
              </div>

              {/* Video Preview */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Preview</label>
                <video
                  src={finalVideoUrl}
                  controls
                  className="w-full rounded-md border"
                />
              </div>

              {/* Download Button */}
              <Button
                onClick={handleDownload}
                className="w-full"
                variant="default"
              >
                Download Video
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
