# Multi-Agent Patterns

Build sophisticated workflows with multiple specialized agents that coordinate through tools, state management, and handoffs.

## Table of Contents

- [When to Use Multiple Agents](#when-to-use-multiple-agents)
- [Agent Handoff Pattern](#agent-handoff-pattern)
- [Shared State Across Agents](#shared-state-across-agents)
- [Information Gathering Agents](#information-gathering-agents)
- [Specialist Agents](#specialist-agents)
- [Supervisor Pattern](#supervisor-pattern)
- [Context Preservation](#context-preservation)
- [Advanced Patterns](#advanced-patterns)

## When to Use Multiple Agents

Create separate agents when you need:

- **Distinct reasoning behavior**: Different agents for sales, support, billing
- **Different tool access**: Each agent has specialized capabilities
- **Workflow stages**: Greeter → Order → Checkout → Confirmation
- **Escalation paths**: Basic agent → Specialist → Supervisor

Use a single agent with multiple tools when:
- All operations share the same reasoning context
- Tools are complementary (search, then format results)
- No clear stage boundaries

## Agent Handoff Pattern

### Basic Handoff

Tools can return a new agent to transfer the conversation:

```python
from livekit.agents import Agent
from livekit.agents.llm import function_tool
from livekit.agents.voice import RunContext

class GreeterAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="Welcome users and ask how you can help them.",
            llm="openai/gpt-4o-mini"
        )

    @function_tool
    async def transfer_to_sales(self, context: RunContext):
        """Transfer to sales agent when user wants to make a purchase."""
        sales_agent = SalesAgent()
        return sales_agent, "Let me connect you with our sales team."

class SalesAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="Help customers purchase products.",
            llm="openai/gpt-4o-mini"
        )

    @function_tool
    async def complete_purchase(self, amount: float, context: RunContext) -> str:
        """Complete the purchase."""
        return f"Purchase of ${amount} completed. Thank you!"
```

**Key points**:
- Tools return `(new_agent, transition_message)` tuple
- The transition message is spoken before switching
- The new agent takes over from that point

### Conditional Handoff

Transfer based on gathered information:

```python
class ReservationAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="Help users make restaurant reservations."
        )

    @function_tool
    async def check_availability(
        self,
        date: str,
        time: str,
        party_size: int,
        context: RunContext
    ):
        """Check if reservation is available."""
        available = await check_reservation_availability(date, time, party_size)

        if not available:
            # Transfer to waitlist agent
            waitlist_agent = WaitlistAgent()
            return waitlist_agent, "Unfortunately that time is booked. Let me help you join the waitlist."

        # Continue with this agent
        context.userdata["reservation"] = {
            "date": date,
            "time": time,
            "party_size": party_size
        }
        return "Great! That time is available. Can I get a name for the reservation?"
```

## Shared State Across Agents

### Using UserData for State Transfer

State in `context.userdata` automatically transfers between agents:

```python
from dataclasses import dataclass, field

@dataclass
class OrderData:
    customer_name: str = ""
    items: list[dict] = field(default_factory=list)
    total: float = 0.0
    payment_confirmed: bool = False

class OrderAgent(Agent):
    @function_tool
    async def add_item(
        self,
        item_name: str,
        quantity: int,
        price: float,
        context: RunContext
    ) -> str:
        """Add item to order."""
        # Initialize order data if needed
        if "order" not in context.userdata:
            context.userdata["order"] = OrderData()

        order = context.userdata["order"]
        order.items.append({
            "name": item_name,
            "quantity": quantity,
            "price": price
        })
        order.total += price * quantity

        return f"Added {quantity}x {item_name} to your order. Total: ${order.total}"

    @function_tool
    async def proceed_to_checkout(self, context: RunContext):
        """Transfer to checkout agent."""
        order = context.userdata.get("order")

        if not order or not order.items:
            return "Your cart is empty. Please add items first."

        checkout_agent = CheckoutAgent()
        return checkout_agent, f"Your total is ${order.total}. Let's complete your order."

class CheckoutAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="Process payment and complete the order."
        )

    @function_tool
    async def confirm_payment(
        self,
        payment_method: str,
        context: RunContext
    ) -> str:
        """Process payment."""
        order = context.userdata["order"]

        # Process payment
        order.payment_confirmed = True

        return f"Payment of ${order.total} processed via {payment_method}. Your order is confirmed!"
```

### State Summary Pattern

Provide state summary to new agents:

```python
@dataclass
class CustomerProfile:
    name: str = ""
    email: str = ""
    issue_type: str = ""
    priority: str = "normal"

    def to_yaml(self) -> str:
        """Convert to YAML for agent instructions."""
        return f"""
customer_name: {self.name}
email: {self.email}
issue_type: {self.issue_type}
priority: {self.priority}
"""

class IntakeAgent(Agent):
    @function_tool
    async def escalate_to_specialist(self, context: RunContext):
        """Escalate to specialist agent."""
        profile = context.userdata.get("profile", CustomerProfile())

        # Create specialist with context
        specialist = SpecialistAgent(customer_context=profile.to_yaml())

        return specialist, "Let me connect you with a specialist who can help."

class SpecialistAgent(Agent):
    def __init__(self, customer_context: str):
        super().__init__(
            instructions=f"""You are a specialist support agent.

Customer context:
{customer_context}

Use this context to provide personalized support."""
        )
```

## Information Gathering Agents

Collect information before transferring to specialized agents:

```python
class IntroAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""Gather the user's name and location to personalize their experience.
            Once you have both pieces of information, call the information_gathered tool."""
        )

    @function_tool
    async def information_gathered(
        self,
        name: str,
        location: str,
        context: RunContext
    ):
        """Called when user has provided name and location.

        Args:
            name: User's name
            location: User's location
            context: Runtime context
        """
        # Store in userdata
        context.userdata["name"] = name
        context.userdata["location"] = location

        # Create personalized agent
        main_agent = PersonalizedAgent(name, location)

        return main_agent, f"Nice to meet you, {name}! Let me help you with that."

class PersonalizedAgent(Agent):
    def __init__(self, name: str, location: str):
        super().__init__(
            instructions=f"""You are helping {name} from {location}.
            Use their name naturally in conversation and provide location-relevant information."""
        )
```

## Specialist Agents

Route to domain specialists based on user needs:

```python
class RouterAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="Understand what the user needs and route them to the appropriate specialist."
        )

    @function_tool
    async def route_to_technical_support(self, context: RunContext):
        """Route to technical support for technical issues."""
        tech_agent = TechnicalSupportAgent()
        return tech_agent, "Let me connect you with technical support."

    @function_tool
    async def route_to_billing(self, context: RunContext):
        """Route to billing for payment and subscription issues."""
        billing_agent = BillingAgent()
        return billing_agent, "I'll transfer you to our billing department."

    @function_tool
    async def route_to_sales(self, context: RunContext):
        """Route to sales for purchasing and upgrades."""
        sales_agent = SalesAgent()
        return sales_agent, "Let me connect you with a sales specialist."

class TechnicalSupportAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="Provide technical support and troubleshooting."
        )

    @function_tool
    async def run_diagnostics(self, issue_description: str) -> str:
        """Run system diagnostics."""
        # Technical support tools
        return "Diagnostics complete. I found the issue."

class BillingAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="Handle billing, payments, and subscriptions."
        )

    @function_tool
    async def check_subscription_status(self, customer_id: str) -> str:
        """Check subscription status."""
        # Billing tools
        return "Your subscription is active."
```

## Supervisor Pattern

Escalate to supervisor agents with full context:

```python
class FrontlineAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="Provide first-level support. Escalate complex issues to supervisor."
        )

    @function_tool
    async def escalate_to_supervisor(
        self,
        reason: str,
        context: RunContext
    ):
        """Escalate to supervisor with context.

        Args:
            reason: Why this needs supervisor attention
            context: Runtime context
        """
        # Gather conversation summary
        context.userdata["escalation_reason"] = reason
        context.userdata["escalated_at"] = datetime.now().isoformat()

        supervisor = SupervisorAgent(
            escalation_context=f"Escalated because: {reason}"
        )

        return supervisor, "Let me connect you with my supervisor who can better assist you."

class SupervisorAgent(Agent):
    def __init__(self, escalation_context: str):
        super().__init__(
            instructions=f"""You are a supervisor handling an escalated case.

Escalation context:
{escalation_context}

You have full authority to resolve the issue."""
        )

    @function_tool
    async def approve_refund(self, amount: float) -> str:
        """Approve refund (supervisor-only action)."""
        return f"Refund of ${amount} approved."

    @function_tool
    async def resolve_and_close(self, resolution: str, context: RunContext) -> str:
        """Mark case as resolved."""
        context.userdata["resolved"] = True
        context.userdata["resolution"] = resolution
        return f"Case resolved: {resolution}"
```

## Context Preservation

### Preserving Chat History

Transfer recent conversation context to new agents:

```python
async def transfer_with_history(
    self,
    new_agent: Agent,
    message: str,
    context: RunContext,
    history_items: int = 10
):
    """Transfer to new agent with conversation history.

    Args:
        new_agent: Agent to transfer to
        message: Transition message
        context: Runtime context
        history_items: Number of recent messages to transfer
    """
    # Get recent chat history
    chat_ctx = context.session.chat_context
    recent_messages = chat_ctx.messages[-history_items:]

    # Store in userdata for new agent
    context.userdata["transferred_history"] = recent_messages

    return new_agent, message
```

### Limiting Context Transfer

Avoid overwhelming new agents with too much history:

```python
def summarize_for_transfer(context: RunContext) -> str:
    """Create concise summary for agent handoff."""
    summary_parts = []

    # Key facts only
    if "customer_name" in context.userdata:
        summary_parts.append(f"Customer: {context.userdata['customer_name']}")

    if "issue_type" in context.userdata:
        summary_parts.append(f"Issue: {context.userdata['issue_type']}")

    if "order_id" in context.userdata:
        summary_parts.append(f"Order: {context.userdata['order_id']}")

    return "\n".join(summary_parts)

@function_tool
async def transfer_to_agent(self, context: RunContext):
    """Transfer with concise context summary."""
    summary = summarize_for_transfer(context)

    new_agent = NextAgent(
        instructions=f"Continue helping this customer.\n\nContext:\n{summary}"
    )

    return new_agent, "Let me transfer you to someone who can help."
```

## Advanced Patterns

### Conditional Return Paths

Agents that can return to previous agents:

```python
class ConfirmationAgent(Agent):
    def __init__(self, previous_agent: Agent):
        super().__init__(
            instructions="Confirm the action with the user."
        )
        self.previous_agent = previous_agent

    @function_tool
    async def user_confirmed(self, context: RunContext) -> str:
        """User confirmed the action."""
        # Complete the action
        result = await complete_action(context.userdata)
        return f"Action completed: {result}"

    @function_tool
    async def user_cancelled(self, context: RunContext):
        """User cancelled the action."""
        # Return to previous agent
        return self.previous_agent, "No problem, let's try something else."
```

### Shared Tools Across Agents

Define common tools once, use in multiple agents:

```python
async def update_customer_name(name: str, context: RunContext) -> str:
    """Shared tool to update customer name."""
    context.userdata["customer_name"] = name
    return f"Updated name to {name}"

async def update_customer_email(email: str, context: RunContext) -> str:
    """Shared tool to update customer email."""
    context.userdata["customer_email"] = email
    return f"Updated email to {email}"

# Register shared tools with multiple agents
greeter = GreeterAgent(
    tools=[
        function_tool(update_customer_name, name="update_name", description="..."),
        function_tool(update_customer_email, name="update_email", description="...")
    ]
)

checkout = CheckoutAgent(
    tools=[
        function_tool(update_customer_name, name="update_name", description="..."),
        function_tool(update_customer_email, name="update_email", description="...")
    ]
)
```

### Multi-Step Workflows

Guide users through ordered steps:

```python
class OnboardingAgent(Agent):
    def __init__(self, step: int = 1):
        super().__init__(
            instructions=f"Guide user through step {step} of onboarding."
        )
        self.step = step

    @function_tool
    async def complete_step(self, data: dict, context: RunContext):
        """Complete current step and move to next."""
        # Save step data
        context.userdata[f"step_{self.step}_data"] = data

        # Move to next step
        next_step = self.step + 1

        if next_step > 3:
            # Onboarding complete
            return "Onboarding complete! You're all set."

        # Continue to next step
        next_agent = OnboardingAgent(step=next_step)
        return next_agent, f"Great! Let's move on to step {next_step}."
```

## Best Practices

1. **Use state for data, agents for behavior**: UserData holds information, agents embody different interaction styles
2. **Clear handoff messages**: Always explain why transferring ("Let me connect you with billing")
3. **Preserve essential context**: Transfer key facts, not entire conversation
4. **Avoid ping-ponging**: Don't transfer back and forth repeatedly
5. **Specialize appropriately**: Don't create agents that are too similar
6. **Test transitions**: Ensure state transfers correctly
7. **Handle edge cases**: What if user says "nevermind" mid-transfer?

## Common Pitfalls

❌ **Don't create too many agents**: 3-5 agents is usually sufficient
❌ **Don't lose context**: Always transfer essential userdata
❌ **Don't forget transition messages**: Users need to know what's happening
❌ **Don't duplicate tools**: Share common tools across agents
❌ **Don't transfer without reason**: Each handoff should add value

✅ **Do plan your agent structure**: Map out the flow before building
✅ **Do test all paths**: Try every possible agent transition
✅ **Do document state expectations**: What each agent needs from userdata
✅ **Do use clear agent purposes**: Each agent should have a distinct role
✅ **Do limit handoff depth**: Avoid deeply nested agent chains
