# Tool Integration Guide

This guide covers best practices for integrating function calling and tools into LiveKit voice agent prompts.

## Overview

LiveKit voice agents can use tools (function calling) to:
- Fetch external data (weather, database queries, API calls)
- Perform actions (book reservations, create tickets, send emails)
- Transition between agents (multi-agent handoffs)
- Retrieve information (search, RAG systems)

The quality of tool integration depends heavily on clear prompt instructions.

## Basic Tool Integration Pattern

### Minimal Tool Instructions

For simple tools, minimal instruction often works:

```python
@function_tool
def get_weather(latitude: str, longitude: str):
    """Get the current weather for a location.
    Estimate the latitude and longitude from the location name - don't ask the user for coordinates."""
    # Implementation
```

**Prompt addition:**
```
You have access to a weather tool. Use it when users ask about weather conditions.
```

The function docstring provides guidance to the LLM about parameter handling.

### Explicit Tool Instructions

For complex workflows, add detailed instructions to the prompt:

```
Use the get_weather tool when users ask about weather:
- Estimate latitude and longitude from city/location names
- Never ask users for coordinates
- If the location is ambiguous, ask for clarification first
```

## Tool Usage Patterns

### Pattern 1: Data Retrieval

**Use case:** Fetching information from external sources.

**Example tools:**
- `get_weather(location)`
- `search_database(query)`
- `lookup_customer(phone_number)`

**Prompt instructions:**

```
You have access to these tools:
- get_weather: Use when users ask about weather or temperature
- search_database: Use to find product information when users ask about items

Guidelines:
- Use tools to provide accurate, up-to-date information
- Don't make up information - use the tools to get real data
- Summarize tool results in conversational language
```

**Example conversation:**
```
User: What's the weather in New York?
Agent: [calls get_weather("New York")]
        The weather in New York is currently 72 degrees and sunny.
```

### Pattern 2: Action Execution

**Use case:** Performing operations that change state.

**Example tools:**
- `create_reservation(date, time, party_size, name, phone)`
- `book_flight(origin, destination, date)`
- `send_email(recipient, subject, body)`

**Prompt instructions:**

```
Use the create_reservation tool after collecting all required information:
- Date and time
- Party size
- Customer name
- Phone number

Before creating the reservation:
1. Confirm all details with the customer
2. Wait for explicit confirmation
3. Then call the tool
4. Announce the result to the customer
```

**Example conversation:**
```
User: I'd like to book a table.
Agent: I'd be happy to help! What date would you like?
User: Tomorrow at 7pm.
Agent: Great! How many people?
User: Four people.
Agent: And may I have your name?
User: John Smith.
Agent: Perfect! And a phone number for the reservation?
User: 555-1234.
Agent: Let me confirm: table for four tomorrow at 7pm under John Smith at 5-5-5, 1-2-3-4. Is that correct?
User: Yes.
Agent: [calls create_reservation()] Excellent! Your reservation is confirmed.
```

### Pattern 3: Agent Handoffs (Multi-Agent Systems)

**Use case:** Transferring users between specialized agents.

**Example tools:**
- `to_reservation_agent()`
- `to_support_agent()`
- `to_checkout_agent(customer_data)`

**Prompt instructions:**

```
Once you determine the customer needs a reservation, transfer them using the to_reservation_agent tool.

Before transferring:
1. Confirm what the customer needs
2. Let them know you're connecting them to the right specialist
3. Call the transfer tool

Example: "Let me connect you with our reservation specialist who can help with that."
```

**Example conversation:**
```
User: I'd like to book a table.
Agent: I'd be happy to help you with a reservation! Let me connect you with our reservation specialist.
       [calls to_reservation_agent()]
```

### Pattern 4: Error Recovery

**Use case:** Handling tool failures gracefully.

**Prompt instructions:**

```
If a tool call fails:
1. Explain the issue to the user in simple terms (don't share technical errors)
2. Suggest a fallback solution
3. Ask how they'd like to proceed

Examples:
- "I'm having trouble checking availability right now. Would you like to try a different date, or I can give you our phone number to call directly?"
- "The search isn't returning results for that. Could you try rephrasing, or would you like to speak with a specialist?"
```

