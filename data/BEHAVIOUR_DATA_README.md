# Behaviour seed examples

`behaviour_seed.jsonl` contains a small set of original, synthetic examples authored for this project. They illustrate the intended Tanzanian Kiswahili conversational style: natural mtaani usage, light Swanglish, humour, banter, sarcasm comprehension, open discussion and serious-tone adaptation.

## Important limits
- These examples are project-authored synthetic material, not collected user chats and not evidence of model capability.
- They are a tiny seed set for format/design validation only. They are far too small to teach robust language competence or personality by themselves.
- Do not mix them into the base-language pretraining corpus as if they were natural text. Keep them in a separate supervised conversation/instruction-tuning stage.
- Expand only with original, commissioned, or properly licensed/permissioned examples. Never scrape private chats or use personal messages without explicit permission.
- Include fluent Tanzanian Kiswahili reviewers to correct unnatural slang, regional bias, and tone.
- Maintain serious examples so humour does not appear in emergencies, grief, health, legal or financial contexts.
- Preserve the `synthetic`, `license`, `language` and `style` metadata during review.

## Record format
Each JSONL line is one object with an ID, language tag, style label, synthetic-data flag, license/provenance label and ordered role/content messages. This file is not yet wired into the base pretraining script; a separate supervised fine-tuning pipeline and evaluation suite are required before these examples can affect model weights.
