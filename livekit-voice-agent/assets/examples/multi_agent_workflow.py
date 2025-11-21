"""
Multi-Agent Workflow - Customer service with agent handoffs.

Demonstrates:
- Multiple specialized agents
- Agent-to-agent handoffs
- Shared user data across agents
- Context preservation during transfers
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, function_tool, RunContext
from livekit.plugins import deepgram, openai, cartesia, silero, turn_detector

load_dotenv(dotenv_path=".env.local")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class UserData:
    """Shared data across all agents."""
    # Customer information
    name: str = ""
    email: str = ""
    phone: str = ""

    # Service request
    request_type: str = ""  # "support", "sales", "billing"
    issue_description: str = ""

    # Support ticket
    ticket_id: str = ""
    ticket_status: str = ""

    # Navigation
    agents: dict = field(default_factory=dict)
    prev_agent: Optional[Agent] = None
    current_task: str = ""


class BaseAgent(Agent):
    """Base class for agents with handoff helpers."""

    async def on_enter(self, session: AgentSession):
        """Called when agent takes control."""
        context = session.context

        # Preserve context from previous agent
        if context.userdata.prev_agent:
            # Copy relevant history (last 5 messages)
            prev_history = context.userdata.prev_agent.chat_history[-5:]
            context.chat_history.extend(prev_history)

        logger.info(f"{self.__class__.__name__} entered session")

        # Generate greeting
        await session.generate_reply()

    def _create_handoff_tool(self, target_agent_name: str, message: str):
        """Helper to create a handoff function."""
        @function_tool
        async def transfer(context: RunContext):
            f"""Transfer to {target_agent_name}."""
            user_data = context.userdata
            user_data.prev_agent = context.session.current_agent
            return user_data.agents[target_agent_name], message

        return transfer


class GreeterAgent(BaseAgent):
    """Initial contact - routes to appropriate department."""

    def __init__(self):
        super().__init__(
            instructions="""You are a friendly customer service greeter.
            Ask how you can help and route to the right department:
            - Technical support for product issues
            - Sales for new purchases or questions
            - Billing for payment or account questions

            Collect the customer's name if they haven't provided it."""
        )

    @function_tool
    async def transfer_to_support(self, context: RunContext):
        """Transfer to technical support."""
        user_data = context.userdata
        user_data.request_type = "support"
        user_data.prev_agent = context.session.current_agent
        return user_data.agents['support'], "Let me connect you with our technical support team."

    @function_tool
    async def transfer_to_sales(self, context: RunContext):
        """Transfer to sales department."""
        user_data = context.userdata
        user_data.request_type = "sales"
        user_data.prev_agent = context.session.current_agent
        return user_data.agents['sales'], "Connecting you with our sales team."

    @function_tool
    async def transfer_to_billing(self, context: RunContext):
        """Transfer to billing department."""
        user_data = context.userdata
        user_data.request_type = "billing"
        user_data.prev_agent = context.session.current_agent
        return user_data.agents['billing'], "I'll transfer you to our billing department."


class SupportAgent(BaseAgent):
    """Technical support agent."""

    def __init__(self):
        super().__init__(
            instructions="""You are a technical support specialist.
            Help customers troubleshoot issues with their products.
            Collect: description of issue, product model, error messages.
            Create a support ticket when you have enough information."""
        )

    @function_tool
    async def create_support_ticket(
        self,
        context: RunContext,
        issue_description: str,
        product_model: str,
        error_message: str = "None provided"
    ):
        """Create a support ticket.

        Args:
            issue_description: Description of the problem
            product_model: Product model number
            error_message: Any error messages shown
        """
        logger.info(f"Creating support ticket: {issue_description}")

        user_data = context.userdata
        user_data.issue_description = issue_description

        # In production: Call ticketing system API
        # ticket = await ticketing_system.create(...)
        ticket_id = f"TICKET-{hash(issue_description) % 10000:04d}"

        user_data.ticket_id = ticket_id
        user_data.ticket_status = "created"

        return (
            {"ticket_id": ticket_id, "status": "created"},
            f"I've created ticket {ticket_id} for your issue. Our team will investigate and follow up within 24 hours."
        )

    @function_tool
    async def escalate_to_specialist(self, context: RunContext):
        """Escalate to a senior specialist."""
        user_data = context.userdata
        user_data.prev_agent = context.session.current_agent
        user_data.current_task = "escalated"
        return user_data.agents['specialist'], "This issue requires our senior specialist. Transferring you now."


class SalesAgent(BaseAgent):
    """Sales agent for new purchases."""

    def __init__(self):
        super().__init__(
            instructions="""You are a sales representative.
            Help customers find the right product for their needs.
            Ask about their requirements, budget, and use case.
            Provide product recommendations."""
        )

    @function_tool
    async def search_products(
        self,
        context: RunContext,
        requirements: str,
        budget: str = "not specified"
    ):
        """Search for products matching requirements."""
        logger.info(f"Searching products for: {requirements}")

        # Mock product search
        products = [
            {"name": "Product A", "price": 299, "features": "Feature 1, 2, 3"},
            {"name": "Product B", "price": 499, "features": "Feature 1, 2, 3, 4, 5"},
        ]

        summary = f"Based on your needs, I recommend: "
        summary += ", ".join([f"{p['name']} at ${p['price']}" for p in products])

        return products, summary

    @function_tool
    async def transfer_to_billing(self, context: RunContext):
        """Transfer to billing to complete purchase."""
        user_data = context.userdata
        user_data.prev_agent = context.session.current_agent
        return user_data.agents['billing'], "Let me transfer you to billing to complete your purchase."


class BillingAgent(BaseAgent):
    """Billing and payment agent."""

    def __init__(self):
        super().__init__(
            instructions="""You are a billing specialist.
            Help with payment questions, account issues, and subscriptions.
            For security, DO NOT ask for full credit card numbers in voice.
            Collect: name, email for sending secure payment links."""
        )

    @function_tool
    async def send_payment_link(
        self,
        context: RunContext,
        email: str,
        amount: float
    ):
        """Send a secure payment link to customer's email."""
        logger.info(f"Sending payment link to {email} for ${amount}")

        user_data = context.userdata
        user_data.email = email

        # In production: Generate and send secure payment link
        # payment_link = await payment_system.create_link(amount, email)
        # await email_service.send(email, payment_link)

        return (
            {"email": email, "amount": amount},
            f"I've sent a secure payment link to {email} for ${amount}. Please check your inbox."
        )

    @function_tool
    async def lookup_account(
        self,
        context: RunContext,
        account_identifier: str
    ):
        """Look up account by email or phone number."""
        logger.info(f"Looking up account: {account_identifier}")

        # Mock account lookup
        account = {
            "id": "12345",
            "balance": 129.99,
            "status": "active",
            "last_payment": "2025-01-15"
        }

        return account, f"Your account balance is ${account['balance']} and status is {account['status']}."


