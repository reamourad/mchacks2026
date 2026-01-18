import { NextRequest, NextResponse } from 'next/server';
import { auth0 } from '@/lib/auth0';
import { connectToDatabase } from '@/lib/mongodb';
import { PROJECTS_COLLECTION, Project } from '@/lib/models/Project';
import { ObjectId } from 'mongodb';
import { callGumloop } from '@/lib/services/gumloop';
// NOTE: Server-side ffmpeg processing disabled for Vercel deployment
// Use browser-based processing instead (see components/editor/video-processor.tsx)
// import { processProjectVideo } from '@/lib/services/ffmpeg';
// import { generateFinalVideoKey } from '@/lib/s3';

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

    // Step 2: Server-side video processing is disabled for Vercel
    // Use browser-based processing from the client instead
    console.log('Gumloop processing complete. Use browser-based video processing.');

    // Mark project as ready for client-side processing
    await projectsCollection.updateOne(
      { _id: new ObjectId(projectId) },
      {
        $set: {
          status: 'ready_for_processing', // Client will pick this up
          updatedAt: new Date(),
        },
      }
    );

    console.log(`Project ${projectId} ready for browser-based video processing`);
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
