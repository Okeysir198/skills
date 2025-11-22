# Testing Guide for LiveKit Voice Agents

Comprehensive guide for testing multi-agent voice systems with LiveKit's testing framework.

## Overview

LiveKit Agents includes native testing support that integrates with pytest. This enables you to write behavioral tests that verify your agent's:

- Expected responses and tone
- Tool usage and arguments
- Handoff logic and timing
- Error handling
- Context preservation

## Prerequisites

```bash
# Install testing dependencies
uv add --dev "pytest"
uv add --dev "pytest-asyncio"
```

## Test Structure

### Basic Test Template

```python
import pytest
from livekit.agents import AgentSession
from livekit.plugins import openai
from agents.my_agent import MyAgent
from models.shared_data import ConversationData


@pytest.mark.asyncio
async def test_agent_behavior():
    """Test basic agent behavior"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        # Start session with agent
        agent = MyAgent()
        await sess.start(agent)

        # Run a conversation turn
        result = await sess.run(user_input="Hello")

        # Make assertions
        result.expect.next_event().is_message(role="assistant")
        result.expect.contains_message("help")
```

### Test File Organization

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures
├── test_agents/
│   ├── test_intro_agent.py
│   ├── test_specialist_agent.py
│   └── test_escalation_agent.py
├── test_tools/
│   ├── test_custom_tools.py
│   └── test_handoff_tools.py
├── test_integration/
│   ├── test_handoff_flows.py
│   └── test_complete_journeys.py
└── test_error_handling/
    └── test_error_scenarios.py
```

## Testing Agent Behavior

### 1. Testing Greetings and Initialization

```python
@pytest.mark.asyncio
async def test_greeting_agent_introduces_itself():
    """Verify agent greets user appropriately"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        agent = GreetingAgent()
        await sess.start(agent)

        result = await sess.run(user_input="Hello")

        # Verify greeting
        result.expect.next_event().is_message(role="assistant")
        result.expect.contains_message("help")
        result.expect.contains_message("how can")  # "how can I help"


@pytest.mark.asyncio
async def test_agent_asks_for_name():
    """Verify agent asks for user's name"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        agent = IntroAgent()
        await sess.start(agent)

        result = await sess.run(user_input="Hi")

        # Should ask for name
        result.expect.contains_message("name")
```

### 2. Testing Tone and Style

```python
@pytest.mark.asyncio
async def test_agent_maintains_professional_tone():
    """Verify agent uses appropriate tone"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        agent = SupportAgent()
        await sess.start(agent)

        result = await sess.run(
            user_input="My account is broken and I'm very frustrated!"
        )

        # Use LLM-based evaluation for tone
        result.expect.next_event().is_message().judge(
            llm=openai.LLM(model="gpt-4o-mini"),
            expected="A professional, empathetic response that acknowledges "
            "the user's frustration and offers help"
        )
```

### 3. Testing Conversation Flow

```python
@pytest.mark.asyncio
async def test_multi_turn_conversation():
    """Test conversation across multiple turns"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        agent = IntroAgent()
        await sess.start(agent)

        # Turn 1: Greeting
        result1 = await sess.run(user_input="Hello")
        result1.expect.next_event().is_message()

        # Turn 2: Provide name
        result2 = await sess.run(user_input="My name is Alice")
        assert sess.userdata.user_name == "Alice"

        # Turn 3: State issue
        result3 = await sess.run(
            user_input="I need help with my billing"
        )
        # Should trigger handoff
        result3.expect.next_event().is_function_call(name="transfer_to_specialist")
```

## Testing Tool Usage

### 1. Testing Function Calls

```python
@pytest.mark.asyncio
async def test_agent_calls_lookup_tool():
    """Verify agent uses lookup tool correctly"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        agent = SupportAgent()
        await sess.start(agent)

        result = await sess.run(
            user_input="What's the status of order #12345?"
        )

        # Verify function was called
        function_call = result.expect.next_event().is_function_call(
            name="lookup_order_status"
        )

        # Verify arguments
        assert "12345" in str(function_call.arguments)

        # Verify output was returned
        result.expect.next_event().is_function_call_output()

        # Verify agent responds with result
        result.expect.next_event().is_message()


@pytest.mark.asyncio
async def test_tool_with_correct_parameters():
    """Test tool receives correct parameter types and values"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        agent = OrderAgent()
        await sess.start(agent)

        result = await sess.run(
            user_input="Add 3 burgers to my order"
        )

        function_call = result.expect.next_event().is_function_call(
            name="add_item"
        )

        # Parse and verify arguments
        args = function_call.arguments
        assert args.get("item_name") == "burger"
        assert args.get("quantity") == 3
