"""
Intro Agent - Initial conversation agent

This agent greets users, collects basic information, and routes them
to specialist agents based on their needs.
"""

from typing import Annotated
from livekit.agents import Agent, RunContext
from livekit.agents.llm import function_tool, ToolError

# Import your data models
from models.shared_data import ConversationData

# Import the next agent in your workflow
from agents.specialist_agent import SpecialistAgent


class IntroAgent(Agent):
    """
    Initial agent that greets users and collects basic information.

    Responsibilities:
    - Welcome the user
    - Ask for their name
    - Understand their need or issue
    - Transfer to appropriate specialist agent
    """

    def __init__(self):
        super().__init__(
            instructions="""You are a friendly customer service agent.

Your role:
1. Greet the user warmly
2. Ask for their name
3. Ask what they need help with
4. Gather enough information to route them correctly
5. Transfer to a specialist agent when ready

Guidelines:
- Be conversational and friendly
- Keep questions brief and natural
- Don't overwhelm with too many questions at once
- Transfer as soon as you understand their need
- Announce the transfer clearly

When you have the user's name and understand their issue category,
immediately use the transfer_to_specialist function."""
        )

    @function_tool
    async def transfer_to_specialist(
        self,
        context: RunContext[ConversationData],
        user_name: Annotated[str, "The user's name"],
        issue_category: Annotated[
            str,
            "Category of the issue: technical, billing, general, or sales"
        ],
        issue_description: Annotated[str, "Brief description of what the user needs help with"],
    ):
        """
        Transfer the conversation to a specialist agent.

        Call this function when you have:
        - The user's name
        - Understanding of their issue category
        - Basic description of their need

        Args:
            user_name: The user's name as they provided it
            issue_category: One of: technical, billing, general, sales
            issue_description: 1-2 sentence summary of their issue

        Returns:
            Tuple of (new_agent, transition_message)
        """
        # Validate category
        valid_categories = ["technical", "billing", "general", "sales"]
        if issue_category.lower() not in valid_categories:
            raise ToolError(
                f"Invalid category '{issue_category}'. "
                f"Must be one of: {', '.join(valid_categories)}"
            )

        # Store information in shared context
        context.userdata.user_name = user_name
        context.userdata.issue_category = issue_category.lower()
        context.userdata.collected_details.append(issue_description)

        # Create the specialist agent
        # Pass chat_ctx to preserve conversation history
        specialist = SpecialistAgent(
            category=issue_category.lower(),
            chat_ctx=self.chat_ctx,
        )

        # Return (agent, transition_message)
        return (
            specialist,
            f"Thanks {user_name}! Let me connect you with our {issue_category} specialist."
        )
