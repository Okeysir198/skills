# Multi-Agent Patterns for LiveKit Voice Agents

This guide covers proven patterns for implementing multi-agent workflows with LiveKit Agents.

## Pattern Overview

Multi-agent systems excel when:
- Different stages require different capabilities
- Specialized knowledge domains exist
- Permission levels vary
- User journey has distinct phases
- Escalation paths are needed

## Core Patterns

### Pattern 1: Linear Pipeline

**Structure:** A → B → C → D

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Agent A │───▶│  Agent B │───▶│  Agent C │───▶│  Agent D │
│ (Intro)  │    │(Collect) │    │(Process) │    │(Confirm) │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

**Best for:**
- Order processing
- Form filling
- Onboarding flows
- Sequential workflows

**Example: Restaurant Ordering**

```python
from dataclasses import dataclass, field
from livekit.agents import Agent, RunContext
from livekit.agents.llm import function_tool
from typing import List, Annotated

@dataclass
class OrderData:
    customer_name: str = ""
    items: List[dict] = field(default_factory=list)
    total_price: float = 0.0
    payment_method: str = ""
    confirmed: bool = False


class WelcomeAgent(Agent):
    """Greets customer and gets name"""

    def __init__(self):
        super().__init__(
            instructions="""You are a friendly restaurant order-taker.

Greet the customer warmly and ask for their name. Once you have
their name, immediately transfer to the menu agent to start ordering.

Keep it brief and welcoming."""
        )

    @function_tool
    async def proceed_to_menu(
        self,
        context: RunContext[OrderData],
        customer_name: Annotated[str, "Customer's name"],
    ):
        """Transfer to menu navigation after getting name"""
        context.userdata.customer_name = customer_name

        menu_agent = MenuAgent(chat_ctx=self.chat_ctx)
        return menu_agent, f"Thanks {customer_name}! Let me show you our menu."


class MenuAgent(Agent):
    """Handles menu navigation and item selection"""

    def __init__(self, chat_ctx=None):
        super().__init__(
            instructions="""You help customers browse the menu and add items to their order.

Available items:
- Burger: $12
- Pizza: $15
- Salad: $10
- Fries: $5
- Drink: $3

Use the add_item tool to add items. When the customer is done ordering
and confirms their order, use complete_order to proceed to payment.""",
            chat_ctx=chat_ctx,
        )

    @function_tool
    async def add_item(
        self,
        context: RunContext[OrderData],
        item_name: Annotated[str, "Name of the menu item"],
        quantity: Annotated[int, "Quantity to add"] = 1,
    ):
        """Add an item to the order"""
        # Simplified pricing
        prices = {
            "burger": 12,
            "pizza": 15,
            "salad": 10,
            "fries": 5,
            "drink": 3,
        }

        item_lower = item_name.lower()
        if item_lower not in prices:
            raise ToolError(f"Sorry, {item_name} is not on our menu.")

        price = prices[item_lower]
        context.userdata.items.append({
            "name": item_name,
            "quantity": quantity,
            "price": price * quantity,
        })
        context.userdata.total_price += price * quantity

        return f"Added {quantity} {item_name}(s) to your order. Total: ${context.userdata.total_price:.2f}"

    @function_tool
    async def complete_order(
        self,
        context: RunContext[OrderData],
    ):
        """Complete ordering and proceed to payment"""
        if not context.userdata.items:
            raise ToolError("No items in order yet. Please add items first.")

        payment_agent = PaymentAgent(chat_ctx=self.chat_ctx)
        return payment_agent, f"Your total is ${context.userdata.total_price:.2f}. Let's complete payment."


class PaymentAgent(Agent):
    """Handles payment processing"""

    def __init__(self, chat_ctx=None):
        super().__init__(
            instructions="""You handle payment for orders.

Ask for payment method (cash or card). Once confirmed, use the
process_payment tool to complete the transaction.""",
            chat_ctx=chat_ctx,
        )

    @function_tool
    async def process_payment(
        self,
        context: RunContext[OrderData],
        payment_method: Annotated[str, "Payment method: cash or card"],
    ):
        """Process payment and confirm order"""
        context.userdata.payment_method = payment_method
        context.userdata.confirmed = True

        confirmation_agent = ConfirmationAgent(chat_ctx=self.chat_ctx)
        return confirmation_agent, "Payment processed! Preparing your confirmation."


class ConfirmationAgent(Agent):
    """Provides order confirmation"""

    def __init__(self, chat_ctx=None):
        super().__init__(
            instructions="""You provide order confirmation to customers.

Thank them, summarize their order, give an order number, and
provide an estimated time. Be warm and appreciative.""",
            chat_ctx=chat_ctx,
        )

    # No handoff tool - final agent


# Entry point
async def entrypoint(ctx: JobContext):
    session = AgentSession[OrderData](
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(model="nova-2-general"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(voice="alloy"),
        userdata=OrderData(),
    )

    await ctx.connect()

    welcome_agent = WelcomeAgent()
    await session.start(ctx.room, welcome_agent)
```

