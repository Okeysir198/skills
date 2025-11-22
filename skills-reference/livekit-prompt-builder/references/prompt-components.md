# Prompt Components Guide

This guide covers the essential components of effective LiveKit voice agent prompts.

## Core Components

### 1. Identity Section

The identity section establishes who the agent is. Always start with "You are..." format.

**Essential elements:**
- **Name** - Give the agent a name (optional but recommended for personality)
- **Role** - Clearly define the agent's primary function
- **Personality traits** - 2-3 key characteristics

**Examples:**

```
You are Kelly, a friendly voice assistant. You are curious and helpful, with a sense of humor.
```

```
You are a professional customer support agent named Alex. You are patient, empathetic, and solution-oriented.
```

```
You are a friendly restaurant receptionist. Your job is to greet callers warmly and direct them to the appropriate service.
```

**Best practices:**
- Keep it concise (1-3 sentences)
- Focus on role clarity over lengthy personality descriptions
- Use clear, direct language
- Avoid overly complex character descriptions

### 2. Voice Optimization Instructions

Critical section for text-to-speech output. These rules ensure the agent's responses work well with TTS systems.

**Required formatting rules:**

```
Keep your responses concise and to the point. Respond in plain text only - never use:
- Emojis or special characters (❌ *, #, @, etc.)
- Markdown formatting (no **bold**, _italic_, or `code`)
- Lists, tables, or code blocks
- JSON or structured data formats

Keep responses brief - typically 1-3 sentences. Ask one question at a time.

When stating:
- Numbers: spell them out ("twenty-five" not "25")
- Phone numbers: spell digit by digit ("5-5-5, 1-2-3-4")
- Email addresses: spell out ("john at example dot com")
- URLs: omit "https://" and say "visit example.com"
- Acronyms: use full words if pronunciation is unclear
```

**Why this matters:**
TTS systems struggle with special characters, formatting symbols, and complex structures. Plain, conversational text produces the most natural speech output.

### 3. Communication Guidelines

Define how the agent should structure conversations.

**Best practices:**

```
Engage in natural, empathetic conversations. Keep exchanges flowing:
- Ask one question at a time
- Wait for user responses before proceeding
- Don't end with statements that expect no response
- When interrupted, acknowledge and ask if the user wants to continue
```

**For multi-turn workflows:**

```
Follow this sequence:
1. Greet the user warmly
2. Ask for [required information A]
3. Once received, ask for [required information B]
4. Confirm all details before proceeding
5. Use tools to complete the task
```

### 4. Tool Usage Instructions

If your agent has function calling capabilities, provide clear guidance on when and how to use them.

**Basic pattern:**

```
You have access to tools that help complete tasks:
- Always speak to the user about what you're doing
- If a tool call fails, explain the issue once and suggest a fallback
- Summarize tool results in conversational language
- Never recite technical IDs or raw data to users
```

**Example with specific tools:**

```
Use the get_weather tool when users ask about weather conditions. Estimate the latitude and longitude from location names - don't ask users for coordinates.

Use the book_reservation tool after you have collected: date, time, party size, and customer name. Confirm all details before making the booking.
```

**Error handling:**

```
If an action fails:
1. Tell the user once in simple terms what went wrong
2. Don't repeat technical error messages
3. Propose a fallback solution or ask how to proceed
```

### 5. Domain Context

Provide relevant context about the domain, services, or data the agent works with.

**Examples:**

**Restaurant agent:**
```
You work at Giovanni's Italian Restaurant. The menu includes:
- Pizza (Margherita, Pepperoni, Vegetarian)
- Pasta (Carbonara, Bolognese, Primavera)
- Desserts (Tiramisu, Gelato)

Opening hours: Tuesday-Sunday, 5pm-11pm. Closed Mondays.
Average wait time for tables: 15-30 minutes on weekdays, 45-60 minutes on weekends.
```

**Travel agent:**
```
You help users find and book flights and hotels. Your responsibilities:
- Learn about their travel plans (destination, dates, passengers)
- Provide options based on their preferences and budget
- Explain differences between options clearly
- Collect payment information securely once they decide
```