```

### 2. Testing Tool Error Handling

```python
@pytest.mark.asyncio
async def test_tool_handles_invalid_input():
    """Verify agent handles tool errors gracefully"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        agent = OrderAgent()
        await sess.start(agent)

        result = await sess.run(
            user_input="I want to order a unicorn"  # Invalid item
        )

        # Should call tool
        result.expect.next_event().is_function_call(name="add_item")

        # Tool returns error
        error_output = result.expect.next_event().is_function_call_output()

        # Agent should respond gracefully
        response = result.expect.next_event().is_message()
        response.judge(
            llm=openai.LLM(model="gpt-4o-mini"),
            expected="A polite message indicating the item is not available "
            "and offering alternatives or asking what else they'd like"
        )


@pytest.mark.asyncio
async def test_tool_retries_on_failure():
    """Test agent retries or recovers from tool failures"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        agent = SupportAgent()
        await sess.start(agent)

        # Simulate API being temporarily unavailable
        result = await sess.run(
            user_input="Check my account balance"
        )

        # First attempt
        result.expect.next_event().is_function_call(name="get_balance")
        result.expect.next_event().is_function_call_output()  # Error

        # Agent should acknowledge and offer alternatives
        response = result.expect.next_event().is_message()
        response.judge(
            llm=openai.LLM(model="gpt-4o-mini"),
            expected="Acknowledge the system issue and offer to try again or "
            "provide alternative assistance"
        )
```

## Testing Handoffs

### 1. Testing Basic Handoffs

```python
@pytest.mark.asyncio
async def test_handoff_to_specialist():
    """Test agent successfully hands off to specialist"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        agent = IntroAgent()
        await sess.start(agent)

        result = await sess.run(
            user_input="Hi, I'm John and I need help with a technical issue"
        )

        # Should trigger handoff function
        result.expect.next_event().is_function_call(
            name="transfer_to_specialist"
        )

        # Verify userdata was populated
        assert sess.userdata.user_name == "John"
        assert "technical" in sess.userdata.issue_category.lower()


@pytest.mark.asyncio
async def test_handoff_preserves_context():
    """Verify context is preserved across handoff"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        agent = IntroAgent()
        await sess.start(agent)

        # Collect information
        await sess.run(user_input="My name is Alice")
        await sess.run(user_input="I have a billing question")

        # Trigger handoff
        result = await sess.run(
            user_input="Yes, please transfer me"
        )

        result.expect.next_event().is_function_call(
            name="transfer_to_specialist"
        )

        # Verify all context preserved
        assert sess.userdata.user_name == "Alice"
        assert sess.userdata.issue_category is not None
```

### 2. Testing Handoff Conditions

```python
@pytest.mark.asyncio
async def test_handoff_only_when_appropriate():
    """Verify agent doesn't handoff prematurely"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        agent = SupportAgent()
        await sess.start(agent)

        # Ask simple question
        result = await sess.run(
            user_input="What are your business hours?"
        )

        # Should NOT trigger handoff for simple question
        # Check no handoff function was called
        events = result.get_all_events()
        function_calls = [e for e in events if e.type == "function_call"]

        handoff_calls = [
            c for c in function_calls
            if "transfer" in c.name or "escalate" in c.name
        ]

        assert len(handoff_calls) == 0, "Agent should not handoff for simple queries"


@pytest.mark.asyncio
async def test_escalation_after_multiple_failures():
    """Test agent escalates after failing to resolve"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        agent = SupportAgent()
        await sess.start(agent)

        # Simulate multiple failed attempts
        sess.userdata.attempts = 3

        result = await sess.run(
            user_input="The solutions you suggested didn't work"
        )

        # Should escalate after multiple failures
        result.expect.next_event().is_function_call(name="escalate")