**Key Features:**
- Each agent has one clear purpose
- Linear progression through stages
- Context builds up over time
- Final agent provides closure

---

### Pattern 2: Hub and Spoke (Router)

**Structure:** Central agent routes to specialists

```
           ┌──────────────┐
           │  Specialist  │
           │   Agent A    │
           └──────────────┘
                  ▲
                  │
┌─────────┐      │      ┌──────────────┐
│  User   │────▶ Router ────▶│  Specialist  │
└─────────┘      │            │   Agent B    │
                  │            └──────────────┘
                  │
                  ▼
           ┌──────────────┐
           │  Specialist  │
           │   Agent C    │
           └──────────────┘
```

**Best for:**
- Multi-domain support systems
- Intent-based routing
- Specialized knowledge areas
- Dynamic capability selection

**Example: Customer Support Hub**

```python
from dataclasses import dataclass
from enum import Enum

class IssueCategory(Enum):
    TECHNICAL = "technical"
    BILLING = "billing"
    GENERAL = "general"
    SALES = "sales"


@dataclass
class SupportData:
    user_name: str = ""
    user_email: str = ""
    category: IssueCategory = None
    issue_description: str = ""
    resolution: str = ""


class RouterAgent(Agent):
    """Central agent that routes to specialists"""

    def __init__(self):
        super().__init__(
            instructions="""You are a customer support router.

Your job:
1. Greet the customer and get their name/email
2. Understand what they need help with
3. Route them to the right specialist:
   - Technical issues → Technical Support
   - Billing/payment → Billing Support
   - Product questions → General Support
   - Sales inquiries → Sales Team

Ask clarifying questions if the category is unclear. Once you
know where to route them, use the appropriate transfer function."""
        )

    @function_tool
    async def transfer_to_technical(
        self,
        context: RunContext[SupportData],
        issue_description: Annotated[str, "Technical issue description"],
    ):
        """Transfer to technical support specialist"""
        context.userdata.category = IssueCategory.TECHNICAL
        context.userdata.issue_description = issue_description

        tech_agent = TechnicalSupportAgent(
            user_name=context.userdata.user_name,
            chat_ctx=self.chat_ctx,
        )
        return tech_agent, "Connecting you to our technical support specialist."

    @function_tool
    async def transfer_to_billing(
        self,
        context: RunContext[SupportData],
        issue_description: Annotated[str, "Billing issue description"],
    ):
        """Transfer to billing support specialist"""
        context.userdata.category = IssueCategory.BILLING
        context.userdata.issue_description = issue_description

        billing_agent = BillingSupportAgent(
            user_name=context.userdata.user_name,
            chat_ctx=self.chat_ctx,
        )
        return billing_agent, "Connecting you to our billing department."

    @function_tool
    async def transfer_to_sales(
        self,
        context: RunContext[SupportData],
        inquiry: Annotated[str, "Sales inquiry description"],
    ):
        """Transfer to sales team"""
        context.userdata.category = IssueCategory.SALES
        context.userdata.issue_description = inquiry

        sales_agent = SalesAgent(
            user_name=context.userdata.user_name,
            chat_ctx=self.chat_ctx,
        )
        return sales_agent, "Let me connect you with our sales team."


class TechnicalSupportAgent(Agent):
    """Handles technical issues"""

    def __init__(self, user_name: str, chat_ctx=None):
        super().__init__(
            instructions=f"""You are a technical support specialist helping {user_name}.

You have access to:
- System diagnostics tools
- Account access tools
- Troubleshooting guides

Guide the user through resolving their technical issue. If you
successfully resolve it, use mark_resolved. If it requires escalation
(account access, billing, or too complex), use escalate.""",
            chat_ctx=chat_ctx,
        )
        self.user_name = user_name

    @function_tool
    async def run_diagnostics(
        self,
        context: RunContext[SupportData],
        check_type: Annotated[str, "Type of diagnostic check"],
    ):
        """Run system diagnostics"""
        # Simulated diagnostic
        return f"Diagnostics complete: {check_type} check passed"

    @function_tool
    async def mark_resolved(
        self,
        context: RunContext[SupportData],
        resolution: Annotated[str, "How the issue was resolved"],
    ):
        """Mark issue as resolved"""
        context.userdata.resolution = resolution
        # Stay with this agent, conversation can end
        return None, f"Great! I've marked your issue as resolved. Is there anything else I can help with?"

    @function_tool
    async def escalate(
        self,
        context: RunContext[SupportData],
        reason: Annotated[str, "Reason for escalation"],
    ):
        """Escalate to senior support"""
        escalation_agent = EscalationAgent(
            user_name=self.user_name,
            previous_agent="Technical Support",
            chat_ctx=self.chat_ctx,
        )
        return escalation_agent, f"Let me escalate this to our senior support team."


class BillingSupportAgent(Agent):
    """Handles billing issues"""

    def __init__(self, user_name: str, chat_ctx=None):
        super().__init__(
            instructions=f"""You are a billing support specialist helping {user_name}.

You can:
- Look up invoices
- Process refunds
- Update payment methods
- Explain charges

Help resolve billing issues. Use mark_resolved when done.""",
            chat_ctx=chat_ctx,
        )

    @function_tool
    async def lookup_invoice(
        self,
        context: RunContext[SupportData],
        invoice_id: Annotated[str, "Invoice ID"],
    ):
        """Look up invoice details"""
        return f"Invoice {invoice_id}: $100.00 - Paid on 2025-01-15"

    @function_tool
    async def mark_resolved(
        self,
        context: RunContext[SupportData],
        resolution: Annotated[str, "Resolution description"],
    ):
        """Mark billing issue as resolved"""
        context.userdata.resolution = resolution
        return None, "Your billing issue has been resolved. Anything else I can help with?"


class SalesAgent(Agent):
    """Handles sales inquiries"""

    def __init__(self, user_name: str, chat_ctx=None):
        super().__init__(
            instructions=f"""You are a sales representative helping {user_name}.

Your goal:
- Understand their needs
- Recommend appropriate solutions
- Answer product questions
- Schedule demos if interested

Be helpful and consultative, not pushy.""",
            chat_ctx=chat_ctx,
        )

    @function_tool
    async def schedule_demo(
        self,
        context: RunContext[SupportData],
        preferred_time: Annotated[str, "Preferred demo time"],
    ):
        """Schedule a product demo"""
        return f"Demo scheduled for {preferred_time}. You'll receive a confirmation email."


# Entry point
async def entrypoint(ctx: JobContext):
    session = AgentSession[SupportData](
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(model="nova-2-general"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(voice="alloy"),
        userdata=SupportData(),
    )

    await ctx.connect()

    router_agent = RouterAgent()
    await session.start(ctx.room, router_agent)
```

