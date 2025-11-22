# LiveKit Agent Best Practices

This guide covers best practices for building production-ready LiveKit voice agents based on real-world implementations and LiveKit's recommendations.

## Architecture Best Practices

### 1. Agent Separation

**When to create separate agents:**
- Different reasoning behavior needed
- Different tool access requirements
- Different permissions or security contexts
- Specialized domain knowledge required
- Different personality or tone needed

**When NOT to create separate agents:**
- Minor instruction variations
- Temporary state changes
- Simple branching logic
- Different responses to same capability

**Example: Good separation**
```python
# GOOD: Clear role distinction
class TriageAgent(Agent):
    """Quickly categorizes issues and routes"""
    # Simple, fast, focused on classification

class TechnicalSupportAgent(Agent):
    """Deep technical troubleshooting"""
    # Complex tools, detailed instructions
```

**Example: Poor separation**
```python
# BAD: Unnecessary separation
class PoliteAgent(Agent):
    """Responds politely"""

class VeryPoliteAgent(Agent):
    """Responds very politely"""
# These should be one agent with context-aware instructions
```

### 2. Prewarm Pattern

**Always prewarm static resources:**

```python
def prewarm(proc: JobProcess):
    """Load models and static data before sessions"""
    # Load VAD model (expensive, reusable)
    proc.userdata["vad"] = silero.VAD.load()

    # Load any other static models
    # proc.userdata["classifier"] = load_custom_model()
```

**DON'T prewarm user-specific data:**

```python
# BAD: User-specific data in prewarm
def prewarm(proc: JobProcess):
    # This won't work - no user context yet
    proc.userdata["user_profile"] = fetch_user_profile()  # ❌

# GOOD: User-specific data in entrypoint
async def entrypoint(ctx: JobContext):
    # Access user metadata from room/participant
    user_id = ctx.room.metadata.get("user_id")
    user_profile = await fetch_user_profile(user_id)  # ✅
```

### 3. Entrypoint Performance

**Critical: Connect before expensive operations:**

```python
async def entrypoint(ctx: JobContext):
    # GOOD: Connect immediately
    await ctx.connect()  # ✅

    # Then do expensive operations
    data = await fetch_external_data()

    # BAD: Expensive ops before connect
    # data = await fetch_external_data()  # ❌ Delays connection
    # await ctx.connect()
```

**Why:** Users see connection latency. Connect fast, load lazily.

### 4. Context Management

**Use typed userdata:**

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class ConversationData:
    """Strongly typed shared context"""
    user_name: str = ""
    user_email: str = ""
    collected_items: List[str] = field(default_factory=list)

    # Good: Validation method
    def is_complete(self) -> bool:
        return bool(self.user_name and self.user_email)

# Use with generics
session = AgentSession[ConversationData](
    # ...
    userdata=ConversationData(),
)
```

**Preserve critical context:**

```python
@function_tool
async def handoff_to_specialist(
    self,
    context: RunContext[ConversationData],
    issue_summary: str,
):
    # Store in shared context
    context.userdata.issue_summary = issue_summary  # ✅

    # Preserve conversation history
    specialist = SpecialistAgent(
        chat_ctx=self.chat_ctx  # ✅ Keeps chat history
    )

    return specialist, "Transferring to specialist..."
```

## Instruction Writing

### 1. Clear Role Definition

**Good instructions:**

```python
instructions = """You are a technical support agent specializing in API issues.

Your role:
1. Understand the specific API error or problem
2. Check API key validity and permissions
3. Review request format and parameters
4. Provide step-by-step debugging guidance

When you identify the issue and have a solution, explain it clearly
with code examples if needed. If the issue requires escalation (billing,
account access, or beyond API scope), transfer to the escalation agent.

Be technical but clear. Use precise terminology. Ask for specific
details like error codes, request payloads, and response statuses."""
```

**Poor instructions:**

```python
instructions = """You help users with problems.
Be helpful and nice."""
# Too vague, no specific guidance
```

### 2. Handoff Conditions

**Be explicit about when to handoff:**

```python
instructions = """...

Transfer to specialist when:
- User explicitly requests a human
- Issue requires account access you don't have
- You've attempted 3 solutions without success
- User is frustrated (indicated by tone or repetition)

Do NOT transfer if:
- You haven't tried basic troubleshooting
- User just has simple questions
- Issue is within your capability to resolve"""
```

### 3. Tone and Style Guidance

```python
instructions = """...

Communication style:
- Conversational but professional
- Use "I" and "you" (not "we" or "the system")
- Acknowledge user frustration with empathy
- Keep responses concise (2-3 sentences typically)
- Avoid corporate jargon

Examples:
✅ "I see the issue - your API key doesn't have write permissions."
❌ "The system has identified a permissions discrepancy in your credentials."
"""
```

## Tool Design

### 1. Function Tool Structure

**Best practices:**

```python
from typing import Annotated
from livekit.agents.llm import function_tool, ToolError
from livekit.agents import RunContext

