import json
import sys
import argparse
from typing import List, Dict, Any

def load_json_data(file_path: str) -> List[Dict[str, Any]]:
	"""
	Load data from a JSON file.

	:param file_path: Path to the JSON file.
	:return: List of dictionaries representing the loaded data.
	"""
	try:
		with open(file_path, 'r', encoding='utf-8') as file:
			data = json.load(file)
		return data
	except Exception as e:
		print(f"Error loading JSON data: {e}", file=sys.stderr)
		return []

def save_json_data(data: List[Dict[str, Any]], file_path: str):
	"""
	Save data to a JSON file.

	:param data: Data to be saved.
	:param file_path: Path to the JSON file where data will be saved.
	"""
	try:
		with open(file_path, 'w', encoding='utf-8') as file:
			json.dump(data, file, ensure_ascii=False, indent=4)
	except Exception as e:
		print(f"Error saving JSON data: {e}")

def parse_arguments():
	"""
	Parse command-line arguments.

	:return: Namespace object with arguments
	"""
	parser = argparse.ArgumentParser()
	parser.add_argument('--given_model', type=str, required=True,
						choices=['GPT-4','Llama3','Claude3'])
	parser.add_argument('--true_model', type=str, required=True,
						choices=['GPT-4','Llama3','Claude3'])
	parser.add_argument('--openai_key', type=str,
						help='OpenAI API key')
	parser.add_argument('--anyscale_key', type=str,
						help='Anyscale API key')
	parser.add_argument('--anthropic_key', type=str,
						help='Anthropic API key')
	return parser.parse_args()