# LiveKit Next.js Examples

This directory contains production-ready examples for building LiveKit applications with Next.js.

## Examples Overview

### 1. Token API Route (`token-api-route.ts`)

Server-side API route for generating LiveKit access tokens with JWT-based authentication.

**Features:**
- Token generation with proper validation
- Environment variable configuration
- Role-based permissions (host, participant, viewer)
- Security best practices

**Usage:**
```typescript
// Place in: app/api/token/route.ts (App Router)
// Or: pages/api/token.ts (Pages Router)
```

### 2. Basic Room (`basic-room.tsx`)

Minimal room component with complete error handling and loading states.

**Features:**
- Token fetching from API
- Connection management
- Error handling
- Loading states
- Out-of-the-box VideoConference UI

**Usage:**
```typescript
<BasicRoom roomName="my-room" username="John Doe" />
```

### 3. Custom Controls (`custom-controls.tsx`)

Build custom UI using LiveKit hooks instead of default components.

**Features:**
- Custom control buttons (audio, video, screen share, disconnect)
- Participant grid layout
- Speaking indicators
- Screen share highlighting
- Responsive design

**Usage:**
```typescript
// Use within a LiveKitRoom context
<CustomRoomUI />
```

### 4. Chat Component (`chat-component.tsx`)

Real-time chat using LiveKit's data channel.

**Features:**
- Send/receive messages via data packets
- Message history
- Auto-scrolling
- Participant count
- Keyboard shortcuts (Enter to send)

**Usage:**
```typescript
// Use within a LiveKitRoom context
<ChatComponent />

// Or with video in a split layout
<RoomWithChat />
```

### 5. Pre-Join Screen (`prejoin-screen.tsx`)

Lobby screen for testing devices before joining.

**Features:**
- Video/audio preview
- Device selection (camera, microphone)
- Display name input
- Device permissions handling
- Loading and error states

**Usage:**
```typescript
<PreJoinScreen
  roomName="my-room"
  onJoin={(config) => {
    // Handle join with config
    console.log(config.username, config.videoEnabled);
  }}
/>
```

## Setup Instructions

### 1. Install Dependencies

```bash
npm install livekit-client @livekit/components-react livekit-server-sdk
# or
yarn add livekit-client @livekit/components-react livekit-server-sdk
```

### 2. Configure Environment Variables

Create `.env.local` in your project root:

```env
# Your LiveKit server URL (wss:// for production)
NEXT_PUBLIC_LIVEKIT_URL=wss://your-project.livekit.cloud

# API credentials (NEVER expose these in client code)
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
```

### 3. Add Global Styles

Import LiveKit styles in your root layout or _app file:

```typescript
import '@livekit/components-styles';
```

### 4. Use Examples

Copy the relevant example files into your project and adapt as needed.

## Common Patterns

### Full Room Page Example

```typescript
'use client';

import { useState } from 'react';
import { PreJoinScreen } from './examples/prejoin-screen';
import { LiveKitRoom } from '@livekit/components-react';
import { CustomRoomUI } from './examples/custom-controls';
import '@livekit/components-styles';

export default function RoomPage() {
  const [token, setToken] = useState<string>('');
  const [joined, setJoined] = useState(false);

  const handleJoin = async (config: JoinConfig) => {
    const response = await fetch(
      `/api/token?room=my-room&username=${config.username}`
    );
    const data = await response.json();
    setToken(data.token);
    setJoined(true);
  };

  if (!joined) {
    return <PreJoinScreen roomName="my-room" onJoin={handleJoin} />;
  }

  return (
    <LiveKitRoom
      token={token}
      serverUrl={process.env.NEXT_PUBLIC_LIVEKIT_URL!}
      connect={true}
    >
      <CustomRoomUI />
    </LiveKitRoom>
  );
}
```

## Best Practices

1. **Always use server-side token generation** - Never expose API secrets
2. **Use LiveKit's built-in hooks** - They handle state and edge cases
3. **Handle errors gracefully** - Show user-friendly error messages
4. **Test on real devices** - Mobile behavior differs from desktop
5. **Implement loading states** - Connection takes time
6. **Clean up tracks** - Stop tracks when unmounting components
7. **Use HTTPS in production** - Required for camera/microphone access

## Troubleshooting

### "Failed to get token"
- Check API route is accessible
- Verify environment variables are set
- Check network tab for API errors

### "Cannot access camera/microphone"
- Ensure HTTPS (localhost works for testing)
- Check browser permissions
- Try different devices

### "No video showing"
- Wait for `networkidle` state
- Check track publication status
- Verify token has `canPublish` permission

## Resources

- [LiveKit Documentation](https://docs.livekit.io)
- [React Components Docs](https://docs.livekit.io/reference/components/react/)
- [LiveKit Examples](https://github.com/livekit-examples)
- [LiveKit Community](https://livekit.io/community)