**Key Features:**
- Central routing logic
- Specialized agents for domains
- Easy to add new specialists
- Clear separation of concerns

---

### Pattern 3: Escalation Hierarchy

**Structure:** Agents can escalate up the chain

```
┌──────────────┐
│   Level 1    │
│   Support    │
└──────┬───────┘
       │ (Escalate if needed)
       ▼
┌──────────────┐
│   Level 2    │
│  Specialist  │
└──────┬───────┘
       │ (Escalate if needed)
       ▼
┌──────────────┐
│  Human       │
│  Operator    │
└──────────────┘
```

**Best for:**
- Support systems
- Progressive assistance
- Complexity-based routing
- Human-in-the-loop workflows

**Example: Tiered Support**

```python
@dataclass
class SupportTicket:
    user_name: str = ""
    issue: str = ""
    severity: str = "low"  # low, medium, high, critical
    attempts: int = 0
    escalation_reason: str = ""


class Tier1Agent(Agent):
    """First-line support"""

    def __init__(self):
        super().__init__(
            instructions="""You are a first-line support agent.

Handle common issues:
- Password resets
- Basic troubleshooting
- Account questions
- General information

Try to resolve issues yourself. Escalate to Tier 2 if:
- Issue is complex or technical
- User requests escalation
- You've tried 3 solutions without success
- Issue requires account access you don't have"""
        )

    @function_tool
    async def attempt_solution(
        self,
        context: RunContext[SupportTicket],
        solution_description: Annotated[str, "Solution being attempted"],
    ):
        """Attempt a solution and track attempts"""
        context.userdata.attempts += 1

        return f"Attempted solution #{context.userdata.attempts}: {solution_description}"

    @function_tool
    async def escalate_to_tier2(
        self,
        context: RunContext[SupportTicket],
        reason: Annotated[str, "Reason for escalation"],
    ):
        """Escalate to Tier 2 specialist"""
        context.userdata.escalation_reason = reason

        if context.userdata.attempts >= 3:
            context.userdata.severity = "medium"

        tier2_agent = Tier2Agent(
            issue=context.userdata.issue,
            previous_attempts=context.userdata.attempts,
            chat_ctx=self.chat_ctx,
        )

        return tier2_agent, "Let me escalate you to our specialist team."


class Tier2Agent(Agent):
    """Advanced specialist support"""

    def __init__(self, issue: str, previous_attempts: int, chat_ctx=None):
        super().__init__(
            instructions=f"""You are a Tier 2 support specialist.

Current issue: {issue}
Previous attempts: {previous_attempts}

You have advanced access and tools:
- System configuration
- Database queries
- Log analysis
- Account modifications

Resolve complex issues. Escalate to human operator only if:
- Requires policy exception
- Account security concerns
- Critical severity
- Technical issue beyond your scope""",
            chat_ctx=chat_ctx,
        )

    @function_tool
    async def check_system_logs(
        self,
        context: RunContext[SupportTicket],
        user_id: Annotated[str, "User ID to check logs for"],
    ):
        """Check system logs for errors"""
        # Simulated log check
        return "Recent logs show: Connection timeout errors on 2025-01-20"

    @function_tool
    async def apply_fix(
        self,
        context: RunContext[SupportTicket],
        fix_description: Annotated[str, "Fix being applied"],
    ):
        """Apply technical fix"""
        context.userdata.attempts += 1
        return f"Applied fix: {fix_description}. Please test to confirm resolution."

    @function_tool
    async def mark_resolved(
        self,
        context: RunContext[SupportTicket],
        resolution: Annotated[str, "Final resolution"],
    ):
        """Mark ticket as resolved"""
        return None, f"Issue resolved: {resolution}. Is there anything else I can help with?"

    @function_tool
    async def escalate_to_human(
        self,
        context: RunContext[SupportTicket],
        reason: Annotated[str, "Reason for human escalation"],
        severity: Annotated[str, "Severity: high or critical"],
    ):
        """Escalate to human operator"""
        context.userdata.escalation_reason = reason
        context.userdata.severity = severity

        human_agent = HumanHandoffAgent(chat_ctx=self.chat_ctx)
        return human_agent, "Connecting you with a human operator who can help further."


class HumanHandoffAgent(Agent):
    """Prepares for human operator handoff"""

    def __init__(self, chat_ctx=None):
        super().__init__(
            instructions="""You prepare the customer for human operator handoff.

Explain:
- A human operator will join shortly
- Estimated wait time
- What information they'll need

Keep the customer engaged while they wait. Summarize their issue
for the operator.""",
            chat_ctx=chat_ctx,
        )

    # In production, this would integrate with queue system
    # For now, it's the end of the automated flow
```

