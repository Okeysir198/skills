# Dynamic Tool Creation

Create and modify tools at runtime to build adaptive agents that respond to changing requirements, user permissions, or application state.

## Table of Contents

- [Why Dynamic Tools](#why-dynamic-tools)
- [Three Approaches](#three-approaches)
- [Creating Tools at Runtime](#creating-tools-at-runtime)
- [Updating Agent Tools](#updating-agent-tools)
- [Temporary Tools](#temporary-tools)
- [User-Based Tool Access](#user-based-tool-access)
- [Database-Driven Tools](#database-driven-tools)
- [Advanced Patterns](#advanced-patterns)

## Why Dynamic Tools

Static tools (defined with `@function_tool` decorator) are compiled at class definition time. Dynamic tools allow you to:

- **Adapt to user permissions**: Show different tools to admins vs. regular users
- **Enable/disable features**: Add tools based on subscription level
- **Load from database**: Create tools from database configurations
- **A/B testing**: Vary tools for different user cohorts
- **Plugin systems**: Load tools from external modules
- **Context-aware tooling**: Different tools for different conversation stages

## Three Approaches

LiveKit provides three ways to add tools dynamically:

### 1. Tools at Agent Creation

Pass tools when creating the agent:

```python
from livekit.agents import Agent
from livekit.agents.llm import function_tool

async def get_weather(location: str) -> str:
    """Get weather for a location."""
    return f"Weather in {location}: Sunny"

# Create function tool
weather_tool = function_tool(
    get_weather,
    name="get_weather",
    description="Get current weather for a location"
)

# Pass to agent
agent = Agent(
    instructions="You are a helpful assistant.",
    llm="openai/gpt-4o-mini",
    tools=[weather_tool]
)
```

### 2. Update Tools After Creation

Modify the agent's tools after it's created:

```python
# Create agent
agent = Agent(instructions="...")

# Add new tool later
new_tool = function_tool(
    get_stock_price,
    name="get_stock_price",
    description="Get current stock price"
)

# Update tools
await agent.update_tools(agent.tools + [new_tool])
```

### 3. Temporary Tools Per LLM Call

Add tools for specific LLM invocations by overriding `llm_node`:

```python
class MyAgent(Agent):
    async def llm_node(self, chat_ctx, tools, model_settings):
        # Add temporary tool just for this call
        special_tool = function_tool(
            do_special_thing,
            name="special_action",
            description="Perform special action"
        )

        tools.append(special_tool)

        # Call parent implementation with modified tools
        return await Agent.default.llm_node(
            self, chat_ctx, tools, model_settings
        )
```

## Creating Tools at Runtime

### Basic Function Tool Creation

```python
def create_search_tool(search_provider: str):
    """Create a search tool for a specific provider."""

    async def search(query: str) -> str:
        # Use the provider from closure
        result = await search_providers[search_provider](query)
        return f"Results from {search_provider}: {result}"

    return function_tool(
        search,
        name=f"search_{search_provider}",
        description=f"Search using {search_provider}"
    )

# Create tools for different providers
google_tool = create_search_tool("google")
bing_tool = create_search_tool("bing")

# Use in agent
agent = Agent(
    instructions="...",
    tools=[google_tool, bing_tool]
)
```

### With Type Hints and Annotations

```python
from typing import Annotated
from pydantic import Field

def create_database_tool(table_name: str):
    """Create a tool to query a specific database table."""

    async def query_table(
        field: str,
        value: Annotated[str, Field(description=f"Value to search for in {table_name}")]
    ) -> str:
        result = await database.query(table_name, field, value)
        return f"Found {len(result)} records in {table_name}"

    return function_tool(
        query_table,
        name=f"query_{table_name}",
        description=f"Search {table_name} table by field value"
    )

# Create tools for different tables
user_tool = create_database_tool("users")
order_tool = create_database_tool("orders")
product_tool = create_database_tool("products")
```

## Updating Agent Tools

### Adding Tools

```python
class AdaptiveAgent(Agent):
    async def enable_feature(self, feature_name: str):
        """Enable a feature by adding its tools."""

        new_tools = []

        if feature_name == "calendar":
            new_tools.extend([
                function_tool(schedule_meeting, name="schedule_meeting", description="..."),
                function_tool(list_meetings, name="list_meetings", description="...")
            ])
        elif feature_name == "email":
            new_tools.extend([
                function_tool(send_email, name="send_email", description="..."),
                function_tool(read_emails, name="read_emails", description="...")
            ])

        # Add to existing tools
        await self.update_tools(self.tools + new_tools)

async def schedule_meeting(title: str, time: str) -> str:
    return f"Scheduled: {title} at {time}"

async def list_meetings() -> str:
    return "You have 3 meetings today"

async def send_email(to: str, subject: str) -> str:
    return f"Sent email to {to}"

async def read_emails() -> str:
    return "You have 5 unread emails"
```

### Removing Tools

```python
async def disable_feature(self, feature_name: str):
    """Disable a feature by removing its tools."""

    # Filter out tools for this feature
    remaining_tools = [
        tool for tool in self.tools
        if not tool.name.startswith(feature_name)
    ]

    await self.update_tools(remaining_tools)
```

### Replacing Tools

```python
async def switch_provider(self, provider: str):
    """Switch to a different service provider."""

    # Remove old provider tools
    other_tools = [
        tool for tool in self.tools
        if not tool.name.startswith("search_")
    ]

    # Add new provider tool
    new_search = create_search_tool(provider)

    await self.update_tools(other_tools + [new_search])
```

## Temporary Tools

### Per-Call Tools

```python
class ContextualAgent(Agent):
    def __init__(self):
        super().__init__(instructions="...")
        self.user_premium = False

    async def llm_node(self, chat_ctx, tools, model_settings):
        # Add premium tools only for premium users
        if self.user_premium:
            premium_tool = function_tool(
                advanced_analytics,
                name="advanced_analytics",
                description="Generate advanced analytics (premium feature)"
            )
            tools.append(premium_tool)

        return await Agent.default.llm_node(
            self, chat_ctx, tools, model_settings
        )

async def advanced_analytics(data: str) -> str:
    return "Advanced analytics results"
```

### Conditional Tool Availability

```python
class TimeAwareAgent(Agent):
    async def llm_node(self, chat_ctx, tools, model_settings):
        from datetime import datetime

        # Only offer time-sensitive tools during business hours
        if 9 <= datetime.now().hour < 17:
            business_hours_tool = function_tool(
                contact_support,
                name="contact_support",
                description="Connect with live support"
            )
            tools.append(business_hours_tool)
        else:
            after_hours_tool = function_tool(
                leave_message,
                name="leave_message",
                description="Leave a message for support"
            )
            tools.append(after_hours_tool)

        return await Agent.default.llm_node(
            self, chat_ctx, tools, model_settings
        )
```

## User-Based Tool Access

### Permission-Based Tools

```python
from enum import Enum

class UserRole(str, Enum):
    GUEST = "guest"
    USER = "user"
    ADMIN = "admin"

def get_tools_for_role(role: UserRole) -> list:
    """Return tools appropriate for user role."""

    # Basic tools for everyone
    tools = [
        function_tool(search, name="search", description="Search"),
        function_tool(get_info, name="get_info", description="Get information")
    ]

    # Additional tools for logged-in users
    if role in [UserRole.USER, UserRole.ADMIN]:
        tools.extend([
            function_tool(save_preferences, name="save_preferences", description="..."),
            function_tool(view_history, name="view_history", description="...")
        ])

    # Admin-only tools
    if role == UserRole.ADMIN:
        tools.extend([
            function_tool(delete_user, name="delete_user", description="..."),
            function_tool(view_analytics, name="view_analytics", description="...")
        ])

    return tools

# Create agent with role-based tools
user_role = UserRole.ADMIN
agent = Agent(
    instructions=f"You are assisting a {user_role.value} user.",
    tools=get_tools_for_role(user_role)
)
```

### Subscription-Based Tools

```python
class SubscriptionTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"

def get_tools_for_tier(tier: SubscriptionTier) -> list:
    """Return tools based on subscription tier."""

    tools = [
        function_tool(basic_search, name="search", description="Basic search")
    ]

    if tier in [SubscriptionTier.BASIC, SubscriptionTier.PRO, SubscriptionTier.ENTERPRISE]:
        tools.append(
            function_tool(advanced_search, name="advanced_search", description="Advanced search with filters")
        )

    if tier in [SubscriptionTier.PRO, SubscriptionTier.ENTERPRISE]:
        tools.extend([
            function_tool(export_data, name="export_data", description="Export data"),
            function_tool(api_access, name="api_access", description="API access")
        ])

    if tier == SubscriptionTier.ENTERPRISE:
        tools.extend([
            function_tool(custom_integration, name="custom_integration", description="Custom integration"),
            function_tool(priority_support, name="priority_support", description="Priority support")
        ])

    return tools
```

## Database-Driven Tools

### Loading Tools from Configuration

```python
async def load_tools_from_database(user_id: str) -> list:
    """Load available tools from database configuration."""

    # Fetch user's enabled features
    enabled_features = await database.get_user_features(user_id)

    tools = []

    # Map features to tool functions
    feature_map = {
        "weather": lambda: function_tool(get_weather, name="get_weather", description="..."),
        "calendar": lambda: function_tool(manage_calendar, name="manage_calendar", description="..."),
        "email": lambda: function_tool(send_email, name="send_email", description="..."),
        "analytics": lambda: function_tool(view_analytics, name="view_analytics", description="..."),
    }

    # Create tools for enabled features
    for feature in enabled_features:
        if feature in feature_map:
            tools.append(feature_map[feature]())

    return tools

# Use database-driven tools
user_tools = await load_tools_from_database("user_123")
agent = Agent(
    instructions="...",
    tools=user_tools
)
```

### Dynamic Tool Parameters from Database

```python
async def create_configured_tool(config_id: str):
    """Create a tool with parameters from database."""

    # Load configuration
    config = await database.get_tool_config(config_id)

    async def configured_action(**kwargs) -> str:
        # Use configuration in tool logic
        result = await perform_action(
            endpoint=config["endpoint"],
            api_key=config["api_key"],
            **kwargs
        )
        return result

    return function_tool(
        configured_action,
        name=config["name"],
        description=config["description"]
    )
```

## Advanced Patterns

### Plugin System

```python
import importlib

async def load_plugin_tools(plugin_names: list[str]) -> list:
    """Dynamically load tools from plugins."""

    tools = []

    for plugin_name in plugin_names:
        # Import plugin module
        plugin = importlib.import_module(f"plugins.{plugin_name}")

        # Get tools from plugin
        if hasattr(plugin, "get_tools"):
            plugin_tools = plugin.get_tools()
            tools.extend(plugin_tools)

    return tools

# Load plugins
plugins = ["weather_plugin", "calendar_plugin"]
plugin_tools = await load_plugin_tools(plugins)

agent = Agent(
    instructions="...",
    tools=plugin_tools
)
```

### A/B Testing Tools

```python
import random

def get_tools_for_experiment(user_id: str, experiment_name: str) -> list:
    """Assign tools based on A/B test variant."""

    # Deterministic assignment based on user_id
    random.seed(hash(f"{user_id}:{experiment_name}"))
    variant = "A" if random.random() < 0.5 else "B"

    base_tools = [
        function_tool(search, name="search", description="...")
    ]

    if variant == "A":
        # Variant A: Single comprehensive tool
        base_tools.append(
            function_tool(comprehensive_action, name="do_action", description="...")
        )
    else:
        # Variant B: Multiple specialized tools
        base_tools.extend([
            function_tool(action_part1, name="do_part1", description="..."),
            function_tool(action_part2, name="do_part2", description="...")
        ])

    # Track variant for analytics
    log_experiment_variant(user_id, experiment_name, variant)

    return base_tools
```

### Progressive Tool Disclosure

```python
class ProgressiveAgent(Agent):
    def __init__(self):
        super().__init__(instructions="...")
        self.interaction_count = 0
        self.base_tools = [
            function_tool(basic_help, name="help", description="Get help")
        ]

    async def on_user_message(self, message: str):
        """Progressively reveal tools as user engages more."""
        self.interaction_count += 1

        current_tools = self.base_tools.copy()

        # Add tools at different interaction thresholds
        if self.interaction_count >= 3:
            current_tools.append(
                function_tool(intermediate_feature, name="feature1", description="...")
            )

        if self.interaction_count >= 5:
            current_tools.append(
                function_tool(advanced_feature, name="feature2", description="...")
            )

        await self.update_tools(current_tools)
```

### Context-Based Tool Generation

```python
async def create_context_tools(context: dict) -> list:
    """Create tools based on conversation context."""

    tools = []

    # If discussing products, add product tools
    if "products" in context.get("topics", []):
        tools.append(
            function_tool(search_products, name="search_products", description="...")
        )

    # If order was mentioned, add order tools
    if context.get("order_id"):
        order_id = context["order_id"]

        async def check_order_status() -> str:
            return await get_order_status(order_id)

        tools.append(
            function_tool(check_order_status, name="check_order", description=f"Check status of order {order_id}")
        )

    return tools
```

## Best Practices

1. **Document dynamic tools**: Clearly comment why tools are added/removed dynamically
2. **Validate permissions**: Always verify user has access before adding privileged tools
3. **Cache tool creation**: Don't recreate the same tools repeatedly
4. **Test all variants**: Ensure each combination of dynamic tools works
5. **Monitor tool usage**: Track which dynamic tools are actually used
6. **Handle missing tools gracefully**: What if expected tool isn't available?
7. **Clear tool naming**: Use consistent naming even for dynamic tools

## Common Pitfalls

❌ **Don't leak sensitive tools**: Always check permissions before adding admin tools
❌ **Don't create tools in tight loops**: Cache and reuse tool instances
❌ **Don't forget to update**: Call `update_tools()` after modifying tool list
❌ **Don't lose type hints**: Maintain proper typing even in dynamic creation
❌ **Don't create too many tools**: LLMs perform better with focused tool sets

✅ **Do validate access**: Check user permissions before adding tools
✅ **Do cache tools**: Reuse tool instances when possible
✅ **Do test combinations**: Verify each tool combination works
✅ **Do document behavior**: Comment why tools are added/removed
✅ **Do limit tool count**: Keep total tools reasonable (< 20)

## Testing Dynamic Tools

```python
import pytest
from livekit.agents.testing import VoiceAgentTestSession

@pytest.mark.asyncio
async def test_admin_tools_for_admin_user():
    """Verify admin users get admin tools."""
    tools = get_tools_for_role(UserRole.ADMIN)
    tool_names = [tool.name for tool in tools]

    assert "delete_user" in tool_names
    assert "view_analytics" in tool_names

@pytest.mark.asyncio
async def test_no_admin_tools_for_regular_user():
    """Verify regular users don't get admin tools."""
    tools = get_tools_for_role(UserRole.USER)
    tool_names = [tool.name for tool in tools]

    assert "delete_user" not in tool_names
    assert "view_analytics" not in tool_names

@pytest.mark.asyncio
async def test_tool_update():
    """Test that agent tools can be updated."""
    agent = Agent(instructions="...")

    initial_count = len(agent.tools)

    new_tool = function_tool(test_function, name="test", description="...")
    await agent.update_tools(agent.tools + [new_tool])

    assert len(agent.tools) == initial_count + 1
    assert any(tool.name == "test" for tool in agent.tools)
```
