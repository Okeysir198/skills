"""
Agent Handoff Tool Example

Demonstrates multi-agent coordination patterns with state transfer.
Shows how to build workflows with multiple specialized agents that hand off to each other.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from livekit.agents import Agent, JobContext, WorkerOptions, cli
from livekit.agents.llm import function_tool
from livekit.agents.voice import AgentSession, RunContext
from livekit.plugins import silero

logger = logging.getLogger("agent-handoff-example")
logger.setLevel(logging.INFO)

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env')


@dataclass
class CustomerData:
    """Shared customer data across agents."""
    name: str = ""
    email: str = ""
    issue_type: str = ""
    order_id: str = ""
    priority: str = "normal"

    def to_context_summary(self) -> str:
        """Create a summary for agent context."""
        parts = []
        if self.name:
            parts.append(f"Customer: {self.name}")
        if self.email:
            parts.append(f"Email: {self.email}")
        if self.issue_type:
            parts.append(f"Issue: {self.issue_type}")
        if self.order_id:
            parts.append(f"Order ID: {self.order_id}")
        parts.append(f"Priority: {self.priority}")
        return "\n".join(parts)


class GreeterAgent(Agent):
    """Initial agent that greets users and routes to specialists."""

    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a friendly greeter for a customer service system.
            Welcome users warmly and ask how you can help them today.
            Based on their needs, route them to the appropriate specialist:
            - Sales inquiries -> use transfer_to_sales
            - Technical issues -> use transfer_to_support
            - Order questions -> use transfer_to_orders

            Gather the customer's name if possible before transferring.""",
            llm="openai/gpt-4o-mini",
            vad=silero.VAD.load()
        )

    @function_tool
    async def collect_customer_info(
        self,
        name: str | None = None,
        email: str | None = None,
        context: RunContext
    ) -> str:
        """Collect customer information before routing.

        Args:
            name: Customer's name
            email: Customer's email
            context: Runtime context
        """
        # Initialize customer data if needed
        if "customer" not in context.userdata:
            context.userdata["customer"] = CustomerData()

        customer: CustomerData = context.userdata["customer"]

        if name:
            customer.name = name
        if email:
            customer.email = email

        logger.info(f"Collected customer info: name={name}, email={email}")
        return f"Thanks! I have your information."

    @function_tool
    async def transfer_to_sales(self, context: RunContext):
        """Transfer to sales specialist.

        Use when customer wants to:
        - Make a purchase
        - Upgrade their plan
        - Learn about pricing

        Args:
            context: Runtime context
        """
        logger.info("Transferring to sales agent")

        customer = context.userdata.get("customer", CustomerData())
        customer.issue_type = "sales"

        sales_agent = SalesAgent(customer_context=customer.to_context_summary())
        return sales_agent, "Let me connect you with our sales team who can help you with that."

    @function_tool
    async def transfer_to_support(self, issue_description: str, context: RunContext):
        """Transfer to technical support.

        Use when customer has:
        - Technical problems
        - Bug reports
        - Questions about how to use features

        Args:
            issue_description: Brief description of the technical issue
            context: Runtime context
        """
        logger.info(f"Transferring to support: {issue_description}")

        customer = context.userdata.get("customer", CustomerData())
        customer.issue_type = f"technical: {issue_description}"

        support_agent = SupportAgent(customer_context=customer.to_context_summary())
        return support_agent, "I'll connect you with our technical support team right away."

    @function_tool
    async def transfer_to_orders(self, order_id: str, context: RunContext):
        """Transfer to order specialist.

        Use when customer asks about:
        - Order status
        - Shipping information
        - Returns or refunds

        Args:
            order_id: The order ID if known
            context: Runtime context
        """
        logger.info(f"Transferring to orders: {order_id}")

        customer = context.userdata.get("customer", CustomerData())
        customer.issue_type = "order"
        customer.order_id = order_id

        orders_agent = OrdersAgent(customer_context=customer.to_context_summary())
        return orders_agent, "Let me get you to our orders team who can look that up."

    async def on_enter(self):
        """Initialize session when agent enters."""
        self.session.generate_reply()