**Key Features:**
- Progressive problem solving
- Escalation based on criteria
- Context preservation at each level
- Tracking of resolution attempts

---

### Pattern 4: Bidirectional Handoff

**Structure:** Agents can pass control back and forth

```
┌──────────────┐              ┌──────────────┐
│  Main Agent  │◀────────────▶│  Specialist  │
│              │              │    Agent     │
└──────────────┘              └──────────────┘
       ▲                             │
       │                             │
       └─────────(Return)────────────┘
```

**Best for:**
- Temporary specialist consultation
- Sub-task delegation
- Information gathering
- Modular capabilities

**Example: Consultation Pattern**

```python
@dataclass
class ConsultationData:
    user_name: str = ""
    main_task: str = ""
    consultation_results: dict = field(default_factory=dict)


class MainAgent(Agent):
    """Primary agent that delegates specific tasks"""

    def __init__(self, chat_ctx=None):
        super().__init__(
            instructions="""You are the main customer service agent.

You handle the overall conversation and customer relationship.
When you need specialized help:
- Price calculations → Transfer to pricing specialist
- Inventory checks → Transfer to inventory specialist
- Technical specs → Transfer to technical specialist

They'll provide the info and return control to you.""",
            chat_ctx=chat_ctx,
        )

    @function_tool
    async def consult_pricing(
        self,
        context: RunContext[ConsultationData],
        product_ids: Annotated[str, "Comma-separated product IDs"],
    ):
        """Consult pricing specialist for quote"""
        pricing_agent = PricingSpecialist(
            return_to=self,
            chat_ctx=self.chat_ctx,
        )

        return pricing_agent, "Let me check those prices for you."

    @function_tool
    async def consult_inventory(
        self,
        context: RunContext[ConsultationData],
        product_id: Annotated[str, "Product ID to check"],
    ):
        """Consult inventory specialist"""
        inventory_agent = InventorySpecialist(
            return_to=self,
            chat_ctx=self.chat_ctx,
        )

        return inventory_agent, "Checking our inventory..."


class PricingSpecialist(Agent):
    """Specialist that handles pricing queries then returns"""

    def __init__(self, return_to: Agent, chat_ctx=None):
        super().__init__(
            instructions="""You are a pricing specialist.

Calculate prices, apply discounts, and provide quotes. Once you've
provided the pricing information, use return_to_main to go back.""",
            chat_ctx=chat_ctx,
        )
        self.return_to = return_to

    @function_tool
    async def calculate_price(
        self,
        context: RunContext[ConsultationData],
        items: Annotated[str, "Items to price"],
        quantity: Annotated[int, "Quantity"] = 1,
    ):
        """Calculate pricing for items"""
        # Pricing logic here
        total = quantity * 100  # Simplified
        context.userdata.consultation_results["pricing"] = {
            "items": items,
            "quantity": quantity,
            "total": total,
        }

        return f"Total for {quantity} {items}: ${total}"

    @function_tool
    async def return_to_main(
        self,
        context: RunContext[ConsultationData],
    ):
        """Return control to main agent"""
        return self.return_to, "I've got the pricing details. How else can I help?"


class InventorySpecialist(Agent):
    """Specialist that checks inventory then returns"""

    def __init__(self, return_to: Agent, chat_ctx=None):
        super().__init__(
            instructions="""You check inventory availability.

Look up stock levels and provide availability info. When done,
return to the main agent.""",
            chat_ctx=chat_ctx,
        )
        self.return_to = return_to

    @function_tool
    async def check_stock(
        self,
        context: RunContext[ConsultationData],
        product_id: Annotated[str, "Product ID"],
    ):
        """Check stock levels"""
        # Inventory check logic
        stock = 42  # Simplified
        context.userdata.consultation_results["inventory"] = {
            "product_id": product_id,
            "stock": stock,
            "available": stock > 0,
        }

        return f"Product {product_id}: {stock} units in stock"

    @function_tool
    async def return_to_main(
        self,
        context: RunContext[ConsultationData],
    ):
        """Return control to main agent"""
        return self.return_to, "I've checked the inventory. What else can I help with?"
```

