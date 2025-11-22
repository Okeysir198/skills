"""
Escalation Agent - Prepares for human operator handoff

This agent manages the transition from automated agent to human operator.
"""

from typing import Annotated
from livekit.agents import Agent, RunContext
from livekit.agents.llm import function_tool

from models.shared_data import ConversationData


class EscalationAgent(Agent):
    """
    Escalation agent that prepares the user for human operator handoff.

    Responsibilities:
    - Explain the handoff process
    - Provide wait time estimate
    - Keep user engaged while waiting
    - Summarize issue for human operator
    - Collect any final details needed
    """

    def __init__(self, previous_category: str = "general", chat_ctx=None):
        """
        Initialize the escalation agent.

        Args:
            previous_category: Category of the previous specialist agent
            chat_ctx: Chat history from previous agent
        """
        self.previous_category = previous_category

        super().__init__(
            instructions=f"""You are preparing the customer for handoff to a human operator.

Your role:
1. Acknowledge that their issue requires human assistance
2. Explain that a human operator will join shortly
3. Provide estimated wait time (typically 2-3 minutes)
4. Keep the customer engaged and reassured while they wait
5. Collect any additional information that would help the operator

Be empathetic and professional. Let them know their previous conversation
will be available to the operator, so they won't need to repeat everything.

If the user decides they want to try automated help again, you can use
the return_to_automated function.

When ready to notify the user that the operator is joining, use notify_operator_joining.

Note: In production, your queue system triggers the actual operator joining based on
availability, priority, and wait times. This agent manages the user experience during
that transition.""",
            chat_ctx=chat_ctx,
        )

    @function_tool
    async def collect_additional_info(
        self,
        context: RunContext[ConversationData],
        info_type: Annotated[str, "Type of information: contact, account, or priority"],
        value: Annotated[str, "The information value"],
    ) -> str:
        """
        Collect additional information to help the human operator.

        Args:
            info_type: What type of information this is
            value: The actual information

        Returns:
            Confirmation message
        """
        # Store in context for the human operator
        if info_type == "contact":
            context.userdata.contact_info = value
        elif info_type == "account":
            context.userdata.account_info = value
        elif info_type == "priority":
            context.userdata.priority_level = value

        context.userdata.collected_details.append(f"{info_type}: {value}")

        return f"Thank you, I've noted that information for the operator."

    @function_tool
    async def return_to_automated(
        self,
        context: RunContext[ConversationData],
        reason: Annotated[str, "Why user wants to return to automated help"],
    ) -> tuple:
        """
        Return to automated specialist agent if user changes their mind.

        Use this if the user decides they want to try the automated
        agent again rather than wait for a human.

        Args:
            reason: Why they want to return to automated help

        Returns:
            Tuple of (specialist_agent, transition_message)
        """
        from agents.specialist_agent import SpecialistAgent

        # Clear escalation flag
        context.userdata.escalation_needed = False

        # Return to specialist
        specialist = SpecialistAgent(
            category=self.previous_category,
            chat_ctx=self.chat_ctx,
        )

        return (
            specialist,
            "No problem! Let me help you with that right now."
        )

    @function_tool
    async def notify_operator_joining(
        self,
        context: RunContext[ConversationData],
    ) -> str:
        """
        Notify the user that a human operator is joining the conversation.

        Returns:
            Message to user

        Production Integration:
            This function is typically triggered by your queue management system
            when a human operator becomes available. Example workflow:

            # 1. Queue System Integration
            from your_queue_system import OperatorQueue

            # Check operator availability
            operator = await OperatorQueue.get_next_available(
                category=context.userdata.issue_category,
                priority=context.userdata.priority_level
            )

            # 2. Add operator to LiveKit room
            from livekit import api

            room_service = api.RoomServiceClient()
            await room_service.update_participant(
                room=context.room.name,
                identity=operator.identity,
                # Configure operator permissions
            )

            # 3. Send context to operator dashboard
            await operator_dashboard.send_context({
                "user_name": context.userdata.user_name,
                "issue_category": context.userdata.issue_category,
                "escalation_reason": context.userdata.escalation_reason,
                "conversation_history": self.chat_ctx,
                "collected_details": context.userdata.collected_details,
            })

            # 4. Configure agent behavior
            # Option A: Mute the AI agent (human takes over completely)
            # Option B: Keep AI agent active for assistance
            # Option C: Remove AI agent from room
        """
        # Mark that handoff is complete
        context.userdata.human_handoff_completed = True

        # Production implementation would include:
        # 1. Notify your queue/routing system that handoff is complete
        # 2. Add human operator to the LiveKit room via API
        # 3. Send conversation context to operator dashboard
        # 4. Update metrics/analytics

        # Example: Send handoff event to your backend
        # await self._send_handoff_event(
        #     room_name=context.room.name,
        #     user_data=context.userdata,
        #     operator_needed_for=context.userdata.issue_category
        # )

        # Prepare comprehensive context for operator
        operator_context = {
            "user_name": context.userdata.user_name or "Customer",
            "user_email": context.userdata.user_email or "Not provided",
            "issue_category": context.userdata.issue_category,
            "escalation_reason": context.userdata.escalation_reason,
            "details": context.userdata.collected_details,
        }

        # Log the handoff for quality assurance
        # await self._log_handoff(operator_context)

        return (
            f"Good news! A {context.userdata.issue_category} specialist is joining now. "
            f"They have full visibility of our conversation, including:\n"
            f"• Your issue: {context.userdata.issue_category}\n"
            f"• Reason for escalation: {context.userdata.escalation_reason}\n"
            f"• All details we've discussed\n\n"
            f"You won't need to repeat anything. Thanks for your patience!"
        )

    @function_tool
    async def provide_summary(
        self,
        context: RunContext[ConversationData],
    ) -> str:
        """
        Provide a summary of the issue for the user to confirm.

        This ensures the information passed to the human operator is accurate.

        Returns:
            Summary of the issue
        """
        summary_parts = [
            f"Name: {context.userdata.user_name}",
            f"Issue Category: {context.userdata.issue_category}",
            f"Escalation Reason: {context.userdata.escalation_reason}",
        ]

        if context.userdata.collected_details:
            details = "\n- ".join(context.userdata.collected_details)
            summary_parts.append(f"Details:\n- {details}")

        summary = "\n".join(summary_parts)

        return (
            f"Here's what I'll share with the operator:\n\n{summary}\n\n"
            "Is there anything else you'd like me to add?"
        )
