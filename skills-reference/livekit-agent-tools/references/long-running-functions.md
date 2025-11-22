# Long-Running Functions

Handle asynchronous operations, interruptions, and long-running tasks in LiveKit agent tools while maintaining responsive voice interactions.

## Table of Contents

- [The Challenge](#the-challenge)
- [Basic Async Pattern](#basic-async-pattern)
- [Interruption Handling](#interruption-handling)
- [Disabling Interruptions](#disabling-interruptions)
- [Background Tasks](#background-tasks)
- [Progress Updates](#progress-updates)
- [Timeout Handling](#timeout-handling)
- [Advanced Patterns](#advanced-patterns)

## The Challenge

Voice agents need to remain responsive while performing long operations like:
- Web searches
- Database queries
- File processing
- API calls to slow services
- Complex calculations

By default, tools can be interrupted if the user speaks. This provides a natural conversation flow, but requires careful handling of incomplete operations.

## Basic Async Pattern

Always use `async def` for tool functions:

```python
import asyncio
import aiohttp

@function_tool
async def search_web(self, query: str) -> str:
    """Search the web for information.

    Args:
        query: Search query
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.search.com/search?q={query}") as response:
            data = await response.json()

    return f"Found {len(data['results'])} results for '{query}'"
```

This allows the agent to handle other events while waiting for I/O operations.

## Interruption Handling

For operations that might take several seconds, handle user interruptions gracefully:

```python
from livekit.agents.voice import RunContext

@function_tool
async def search_database(
    self,
    query: str,
    context: RunContext
) -> str | None:
    """Search database for matching records.

    Args:
        query: Search query
        context: Runtime context
    """
    # Start the long-running operation
    search_task = asyncio.ensure_future(
        perform_database_search(query)
    )

    # Wait for completion, but allow user interruptions
    await context.speech_handle.wait_if_not_interrupted([search_task])

    # Check if user interrupted
    if context.speech_handle.interrupted:
        # Cancel the operation
        search_task.cancel()
        # Return None to skip the tool reply
        return None

    # Return the results
    results = search_task.result()
    return f"Found {len(results)} matching records"

async def perform_database_search(query: str):
    """Simulate long database search."""
    await asyncio.sleep(5)  # Long operation
    return ["result1", "result2", "result3"]
```

**Key points**:
- Use `asyncio.ensure_future()` to create a task
- Call `context.speech_handle.wait_if_not_interrupted()` to wait with interruption support
- Check `context.speech_handle.interrupted` to see if user spoke
- Return `None` to skip the tool reply when interrupted
- Always `cancel()` the task if interrupted to free resources

## Disabling Interruptions

For critical operations that must complete, disable interruptions:

```python
@function_tool
async def process_payment(
    self,
    amount: float,
    card_token: str,
    context: RunContext
) -> str:
    """Process a payment transaction.

    Args:
        amount: Payment amount
        card_token: Payment token
        context: Runtime context
    """
    # Disable interruptions for payment processing
    context.speech_handle.disallow_interruptions()

    # Process the payment (must complete)
    result = await payment_gateway.charge(
        amount=amount,
        token=card_token
    )

    if result.success:
        return f"Payment of ${amount} processed successfully. Confirmation: {result.transaction_id}"
    else:
        return f"Payment failed: {result.error_message}"
```

Use `disallow_interruptions()` for:
- Financial transactions
- Database commits
- File writes
- Any operation that shouldn't be canceled mid-stream

## Background Tasks

For operations that should continue even if interrupted:

```python
@function_tool
async def generate_report(
    self,
    report_type: str,
    context: RunContext
) -> str:
    """Generate a report in the background.

    Args:
        report_type: Type of report to generate
        context: Runtime context
    """
    # Start the report generation
    report_task = asyncio.create_task(
        create_report(report_type)
    )

    # Store task reference in userdata
    context.userdata["pending_report"] = report_task

    # Return immediately
    return f"I've started generating the {report_type} report. I'll let you know when it's ready."

@function_tool
async def check_report_status(self, context: RunContext) -> str:
    """Check if the report is ready."""
    report_task = context.userdata.get("pending_report")

    if not report_task:
        return "No report is currently being generated."

    if report_task.done():
        report = await report_task
        return f"Your report is ready! {report.summary}"
    else:
        return "Your report is still being generated. I'll notify you when it's ready."

async def create_report(report_type: str):
    """Simulate long report generation."""
    await asyncio.sleep(30)
    return {"summary": f"{report_type} report with 50 entries"}
```

## Progress Updates

For very long operations, provide progress updates:

```python
@function_tool
async def process_large_file(
    self,
    filename: str,
    context: RunContext
) -> str:
    """Process a large file with progress updates.

    Args:
        filename: File to process
        context: Runtime context
    """
    total_chunks = 10
    processed = 0

    for i in range(total_chunks):
        # Check for interruption between chunks
        if context.speech_handle.interrupted:
            return None

        # Process one chunk
        await process_chunk(filename, i)
        processed += 1

        # Update every few chunks
        if processed % 3 == 0:
            percentage = (processed / total_chunks) * 100
            # You could store this in userdata for another tool to query
            context.userdata["processing_progress"] = percentage

        await asyncio.sleep(1)  # Simulate chunk processing

    return f"Successfully processed {filename} ({total_chunks} chunks)"

async def process_chunk(filename: str, chunk_index: int):
    """Process one chunk of the file."""
    await asyncio.sleep(0.5)
```

## Timeout Handling

Add timeouts to prevent tools from running indefinitely:

```python
@function_tool
async def fetch_external_data(
    self,
    url: str,
    context: RunContext
) -> str:
    """Fetch data from external API with timeout.

    Args:
        url: API endpoint URL
        context: Runtime context
    """
    try:
        # Create the fetch task
        fetch_task = asyncio.create_task(fetch_from_api(url))

        # Wait with timeout
        result = await asyncio.wait_for(fetch_task, timeout=10.0)

        return f"Successfully fetched data: {result[:100]}..."

    except asyncio.TimeoutError:
        return "The request timed out. The external service might be slow or unavailable."
    except Exception as e:
        return f"Error fetching data: {str(e)}"

async def fetch_from_api(url: str) -> str:
    """Fetch data from API."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
```

## Advanced Patterns

### Multiple Concurrent Operations

```python
@function_tool
async def fetch_all_data(
    self,
    sources: list[str],
    context: RunContext
) -> str:
    """Fetch data from multiple sources concurrently.

    Args:
        sources: List of data sources to fetch from
        context: Runtime context
    """
    # Start all fetch operations concurrently
    tasks = [
        asyncio.create_task(fetch_from_source(source))
        for source in sources
    ]

    # Wait for all, but allow interruptions
    await context.speech_handle.wait_if_not_interrupted(tasks)

    if context.speech_handle.interrupted:
        # Cancel all pending tasks
        for task in tasks:
            if not task.done():
                task.cancel()
        return None

    # Gather all results
    results = [task.result() for task in tasks]
    return f"Fetched data from {len(results)} sources"

async def fetch_from_source(source: str):
    """Fetch from a single source."""
    await asyncio.sleep(2)
    return f"Data from {source}"
```

### Retry Logic

```python
@function_tool
async def fetch_with_retry(
    self,
    url: str,
    context: RunContext
) -> str:
    """Fetch data with automatic retries.

    Args:
        url: URL to fetch
        context: Runtime context
    """
    max_retries = 3
    retry_delay = 1.0

    for attempt in range(max_retries):
        try:
            # Check for interruption before each attempt
            if context.speech_handle.interrupted:
                return None

            # Attempt the fetch
            result = await fetch_from_api(url)
            return f"Successfully fetched data: {result[:100]}..."

        except Exception as e:
            if attempt < max_retries - 1:
                # Wait before retrying
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                return f"Failed after {max_retries} attempts: {str(e)}"
```

### Streaming Results

For operations that produce incremental results:

```python
@function_tool
async def stream_search_results(
    self,
    query: str,
    context: RunContext
) -> str:
    """Search and return results as they're found.

    Args:
        query: Search query
        context: Runtime context
    """
    results = []

    async for result in search_incrementally(query):
        # Check for interruption
        if context.speech_handle.interrupted:
            break

        results.append(result)

        # Could update userdata with partial results
        context.userdata["search_results"] = results

    if context.speech_handle.interrupted:
        return None

    return f"Found {len(results)} results for '{query}'"

async def search_incrementally(query: str):
    """Yield search results as they're found."""
    for i in range(10):
        await asyncio.sleep(0.5)
        yield f"Result {i+1}"
```

### Cancellation Cleanup

Properly clean up resources when interrupted:

```python
@function_tool
async def process_with_cleanup(
    self,
    data: str,
    context: RunContext
) -> str | None:
    """Process data with proper cleanup on cancellation.

    Args:
        data: Data to process
        context: Runtime context
    """
    # Open resources
    temp_file = await create_temp_file()

    try:
        # Create processing task
        process_task = asyncio.create_task(
            process_data(data, temp_file)
        )

        # Wait with interruption support
        await context.speech_handle.wait_if_not_interrupted([process_task])

        if context.speech_handle.interrupted:
            process_task.cancel()
            return None

        result = process_task.result()
        return f"Processing complete: {result}"

    finally:
        # Always clean up resources
        await cleanup_temp_file(temp_file)

async def create_temp_file():
    """Create temporary file."""
    return "/tmp/tempfile"

async def cleanup_temp_file(path: str):
    """Delete temporary file."""
    # Cleanup code here
    pass

async def process_data(data: str, temp_file: str):
    """Process the data."""
    await asyncio.sleep(3)
    return "Processed successfully"
```

## Best Practices

1. **Always use async/await**: Never block the event loop with synchronous I/O
2. **Handle interruptions for long operations**: Use `wait_if_not_interrupted()` for anything over 2-3 seconds
3. **Cancel tasks when interrupted**: Always `cancel()` tasks to free resources
4. **Return None when interrupted**: This skips the tool reply
5. **Use timeouts**: Prevent tools from hanging indefinitely
6. **Clean up resources**: Use try/finally for cleanup code
7. **Provide feedback**: Let users know when operations will take time
8. **Consider background tasks**: For operations users don't need to wait for

## Common Pitfalls

❌ **Don't block the event loop**:
```python
# Bad: Blocks the event loop
time.sleep(5)
requests.get(url)
```

✅ **Do use async alternatives**:
```python
# Good: Non-blocking
await asyncio.sleep(5)
async with aiohttp.ClientSession() as session:
    await session.get(url)
```

❌ **Don't forget to check interruptions**:
```python
# Bad: Long operation ignores interruptions
result = await very_long_operation()
```

✅ **Do check for interruptions**:
```python
# Good: Respects user interruptions
task = asyncio.create_task(very_long_operation())
await context.speech_handle.wait_if_not_interrupted([task])
if context.speech_handle.interrupted:
    task.cancel()
    return None
```

❌ **Don't leak resources**:
```python
# Bad: Resources not cleaned up if interrupted
file = open("data.txt")
await long_operation()
file.close()
```

✅ **Do use try/finally or async context managers**:
```python
# Good: Resources always cleaned up
async with aiofiles.open("data.txt") as file:
    await long_operation()
```

## Testing Long-Running Tools

Test both completion and interruption scenarios:

```python
import pytest
from livekit.agents.testing import VoiceAgentTestSession

@pytest.mark.asyncio
async def test_long_search_completes():
    """Test that search completes successfully."""
    async with VoiceAgentTestSession(agent=MyAgent()) as session:
        response = await session.send_text("Search for Python tutorials")
        assert "Found" in response.text
        assert session.tool_calls[-1].name == "search_database"

@pytest.mark.asyncio
async def test_long_search_interrupted():
    """Test that search handles interruption gracefully."""
    async with VoiceAgentTestSession(agent=MyAgent()) as session:
        # Start search
        session.send_text_async("Search for Python tutorials")

        # Simulate user interruption
        await asyncio.sleep(0.5)
        response = await session.send_text("Never mind")

        # Verify graceful handling
        assert "search_database" in [call.name for call in session.tool_calls]
```
