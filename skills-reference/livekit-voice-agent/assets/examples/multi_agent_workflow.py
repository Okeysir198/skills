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
import os
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
        logger.info(f"{self.__class__.__name__} entered session")

        # Generate greeting
        await session.generate_reply()


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
        return user_data.agents['support'], "Let me connect you with our technical support team."

    @function_tool
    async def transfer_to_sales(self, context: RunContext):
        """Transfer to sales department."""
        user_data = context.userdata
        user_data.request_type = "sales"
        return user_data.agents['sales'], "Connecting you with our sales team."

    @function_tool
    async def transfer_to_billing(self, context: RunContext):
        """Transfer to billing department."""
        user_data = context.userdata
        user_data.request_type = "billing"
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

        try:
            # Real implementation would call your ticketing system API
            # Examples: Zendesk, Jira, ServiceNow, Freshdesk, etc.

            ticketing_api_url = os.getenv("TICKETING_API_URL")
            ticketing_api_key = os.getenv("TICKETING_API_KEY")

            if not ticketing_api_url:
                # If not configured, store the info and notify user
                ticket_id = f"REF-{id(user_data):06d}"  # Temporary reference
                return (
                    {"ticket_id": ticket_id, "status": "pending"},
                    f"I've recorded your issue under reference {ticket_id}. Our team will create a formal ticket and contact you within 24 hours."
                )

            # Real API call example (replace with your actual ticketing system)
            # import httpx
            # async with httpx.AsyncClient() as client:
            #     response = await client.post(
            #         f"{ticketing_api_url}/tickets",
            #         json={
            #             "title": f"Issue with {product_model}",
            #             "description": issue_description,
            #             "error_message": error_message,
            #             "customer_email": user_data.email,
            #             "customer_phone": user_data.phone,
            #             "priority": "medium"
            #         },
            #         headers={"Authorization": f"Bearer {ticketing_api_key}"}
            #     )
            #     ticket = response.json()
            #     ticket_id = ticket["id"]

            # For demonstration, provide guidance
            ticket_id = f"REF-{id(user_data):06d}"
            user_data.ticket_id = ticket_id
            user_data.ticket_status = "created"

            return (
                {"ticket_id": ticket_id, "status": "created"},
                f"I've created ticket {ticket_id} for your issue with {product_model}. Our team will investigate and follow up within 24 hours."
            )

        except Exception as e:
            logger.error(f"Ticket creation failed: {e}")
            return None, "I'm having trouble creating a ticket right now, but I've recorded your issue. Our team will reach out to you soon."

    @function_tool
    async def escalate_to_specialist(self, context: RunContext):
        """Escalate to a senior specialist."""
        user_data = context.userdata
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

        # Real implementation would query your product database or API
        # This is a placeholder showing the pattern - replace with your actual implementation
        # Example: query a database, CRM, or product recommendation engine
        try:
            # For demonstration: return helpful guidance when not configured
            api_url = os.getenv("PRODUCT_API_URL")
            if not api_url:
                return None, "I don't have access to product information right now. Let me transfer you to someone who can help."

            # Real API call would go here
            # For now, provide a helpful response
            summary = f"I understand you're looking for products related to '{requirements}'"
            if budget != "not specified":
                summary += f" within a budget of {budget}"
            summary += ". Let me transfer you to billing to complete your purchase."

            return {"requirements": requirements, "budget": budget}, summary

        except Exception as e:
            logger.error(f"Product search error: {e}")
            return None, "I'm having trouble accessing product information. Let me transfer you to someone who can assist."

    @function_tool
    async def transfer_to_billing(self, context: RunContext):
        """Transfer to billing to complete purchase."""
        user_data = context.userdata
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

        try:
            # Real implementation would query your CRM, billing system, or database
            # This is a placeholder showing the pattern - replace with your actual implementation

            # Check for database configuration
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                return None, "I'm unable to access account information right now. For security reasons, please verify your identity with our billing team."

            # Real database query would go here
            # Example: query customer database, Stripe, or billing system
            # account = await database.query("SELECT * FROM accounts WHERE email = ? OR phone = ?", account_identifier)

            # For now, provide secure handling
            user_data = context.userdata
            user_data.phone = account_identifier if "@" not in account_identifier else user_data.phone
            user_data.email = account_identifier if "@" in account_identifier else user_data.email

            return None, f"For security reasons, I've noted your account identifier. Our billing team will look up your account details when we transfer you."

        except Exception as e:
            logger.error(f"Account lookup error: {e}")
            return None, "I'm having trouble accessing account information. Please hold while I transfer you to our billing team."


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
    await session.start(room=ctx.room, agent=greeter)

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
