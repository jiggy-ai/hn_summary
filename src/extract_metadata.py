import json
from typing import Dict
from typing import List
import openai


from tenacity import retry, wait_random_exponential, stop_after_attempt



@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(5))
def get_chat_completion(
    messages,
    model="gpt-3.5-turbo",  # use "gpt-4" for better results
):
    """
    Generate a chat completion using OpenAI's chat completion API.

    Args:
        messages: The list of messages in the chat history.
        model: The name of the model to use for the completion. Default is gpt-3.5-turbo, which is a fast, cheap and versatile model. Use gpt-4 for higher quality but slower results.

    Returns:
        A string containing the chat completion.

    Raises:
        Exception: If the OpenAI API call fails.
    """
    # call the OpenAI chat completion API with the given messages
    response = openai.ChatCompletion.create(
        model=model,
        temperature=0,
        messages=messages,
    )

    choices = response["choices"]  # type: ignore
    completion = choices[0].message.content.strip()
    print(f"Completion: {completion}")
    return completion



def extract_metadata_from_document(text: str) -> Dict[str, str]:
    # This prompt is just an example, change it to fit your use case
    messages = [
        {
            "role": "system",
            "content": f"""
            Given an article from the web below, try to extract the following metadata:
            - created_at: ISO date string or None
            - author: string or None

            Respond with a JSON containing the extracted metadata in key value pairs. If you don't find a metadata field use None.
            """,
        },        
        {"role": "user", "content": text},
    ]
    print(text)
    completion = get_chat_completion(
        messages, "gpt-3.5-turbo",
    )  # TODO: change to your preferred model name

    print(f"completion: {completion}")

    try:
        metadata = json.loads(completion)
    except:
        metadata = {}

    return metadata