**Example conversation:**
```
Agent: [calls get_weather(), receives error]
       I'm having trouble getting the weather information right now. Would you like me to try again, or is there something else I can help you with?
```

## Tool Result Handling

### Speak Results Conversationally

Don't recite raw data - translate it into natural language.

❌ **Raw data:**
```
Agent: The tool returned: {"temp": 72, "condition": "sunny", "humidity": 45}
```

✓ **Conversational:**
```
Agent: It's currently 72 degrees and sunny.
```

**Prompt instruction:**

```
When you receive tool results, summarize them in conversational language. Don't recite technical data, IDs, or JSON structures to users.
```

### Handle Missing Data

If tool results are incomplete, explain clearly.

**Prompt instruction:**

```
If tool results are incomplete or missing expected information, acknowledge what you found and what's unavailable.

Example: "I can see the current temperature is 72 degrees, but I don't have the forecast for later today."
```

### Structured Data

For complex data, extract what's relevant for the user.

❌ **Too much detail:**
```
Agent: I found 47 search results. The first one has ID 12847, created on 2024-03-15, with tags "electronics", "sale", "featured", and the price is $49.99 with SKU EL-1284...
```

✓ **Relevant summary:**
```
Agent: I found several options. The most popular one is forty-nine ninety-nine. Would you like to hear more about it?
```

**Prompt instruction:**

```
When tools return large datasets:
- Summarize the most relevant information
- Offer to provide more details if the user wants them
- Don't recite technical IDs, timestamps, or metadata unless specifically asked
```

## Parameter Collection

### Implicit vs Explicit Collection

**Implicit:** Let the tool docstring guide the LLM.

```python
@function_tool
def book_flight(origin: str, destination: str, date: str):
    """Book a flight. Estimate the airport codes from city names - don't ask users for airport codes."""
```

**Explicit:** Add collection flow to the prompt.

```
To book a flight, collect in this order:
1. Departure city
2. Destination city
3. Travel date
4. Number of passengers

After collecting all information, confirm details before booking.
```

### Required vs Optional Parameters

Make it clear which parameters are required.

**Prompt instruction:**

```
Required information for booking:
- Date and time (required)
- Party size (required)
- Name (required)
- Phone number (required)

Optional information:
- Seating preference (indoor/outdoor)
- Special requests

Collect all required information before calling the tool. Optional information can be included if the user provides it.
```

### Validation Before Tool Calls

Ensure data quality before making tool calls.

**Prompt instruction:**

```
Before calling create_reservation:
- Verify the date is in the future
- Ensure party size is a reasonable number (1-20)
- Confirm phone number has at least 10 digits
- If anything seems wrong, ask for clarification
```

## Sequential vs Parallel Tool Calls

### Sequential Tool Calls

When one tool's result is needed for the next.

**Prompt instruction:**

```
Follow this sequence:
1. First, use check_availability to see if the time slot is open
2. If available, then use create_reservation with the customer's details
3. If not available, suggest alternative times using suggest_alternatives
```

### Parallel Tool Calls

When multiple independent pieces of information are needed.

**Note:** Some LLM configurations support `parallel_tool_calls=True`, allowing simultaneous calls.

**Prompt instruction:**

```
You can use multiple tools at once when gathering independent information. For example, you can check weather and restaurant hours simultaneously.
```

## Multi-Agent Tool Patterns

### Passing Context Between Agents

When transitioning between agents, decide what context to preserve.

**Pattern 1: Full chat history**

```python
@function_tool
def to_reservation_agent():
    """Transfer to reservation agent with full conversation history."""
    return ReservationAgent(chat_ctx=current_chat_history)
```

**Pattern 2: Structured data only**

```python
@function_tool
def to_checkout_agent(customer_name: str, phone: str, order_items: list):
    """Transfer to checkout with collected customer data."""
    return CheckoutAgent(user_data={"name": customer_name, "phone": phone, "order": order_items})
```

**Prompt consideration:**

```
When transferring to the next agent, ensure you've collected: [list required fields].

The next agent will receive this information, so make sure it's accurate before transferring.
```

### Validation Before Handoff

Ensure required data is collected before transferring.

**Prompt instruction:**

```
Before transferring to the checkout agent:
- Verify you have the customer's full order
- Confirm you have their name and phone number
- Check that you've confirmed the total price with them

If any information is missing, collect it before transferring.
```