```

### 3. Testing Bidirectional Handoffs

```python
@pytest.mark.asyncio
async def test_return_from_specialist():
    """Test specialist can return control to main agent"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        main_agent = MainAgent()
        await sess.start(main_agent)

        # Request specialist
        result1 = await sess.run(
            user_input="Can you check pricing for product ABC?"
        )

        result1.expect.next_event().is_function_call(
            name="consult_pricing"
        )

        # Now with pricing specialist
        result2 = await sess.run(
            user_input="Yes, please quote 10 units"
        )

        result2.expect.next_event().is_function_call(
            name="calculate_price"
        )

        # Specialist completes and returns
        result3 = await sess.run(
            user_input="Thank you"
        )

        result3.expect.next_event().is_function_call(
            name="return_to_main"
        )

        # Verify back with main agent
        # Could check agent instructions or behavior
```

## Testing Error Scenarios

### 1. Testing Invalid Inputs

```python
@pytest.mark.asyncio
async def test_handles_empty_input():
    """Test agent handles empty/unclear input"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        agent = IntroAgent()
        await sess.start(agent)

        result = await sess.run(user_input="...")

        # Should ask for clarification
        response = result.expect.next_event().is_message()
        response.judge(
            llm=openai.LLM(model="gpt-4o-mini"),
            expected="A polite request for clarification or more information"
        )


@pytest.mark.asyncio
async def test_handles_out_of_scope_requests():
    """Test agent handles requests outside its scope"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        agent = TechnicalSupportAgent()
        await sess.start(agent)

        result = await sess.run(
            user_input="Can you tell me a joke?"  # Out of scope
        )

        response = result.expect.next_event().is_message()
        response.judge(
            llm=openai.LLM(model="gpt-4o-mini"),
            expected="Politely redirect to technical support topics or "
            "acknowledge the request but maintain focus on technical help"
        )
```

### 2. Testing Grounding

```python
@pytest.mark.asyncio
async def test_agent_stays_factual():
    """Verify agent doesn't hallucinate information"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        agent = SupportAgent()
        await sess.start(agent)

        result = await sess.run(
            user_input="What's the status of order #99999999?"
        )

        # Agent should call lookup tool
        result.expect.next_event().is_function_call(
            name="lookup_order_status"
        )

        # Tool returns not found
        result.expect.next_event().is_function_call_output()

        # Agent should NOT make up information
        response = result.expect.next_event().is_message()
        response.judge(
            llm=openai.LLM(model="gpt-4o-mini"),
            expected="State that the order was not found and ask to verify "
            "the order number. Should NOT make up order details or status."
        )
```

## Testing Complete Journeys

### Integration Tests

```python
@pytest.mark.asyncio
async def test_complete_support_journey():
    """Test full customer support flow from greeting to resolution"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        agent = GreetingAgent()
        await sess.start(agent)

        # Step 1: Greeting
        result1 = await sess.run(user_input="Hello")
        result1.expect.next_event().is_message()

        # Step 2: Provide info
        result2 = await sess.run(
            user_input="I'm Sarah and I'm having login issues"
        )

        # Should handoff to technical support
        result2.expect.next_event().is_function_call(
            name="transfer_to_technical"
        )

        # Step 3: Technical troubleshooting
        result3 = await sess.run(
            user_input="I get an error 'invalid password'"
        )

        # Should suggest password reset
        result3.expect.contains_message("password")
        result3.expect.contains_message("reset")

        # Step 4: Resolution
        result4 = await sess.run(
            user_input="The reset link worked, thanks!"
        )

        result4.expect.next_event().is_function_call(
            name="mark_resolved"
        )

        # Verify final state
        assert sess.userdata.user_name == "Sarah"
        assert sess.userdata.resolution != ""


@pytest.mark.asyncio
async def test_order_placement_flow():
    """Test complete order flow"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=OrderData(),
    ) as sess:
        agent = WelcomeAgent()
        await sess.start(agent)

        # Welcome and get name
        await sess.run(user_input="Hi, I'm Mike")
        assert sess.userdata.customer_name == "Mike"

        # Add items
        await sess.run(user_input="I'd like 2 burgers")
        assert len(sess.userdata.items) > 0

        await sess.run(user_input="And 1 order of fries")
        assert len(sess.userdata.items) > 1

        # Complete order
        await sess.run(user_input="That's all")
        assert sess.userdata.total_price > 0

        # Payment
        await sess.run(user_input="I'll pay with card")

        # Verify final state
        assert sess.userdata.payment_method == "card"
        assert sess.userdata.confirmed == True
