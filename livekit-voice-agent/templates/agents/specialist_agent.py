"""
Specialist Agent - Handles specific domains or issue types

This agent has specialized knowledge and tools for a specific category.
"""

from typing import Annotated
from livekit.agents import Agent, RunContext
from livekit.agents.llm import function_tool, ToolError

from models.shared_data import ConversationData
from agents.escalation_agent import EscalationAgent


class SpecialistAgent(Agent):
    """
    Specialist agent that handles domain-specific issues.

    Responsibilities:
    - Provide expert help in their domain
    - Use specialized tools to resolve issues
    - Escalate to human operators when needed
    """

    def __init__(self, category: str, chat_ctx=None):
        """
        Initialize the specialist agent.

        Args:
            category: The specialization (technical, billing, general, sales)
            chat_ctx: Chat history from previous agent (preserves conversation)
        """
        self.category = category

        # Customize instructions based on category
        category_instructions = {
            "technical": """You are a technical support specialist.

You help users with:
- Login and authentication issues
- Technical errors and bugs
- System performance problems
- Integration questions

Use the lookup_account and run_diagnostics tools to help troubleshoot.
If you successfully resolve the issue, use mark_resolved.
If the issue is too complex or requires account-level access, use escalate_to_human.""",

            "billing": """You are a billing support specialist.

You help users with:
- Invoice questions
- Payment issues
- Subscription changes
- Refund requests

Use the lookup_invoice tool to check billing details.
When resolved, use mark_resolved.
For policy exceptions or refunds over $100, use escalate_to_human.""",

            "general": """You are a general customer service agent.

You help users with:
- General questions
- Account information
- Product information
- Policy questions

Answer questions clearly and helpfully.
When done, use mark_resolved.
For complex issues, use escalate_to_human.""",

            "sales": """You are a sales representative.

You help users with:
- Product inquiries
- Feature comparisons
- Pricing questions
- Demo scheduling

Be consultative and helpful, not pushy.
Use schedule_demo for demo requests.
When inquiry is addressed, use mark_resolved.""",
        }

        instructions = category_instructions.get(
            category,
            "You are a customer service specialist. Help the user with their issue."
        )

        super().__init__(
            instructions=instructions,
            chat_ctx=chat_ctx,  # Preserve conversation history
        )

    @function_tool
    async def lookup_account(
        self,
        context: RunContext[ConversationData],
        user_identifier: Annotated[str, "User email or account ID"],
    ) -> str:
        """
        Look up account information.

        Args:
            user_identifier: User's email address or account ID

        Returns:
            Account information summary
        """
        # In production, this would call your actual API
        # For template, return simulated data

        # Example API call:
        # account_info = await api_client.get_account(user_identifier)
        # return format_account_info(account_info)

        return f"Account found for {user_identifier}. Status: Active. Plan: Professional"

    @function_tool
    async def run_diagnostics(
        self,
        context: RunContext[ConversationData],
        diagnostic_type: Annotated[
            str,
            "Type of diagnostic: connection, performance, or authentication"
        ],
    ) -> str:
        """
        Run system diagnostics for troubleshooting.

        Args:
            diagnostic_type: Type of diagnostic to run

        Returns:
            Diagnostic results
        """
        valid_types = ["connection", "performance", "authentication"]
        if diagnostic_type not in valid_types:
            raise ToolError(
                f"Invalid diagnostic type. Must be one of: {', '.join(valid_types)}"
            )

        # In production, run actual diagnostics
        # For template, return simulated results

        results = {
            "connection": "Connection test: ✓ All systems operational. Latency: 45ms",
            "performance": "Performance check: ✓ API response time: 120ms (within normal range)",
            "authentication": "Auth check: ✓ API key is valid and has correct permissions"
        }

        return results.get(diagnostic_type, "Diagnostic complete")

    @function_tool
    async def lookup_invoice(
        self,
        context: RunContext[ConversationData],
        invoice_id: Annotated[str, "Invoice ID (format: INV-XXXXX)"],
    ) -> str:
        """
        Look up invoice details.

        Args:
            invoice_id: Invoice ID to look up

        Returns:
            Invoice information
        """
        # Validate format
        if not invoice_id.startswith("INV-"):
            raise ToolError(
                f"Invalid invoice ID format: {invoice_id}. "
                "Invoice IDs should start with 'INV-'. Example: INV-12345"
            )

        # In production, query your billing system
        # For template, return simulated data

        return f"Invoice {invoice_id}: Amount $99.00, Status: Paid, Date: 2025-01-15"

    @function_tool
    async def schedule_demo(
        self,
        context: RunContext[ConversationData],
        preferred_date: Annotated[str, "Preferred demo date and time"],
        contact_email: Annotated[str, "Contact email for demo confirmation"],
    ) -> str:
        """
        Schedule a product demo.

        Args:
            preferred_date: When the user wants the demo
            contact_email: Email to send confirmation

        Returns:
            Confirmation message
        """
        # In production, integrate with your calendar system
        # For template, return confirmation

        # Store in context for follow-up
        context.userdata.collected_details.append(
            f"Demo scheduled for {preferred_date}"
        )

        return f"Demo scheduled for {preferred_date}. Confirmation sent to {contact_email}"

    @function_tool
    async def mark_resolved(
        self,
        context: RunContext[ConversationData],
        resolution_summary: Annotated[str, "Summary of how the issue was resolved"],
    ) -> str:
        """
        Mark the issue as resolved.

        Call this when you have successfully helped the user.

        Args:
            resolution_summary: Brief summary of the resolution

        Returns:
            Confirmation message (returns None for agent to continue conversation)
        """
        # Store resolution in context
        context.userdata.issue_resolved = True
        context.userdata.resolution_summary = resolution_summary

        # Don't return a new agent - stay with current agent
        # Returning None allows conversation to continue or end naturally
        return "Issue marked as resolved. Is there anything else I can help you with?"

    @function_tool
    async def escalate_to_human(
        self,
        context: RunContext[ConversationData],
        escalation_reason: Annotated[str, "Reason for escalating to a human operator"],
    ) -> tuple:
        """
        Escalate the conversation to a human operator.

        Use this when:
        - Issue is too complex for automated resolution
        - User explicitly requests a human
        - Policy exception needed
        - Multiple resolution attempts failed
        - Account security concerns

        Args:
            escalation_reason: Why escalation is needed

        Returns:
            Tuple of (escalation_agent, transition_message)
        """
        # Store escalation details
        context.userdata.escalation_needed = True
        context.userdata.escalation_reason = escalation_reason

        # Create escalation agent
        escalation_agent = EscalationAgent(
            previous_category=self.category,
            chat_ctx=self.chat_ctx,
        )

        return (
            escalation_agent,
            "Let me connect you with a human operator who can help you further."
        )
