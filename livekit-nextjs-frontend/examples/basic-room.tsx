/**
 * Basic Room Component
 *
 * A minimal example showing how to connect to a LiveKit room
 * with token authentication and basic video conferencing UI.
 */

'use client';

import { LiveKitRoom, VideoConference } from '@livekit/components-react';
import '@livekit/components-styles';
import { useEffect, useState } from 'react';

interface BasicRoomProps {
  roomName: string;
  username: string;
}

export default function BasicRoom({ roomName, username }: BasicRoomProps) {
  const [token, setToken] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchToken() {
      try {
        setIsLoading(true);
        const response = await fetch(
          `/api/token?room=${encodeURIComponent(roomName)}&username=${encodeURIComponent(username)}`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch token');
        }

        const data = await response.json();
        setToken(data.token);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setIsLoading(false);
      }
    }

    if (roomName && username) {
      fetchToken();
    }
  }, [roomName, username]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p>Connecting to room...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center text-red-500">
          <h2 className="text-xl font-bold mb-2">Connection Error</h2>
          <p>{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p>No token available</p>
      </div>
    );
  }

  return (
    <LiveKitRoom
      token={token}
      serverUrl={process.env.NEXT_PUBLIC_LIVEKIT_URL!}
      connect={true}
      video={true}
      audio={true}
      onDisconnected={() => {
        console.log('Disconnected from room');
        // Handle disconnection (e.g., redirect to home page)
      }}
      onError={(error) => {
        console.error('Room error:', error);
        setError(error.message);
      }}
      className="h-screen"
    >
      {/* VideoConference provides a complete UI out of the box */}
      <VideoConference />
    </LiveKitRoom>
  );
}
