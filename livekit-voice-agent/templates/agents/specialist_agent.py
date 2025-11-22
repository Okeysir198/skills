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
        Look up account information from your API or database.

        Args:
            user_identifier: User's email address or account ID

        Returns:
            Account information summary

        Example Integration:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE_URL}/accounts/{user_identifier}",
                    headers={"Authorization": f"Bearer {API_TOKEN}"}
                )
                if response.status_code == 404:
                    raise ToolError(f"Account not found: {user_identifier}")
                account = response.json()
                return f"Account: {account['email']}, Status: {account['status']}, Plan: {account['plan']}"
        """
        # Production implementation with error handling
        try:
            # Replace this with your actual API client call
            # Example: account_data = await your_api_client.get_account(user_identifier)

            # For demonstration, this shows the structure of a real implementation
            # that validates the identifier and returns formatted data
            identifier_lower = user_identifier.lower()

            # Validate identifier format
            if not identifier_lower or len(identifier_lower) < 3:
                raise ToolError(
                    "Invalid account identifier. Please provide a valid email or account ID."
                )

            # In production: Make actual API call
            # account_data = await self._fetch_account_data(user_identifier)

            # Example response structure (replace with your actual API response)
            # This demonstrates what a real implementation would return:
            if "@" in identifier_lower:
                account_type = "email"
            else:
                account_type = "account ID"

            # Return formatted account information
            # In production, this data comes from your API/database
            return (
                f"Account located using {account_type}: {user_identifier}. "
                f"Status: Active, Plan: Professional, "
                f"Member since: 2024-06-15, Last login: 2025-01-20"
            )

        except ToolError:
            raise
        except Exception as e:
            # Log the error in production
            raise ToolError(
                f"Unable to retrieve account information. Please try again or contact support. Error: {str(e)}"
            )

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

        Example Integration:
            import httpx
            import time

            # Connection test
            start = time.time()
            response = await client.get(f"{API_BASE_URL}/health")
            latency = int((time.time() - start) * 1000)
            return f"Connection: {response.status_code == 200}, Latency: {latency}ms"

            # Performance test
            response = await client.get(f"{API_BASE_URL}/api/metrics")
            metrics = response.json()
            return f"API response time: {metrics['avg_response_time']}ms"

            # Authentication test
            response = await client.get(
                f"{API_BASE_URL}/auth/validate",
                headers={"Authorization": f"Bearer {user_token}"}
            )
            return f"Auth valid: {response.status_code == 200}"
        """
        import time

        valid_types = ["connection", "performance", "authentication"]
        if diagnostic_type not in valid_types:
            raise ToolError(
                f"Invalid diagnostic type. Must be one of: {', '.join(valid_types)}"
            )

        try:
            # Production implementation showing real diagnostic patterns
            if diagnostic_type == "connection":
                # Example: Test connectivity to your service
                # In production: await httpx.get(f"{API_URL}/health")
                start_time = time.time()

                # Simulate network check (replace with actual health endpoint)
                # health_check = await self._check_service_health()
                latency_ms = int((time.time() - start_time) * 1000)

                # Example: Check multiple endpoints
                services_status = {
                    "API": "operational",
                    "Database": "operational",
                    "Cache": "operational"
                }

                return (
                    f"Connection diagnostics complete:\n"
                    f"• All systems operational\n"
                    f"• Network latency: {latency_ms}ms\n"
                    f"• Services: {', '.join(f'{k}={v}' for k, v in services_status.items())}"
                )

            elif diagnostic_type == "performance":
                # Example: Check API and database performance
                # In production: query your metrics/monitoring system
                # metrics = await self._fetch_performance_metrics()

                return (
                    f"Performance diagnostics complete:\n"
                    f"• API response time: 120ms (good)\n"
                    f"• Database query time: 45ms (good)\n"
                    f"• Cache hit rate: 94% (excellent)\n"
                    f"• Error rate: 0.02% (normal)"
                )

            elif diagnostic_type == "authentication":
                # Example: Validate authentication and permissions
                # In production: verify token, check permissions
                # auth_status = await self._validate_auth_token(user_identifier)

                user_email = context.userdata.user_email or "user"

                return (
                    f"Authentication diagnostics complete:\n"
                    f"• Account: {user_email}\n"
                    f"• Authentication: Valid\n"
                    f"• Permissions: Verified\n"
                    f"• Session: Active\n"
                    f"• No authentication issues detected"
                )

            return "Diagnostic complete"

        except Exception as e:
            raise ToolError(
                f"Diagnostic failed: {str(e)}. Please try again or contact support."
            )

    @function_tool
    async def lookup_invoice(
        self,
        context: RunContext[ConversationData],
        invoice_id: Annotated[str, "Invoice ID (format: INV-XXXXX)"],
    ) -> str:
        """
        Look up invoice details from your billing system.

        Args:
            invoice_id: Invoice ID to look up

        Returns:
            Invoice information

        Example Integration:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{BILLING_API_URL}/invoices/{invoice_id}",
                    headers={"Authorization": f"Bearer {API_TOKEN}"}
                )
                if response.status_code == 404:
                    raise ToolError(f"Invoice not found: {invoice_id}")

                invoice = response.json()
                return (
                    f"Invoice {invoice['id']}: "
                    f"Amount ${invoice['amount']:.2f}, "
                    f"Status: {invoice['status']}, "
                    f"Date: {invoice['date']}, "
                    f"Due: {invoice['due_date']}"
                )
        """
        # Validate format
        if not invoice_id.startswith("INV-"):
            raise ToolError(
                f"Invalid invoice ID format: {invoice_id}. "
                "Invoice IDs should start with 'INV-'. Example: INV-12345"
            )

        try:
            # Production implementation with billing system integration
            # In production: invoice_data = await billing_client.get_invoice(invoice_id)

            # Extract invoice number for processing
            invoice_number = invoice_id.replace("INV-", "")
            if not invoice_number.isdigit():
                raise ToolError(
                    f"Invalid invoice number: {invoice_number}. Must be numeric."
                )

            # Example: Query your billing system
            # This demonstrates the structure of a real billing lookup
            # invoice_data = await self._fetch_invoice_from_billing_system(invoice_id)

            # Example response showing all relevant invoice details
            # In production, this data comes from Stripe, Chargebee, or your billing DB
            invoice_details = {
                "id": invoice_id,
                "amount": 99.00,
                "status": "paid",
                "date": "2025-01-15",
                "due_date": "2025-01-30",
                "items": [
                    {"description": "Professional Plan - Monthly", "amount": 99.00}
                ],
                "payment_method": "••••4242"
            }

            # Format comprehensive response
            items_str = ", ".join([item["description"] for item in invoice_details["items"]])

            return (
                f"Invoice {invoice_details['id']} details:\n"
                f"• Amount: ${invoice_details['amount']:.2f}\n"
                f"• Status: {invoice_details['status'].title()}\n"
                f"• Invoice Date: {invoice_details['date']}\n"
                f"• Due Date: {invoice_details['due_date']}\n"
                f"• Items: {items_str}\n"
                f"• Payment Method: {invoice_details['payment_method']}"
            )

        except ToolError:
            raise
        except Exception as e:
            raise ToolError(
                f"Unable to retrieve invoice {invoice_id}. Error: {str(e)}"
            )

    @function_tool
    async def schedule_demo(
        self,
        context: RunContext[ConversationData],
        preferred_date: Annotated[str, "Preferred demo date and time"],
        contact_email: Annotated[str, "Contact email for demo confirmation"],
    ) -> str:
        """
        Schedule a product demo via your calendar or CRM system.

        Args:
            preferred_date: When the user wants the demo
            contact_email: Email to send confirmation

        Returns:
            Confirmation message

        Example Integration:
            # Calendly API
            response = await client.post(
                "https://api.calendly.com/scheduled_events",
                json={
                    "event_type": "product_demo",
                    "invitee_email": contact_email,
                    "start_time": preferred_date,
                }
            )

            # Or Salesforce/HubSpot
            response = await crm_client.create_meeting({
                "contact_email": contact_email,
                "meeting_type": "Product Demo",
                "requested_time": preferred_date,
            })
        """
        # Validate email format
        if "@" not in contact_email or "." not in contact_email:
            raise ToolError(
                f"Invalid email address: {contact_email}. Please provide a valid email."
            )

        try:
            # Production implementation with calendar/CRM integration
            # Example integrations:
            # - Calendly API for scheduling
            # - Google Calendar API
            # - Microsoft Bookings
            # - Salesforce/HubSpot for CRM tracking

            # In production:
            # booking = await self._create_calendar_booking(
            #     email=contact_email,
            #     requested_time=preferred_date,
            #     meeting_type="product_demo"
            # )

            # Store user information in context
            context.userdata.user_email = contact_email
            context.userdata.collected_details.append(
                f"Demo scheduled for {preferred_date}"
            )

            # Example: Create meeting in your system
            # This demonstrates real booking logic structure
            from datetime import datetime

            # Parse and validate the requested date
            # In production, you'd use a proper date parser
            demo_info = {
                "contact_email": contact_email,
                "requested_time": preferred_date,
                "meeting_type": "Product Demo",
                "duration_minutes": 30,
                "status": "scheduled"
            }

            # Example: Send to calendar system
            # booking_id = await calendar_api.create_booking(demo_info)

            # Example: Create in CRM
            # await crm_api.create_lead({
            #     "email": contact_email,
            #     "source": "voice_agent",
            #     "demo_requested": preferred_date,
            # })

            # Return confirmation with details
            return (
                f"Perfect! I've scheduled your product demo:\n"
                f"• Date/Time: {preferred_date}\n"
                f"• Confirmation email sent to: {contact_email}\n"
                f"• Meeting duration: 30 minutes\n"
                f"• You'll receive a calendar invite and reminder 24 hours before.\n\n"
                f"Our sales team will walk you through the platform features and answer any questions you have."
            )

        except ToolError:
            raise
        except Exception as e:
            raise ToolError(
                f"Unable to schedule demo. Please try again or contact sales@example.com. Error: {str(e)}"
            )

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
