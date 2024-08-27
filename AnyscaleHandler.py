from openai import OpenAI

class anyscaleHandler:
    def __init__(self, api_key: str, base_url: str = "https://api.endpoints.anyscale.com/"):
        """
        Initialize the AnyScale API handler with the necessary API key and optional base URL.

        :param api_key: Your AnyScale API key.
        :param base_url: The base URL for the AnyScale API endpoints.
        """
        # Ensure base_url ends with a forward slash
        if not base_url.endswith("/"):
            base_url += "/"

        self.api_key = api_key
        self.base_url = base_url
        self.client = OpenAI(base_url=self.base_url + "v1", api_key=self.api_key)

    def anyscale_chat(self, conversation: str, model_id: str):
        """
        Handle a chat request using RayLLM models like Mistral

        :param conversation: The user's query or conversation string.
        :param model_id: The RayLLM model ID to use, e.g., 'mistralai/Mistral-7B-Instruct-v0.1'.
        :return: The response from the given model.
        """
        # Set up the initial system and user messages according to the new API requirements
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": conversation}
        ]

        # Use stream=False unless you specifically need streaming responses
        response = self.client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=0.01,
            stream=False  # Set to True if you need streaming
        )
        return response.choices[0].message.content if response.choices[0].message.content is not None else "No response generated."