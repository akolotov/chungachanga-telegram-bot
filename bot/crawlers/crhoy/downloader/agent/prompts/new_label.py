from bot.llm.gemini import response_content as content

namer_prompt = """
Identify the category of the given news.

## Process
1. Read the original article carefully.
2. Suggest a suitable name for the new category where the article could be placed. The category can be one level, such as "lifestyle," or include sub-categories like "sport/football."
3. Evaluate your suggested category on a scale from 0 to 100, with 100 being the highest score.
4. Consider how you might adjust your approach to improve the evaluation score to between 95 and 100.
5. Revise your answer based on this reflection.

## Output format

- Provide JSON output following the specified schema.
- Ensure all fields are present and correctly formatted.
- DON'T ADD any introductory text or comments before the JSON; adherence is mandatory to avoid penalties.

Schema Description:
- 'a_chain_of_thought': A detailed, step-by-step evaluation in English of why the category was chosen.
  The evaluation process must include either all or at least two of the following:
  - verification ("Let me check my answer ..."),
  - subgoal setting ("Let me break down the problem into smaller steps ..."),
  - backtracking ("Let's try a different approach, what if ...?"),
  - backward chaining ("Let me use the answer to check my work ...").
- 'b_category': The suggested category name as a string (e.g., "weather" or "sport/baseball"). The category or sub-category must not contain any spaces or special characters. Underscores are allowed.
- 'd_category_description': A concise description of the category for future categorization tasks.

## Output Examples
Example #1:
{
  "a_chain_of_thought":"Reasoning which categories are most appliable for the news article",
  "b_category":"weather",
  "d_category_description":"News related to weather conditions, forecasts, and climate-related events"
}

Example #2:
{
  "a_chain_of_thought":"Reasoning which categories are most appliable for the news article",
  "b_category":"sport/baseball",
  "d_category_description":"News related to baseball as a sport, including games, tournaments, and events surrounding the sport"
}
"""

namer_structured_output = content.Schema(
    type = content.Type.OBJECT,
    enum = [],
    required = ["a_chain_of_thought", "b_category", "d_category_description"],
    properties = {
      "a_chain_of_thought": content.Schema(
        type = content.Type.STRING,
      ),
      "b_category": content.Schema(
        type = content.Type.STRING,
      ),
      "d_category_description": content.Schema(
        type = content.Type.STRING,
      ),
    },
  )