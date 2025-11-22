# Context & State Management

The `RunContext` object provides access to session state, speech control, and agent communication. It's the primary mechanism for building stateful, interactive tools.

## Table of Contents

- [RunContext Basics](#runcontext-basics)
- [User Data for State Management](#user-data-for-state-management)
- [Speech Control](#speech-control)
- [Session Access](#session-access)
- [Function Call Metadata](#function-call-metadata)
- [Advanced Patterns](#advanced-patterns)

## RunContext Basics

The `RunContext` parameter is automatically provided by the framework when your tool is called. It contains:

- `userdata` - Dictionary for sharing state across tools and agents
- `session` - Current agent session
- `speech_handle` - Control over agent speech (interruptions, etc.)
- `function_call` - Metadata about the current tool invocation

```python
from livekit.agents.voice import RunContext

@function_tool
async def my_tool(self, param: str, context: RunContext) -> str:
    # Access session state
    user_data = context.userdata

    # Control speech
    speech = context.speech_handle

    # Get session info
    session = context.session

    return "Tool executed"
```

**Important**: The `context` parameter is automatically injected—you don't pass it when calling the tool. The LLM only sees the other parameters.

## User Data for State Management

`context.userdata` is a dictionary-like object for maintaining state across tool calls and agent handoffs.

### Basic Usage

```python
@function_tool
async def save_user_name(self, name: str, context: RunContext) -> str:
    """Save the user's name for personalization.

    Args:
        name: The user's name
        context: Runtime context
    """
    context.userdata["user_name"] = name
    return f"I'll remember that your name is {name}"

@function_tool
async def greet_user(self, context: RunContext) -> str:
    """Greet the user by name if we know it."""
    name = context.userdata.get("user_name", "friend")
    return f"Hello, {name}!"
```

### Structured User Data

For complex state, use a dataclass:

```python
from dataclasses import dataclass, field

@dataclass
class UserProfile:
    name: str = ""
    email: str = ""
    preferences: dict = field(default_factory=dict)

    def to_summary(self) -> str:
        """Convert to YAML summary for agent instructions."""
        return f"""
name: {self.name}
email: {self.email}
preferences: {self.preferences}
"""

@function_tool
async def update_profile(
    self,
    name: str | None = None,
    email: str | None = None,
    context: RunContext = None
) -> str:
    # Initialize profile if not exists
    if "profile" not in context.userdata:
        context.userdata["profile"] = UserProfile()

    profile = context.userdata["profile"]

    if name:
        profile.name = name
    if email:
        profile.email = email

    return f"Updated profile: {profile.to_summary()}"
```

### State Across Agent Handoffs

User data persists when transferring between agents:

```python
@function_tool
async def collect_order_items(
    self,
    item: str,
    quantity: int,
    context: RunContext
) -> str:
    """Add items to the order."""
    if "order_items" not in context.userdata:
        context.userdata["order_items"] = []

    context.userdata["order_items"].append({
        "item": item,
        "quantity": quantity
    })

    return f"Added {quantity}x {item} to your order"

@function_tool
async def proceed_to_checkout(self, context: RunContext):
    """Transfer to checkout agent with order data."""
    # Order data is automatically available to CheckoutAgent
    checkout_agent = CheckoutAgent()
    return checkout_agent, "Let me help you complete your order"
```

## Speech Control

The `speech_handle` allows you to control agent speech, handle interruptions, and manage timing.

### Check for Interruptions

```python
@function_tool
async def long_operation(self, context: RunContext) -> str | None:
    """Perform a time-consuming operation."""
    # Start the operation
    task = asyncio.ensure_future(perform_calculation())

    # Wait, but allow interruptions
    await context.speech_handle.wait_if_not_interrupted([task])

    # Check if user interrupted
    if context.speech_handle.interrupted:
        task.cancel()
        return None  # Skip the tool reply

    return f"Result: {task.result()}"
```

### Disable Interruptions

For critical operations that must complete:

```python
@function_tool
async def process_payment(self, amount: float, context: RunContext) -> str:
    """Process a payment - cannot be interrupted."""
    # Disable interruptions for this operation
    context.speech_handle.disallow_interruptions()

    result = await payment_gateway.charge(amount)

    return f"Payment of ${amount} processed successfully"
```

### Control Agent Speech

Generate custom responses outside the normal flow:

```python
@function_tool
async def announce_event(self, event: str, context: RunContext) -> str:
    """Make an announcement to the user."""
    # Generate immediate speech
    await context.session.generate_reply(
        instructions=f"Announce this event enthusiastically: {event}",
        allow_interruptions=False
    )

    return "Announcement made"
```

## Session Access

The `session` object provides access to the current conversation and agent state.

### Generate Custom Replies

```python
@function_tool
async def goodbye(self, context: RunContext) -> str:
    """End the conversation gracefully."""
    # Interrupt any ongoing speech
    context.session.interrupt()

    # Generate final message
    await context.session.generate_reply(
        instructions="Say goodbye warmly and thank the user",
        allow_interruptions=False
    )

    return "Ending session"
```

### Access Chat History

```python
@function_tool
async def summarize_conversation(self, context: RunContext) -> str:
    """Provide a summary of the conversation so far."""
    # Access the conversation history
    chat_ctx = context.session.chat_context

    # Get recent messages
    recent_messages = chat_ctx.messages[-10:]

    # Generate summary
    summary = "Recent topics: " + ", ".join([
        msg.content for msg in recent_messages
        if hasattr(msg, 'content')
    ])

    return summary
```

## Function Call Metadata

Access information about the current tool invocation:

```python
@function_tool
async def debug_tool(self, context: RunContext) -> str:
    """Show metadata about this function call."""
    fc = context.function_call

    return f"""
Tool: {fc.name}
Called at: {fc.timestamp}
Arguments: {fc.arguments}
"""
```

## Advanced Patterns

### Shared State Between Multiple Agents

```python
from dataclasses import dataclass

@dataclass
class SharedState:
    customer_name: str = ""
    order_total: float = 0.0
    payment_confirmed: bool = False

class OrderAgent(Agent):
    @function_tool
    async def set_customer_name(self, name: str, context: RunContext) -> str:
        state = context.userdata.setdefault("shared", SharedState())
        state.customer_name = name
        return f"Recording name: {name}"

class PaymentAgent(Agent):
    @function_tool
    async def confirm_payment(self, context: RunContext) -> str:
        # Access same state
        state = context.userdata.get("shared", SharedState())
        state.payment_confirmed = True
        return f"Payment confirmed for {state.customer_name}"
```

### Context Initialization Pattern

```python
class MyAgent(Agent):
    async def on_enter(self):
        """Initialize user data when agent starts."""
        from datetime import datetime

        # Access userdata through self.session
        # Set defaults if not already set
        if "session_start" not in self.session.userdata:
            self.session.userdata["session_start"] = datetime.now().isoformat()
        self.session.userdata.setdefault("interaction_count", 0)
        self.session.userdata["interaction_count"] += 1

        # Generate initial greeting
        await self.session.generate_reply()
```

### Conditional Tool Behavior Based on State

```python
@function_tool
async def advanced_search(self, query: str, context: RunContext) -> str:
    """Search with user's preferences applied.

    Args:
        query: Search query
        context: Runtime context
    """
    # Check if user is premium
    is_premium = context.userdata.get("premium_user", False)

    if is_premium:
        # Use advanced search with more results
        results = await premium_search(query, limit=50)
        return f"Found {len(results)} premium results"
    else:
        # Basic search
        results = await basic_search(query, limit=10)
        return f"Found {len(results)} results (upgrade for more)"
```

### State Persistence Across Sessions

Note: `userdata` exists only for the current session. For persistence across sessions, use external storage:

```python
import json

@function_tool
async def save_preferences(
    self,
    preferences: dict,
    context: RunContext
) -> str:
    """Save user preferences to database."""
    user_id = context.userdata.get("user_id")

    # Save to userdata for this session
    context.userdata["preferences"] = preferences

    # Persist to database for future sessions
    await database.save_user_preferences(user_id, preferences)

    return "Preferences saved"

@function_tool
async def load_preferences(self, context: RunContext) -> str:
    """Load saved preferences from database."""
    user_id = context.userdata.get("user_id")

    # Load from database
    preferences = await database.load_user_preferences(user_id)

    # Store in userdata for this session
    context.userdata["preferences"] = preferences

    return f"Loaded preferences: {preferences}"
```

## Best Practices

1. **Always check before setting**: Use `setdefault()` or check if key exists before accessing userdata
2. **Use structured data**: Prefer dataclasses over raw dictionaries for complex state
3. **Document state expectations**: Make it clear what userdata your tools expect/provide
4. **Clean up state**: Remove unnecessary data to prevent memory bloat in long sessions
5. **Handle missing context gracefully**: Tools should work even if expected state is missing
6. **Type your context parameter**: Always use `RunContext` type hint for proper IDE support

## Common Pitfalls

❌ **Don't modify context outside tools**:
```python
# Bad: Trying to access context outside a tool
context.userdata["value"] = 123  # No context available here
```

✅ **Do use tools to manage state**:
```python
@function_tool
async def set_value(self, value: int, context: RunContext):
    context.userdata["value"] = value
```

❌ **Don't assume userdata exists**:
```python
# Bad: May raise KeyError
name = context.userdata["name"]
```

✅ **Do check or provide defaults**:
```python
# Good: Safe access
name = context.userdata.get("name", "Guest")
```

❌ **Don't store large objects in userdata**:
```python
# Bad: Keeping full dataset in memory
context.userdata["all_records"] = huge_database_result
```

✅ **Do store references or summaries**:
```python
# Good: Store IDs or summaries
context.userdata["selected_record_id"] = record.id
context.userdata["summary"] = generate_summary(records)
```
