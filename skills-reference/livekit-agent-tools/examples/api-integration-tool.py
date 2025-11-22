"""
API Integration Tool Example

Demonstrates how to integrate external APIs with LiveKit agent tools.
Shows best practices for async HTTP calls, error handling, and response formatting.
"""

import logging
from pathlib import Path

import aiohttp
from dotenv import load_dotenv
from livekit.agents import Agent, JobContext, WorkerOptions, cli
from livekit.agents.llm import function_tool
from livekit.agents.voice import AgentSession
from livekit.plugins import silero

logger = logging.getLogger("api-integration-example")
logger.setLevel(logging.INFO)

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env')


class APIIntegrationAgent(Agent):
    """Agent demonstrating external API integration patterns."""

    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful assistant with access to weather data and other online information.
            When users ask about weather, use the weather tool to get current conditions.
            Always mention the location when providing weather information.""",
            llm="openai/gpt-4o-mini",
            vad=silero.VAD.load()
        )

    @function_tool
    async def get_weather(self, location: str) -> str:
        """Get current weather information for a location.

        Use this when the user asks about weather, temperature, or current conditions.
        When given a location, estimate the latitude and longitude - don't ask the user for them.

        Args:
            location: City name or location (e.g., "Tokyo", "New York", "London")
        """
        try:
            # Use a geocoding service to get coordinates
            # This is a simplified example - in production use a proper geocoding API
            coords = await self._geocode_location(location)

            if not coords:
                return f"I couldn't find the location '{location}'. Please try a different city name."

            lat, lon = coords

            # Fetch weather data from Open-Meteo API (free, no API key needed)
            async with aiohttp.ClientSession() as session:
                url = f"https://api.open-meteo.com/v1/forecast"
                params = {
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
                    "temperature_unit": "fahrenheit",
                    "wind_speed_unit": "mph"
                }

                async with session.get(url, params=params, timeout=10) as response:
                    if response.status != 200:
                        return f"I couldn't fetch weather data for {location}. Please try again later."

                    data = await response.json()
                    current = data.get("current", {})

                    # Format the weather information
                    temp = current.get("temperature_2m")
                    feels_like = current.get("apparent_temperature")
                    humidity = current.get("relative_humidity_2m")
                    wind_speed = current.get("wind_speed_10m")

                    weather_desc = self._interpret_weather_code(current.get("weather_code", 0))

                    return f"""Weather in {location}:
- Condition: {weather_desc}
- Temperature: {temp}°F (feels like {feels_like}°F)
- Humidity: {humidity}%
- Wind: {wind_speed} mph"""

        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching weather: {e}")
            return "I'm having trouble connecting to the weather service. Please try again in a moment."
        except Exception as e:
            logger.error(f"Unexpected error in get_weather: {e}")
            return "I encountered an error getting the weather. Please try again."

    async def _geocode_location(self, location: str) -> tuple[float, float] | None:
        """Convert location name to coordinates using geocoding API."""
        try:
            # Using Open-Meteo geocoding API (free, no key needed)
            async with aiohttp.ClientSession() as session:
                url = "https://geocoding-api.open-meteo.com/v1/search"
                params = {"name": location, "count": 1, "language": "en", "format": "json"}

                async with session.get(url, params=params, timeout=10) as response:
                    if response.status != 200:
                        return None

                    data = await response.json()
                    results = data.get("results", [])

                    if not results:
                        return None

                    return (results[0]["latitude"], results[0]["longitude"])

        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return None

    def _interpret_weather_code(self, code: int) -> str:
        """Convert WMO weather code to human-readable description."""
        weather_codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Foggy",
            48: "Foggy with rime",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail"
        }
        return weather_codes.get(code, "Unknown")

    @function_tool
    async def get_exchange_rate(self, from_currency: str, to_currency: str) -> str:
        """Get current exchange rate between two currencies.

        Args:
            from_currency: Source currency code (e.g., "USD", "EUR", "GBP")
            to_currency: Target currency code (e.g., "USD", "EUR", "GBP")
        """
        try:
            from_currency = from_currency.upper()
            to_currency = to_currency.upper()

            # Using exchangerate-api.com (has free tier)
            # In production, use environment variable for API key
            async with aiohttp.ClientSession() as session:
                url = f"https://open.er-api.com/v6/latest/{from_currency}"

                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        return f"I couldn't fetch exchange rates. Please verify the currency codes."

                    data = await response.json()

                    if data.get("result") != "success":
                        return f"Invalid currency code. Please use standard codes like USD, EUR, GBP."

                    rates = data.get("rates", {})
                    rate = rates.get(to_currency)

                    if not rate:
                        return f"I couldn't find the exchange rate for {to_currency}."

                    return f"1 {from_currency} = {rate:.4f} {to_currency}"

        except Exception as e:
            logger.error(f"Error fetching exchange rate: {e}")
            return "I encountered an error fetching the exchange rate. Please try again."

    async def on_enter(self):
        """Called when the agent enters the session."""
        self.session.generate_reply()


async def entrypoint(ctx: JobContext):
    """Entry point for the agent."""
    session = AgentSession()
    await session.start(agent=APIIntegrationAgent(), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