@function_tool
async def lookup_order_status(
    context: RunContext,
    order_id: Annotated[
        str,
        "The order ID in format ORD-XXXXX. Example: ORD-12345"
    ],
) -> str:
    """Look up the current status of an order.

    Returns the order status, shipping info, and estimated delivery date.
    Use this when the user asks about their order or delivery.

    Common questions this answers:
    - "Where is my order?"
    - "When will my package arrive?"
    - "What's the status of order X?"
    """
    try:
        # Validate format
        if not order_id.startswith("ORD-"):
            raise ToolError(
                f"Invalid order ID format: {order_id}. "
                "Order IDs should start with 'ORD-' followed by numbers. "
                "Example: ORD-12345"
            )

        # Make API call
        result = await api_client.get_order(order_id)

        return (
            f"Order {order_id} status: {result.status}\n"
            f"Shipped: {result.ship_date}\n"
            f"Estimated delivery: {result.delivery_date}"
        )

    except OrderNotFoundError:
        raise ToolError(
            f"Order {order_id} not found. Please verify the order ID "
            "or ask the user to check their confirmation email."
        )
    except Exception as e:
        raise ToolError(
            f"Unable to retrieve order status: {str(e)}. "
            "Please try again or escalate to a human agent."
        )
```

**Key elements:**
1. **Type hints with Annotated**: Help LLM understand parameters
2. **Detailed docstring**: LLM sees this, explain clearly
3. **Examples**: Show expected input/output formats
4. **Error handling**: Always return actionable messages
5. **ToolError usage**: Provides feedback to LLM for recovery

### 2. Tool Naming

**Good names:**
- `lookup_order_status` (clear action + object)
- `schedule_callback` (action-oriented)
- `verify_payment_method` (specific purpose)
- `escalate_to_human` (clear intent)

**Poor names:**
- `get_data` (too vague)
- `handle_order` (unclear what it does)
- `process` (no context)
- `tool1` (meaningless)

### 3. Tool Scope

**Single responsibility:**

```python
# GOOD: Focused tools
@function_tool
async def get_account_balance(context, account_id: str) -> str:
    """Get current account balance"""
    # Just returns balance

@function_tool
async def get_recent_transactions(context, account_id: str) -> str:
    """Get last 10 transactions"""
    # Just returns transactions

# BAD: Kitchen sink tool
@function_tool
async def get_account_everything(
    context,
    account_id: str,
    include_balance: bool,
    include_transactions: bool,
    include_preferences: bool,
) -> str:
    """Get various account information"""
    # Too many responsibilities, complex parameters
```

**Why:** Focused tools are easier for LLMs to use correctly and compose together.

## Handoff Best Practices

### 1. Preserve Context

**Always pass critical data:**

```python
@function_tool
async def transfer_to_billing(
    self,
    context: RunContext[UserData],
    issue_description: str,
):
    # Update shared context
    context.userdata.issue_description = issue_description
    context.userdata.transferred_from = "technical_support"
    context.userdata.transfer_reason = "billing_issue"

    # Create agent with context
    billing_agent = BillingAgent(
        user_name=context.userdata.user_name,  # Pass name
        chat_ctx=self.chat_ctx,  # Preserve history
    )

    return billing_agent, (
        f"I'm transferring you to our billing team. "
        f"They'll help with: {issue_description}"
    )
```

### 2. Announce Transitions

**Good transition messages:**

```python
# Clear and informative
return agent, "Connecting you to our technical specialist who can help with API issues."

