import os
from dotenv import load_dotenv
import chainlit as cl
import openai
import asyncio
import json
from datetime import datetime
from prompts import ASSESSMENT_PROMPT, SYSTEM_PROMPT
from student_record import read_student_record, write_student_record, format_student_record, parse_student_record
from langsmith import traceable

# Load environment variables
load_dotenv()

configurations = {
    "mistral_7B_instruct": {
        "endpoint_url": os.getenv("MISTRAL_7B_INSTRUCT_ENDPOINT"),
        "api_key": os.getenv("RUNPOD_API_KEY"),
        "model": "mistralai/Mistral-7B-Instruct-v0.2"
    },
    "mistral_7B": {
        "endpoint_url": os.getenv("MISTRAL_7B_ENDPOINT"),
        "api_key": os.getenv("RUNPOD_API_KEY"),
        "model": "mistralai/Mistral-7B-v0.1"
    },
    "openai_gpt-4": {
        "endpoint_url": os.getenv("OPENAI_ENDPOINT"),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "model": "gpt-4"
    }
}

# Choose configuration
config_key = "openai_gpt-4"

# Get selected configuration
config = configurations[config_key]

# Initialize the OpenAI async client
client = openai.AsyncClient(api_key=config["api_key"], base_url=config["endpoint_url"])

gen_kwargs = {
    "model": config["model"],
    "temperature": 0.3,
    "max_tokens": 500
}

@traceable
def get_latest_user_message(message_history):
    # Iterate through the message history in reverse to find the last user message
    for message in reversed(message_history):
        if message['role'] == 'user':
            return message['content']
    return None

@traceable
def get_latest_assistant_message(message_history):
    # Iterate through the message history in reverse to find the last user message
    for message in reversed(message_history):
        if message['role'] == 'assistant':
            return message['content']
    return None

@traceable
def parse_assessment_output(output):
    try:
        parsed_output = json.loads(output)
        engagement = parsed_output.get("engagement", [])
        knowledge_updates = parsed_output.get("knowledge", [])
        return engagement, knowledge_updates
    except json.JSONDecodeError as e:
        print("Failed to parse assessment output:", e)
        return [], []

@traceable
async def assess_message(message_history):
    file_path = "student_record.md"
    markdown_content = read_student_record(file_path)
    parsed_record = parse_student_record(markdown_content)

    latest_message = get_latest_user_message(message_history)
    latest_assistant_message = get_latest_assistant_message(message_history)

    # Remove the original prompt from the message history for assessment
    filtered_history = [msg for msg in message_history if msg['role'] != 'system']

    # Convert message history, alerts, and knowledge to strings
    history_str = json.dumps(filtered_history, indent=4)
    engagement_str = json.dumps(parsed_record.get("engagement", []), indent=4)
    knowledge_str = json.dumps(parsed_record.get("knowledge", {}), indent=4)
    

    # Generate the assessment prompt
    filled_prompt = ASSESSMENT_PROMPT.format(
        latest_message=latest_message,
        history=history_str,
        existing_engagement=engagement_str,
        existing_knowledge=knowledge_str,
    )
    print("Filled prompt: \n\n", filled_prompt)

    response = await client.chat.completions.create(messages=[{"role": "system", "content": filled_prompt}], **gen_kwargs)

    assessment_output = response.choices[0].message.content.strip()
    print("Assessment Output: \n\n", assessment_output)

    # Parse the assessment output
    engagement, knowledge_updates = parse_assessment_output(assessment_output)

    # Update the student record with the new alerts and knowledge updates
    parsed_record["Engagement"].extend(engagement)
    for update in knowledge_updates:
        topic = update["topic"]
        summary = update.get("summary", "")
        score = update.get("score", "") 
        parsed_record["Knowledge"][topic] = f"score: {score} summary: {summary}"

    # Format the updated record and write it back to the file
    updated_content = format_student_record(
        parsed_record["Student Information"],
        parsed_record["Engagement"],
        parsed_record["Knowledge"]
    )
    write_student_record(file_path, updated_content)
    return {"role": "assistant", "content": latest_assistant_message}

output = {}
@traceable
async def handle_input_output(input, message_history):
    response_message = cl.Message(content="")
    await response_message.send()

    stream = await client.chat.completions.create(messages=message_history, stream=True, **gen_kwargs)
    async for part in stream:
        if token := part.choices[0].delta.content or "":
            await response_message.stream_token(token)

    message_history.append({"role": "assistant", "content": response_message.content})
    cl.user_session.set("message_history", message_history)
    await response_message.update()
    global output
    output = {"output": [{"role": "assistant", "content": response_message.content}]}
    log_input_output([input])

@traceable
# This is a bit cludgy, but it's for allowing me to quickly add the input to the output to the dataset via the UI
def log_input_output(input):
    global output
    return output

@traceable
@cl.on_message
async def on_message(message: cl.Message):
    message_history = cl.user_session.get("message_history", [])
    if not message_history or message_history[0].get("role") != "system":
        system_prompt_content = SYSTEM_PROMPT
        message_history.insert(0, {"role": "system", "content": system_prompt_content})

    message_history.append({"role": "user", "content": message.content})
    asyncio.create_task(assess_message(message_history))
    await handle_input_output({"role": "user", "content": message.content}, message_history)


if __name__ == "__main__":
    cl.main()