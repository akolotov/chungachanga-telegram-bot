from bot.llm.gemini import response_content as content

UNKNOWN_CATEGORY = "__unknown__"

categorizer_prompt = """
You are the head of content editors for a Telegram channel with recognition of the Society of Editors' prestigious Media Freedom Awards. The channel publishes announcements for news related to Costa Rica. Before you pass the news article for further handling to one of your editors, you need to identify:
- whether the news is related to Costa Rica 
- what the category of the news is

Process:
1. Read the original article.
2. Decide if the news is related to Costa Rica directly, indirectly or not related at all.
   - **Directly**: Explicit mention of Costa Rica (e.g., locations, people, institutions).  
   - **Indirectly**: Clear, stated impact on Costa Rica (e.g., "Costa Rican investors affected" or "event postponed in Costa Rica"). Never classify as "indirectly related" solely because a topic is globally relevant (e.g., domestic violence, climate change).
   - **na**: No mention of Costa Rica or Costa Rican entities, and no logical connection stated in the text.  
   - **Critical Rule**: Never assume unstated connections (e.g., tours, regional effects). Only use explicit information. 
3. Go through the list of existing news categories provided below and decide if the article falls into one of the categories. If there is no suitable category, suggest your own name for a new category. Don't hesitate to introduce sub-categories if necessary, e.g. "sport/football". Make sure that you don't make groundless or incorrect category assignments since this will reduce the quality of information provided to users and may cause them to leave the channel. When a new category (or subcategory) is suggested, it is necessary to avoid too specific category.

###EXISTING CATEGORIES LIST###
{existing_categories}
###END OF EXISTING CATEGORIES LIST###

Your goal is to provide output following the schema provided. Ensure that all fields are present and correctly formatted.
Schema Description:
- 'a_relation_chain_of_thought': step-by-step evaluation in English of whether the news article is related to Costa Rica, quote the exact text proving the relation or state "No mention of Costa Rica" if none exists.
- 'b_related': whether the news article is related to Costa Rica. Possible values: "directly", "indirectly", "na" (not applicable)
- 'c_category_chain_of_thought': step-by-step evaluation in English of which existing categories the news could be assigned to
- 'd_existing_categories_list': a list of three elements with existing categories that the news falls into
- 'e_new_category_chain_of_thought': step-by-step evaluation of whether the existing categories are insufficient to assign the news and suggestion of a new category.
- 'f_new_categories_list': a list of three elements with new categories that the news falls into, or empty if no new categories are needed. Each element is either a category name or a category name with a subcategory separated by a slash, e.g. "sport/football". Both the category and subcategory must be single words. 
- 'g_category_election_chain_of_thought': pros and cons in English for choosing one element from the existing or newly suggested categories
- 'h_category': the final chosen category for the news article
- 'i_category_description': if a new category is chosen, provide a short description of the category to use it further for in next categorization operations
"""

categorizer_structured_output = content.Schema(
    type = content.Type.OBJECT,
    enum = [],
    required = ["a_relation_chain_of_thought", "b_related", "c_category_chain_of_thought", "d_existing_categories_list", "e_new_category_chain_of_thought", "f_new_categories_list", "g_category_election_chain_of_thought", "h_category", "i_category_description"],
    properties = {
      "a_relation_chain_of_thought": content.Schema(
        type = content.Type.STRING,
      ),
      "b_related": content.Schema(
        type = content.Type.STRING,
      ),
      "c_category_chain_of_thought": content.Schema(
        type = content.Type.STRING,
      ),
      "d_existing_categories_list": content.Schema(
        type = content.Type.ARRAY,
        items = content.Schema(
          type = content.Type.STRING,
        ),
      ),
      "e_new_category_chain_of_thought": content.Schema(
        type = content.Type.STRING,
      ),
      "f_new_categories_list": content.Schema(
        type = content.Type.ARRAY,
        items = content.Schema(
          type = content.Type.STRING,
        ),
      ),
      "g_category_election_chain_of_thought": content.Schema(
        type = content.Type.STRING,
      ),
      "h_category": content.Schema(
        type = content.Type.STRING,
      ),
      "i_category_description": content.Schema(
        type = content.Type.STRING,
      ),
    },
  )

