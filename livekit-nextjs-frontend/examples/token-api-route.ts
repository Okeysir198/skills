/**
 * Token Generation API Route
 *
 * Server-side API route for generating LiveKit access tokens.
 * This MUST be server-side to keep API secrets secure.
 *
 * For Next.js App Router: app/api/token/route.ts
 * For Next.js Pages Router: pages/api/token.ts
 */

import { AccessToken } from 'livekit-server-sdk';
import { NextRequest, NextResponse } from 'next/server';

// For App Router (Next.js 13+)
export async function GET(request: NextRequest) {
  // Extract parameters from URL
  const roomName = request.nextUrl.searchParams.get('room');
  const participantName = request.nextUrl.searchParams.get('username');

  // Validate required parameters
  if (!roomName) {
    return NextResponse.json(
      { error: 'Missing required parameter: room' },
      { status: 400 }
    );
  }

  if (!participantName) {
    return NextResponse.json(
      { error: 'Missing required parameter: username' },
      { status: 400 }
    );
  }

  // Validate environment variables
  if (!process.env.LIVEKIT_API_KEY || !process.env.LIVEKIT_API_SECRET) {
    console.error('Missing LIVEKIT_API_KEY or LIVEKIT_API_SECRET environment variables');
    return NextResponse.json(
      { error: 'Server configuration error' },
      { status: 500 }
    );
  }

  try {
    // Create access token
    const at = new AccessToken(
      process.env.LIVEKIT_API_KEY,
      process.env.LIVEKIT_API_SECRET,
      {
        identity: participantName,
        // Optional: set token name (appears in webhooks and logs)
        name: participantName,
        // Token expires after 6 hours by default, can be customized
        ttl: '6h',
      }
    );

    // Add grants (permissions) to the token
    at.addGrant({
      roomJoin: true,         // Allow joining the room
      room: roomName,         // Specific room name
      canPublish: true,       // Allow publishing tracks
      canSubscribe: true,     // Allow subscribing to other tracks
      canPublishData: true,   // Allow sending data messages

      // Optional: restrict to specific sources
      // canPublishSources: ['camera', 'microphone', 'screen_share'],

      // Optional: recording permissions
      // canUpdateOwnMetadata: true,
      // hidden: false,          // Whether participant is hidden
      // recorder: false,        // Whether this is a recorder participant
    });

    // Generate JWT token
    const token = await at.toJwt();

    return NextResponse.json({ token });
  } catch (error) {
    console.error('Error generating token:', error);
    return NextResponse.json(
      { error: 'Failed to generate token' },
      { status: 500 }
    );
  }
}

// For Pages Router (Next.js 12 and earlier)
// Uncomment this if using Pages Router instead of App Router:

/*
import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { room: roomName, username: participantName } = req.query;

  if (!roomName || typeof roomName !== 'string') {
    return res.status(400).json({ error: 'Missing required parameter: room' });
  }

  if (!participantName || typeof participantName !== 'string') {
    return res.status(400).json({ error: 'Missing required parameter: username' });
  }

  if (!process.env.LIVEKIT_API_KEY || !process.env.LIVEKIT_API_SECRET) {
    console.error('Missing LIVEKIT_API_KEY or LIVEKIT_API_SECRET environment variables');
    return res.status(500).json({ error: 'Server configuration error' });
  }

  try {
    const at = new AccessToken(
      process.env.LIVEKIT_API_KEY,
      process.env.LIVEKIT_API_SECRET,
      {
        identity: participantName,
        name: participantName,
        ttl: '6h',
      }
    );

    at.addGrant({
      roomJoin: true,
      room: roomName,
      canPublish: true,
      canSubscribe: true,
      canPublishData: true,
    });

    const token = await at.toJwt();

    return res.status(200).json({ token });
  } catch (error) {
    console.error('Error generating token:', error);
    return res.status(500).json({ error: 'Failed to generate token' });
  }
}
*/

/**
 * ADVANCED: Custom Permissions Based on User Role
 *
 * You can customize token permissions based on user roles or other criteria.
 */

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { room, username, role } = body;

    if (!room || !username) {
      return NextResponse.json(
        { error: 'Missing required parameters' },
        { status: 400 }
      );
    }

    const at = new AccessToken(
      process.env.LIVEKIT_API_KEY!,
      process.env.LIVEKIT_API_SECRET!,
      {
        identity: username,
        name: username,
        ttl: '6h',
        metadata: JSON.stringify({ role }), // Store role in metadata
      }
    );

    // Customize permissions based on role
    switch (role) {
      case 'host':
        at.addGrant({
          roomJoin: true,
          room,
          canPublish: true,
          canSubscribe: true,
          canPublishData: true,
          canUpdateOwnMetadata: true,
          roomAdmin: true,  // Can remove participants, update room metadata
        });
        break;

      case 'participant':
        at.addGrant({
          roomJoin: true,
          room,
          canPublish: true,
          canSubscribe: true,
          canPublishData: true,
        });
        break;

      case 'viewer':
        at.addGrant({
          roomJoin: true,
          room,
          canPublish: false,     // Viewers cannot publish
          canSubscribe: true,     // But can watch/listen
          canPublishData: false,  // Cannot send messages
          hidden: true,           // Hidden from participant list
        });
        break;

      default:
        return NextResponse.json(
          { error: 'Invalid role' },
          { status: 400 }
        );
    }

    const token = await at.toJwt();

    return NextResponse.json({ token });
  } catch (error) {
    console.error('Error generating token:', error);
    return NextResponse.json(
      { error: 'Failed to generate token' },
      { status: 500 }
    );
  }
}

/**
 * SECURITY CONSIDERATIONS:
 *
 * 1. Never expose API keys/secrets in client code
 * 2. Validate user identity before issuing tokens (integrate with your auth system)
 * 3. Implement rate limiting to prevent token abuse
 * 4. Use appropriate token TTL based on your use case
 * 5. Consider implementing token refresh logic for long sessions
 * 6. Log token generation for auditing
 * 7. Use HTTPS in production
 *
 * EXAMPLE: Integration with Auth
 *
 * import { getServerSession } from 'next-auth';
 *
 * export async function GET(request: NextRequest) {
 *   const session = await getServerSession();
 *
 *   if (!session) {
 *     return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
 *   }
 *
 *   const participantName = session.user.email || session.user.name;
 *   // ... rest of token generation
 * }
 */
