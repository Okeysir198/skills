# Common Voice Agent Patterns

## Tool Calling (Function Calling)

Allow your agent to call external functions and APIs.

### Basic Tool Pattern

```python
from livekit import agents
from livekit.agents import function_tool, RunContext

class MyAgent(agents.Agent):
    def __init__(self):
        super().__init__(
            instructions="""You are a helpful assistant with access to tools.
            When asked about the weather, use the lookup_weather function."""
        )

    @function_tool
    async def lookup_weather(
        self,
        context: RunContext,
        location: str,
        units: str = "fahrenheit"
    ):
        """Look up current weather for a location.

        Args:
            location: City name or address
            units: Temperature units (fahrenheit or celsius)
        """
        # Call external weather API
        weather_data = await fetch_weather_api(location, units)

        # Return (result_data, voice_message)
        return (
            weather_data,
            f"The weather in {location} is {weather_data['temp']} degrees and {weather_data['conditions']}."
        )
```

**Key points**:
- Use `@function_tool` decorator
- First parameter must be `self, context: RunContext`
- Add type hints for all parameters
- Docstring describes the function and arguments
- Return tuple: `(result_data, voice_message)`
- Voice message is what the agent will say

### Tool with Silent Execution

For tools that don't need to announce results:

```python
@function_tool
async def log_event(self, context: RunContext, event: str):
    """Log an event to the system."""
    await database.log(event)
    # Return None as voice message for silent execution
    return event, None
```

### Tool with Structured Return

```python
from dataclasses import dataclass

@dataclass
class WeatherData:
    temperature: float
    conditions: str
    humidity: int

@function_tool
async def get_detailed_weather(
    self,
    context: RunContext,
    location: str
) -> tuple[WeatherData, str]:
    """Get detailed weather information."""
    data = await fetch_weather_api(location)

    weather = WeatherData(
        temperature=data['temp'],
        conditions=data['conditions'],
        humidity=data['humidity']
    )

    message = f"In {location}: {weather.temperature}°F, {weather.conditions}, {weather.humidity}% humidity"

    return weather, message
```

### Accessing User Data in Tools

```python
@function_tool
async def save_preference(
    self,
    context: RunContext,
    preference_key: str,
    preference_value: str
):
    """Save a user preference."""
    # Access shared user data
    user_data = context.userdata
    user_data.preferences[preference_key] = preference_value

    return None, f"I've saved your preference for {preference_key}."
```

### Tool with External API Call

```python
@function_tool
async def search_database(
    self,
    context: RunContext,
    query: str,
    limit: int = 5
):
    """Search the product database.

    Args:
        query: Search terms
        limit: Maximum number of results (default 5)
    """
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.example.com/search",
            json={"query": query, "limit": limit},
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        results = response.json()

    if not results:
        return None, "I couldn't find any matching products."

    # Format results for voice
    summary = f"I found {len(results)} products. "
    summary += ". ".join([r['name'] for r in results[:3]])

    return results, summary
```

### Long-Running Tool with Progress Updates

```python
@function_tool
async def process_order(
    self,
    context: RunContext,
    order_id: str
):
    """Process a customer order."""
    session = context.session

    # Acknowledge start
    await session.send_tts("I'm processing your order now.")

    # Do work
    await validate_order(order_id)
    await charge_payment(order_id)
    await schedule_shipment(order_id)

    return order_id, "Your order has been processed and will ship tomorrow."
```

---

## Retrieval Augmented Generation (RAG)

Integrate knowledge bases and vector databases for context-aware responses.

### Basic RAG Pattern

```python
from livekit import agents
from livekit.agents import function_tool, RunContext
import chromadb

class RAGAgent(agents.Agent):
    def __init__(self, vector_db):
        self.vector_db = vector_db
        super().__init__(
            instructions="""You are a knowledgeable assistant with access to a documentation database.
            When asked questions, search the documentation first using search_docs."""
        )

    @function_tool
    async def search_docs(
        self,
        context: RunContext,
        query: str,
        num_results: int = 3
    ):
        """Search documentation for relevant information.

        Args:
            query: What to search for
            num_results: Number of results to return (default 3)
        """
        # Query vector database
        results = self.vector_db.query(
            query_texts=[query],
            n_results=num_results
        )

        if not results['documents'][0]:
            return None, "I couldn't find relevant documentation for that question."

        # Combine results
        context_text = "\n\n".join(results['documents'][0])

        # Inject into LLM context
        return (
            {"query": query, "documents": results['documents'][0]},
            f"Based on the documentation: {context_text}"
        )


# In entrypoint
vector_db = chromadb.Client()
agent = RAGAgent(vector_db=vector_db)
```

### RAG with Embedding Search

