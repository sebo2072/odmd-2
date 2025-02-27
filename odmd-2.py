import os
import functions_framework
from flask import Flask, jsonify, request, abort
from flask_cors import CORS, cross_origin 
from openai import OpenAI, OpenAIError
import jsonschema
from jsonschema import validate
import json
import re

# Initialize Flask app and Flask-CORS
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.config['CORS_HEADERS'] = 'Content-Type'


# Initialize OpenAI client
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)


def fix_json_response(latest_response):
    # Implement your logic to fix JSON response here
    # Example: basic check for common errors and fix them
    try:
        return json.loads(latest_response)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        # Add more robust JSON fixing logic here if needed
        return latest_response


def clean_response(latest_response):
    # Check if the response is wrapped in a code block and remove it
    latest_response = latest_response.strip()
    if latest_response.startswith("```") and latest_response.endswith("```"):
        latest_response = latest_response[3:-3].strip()

    # Remove the 'json' marker if it exists
    if latest_response.startswith("json"):
        latest_response = latest_response[4:].strip()

    # Clean the response (fix JSON issues)
    cleaned_response = fix_json_response(latest_response)

    return cleaned_response



# Assistant Function for the second API call
def transform_text(assistant_response, focus_keyword):
    assistant_id = "asst_nnxpQdzLJyjKRoBTIl9Cfpid"
    my_assistant_2 = client.beta.assistants.retrieve(assistant_id)
    #print("Retrieved Assistant 2 Details:")

    create_thread = client.beta.threads.create()
    user_prompt_2 = (
        f"Original Odia meta information and article elements text: {assistant_response}\n\n"
        f"Focus Keyword: {focus_keyword}\n\n"
        "Instructions:\n"
        "- Modify the supplied meta information and article elements 'assistant_response' using the optional 'focus_keyword' and strictly adhering to the 'JSON Output Object Template' below.\n"
        "- Use the 'focus_keyword' provided. If not provided, extract it from the first position of 'semantic_meta_keywords' in the 'assistant_response', translate it to English non-literally as per the 'Translation Criteria and Examples' in the Assistant Prompt, and use it accordingly.\n"
        "- Apply this logic in every field where the Focus Keyword is to be used.\n"
        "- Refer to the 'Instructions for transforming the input' and examples in the Assistant Prompt for detailed guidance.\n\n"
        "**JSON Output Object Template:**\n\n"
        "{\n"
        "  \"focus_keyword_odia\": \"As determined in Step 1: The Focus Keyword in Odia.\",  // String\n"
        "  \"focus_keyword_english\": \"As determined in Step 1: The Focus Keyword in English.\",  // String\n"
        "  \"meta_title\": \"Start with the value of focus_keyword_english followed by ': '. Then reproduce the Odia 'meta_title' exactly as received in the 'assistant_response', unchanged. Insert a separator '|'. Append a full English translation of the Odia meta title component, in high-quality Indian English news outlet style, *making sure the news keywords used in the source Odia meta title are reliably and accurately represented in the English translation*. Note: No character limit.\",  // String\n"
        "  \"meta_description\": \"Start with the value of focus_keyword_english followed by ': '. Then reproduce the Odia 'meta_description' exactly as received in the 'assistant_response', unchanged.\",  // String\n"
        "  \"headline\": \"Start with the value of focus_keyword_english followed by ': '. Then reproduce the Odia 'headline' exactly as received in the 'assistant_response', unchanged.\",  // String\n"
        "  \"semantic_meta_keywords\": [  // Array of Strings\n"
        "    \"The value of Focus Keyword in Odia\",\n"
        "    \"List of additional Odia keywords\",\n"
        "    \"The value of Focus Keyword in English\",\n"
        "    \"Non-literal English translations of the Odia keywords\"\n"
        "  ],\n"
        "  \"article_summary\": \"Reproduce the 'article_summary' exactly as received in the 'assistant_response', unchanged. No English text or alphabet should be included in this part.\",  // String\n"
        "  \"five_key_points\": [  // Array of Strings\n"
        "    \"Reproduce the 'five_key_points' exactly as received in the 'assistant_response', unchanged. No English text or alphabet should be included in this part.\"\n"
        "  ]\n"
        "}\n\n"
        "Other Instructions:\n"
        "- Do not include any notation characters such as '[...]' or '<...>' in the final output.\n"
        "- Strictly follow the JSON Output Structure provided above.\n"
        "- Stop generating when the JSON template is fully completed. Do not write outside the JSON template.\n"
        "- Write only using Odia and English language and alphabets as instructed. Do not use any other language.\n"
    )

    create_thread_message = client.beta.threads.messages.create(
        thread_id=create_thread.id,
        role="user",
        content=user_prompt_2
    )

    create_run = client.beta.threads.runs.create(
        thread_id=create_thread.id,
        assistant_id=my_assistant_2.id,
        instructions=(
            "Ensure the response appropriately modified as per Assistant Instructions and the 'focus_keyword' logic is applied as intended "
            "Follow the JSON format template strictly as outlined in the Assistant and User prompts."
        )
    )

    while create_run.status in ["queued", "in_progress"]:
        keep_retrieving_run = client.beta.threads.runs.retrieve(
            thread_id=create_thread.id,
            run_id=create_run.id
        )

        if keep_retrieving_run.status == "completed":
            all_messages = client.beta.threads.messages.list(
                thread_id=create_thread.id
            )

            assistant_2_response = None
            for message in all_messages.data:
                if message.role == "assistant":
                    assistant_2_response = message.content[0].text.value
                    break

            print("Raw Assistant_2 Response:", assistant_2_response)

            return assistant_2_response