class SalesAgent(Agent):
    """Specialized agent for sales inquiries."""

    def __init__(self, customer_context: str = "") -> None:
        super().__init__(
            instructions=f"""You are a sales specialist.
            Help customers with purchases, plan upgrades, and pricing questions.
            Be helpful and informative, but not pushy.

            Customer context:
            {customer_context}

            You can complete purchases, provide quotes, and answer pricing questions.""",
            llm="openai/gpt-4o-mini",
            vad=silero.VAD.load()
        )

    @function_tool
    async def provide_quote(self, product: str, quantity: int = 1) -> str:
        """Provide a price quote for a product.

        Args:
            product: Product name
            quantity: Quantity requested
        """
        # In production, this would query your pricing system
        base_price = 99.00
        total = base_price * quantity
        discount = 0.1 if quantity >= 10 else 0

        logger.info(f"Generated quote: {quantity}x {product} = ${total}")

        if discount > 0:
            total_after_discount = total * (1 - discount)
            return f"Quote for {quantity}x {product}: ${total:.2f} (10% bulk discount: ${total_after_discount:.2f})"

        return f"Quote for {quantity}x {product}: ${total:.2f}"

    @function_tool
    async def complete_purchase(
        self,
        product: str,
        quantity: int,
        context: RunContext
    ) -> str:
        """Complete a purchase (would process payment in production).

        Args:
            product: Product being purchased
            quantity: Quantity
            context: Runtime context
        """
        customer = context.userdata.get("customer", CustomerData())

        # In production: process payment, create order, etc.
        order_id = f"ORD-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        logger.info(f"Purchase completed: {quantity}x {product}, order {order_id}")

        return f"Purchase complete! Order {order_id} for {quantity}x {product}. You'll receive a confirmation email at {customer.email or 'your email address'}."


class SupportAgent(Agent):
    """Specialized agent for technical support."""

    def __init__(self, customer_context: str = "") -> None:
        super().__init__(
            instructions=f"""You are a technical support specialist.
            Help customers troubleshoot issues and answer technical questions.
            Be patient and thorough. Escalate complex issues to supervisor if needed.

            Customer context:
            {customer_context}""",
            llm="openai/gpt-4o-mini",
            vad=silero.VAD.load()
        )

    @function_tool
    async def run_diagnostics(self, issue_description: str) -> str:
        """Run system diagnostics for the reported issue.

        Args:
            issue_description: Description of the issue
        """
        # In production: run actual diagnostics
        logger.info(f"Running diagnostics for: {issue_description}")

        return f"Diagnostics complete for '{issue_description}'. System status: Normal. Recommended action: Clear cache and restart."

    @function_tool
    async def escalate_to_supervisor(self, reason: str, context: RunContext):
        """Escalate complex issues to supervisor.

        Args:
            reason: Why this needs supervisor attention
            context: Runtime context
        """
        logger.info(f"Escalating to supervisor: {reason}")

        customer = context.userdata.get("customer", CustomerData())
        customer.priority = "high"
        customer.issue_type = f"{customer.issue_type} (escalated: {reason})"

        supervisor = SupervisorAgent(customer_context=customer.to_context_summary())
        return supervisor, "Let me connect you with my supervisor who can better assist with this."


class SupervisorAgent(Agent):
    """Supervisor with elevated permissions."""

    def __init__(self, customer_context: str = "") -> None:
        super().__init__(
            instructions=f"""You are a supervisor handling escalated cases.
            You have authority to approve refunds, make exceptions, and resolve complex issues.
            Be empathetic and solution-oriented.

            Customer context:
            {customer_context}""",
            llm="openai/gpt-4o-mini",
            vad=silero.VAD.load()
        )

    @function_tool
    async def approve_refund(self, amount: float, reason: str) -> str:
        """Approve a refund (supervisor-only action).

        Args:
            amount: Refund amount
            reason: Reason for refund
        """
        # In production: process refund
        logger.info(f"Supervisor approved refund: ${amount} ({reason})")

        return f"I've approved a refund of ${amount:.2f}. It will be processed within 3-5 business days."


class OrdersAgent(Agent):
    """Specialized agent for order-related inquiries."""

    def __init__(self, customer_context: str = "") -> None:
        super().__init__(
            instructions=f"""You are an order specialist.
            Help customers check order status, tracking info, and handle returns.

            Customer context:
            {customer_context}""",
            llm="openai/gpt-4o-mini",
            vad=silero.VAD.load()
        )

    @function_tool
    async def check_order_status(self, order_id: str) -> str:
        """Check the status of an order.

        Args:
            order_id: Order ID to look up
        """
        # In production: query order database
        logger.info(f"Checking status for order: {order_id}")

        return f"Order {order_id} is currently in transit. Expected delivery: 2 business days. Tracking: TRK123456789"

    @function_tool
    async def initiate_return(self, order_id: str, reason: str) -> str:
        """Start a return process.

        Args:
            order_id: Order to return
            reason: Reason for return
        """
        # In production: create return authorization
        return_id = f"RET-{datetime.now().strftime('%Y%m%d')}"

        logger.info(f"Initiated return {return_id} for order {order_id}: {reason}")

        return f"Return initiated (ID: {return_id}). You'll receive a prepaid shipping label by email within 1 hour."


async def entrypoint(ctx: JobContext):
    """Entry point for the agent system."""
    session = AgentSession()
    # Start with the greeter agent
    await session.start(agent=GreeterAgent(), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