return agent, "Let me get you to someone who can access your account details."

return agent, "I'm transferring you to Sarah, our senior support agent."
```

**Poor transition messages:**

```python
# Too vague or jarring
return agent, "Transferring."  # No context

return agent, "You are now talking to Agent B."  # Robotic

return agent, ""  # Silent handoff confuses users
```

### 3. Bidirectional Handoffs

**Support returning to original agent:**

```python
class SpecialistAgent(Agent):
    def __init__(self, return_to_agent=None, chat_ctx=None):
        self.return_to_agent = return_to_agent
        super().__init__(
            instructions="...",
            chat_ctx=chat_ctx,
        )

    @function_tool
    async def complete_and_return(
        self,
        context: RunContext,
        resolution_summary: str,
    ):
        """Return to original agent after completing specialized task"""
        context.userdata.resolution = resolution_summary

        if self.return_to_agent:
            return self.return_to_agent, "Returning to main agent..."
        else:
            # No return agent, stay here
            return None, "Task completed!"
```

## Error Handling

### 1. Graceful Degradation

```python
@function_tool
async def check_inventory(
    context: RunContext,
    product_id: str,
) -> str:
    """Check product inventory levels"""
    try:
        stock = await inventory_api.check(product_id)
        return f"Product {product_id} has {stock.quantity} units in stock."

    except APITimeoutError:
        # Graceful fallback
        raise ToolError(
            "Inventory system is responding slowly. "
            "I can help you place an order anyway, or we can try again shortly. "
            "What would you prefer?"
        )

    except ProductNotFoundError:
        raise ToolError(
            f"Product {product_id} not found. "
            "Could you verify the product ID or describe what you're looking for?"
        )

    except Exception as e:
        # Last resort
        logger.error(f"Inventory check failed: {e}")
        raise ToolError(
            "I'm having trouble checking inventory right now. "
            "Would you like to speak with someone who can check manually?"
        )
```

### 2. User-Friendly Error Messages

**Good error messages:**
- Explain what went wrong
- Suggest next steps
- Offer alternatives

```python
raise ToolError(
    "Your API key doesn't have permission to delete resources. "
    "You'll need to either:\n"
    "1. Use an API key with admin permissions, or\n"
    "2. Contact your account admin to grant delete permissions\n"
    "Would you like help with either option?"
)
```

**Poor error messages:**
```python
raise ToolError("Error 403")  # Too technical, no guidance

raise ToolError("Something went wrong")  # Too vague

raise ToolError("FORBIDDEN_RESOURCE_ACCESS")  # Raw error code
```

## Performance Optimization

### 1. Model Selection

**Balance quality and latency:**

```python
# Fast intro/routing agent
class GreetingAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="...",
            llm=openai.LLM(model="gpt-4o-mini"),  # Faster, cheaper
        )

# Deep reasoning agent
class AnalysisAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="...",
            llm=openai.LLM(model="gpt-4o"),  # More capable
        )
```

### 2. Lazy Loading

```python
class SpecialistAgent(Agent):
    def __init__(self):
        super().__init__(instructions="...")
        self._knowledge_base = None

    async def _get_knowledge_base(self):
        """Load knowledge base only when needed"""
        if self._knowledge_base is None:
            self._knowledge_base = await load_knowledge_base()
        return self._knowledge_base

    @function_tool
    async def search_docs(self, context: RunContext, query: str):
        kb = await self._get_knowledge_base()  # Lazy load
        return await kb.search(query)
```

### 3. Caching

```python
from functools import lru_cache
import asyncio

# Cache expensive computations
@lru_cache(maxsize=100)
def calculate_pricing(product_id: str, quantity: int) -> float:
    # Expensive calculation cached
    return complex_pricing_logic(product_id, quantity)

# Cache async API calls
class APICache:
    def __init__(self, ttl_seconds=300):
        self.cache = {}
        self.ttl = ttl_seconds

    async def get_or_fetch(self, key: str, fetch_fn):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return data

        data = await fetch_fn()
        self.cache[key] = (data, time.time())
        return data
```

## Testing Best Practices

### 1. Test Coverage

**Essential test types:**

```python
# 1. Greeting/initialization
@pytest.mark.asyncio
async def test_agent_greets_user():
    """Verify agent greets appropriately"""
    pass

