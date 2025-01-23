from bot.llm.gemini import response_content as content

extractor_prompt = """
Above is a transcript of the video produced by the CRHoy.com news agency in Costa Rica.

The video contains several news stories with no separation between them in the transcript.
Make an analysis of the transcript using a step-by-step approach and divide it into intro, separate news stories, and outro.
Keep the news content in the output in Spanish.

Hints:
- The intro may start with the word "resumamos" which means "let's summarize"
- The outro may contain text like "Para el detalle de estas y otras informaciones visite crhoy.com y nuestras redes sociales."

Provide the output following the schema provided. Ensure that all fields are present and correctly formatted.
Schema Description:
- 'intro': words before the first news story
- 'stories': the list of news stories 
- 'outro': words after the last news story
"""

extractor_prompt_so = content.Schema(
    type=content.Type.OBJECT,
    enum=[],
    required=["intro", "stories", "outro"],
    properties={
        "intro": content.Schema(
            type=content.Type.STRING,
        ),
        "stories": content.Schema(
            type=content.Type.ARRAY,
            items=content.Schema(
                type=content.Type.STRING,
            ),
        ),
        "outro": content.Schema(
            type=content.Type.STRING,
        ),
    },
)

localizator_prompt = """
Above is a list of news stories recovered from a transcript of a video produced by the CRHoy.com news agency in Costa Rica.

Analyze the list and for each news story, identify whether it is related to Costa Rica directly or indirectly.

Provide the output following the schema provided. Ensure that all fields are present and correctly formatted.
Schema Description:
- 'id': identifier of the news story 
- 'is_related_to_costa_rica': boolean indicating if the news is related to Costa Rica directly or indirectly
"""

localizator_prompt_so = content.Schema(
    type=content.Type.OBJECT,
    enum=[],
    required=["stories"],
    properties={
        "stories": content.Schema(
            type=content.Type.ARRAY,
            items=content.Schema(
                type=content.Type.OBJECT,
                enum=[],
                required=["id", "is_related_to_costa_rica"],
                properties={
                    "id": content.Schema(
                        type=content.Type.STRING,
                    ),
                    "is_related_to_costa_rica": content.Schema(
                        type=content.Type.BOOLEAN,
                    ),
                },
            ),
        ),
    },
)

corrector_prompt = """
Above is a list of news stories related to Costa Rica, directly or indirectly, recovered from a transcript of a video produced by the CRHoy.com news agency in Costa Rica.

Correct any spelling discrepancies in the transcribed text. Make sure that names, places, and organizations are spelled correctly. Only add necessary punctuation such as periods, commas, and capitalization, and use only the context provided.

Provide the output following the schema provided. Ensure that all fields are present and correctly formatted.
Schema Description:
- 'correction_required': boolean indicating if the news story needs to be corrected
- 'text': corrected news story or the original text if no correction is required
"""

corrector_prompt_so = content.Schema(
    type=content.Type.OBJECT,
    enum=[],
    required=["stories"],
    properties={
        "stories": content.Schema(
            type=content.Type.ARRAY,
            items=content.Schema(
                type=content.Type.OBJECT,
                enum=[],
                required=["correction_required", "text"],
                properties={
                    "correction_required": content.Schema(
                        type=content.Type.BOOLEAN,
                    ),
                    "text": content.Schema(
                        type=content.Type.STRING,
                    ),
                },
            ),
        ),
    },
)
