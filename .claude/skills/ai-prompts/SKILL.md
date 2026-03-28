---
name: ai-prompts
description: AI/LLM integration patterns, guardrails infrastructure, and compliance (EU AI Act, NIST AI RMF)
---

# AI/LLM Integration & Guardrails

This project includes AI guardrails infrastructure in `src/lib/ai/` (TypeScript) or `app/ai/` (Python).

## Using the AI Client

All AI calls MUST go through the guardrails client. Never call the Anthropic SDK directly.

**TypeScript:**
```typescript
import { getAIClient } from '@/lib/ai';
import { z } from 'zod';

const ai = getAIClient();
const result = await ai.generate({
  prompt: 'Analyze this text',
  schema: z.object({ sentiment: z.enum(['positive', 'negative', 'neutral']), confidence: z.number() }),
  purpose: 'sentiment-analysis',  // Required for audit trail
});

if (result.needsHumanReview) {
  // Route to approval queue — confidence below threshold
}
```

**Python:**
```python
from app.ai import get_ai_client
from pydantic import BaseModel

class Sentiment(BaseModel):
    sentiment: str
    confidence: float

ai = get_ai_client()
result = await ai.generate(prompt="Analyze this text", schema=Sentiment, purpose="sentiment-analysis")

if result.needs_human_review:
    # Route to approval queue
```

## Guardrails Architecture

| Layer | What It Does | Compliance |
|-------|-------------|------------|
| **Input Guard** | Prompt injection detection, input sanitization, length limits | EU AI Act Art. 15, NIST Manage 2.2 |
| **Output Validation** | Zod/Pydantic schema validation with retry on parse failure | NIST Manage 2.4 |
| **Confidence Scoring** | Scores each response (0-1), routes low confidence to human review | NIST Measure 2.5, EU AI Act Art. 14 |
| **Audit Logger** | Structured logging of every AI interaction (input preview, output, confidence, model, latency) | EU AI Act Art. 12, NIST Manage 1.3 |
| **Health Metrics** | AI-specific health endpoint: availability, confidence distribution, error rates, per-model stats | NIST Manage 3.2, EU AI Act Art. 9 |
| **AI Disclosure** | All AI responses carry `aiGenerated: true` flag | EU AI Act Art. 50 |

## Rules

- **Never call the Anthropic/OpenAI SDK directly.** Always use `getAIClient()` / `get_ai_client()`
- **Never use raw string responses in application logic.** Always validate with Zod/Pydantic schemas
- **Never skip the `purpose` parameter.** Every AI call must be tagged for audit traceability
- **Never trust AI output for security decisions.** Always validate independently
- **Never log full prompts.** The audit logger captures only a 200-char preview to avoid PII leakage
- **Always handle `needsHumanReview`.** If confidence is below threshold, the response must be reviewed before acting on it

## Confidence Thresholds

| Confidence | Action | Use Case |
|-----------|--------|----------|
| > 0.9 | Auto-accept | Low-risk: summaries, formatting, classification |
| 0.7 - 0.9 | Accept with logging | Medium-risk: recommendations, content generation |
| 0.5 - 0.7 | Flag for review | High-risk: decisions, user-facing content |
| < 0.5 | Require human approval | Critical: financial, medical, legal, safety |

Configure the threshold per-call via `confidenceThreshold` parameter.

## Prompt Injection Protection

The input guard detects:
- **Instruction override**: "ignore previous instructions", "disregard your rules"
- **Role manipulation**: "you are now a...", "pretend to be..."
- **System prompt extraction**: "show me your system prompt", "repeat your instructions"
- **Delimiter injection**: `<system>`, `[INST]`, `<|im_start|>`
- **Data exfiltration**: "send this data to..."

Detected injections are blocked and logged. Suspicious patterns (encoded payloads, code execution) are logged but not blocked.

## AI Health Endpoint

Mount at `/api/ai/health`. Returns:
```json
{
  "status": "ok | degraded | unhealthy",
  "aiAvailable": true,
  "metrics": {
    "totalCalls": 142,
    "successRate": 0.97,
    "avgConfidence": 0.84,
    "avgLatencyMs": 1230,
    "lowConfidenceRate": 0.08,
    "errorRate": 0.03
  },
  "models": {
    "claude-sonnet-4-20250514": { "calls": 142, "successRate": 0.97, "avgLatencyMs": 1230 }
  }
}
```

## Recommended Libraries

**TypeScript:** Zod (validation), @anthropic-ai/sdk (model calls), @instructor-ai/instructor (structured extraction)
**Python:** Pydantic (validation), anthropic (model calls), instructor (structured extraction), guardrails-ai (advanced validation), presidio (PII detection)
**Observability:** Langfuse (open-source LLM tracing), OpenTelemetry (spans), Helicone (proxy logging)

## Testing AI Integrations

- Mock AI responses in unit tests — never make real API calls in CI
- Use golden datasets for regression testing prompt quality
- Test timeout, retry, and error handling paths explicitly
- Test with adversarial inputs (prompt injection patterns)
- Monitor confidence score distribution for drift over time