initial_smart_categories = {
    UNKNOWN_CATEGORY: {
        "description": "Internal category used only for database tracking of news articles that have not yet been assigned a proper category",
        "ignore": True
    },
    "lifestyle": {
        "description": "news related to people's way of life, their choices, values and stories of their life",
        "ignore": False
    },
    "lifestyle/expats": {
        "description": "news about Costa Ricans who are achieving significant success and recognition while living and working in other countries",
        "ignore": False
    },
    "entertainment": {
        "description": "news and articles related to entertainment such as movies, music, TV and live events",
        "ignore": False
    },
    "entertainment/celebrities": {
        "description": "news related to celebrities and prominent figures in the entertainment industry, including their personal lives, events (e.g., births, deaths, weddings, etc.), and achievements",
        "ignore": False
    },
    "crime": {
        "description": "news about criminal activities and law enforcement",
        "ignore": True
    },
    "crime/femicide": {
        "description": "News related to homicides specifically targeting women, often involving gender-based violence and related legal proceedings",
        "ignore": True
    },
    "government": {
        "description": "news related to the actions and decisions of the government at all levels, including municipalities, courts, and other governmental bodies",
        "ignore": False
    },
    "government/public_opinion": {
        "description": "News related to the public's sentiment, opinions, and reactions towards government actions, policies, and officials. It includes analysis of public perception and feedback on governmental decisions and their impact",
        "ignore": False
    },
    "government/courts": {
        "description": "News related to the actions and decisions of the government at all levels, including decisions and operations of the court system",
        "ignore": False
    },
    "government/party_politics": {
        "description": "News related to the internal operations, elections, and decision-making processes within political parties",
        "ignore": False
    },
    "weather": {
        "description": "news related to weather conditions, forecasts, and climate-related events",
        "ignore": False
    },
    "culture/arts": {
        "description": "news related to artistic endeavors, cultural events, and figures",
        "ignore": False
    },
    "sport/boxing": {
        "description": "news related to boxing as a sport, including fights, tournaments, and controversies surrounding the sport",
        "ignore": True
    },
    "sport/baseball": {
        "description": "News related to baseball as a sport, including games, tournaments, and events surrounding the sport",
        "ignore": True
    },
    "health/children": {
        "description": "news specifically related to the health and well-being of children, including public health issues, medical treatments, and healthcare policies affecting children",
        "ignore": False
    },
    "economy/trade": {
        "description": "News related to economic activities, trade, commerce, and their impact on the country. This includes analysis of economic indicators, trade agreements, and issues affecting businesses",
        "ignore": False
    },
    "transportation/aviation": {
        "description": "News related to air travel and aviation incidents",
        "ignore": False
    },
    "incidents": {
        "description": "News related to accidents, disasters, and other unexpected events that cause harm or disruption",
        "ignore": False
    },
    "incidents/infrastructure": {
        "description": "News related to accidents and incidents that cause damage to essential infrastructure, such as power grids, communication networks, roads, and water supply systems, and their resulting impact on services and communities",
        "ignore": False
    },
    "incidents/roads": {
        "description": "News related to accidents, collisions, and other road incidents involving injuries, fatalities, or traffic disruptions, highlighting events on highways, streets, and other public thoroughfares.",
        "ignore": False
    },
    "education": {
        "description": "News related to educational policies, initiatives, student achievements, and other developments in the education sector",
        "ignore": False
    },
    "education/awards": {
        "description": "News related to scholarships, grants, awards, and other forms of recognition within the education sector, covering student achievements and opportunities",
        "ignore": False
    },
    "technology/internet_services": {
        "description": "News related to the functioning, outages, and security of internet-based services and platforms",
        "ignore": False
    },
    "environment/parks": {
        "description": "News related to the establishment, maintenance, and conservation of parks and protected natural areas, including related policies and community involvement",
        "ignore": False
    }
}

def initial_existing_categories_to_map():
    """
    Transform a dictionary with nested description/ignore structure to a simple category -> description mapping.
    Excludes the UNKNOWN_CATEGORY from the mapping.
    
    Returns:
        dict: Simple mapping of category names to their descriptions
    """
    return {
        category: info["description"]
        for category, info in initial_smart_categories.items()
        if category != UNKNOWN_CATEGORY
    }