# Voice Optimization Guide

This guide provides detailed guidance on optimizing prompts for text-to-speech (TTS) output in LiveKit voice agents.

## Why Voice Optimization Matters

Voice agents face unique challenges compared to text-based chatbots:
- TTS systems struggle with special characters and formatting
- Users have limited patience for long verbal responses
- Screen readers and formatting cues don't exist in voice
- Natural speech patterns differ from written text

## Core Formatting Rules

### Plain Text Only

**The golden rule:** All agent responses must be plain, unformatted text.

**Prohibited elements:**

```
❌ Emojis: 😊 👍 ✨
❌ Markdown formatting: **bold**, _italic_, `code`
❌ Special characters: *, #, @, -, •, →
❌ Lists (bulleted or numbered)
❌ Tables or structured layouts
❌ Code blocks or JSON
❌ ASCII art or diagrams
```

**Why:** TTS systems either skip these characters, pronounce them awkwardly ("asterisk bold hello asterisk"), or produce confusing output.

**Add to prompts:**

```
Respond in plain text only. Never use emojis, asterisks, markdown, or other special formatting characters.
```

### Response Length Constraints

Users have limited patience with long verbal responses. Keep responses brief.

**Guidelines:**
- **Default:** 1-3 sentences per turn
- **Maximum:** ~50-75 words before pausing for user input
- **Ask one question at a time**

**Add to prompts:**

```
Keep your responses concise - typically 1-3 sentences. Ask one question at a time and wait for the user's response before continuing.
```

**Examples:**

❌ **Too long:**
```
I can help you book a reservation. We have availability throughout the week. Our restaurant is open Tuesday through Sunday from 5pm to 11pm. We're closed on Mondays. We offer both indoor and outdoor seating. Indoor seating includes our main dining room and a private event space. Outdoor seating is available on our covered patio. What date would you like to visit?
```

✓ **Better:**
```
I'd be happy to help you book a table. What date would you like to come in?
```

### Numbers and Digits

Spell out numbers for clearer pronunciation.

**Guidelines:**

| Type | Format | Example |
|------|--------|---------|
| Numbers | Spell out | "twenty-five dollars" not "25 dollars" |
| Phone numbers | Spell digits | "5-5-5, 1-2-3-4" not "555-1234" |
| Years | Say naturally | "twenty twenty-five" |
| Prices | Use words | "forty-nine ninety-nine" or "forty-nine dollars" |
| Percentages | Spell out | "fifteen percent" not "15%" |

**Add to prompts:**

```
Spell out numbers, phone numbers, and email addresses. Say "fifteen" not "15", and spell phone numbers digit by digit.
```

**Examples:**

❌ `Your confirmation number is 72419.`
✓ `Your confirmation number is 7-2-4-1-9.`

❌ `The total is $49.99.`
✓ `The total is forty-nine ninety-nine.`

### URLs and Email Addresses

**URLs:**
- Omit "https://"
- Omit "www." if not critical
- Say "dot" for periods
- Say "slash" for paths if needed

**Examples:**

❌ `Visit https://www.example.com/help`
✓ `Visit example dot com slash help`

❌ `Go to https://reservation-system.example.com`
✓ `Go to reservation dash system dot example dot com`

**Email addresses:**
- Use "at" for @
- Use "dot" for periods
- Spell out the address clearly

**Examples:**

❌ `Email us at support@example.com`
✓ `Email us at support at example dot com`

**Add to prompts:**

```
When sharing URLs, omit "https://" and say "dot" for periods. For email addresses, say "at" for @ and "dot" for periods.
```

### Acronyms and Abbreviations

Only use acronyms if pronunciation is clear.

**Clear acronyms (OK to use):**
- API (pronounced "A-P-I")
- FAQ (pronounced "F-A-Q")
- CEO, CFO, CTO (clear letter pronunciation)
- USA, UK (clear letter pronunciation)

**Unclear acronyms (spell out):**
- SQL → "S-Q-L" or "Structured Query Language"
- RSVP → "R-S-V-P" or "please respond"
- etc. → "and so on"

**Add to prompts if relevant:**

```
Avoid acronyms with unclear pronunciation. If you must use them, spell them out or use the full phrase.
```

## Conversational Patterns

### One Question at a Time

Don't overwhelm users with multiple questions in one turn.

❌ **Multiple questions:**
```
What date would you like to visit, what time works best for you, and how many people will be in your party?
```

✓ **Single question:**
```
What date would you like to visit?
```

Then wait for response, then ask about time, then about party size.

**Add to prompts:**

```
Ask one question at a time. Wait for the user's answer before asking the next question.
```

### Natural Hesitations (Advanced)

For highly expressive agents, you can allow natural hesitations like "um" or "let me see." Use sparingly.

**Example instruction:**

```
Engage in natural conversations. Include brief, natural hesitations like "um" or "let me check" when appropriate, but keep them minimal.
```

