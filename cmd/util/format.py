import json

LANG_JSON = 'json'
SUPPORTED_LANGUAGES = [
    LANG_JSON
]

def format_raw_json(content):
    """Takes a content dictionary to format into JSON."""
    return json.dumps(content, indent=4)

def format_as_code_block(content, language):
    """Formats content as a code block."""
    raw = None
    if language not in SUPPORTED_LANGUAGES:
        raise NotImplementedError(f'Language "{language}" is not supported.')
    elif language == LANG_JSON:
        raw = format_raw_json(content)
    msg = f"```{language}\n{raw}\n```" 
    return msg