from bot.llm.gemini import response_content as content

labeler_prompt = """
Identify the category of the given news.

## Process
1. Read the original article carefully.
2. Review the list of existing news categories provided below and determine if the article fits into any of them. Assign a suitability rank for each applicable category on a scale from 0 to 100, where 100 represents perfect applicability. If no suitable category exists, indicate that the category cannot be defined.
  - DON'T assign incorrect categories to the article.
  - DON'T over-rank the categories without strong evidence.
3. Evaluate your response by assessing its accuracy and adherence to guidelines, scoring it between 0 and 100, with 100 being the highest score.
4. Reflect on potential improvements to enhance your evaluation score up to 95-100.
5. Revise your answer accordingly.

###EXISTING CATEGORIES LIST###
{existing_categories}
###END OF EXISTING CATEGORIES LIST###

## Output format

- Provide JSON output following the specified schema.
- Ensure all fields are present and correctly formatted.
- DON'T ADD any introductory text or comments before the JSON; adherence is mandatory to avoid penalties.

Schema Description:
- 'a_chain_of_thought': A detailed, step-by-step evaluation in English of which existing categories the news article could be assigned to.
  The evaluation process must include either all or at least two of the following:
  - verification ("Let me check my answer ..."),
  - subgoal setting ("Let me break down the problem into smaller steps ..."),
  - backtracking ("Let's try a different approach, what if ...?"),
  - backward chaining ("Let me use the answer to check my work ...").
- 'b_no_category': Indicate if a category cannot be selected ('true' or 'false').
- 'c_existing_categories_list': A list containing up to three elements, representing an applicable category with its suitability rank (0-100). An empty list is used if no category applies. . Each element consists of
  - 'a_category'
  - 'b_rank'

## Output Examples
Example #1:
{{
  "a_chain_of_thought":"Reasoning regarding the most applicable categories for the news article.",
  "b_no_category":"false",
  "c_existing_categories_list":[{{"a_category":"health/children","b_rank":"25"}},{{"a_category":"incidents","b_rank":"80"}},{{"a_category":"incidents/roads","b_rank":"99"}}]
}}

Example #2:
{{
  "a_chain_of_thought":"Reasoning that no category can be selected.",
  "b_no_category":"true",
  "c_existing_categories_list":[]
}}
"""

labeler_structured_output = content.Schema(
    type=content.Type.OBJECT,
    required=["a_chain_of_thought", "b_no_category", "c_existing_categories_list"],
    properties={
        "a_chain_of_thought": content.Schema(
            type=content.Type.STRING,
        ),
        "b_no_category": content.Schema(
            type=content.Type.BOOLEAN,
        ),
        "c_existing_categories_list": content.Schema(
            type=content.Type.ARRAY,
            items=content.Schema(
                type=content.Type.OBJECT,
                required=["a_category", "b_rank"],
                properties={
                    "a_category": content.Schema(
                        type=content.Type.STRING,
                    ),
                    "b_rank": content.Schema(
                        type=content.Type.INTEGER,
                    ),
                },
            ),
        ),
    },
)