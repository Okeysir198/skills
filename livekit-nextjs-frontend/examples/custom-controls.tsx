/**
 * Custom Controls Component
 *
 * Shows how to build custom UI controls using LiveKit hooks
 * instead of the default VideoConference component.
 */

'use client';

import {
  useRoom,
  useLocalParticipant,
  useTrackToggle,
  useTracks,
  VideoTrack,
} from '@livekit/components-react';
import { Track } from 'livekit-client';
import { Mic, MicOff, Video, VideoOff, PhoneOff, Monitor } from 'lucide-react';

/**
 * Note: This example uses lucide-react for icons. Install with:
 * npm install lucide-react
 *
 * Alternatively, use text labels or your own icon solution.
 */

export function CustomControls() {
  const room = useRoom();
  const { localParticipant } = useLocalParticipant();

  // Use built-in hooks for track toggling (BEST PRACTICE)
  const { buttonProps: audioProps, enabled: audioEnabled } = useTrackToggle({
    source: Track.Source.Microphone,
  });

  const { buttonProps: videoProps, enabled: videoEnabled } = useTrackToggle({
    source: Track.Source.Camera,
  });

  const { buttonProps: screenProps, enabled: screenEnabled } = useTrackToggle({
    source: Track.Source.ScreenShare,
  });

  const handleDisconnect = () => {
    room.disconnect();
    // Redirect or show disconnected state
  };

  return (
    <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 flex gap-2 bg-gray-800 rounded-full px-4 py-3 shadow-lg">
      {/* Audio Toggle */}
      <button
        {...audioProps}
        className={`p-3 rounded-full transition-colors ${
          audioEnabled
            ? 'bg-gray-700 hover:bg-gray-600 text-white'
            : 'bg-red-500 hover:bg-red-600 text-white'
        }`}
        title={audioEnabled ? 'Mute microphone' : 'Unmute microphone'}
      >
        {audioEnabled ? <Mic size={20} /> : <MicOff size={20} />}
      </button>

      {/* Video Toggle */}
      <button
        {...videoProps}
        className={`p-3 rounded-full transition-colors ${
          videoEnabled
            ? 'bg-gray-700 hover:bg-gray-600 text-white'
            : 'bg-red-500 hover:bg-red-600 text-white'
        }`}
        title={videoEnabled ? 'Stop video' : 'Start video'}
      >
        {videoEnabled ? <Video size={20} /> : <VideoOff size={20} />}
      </button>

      {/* Screen Share Toggle */}
      <button
        {...screenProps}
        className={`p-3 rounded-full transition-colors ${
          screenEnabled
            ? 'bg-blue-500 hover:bg-blue-600 text-white'
            : 'bg-gray-700 hover:bg-gray-600 text-white'
        }`}
        title={screenEnabled ? 'Stop sharing' : 'Share screen'}
      >
        <Monitor size={20} />
      </button>

      {/* Disconnect Button */}
      <button
        onClick={handleDisconnect}
        className="p-3 rounded-full bg-red-500 hover:bg-red-600 text-white transition-colors ml-2"
        title="Leave room"
      >
        <PhoneOff size={20} />
      </button>
    </div>
  );
}

export function ParticipantGrid() {
  // Subscribe to all camera tracks
  const tracks = useTracks([
    { source: Track.Source.Camera, withPlaceholder: true },
    { source: Track.Source.ScreenShare, withPlaceholder: false },
  ]);

  // Separate screen shares from cameras
  const screenShares = tracks.filter(t => t.source === Track.Source.ScreenShare);
  const cameras = tracks.filter(t => t.source === Track.Source.Camera);

  return (
    <div className="flex flex-col h-full">
      {/* Screen Share - Full Width */}
      {screenShares.length > 0 && (
        <div className="flex-1 bg-black">
          {screenShares.map((track) => (
            <div key={track.participant.sid} className="h-full">
              <VideoTrack
                trackRef={track}
                className="h-full w-full object-contain"
              />
              <div className="absolute bottom-2 left-2 bg-black/50 px-2 py-1 rounded text-white text-sm">
                {track.participant.identity}'s screen
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Camera Grid */}
      <div className={`grid gap-2 p-2 ${
        screenShares.length > 0
          ? 'grid-cols-4 h-32'
          : 'grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 flex-1'
      }`}>
        {cameras.map((track) => (
          <div
            key={track.participant.sid}
            className="relative bg-gray-900 rounded-lg overflow-hidden"
          >
            <VideoTrack
              trackRef={track}
              className="h-full w-full object-cover"
            />

            {/* Participant Name Overlay */}
            <div className="absolute bottom-2 left-2 bg-black/50 px-2 py-1 rounded text-white text-sm">
              {track.participant.identity}
              {track.participant.isSpeaking && (
                <span className="ml-2 inline-block w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
              )}
            </div>

            {/* Audio Indicator */}
            {!track.participant.isMicrophoneEnabled && (
              <div className="absolute top-2 right-2 bg-red-500 p-1 rounded">
                <MicOff size={16} className="text-white" />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// Usage in a page component:
export function CustomRoomUI() {
  return (
    <div className="h-screen relative">
      <ParticipantGrid />
      <CustomControls />
    </div>
  );
}