# 2. Tool usage
@pytest.mark.asyncio
async def test_agent_uses_lookup_tool():
    """Verify agent calls lookup tool with correct args"""
    pass

# 3. Handoff logic
@pytest.mark.asyncio
async def test_agent_hands_off_when_appropriate():
    """Verify handoff triggers correctly"""
    pass

# 4. Error handling
@pytest.mark.asyncio
async def test_agent_handles_tool_errors():
    """Verify graceful error handling"""
    pass

# 5. Context preservation
@pytest.mark.asyncio
async def test_handoff_preserves_user_data():
    """Verify userdata persists across handoff"""
    pass
```

### 2. Test Assertions

**Use LiveKit's fluent API:**

```python
@pytest.mark.asyncio
async def test_conversation_flow():
    async with AgentSession(llm=llm) as sess:
        await sess.start(MyAgent())

        result = await sess.run(user_input="Hello")

        # Message assertions
        result.expect.next_event().is_message(role="assistant")
        result.expect.contains_message("help")

        # Tool call assertions
        result = await sess.run(user_input="Look up order 12345")
        result.expect.next_event().is_function_call(name="lookup_order_status")
        result.expect.next_event().is_function_call_output()

        # State assertions
        assert sess.userdata.current_order == "12345"
```

### 3. Mock External Services

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_order_lookup_with_mock():
    """Test tool with mocked API"""
    with patch('api_client.get_order') as mock_get:
        # Setup mock
        mock_get.return_value = AsyncMock(
            status="shipped",
            tracking="TRACK123"
        )

        # Test
        async with AgentSession(llm=llm) as sess:
            agent = SupportAgent()
            await sess.start(agent)
            result = await sess.run("Check order ORD-12345")

            # Verify mock was called correctly
            mock_get.assert_called_once_with("ORD-12345")

            # Verify response
            result.expect.contains_message("shipped")
```

## Security Best Practices

### 1. Input Validation

```python
@function_tool
async def update_user_email(
    context: RunContext,
    email: Annotated[str, "New email address"],
) -> str:
    """Update user's email address"""

    # Validate email format
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise ToolError(
            f"Invalid email format: {email}. "
            "Please provide a valid email address."
        )

    # Additional validation
    if len(email) > 255:
        raise ToolError("Email address too long.")

    # Proceed with update
    await api.update_email(context.userdata.user_id, email)
    return f"Email updated to {email}"
```

### 2. Permission Checks

```python
@function_tool
async def delete_account(
    context: RunContext,
    account_id: str,
) -> str:
    """Delete an account (requires admin privileges)"""

    # Check permissions
    user_role = context.userdata.user_role
    if user_role != "admin":
        raise ToolError(
            "Account deletion requires admin privileges. "
            "Please contact your administrator."
        )

    # Verify account ownership or admin rights
    if not await has_permission(context.userdata.user_id, account_id):
        raise ToolError(
            "You don't have permission to delete this account."
        )

    # Proceed with deletion
    await api.delete_account(account_id)
    return f"Account {account_id} deleted successfully."
```

### 3. Sensitive Data Handling

```python
# Don't log sensitive information
logger.info(f"Processing payment for user {user_id}")  # ✅
logger.info(f"Credit card: {card_number}")  # ❌

# Mask sensitive data in responses
@function_tool
async def get_payment_method(context: RunContext) -> str:
    """Get user's payment method"""
    card = await api.get_card(context.userdata.user_id)

    # Mask card number
    masked = f"**** **** **** {card.last_four}"

    return f"Payment method: {card.brand} ending in {card.last_four}"
```

## Monitoring and Observability

### 1. Structured Logging

```python
import logging
import json

logger = logging.getLogger("voice-agent")

# Structured logs for better analysis
def log_handoff(from_agent: str, to_agent: str, reason: str, user_data: dict):
    logger.info(
        json.dumps({
            "event": "agent_handoff",
            "from_agent": from_agent,
            "to_agent": to_agent,
            "reason": reason,
            "user_id": user_data.get("user_id"),
            "timestamp": time.time(),
        })
    )

# In agents
@function_tool
async def transfer_to_specialist(self, context, reason):
    log_handoff(
        from_agent=self.__class__.__name__,
        to_agent="SpecialistAgent",
        reason=reason,
        user_data={"user_id": context.userdata.user_id}
    )
    # ... handoff logic
```

