"""
Stateful Tool Example

Demonstrates state management using RunContext.userdata.
Shows patterns for maintaining conversation state, user preferences, and session data.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from livekit.agents import Agent, JobContext, WorkerOptions, cli
from livekit.agents.llm import function_tool
from livekit.agents.voice import AgentSession, RunContext
from livekit.plugins import silero

logger = logging.getLogger("stateful-tool-example")
logger.setLevel(logging.INFO)

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env')


@dataclass
class UserProfile:
    """User profile data stored in session."""
    name: str = ""
    email: str = ""
    preferences: dict = field(default_factory=dict)
    interaction_count: int = 0

    def to_summary(self) -> str:
        """Convert profile to text summary."""
        if not self.name:
            return "No user profile set"

        summary = f"User: {self.name}"
        if self.email:
            summary += f"\nEmail: {self.email}"
        if self.preferences:
            prefs = ", ".join(f"{k}: {v}" for k, v in self.preferences.items())
            summary += f"\nPreferences: {prefs}"
        return summary


@dataclass
class ShoppingCart:
    """Shopping cart stored in session."""
    items: list[dict] = field(default_factory=list)
    total: float = 0.0

    def add_item(self, name: str, price: float, quantity: int = 1):
        """Add item to cart."""
        self.items.append({
            "name": name,
            "price": price,
            "quantity": quantity
        })
        self.total += price * quantity

    def get_summary(self) -> str:
        """Get cart summary."""
        if not self.items:
            return "Your cart is empty"

        lines = [f"Shopping Cart ({len(self.items)} items):"]
        for item in self.items:
            lines.append(f"- {item['quantity']}x {item['name']}: ${item['price'] * item['quantity']:.2f}")
        lines.append(f"Total: ${self.total:.2f}")
        return "\n".join(lines)


class StatefulAgent(Agent):
    """Agent demonstrating state management patterns."""

    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful shopping assistant that remembers user preferences.
            You can help users build a shopping cart, save preferences, and personalize their experience.
            Use the user's name naturally in conversation when you know it.""",
            llm="openai/gpt-4o-mini",
            vad=silero.VAD.load()
        )

    @function_tool
    async def save_user_profile(
        self,
        name: str | None = None,
        email: str | None = None,
        context: RunContext
    ) -> str:
        """Save or update user profile information.

        Args:
            name: User's name (optional)
            email: User's email address (optional)
            context: Runtime context
        """
        # Initialize profile if it doesn't exist
        if "profile" not in context.userdata:
            context.userdata["profile"] = UserProfile()

        profile: UserProfile = context.userdata["profile"]

        # Update fields if provided
        updated = []
        if name:
            profile.name = name
            updated.append("name")

        if email:
            profile.email = email
            updated.append("email")

        if not updated:
            return "No profile information provided to save"

        logger.info(f"Updated profile: {updated}")
        return f"I've saved your {' and '.join(updated)}. {profile.to_summary()}"

    @function_tool
    async def set_preference(
        self,
        preference_name: str,
        value: str,
        context: RunContext
    ) -> str:
        """Save a user preference.

        Args:
            preference_name: Name of the preference (e.g., "favorite_color", "theme")
            value: The preference value
            context: Runtime context
        """
        # Initialize profile if needed
        if "profile" not in context.userdata:
            context.userdata["profile"] = UserProfile()

        profile: UserProfile = context.userdata["profile"]
        profile.preferences[preference_name] = value

        logger.info(f"Saved preference: {preference_name} = {value}")
        return f"I've saved your preference: {preference_name} = {value}"

    @function_tool
    async def get_profile(self, context: RunContext) -> str:
        """Retrieve the user's profile and preferences.

        Args:
            context: Runtime context
        """
        profile = context.userdata.get("profile")

        if not profile:
            return "I don't have any profile information for you yet. Would you like to share your name?"

        return profile.to_summary()

    @function_tool
    async def add_to_cart(
        self,
        item_name: str,
        price: float,
        quantity: int = 1,
        context: RunContext
    ) -> str:
        """Add an item to the shopping cart.

        Args:
            item_name: Name of the item
            price: Price per item
            quantity: Number of items to add (default: 1)
            context: Runtime context
        """
        # Initialize cart if needed
        if "cart" not in context.userdata:
            context.userdata["cart"] = ShoppingCart()

        cart: ShoppingCart = context.userdata["cart"]
        cart.add_item(item_name, price, quantity)

        logger.info(f"Added to cart: {quantity}x {item_name} @ ${price}")
        return f"Added {quantity}x {item_name} to your cart. Cart total: ${cart.total:.2f}"

    @function_tool
    async def view_cart(self, context: RunContext) -> str:
        """View the current shopping cart.

        Args:
            context: Runtime context
        """
        cart = context.userdata.get("cart")

        if not cart:
            return "Your cart is empty. Would you like to add some items?"

        return cart.get_summary()

    @function_tool
    async def clear_cart(self, context: RunContext) -> str:
        """Clear all items from the shopping cart.

        Args:
            context: Runtime context
        """
        if "cart" in context.userdata:
            del context.userdata["cart"]
            logger.info("Cart cleared")
            return "I've cleared your shopping cart"
        else:
            return "Your cart is already empty"

    @function_tool
    async def track_interaction(
        self,
        interaction_type: Literal["question", "purchase", "support"],
        context: RunContext
    ) -> str:
        """Track user interaction for analytics.

        Args:
            interaction_type: Type of interaction
            context: Runtime context
        """
        # Initialize profile if needed
        if "profile" not in context.userdata:
            context.userdata["profile"] = UserProfile()

        profile: UserProfile = context.userdata["profile"]
        profile.interaction_count += 1

        # Store interaction history
        if "interactions" not in context.userdata:
            context.userdata["interactions"] = []

        context.userdata["interactions"].append({
            "type": interaction_type,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"Tracked interaction: {interaction_type} (count: {profile.interaction_count})")
        return f"Thanks for your {interaction_type}! This is interaction #{profile.interaction_count}"

    @function_tool
    async def get_personalized_recommendation(self, context: RunContext) -> str:
        """Get personalized recommendations based on user preferences and history.

        Args:
            context: Runtime context
        """
        profile = context.userdata.get("profile")
        cart = context.userdata.get("cart")
        interactions = context.userdata.get("interactions", [])

        recommendations = []

        # Use profile for personalization
        if profile and profile.name:
            recommendations.append(f"Hi {profile.name}!")

        # Check preferences
        if profile and "favorite_category" in profile.preferences:
            category = profile.preferences["favorite_category"]
            recommendations.append(f"Based on your interest in {category}, you might like...")

        # Check cart
        if cart and cart.items:
            recommendations.append(f"Since you have {len(cart.items)} items in your cart, consider adding...")

        # Check interaction count
        if profile and profile.interaction_count > 5:
            recommendations.append("As a frequent user, we have special offers for you...")

        if not recommendations:
            return "I'd love to make recommendations! Tell me about your preferences first."

        return "\n".join(recommendations)

    @function_tool
    async def save_session_note(
        self,
        note: str,
        category: str,
        context: RunContext
    ) -> str:
        """Save a note or reminder for this session.

        Args:
            note: The note content
            category: Category for the note
            context: Runtime context
        """
        if "notes" not in context.userdata:
            context.userdata["notes"] = []

        context.userdata["notes"].append({
            "note": note,
            "category": category,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"Saved note in category '{category}'")
        return f"I've saved that note under {category}"

    @function_tool
    async def get_session_summary(self, context: RunContext) -> str:
        """Get a summary of the current session.

        Args:
            context: Runtime context
        """
        profile = context.userdata.get("profile")
        cart = context.userdata.get("cart")
        interactions = context.userdata.get("interactions", [])
        notes = context.userdata.get("notes", [])

        summary_parts = ["Session Summary:"]

        if profile:
            summary_parts.append(f"\n{profile.to_summary()}")

        if cart:
            summary_parts.append(f"\n{cart.get_summary()}")

        if interactions:
            summary_parts.append(f"\nInteractions: {len(interactions)}")

        if notes:
            summary_parts.append(f"\nNotes saved: {len(notes)}")

        return "\n".join(summary_parts)

    async def on_enter(self):
        """Called when the agent enters the session."""
        # Initialize session metadata
        if "session_start" not in self.session.userdata:
            self.session.userdata["session_start"] = datetime.now().isoformat()

        self.session.generate_reply()


async def entrypoint(ctx: JobContext):
    """Entry point for the agent."""
    session = AgentSession()
    await session.start(agent=StatefulAgent(), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
