import os
import openai
from pydantic import BaseModel
from typing import Literal, Optional
from textwrap import dedent
from dotenv import load_dotenv

class NewsSummary(BaseModel):
    voice_tag: Literal['male', 'female']
    news_original: str
    news_translated: str

class OpenAISummarizerError(Exception):
    """Custom exception for OpenAI Summarizer errors."""
    pass

class OpenAISummarizer:
    """A class to summarize news articles using OpenAI API."""

    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06")

        if not self.api_key:
            raise OpenAISummarizerError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")

        openai.api_key = self.api_key

    def create_news_summary(self, article: str) -> Optional[NewsSummary]:
        """
        Summarizes a news article using OpenAI API.

        Args:
            article (str): The full text of the news article to summarize.

        Returns:
            Optional[NewsSummary]: A NewsSummary object containing the summarized news in Spanish,
                                   its Russian translation, and a voice tag. Returns None if summarization fails.

        Raises:
            OpenAISummarizerError: If there's an error during the summarization process.
        """
        prompt = """
You are a content editor for a Costa Rican radio station targeting non-native Spanish speakers, aged 25-45. Your task is to create concise, easy-to-understand news announcements, each approximately 20 seconds long when read aloud. In addition to writing the news, you will assign either a 'male' or 'female' DJ to read the text based on the news category, and provide a Russian translation for publication on the station's website.

Process:
1. Read the original article.
2. Identify key points that will engage listeners and encourage them to tune in regularly.
3. Compose the news item in Costa Rican Spanish, adhering to these guidelines:
   - Use B1 level Spanish (CEFR scale)
   - Limit to 3 sentences, each generally 7-10 words
   - Avoid acronyms, idioms, and complex terminology
   - Use a casual, friendly tone
   - Ensure cultural sensitivity and relevance to the audience
   - If complex topics or necessary technical terms arise, briefly explain them in simple language.
4. Based on the following criteria, assign the tag 'male' or 'female' to indicate the preferred DJ for delivering the news:
   - Political News: male
   - Health and Lifestyle: female
   - Entertainment: male for technical aspects, female for celebrity gossip
   - Financial News: male
   - Sports: male
   - Weather: female
   - Crime and Disaster Reporting: male
   - Science and Technology: male
   - Emotional or Human-Interest Stories: female
   - General News: male for analytical coverage, female for human-interest angles
5. Translate the news into Russian, ensuring it is clear and accurate while retaining the meaning and tone of the original Spanish version.

Your goal is to provide the output following the schema provided. Ensure that all fields are present and correctly formatted.
Here is a description of the parameters:
- 'voice_tag': The assigned voice tag ('male' or 'female')
- 'news_original': The final news transcription in Spanish
- 'news_translated': The news translation in Russian

If the news category does not clearly fit into the predefined tags, default to using 'male' for the `voice_tag`.
        """

        try:
            completion = openai.OpenAI().beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": dedent(prompt)},
                    {"role": "user", "content": article}
                ],
                temperature=1,  # Adjust for creativity vs. determinism
                max_tokens=1000,    # Adjust based on expected output size
                response_format=NewsSummary,
            )

            response = completion.choices[0].message
            if response.refusal:
                raise OpenAISummarizerError(f"API refused to generate summary: {response.refusal}")
            return response.parsed

        except openai.OpenAIError as oe:
            raise OpenAISummarizerError(f"OpenAI API error: {str(oe)}")
        except Exception as e:
            raise OpenAISummarizerError(f"Unexpected error during summarization: {str(e)}")

def summarize_article(article: str) -> Optional[NewsSummary]:
    """
    Summarizes a news article using the OpenAISummarizer.

    Args:
        article (str): The full text of the news article to summarize.

    Returns:
        Optional[NewsSummary]: A NewsSummary object containing the summarized news in Spanish,
                               its Russian translation, and a voice tag. Returns None if summarization fails.
    """
    summarizer = OpenAISummarizer()
    try:
        return summarizer.create_news_summary(article)
    except OpenAISummarizerError as e:
        print(f"An error occurred while summarizing the article: {e}")
        return None

if __name__ == "__main__":
    # Example usage
    news_article = """
El Consejo Nacional de Supervisión del Sistema Financiero (Conassif) acordó en su sesión ordinaria extender el plazo al proceso de intervención de la Financiera Desyfin S.A., hasta el próximo 13 de octubre.
La entidad informó que la ampliación se otorga debido a que es imprescindible al momento de la decisión que se adopte disponer de información precisa, además, que la Interventoría requiere de los plazos y requisitos establecidos para la presentación de un plan de regularización de la entidad.
La Ley 9816 permite al Conassif ampliar el periodo de intervención hasta en 30 días naturales más, para aquellos casos que, debido a su complejidad, requieran de mayor tiempo para efectuar el análisis respectivo.
Al finalizar el plazo acordado, la interventoría presentará al Conassif un informe que muestre la situación de la entidad intervenida, así como la recomendación de un plan de regularización en caso de que la entidad se considere viable o, en su defecto, el mecanismo de resolución o liquidación si fuera inviable.
    """

    summary = summarize_article(news_article)
    if summary:
        print("Summary Created Successfully!")
        print(f"Voice Tag: {summary.voice_tag}")
        print(f"Spanish Summary: {summary.news_original}")
        print(f"Russian Translation: {summary.news_translated}")
    else:
        print("Failed to create summary.")