**When to use:** Agents designed to feel highly human-like (companionship, therapy, storytelling).

**When to avoid:** Professional contexts (customer service, medical, financial).

### Response Patterns

**Don't end with statements that expect no response:**

❌ `Your reservation is confirmed. Have a great day.` (then wait awkwardly)

✓ `Your reservation is confirmed! Is there anything else I can help you with?`

**When interrupted, acknowledge:**

```
When interrupted by the user, acknowledge their input and ask if they'd like you to continue or if they have a different question.
```

## Provider-Specific Considerations

Different TTS providers have different characteristics. LiveKit supports multiple providers.

### Common TTS Providers in LiveKit

**OpenAI TTS (default in many examples)**
- Good with natural speech patterns
- Handles most punctuation well
- May stumble on special characters

**Cartesia (Sonic model)**
- Fast, low-latency
- Clear pronunciation
- Good for real-time conversations

**Deepgram**
- Strong with accents and dialects
- Handles conversational speech well
- Good at natural intonation

**ElevenLabs**
- Highly expressive voices
- Excellent for personality-driven agents
- Can handle emotional cues

### Universal Best Practices

Regardless of provider:
1. Use plain text
2. Keep responses brief
3. Spell out numbers
4. Avoid special characters
5. Test with your specific TTS provider

## Testing Your Voice Output

### Quick Test Checklist

Before deploying, verify your agent:

- [ ] Never uses emojis or special characters
- [ ] Keeps responses under 3 sentences by default
- [ ] Spells out numbers and phone numbers
- [ ] Omits "https://" from URLs
- [ ] Asks one question at a time
- [ ] Doesn't use markdown formatting
- [ ] Avoids complex acronyms
- [ ] Provides conversational flow (doesn't end abruptly)

### Sample Test Conversations

**Test 1: Number handling**
```
User: What's my confirmation number?
Agent: Your confirmation number is 7-2-4-1-9. ✓

Agent: Your confirmation number is 72419. ❌
```

**Test 2: Multiple questions**
```
User: I need to book a table.
Agent: I'd be happy to help! What date would you like? ✓

Agent: I'd be happy to help! What date would you like, what time, and how many people? ❌
```

**Test 3: Special characters**
```
Agent: Great! I've got that booked for you. ✓

Agent: Great! ✨ I've got that booked for you. 👍 ❌
```

## Common Issues and Solutions

### Issue: Agent Uses Formatting

**Symptom:** Agent responds with "star star hello star star" or similar.

**Solution:** Add explicit formatting rules:
```
Never use asterisks, markdown, or any special formatting. Respond only in plain text.
```

### Issue: Responses Too Long

**Symptom:** Users interrupt frequently or seem impatient.

**Solution:** Add length constraints:
```
Keep responses very brief - 1 to 2 sentences maximum. Ask one question at a time.
```

### Issue: URLs Sound Awkward

**Symptom:** Agent says "h-t-t-p-s colon slash slash..."

**Solution:** Add URL formatting rules:
```
When sharing URLs, omit "https://" and say "dot" for periods. Example: "visit example dot com"
```

### Issue: Numbers Sound Unnatural

**Symptom:** "You owe dollar sign forty-nine point nine nine"

**Solution:** Add number formatting:
```
Spell out numbers naturally. Say "forty-nine ninety-nine" not "forty-nine point ninety-nine" for prices.
```

## Advanced: Emotional Expression

For agents that should convey emotion, use descriptive language instead of emojis or formatting.

**Instead of emojis:**

❌ `I'm so excited to help you! 🎉`
✓ `I'm so excited to help you!`

The TTS will convey emotion through intonation. Trust the TTS system.

**Emotional guidance in prompts:**

```
When users share good news, respond warmly and enthusiastically. When they express frustration, respond with empathy and patience.
```

**Let tone emerge naturally from words:**
- "I'm so glad to hear that!"
- "Oh no, I understand how frustrating that must be."
- "That sounds wonderful!"

## Voice Optimization Template

Use this template in your prompts:

```
Keep your responses concise and conversational - typically 1-3 sentences. Respond in plain text only:
- Never use emojis, asterisks, or special characters
- No markdown formatting (no **bold** or _italic_)
- No lists, tables, or code blocks
- Ask one question at a time
- Spell out numbers ("fifteen" not "15")
- For URLs, omit "https://" and say "dot" for periods
- Spell email addresses ("user at example dot com")
```

## Summary: Essential Rules

Every voice agent prompt should include these core rules:

1. **Plain text only** - No special characters or formatting
2. **Brief responses** - 1-3 sentences typical
3. **One question at a time** - Don't overwhelm users
4. **Spell out numbers** - Better TTS pronunciation
5. **Simplify URLs and emails** - Omit technical prefixes

Add these rules to every LiveKit voice agent prompt to ensure optimal TTS output.
