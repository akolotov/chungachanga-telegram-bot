from telegram.helpers import escape_markdown

def format_vocabulary(vocabulary):
    """
    Format the vocabulary items for Markdown V2 parsing.

    Args:
        vocabulary (List[VocabularyItem]): List of vocabulary items.

    Returns:
        str: Formatted vocabulary string for Markdown V2 parsing.
    """
    vocabulary_items = []
    for item in vocabulary:
        escaped_word = escape_markdown(item.word, version=2)
        escaped_translation = escape_markdown(item.translation, version=2)
        vocabulary_items.append(f"{escaped_word} \\(_{escaped_translation}_\\)")
    
    return ",\n".join(vocabulary_items)

def trim_message(message, max_length=4096):
    """
    Trim a message to ensure it doesn't exceed the maximum length.

    Args:
        message (str): The message to trim.
        max_length (int): The maximum allowed length of the message. Default is 4096 (Telegram's limit).

    Returns:
        str: The trimmed message.
    """
    if len(message) > max_length:
        return message[:max_length-3] + "..."
    return message
