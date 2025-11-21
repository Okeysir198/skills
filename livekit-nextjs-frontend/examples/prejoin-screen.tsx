/**
 * Pre-Join Screen Component
 *
 * A lobby/pre-join screen that allows users to:
 * - Test their camera and microphone
 * - Choose their devices
 * - Set their display name
 * - Preview before joining the room
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import { createLocalVideoTrack, createLocalAudioTrack, LocalVideoTrack, LocalAudioTrack } from 'livekit-client';
import { Video, VideoOff, Mic, MicOff } from 'lucide-react';

/**
 * Note: This example uses lucide-react for icons. Install with:
 * npm install lucide-react
 *
 * Alternatively, use SVG icons, text labels, or your own icon solution.
 */

interface PreJoinScreenProps {
  roomName: string;
  onJoin: (config: JoinConfig) => void;
}

interface JoinConfig {
  username: string;
  videoEnabled: boolean;
  audioEnabled: boolean;
  videoDeviceId?: string;
  audioDeviceId?: string;
}

export function PreJoinScreen({ roomName, onJoin }: PreJoinScreenProps) {
  const [username, setUsername] = useState('');
  const [videoEnabled, setVideoEnabled] = useState(true);
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [videoTrack, setVideoTrack] = useState<LocalVideoTrack | null>(null);
  const [audioTrack, setAudioTrack] = useState<LocalAudioTrack | null>(null);
  const [videoDevices, setVideoDevices] = useState<MediaDeviceInfo[]>([]);
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedVideoDevice, setSelectedVideoDevice] = useState<string>('');
  const [selectedAudioDevice, setSelectedAudioDevice] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const videoRef = useRef<HTMLVideoElement>(null);

  // Enumerate devices
  useEffect(() => {
    async function getDevices() {
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoInputs = devices.filter(d => d.kind === 'videoinput');
        const audioInputs = devices.filter(d => d.kind === 'audioinput');

        setVideoDevices(videoInputs);
        setAudioDevices(audioInputs);

        if (videoInputs.length > 0) {
          setSelectedVideoDevice(videoInputs[0].deviceId);
        }
        if (audioInputs.length > 0) {
          setSelectedAudioDevice(audioInputs[0].deviceId);
        }
      } catch (err) {
        console.error('Error enumerating devices:', err);
        setError('Could not access media devices');
      }
    }

    getDevices();
  }, []);

  // Create and manage video track
  useEffect(() => {
    if (!videoEnabled || !selectedVideoDevice) {
      if (videoTrack) {
        videoTrack.stop();
        setVideoTrack(null);
      }
      return;
    }

    let mounted = true;

    async function startVideo() {
      try {
        setIsLoading(true);
        const track = await createLocalVideoTrack({
          deviceId: selectedVideoDevice,
          resolution: {
            width: 1280,
            height: 720,
            frameRate: 30,
          },
        });

        if (mounted) {
          setVideoTrack(track);
          setError('');
        } else {
          track.stop();
        }
      } catch (err) {
        console.error('Error creating video track:', err);
        if (mounted) {
          setError('Could not access camera');
          setVideoEnabled(false);
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    }

    startVideo();

    return () => {
      mounted = false;
      if (videoTrack) {
        videoTrack.stop();
      }
    };
  }, [videoEnabled, selectedVideoDevice]);

  // Create and manage audio track
  useEffect(() => {
    if (!audioEnabled || !selectedAudioDevice) {
      if (audioTrack) {
        audioTrack.stop();
        setAudioTrack(null);
      }
      return;
    }

    let mounted = true;

    async function startAudio() {
      try {
        const track = await createLocalAudioTrack({
          deviceId: selectedAudioDevice,
        });

        if (mounted) {
          setAudioTrack(track);
          setError('');
        } else {
          track.stop();
        }
      } catch (err) {
        console.error('Error creating audio track:', err);
        if (mounted) {
          setError('Could not access microphone');
          setAudioEnabled(false);
        }
      }
    }

    startAudio();

    return () => {
      mounted = false;
      if (audioTrack) {
        audioTrack.stop();
      }
    };
  }, [audioEnabled, selectedAudioDevice]);

  // Attach video track to video element
  useEffect(() => {
    if (videoRef.current && videoTrack) {
      videoTrack.attach(videoRef.current);
    }

    return () => {
      if (videoTrack) {
        videoTrack.detach();
      }
    };
  }, [videoTrack]);

  const handleJoin = () => {
    if (!username.trim()) {
      setError('Please enter your name');
      return;
    }

    // Clean up tracks (they'll be recreated when joining)
    if (videoTrack) videoTrack.stop();
    if (audioTrack) audioTrack.stop();

    onJoin({
      username: username.trim(),
      videoEnabled,
      audioEnabled,
      videoDeviceId: selectedVideoDevice,
      audioDeviceId: selectedAudioDevice,
    });
  };

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-2xl w-full bg-gray-800 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-4">
          <h1 className="text-2xl font-bold text-white">Join Room</h1>
          <p className="text-blue-100 text-sm">{roomName}</p>
        </div>

        <div className="p-6 space-y-6">
          {/* Video Preview */}
          <div className="relative aspect-video bg-gray-900 rounded-lg overflow-hidden">
            {videoEnabled && videoTrack ? (
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <VideoOff size={64} className="text-gray-600" />
              </div>
            )}

            {/* Loading Overlay */}
            {isLoading && videoEnabled && (
              <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white"></div>
              </div>
            )}

            {/* Controls Overlay */}
            <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex gap-2">
              <button
                onClick={() => setVideoEnabled(!videoEnabled)}
                aria-label={videoEnabled ? 'Turn off camera' : 'Turn on camera'}
                className={`p-3 rounded-full transition-colors ${
                  videoEnabled
                    ? 'bg-gray-700/80 hover:bg-gray-600/80'
                    : 'bg-red-500/80 hover:bg-red-600/80'
                } text-white`}
              >
                {videoEnabled ? <Video size={20} /> : <VideoOff size={20} />}
              </button>

              <button
                onClick={() => setAudioEnabled(!audioEnabled)}
                aria-label={audioEnabled ? 'Mute microphone' : 'Unmute microphone'}
                className={`p-3 rounded-full transition-colors ${
                  audioEnabled
                    ? 'bg-gray-700/80 hover:bg-gray-600/80'
                    : 'bg-red-500/80 hover:bg-red-600/80'
                } text-white`}
              >
                {audioEnabled ? <Mic size={20} /> : <MicOff size={20} />}
              </button>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-500/10 border border-red-500 rounded-lg p-3 text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Username Input */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Your Name
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your display name"
              className="w-full bg-gray-700 text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
              onKeyPress={(e) => e.key === 'Enter' && handleJoin()}
            />
          </div>

          {/* Device Selection */}
          <div className="grid md:grid-cols-2 gap-4">
            {/* Camera Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Camera
              </label>
              <select
                value={selectedVideoDevice}
                onChange={(e) => setSelectedVideoDevice(e.target.value)}
                disabled={!videoEnabled}
                className="w-full bg-gray-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {videoDevices.map((device) => (
                  <option key={device.deviceId} value={device.deviceId}>
                    {device.label || `Camera ${device.deviceId.substring(0, 5)}...`}
                  </option>
                ))}
              </select>
            </div>

            {/* Microphone Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Microphone
              </label>
              <select
                value={selectedAudioDevice}
                onChange={(e) => setSelectedAudioDevice(e.target.value)}
                disabled={!audioEnabled}
                className="w-full bg-gray-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {audioDevices.map((device) => (
                  <option key={device.deviceId} value={device.deviceId}>
                    {device.label || `Microphone ${device.deviceId.substring(0, 5)}...`}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Join Button */}
          <button
            onClick={handleJoin}
            disabled={!username.trim() || isLoading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-lg transition-colors"
          >
            {isLoading ? 'Preparing...' : 'Join Room'}
          </button>
        </div>
      </div>
    </div>
  );
}
