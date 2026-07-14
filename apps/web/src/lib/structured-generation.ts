import { z } from "zod";

/**
 * Zod mirror of packages/generation StructuredGeneration.
 * Used by AI SDK streamObject so the claim matches the Python schema.
 */
export const structuredClaimSchema = z.object({
  claim_text: z
    .string()
    .describe("A single factual claim supported by the cited chunk."),
  chunk_id: z
    .string()
    .describe("Must be one of the provided evidence chunk_ids."),
  excerpt: z
    .string()
    .describe("Short verbatim quote copied from that chunk's text."),
});

export const structuredGenerationSchema = z.object({
  abstain: z
    .boolean()
    .describe("True if evidence is insufficient to answer confidently."),
  confidence: z
    .number()
    .min(0)
    .max(1)
    .describe("Confidence in [0, 1] that the answer is grounded."),
  answer_text: z
    .string()
    .describe(
      "Full answer with inline markers like [c1], or abstention message."
    ),
  claims: z
    .array(structuredClaimSchema)
    .describe("Claims with chunk_id citations; empty when abstaining."),
});

export type StructuredGenerationPayload = z.infer<
  typeof structuredGenerationSchema
>;
