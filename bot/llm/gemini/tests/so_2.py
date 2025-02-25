"""
This test module demonstrates how to handle multiple response formats within a single Gemini LLM chat session.

Contains demonstrations for:
- Defining and switching between different response schemas during a chat session
- Incorporating external documentation into prompts to guide LLM responses
"""

import json
from typing import Union

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


class ChildrenCount(BaseStructuredOutput):
    male: int
    female: int

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return content.Schema(
            type=content.Type.OBJECT,
            enum=[],
            required=["a_chain_of_thought", "b_children"],
            properties={
                "a_chain_of_thought": content.Schema(
                    type=content.Type.STRING,
                ),
                "b_children": content.Schema(
                    type=content.Type.OBJECT,
                    enum=[],
                    required=["female", "male"],
                    properties={
                        "female": content.Schema(
                            type=content.Type.INTEGER,
                        ),
                        "male": content.Schema(
                            type=content.Type.INTEGER,
                        ),
                    },
                ),
            },
        )

    @classmethod
    def deserialize(cls, json_str: str, _engine: LLMEngine) -> "ChildrenCount":
        try:
            engine_output = json.loads(json_str)

            # Chain of thought is ommitted from the response, but it is still
            # returned by the LLM.
            # This line is just to show that the chain of thought is returned
            print(engine_output["a_chain_of_thought"])

            return ChildrenCount(
                male=engine_output["b_children"]["male"],
                female=engine_output["b_children"]["female"]
            )

        except (json.JSONDecodeError, KeyError) as e:
            raise DeserializationError(
                f"Failed to parse Gemini response: {e}")


class ChildrenNames(BaseStructuredOutput):
    names: list[str]

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return content.Schema(
            type=content.Type.OBJECT,
            enum=[],
            required=["a_chain_of_thought", "b_children_names"],
            properties={
                "a_chain_of_thought": content.Schema(
                    type=content.Type.STRING,
                ),
                "b_children_names": content.Schema(
                    type=content.Type.ARRAY,
                    items=content.Schema(
                        type=content.Type.STRING,
                    ),
                ),
            },
        )

    @classmethod
    def deserialize(cls, json_str: str, _engine: LLMEngine) -> "ChildrenNames":
        try:
            engine_output = json.loads(json_str)

            return ChildrenNames(
                names=engine_output["b_children_names"]
            )

        except (json.JSONDecodeError, KeyError) as e:
            raise DeserializationError(
                f"Failed to parse Gemini response: {e}")


system_prompt_template = """
Analyze the text below and respond on the question asked.

###TEXT START###
{text}
###TEXT END###
"""

text_for_analysis = """
The Harrington family, a bustling household of nine, is a marvel of organization
and energy. Dr. Leonard Harrington, a 42-year-old astrophysicist, spends his days
unraveling cosmic mysteries, while his wife, Eleanor, 39, a dedicated biomedical
researcher, seeks cures for rare diseases. Their seven children, each a star in
their own right, range in age from 3 to 21. Youngest of the brood is Felix, an
inquisitive kindergartener at 3, while his 6-year-old sister, Clara, just embarked
on her elementary school journey. Twins Jasper and Beatrice, both 10, are
sharp-witted schoolchildren with a penchant for robotics. Thirteen-year-old Adrian,
a middle schooler, aspires to be a marine biologist, while 17-year-old Miranda,
a high school senior, already interns at a genetics lab. The eldest, 21-year-old
Dominic, a physics major in college, follows in his father’s footsteps, pondering
the fabric of spacetime. Together, they form a microcosm of intellect, curiosity,
and boundless familial warmth, their home a symphony of science, study, and
laughter.
"""

question_1 = """
How many children does the Harrington family have?"

The output must follow the schema provided. Ensure that all fields are present and correctly formatted.
Schema Description:
- 'a_chain_of_thought': A detailed chain of thought process for the answer.
- 'b_children': The structure containing the number of children in the family. It consists of:
  - 'male': The number of male children.
  - 'female': The number of female children.
"""

question_2 = """
What names of the children are mentioned in the text?"

The output must follow the schema provided. Ensure that all fields are present and correctly formatted.
Schema Description:
- 'a_chain_of_thought': A detailed chain of thought process for the answer.
- 'b_children_names': A list of names of the children.
"""


class TextAnalyzer(GeminiChatModel):
    def __init__(self, model_name: str, prompt: str):
        model_config = ChatModelConfig(
            llm_model_name=model_name,
            temperature=1.0,
            max_tokens=8192,
            system_prompt=prompt
        )
        super().__init__(model_config)

    def analyze(self, prompt: str, response_class: BaseStructuredOutput) -> Union[BaseStructuredOutput, BaseResponseError]:
        try:
            model_response = self.generate_response(prompt, response_class)
        except UnexpectedFinishReason as e:
            return BaseResponseError(error=f"LLM engine responded with: {e}")
        except Exception:
            raise

        return model_response.response


if __name__ == "__main__":
    from bot.llm import initialize

    # Assumes that the module bot.settings is available
    # and `AGENT_ENGINE_API_KEY` is set in the environment variables
    initialize()

    # System prompt with the text to analyze will be applied to all requests
    system_prompt = system_prompt_template.format(text=text_for_analysis)
    analyzer = TextAnalyzer(
        model_name="gemini-2.0-flash", prompt=system_prompt)

    # The first response will be deserialized into a ChildrenCount object
    response = analyzer.analyze(question_1, ChildrenCount)
    print(f"Children count: {response.male} boys and {response.female} girls")

    # The second response will be deserialized into a ChildrenNames object
    response = analyzer.analyze(question_2, ChildrenNames)
    print(f"Children names: {', '.join(response.names)}")