```python
@function_tool
async def semantic_search(
    self,
    context: RunContext,
    question: str
):
    """Search knowledge base using semantic similarity."""
    from openai import OpenAI

    # Generate embedding for question
    client = OpenAI()
    embedding = client.embeddings.create(
        model="text-embedding-3-small",
        input=question
    ).data[0].embedding

    # Search vector database
    results = self.vector_db.query(
        query_embeddings=[embedding],
        n_results=5
    )

    # Rank by relevance
    relevant_docs = [
        doc for doc, score in zip(results['documents'][0], results['distances'][0])
        if score < 0.7  # Similarity threshold
    ]

    if not relevant_docs:
        return None, "I don't have information about that in my knowledge base."

    # Return context for LLM
    context_str = "\n\n".join(relevant_docs)
    return {
        "question": question,
        "context": context_str
    }, f"Let me answer based on what I know: {context_str}"
```

---

## Multi-Agent Workflows

Coordinate multiple specialized agents with handoff patterns.

### Basic Handoff Pattern

```python
from dataclasses import dataclass, field
from livekit import agents
from livekit.agents import function_tool, RunContext

@dataclass
class UserData:
    """Shared data across agents."""
    name: str = ""
    phone: str = ""
    current_task: str = ""
    agents: dict = field(default_factory=dict)
    prev_agent: agents.Agent = None


class GreeterAgent(agents.Agent):
    """Initial contact point."""

    def __init__(self):
        super().__init__(
            instructions="""You are a friendly greeter for our restaurant.
            Ask how you can help: reservations or takeout orders."""
        )

    @function_tool
    async def transfer_to_reservations(self, context: RunContext):
        """Transfer to reservation agent."""
        user_data = context.userdata
        return user_data.agents['reservation'], "Transferring you to reservations."

    @function_tool
    async def transfer_to_takeout(self, context: RunContext):
        """Transfer to takeout agent."""
        user_data = context.userdata
        return user_data.agents['takeout'], "Let me connect you with takeout orders."


class ReservationAgent(agents.Agent):
    """Handles table reservations."""

    def __init__(self):
        super().__init__(
            instructions="""You handle restaurant reservations.
            Collect: date, time, party size, name, and phone number."""
        )

    @function_tool
    async def book_reservation(
        self,
        context: RunContext,
        date: str,
        time: str,
        party_size: int,
        name: str,
        phone: str
    ):
        """Book a reservation."""
        # Store in user data
        user_data = context.userdata
        user_data.name = name
        user_data.phone = phone

        # Book in system
        reservation_id = await booking_system.create(date, time, party_size, name, phone)

        return (
            {"reservation_id": reservation_id},
            f"Perfect! Your reservation for {party_size} on {date} at {time} is confirmed. Confirmation number {reservation_id}."
        )


# In entrypoint
@agents.entrypoint
async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    # Initialize shared user data
    user_data = UserData()
    ctx.userdata = user_data

    # Create all agents
    greeter = GreeterAgent()
    reservation = ReservationAgent()
    takeout = TakeoutAgent()

    # Register agents for handoff
    user_data.agents = {
        'greeter': greeter,
        'reservation': reservation,
        'takeout': takeout
    }

    # Start with greeter
    session = agents.AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        vad=vad,
    )

    # Start session with initial agent
    session.start(ctx.room, initial_agent=greeter)
    await session.wait_for_complete()
```

### Context Preservation During Handoff

```python
class BaseHandoffAgent(agents.Agent):
    """Base class with handoff context preservation."""

    async def on_enter(self, session: agents.AgentSession):
        """Called when agent takes control."""
        context = session.context

        # Preserve relevant history from previous agent
        if context.userdata.prev_agent:
            # Copy last N messages (excluding instructions)
            prev_history = context.userdata.prev_agent.chat_history[-5:]
            context.chat_history.extend(prev_history)

        # Announce transition
        await session.generate_reply("I'm here to help with your request.")

    def _transfer(self, context: RunContext, target_agent: agents.Agent, message: str):
        """Helper for agent handoff."""
        user_data = context.userdata
        user_data.prev_agent = context.session.current_agent
        return target_agent, message
```

---

## Background Audio

Add ambient sounds or "thinking" audio for better UX.

```python
from livekit import rtc

class AgentWithBackgroundAudio(agents.Agent):
    def __init__(self):
        super().__init__(
            instructions="You are a helpful assistant."
        )
        self.audio_source = None

    async def on_enter(self, session: agents.AgentSession):
        """Start background music when agent enters."""
        # Load audio file
        audio_data = await load_audio_file("background_music.mp3")

        # Create audio source
        self.audio_source = rtc.AudioSource(
            sample_rate=48000,
            num_channels=1
        )

        # Publish to room
        track = rtc.LocalAudioTrack.create_audio_track("background", self.audio_source)
        await session.room.local_participant.publish_track(track)

        # Play audio
        await self.audio_source.capture_frame(audio_data)

    async def on_exit(self, session: agents.AgentSession):
        """Stop background audio when leaving."""
        if self.audio_source:
            await session.room.local_participant.unpublish_track("background")
```

---

## Push-to-Talk

Alternative to VAD for user-controlled speaking.

