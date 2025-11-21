# Best Practices

Production-ready patterns, security considerations, performance optimizations, and design principles for building robust LiveKit agent tools.

## Table of Contents

- [Tool Design Principles](#tool-design-principles)
- [Error Handling](#error-handling)
- [Security](#security)
- [Performance](#performance)
- [User Experience](#user-experience)
- [Code Organization](#code-organization)
- [Documentation](#documentation)
- [Production Readiness](#production-readiness)

## Tool Design Principles

### Single Responsibility

Each tool should do one thing well:

✅ **Good**: Focused tools
```python
@function_tool
async def search_flights(self, origin: str, destination: str, date: str) -> str:
    """Search for available flights."""

@function_tool
async def book_flight(self, flight_id: str) -> str:
    """Book a specific flight."""
```

❌ **Bad**: Kitchen sink tool
```python
@function_tool
async def handle_flights(self, action: str, **kwargs) -> str:
    """Search, book, cancel, or modify flights."""
    # Too many responsibilities
```

### Clear, Descriptive Names

Use action-oriented names that clearly indicate purpose:

✅ **Good**:
- `search_products`
- `create_calendar_event`
- `get_order_status`
- `update_user_preferences`

❌ **Bad**:
- `do_thing`
- `process`
- `handle`
- `action`

### Comprehensive Descriptions

Tool descriptions are critical for LLM tool selection:

✅ **Good**: Specific and clear
```python
@function_tool
async def cancel_subscription(self, subscription_id: str) -> str:
    """Cancel a user's subscription immediately.

    Use this when the user explicitly requests to cancel their subscription.
    DO NOT use this for pausing, downgrading, or modifying subscriptions.
    ALWAYS confirm cancellation intent before calling this tool.

    Args:
        subscription_id: The subscription ID to cancel
    """
```

❌ **Bad**: Vague
```python
@function_tool
async def cancel_subscription(self, subscription_id: str) -> str:
    """Cancel subscription."""  # Too brief, no guidance
```

### Meaningful Return Values

Return information that helps the LLM respond appropriately:

✅ **Good**: Informative return
```python
@function_tool
async def create_task(self, title: str, due_date: str) -> str:
    task = await database.create_task(title, due_date)
    return f"Created task '{title}' (ID: {task.id}) due on {due_date}"
```

❌ **Bad**: Uninformative return
```python
@function_tool
async def create_task(self, title: str, due_date: str) -> str:
    await database.create_task(title, due_date)
    return "OK"  # LLM has no context to provide meaningful response
```

## Error Handling

### Graceful Error Messages

Provide actionable error messages the LLM can communicate to users:

✅ **Good**: Helpful error message
```python
@function_tool
async def get_user_profile(self, user_id: str) -> str:
    try:
        profile = await database.get_user(user_id)
        return f"User: {profile.name}, Email: {profile.email}"
    except UserNotFoundError:
        return f"No user found with ID '{user_id}'. Please check the ID and try again."
    except DatabaseConnectionError:
        return "I'm having trouble connecting to the database. Please try again in a moment."
    except Exception as e:
        logger.error(f"Unexpected error in get_user_profile: {e}")
        return "I encountered an unexpected error. Please try again or contact support."
```

❌ **Bad**: Technical error exposed
```python
@function_tool
async def get_user_profile(self, user_id: str) -> str:
    profile = await database.get_user(user_id)  # Raises exception to LLM
    return str(profile)
```

### Validation

Validate inputs before processing:

```python
@function_tool
async def schedule_meeting(
    self,
    date: str,
    time: str,
    duration_minutes: int
) -> str:
    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return f"Invalid date format '{date}'. Please use YYYY-MM-DD (e.g., 2024-03-15)"

    # Validate time format
    try:
        datetime.strptime(time, "%H:%M")
    except ValueError:
        return f"Invalid time format '{time}'. Please use HH:MM in 24-hour format (e.g., 14:30)"

    # Validate duration
    if not 15 <= duration_minutes <= 480:
        return "Meeting duration must be between 15 minutes and 8 hours"

    # Proceed with scheduling
    meeting = await calendar.create_meeting(date, time, duration_minutes)
    return f"Meeting scheduled for {date} at {time} ({duration_minutes} minutes)"
```

## Security

### Never Trust LLM Input

Always validate and sanitize inputs:

```python
@function_tool
async def execute_database_query(self, table: str, field: str, value: str) -> str:
    # Validate table name against whitelist
    ALLOWED_TABLES = ["users", "orders", "products"]
    if table not in ALLOWED_TABLES:
        return f"Access to table '{table}' is not allowed"

    # Use parameterized queries to prevent SQL injection
    query = "SELECT * FROM {table} WHERE {field} = ?"  # Parameterized
    results = await database.execute(query, (table, field, value))

    return f"Found {len(results)} results"
```

### Require Confirmation for Destructive Actions

```python
@function_tool
async def delete_all_data(self, confirmation: str, context: RunContext) -> str:
    """Delete all user data (DESTRUCTIVE).

    Requires explicit confirmation by typing "CONFIRM DELETE ALL DATA".

    Args:
        confirmation: Must be exactly "CONFIRM DELETE ALL DATA"
        context: Runtime context
    """
    if confirmation != "CONFIRM DELETE ALL DATA":
        return "Deletion cancelled. To confirm, you must type exactly: CONFIRM DELETE ALL DATA"

    # Additional safety: check user permissions
    if not context.userdata.get("is_admin", False):
        return "Only administrators can delete all data"

    # Perform deletion
    await database.delete_all()
    return "All data has been deleted"
```

### Respect Permissions

```python
@function_tool
async def view_sensitive_data(self, record_id: str, context: RunContext) -> str:
    """View sensitive financial records."""

    # Check permissions
    user_role = context.userdata.get("role", "guest")
    if user_role not in ["admin", "financial_analyst"]:
        return "You don't have permission to view sensitive financial data"

    # Verify the user has access to this specific record
    user_id = context.userdata.get("user_id")
    if not await has_access(user_id, record_id):
        return "You don't have access to this record"

    # Proceed with retrieval
    data = await database.get_sensitive_record(record_id)
    return f"Record {record_id}: {data}"
```

### Protect Against Prompt Injection

```python
@function_tool
async def send_email(self, to: str, subject: str, body: str) -> str:
    """Send an email."""

    # Validate email format
    if not is_valid_email(to):
        return f"Invalid email address: {to}"

    # Sanitize subject and body
    subject = subject[:200]  # Limit length
    body = body[:5000]

    # Check for suspicious patterns
    if any(pattern in body.lower() for pattern in ["ignore previous", "new instruction", "system:"]):
        logger.warning(f"Possible prompt injection attempt in email: {body}")
        return "Email content contains suspicious patterns. Please rephrase."

    # Send email
    await email_service.send(to, subject, body)
    return f"Email sent to {to}"
```

## Performance

### Use Async/Await

Never block the event loop:

✅ **Good**: Async I/O
```python
@function_tool
async def fetch_data(self, url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.text()
    return data
```

❌ **Bad**: Blocking I/O
```python
@function_tool
async def fetch_data(self, url: str) -> str:
    response = requests.get(url)  # Blocks event loop!
    return response.text
```

### Implement Timeouts

Prevent tools from hanging indefinitely:

```python
@function_tool
async def fetch_external_data(self, url: str) -> str:
    try:
        async with asyncio.timeout(10):  # 10 second timeout
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.text()
    except asyncio.TimeoutError:
        return "Request timed out after 10 seconds"
```

### Cache Results

Cache expensive operations:

```python
from functools import lru_cache
from datetime import datetime, timedelta

# Cache with TTL
_cache = {}

async def get_weather_data(location: str) -> dict:
    # Check cache
    if location in _cache:
        cached_data, timestamp = _cache[location]
        if datetime.now() - timestamp < timedelta(minutes=15):
            return cached_data

    # Fetch fresh data
    data = await weather_api.fetch(location)

    # Update cache
    _cache[location] = (data, datetime.now())

    return data

@function_tool
async def get_weather(self, location: str) -> str:
    data = await get_weather_data(location)
    return f"Weather in {location}: {data['condition']}, {data['temp']}°F"
```

### Limit Response Size

Don't overwhelm the LLM with huge responses:

```python
@function_tool
async def search_database(self, query: str) -> str:
    results = await database.search(query)

    # Limit results
    MAX_RESULTS = 10
    if len(results) > MAX_RESULTS:
        limited_results = results[:MAX_RESULTS]
        return f"Found {len(results)} results (showing first {MAX_RESULTS}):\n" + \
               "\n".join(str(r) for r in limited_results)

    return f"Found {len(results)} results:\n" + "\n".join(str(r) for r in results)
```

## User Experience

### Provide Feedback for Long Operations

```python
@function_tool
async def process_large_file(self, filename: str, context: RunContext) -> str:
    # Announce starting
    await context.session.generate_reply(
        instructions=f"Tell the user you're starting to process {filename} and it may take a minute",
        allow_interruptions=False
    )

    # Process file
    result = await long_processing(filename)

    return f"Finished processing {filename}: {result}"
```

### Natural Conversation Flow

Design tools that enable natural responses:

✅ **Good**: Conversational return
```python
@function_tool
async def check_order_status(self, order_id: str) -> str:
    order = await get_order(order_id)
    return f"Your order #{order_id} is {order.status}. It's expected to arrive on {order.delivery_date}."
```

❌ **Bad**: Data dump
```python
@function_tool
async def check_order_status(self, order_id: str) -> str:
    order = await get_order(order_id)
    return str(order)  # Returns raw object representation
```

### Handle Ambiguity

```python
@function_tool
async def search_products(self, query: str) -> str:
    results = await product_search(query)

    if len(results) == 0:
        return f"I couldn't find any products matching '{query}'. Try different keywords or check the spelling."

    if len(results) == 1:
        return f"I found one product: {results[0].name} - ${results[0].price}"

    if len(results) > 20:
        return f"I found {len(results)} products matching '{query}'. That's a lot! Can you be more specific?"

    return f"I found {len(results)} products:\n" + "\n".join(
        f"- {r.name}: ${r.price}" for r in results
    )
```

## Code Organization

### Group Related Tools

```python
class OrderManagementAgent(Agent):
    """Agent for order management with related tools grouped."""

    @function_tool
    async def create_order(self, items: list[str]) -> str:
        """Create a new order."""

    @function_tool
    async def get_order_status(self, order_id: str) -> str:
        """Check order status."""

    @function_tool
    async def update_order(self, order_id: str, changes: dict) -> str:
        """Modify an existing order."""

    @function_tool
    async def cancel_order(self, order_id: str) -> str:
        """Cancel an order."""
```

### Extract Complex Logic

Keep tool functions focused on coordination:

✅ **Good**: Separated concerns
```python
# business_logic.py
async def calculate_shipping_cost(items: list, destination: str) -> float:
    """Complex shipping calculation logic."""
    # ... complex logic ...
    return cost

# agent.py
@function_tool
async def get_shipping_quote(self, items: list[str], destination: str) -> str:
    """Get shipping cost estimate."""
    cost = await calculate_shipping_cost(items, destination)
    return f"Shipping to {destination} will cost ${cost:.2f}"
```

❌ **Bad**: Everything in the tool
```python
@function_tool
async def get_shipping_quote(self, items: list[str], destination: str) -> str:
    # Hundreds of lines of calculation logic here...
    return f"Shipping costs ${cost}"
```

### Use Type Hints

```python
from typing import Annotated
from pydantic import Field

@function_tool
async def create_event(
    self,
    title: str,
    date: Annotated[str, Field(description="Date in YYYY-MM-DD format")],
    attendees: list[str],
    optional: bool = False
) -> str:
    """Create a calendar event with proper type hints."""
```

## Documentation

### Document Tool Purpose

```python
@function_tool
async def escalate_to_supervisor(self, reason: str, context: RunContext):
    """Escalate the conversation to a supervisor.

    Use this tool when:
    - Issue is beyond your capability to resolve
    - User explicitly requests a supervisor
    - Situation requires higher authority

    Do NOT use for:
    - Routine questions you can answer
    - Issues you haven't attempted to solve
    - User is just frustrated (try de-escalation first)

    Args:
        reason: Specific reason for escalation (be detailed)
        context: Runtime context
    """
```

### Document Parameters Clearly

```python
@function_tool
async def book_appointment(
    self,
    service: str,
    date: str,
    time: str,
    duration: int
) -> str:
    """Book an appointment.

    Args:
        service: Service type (e.g., "consultation", "procedure", "followup")
        date: Appointment date in YYYY-MM-DD format (e.g., "2024-03-15")
        time: Start time in HH:MM 24-hour format (e.g., "14:30")
        duration: Appointment duration in minutes (15, 30, 45, or 60)
    """
```

## Production Readiness

### Logging

```python
import logging

logger = logging.getLogger(__name__)

@function_tool
async def process_payment(self, amount: float, payment_method: str) -> str:
    logger.info(f"Processing payment: ${amount} via {payment_method}")

    try:
        result = await payment_gateway.charge(amount, payment_method)
        logger.info(f"Payment successful: {result.transaction_id}")
        return f"Payment of ${amount} processed successfully"
    except PaymentError as e:
        logger.error(f"Payment failed: {e}")
        return "Payment failed. Please try a different payment method."
```

### Monitoring

```python
from prometheus_client import Counter, Histogram

tool_calls = Counter('agent_tool_calls_total', 'Total tool calls', ['tool_name', 'status'])
tool_duration = Histogram('agent_tool_duration_seconds', 'Tool execution time', ['tool_name'])

@function_tool
async def monitored_tool(self, param: str) -> str:
    with tool_duration.labels(tool_name='monitored_tool').time():
        try:
            result = await do_work(param)
            tool_calls.labels(tool_name='monitored_tool', status='success').inc()
            return result
        except Exception as e:
            tool_calls.labels(tool_name='monitored_tool', status='error').inc()
            raise
```

### Error Tracking

```python
import sentry_sdk

@function_tool
async def critical_operation(self, data: str) -> str:
    try:
        result = await perform_operation(data)
        return result
    except Exception as e:
        # Report to error tracking
        sentry_sdk.capture_exception(e)
        logger.error(f"Critical operation failed: {e}")
        return "An error occurred. The team has been notified."
```

### Configuration

```python
from pydantic_settings import BaseSettings

class AgentSettings(BaseSettings):
    api_key: str
    api_timeout: int = 30
    max_retries: int = 3
    cache_ttl: int = 900  # 15 minutes

    class Config:
        env_file = ".env"

settings = AgentSettings()

@function_tool
async def configured_tool(self, query: str) -> str:
    async with asyncio.timeout(settings.api_timeout):
        result = await api.query(query, api_key=settings.api_key)
    return result
```

### Graceful Degradation

```python
@function_tool
async def fetch_recommendations(self, user_id: str) -> str:
    try:
        # Try ML-powered recommendations
        recommendations = await ml_service.get_recommendations(user_id)
        return f"Personalized recommendations: {recommendations}"
    except MLServiceUnavailable:
        # Fallback to simple recommendations
        logger.warning("ML service unavailable, using fallback")
        recommendations = await get_popular_items()
        return f"Popular items: {recommendations}"
```

## Summary Checklist

✅ **Tool Design**
- [ ] Single responsibility per tool
- [ ] Clear, action-oriented names
- [ ] Comprehensive descriptions with when/when-not guidance
- [ ] Meaningful return values

✅ **Error Handling**
- [ ] All exceptions caught and handled gracefully
- [ ] User-friendly error messages
- [ ] Input validation
- [ ] Logging of errors

✅ **Security**
- [ ] Input sanitization
- [ ] Permission checks
- [ ] Confirmation for destructive actions
- [ ] Protection against injection attacks

✅ **Performance**
- [ ] Async/await for all I/O
- [ ] Timeouts implemented
- [ ] Caching where appropriate
- [ ] Response size limits

✅ **User Experience**
- [ ] Feedback for long operations
- [ ] Natural conversation flow
- [ ] Ambiguity handling
- [ ] Helpful error messages

✅ **Production**
- [ ] Logging implemented
- [ ] Monitoring/metrics
- [ ] Error tracking
- [ ] Configuration externalized
- [ ] Tests written
