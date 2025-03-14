from bot.llm.gemini import response_content as content

label_finalizer_prompt = """
Identify the category of the given news.

## Process
1. Read the original article carefully.
2. Review the list of existing news categories.
   - Compare the article to each existing category.  
   - **Important**: If the new category is only slightly different (i.e., it does not offer a clearly distinguishable scope) from an existing category, you must choose the existing category instead.
3. Determine if the new category is necessary. Only select the new category if it represents a significantly different or clearly distinct classification that cannot be covered by any of the existing categories.
4. Resolve ties in favor of existing categories. If two or more categories are equally applicable, pick the one that already exists to avoid unnecessary proliferation.
4. Evaluate your response by assessing its accuracy and adherence to guidelines, scoring it between 0 and 100, with 100 being the highest score.
5. Reflect on potential improvements to enhance your evaluation score up to 95-100.
6. Revise your answer accordingly.

###EXISTING CATEGORIES LIST###
{existing_categories_list}
###END OF EXISTING CATEGORIES LIST###

###NEW CATEGORY###
{new_category}: {new_category_description}
###END OF NEW CATEGORY###

## Output format

- Provide JSON output following the specified schema.
- Ensure all fields are present and correctly formatted.
- DON'T ADD any introductory text or comments before the JSON; adherence is mandatory to avoid penalties.

Schema Description:
- 'a_chain_of_thought': A detailed, step-by-step evaluation in English of which category the news article fits the best into.
  The evaluation process must include either all or at least two of the following:
  - verification ("Let me check my answer ..."),
  - subgoal setting ("Let me break down the problem into smaller steps ..."),
  - backtracking ("Let's try a different approach, what if ...?"),
  - backward chaining ("Let me use the answer to check my work ...").
- 'b_new_chosen': False, if the chosen category is from the list of existing categories.
- 'c_category': The category that the news article fits the best into.

## Output Examples
Example #1:
{{
  "a_chain_of_thought":"Reasoning regarding the most applicable categories for the news article.",
  "b_new_chosen": "true",
  "c_category":"sport/baseball",
}}
"""

label_finalizer_structured_output = content.Schema(
    type=content.Type.OBJECT,
    required=["a_chain_of_thought", "b_new_chosen", "c_category"],
    properties={
        "a_chain_of_thought": content.Schema(
            type=content.Type.STRING,
        ),
        "b_new_chosen": content.Schema(
            type=content.Type.BOOLEAN,
        ),
        "c_category": content.Schema(
            type=content.Type.STRING,
        ),
    },
)