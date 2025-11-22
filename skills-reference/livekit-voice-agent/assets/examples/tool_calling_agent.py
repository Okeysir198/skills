"""
Tool Calling Agent - Demonstrates function calling with external API integration.

This agent can:
- Look up weather information
- Search a product database
- Save user preferences
"""

import asyncio
import logging
import os
import httpx
from dataclasses import dataclass, field
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, function_tool, RunContext
from livekit.plugins import deepgram, openai, cartesia, silero, turn_detector

load_dotenv(dotenv_path=".env.local")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class UserData:
    """User preferences and session data."""
    name: str = ""
    location: str = ""
    preferences: dict = field(default_factory=dict)


class ToolCallingAgent(Agent):
    """Agent with multiple tools for external integrations."""

    def __init__(self):
        super().__init__(
            instructions="""You are a helpful assistant with access to several tools:
            - Weather lookups
            - Product search
            - User preference management

            When users ask about weather, use lookup_weather.
            When users ask about products, use search_products.
            Save important user preferences using save_preference."""
        )
        # Reusable HTTP client with connection pooling
        self.http_client = httpx.AsyncClient(timeout=10.0)

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
        logger.info(f"Looking up weather for {location}")

        try:
            # Real implementation using OpenWeather API
            # Get API key from environment variable
            api_key = os.getenv("OPENWEATHER_API_KEY")
            if not api_key:
                return None, "Weather service is not configured. Please contact support."

            # Convert fahrenheit/celsius to API format
            units_param = "imperial" if units == "fahrenheit" else "metric"

            response = await self.http_client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": location,
                    "units": units_param,
                    "appid": api_key
                }
            )

            if response.status_code != 200:
                logger.error(f"Weather API error: {response.status_code}")
                return None, f"I couldn't retrieve weather data for {location}. Please try another location."

            data = response.json()

            # Extract relevant data
            weather_data = {
                "temp": round(data["main"]["temp"]),
                "conditions": data["weather"][0]["description"],
                "humidity": data["main"]["humidity"],
                "wind_speed": data["wind"]["speed"]
            }

            # Store location in user data
            user_data = context.userdata
            user_data.location = location

            # Create natural voice response
            message = f"The weather in {location} is {weather_data['conditions']} with a temperature of {weather_data['temp']} degrees {units}."

            return weather_data, message

        except httpx.HTTPStatusError as e:
            logger.error(f"Weather API HTTP error: {e}")
            return None, "I'm having trouble accessing the weather service right now. Please try again later."
        except Exception as e:
            logger.error(f"Weather lookup failed: {e}")
            return None, f"I couldn't look up the weather for {location}. Please try again."

    @function_tool
    async def search_products(
        self,
        context: RunContext,
        query: str,
        category: str = "all",
        max_results: int = 5
    ):
        """Search the product database.

        Args:
            query: Search terms
            category: Product category (all, electronics, clothing, home)
            max_results: Maximum number of results
        """
        logger.info(f"Searching products: {query} in {category}")

        try:
            # Real implementation - replace with your actual API endpoint
            api_url = os.getenv("PRODUCT_API_URL")
            api_key = os.getenv("PRODUCT_API_KEY")

            if not api_url:
                return None, "Product search is not configured. Please contact support."

            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            response = await self.http_client.post(
                f"{api_url}/search",
                json={
                    "query": query,
                    "category": category,
                    "limit": max_results
                },
                headers=headers
            )

            if response.status_code != 200:
                logger.error(f"Product API error: {response.status_code}")
                return None, "I'm having trouble searching our product catalog right now."

            results = response.json()

            if not results or len(results) == 0:
                return None, f"I couldn't find any products matching '{query}'. Try a different search term."

            # Format for voice - mention top 3 results
            summary = f"I found {len(results)} products. "
            top_products = results[:3]
            product_descriptions = [f"{p['name']} for ${p['price']}" for p in top_products]
            summary += ", ".join(product_descriptions)

            if len(results) > 3:
                summary += f", and {len(results) - 3} more."

            return results, summary

        except httpx.HTTPError as e:
            logger.error(f"Product search HTTP error: {e}")
            return None, "I'm having trouble accessing the product database. Please try again later."
        except Exception as e:
            logger.error(f"Product search failed: {e}")
            return None, "I encountered an error searching for products. Please try again."

    @function_tool
    async def save_preference(
        self,
        context: RunContext,
        preference_name: str,
        preference_value: str
    ):
        """Save a user preference.

        Args:
            preference_name: Name of the preference (e.g., 'favorite_color')
            preference_value: Value of the preference
        """
        logger.info(f"Saving preference: {preference_name} = {preference_value}")

        user_data = context.userdata
        user_data.preferences[preference_name] = preference_value

        # In production, you might save to a database here
        # await database.save_preference(user_id, preference_name, preference_value)

        return (
            {"name": preference_name, "value": preference_value},
            f"I've saved your preference: {preference_name} is {preference_value}."
        )

    @function_tool
    async def get_user_info(self, context: RunContext):
        """Get current user information and preferences."""
        user_data = context.userdata

        info = {
            "name": user_data.name or "Not set",
            "location": user_data.location or "Not set",
            "preferences": user_data.preferences
        }

        summary = f"Your name is {info['name']}"
        if info['location']:
            summary += f", you're in {info['location']}"
        if info['preferences']:
            summary += f", and you have {len(info['preferences'])} saved preferences"

        return info, summary

    async def on_enter(self, session: AgentSession):
        """Called when agent enters the session."""
        logger.info("Tool calling agent entered session")
        await session.generate_reply()

    async def cleanup(self):
        """Clean up resources."""
        await self.http_client.aclose()


@agents.entrypoint
async def entrypoint(ctx: JobContext):
    """Agent entrypoint."""
    logger.info(f"Starting tool calling agent for room: {ctx.room.name}")

    await ctx.connect()

    # Initialize user data
    ctx.userdata = UserData()

    # Create agent
    agent = ToolCallingAgent()

    try:
        # Initialize components
        stt = deepgram.STT(model="nova-3", language="multi")
        llm = openai.LLM(model="gpt-4.1-mini", temperature=0.7)
        tts = cartesia.TTS(voice="79a125e8-cd45-4c13-8a67-188112f4dd22")
        vad = silero.VAD.load()
        turn_detection = turn_detector.MultilingualModel(languages=["en"])

        # Create session
        session = AgentSession(
            stt=stt,
            llm=llm,
            tts=tts,
            vad=vad,
            turn_detection=turn_detection,
            allow_interruptions=True,
            preemptive_synthesis=True,
        )

        await session.start(room=ctx.room, agent=agent)
        await session.wait_for_complete()

    finally:
        # Clean up
        await agent.cleanup()

    logger.info("Session completed")


def download_models():
    """Download required models."""
    silero.VAD.load()
    turn_detector.MultilingualModel.load(languages=["en"])


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "download-files":
        download_models()
        sys.exit(0)

    from livekit.agents import cli
    cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
