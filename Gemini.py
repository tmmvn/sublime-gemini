import sublime
import sublime_plugin
import requests
import json
import os

# File to store the API key
API_KEY_FILE = "gemini_api_key.txt"
GEN_PROMPT = ""
DEBUG_PROMPT = ""
SUGGESTION_PROMPT = ""


def get_api_key(view):
    """Gets the API key from the file, prompting the user if not found."""

    api_key_path = os.path.join(sublime.cache_path(), "Gemini.cache", API_KEY_FILE)
    try:
        with open(api_key_path, "r") as f:
            api_key = f.read().strip()
            if api_key:
                return api_key
            else:
                raise FileNotFoundError  # Treat empty file as not found
    except FileNotFoundError:
        # Prompt user for API key
        def on_done(input_key):
            if input_key:
                with open(api_key_path, "w") as f:
                    f.write(input_key)
                sublime.message_dialog("API key saved successfully!")
            else:
                sublime.error_message("API key not entered. Please try again.")
        view.window().show_input_panel(
            "Enter your Gemini API key:", "", on_done, None, None
        )
        return None  # Return None for now, key will be available on next run


def send_prompt_to_gemini(prompt, api_key):
    """Sends a prompt to Gemini 1.5 Flash and returns the response."""

    api_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={}".format(api_key)
    headers = {
        "Content-Type": "application/json",
    }
    data = {
        "contents": [{
            "parts":[
                {"text": prompt}
            ]
        }],
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_ONLY_HIGH"
            }
        ],
        "generationConfig": {
            "temperature": 1.0,
            "maxOutputTokens": 800,
            "topP": 0.8,
            "topK": 10
        }
    }
    response = requests.post(api_endpoint, headers=headers, json=data)
    if response.status_code == 200:
        try:
            response_json = response.json()
            return response_json["predictions"][0]["content"]
        except (KeyError, IndexError) as e:
            print("Error extracting response: {}".format(e))
            return None
    else:
        print("Error: {} - {}".format(response.status_code, response.text))
        return None


class SendSelectionToGeminiCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        selection = self.view.get_selection()
        if selection.empty():
            sublime.error_message("No text selected.")
            return
        selected_text = self.view.substr(selection)
        api_key = get_api_key(self.view)
        if api_key:
            response = send_prompt_to_gemini(selected_text, api_key)
            if response:
                new_view = self.view.window().new_file()
                new_view.run_command("insert", {"characters": response})
