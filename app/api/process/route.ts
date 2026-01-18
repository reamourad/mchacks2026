import { NextRequest, NextResponse } from 'next/server';
import { auth0 } from '@/lib/auth0';
import { connectToDatabase } from '@/lib/mongodb';
import { PROJECTS_COLLECTION, Project } from '@/lib/models/Project';
import { ObjectId } from 'mongodb';
import { callGumloop } from '@/lib/services/gumloop';
import { processProjectVideo } from '@/lib/services/ffmpeg';
import { generateFinalVideoKey } from '@/lib/s3';

export async function POST(request: NextRequest) {
  try {
    // Verify authentication
    const session = await auth0.getSession(request);

    if (!session || !session.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const userId = session.user.sub;

    // Parse request body
    const body = await request.json();
    const { projectId } = body;

    if (!projectId) {
      return NextResponse.json(
        { error: 'Project ID is required' },
        { status: 400 }
      );
    }

    // Validate project ID format
    if (!ObjectId.isValid(projectId)) {
      return NextResponse.json(
        { error: 'Invalid project ID' },
        { status: 400 }
      );
    }

    // Connect to database
    const { db } = await connectToDatabase();
    const projectsCollection = db.collection(PROJECTS_COLLECTION);

    // Find project and verify ownership
    const project = await projectsCollection.findOne({
      _id: new ObjectId(projectId),
      userId,
    });

    if (!project) {
      return NextResponse.json(
        { error: 'Project not found or access denied' },
        { status: 404 }
      );
    }

    // Check if project has clips
    if (!project.clips || project.clips.length === 0) {
      return NextResponse.json(
        { error: 'Project has no clips uploaded' },
        { status: 400 }
      );
    }

    // Update status to processing
    await projectsCollection.updateOne(
      { _id: new ObjectId(projectId) },
      {
        $set: {
          status: 'processing',
          updatedAt: new Date(),
        },
      }
    );

    // Start async processing (don't await)
    processVideoAsync(project as Project, projectId).catch((error) => {
      console.error('Background processing error:', error);
    });

    return NextResponse.json(
      {
        message: 'Video processing started',
        projectId,
        status: 'processing',
      },
      { status: 200 }
    );
  } catch (error) {
    console.error('Error starting video processing:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * Background async function to process video
 */
async function processVideoAsync(project: Project, projectId: string) {
  const { db } = await connectToDatabase();
  const projectsCollection = db.collection(PROJECTS_COLLECTION);

  try {
    console.log(`Starting video processing for project: ${projectId}`);

    // Step 1: Call Gumloop API
    console.log('Calling Gumloop API...');
    const gumloopMatches = await callGumloop(project.username, project.projectName);

    console.log(`Received ${gumloopMatches.length} matches from Gumloop`);

    // Save Gumloop output to project
    await projectsCollection.updateOne(
      { _id: new ObjectId(projectId) },
      {
        $set: {
          gumloopOutput: gumloopMatches,
          updatedAt: new Date(),
        },
      }
    );

    // Step 2: Process video with FFmpeg
    console.log('Processing video with FFmpeg...');

    // Reload project with Gumloop output
    const updatedProject = await projectsCollection.findOne({
      _id: new ObjectId(projectId),
    });

    if (!updatedProject) {
      throw new Error('Project not found after Gumloop update');
    }

    const finalVideoUrl = await processProjectVideo(updatedProject as Project);

    console.log(`Video processing complete: ${finalVideoUrl}`);

    // Step 3: Update project with final video URL and status
    const finalS3Key = generateFinalVideoKey(project.username, project.projectName);

    await projectsCollection.updateOne(
      { _id: new ObjectId(projectId) },
      {
        $set: {
          status: 'completed',
          finalVideoUrl,
          finalVideoS3Key: finalS3Key,
          updatedAt: new Date(),
        },
      }
    );

    console.log(`Project ${projectId} completed successfully`);
  } catch (error) {
    console.error(`Error processing video for project ${projectId}:`, error);

    // Update project status to failed
    await projectsCollection.updateOne(
      { _id: new ObjectId(projectId) },
      {
        $set: {
          status: 'failed',
          error: error instanceof Error ? error.message : 'Unknown error',
          updatedAt: new Date(),
        },
      }
    );
  }
}
