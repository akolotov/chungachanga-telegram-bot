from bot.llm.gemini import response_content as content

UNKNOWN_CATEGORY = "__unknown__"
UNKNOWN_CATEGORY_DESCRIPTION = "Internal category used only for database tracking of news articles that have not yet been assigned a proper category"

initial_smart_categories = {
    UNKNOWN_CATEGORY: {
        "description": UNKNOWN_CATEGORY_DESCRIPTION,
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