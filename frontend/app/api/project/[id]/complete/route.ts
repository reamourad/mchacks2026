import { NextRequest, NextResponse } from 'next/server';
import { auth0 } from '@/lib/auth0';
import { connectToDatabase } from '@/lib/mongodb';
import { PROJECTS_COLLECTION } from '@/lib/models/Project';
import { ObjectId } from 'mongodb';

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    // Verify authentication
    const session = await auth0.getSession(request);

    if (!session || !session.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const userId = session.user.sub;
    const projectId = params.id;

    const body = await request.json();
    const { finalVideoUrl, finalVideoS3Key } = body;

    if (!finalVideoUrl || !finalVideoS3Key) {
      return NextResponse.json(
        { error: 'Final video URL and S3 key are required' },
        { status: 400 }
      );
    }

    // Connect to database
    const { db } = await connectToDatabase();
    const projectsCollection = db.collection(PROJECTS_COLLECTION);

    // Update project
    const result = await projectsCollection.updateOne(
      {
        _id: new ObjectId(projectId),
        userId,
      },
      {
        $set: {
          status: 'completed',
          finalVideoUrl,
          finalVideoS3Key,
          updatedAt: new Date(),
        },
      }
    );

    if (result.matchedCount === 0) {
      return NextResponse.json(
        { error: 'Project not found or access denied' },
        { status: 404 }
      );
    }

    return NextResponse.json({ message: 'Project completed successfully' });
  } catch (error) {
    console.error('Error completing project:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