# Integrate the transformation into the main function
@app.route("/")
@cross_origin()
@functions_framework.http
def metadata_odia(request):
    try:
        expected_key = os.environ.get("ACCESS_KEY")
        request_key = request.args.get('key')

        if not request_key or request_key != expected_key:
            abort(403)  # Abort if the key doesn't match

        request_json = request.get_json()
        article_text = request_json.get('articleText', '')
        print(f"article text {article_text}")
        special_instructions = request_json.get('specialInstructions', '')

        # Directly extract 'focus_keyword' from 'specialInstructions'
        focus_keyword = special_instructions.get('focus_keyword', '')

        # Print statement to check if 'focus_keyword' is available
        if focus_keyword:
            print(f"Focus keyword is available: {focus_keyword}")
        else:
            print("Focus keyword is not available in the request.")

        assistant_id = "asst_atTgMWrNdNOz2TvTC5mZQCTd"
        my_assistant = client.beta.assistants.retrieve(assistant_id)
        #print("Retrieved Assistant 1 Details:")

        my_thread = client.beta.threads.create()

        user_prompt = (
            f"Article text: {article_text}\n\n"
            f"Special Instructions: {special_instructions}\n\n"
            "As a journalist specializing in SEO-optimized high-quality Indian Odia language news article writing, your task is to generate structured and SEO-optimized Indian Odia language meta-information and article elements exclusively based on the provided article text (`sanitized_article_text`) following special instructions (`special_instructions`) embedded in the User Message. Use Indian Odia language and alphabets only, strictly obeying the 'Linguistic Style Guide' below.\n\n"
            "A. **Linguistic Style Guide**\n"
            "1. Use nouns, pronouns, adjectives, adverbs, modifiers, syntaxes, and sentence patterns learned from the source 'article_text' to maintain grammatical and factual alignment. *Do not use prior knowledge.*\n"
            "2. Use newsy, matter-of-fact, urban, conversational, natural, and simple writing style as used by top Odia news outlets such as Sambad.\n"
            "3. Write in direct, short, compact, punchy sentences. Avoid passive voice sentences.\n"
            "4. Include names of people, places, things, events, technologies, historical facts, etc. in your output. For articles about personalities, mandatorily include the personality's name in headline, meta title, and meta description.\n"
            "5. Do not create new Odia words. Do not use rarely used, old, or awkward-sounding Odia words.\n"
            "6. Fully align with the `article_text` and *ensure correct gender identification and treatment for all references throughout the generated output*.\n\n"
            "B. **Steps Sequence to Carry Out the Task**\n"
            "1. Scan and analyze 'special_instructions' and 'article_text'.\n"
            "2. From 'special_instructions', mandatorily use 'Angle' key value to set '*story angle*' for your task and 'language style' key value to set *linguistic style* of your task. If missing, use a neutral tone and focus.\n"
            "3. Identify 'semantic_meta_keywords' first, encompassing focus, long-tail, topical, and generic keywords. Prioritize generating contextual keyphrases as long-tail keywords. You will blend these keywords into other meta information or article elements in the subsequent steps.\n"
            "4. Following the *Linguistic Style Guide*, generate 'article_summary', 'headline', 'meta_title', a longish 'meta_description' of minimum 200 characters, and descriptive 'five_key_points' of the article. Use important keywords for maximum SEO impact.\n"
            "5. Review: Before generating output, review alignment with `article_text` and `special_instructions`. Replace rarely used words and awkward syntax with simple explanations before generating the final output.\n"
            "6. Strictly follow the *JSON Output Template and instructions* to produce the JSON output.\n\n"
            "C. **JSON Output Template and Instructions**\n"
            "1. Text within '[...]' brackets are for instruction purposes only; do not include them in the output.\n"
            "2. Replace instructional text with content generated from 'article_text', ensuring it is aligned, relevant, and factually correct.\n"
            "3. Generate 'key' element names in English and 'value' elements in Odia using the Odia script. Ensure the text is written in high-quality Odia news outlet style. *Do not include any instructional text in the output*.\n"
            "4. Ensure all 'key: value' pair elements defined in the JSON Output Template are included in your output.\n"
            "5. *Do not write outside the JSON template* and *do not alter the JSON output structure*.\n"
            "6. *Do not include any instructional language IDs such as 'guj' or other language cues in the output.*\n\n"
            "*JSON Output Template:*\n"
            "{\n"
            "    \"semantic_meta_keywords\": \"[*Data type: Array.* Set the focus as 'story angle' value from 'specialInstructions'. Generate an array of Odia news keyphrases and keywords contextually relevant to the article's topic for SEO. Focus on generating key phrases representing the topic through focus keyword, other news keywords, long-tail keywords, and generic keywords. Place the focus keyword at the beginning.]\", // Array of strings\n"
            "    \"article_summary\": \"[Set the focus as 'story angle' value from 'specialInstructions'. Provide a comprehensive, longish summary of the article in high-quality Odia news outlet style, following the *cardinal 5W1H rule of writing news content*, focusing on key facts and compelling enough to encourage further reading.]\",\n"
            "    \"headline\": \"[Set the focus as 'story angle' value from 'specialInstructions'. Write a clear and crisp headline in high-quality Odia news outlet style, focusing on the latest developments with a specific focus from 'special_instructions' if available. Must include two top keywords.]\",\n"
            "    \"five_key_points\": \"[*Data type: Array.* Set the focus as 'story angle' value from 'specialInstructions'. Generate an array of five longish, descriptive key points including key facts, statements, and interpretations from the article in high-quality Odia news outlet style, *following the 5W1H rule of news writing*. *Items must be comma-separated inside the array; do not create a numbered list.*]\", // Array of strings\n"
            "    \"meta_description\": \"[Set the focus as 'story angle' value from 'specialInstructions'. Craft a compelling and SEO-optimized, descriptive meta description of minimum 200 characters and maximum 220 characters in Odia, summarizing the article's key facts, interpretations, and appeal. Include the focus keyword and at least three top keywords from the previous steps, including the ones in the headline. Write in high-quality Odia news outlet style.]\",\n"
            "    \"meta_title\": \"[Set the focus as 'story angle' value from 'specialInstructions'. Generate a newsy and longish meta title recognizing `special_instructions` and encapsulating the article's main topic, including three major keywords in order of priority, including the ones used in the headline. The meta title can be longer than 120 characters. Write in high-quality Odia news outlet style.]\"\n"
            "}\n"
            "Stop generating when the JSON template is fully completed. Do not write outside the JSON template.\n"
            "Do not include '[..]' brackets in your output unless you have to define an array."
        )


        my_thread_message = client.beta.threads.messages.create(
            thread_id=my_thread.id,
            role="user",
            content=user_prompt
        )

        my_run = client.beta.threads.runs.create(
            thread_id=my_thread.id,
            assistant_id=my_assistant.id,
            instructions=(
                "Adhere to the default assistant instructions and the JSON output format."
            )
        )

        while my_run.status in ["queued", "in_progress"]:
            keep_retrieving_run = client.beta.threads.runs.retrieve(
                thread_id=my_thread.id,
                run_id=my_run.id
            )

            if keep_retrieving_run.status == "completed":
                all_messages = client.beta.threads.messages.list(
                    thread_id=my_thread.id
                )

                assistant_response = None
                for message in all_messages.data:
                    if message.role == "assistant":
                        assistant_response = message.content[0].text.value
                        break

                print("Raw Assistant 1 Response:", assistant_response)

                # Transform the assistant response using GPT-4o
                transformed_response = transform_text(assistant_response, focus_keyword)

                #print("Assistant_2 Response before JSON validation:", transformed_response)

                # Clean the JSON response
                cleaned_json = clean_response(transformed_response)

                # Remove 'focus_keyword_odia' and 'focus_keyword_english' from cleaned_json
                if isinstance(cleaned_json, dict):
                    cleaned_json.pop('focus_keyword_odia', None)
                    cleaned_json.pop('focus_keyword_english', None)

                print("Cleaned JSON:", cleaned_json)


                # Build the final response
                response = jsonify({
                    "task_response": cleaned_json
                })
                #response.headers['Access-Control-Allow-Origin'] = '*'
               
                return response


    except Exception as e:
        print(f"An error occurred: {e}")
        # Optional: Log the request details if needed for debugging
        print(f"Request Data: {request.get_json()}")
        abort(500, description=str(e))