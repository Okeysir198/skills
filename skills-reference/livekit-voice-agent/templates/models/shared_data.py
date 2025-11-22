"""
Shared Data Models

These dataclasses hold information that persists across agent handoffs.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ConversationData:
    """
    Shared context that persists across all agents in a session.

    This data is accessible to all agents and maintains state as
    conversations are handed off between agents.

    Customize this class for your specific use case by adding
    relevant fields.
    """

    # User information
    user_name: str = ""
    user_email: str = ""
    contact_info: str = ""
    account_info: str = ""

    # Issue tracking
    issue_category: str = ""  # technical, billing, general, sales
    collected_details: List[str] = field(default_factory=list)

    # Resolution tracking
    issue_resolved: bool = False
    resolution_summary: str = ""

    # Escalation tracking
    escalation_needed: bool = False
    escalation_reason: str = ""
    priority_level: str = "normal"  # normal, high, urgent

    # Handoff tracking
    human_handoff_completed: bool = False
    previous_agents: List[str] = field(default_factory=list)

    def is_complete(self) -> bool:
        """
        Check if required information has been collected.

        Returns:
            True if all required fields are populated
        """
        return bool(
            self.user_name
            and self.issue_category
        )

    def get_summary(self) -> str:
        """
        Get a human-readable summary of the conversation state.

        Returns:
            Formatted summary string
        """
        lines = [
            f"User: {self.user_name}",
            f"Category: {self.issue_category}",
        ]

        if self.user_email:
            lines.append(f"Email: {self.user_email}")

        if self.collected_details:
            details = "\n  - ".join(self.collected_details)
            lines.append(f"Details:\n  - {details}")

        if self.issue_resolved:
            lines.append(f"Resolution: {self.resolution_summary}")

        if self.escalation_needed:
            lines.append(f"Escalation: {self.escalation_reason}")

        return "\n".join(lines)


# Example: Specialized dataclass for order taking
@dataclass
class OrderData:
    """
    Example dataclass for restaurant ordering or e-commerce.

    Use this as a template for domain-specific shared data.
    """

    # Customer info
    customer_name: str = ""
    customer_phone: str = ""
    customer_email: str = ""

    # Order details
    items: List[dict] = field(default_factory=list)
    special_instructions: str = ""
    total_price: float = 0.0

    # Payment and delivery
    payment_method: str = ""  # cash, card, etc.
    delivery_address: str = ""
    delivery_time: str = ""

    # Status
    order_confirmed: bool = False
    order_number: str = ""

    def add_item(self, name: str, quantity: int, price: float):
        """Add an item to the order"""
        self.items.append({
            "name": name,
            "quantity": quantity,
            "price": price,
            "total": price * quantity
        })
        self.total_price += price * quantity

    def get_order_summary(self) -> str:
        """Get a formatted order summary"""
        if not self.items:
            return "No items in order"

        lines = [f"Order for {self.customer_name}:"]
        for item in self.items:
            lines.append(
                f"  - {item['quantity']}x {item['name']} "
                f"(${item['total']:.2f})"
            )

        lines.append(f"\nTotal: ${self.total_price:.2f}")

        if self.special_instructions:
            lines.append(f"Special instructions: {self.special_instructions}")

        return "\n".join(lines)


# Example: Support ticket dataclass
@dataclass
class SupportTicket:
    """
    Example dataclass for support ticket tracking.

    Use this pattern for customer support systems.
    """

    # Ticket info
    ticket_id: str = ""
    created_at: str = ""
    status: str = "open"  # open, in_progress, resolved, escalated

    # User info
    user_name: str = ""
    user_email: str = ""
    user_id: str = ""

    # Issue details
    category: str = ""  # bug, feature_request, question, complaint
    severity: str = "medium"  # low, medium, high, critical
    description: str = ""
    steps_to_reproduce: List[str] = field(default_factory=list)

    # Resolution
    attempted_solutions: List[str] = field(default_factory=list)
    resolution: str = ""
    resolved_by: str = ""  # agent name or "human"

    # Tracking
    handoff_count: int = 0
    escalation_history: List[str] = field(default_factory=list)

    def add_attempted_solution(self, solution: str):
        """Track solution attempts"""
        self.attempted_solutions.append(solution)

        # Auto-escalate after 3 failed attempts
        if len(self.attempted_solutions) >= 3:
            self.severity = "high"

    def escalate(self, reason: str):
        """Record an escalation"""
        self.handoff_count += 1
        self.escalation_history.append(reason)
        self.status = "escalated"
