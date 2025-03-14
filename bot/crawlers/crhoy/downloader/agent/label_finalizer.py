import json
from typing import Dict, Tuple, Union

from bot.llm import (
    BaseStructuredOutput,
    ChatModelConfig,
    DeserializationError,
    GeminiChatModel,
    UnexpectedFinishReason,
    BaseResponseError
)
from bot.llm.gemini import response_content as content
from bot.types import LLMEngine
from ...common.logger import get_component_logger

from .exceptions import GeminiLabelFinalizerError
from .prompts.label_finalization import (
    label_finalizer_prompt,
    label_finalizer_structured_output
)
from . import agents_config

logger = get_component_logger("downloader.agent.label_finalizer")

class FinalizedLabel(BaseStructuredOutput):
    """Structured output for label finalization."""
    category: str
    new_chosen: bool

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return label_finalizer_structured_output

    @classmethod
    def deserialize(cls, json_str: str, _engine: LLMEngine) -> "FinalizedLabel":
        """Deserialize the LLM response into a FinalizedLabel object."""
        try:
            finalization_data = json.loads(json_str)
            
            return FinalizedLabel(
                category=finalization_data["c_category"],
                new_chosen=finalization_data["b_new_chosen"]
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise DeserializationError(f"Failed to parse Gemini response: {e}")

class LabelFinalizer(GeminiChatModel):
    """Gemini-powered agent that finalizes category selection for news articles.
    
    This class extends GeminiChatModel to provide label finalization functionality:
    - Compares a new suggested category with existing categories
    - Determines whether to use the new category or an existing one
    - Selects the most appropriate category for the article
    
    The agent uses a structured prompt to ensure consistent output formatting and
    leverages the Gemini model's capabilities for text analysis and decision making.
    """

    def __init__(self, existing_categories: Dict[str, str], new_category_tuple: Tuple[str, str], session_id: str = ""):
        """Initialize the LabelFinalizer agent with specific configuration.
        
        Args:
            existing_categories (Dict[str, str]): Dictionary of existing categories and their descriptions
            new_category_tuple (Tuple[str, str]): Tuple containing (new_category, new_category_description)
            session_id (str): Unique identifier to track agents' responses belong to the same session
        """
        # Create obfuscated category names and mapping
        self._obfuscated_to_real = {}
        
        # Obfuscate categories and get the obfuscated new category name
        new_category, new_category_description = new_category_tuple
        obfuscated_categories, new_obfuscated_name = self._obfuscate_categories(
            existing_categories, new_category
        )
        
        # Format the system prompt with the obfuscated categories and new category
        formatted_system_prompt = label_finalizer_prompt.format(
            existing_categories_list=json.dumps(obfuscated_categories, indent=2),
            new_category=new_obfuscated_name,
            new_category_description=new_category_description
        )
        
        config = agents_config.label_finalizer
        model_config = ChatModelConfig(
            session_id=session_id,
            agent_id="label_finalizer",
            llm_model_name=config.llm_model_name,
            temperature=config.temperature,
            system_prompt=formatted_system_prompt,
            response_class=FinalizedLabel,
            max_tokens=config.max_tokens,
            keep_raw_engine_responses=config.keep_raw_engine_responses,
            raw_engine_responses_dir=config.raw_engine_responses_dir,
            request_limit=config.request_limit,
            request_limit_period_seconds=config.request_limit_period_seconds,
            support_model_config=config.supplementary_model_config,
            logger=logger
        )
        super().__init__(model_config)

    def _obfuscate_categories(self, existing_categories: Dict[str, str], new_category: str) -> Tuple[Dict[str, str], str]:
        """Obfuscate category names to prevent bias in the model's decision.
        
        This method creates obfuscated names (like "CAT000") for all categories and
        builds a mapping from obfuscated names to real category names.
        
        Obfuscation is necessary to ensure the model makes unbiased decisions:
        1. It prevents the model from having preferences for certain category names based on its training
        2. It ensures the model focuses on the semantic content of the article and category descriptions
           rather than being influenced by the category names themselves
        3. It creates a level playing field between existing categories and the new category,
           as the model won't know which is which based on naming conventions or familiarity
        4. It helps avoid potential issues with category names in different languages or with
           specialized terminology that might confuse the model
        
        Args:
            existing_categories: Dictionary of existing categories and their descriptions
            new_category: The new category name to obfuscate
            
        Returns:
            Tuple containing:
            - Dictionary mapping obfuscated category names to their descriptions
            - Obfuscated name for the new category
        """
        # Create obfuscated names for existing categories
        obfuscated_categories = {}
        for i, (category, description) in enumerate(existing_categories.items()):
            obfuscated_name = f"CAT{i:03d}"
            obfuscated_categories[obfuscated_name] = description
            self._obfuscated_to_real[obfuscated_name] = category
        
        # Create obfuscated name for the new category
        new_obfuscated_name = f"CAT{len(existing_categories):03d}"
        self._obfuscated_to_real[new_obfuscated_name] = new_category
        
        return obfuscated_categories, new_obfuscated_name

    def _de_obfuscate_response(self, response) -> FinalizedLabel:
        """De-obfuscate the category name in the model response.
        
        This method converts the obfuscated category name (e.g., "CAT000") in the model's response
        back to the original category name using the mapping created during initialization.
        
        Args:
            response: The response from the model
            
        Returns:
            FinalizedLabel: The processed response with de-obfuscated category
            
        Raises:
            GeminiLabelFinalizerError: If the response is not a FinalizedLabel or contains an unknown category
        """
        if isinstance(response, FinalizedLabel):
            obfuscated_category = response.category
            
            # Restore the actual category name
            if obfuscated_category in self._obfuscated_to_real:
                actual_category = self._obfuscated_to_real[obfuscated_category]
                
                # Create a new FinalizedLabel with the de-obfuscated category
                return FinalizedLabel(
                    category=actual_category,
                    new_chosen=response.new_chosen
                )
            else:
                error_msg = f"Unknown obfuscated category: {obfuscated_category}"
                logger.error(error_msg)
                raise GeminiLabelFinalizerError(error_msg)
        else:
            error_msg = f"Expected FinalizedLabel but got {type(response).__name__}"
            logger.error(error_msg)
            raise GeminiLabelFinalizerError(error_msg)

    def process(self, article: str) -> Union[FinalizedLabel, BaseResponseError]:
        """Process and finalize category selection for a news article.
        
        This method takes news content and:
        1. Compares the new category with existing categories
        2. Determines whether to use the new category or an existing one
        3. Selects the most appropriate category for the article
        
        Args:
            article (str): The news article to analyze
        
        Returns:
            Union[FinalizedLabel, BaseResponseError]: Either a FinalizedLabel object containing:
                - category (str): The selected category (de-obfuscated)
                - new_chosen (bool): Whether the new category was chosen
            Or a BaseResponseError if the finalization fails
        """
        logger.info(f"Sending a request to Gemini to finalize category selection for a news article.")

        try:
            model_response = self.generate_response(article)
        except UnexpectedFinishReason as e:
            return BaseResponseError(error=f"LLM engine responded with: {e}")
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise GeminiLabelFinalizerError(f"Failed to generate response: {e}")
            
        # De-obfuscate the response
        return self._de_obfuscate_response(model_response.response)

if __name__ == "__main__":
    from datetime import datetime
    from bot.llm import initialize
    from .prompts.tests import test_article

    # Initialize LLM
    initialize()

    # Create session ID
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Example new category
    new_category = "politics/legislation"
    new_category_description = "News related to the creation, modification, or implementation of laws and regulations"
    
    # Test existing categories
    existing_categories = {
        "government": "news related to the actions and decisions of the government at all levels, including municipalities, courts, and other governmental bodies",
        "government/courts": "News related to the actions and decisions of the government at all levels, including decisions and operations of the court system"
    }

    # Test label finalization
    finalizer = LabelFinalizer(
        existing_categories,
        (new_category, new_category_description),
        session_id
    )
    
    result = finalizer.process(test_article)

    if isinstance(result, BaseResponseError):
        print(f"Error: {result.error}")
    else:
        print("\nLabel Finalization Results:")
        print(f"Selected Category: {result.category}")
        print(f"New Category Chosen: {result.new_chosen}")