### 2. Metrics Collection

```python
from livekit.agents import metrics

# Track tool usage
class InstrumentedAgent(Agent):
    def __init__(self):
        super().__init__(instructions="...")
        self.tool_usage = {}

    async def on_tool_call(self, tool_name: str):
        self.tool_usage[tool_name] = self.tool_usage.get(tool_name, 0) + 1
        logger.info(f"Tool called: {tool_name} (total: {self.tool_usage[tool_name]})")

# Track session metrics
@ctx.on("agent_completed")
async def log_completion():
    duration = time.time() - session_start
    logger.info(
        json.dumps({
            "event": "session_completed",
            "duration_seconds": duration,
            "tool_calls": sum(agent.tool_usage.values()),
            "handoffs": handoff_count,
        })
    )
```

## Common Pitfalls to Avoid

### 1. Forgetting to Connect

```python
# ❌ BAD: Connect after expensive operation
async def entrypoint(ctx: JobContext):
    await load_heavy_data()  # User waits!
    await ctx.connect()

# ✅ GOOD: Connect immediately
async def entrypoint(ctx: JobContext):
    await ctx.connect()
    await load_heavy_data()  # Load in background
```

### 2. Not Prewarming VAD

```python
# ❌ BAD: Load VAD in entrypoint
async def entrypoint(ctx: JobContext):
    vad = silero.VAD.load()  # Slow!
    session = AgentSession(vad=vad, ...)

# ✅ GOOD: Prewarm VAD
def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    vad = ctx.proc.userdata["vad"]  # Instant!
    session = AgentSession(vad=vad, ...)
```

### 3. Losing Context on Handoff

```python
# ❌ BAD: New agent has no context
@function_tool
async def handoff(self, context):
    return SpecialistAgent(), "Transferring..."
    # User name, issue details lost!

# ✅ GOOD: Preserve context
@function_tool
async def handoff(self, context):
    context.userdata.previous_agent = self.__class__.__name__
    agent = SpecialistAgent(chat_ctx=self.chat_ctx)
    return agent, "Transferring..."
```

### 4. Vague Instructions

```python
# ❌ BAD: Too vague
instructions = "Help users with their problems."

# ✅ GOOD: Specific and actionable
instructions = """You are a billing support agent.

Handle:
- Payment issues and failed transactions
- Subscription changes and cancellations
- Invoice questions and billing history

Process:
1. Verify user identity (ask for email)
2. Understand the billing issue
3. Provide solution or escalate if needed

Transfer to technical support if the issue is not billing-related."""
```

### 5. Blocking Operations

```python
# ❌ BAD: Synchronous blocking call
@function_tool
def slow_operation(context):
    time.sleep(5)  # Blocks everything!
    return result

# ✅ GOOD: Async non-blocking
@function_tool
async def fast_operation(context):
    await asyncio.sleep(5)  # Doesn't block
    return result
```

---

## Summary Checklist

Before deploying your agent:

### Architecture
- [ ] Agents have clear, distinct roles
- [ ] Handoffs are intentional and well-motivated
- [ ] Shared context is properly typed
- [ ] Static resources prewarmed

### Implementation
- [ ] Instructions are clear and specific
- [ ] Tools have descriptive names and docstrings
- [ ] Errors provide actionable guidance
- [ ] Context preserved across handoffs
- [ ] Async operations throughout

### Testing
- [ ] Unit tests for each agent
- [ ] Integration tests for handoffs
- [ ] Error scenarios covered
- [ ] Tool calls verified
- [ ] Context persistence tested

### Performance
- [ ] VAD loaded in prewarm()
- [ ] Connect() called early
- [ ] Appropriate models selected
- [ ] Caching where beneficial

### Production
- [ ] Logging structured and informative
- [ ] Metrics collected
- [ ] Errors handled gracefully
- [ ] Sensitive data protected
- [ ] Monitoring configured

---

This guide represents best practices learned from production LiveKit deployments. Adapt these patterns to your specific use case while maintaining the core principles of clarity, performance, and user experience.