```python
@agents.entrypoint
async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    agent = MyAgent()
    session = agents.AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        vad=None,  # Disable VAD for push-to-talk
    )

    # Listen for data messages to control recording
    @ctx.room.on("data_received")
    def on_data(data_packet: rtc.DataPacket):
        data = data_packet.data.decode()

        if data == "START_RECORDING":
            session.start_recording()
        elif data == "STOP_RECORDING":
            session.stop_recording()

    session.start(ctx.room)
    await session.wait_for_complete()
```

---

## Structured Output

Control TTS parameters based on LLM response.

```python
from pydantic import BaseModel

class ResponseWithEmotion(BaseModel):
    text: str
    emotion: str  # "happy", "sad", "neutral", "excited"
    speed: float = 1.0  # 0.5 to 2.0

class EmotionalAgent(agents.Agent):
    def __init__(self):
        super().__init__(
            instructions="""Respond with appropriate emotion.
            Output format: {"text": "your response", "emotion": "happy|sad|neutral|excited", "speed": 1.0}"""
        )

    async def generate_response(self, session: agents.AgentSession, user_input: str):
        """Generate response with emotion control."""
        # Get LLM response
        llm_response = await session.llm.chat(user_input)

        # Parse structured output
        import json
        response_data = json.loads(llm_response)
        response = ResponseWithEmotion(**response_data)

        # Adjust TTS based on emotion
        tts_config = self._get_tts_config(response.emotion)
        tts_config['speed'] = response.speed

        # Generate speech with adjusted parameters
        await session.tts.synthesize(
            response.text,
            **tts_config
        )

    def _get_tts_config(self, emotion: str) -> dict:
        """Map emotion to TTS parameters."""
        emotion_map = {
            "happy": {"pitch": 1.1, "energy": 1.2},
            "sad": {"pitch": 0.9, "energy": 0.8},
            "excited": {"pitch": 1.2, "energy": 1.4},
            "neutral": {"pitch": 1.0, "energy": 1.0},
        }
        return emotion_map.get(emotion, emotion_map["neutral"])
```

---

## Phone Integration (SIP/Twilio)

Connect voice agent to phone systems.

```python
# Requires SIP trunk or Twilio integration

@agents.entrypoint
async def entrypoint(ctx: agents.JobContext):
    """Handle inbound phone calls."""
    await ctx.connect()

    # Get caller information
    caller_number = ctx.room.metadata.get("caller_number")
    call_id = ctx.room.metadata.get("call_id")

    # Initialize agent with caller context
    agent = CustomerServiceAgent(caller_number=caller_number)

    session = agents.AgentSession(
        stt=deepgram.STT(model="nova-3-phonecall"),  # Optimized for phone audio
        llm=llm,
        tts=cartesia.TTS(
            voice="phone_optimized",
            sample_rate=8000,  # Phone quality
            encoding="mulaw"   # Phone codec
        ),
        vad=vad,
    )

    session.start(ctx.room)

    # Log call
    await log_call(call_id, caller_number)

    await session.wait_for_complete()

    # Call cleanup
    await end_call(call_id)
```

---

## Interrupt Handling

Advanced interruption logic for natural conversations.

```python
class InterruptibleAgent(agents.Agent):
    def __init__(self):
        super().__init__(
            instructions="You are a helpful assistant."
        )
        self.interruption_count = 0

    async def on_interrupted(self, session: agents.AgentSession):
        """Called when user interrupts agent."""
        self.interruption_count += 1

        # After multiple interruptions, ask if user wants to change topic
        if self.interruption_count >= 3:
            await session.generate_reply(
                "I notice you're interrupting frequently. Would you like to discuss something else?"
            )
            self.interruption_count = 0

    async def on_enter(self, session: agents.AgentSession):
        # Configure interruption behavior
        session.configure_interruptions(
            allow=True,
            min_duration=0.8,  # Minimum speech duration to consider
            false_interruption_timeout=1.2,  # Wait before stopping
        )
```

---

## Speaker Diarization (Multi-Speaker)

Handle multiple speakers in the same room.

```python
@agents.entrypoint
async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    # Track speakers
    speakers = {}

    @ctx.room.on("participant_connected")
    def on_participant(participant: rtc.RemoteParticipant):
        speakers[participant.identity] = {
            "name": participant.name or f"Speaker {len(speakers) + 1}",
            "messages": []
        }

    agent = MultiSpeakerAgent(speakers=speakers)

    # Use STT with speaker diarization
    stt = assemblyai.STT(
        speaker_labels=True,  # Enable diarization
    )

    session = agents.AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        vad=vad,
    )

    session.start(ctx.room)
    await session.wait_for_complete()
```

---

## Testing and Development Patterns

### Console Mode for Local Testing

```python
# Run agent in terminal for testing
if __name__ == "__main__":
    from livekit.agents import cli

    cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            console_mode=True,  # Enable console testing
        )
    )
```

Run with:
```bash
python agent.py console
```

### Development Mode with Auto-reload

```python
# In agent.py
if __name__ == "__main__":
    from livekit.agents import cli

    cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            dev_mode=True,  # Enable hot reload
        )
    )
```

Run with:
```bash
python agent.py dev
```
