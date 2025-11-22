"""
Long-Running Tool Example

Demonstrates handling long-running operations with proper interruption support.
Shows patterns for async operations, user interruptions, and graceful cancellation.
"""

import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv
from livekit.agents import Agent, JobContext, WorkerOptions, cli
from livekit.agents.llm import function_tool
from livekit.agents.voice import AgentSession, RunContext
from livekit.plugins import silero

logger = logging.getLogger("long-running-example")
logger.setLevel(logging.INFO)

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env')


class LongRunningAgent(Agent):
    """Agent demonstrating long-running operation patterns."""

    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful assistant that can perform searches and data processing.
            Some operations may take a few moments - you'll let the user know when they complete.
            Users can interrupt you at any time if they change their mind.""",
            llm="openai/gpt-4o-mini",
            vad=silero.VAD.load()
        )

    @function_tool
    async def search_database(
        self,
        query: str,
        context: RunContext
    ) -> str | None:
        """Search the database for matching records (may take several seconds).

        Use this when the user wants to search for information.
        This operation can be interrupted if the user speaks.

        Args:
            query: Search query
            context: Runtime context
        """
        logger.info(f"Starting database search for: {query}")

        # Start the long-running search operation
        search_task = asyncio.ensure_future(
            self._perform_database_search(query)
        )

        # Wait for completion, but allow user interruptions
        await context.speech_handle.wait_if_not_interrupted([search_task])

        # Check if user interrupted
        if context.speech_handle.interrupted:
            logger.info("Search interrupted by user")
            # Cancel the ongoing search
            search_task.cancel()
            # Return None to skip the tool reply
            return None

        # Get results
        results = search_task.result()
        logger.info(f"Search completed with {len(results)} results")

        if not results:
            return f"I didn't find any results for '{query}'"

        # Format results (limit to first 5)
        result_text = "\n".join([f"- {r}" for r in results[:5]])

        if len(results) > 5:
            return f"Found {len(results)} results for '{query}':\n{result_text}\n... and {len(results) - 5} more"
        else:
            return f"Found {len(results)} results for '{query}':\n{result_text}"

    async def _perform_database_search(self, query: str) -> list[str]:
        """Simulate a database search that takes time."""
        # Simulate searching through large dataset
        await asyncio.sleep(5)  # 5 second search

        # Return mock results
        return [
            f"Record matching '{query}' #1",
            f"Record matching '{query}' #2",
            f"Record matching '{query}' #3",
            f"Related item: '{query}' variant A",
            f"Related item: '{query}' variant B",
            f"Historical data for '{query}'",
        ]

    @function_tool
    async def process_large_file(
        self,
        filename: str,
        context: RunContext
    ) -> str | None:
        """Process a large file with progress tracking.

        Args:
            filename: Name of file to process
            context: Runtime context
        """
        logger.info(f"Starting file processing: {filename}")

        total_chunks = 10
        processed = 0

        try:
            for chunk_num in range(total_chunks):
                # Check for interruption between chunks
                if context.speech_handle.interrupted:
                    logger.info(f"File processing interrupted at chunk {chunk_num}")
                    return None

                # Process one chunk
                await self._process_chunk(filename, chunk_num)
                processed += 1

                # Store progress in userdata for potential status checks
                context.userdata["processing_progress"] = (processed / total_chunks) * 100

                logger.info(f"Processed chunk {chunk_num + 1}/{total_chunks}")

            logger.info(f"File processing completed: {filename}")
            return f"Successfully processed {filename} ({total_chunks} chunks, 100% complete)"

        except Exception as e:
            logger.error(f"Error processing file: {e}")
            return f"I encountered an error while processing {filename}"

    async def _process_chunk(self, filename: str, chunk_num: int):
        """Simulate processing one chunk of a file."""
        await asyncio.sleep(1)  # Each chunk takes 1 second

    @function_tool
    async def fetch_with_retry(
        self,
        url: str,
        context: RunContext
    ) -> str:
        """Fetch data from URL with automatic retries.

        Args:
            url: URL to fetch data from
            context: Runtime context
        """
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                # Check for interruption before each attempt
                if context.speech_handle.interrupted:
                    return None

                logger.info(f"Fetch attempt {attempt + 1}/{max_retries} for {url}")

                # Simulate fetching (in production, use aiohttp)
                result = await self._simulate_fetch(url, should_fail=(attempt < 2))

                logger.info(f"Fetch succeeded on attempt {attempt + 1}")
                return f"Successfully fetched data from {url}: {result}"

            except Exception as e:
                logger.warning(f"Fetch attempt {attempt + 1} failed: {e}")

                if attempt < max_retries - 1:
                    # Wait before retrying (exponential backoff)
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    return f"Failed to fetch data from {url} after {max_retries} attempts"

    async def _simulate_fetch(self, url: str, should_fail: bool = False):
        """Simulate fetching data from a URL."""
        await asyncio.sleep(2)

        if should_fail:
            raise Exception("Network timeout")

        return f"Data from {url}"

    @function_tool
    async def run_analysis(
        self,
        dataset: str,
        context: RunContext
    ) -> str | None:
        """Run complex analysis that cannot be interrupted.

        This is a critical operation that must complete once started.

        Args:
            dataset: Dataset to analyze
            context: Runtime context
        """
        logger.info(f"Starting critical analysis: {dataset}")

        # Disable interruptions for this critical operation
        context.speech_handle.disallow_interruptions()

        try:
            # Perform analysis that must complete
            result = await self._perform_analysis(dataset)

            logger.info(f"Analysis completed: {dataset}")
            return f"Analysis complete for {dataset}: {result}"

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return f"Analysis failed for {dataset}. Please try again."

    async def _perform_analysis(self, dataset: str) -> str:
        """Simulate complex analysis."""
        await asyncio.sleep(3)
        return f"Found 42 patterns in {dataset}"

    async def on_enter(self):
        """Called when the agent enters the session."""
        self.session.generate_reply()


async def entrypoint(ctx: JobContext):
    """Entry point for the agent."""
    session = AgentSession()
    await session.start(agent=LongRunningAgent(), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