**Key Features:**
- Main agent maintains control
- Specialists do focused tasks
- Explicit return mechanism
- Results stored in shared context

---

## Pattern Selection Guide

| Use Case | Recommended Pattern | Reason |
|----------|-------------------|--------|
| E-commerce checkout | Linear Pipeline | Clear sequential steps |
| Customer support | Hub and Spoke | Multiple issue types |
| Technical troubleshooting | Escalation Hierarchy | Progressive complexity |
| Consultation workflow | Bidirectional Handoff | Temporary specialists |
| Appointment booking | Linear Pipeline | Sequential data collection |
| Call center | Escalation Hierarchy | Human escalation needed |
| Multi-department help | Hub and Spoke | Domain specialization |
| Form filling | Linear Pipeline | Step-by-step process |

## Combining Patterns

You can combine patterns for complex workflows:

```python
# Hub + Escalation: Router that leads to tiered support
RouterAgent → TechnicalAgent → SeniorTechnical → Human

# Pipeline + Bidirectional: Main flow with consultations
WelcomeAgent → OrderAgent ⇄ PricingAgent
                         ⇄ InventoryAgent
             → PaymentAgent → ConfirmationAgent

# Hub + Bidirectional: Router with specialist consultations
RouterAgent → MainAgent ⇄ Specialist1
                        ⇄ Specialist2
```

## Best Practices Summary

### Do's
✅ Keep handoff conditions clear
✅ Preserve context at each transition
✅ Announce agent changes to users
✅ Test handoff scenarios thoroughly
✅ Log transitions for monitoring

### Don'ts
❌ Create unnecessary agents
❌ Handoff too frequently
❌ Lose critical context
❌ Use handoffs for simple branching
❌ Forget to handle edge cases

---

This guide provides patterns proven in production LiveKit deployments. Adapt them to your specific needs while maintaining clarity and user experience.
