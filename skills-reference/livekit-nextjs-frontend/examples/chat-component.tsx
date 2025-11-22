/**
 * Chat Component with Data Messages
 *
 * Demonstrates sending and receiving data messages over LiveKit's
 * data channel for real-time chat functionality.
 *
 * BEST PRACTICES IMPLEMENTED:
 * - Uses topics to differentiate message types (allows multiple data channels)
 * - Validates message size (16KiB limit for reliable messages)
 * - Uses reliable delivery mode for guaranteed message delivery
 * - Implements proper error handling for send failures
 * - Filters incoming messages by topic to avoid processing unrelated data
 */

'use client';

import { useRoom, useLocalParticipant } from '@livekit/components-react';
import { RemoteParticipant } from 'livekit-client';
import { useEffect, useState, useRef } from 'react';
import { Send } from 'lucide-react';

/**
 * Note: This example uses lucide-react for icons. Install with:
 * npm install lucide-react
 *
 * Alternatively, use text labels like "Send" or your own icon solution.
 */

interface ChatMessage {
  id: string;
  senderIdentity: string;
  senderName: string;
  message: string;
  timestamp: number;
  isLocal: boolean;
}

// LiveKit recommends 16KiB limit for reliable data packets
const MAX_MESSAGE_SIZE = 16 * 1024; // 16KB in bytes
const CHAT_TOPIC = 'chat'; // Use topics to differentiate message types

export function ChatComponent() {
  const room = useRoom();
  const { localParticipant } = useLocalParticipant();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Listen for incoming data messages
  useEffect(() => {
    const handleData = (
      payload: Uint8Array,
      participant?: RemoteParticipant,
      kind?: any,
      topic?: string
    ) => {
      // Filter by topic to only handle chat messages
      if (topic !== CHAT_TOPIC) return;

      try {
        const decoder = new TextDecoder();
        const messageData = JSON.parse(decoder.decode(payload));

        const newMessage: ChatMessage = {
          id: `${participant?.sid || 'local'}-${Date.now()}`,
          senderIdentity: participant?.identity || localParticipant.identity,
          senderName: participant?.name || localParticipant.name || 'You',
          message: messageData.message,
          timestamp: Date.now(),
          isLocal: !participant, // If no participant, it's our own message echoed back
        };

        setMessages((prev) => [...prev, newMessage]);
      } catch (error) {
        console.error('Error parsing chat message:', error);
      }
    };

    room.on('dataReceived', handleData);

    return () => {
      room.off('dataReceived', handleData);
    };
  }, [room, localParticipant]);

  const sendMessage = () => {
    if (!inputValue.trim()) return;

    const messageData = {
      message: inputValue,
    };

    const encoder = new TextEncoder();
    const data = encoder.encode(JSON.stringify(messageData));

    // Validate message size (LiveKit recommends 16KiB limit for reliable packets)
    if (data.byteLength > MAX_MESSAGE_SIZE) {
      console.error(`Message too large: ${data.byteLength} bytes (max: ${MAX_MESSAGE_SIZE})`);
      alert('Message is too long. Please shorten your message.');
      return;
    }

    try {
      // Send as reliable data packet with topic (guaranteed delivery)
      localParticipant.publishData(
        data,
        {
          reliable: true, // Use reliable delivery for chat
          topic: CHAT_TOPIC, // Set topic to differentiate message types
        }
      );

      // Add message to local state immediately
      const newMessage: ChatMessage = {
        id: `local-${Date.now()}`,
        senderIdentity: localParticipant.identity,
        senderName: 'You',
        message: inputValue,
        timestamp: Date.now(),
        isLocal: true,
      };

      setMessages((prev) => [...prev, newMessage]);
      setInputValue('');
    } catch (error) {
      console.error('Failed to send message:', error);
      alert('Failed to send message. Please try again.');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 rounded-lg overflow-hidden">
      {/* Chat Header */}
      <div className="bg-gray-800 px-4 py-3 border-b border-gray-700">
        <h3 className="text-white font-semibold">Chat</h3>
        <p className="text-gray-400 text-sm">
          {room.participants.size + 1} participant{room.participants.size !== 0 ? 's' : ''}
        </p>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 mt-8">
            No messages yet. Start the conversation!
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.isLocal ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[70%] rounded-lg px-4 py-2 ${
                  msg.isLocal
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-100'
                }`}
              >
                {!msg.isLocal && (
                  <div className="font-semibold text-sm mb-1">
                    {msg.senderName}
                  </div>
                )}
                <div className="break-words">{msg.message}</div>
                <div className="text-xs opacity-70 mt-1">
                  {new Date(msg.timestamp).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="bg-gray-800 p-4 border-t border-gray-700">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type a message..."
            aria-label="Chat message input"
            className="flex-1 bg-gray-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={sendMessage}
            disabled={!inputValue.trim()}
            aria-label="Send message"
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg px-4 py-2 transition-colors"
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  );
}

// Example: Using chat in a layout with video
export function RoomWithChat() {
  return (
    <div className="h-screen flex">
      {/* Video Area - 70% */}
      <div className="flex-[7] bg-black">
        {/* Your video components here */}
      </div>

      {/* Chat Sidebar - 30% */}
      <div className="flex-[3] min-w-[300px] max-w-[400px]">
        <ChatComponent />
      </div>
    </div>
  );
}
