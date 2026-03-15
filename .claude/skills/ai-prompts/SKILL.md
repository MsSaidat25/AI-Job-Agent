---
name: AI Prompts
description: AI/LLM integration patterns and best practices
---

# AI/LLM Integration

## Structured Output
- Always validate AI responses with Pydantic (Python) or Zod (TypeScript)
- Never use raw string responses in application logic
- Define response schemas before making API calls
- Handle malformed responses gracefully

## Prompt Engineering
- Use system prompts for consistent behavior
- Include examples (few-shot) for complex tasks
- Be specific about output format
- Test prompts with edge cases

## Failover Patterns
- Implement rule-based fallback when AI is unavailable
- Set aggressive timeouts (30-60s for most calls)
- Retry with exponential backoff (max 3 attempts)
- Cache responses when appropriate
- Monitor token usage and costs

## Rate Limiting
- Implement client-side rate limiting before API calls
- Queue requests during high load
- Use batch APIs when processing multiple items
- Handle 429 responses gracefully

## Security
- Never include user secrets in prompts
- Sanitize user input before including in prompts
- Validate and sanitize AI output before using
- Don't trust AI output for security decisions

## Testing
- Use golden datasets for regression testing
- Mock AI responses in unit tests
- Test timeout and error handling paths
- Monitor response quality over time