class SpecialistAgent(BaseAgent):
    """Senior specialist for escalated issues."""

    def __init__(self):
        super().__init__(
            instructions="""You are a senior technical specialist.
            Handle complex escalated issues with deep technical knowledge.
            Provide detailed solutions and explanations."""
        )

    @function_tool
    async def update_ticket(
        self,
        context: RunContext,
        resolution: str,
        status: str = "resolved"
    ):
        """Update the support ticket with resolution."""
        user_data = context.userdata
        ticket_id = user_data.ticket_id

        logger.info(f"Updating ticket {ticket_id}: {status}")

        user_data.ticket_status = status

        return (
            {"ticket_id": ticket_id, "status": status},
            f"I've updated ticket {ticket_id} to {status}. {resolution}"
        )


@agents.entrypoint
async def entrypoint(ctx: JobContext):
    """Multi-agent workflow entrypoint."""
    logger.info(f"Starting multi-agent workflow for room: {ctx.room.name}")

    await ctx.connect()

    # Initialize shared user data
    user_data = UserData()
    ctx.userdata = user_data

    # Create all agents
    greeter = GreeterAgent()
    support = SupportAgent()
    sales = SalesAgent()
    billing = BillingAgent()
    specialist = SpecialistAgent()

    # Register agents for handoffs
    user_data.agents = {
        'greeter': greeter,
        'support': support,
        'sales': sales,
        'billing': billing,
        'specialist': specialist,
    }

    # Initialize components (shared across all agents)
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

    # Start with greeter agent
    logger.info("Starting session with greeter agent")
    session.start(ctx.room, initial_agent=greeter)

    # Wait for session to complete
    await session.wait_for_complete()

    logger.info(f"Session completed. Final request type: {user_data.request_type}")


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
