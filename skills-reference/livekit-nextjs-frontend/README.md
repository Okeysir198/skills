# LiveKit Next.js Frontend Skill

A comprehensive Claude Code skill for building and reviewing production-grade web and mobile frontends using LiveKit with Next.js.

## What This Skill Provides

This skill offers complete guidance for developing real-time video, audio, and data communication applications with LiveKit and Next.js, including:

- **Architecture patterns** for token-based authentication, room connections, and track management
- **Best practices** for using LiveKit React hooks and components
- **Security guidelines** for API secrets, token generation, and user authentication
- **Code review checklist** covering security, performance, UX, and testing
- **Troubleshooting guide** for common issues
- **Mobile considerations** for iOS, Android, and React Native
- **5 production-ready examples** with full TypeScript support

## Quick Start

1. **View the skill**: Read `SKILL.md` for comprehensive documentation
2. **Check examples**: Browse `examples/` for ready-to-use components
3. **Install dependencies**: Follow setup instructions in `examples/README.md`

## Examples Included

### 1. Token API Route (`examples/token-api-route.ts`)
Server-side JWT token generation with role-based permissions (host, participant, viewer).

### 2. Basic Room (`examples/basic-room.tsx`)
Minimal room component with token fetching, error handling, and LiveKit's VideoConference UI.

### 3. Custom Controls (`examples/custom-controls.tsx`)
Custom UI controls using LiveKit hooks for audio, video, screen share, and disconnect functionality.

### 4. Chat Component (`examples/chat-component.tsx`)
Real-time chat using LiveKit's data channel with message history and auto-scrolling.

### 5. Pre-Join Screen (`examples/prejoin-screen.tsx`)
Lobby screen with device preview, selection, and testing before joining.

## Key Features

✅ **Production-ready code** - No mockups, placeholders, or TODOs
✅ **TypeScript-first** - Full type safety throughout
✅ **Comprehensive error handling** - Graceful degradation and user feedback
✅ **Security-focused** - Server-side tokens, validation, best practices
✅ **Performance optimized** - Efficient rendering, track management
✅ **Mobile-responsive** - Works on desktop, tablets, and phones
✅ **Accessibility considerations** - Semantic HTML, keyboard navigation

## Dependencies

**Required:**
- `livekit-client` - Core LiveKit client library
- `@livekit/components-react` - Official React components
- `livekit-server-sdk` - Server-side token generation

**Optional (for styled examples):**
- `tailwindcss` - Utility-first CSS framework
- `lucide-react` - Icon library

All examples document their dependencies and provide alternatives.

## Use Cases

- Video conferencing applications
- Live streaming platforms
- Audio rooms and podcasts
- Real-time collaboration tools
- Virtual events and webinars
- Online education platforms
- Telehealth solutions

## Architecture Overview

```
Client (Browser)
  ↓ Request token
Server (Next.js API Route)
  ↓ Generate JWT with permissions
Client receives token
  ↓ Connect to LiveKit
LiveKit Server
  ↓ WebRTC connection established
Real-time audio/video/data
```

## Best Practices Highlighted

1. **Always use server-side token generation** - Never expose API secrets
2. **Use LiveKit's built-in hooks** - Avoid reimplementing state management
3. **Handle errors gracefully** - Provide clear user feedback
4. **Test on real devices** - Mobile behavior differs from desktop
5. **Implement proper cleanup** - Stop tracks when unmounting
6. **Use HTTPS in production** - Required for camera/microphone access

## Resources

- [LiveKit Documentation](https://docs.livekit.io)
- [React Components Guide](https://docs.livekit.io/reference/components/react/)
- [LiveKit Examples](https://github.com/livekit-examples)
- [LiveKit Community](https://livekit.io/community)

## License

Apache License 2.0 - See LICENSE.txt for complete terms.

## Contributing

This skill is part of the Claude Code skills repository. When using this skill, Claude will:
- Guide development with LiveKit best practices
- Review code for security, performance, and correctness
- Provide working examples and patterns
- Help troubleshoot issues

The skill focuses on Next.js specifically, but the concepts apply to other React frameworks.
