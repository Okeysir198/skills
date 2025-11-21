# Parameter Patterns

Learn how to document tool parameters effectively so LLMs can call your tools correctly with proper types, constraints, and validation.

## Table of Contents

- [Basic Type Hints](#basic-type-hints)
- [Docstring Documentation](#docstring-documentation)
- [Annotated Types with Field](#annotated-types-with-field)
- [Enums for Discrete Options](#enums-for-discrete-options)
- [Literal Types](#literal-types)
- [Optional Parameters](#optional-parameters)
- [Complex Types](#complex-types)
- [Validation Patterns](#validation-patterns)

## Basic Type Hints

Always use type hints for all parameters—they're automatically included in the tool schema:

```python
@function_tool
async def book_flight(
    self,
    origin: str,
    destination: str,
    departure_date: str,
    passengers: int
) -> str:
    """Book a flight."""
    return f"Booked flight for {passengers} from {origin} to {destination}"
```

The LLM receives this schema:
- `origin`: string
- `destination`: string
- `departure_date`: string
- `passengers`: integer

## Docstring Documentation

Use Google-style docstring Args sections to document parameters:

```python
@function_tool
async def create_task(
    self,
    title: str,
    description: str,
    due_date: str
) -> str:
    """Create a new task in the task management system.

    Use this when the user wants to add a task, create a reminder,
    or schedule something to do later.

    Args:
        title: Brief, descriptive title for the task (e.g., "Review PR #123")
        description: Detailed description of what needs to be done
        due_date: When the task is due in YYYY-MM-DD format
    """
    return f"Created task: {title}"
```

The framework parses the Args section and includes descriptions in the tool schema. Be specific about:
- Expected format (e.g., "YYYY-MM-DD format")
- Valid values (e.g., "between 1 and 100")
- Examples (e.g., "e.g., 'Review PR #123'")

## Annotated Types with Field

Use `Annotated` with Pydantic's `Field` for rich metadata:

```python
from typing import Annotated
from pydantic import Field

@function_tool
async def update_inventory(
    self,
    product_id: Annotated[str, Field(description="Unique product identifier (SKU)")],
    quantity: Annotated[int, Field(description="Number of items to add (positive) or remove (negative)", ge=-1000, le=1000)],
    warehouse: Annotated[str, Field(description="Warehouse location code", pattern="^[A-Z]{3}-[0-9]{2}$")]
) -> str:
    """Update product inventory levels.

    Args:
        product_id: Product SKU
        quantity: Quantity change
        warehouse: Warehouse code
    """
    return f"Updated {product_id} by {quantity} at {warehouse}"
```

Field parameters:
- `description`: Human-readable description
- `ge`, `le`, `gt`, `lt`: Numeric constraints (greater/less than or equal)
- `min_length`, `max_length`: String length constraints
- `pattern`: Regex pattern for validation
- `examples`: List of example values

## Enums for Discrete Options

Use Enums when parameters have a fixed set of valid values:

```python
from enum import Enum

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class Status(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

@function_tool
async def update_task_status(
    self,
    task_id: str,
    status: Status,
    priority: Priority = Priority.MEDIUM
) -> str:
    """Update the status and priority of a task.

    Args:
        task_id: Task identifier
        status: New status for the task
        priority: Task priority level (defaults to medium)
    """
    return f"Task {task_id} set to {status.value} with {priority.value} priority"
```

Benefits:
- LLM sees all valid options
- Type-safe in your code
- Automatic validation
- Better autocomplete in IDEs

## Literal Types

For simple fixed choices, use `Literal`:

```python
from typing import Literal

@function_tool
async def toggle_light(
    self,
    room: Literal["bedroom", "living_room", "kitchen", "bathroom"],
    action: Literal["on", "off", "toggle"]
) -> str:
    """Control room lights.

    Args:
        room: Which room's lights to control
        action: What to do with the lights
    """
    return f"Turned lights {action} in {room}"
```

Use `Literal` when:
- Values are simple strings or numbers
- You don't need the structure of an Enum
- The choices are specific to one function

Use `Enum` when:
- Values are reused across multiple tools
- You need methods on the enum
- You want better IDE support

## Optional Parameters

Use `| None` with defaults for optional parameters:

```python
@function_tool
async def search_products(
    self,
    query: str,
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    in_stock_only: bool = True
) -> str:
    """Search for products with optional filters.

    Args:
        query: Search keywords
        category: Filter by category (optional)
        min_price: Minimum price filter (optional)
        max_price: Maximum price filter (optional)
        in_stock_only: Only show in-stock items (default: True)
    """
    filters = []
    if category:
        filters.append(f"category={category}")
    if min_price:
        filters.append(f"price>={min_price}")
    if max_price:
        filters.append(f"price<={max_price}")

    return f"Searching '{query}' with filters: {', '.join(filters)}"
```

## Complex Types

### Lists

```python
@function_tool
async def create_playlist(
    self,
    name: str,
    song_ids: list[str],
    tags: list[str] | None = None
) -> str:
    """Create a music playlist.

    Args:
        name: Playlist name
        song_ids: List of song IDs to include
        tags: Optional categorization tags
    """
    return f"Created playlist '{name}' with {len(song_ids)} songs"
```

### Dictionaries

```python
@function_tool
async def update_settings(
    self,
    settings: dict[str, str | int | bool]
) -> str:
    """Update application settings.

    Args:
        settings: Dictionary of setting names to values
                 (e.g., {"theme": "dark", "notifications": true})
    """
    return f"Updated {len(settings)} settings"
```

### Custom Models (Pydantic)

For complex structured data:

```python
from pydantic import BaseModel

class Address(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str

@function_tool
async def update_shipping_address(
    self,
    customer_id: str,
    address: Address
) -> str:
    """Update customer's shipping address.

    Args:
        customer_id: Customer identifier
        address: New shipping address
    """
    return f"Updated address for {customer_id}: {address.street}, {address.city}"
```

Note: LLM will receive full schema with all Address fields.

## Validation Patterns

### Range Validation

```python
from typing import Annotated
from pydantic import Field

@function_tool
async def set_temperature(
    self,
    room: str,
    celsius: Annotated[float, Field(ge=15.0, le=30.0, description="Temperature in Celsius (15-30°C)")]
) -> str:
    """Set room temperature.

    Args:
        room: Room name
        celsius: Target temperature
    """
    return f"Setting {room} to {celsius}°C"
```

### String Pattern Validation

```python
@function_tool
async def call_phone(
    self,
    phone_number: Annotated[str, Field(pattern=r"^\+?[1-9]\d{1,14}$", description="Phone number in E.164 format")]
) -> str:
    """Make a phone call.

    Args:
        phone_number: Phone number (e.g., +1234567890)
    """
    return f"Calling {phone_number}"
```

### Email Validation

```python
from pydantic import EmailStr

@function_tool
async def send_email(
    self,
    to: EmailStr,
    subject: str,
    body: str
) -> str:
    """Send an email.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body content
    """
    return f"Sent email to {to}"
```

### URL Validation

```python
from pydantic import HttpUrl

@function_tool
async def fetch_webpage(
    self,
    url: HttpUrl
) -> str:
    """Fetch and summarize a webpage.

    Args:
        url: Webpage URL to fetch
    """
    return f"Fetching {url}"
```

## Combining Approaches

You can combine docstrings, type hints, and Field annotations:

```python
from typing import Annotated, Literal
from pydantic import Field
from enum import Enum

class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    CRYPTO = "crypto"

@function_tool
async def process_payment(
    self,
    amount: Annotated[float, Field(gt=0, le=10000, description="Payment amount in USD")],
    method: PaymentMethod,
    description: Annotated[str, Field(min_length=3, max_length=200)],
    save_method: bool = False,
    tip_percentage: Annotated[float | None, Field(ge=0, le=30)] = None
) -> str:
    """Process a payment transaction.

    Use this when the user wants to make a payment or complete a purchase.
    DO NOT use this without explicit user confirmation of the amount.

    Args:
        amount: Payment amount in USD (must be positive, max $10,000)
        method: Payment method to use
        description: Payment description (3-200 characters)
        save_method: Whether to save this payment method for future use
        tip_percentage: Optional tip as percentage (0-30%)
    """
    total = amount
    if tip_percentage:
        total += amount * (tip_percentage / 100)

    return f"Processing ${total:.2f} via {method.value}"
```

## Best Practices

1. **Always use type hints**: The LLM needs to know what type to pass
2. **Document parameter purpose**: Don't just repeat the parameter name
3. **Provide examples**: Help the LLM understand expected format
4. **Use enums for fixed choices**: Better than free-form strings
5. **Make constraints explicit**: Use Field validation rather than checking in code
6. **Default to required**: Only make parameters optional if they truly are
7. **Keep parameters focused**: If you need many parameters, consider splitting into multiple tools

## Common Patterns by Use Case

### Date and Time

```python
@function_tool
async def schedule_meeting(
    self,
    date: Annotated[str, Field(description="Date in YYYY-MM-DD format", pattern=r"^\d{4}-\d{2}-\d{2}$")],
    time: Annotated[str, Field(description="Time in HH:MM format (24-hour)", pattern=r"^\d{2}:\d{2}$")],
    duration_minutes: Annotated[int, Field(ge=15, le=480, description="Meeting duration (15-480 minutes)")]
) -> str:
    """Schedule a meeting."""
    return f"Scheduled for {date} at {time} ({duration_minutes} min)"
```

### Geographic Data

```python
@function_tool
async def get_location_info(
    self,
    latitude: Annotated[float, Field(ge=-90, le=90)],
    longitude: Annotated[float, Field(ge=-180, le=180)]
) -> str:
    """Get information about a geographic location."""
    return f"Info for {latitude}, {longitude}"
```

### File Operations

```python
@function_tool
async def save_file(
    self,
    filename: Annotated[str, Field(pattern=r"^[\w\-. ]+$", description="Filename (alphanumeric, dots, dashes, spaces)")],
    content: str,
    format: Literal["txt", "json", "csv", "md"] = "txt"
) -> str:
    """Save content to a file."""
    return f"Saved {filename}.{format}"
```

### Identifiers

```python
@function_tool
async def get_order(
    self,
    order_id: Annotated[str, Field(pattern=r"^ORD-\d{8}$", description="Order ID in format ORD-12345678")]
) -> str:
    """Retrieve order details."""
    return f"Fetching order {order_id}"
```

## Troubleshooting

**Issue**: LLM passes wrong type
**Solution**: Add explicit type hints and examples in Field description

**Issue**: LLM doesn't use optional parameters
**Solution**: Make the benefit clear in the parameter description

**Issue**: Validation fails frequently
**Solution**: Relax constraints or add examples showing valid values

**Issue**: LLM confused between similar parameters
**Solution**: Use more distinct names and clarify differences in descriptions
