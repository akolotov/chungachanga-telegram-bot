from bot.llm.gemini import response_content as content

summarizer_prompt = """
You are a content editor for a Telegram channel with recognition of the Society of Editors' prestigious Media Freedom Awards. The channel publishes announcements for news related to Costa Rica. The audience of the channel consists of expats aged 25-45 who recently moved to Costa Rica. Your task is to create concise, easy-to-understand news announcements.

Process:
1. Read the original article.
2. Make the article analysis
3. Compose the summary of the article in English, adhering to these guidelines:
   - Avoid idioms and complex terminology
   - Focus on providing factual information. Avoid exclamations, slogans, calls to action, appeals, expressions of well-wishing (e.g., "Stay healthy!" or "Best wishes to all!"), and words of encouragement or support (e.g., "Wishing our team success!" or "Good luck to all!")
   - Do not include URLs or website links in the final transcription. If necessary, summarize or mention the source without using a URL
   - Use a casual, friendly tone
   - If complex topics or necessary technical terms arise, briefly explain them in simple language

Your goal is to provide the output following the schema provided. Ensure that all fields are present and correctly formatted.
Schema Description:
- 'a_news_analysis' is an object that consists of
  - 'a_mainActor': The primary individual, organization, or entity discussed in the news. Value should be a string.
  - 'b_otherActors': A list of additional participants mentioned in the news. Each element should be a string. If no other participants are mentioned, this can be an empty list.
  - 'c_mainAction': The main action, event, or decision described in the news. Value should be a string.
  - 'd_additionalActions': A list of supplementary actions or events, if mentioned. Each element should be a string. If none are mentioned, this can be an empty list.
  - 'e_timeOrientation': The temporal focus of the main event. Possible values: "past", "present", "future", or "unspecified".
  - 'f_location': The geographical location or context of the event. Value should be a string or "unspecified" if not mentioned.
  - 'g_target': The entity, resource, or group affected by the action or event. Value should be a string or "unspecified" if not mentioned.
  - 'h_reason': The rationale or motive behind the action or event as described in the news. Value should be a string or "unspecified" if not mentioned.
  - 'i_consequences': A list of potential outcomes or impacts explicitly mentioned in the news. Each element should be a map with:
    - 'a_type': The type of consequence (e.g., "economic", "political", "social"). Value should be a string.
    - 'b_description': A detailed explanation of the consequence. Value should be a string.
  - 'j_contextBackground': Relevant historical or contextual information provided in the news. Value should be a string or "unspecified" if not mentioned.
  - 'k_keyPoints': A list of essential facts, quotes, or data points mentioned in the news. Each element should be a string. If no key points are explicitly stated, this can be an empty list.
  - 'l_sentiment': The overall tone of the news as inferred from the text. Possible values: "positive", "negative", "neutral", or "unspecified".
- 'b_news_summary': The final news summary in English.
"""

summarizer_structured_output = content.Schema(
    type = content.Type.OBJECT,
    enum = [],
    required = ["a_news_analysis", "b_news_summary"],
    properties = {
      "a_news_analysis": content.Schema(
        type = content.Type.OBJECT,
        enum = [],
        required = ["a_mainActor", "b_otherActors", "c_mainAction", "d_additionalActions", "e_timeOrientation", "f_location", "g_target", "h_reason", "i_consequences", "j_contextBackground", "k_keyPoints", "l_sentiment"],
        properties = {
          "a_mainActor": content.Schema(
            type = content.Type.STRING,
          ),
          "b_otherActors": content.Schema(
            type = content.Type.ARRAY,
            items = content.Schema(
              type = content.Type.STRING,
            ),
          ),
          "c_mainAction": content.Schema(
            type = content.Type.STRING,
          ),
          "d_additionalActions": content.Schema(
            type = content.Type.ARRAY,
            items = content.Schema(
              type = content.Type.STRING,
            ),
          ),
          "e_timeOrientation": content.Schema(
            type = content.Type.STRING,
          ),
          "f_location": content.Schema(
            type = content.Type.STRING,
          ),
          "g_target": content.Schema(
            type = content.Type.STRING,
          ),
          "h_reason": content.Schema(
            type = content.Type.STRING,
          ),
          "i_consequences": content.Schema(
            type = content.Type.ARRAY,
            items = content.Schema(
              type = content.Type.OBJECT,
              enum = [],
              required = ["a_type", "b_description"],
              properties = {
                "a_type": content.Schema(
                  type = content.Type.STRING,
                ),
                "b_description": content.Schema(
                  type = content.Type.STRING,
                ),
              },
            ),
          ),
          "j_contextBackground": content.Schema(
            type = content.Type.STRING,
          ),
          "k_keyPoints": content.Schema(
            type = content.Type.ARRAY,
            items = content.Schema(
              type = content.Type.STRING,
            ),
          ),
          "l_sentiment": content.Schema(
            type = content.Type.STRING,
          ),
        },
      ),
      "b_news_summary": content.Schema(
        type = content.Type.STRING,
      ),
    },
  )