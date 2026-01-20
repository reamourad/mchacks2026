'use client'

import { useMemo, useRef, useState, useEffect, useCallback } from 'react'
import { useUser } from '@auth0/nextjs-auth0/client'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Download, Search, Settings, Type, Upload as UploadIcon, Loader2, Play } from "lucide-react"
import {
  projectsAPI,
  assetsAPI,
  clipsAPI,
  exportAPI,
  uploadFilesAsClips,
  type Project,
  type Asset,
  type TimelineClip,
  type TranscriptEntry,
} from "@/lib/api"

interface UploadProgress {
  [fileIndex: number]: number
}

export default function Editor() {
  const { user, isLoading: authLoading } = useUser()

  // Project state
  const [projectId, setProjectId] = useState<string | null>(null)
  const [projectName, setProjectName] = useState('')
  const [project, setProject] = useState<Project | null>(null)
  const [assets, setAssets] = useState<Asset[]>([])

  // UI state
  const [creating, setCreating] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<UploadProgress>({})
  const [exporting, setExporting] = useState(false)
  const [exportedVideoUrl, setExportedVideoUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [aspect, setAspect] = useState<'16:9' | '9:16'>('9:16')
  const [isFontPickerOpen, setIsFontPickerOpen] = useState(false)
  const [fontSearch, setFontSearch] = useState('')
  const [selectedFont, setSelectedFont] = useState<
    | 'Playfair Display'
    | 'Bowlby One SC'
    | 'Playwrite NG Modern'
    | 'Cherry Bomb One'
    | 'Limelight'
    | 'Monsieur La Doulaise'
  >('Playfair Display')

  const fileInputRef = useRef<HTMLInputElement>(null)

  const fontOptions = useMemo(
    () => [
      { label: 'Playfair Display' as const, fontFamily: 'var(--font-playfair)' },
      { label: 'Bowlby One SC' as const, fontFamily: 'var(--font-bowlby)' },
      { label: 'Playwrite NG Modern' as const, fontFamily: '"Playwrite NG Modern"' },
      { label: 'Cherry Bomb One' as const, fontFamily: 'var(--font-cherry-bomb-one)' },
      { label: 'Limelight' as const, fontFamily: 'var(--font-limelight)' },
      { label: 'Monsieur La Doulaise' as const, fontFamily: 'var(--font-monsieur-la-doulaise)' },
    ],
    []
  )

  const selectedFontFamily = useMemo(() => {
    return fontOptions.find((f) => f.label === selectedFont)?.fontFamily
  }, [fontOptions, selectedFont])

  const filteredFontOptions = useMemo(() => {
    const q = fontSearch.trim().toLowerCase()
    if (!q) return fontOptions
    return fontOptions.filter((f) => f.label.toLowerCase().includes(q))
  }, [fontOptions, fontSearch])

  const clips = useMemo(() => project?.clips || [], [project?.clips])

  // Refresh project data
  const refreshProject = useCallback(async () => {
    if (!projectId) return
    try {
      const [proj, assetList] = await Promise.all([
        projectsAPI.get(projectId),
        assetsAPI.list(projectId),
      ])
      setProject(proj)
      setAssets(assetList)
    } catch (err) {
      console.error('Failed to refresh project:', err)
    }
  }, [projectId])

  // Poll for project status when processing
  useEffect(() => {
    if (!projectId || project?.status === 'completed' || project?.status === 'failed') {
      return
    }
    if (project?.status !== 'processing') return

    const pollInterval = setInterval(async () => {
      await refreshProject()
    }, 3000)

    return () => clearInterval(pollInterval)
  }, [projectId, project?.status, refreshProject])

  // Create project
  const createProject = async () => {
    if (!projectName.trim()) return

    setCreating(true)
    setError(null)

    try {
      const newProject = await projectsAPI.create(projectName.trim())
      setProjectId(newProject.id)
      setProject(newProject)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project')
    } finally {
      setCreating(false)
    }
  }

  // Upload files
  const uploadFiles = async (filesOverride?: File[]) => {
    const filesToUpload = filesOverride || selectedFiles
    if (!projectId || filesToUpload.length === 0) return

    setUploading(true)
    setError(null)
    setUploadProgress({})

    try {
      const { clips: newClips } = await uploadFilesAsClips(
        projectId,
        filesToUpload,
        (fileIndex, progress) => {
          setUploadProgress((prev) => ({ ...prev, [fileIndex]: progress }))
        }
      )

      // Refresh project to get updated clips
      await refreshProject()
      setSelectedFiles([])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload files')
    } finally {
      setUploading(false)
      setUploadProgress({})
    }
  }

  // Export video
  const handleExport = async () => {
    if (!projectId || clips.length === 0) return

    setExporting(true)
    setError(null)

    try {
      // For now, export without transcript (no subtitles)
      // You can add transcript data here when you have it
      const transcript: TranscriptEntry[] = []

      const result = await exportAPI.exportProject(projectId, transcript)
      setExportedVideoUrl(result.video_url)

      // Update project status
      await refreshProject()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export video')
    } finally {
      setExporting(false)
    }
  }

  const handleCenterUploadClick = () => {
    if (authLoading) return
    if (!user) {
      window.location.href = '/api/auth/login'
      return
    }
    fileInputRef.current?.click()
  }

  const downloadVideo = () => {
    const url = exportedVideoUrl || project?.voiceover?.s3_url
    if (url) {
      window.open(url, '_blank')
    }
  }

  // Get asset info for a clip
  const getAssetForClip = (clip: TimelineClip): Asset | undefined => {
    return assets.find((a) => a.id === clip.asset_id)
  }

  return (
    <main className="min-h-screen bg-[#151E23] text-foreground">
      <div className="flex h-screen flex-col">
        {/* Header */}
        <header className="flex h-14 items-center justify-between border-b border-foreground/10 px-4">
          <div className="text-sm text-foreground/60">
            {project ? project.title : 'Video Editor'}
          </div>

          <div className="flex items-center gap-2 rounded-lg border border-foreground/10 bg-black/20 p-1">
            <button
              type="button"
              onClick={() => setAspect('16:9')}
              className={`rounded-md px-3 py-1 text-xs transition-colors ${
                aspect === '16:9'
                  ? 'bg-primary text-[#151E23]'
                  : 'text-foreground/70 hover:bg-white/5'
              }`}
            >
              16:9
            </button>
            <button
              type="button"
              onClick={() => setAspect('9:16')}
              className={`rounded-md px-3 py-1 text-xs transition-colors ${
                aspect === '9:16'
                  ? 'bg-primary text-[#151E23]'
                  : 'text-foreground/70 hover:bg-white/5'
              }`}
            >
              9:16
            </button>
          </div>

          <div className="flex items-center gap-2">
            <Button
              onClick={handleExport}
              disabled={exporting || clips.length === 0}
              variant="outline"
              className="gap-2"
            >
              {exporting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Exporting...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Export
                </>
              )}
            </Button>
            <Button
              onClick={downloadVideo}
              disabled={!exportedVideoUrl}
              className="gap-2"
            >
              <Download className="h-4 w-4" />
              Download
            </Button>
          </div>
        </header>

        {/* Error banner */}
        {error && (
          <div className="bg-red-500/20 border-b border-red-500/30 px-4 py-2 text-sm text-red-300">
            {error}
            <button
              onClick={() => setError(null)}
              className="ml-4 text-red-400 hover:text-red-200"
            >
              Dismiss
            </button>
          </div>
        )}

        <div className="flex min-h-0 flex-1">
          {/* Left Sidebar */}
          <aside className="hidden w-[300px] flex-shrink-0 border-r border-foreground/10 bg-black/20 p-4 md:block">
            <div className="mb-4 flex items-center justify-between">
              <div className="text-sm font-semibold">Fonts Library</div>
            </div>

            <div className="mb-4 flex items-center gap-2 rounded-lg border border-foreground/10 bg-black/20 px-3 py-2">
              <Search className="h-4 w-4 text-foreground/60" />
              <input
                className="w-full bg-transparent text-sm text-foreground outline-none placeholder:text-foreground/40"
                placeholder="Search fonts..."
                value={fontSearch}
                onChange={(e) => setFontSearch(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              {isFontPickerOpen ? (
                filteredFontOptions.length === 0 ? (
                  <div className="rounded-lg border border-foreground/10 bg-black/20 px-3 py-3 text-sm text-foreground/60">
                    No fonts found
                  </div>
                ) : (
                  filteredFontOptions.map((font) => {
                    const isSelected = font.label === selectedFont
                    return (
                      <button
                        key={font.label}
                        type="button"
                        onClick={() => setSelectedFont(font.label)}
                        className={`w-full rounded-lg border px-3 py-3 text-left transition-colors ${
                          isSelected
                            ? 'border-primary/40 bg-black/20'
                            : 'border-foreground/10 bg-black/20 hover:bg-white/5'
                        }`}
                      >
                        <div className="text-[10px] uppercase tracking-wider text-foreground/50">Font</div>
                        <div className="mt-1 text-sm font-semibold text-foreground">{font.label}</div>
                        <div className="mt-1 text-xs text-foreground/60" style={{ fontFamily: font.fontFamily }}>
                          The quick brown fox jumps...
                        </div>
                      </button>
                    )
                  })
                )
              ) : (
                <div className="rounded-lg border border-foreground/10 bg-black/20 px-3 py-3 text-sm text-foreground/60">
                  Press the <span className="text-foreground">T</span> tool to browse fonts
                </div>
              )}
            </div>

            {/* Project controls */}
            <div className="mt-6 border-t border-foreground/10 pt-4">
              {authLoading ? (
                <div className="text-xs text-foreground/60">Loading...</div>
              ) : !user ? (
                <div className="text-xs text-foreground/60">Log in to upload clips</div>
              ) : (
                <div className="space-y-3">
                  {!projectId && (
                    <div className="space-y-2">
                      <div className="text-xs font-semibold text-foreground/80">Create Project</div>
                      <Input
                        value={projectName}
                        onChange={(e) => setProjectName(e.target.value)}
                        placeholder="Project name"
                        disabled={creating}
                        onKeyDown={(e) => e.key === 'Enter' && createProject()}
                      />
                      <Button
                        onClick={createProject}
                        disabled={creating || !projectName.trim()}
                        className="w-full"
                      >
                        {creating ? 'Creating...' : 'Create Project'}
                      </Button>
                    </div>
                  )}

                  {projectId && (
                    <div className="space-y-2">
                      <div className="text-xs text-foreground/60">
                        Project: <span className="text-foreground/90">{project?.title}</span>
                      </div>

                      <Button
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploading}
                        variant="outline"
                        className="w-full gap-2"
                      >
                        <UploadIcon className="h-4 w-4" />
                        {uploading ? 'Uploading...' : 'Add Clips'}
                      </Button>

                      {clips.length > 0 && (
                        <Button
                          onClick={handleExport}
                          disabled={exporting || clips.length === 0}
                          className="w-full gap-2"
                        >
                          {exporting ? (
                            <>
                              <Loader2 className="h-4 w-4 animate-spin" />
                              Exporting...
                            </>
                          ) : (
                            <>
                              <Play className="h-4 w-4" />
                              Export Video
                            </>
                          )}
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </aside>

          {/* Main content */}
          <section className="relative flex min-h-0 flex-1 flex-col">
            {/* Canvas area */}
            <div className="relative flex min-h-0 flex-1 items-center justify-center p-6">
              <div
                className="absolute inset-0 opacity-30"
                style={{
                  backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(241,250,238,0.15) 1px, transparent 0)',
                  backgroundSize: '22px 22px',
                }}
              />

              <div
                className={`relative rounded-xl border border-foreground/10 bg-black/30 p-6 shadow-[0_30px_80px_rgba(0,0,0,0.6)] ${
                  aspect === '16:9' ? 'w-full max-w-4xl' : 'w-auto max-w-full'
                }`}
              >
                <div
                  className={`mx-auto overflow-hidden rounded-lg border border-foreground/10 bg-black/40 ${
                    aspect === '16:9' ? 'w-full' : 'w-auto'
                  }`}
                >
                  <div
                    className={`mx-auto max-h-[calc(100vh-56px-240px-48px)] ${
                      aspect === '16:9'
                        ? 'aspect-video w-full'
                        : 'aspect-[9/16] h-[calc(100vh-56px-240px-48px)] w-auto max-w-full'
                    }`}
                  >
                    {/* Hidden file input */}
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="video/*"
                      multiple
                      className="hidden"
                      onChange={(e) => {
                        const files = e.target.files ? Array.from(e.target.files) : []
                        setSelectedFiles(files)
                        if (files.length > 0 && projectId) {
                          void uploadFiles(files)
                        }
                      }}
                      disabled={uploading}
                    />

                    {/* Text overlay preview */}
                    <div className="pointer-events-none absolute inset-0 flex items-start justify-center pt-10 z-10">
                      <div
                        className="rounded-lg border border-foreground/10 bg-black/30 px-4 py-2 text-2xl text-foreground shadow-sm"
                        style={{ fontFamily: selectedFontFamily }}
                      >
                        Add text
                      </div>
                    </div>

                    {/* Video preview or upload button */}
                    {exportedVideoUrl ? (
                      <video
                        className="h-full w-full object-cover"
                        src={exportedVideoUrl}
                        controls
                        playsInline
                      />
                    ) : (
                      <div className="flex h-full w-full flex-col items-center justify-center gap-4 text-sm text-foreground/60">
                        {exporting ? (
                          <>
                            <Loader2 className="h-8 w-8 animate-spin text-primary" />
                            <div>Exporting your video...</div>
                          </>
                        ) : (
                          <>
                            <Button
                              type="button"
                              onClick={handleCenterUploadClick}
                              disabled={uploading || authLoading}
                              className="h-12 rounded-xl px-6"
                            >
                              {uploading ? 'Uploading...' : projectId ? 'Add clips' : 'Upload video'}
                            </Button>
                            <div>
                              {clips.length > 0
                                ? `${clips.length} clip${clips.length > 1 ? 's' : ''} ready - click Export`
                                : 'Upload clips to preview your edit here'}
                            </div>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Right toolbar */}
              <div className="absolute right-4 top-1/2 hidden -translate-y-1/2 flex-col gap-2 md:flex">
                <button className="flex h-11 w-11 items-center justify-center rounded-xl border border-foreground/10 bg-black/25 text-foreground/80 hover:bg-white/5">
                  <Search className="h-5 w-5" />
                </button>
                <button
                  type="button"
                  onClick={() => setIsFontPickerOpen((v) => !v)}
                  className={`flex h-11 w-11 items-center justify-center rounded-xl border bg-black/25 hover:bg-white/5 ${
                    isFontPickerOpen
                      ? 'border-primary/40 text-primary'
                      : 'border-foreground/10 text-foreground/80'
                  }`}
                >
                  <Type className="h-5 w-5" />
                </button>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={!projectId || uploading}
                  className="flex h-11 w-11 items-center justify-center rounded-xl border border-foreground/10 bg-black/25 text-foreground/80 hover:bg-white/5 disabled:opacity-50"
                >
                  <UploadIcon className="h-5 w-5" />
                </button>
                <button className="flex h-11 w-11 items-center justify-center rounded-xl border border-foreground/10 bg-black/25 text-foreground/80 hover:bg-white/5">
                  <Settings className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Timeline */}
            <div className="h-[240px] border-t border-foreground/10 bg-black/25">
              <div className="flex h-full flex-col">
                <div className="flex items-center justify-between border-b border-foreground/10 px-4 py-2">
                  <div className="text-xs text-foreground/70">
                    {exporting ? 'Exporting...' : project?.status ? `Status: ${project.status}` : 'Status: idle'}
                  </div>
                  <div className="text-xs text-foreground/50">
                    Timeline ({clips.length} clip{clips.length !== 1 ? 's' : ''})
                  </div>
                </div>

                <div className="min-h-0 flex-1 overflow-auto p-4">
                  {clips.length === 0 ? (
                    <div className="text-sm text-foreground/60">
                      {projectId
                        ? 'No clips yet. Click "Add Clips" to upload videos.'
                        : 'Create a project first to start adding clips.'}
                    </div>
                  ) : (
                    <div className="flex gap-3 overflow-x-auto pb-2">
                      {clips
                        .sort((a, b) => a.order - b.order)
                        .map((clip, index) => {
                          const asset = getAssetForClip(clip)
                          return (
                            <div
                              key={clip.id}
                              className="flex-shrink-0 w-48 rounded-lg border border-foreground/10 bg-black/20 p-3"
                            >
                              <div className="flex items-center justify-between mb-2">
                                <div className="text-xs font-medium text-foreground/80">
                                  Clip {index + 1}
                                </div>
                                <div className="text-[10px] text-foreground/50">
                                  {(clip.end_time - clip.start_time).toFixed(1)}s
                                </div>
                              </div>
                              <div className="text-xs text-foreground/60 truncate">
                                {asset?.filename || 'Loading...'}
                              </div>
                              <div className="mt-2 h-1.5 w-full rounded-full bg-white/10">
                                <div
                                  className="h-1.5 rounded-full bg-primary"
                                  style={{ width: '100%' }}
                                />
                              </div>
                            </div>
                          )
                        })}
                    </div>
                  )}

                  {/* Upload progress */}
                  {uploading && Object.keys(uploadProgress).length > 0 && (
                    <div className="mt-4 space-y-2">
                      <div className="text-xs text-foreground/60">Uploading files...</div>
                      {selectedFiles.map((file, index) => (
                        <div key={file.name} className="rounded-lg border border-foreground/10 bg-black/20 p-3">
                          <div className="flex items-center justify-between mb-1">
                            <div className="text-xs text-foreground/80 truncate">{file.name}</div>
                            <div className="text-xs text-foreground/50">{uploadProgress[index] || 0}%</div>
                          </div>
                          <div className="h-1.5 w-full rounded-full bg-white/10">
                            <div
                              className="h-1.5 rounded-full bg-primary transition-all"
                              style={{ width: `${uploadProgress[index] || 0}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>
  )
}