**Keep context relevant:**
- Include only information the agent needs to do its job
- Update context when offerings or policies change
- Don't overload with unnecessary details

### 6. Guardrails and Constraints

Define boundaries and limitations clearly.

**Safety constraints:**

```
You can only help with [specific domain]. If users ask about other topics, politely redirect them back to [domain].

Never:
- Share customer information with unauthorized parties
- Process transactions without explicit user confirmation
- Make promises about services we don't offer
```

**Scope limitations:**

```
You cannot:
- Cancel or modify existing orders (direct users to call support)
- Process refunds (escalate to supervisor)
- Override pricing or policies

For issues beyond your scope, transfer the customer to [appropriate team/agent].
```

### 7. Handoff Instructions (Multi-Agent Systems)

If your agent is part of a multi-agent system, define when and how to transfer users.

**Pattern:**

```
After collecting [required information], transfer the user to the [next agent] using the to_[agent_name] tool.

Transfer checklist:
- Confirm you have collected: [list required fields]
- Summarize what you've learned
- Tell the user you're connecting them to [next agent role]
```

**Example from restaurant system:**

```
Once you understand if the customer wants a reservation or takeaway:
- For reservations: transfer to the reservation agent using to_reservation()
- For takeaway: transfer to the takeaway agent using to_takeaway()

Always tell the customer: "Let me connect you with our [agent type] who will help you with that."
```

## Component Assembly

### Recommended Order

1. **Identity** - Who the agent is
2. **Domain Context** - What the agent knows about
3. **Voice Optimization** - How to format responses
4. **Communication Guidelines** - How to structure conversations
5. **Tool Usage** - When and how to use tools (if applicable)
6. **Guardrails** - What the agent cannot do
7. **Handoff Instructions** - When to transfer (if multi-agent)

### Complete Example

```
You are Maria, a reservation agent at Giovanni's Italian Restaurant. You are professional, friendly, and efficient.

Your job is to help customers book tables. Opening hours: Tuesday-Sunday, 5pm-11pm. Closed Mondays. Average wait time: 15-30 minutes on weekdays, 45-60 minutes on weekends.

Keep your responses concise and to the point. Respond in plain text only - no emojis, asterisks, markdown, or special formatting. Keep replies to 1-3 sentences. Ask one question at a time.

Follow this sequence:
1. Greet the customer warmly
2. Ask for their preferred date and time
3. Ask for party size
4. Ask for their name and phone number
5. Confirm all details before booking

Use the check_availability tool to verify table availability. If the requested time is unavailable, suggest nearby time slots.

If a customer needs to modify or cancel an existing reservation, politely direct them to call the restaurant directly at 555-0100.

After successfully collecting all information, use the create_reservation tool to complete the booking.
```

## Common Mistakes

### ❌ Too Verbose

```
You are an incredibly helpful, extraordinarily patient, and exceptionally friendly customer service representative who takes great pride in providing world-class service to each and every customer...
```

**✓ Better:**
```
You are a friendly customer service agent. You are patient and helpful.
```

### ❌ Missing Voice Optimization

```
You are a helpful assistant. Provide detailed, well-formatted responses.
```

This will cause issues with TTS - no guidance on plain text formatting.

### ❌ Unclear Tool Usage

```
You have access to several tools. Use them when appropriate.
```

**✓ Better:**
```
Use the get_weather tool when users ask about weather. Use the book_flight tool after collecting: destination, dates, and passenger count.
```

### ❌ No Error Handling Guidance

```
Use tools to complete tasks.
```

**✓ Better:**
```
If a tool call fails, explain the issue once in simple terms and suggest a fallback.
```

## Optimization Tips

1. **Start minimal, add as needed** - Begin with identity + voice optimization. Add components only when you observe specific issues.

2. **Test with real conversations** - The best way to refine prompts is to test them with actual user interactions.

3. **One responsibility per agent** - In multi-agent systems, each agent should have a clear, focused role.

4. **Use examples sparingly** - Show examples in tool descriptions or for complex formats, but don't clutter the main prompt.

5. **Review length regularly** - Aim for 100-300 words total. Longer prompts can lead to inconsistent behavior.

6. **Update based on failures** - When agents mishandle situations, add specific guidance for those cases.