## Tool Naming and Discovery

### Clear, Descriptive Names

Tool names should clearly indicate their purpose.

**Good names:**
- `get_weather`
- `create_reservation`
- `search_products`
- `to_support_agent`

**Avoid:**
- `tool1`
- `helper`
- `process`

### Consistent Prefixes

For multiple related tools, use consistent naming:

**Good pattern:**
- `reservation_create`
- `reservation_modify`
- `reservation_cancel`

Or:
- `to_reservation_agent`
- `to_checkout_agent`
- `to_support_agent`

## Complete Tool Integration Example

### Restaurant Multi-Agent System

**Greeter Agent Prompt:**

```
You are a friendly restaurant receptionist at Giovanni's Italian Restaurant.

Your job is to greet callers and understand what they need:
- Reservations: booking a table
- Takeaway: ordering food for pickup

Keep your responses brief and conversational. No special formatting or emojis.

After determining what the customer needs, transfer them to the appropriate agent:
- For reservations: use to_reservation_agent()
- For takeaway orders: use to_takeaway_agent()

Before transferring, always say: "Let me connect you with our [type] specialist who can help you with that."
```

**Reservation Agent Prompt:**

```
You are a reservation agent at Giovanni's Italian Restaurant. You are professional and efficient.

Collect the following information in order:
1. Preferred date
2. Preferred time
3. Party size
4. Customer name
5. Phone number

Ask one question at a time. Keep responses brief - 1-2 sentences.

Before creating the reservation:
- Confirm all details with the customer
- Wait for explicit confirmation
- Then use create_reservation(date, time, party_size, name, phone)

If the requested time is unavailable, use check_availability to suggest nearby time slots.

For modifications or cancellations of existing reservations, direct customers to call the restaurant directly at 5-5-5, 0-1-0-0.
```

**Takeaway Agent Prompt:**

```
You are a takeaway order agent at Giovanni's Italian Restaurant.

Our menu:
- Pizza: Margherita ($15), Pepperoni ($17), Vegetarian ($16)
- Pasta: Carbonara ($14), Bolognese ($15), Primavera ($13)
- Dessert: Tiramisu ($8), Gelato ($6)

Process orders following these steps:
1. Ask what they'd like to order
2. For each item, confirm any special requests
3. Ask if they'd like anything else
4. Confirm the complete order
5. Use calculate_total to get the price
6. Transfer to checkout using to_checkout_agent(customer_order)

Keep responses conversational and brief. No special formatting. Spell out prices ("fifteen dollars" not "$15").
```

## Testing Tool Integration

### Test Checklist

- [ ] Agent uses tools at appropriate times
- [ ] Agent collects all required parameters before calling tools
- [ ] Agent confirms details before action tools (reservations, bookings, etc.)
- [ ] Agent handles tool failures gracefully
- [ ] Agent summarizes tool results conversationally (no raw data)
- [ ] Agent doesn't ask for information that tools can infer
- [ ] Agent validates data before tool calls
- [ ] Multi-agent transfers happen at the right time with required context

### Common Issues

**Issue: Agent asks for data the tool can infer**

Example: Asking users for latitude/longitude when tool can estimate from city name.

**Solution:** Add guidance to prompt or tool docstring:
```
Estimate coordinates from location names - don't ask users for coordinates.
```

**Issue: Agent doesn't confirm before destructive actions**

**Solution:** Add confirmation step:
```
Before creating the reservation, confirm all details and wait for explicit user confirmation.
```

**Issue: Agent recites raw data**

**Solution:** Add result formatting guidance:
```
Summarize tool results in natural, conversational language. Don't recite technical IDs or raw data structures.
```

## Summary: Tool Integration Best Practices

1. **Provide clear tool usage instructions** - When to use each tool
2. **Define parameter collection flow** - What to ask, in what order
3. **Require confirmation for actions** - Especially for destructive operations
4. **Handle errors gracefully** - Simple explanations, not technical errors
5. **Speak results conversationally** - Translate data into natural language
6. **Validate before calling** - Check data quality first
7. **For multi-agent: define handoff criteria** - When to transfer, what context to pass

These practices ensure tools integrate smoothly into natural voice conversations.