```

## Fixtures and Helpers

### conftest.py

```python
import pytest
from livekit.agents import AgentSession
from livekit.plugins import openai


@pytest.fixture
def llm():
    """Provide LLM for tests"""
    return openai.LLM(model="gpt-4o-mini")


@pytest.fixture
async def session_factory(llm):
    """Factory for creating test sessions"""
    async def _create_session(userdata):
        return AgentSession(
            llm=llm,
            userdata=userdata,
        )
    return _create_session


@pytest.fixture
def mock_api_client():
    """Mock API client for tests"""
    from unittest.mock import AsyncMock, MagicMock

    client = MagicMock()
    client.get_order = AsyncMock(return_value={
        "status": "shipped",
        "tracking": "TRACK123"
    })
    client.get_balance = AsyncMock(return_value={"balance": 100.00})

    return client
```

### Test Helpers

```python
# tests/helpers.py

from typing import List
from livekit.agents import AgentSession


async def run_conversation(
    session: AgentSession,
    user_inputs: List[str]
) -> List[any]:
    """Helper to run a multi-turn conversation"""
    results = []
    for input_text in user_inputs:
        result = await session.run(user_input=input_text)
        results.append(result)
    return results


def assert_no_handoff(result):
    """Assert that no handoff occurred"""
    events = result.get_all_events()
    function_calls = [e for e in events if e.type == "function_call"]

    handoff_keywords = ["transfer", "escalate", "handoff", "return_to"]

    handoff_calls = [
        c for c in function_calls
        if any(keyword in c.name.lower() for keyword in handoff_keywords)
    ]

    assert len(handoff_calls) == 0, f"Unexpected handoff: {handoff_calls}"


def assert_context_preserved(session, expected_fields: dict):
    """Assert userdata contains expected values"""
    for field, expected_value in expected_fields.items():
        actual_value = getattr(session.userdata, field)
        assert actual_value == expected_value, \
            f"Field {field}: expected {expected_value}, got {actual_value}"
```

## Running Tests

### Basic Usage

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_agents/test_intro_agent.py

# Run specific test
uv run pytest tests/test_agents/test_intro_agent.py::test_greeting

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run only fast tests (mark with @pytest.mark.fast)
uv run pytest -m fast
```

### Test Markers

```python
# Mark expensive tests
@pytest.mark.slow
@pytest.mark.asyncio
async def test_complex_integration():
    pass

# Mark tests that require API keys
@pytest.mark.requires_api
@pytest.mark.asyncio
async def test_with_external_api():
    pass

# Run with: pytest -m "not slow"
```

## Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: uv sync

      - name: Run tests
        run: uv run pytest -v
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

## Best Practices

### Test Organization

✅ **DO:**
- Group related tests in classes
- Use descriptive test names
- Test one behavior per test
- Use fixtures for common setup
- Mock external dependencies

❌ **DON'T:**
- Test multiple unrelated things
- Depend on test execution order
- Leave hard-coded API keys
- Skip error scenarios
- Ignore flaky tests

### Coverage Goals

Aim for:
- **90%+ code coverage** for core agent logic
- **100% coverage** for handoff functions
- **100% coverage** for custom tools
- **Error paths tested** for all tools

### Performance Testing

```python
import time

@pytest.mark.asyncio
async def test_response_latency():
    """Verify agent responds quickly"""
    async with AgentSession(...) as sess:
        agent = MyAgent()
        await sess.start(agent)

        start = time.time()
        result = await sess.run(user_input="Hello")
        duration = time.time() - start

        # Should respond in under 2 seconds
        assert duration < 2.0, f"Response took {duration}s"
```

---

## Summary Checklist

Before deploying:

- [ ] All agents have greeting tests
- [ ] All tools have usage tests
- [ ] All handoffs have integration tests
- [ ] Error scenarios covered
- [ ] Context preservation verified
- [ ] LLM-based evaluations for tone/quality
- [ ] Performance benchmarks established
- [ ] CI/CD pipeline configured
- [ ] Coverage reports reviewed
- [ ] Flaky tests investigated and fixed

---

This testing guide ensures your LiveKit voice agents are reliable, maintainable, and production-ready.
