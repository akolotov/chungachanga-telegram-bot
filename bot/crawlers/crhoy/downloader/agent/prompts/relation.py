from bot.llm.gemini import response_content as content

classifier_prompt = """
Identify whether the given news is related to Costa Rica.

## Process
1. Read the original article carefully.
2. Decide if the news is related to Costa Rica directly, indirectly, or not related at all:
   - **Directly**: Explicit mention of Costa Rica (e.g., locations, people, institutions).
   - **Indirectly**: Clear, stated impact on Costa Rica (e.g., "Costa Rican investors affected" or "event postponed in Costa Rica"). Never classify as "indirectly related" solely because a topic is globally relevant (e.g., domestic violence, climate change).
   - **na**: No mention of Costa Rica or Costa Rican entities and no logical connection stated in the text.
   - **Critical Rule**: Only use explicit information; do not assume unstated connections (e.g., tours, regional effects).
3. Evaluate your response by assessing its accuracy and adherence to guidelines, scoring it between 0 and 100, with 100 being the highest score.
4. Reflect on potential improvements to enhance your evaluation score up to 95-100.
5. Revise your answer accordingly.

## Output format

- Provide JSON output following the specified schema.
- Ensure all fields are present and correctly formatted.
- DON'T ADD any introductory text or comments before the JSON; adherence is mandatory to avoid penalties.

Schema Description:
- 'a_chain_of_thought': A detailed, step-by-step evaluation in English of why the news article is related to Costa Rica, quote the exact text proving the relation or state "No mention of Costa Rica" if none exists.
  The evaluation process must include either all or at least two of the following:
  - verification ("Let me check my answer ..."),
  - subgoal setting ("Let me break down the problem into smaller steps ..."),
  - backtracking ("Let's try a different approach, what if ...?"),
  - backward chaining ("Let me use the answer to check my work ...").
- 'b_related': Whether the news article is related to Costa Rica. Possible values: "directly," "indirectly," "na" (not applicable).

## Output examples
Example #1:
{"a_chain_of_thought":"Reasoning to conclude about the news relation to Costa Rica","b_related":"directly"}

Example #2:
{"a_chain_of_thought":"Reasoning to conclude about the news relation to Costa Rica","b_related":"indirectly"}

Example #3:
{"a_chain_of_thought":"Reasoning to conclude about the news relation to Costa Rica","b_related":"na"}
"""

classifier_structured_output = content.Schema(
    type = content.Type.OBJECT,
    enum = [],
    required = ["a_chain_of_thought", "b_related"],
    properties = {
      "a_chain_of_thought": content.Schema(
        type = content.Type.STRING,
      ),
      "b_related": content.Schema(
        type = content.Type.STRING,
      ),
    },
  )