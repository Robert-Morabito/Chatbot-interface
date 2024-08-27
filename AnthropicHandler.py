from anthropic import Anthropic

class anthropicHandler:
	def __init__(self, api_key:str):
		"""
		Initialize the Anthropic handler with the necessary API key

		:param api_key: Your Anthropic API key
		"""
		self.api_key = api_key
		self.client = Anthropic(api_key=self.api_key)

	def claude_chat(self, conversation: str, model: str):
		"""
		Handle a chat request for Claude versions

		:param conversation: The conversation history as a single string. Includes system instructions.
		:param model: The chat completion model to use.
		:return: The response from the given model.
		"""
		response = self.client.messages.create(
			model=model,
			max_tokens=800,
			messages=[{"role": "user", "content": conversation}]
		)
		return response.content[0].text