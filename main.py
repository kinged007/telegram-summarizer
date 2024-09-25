import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telethon import TelegramClient
from litellm import LiteLLM

# Load environment variables
load_dotenv()

# Telegram configuration
api_id = os.getenv('TELEGRAM_API_ID')
api_hash = os.getenv('TELEGRAM_API_HASH')
phone = os.getenv('TELEGRAM_PHONE')
channel_id_1 = int(os.getenv('CHANNEL_ID_1'))
channel_id_2 = int(os.getenv('CHANNEL_ID_2'))
response_channel_id = int(os.getenv('RESPONSE_CHANNEL_ID'))
prompt_text = os.getenv('PROMPT_TEXT')

# LLM configuration
llm_provider = os.getenv('LLM_PROVIDER')
llm_model = os.getenv('LLM_MODEL')
llm_api_key = os.getenv('LLM_API_KEY')

# Initialize Telegram client
client = TelegramClient('session_name', api_id, api_hash)

async def fetch_messages(channel_id):
    print(f"Fetching messages from channel ID: {channel_id}")
    messages = []
    async for message in client.iter_messages(channel_id, offset_date=datetime.now() - timedelta(days=7), reverse=True):
        messages.append(f"{message.date}: {message.post_author}: {message.text}")
        print(f" - {message.date}: {message.post_author}: {message.text}")
    print(f"Fetched {len(messages)} messages from channel ID: {channel_id}")
    return "\n".join(messages)

async def main():
    print("Starting Telegram client...")
    await client.start(phone)
    print("Telegram client started.")

    # Fetch messages from both channels
    print("Fetching messages from both channels...")
    messages_1 = await fetch_messages(channel_id_1)
    messages_2 = await fetch_messages(channel_id_2)
    return
    # Prepare the prompt
    print("Preparing the prompt...")
    full_prompt = f"{messages_1}\n\n{messages_2}\n\n{prompt_text}"

    # Initialize LiteLLM
    print(f"Initializing LiteLLM with provider: {llm_provider}, model: {llm_model}")
    llm = LiteLLM(provider=llm_provider, model=llm_model, api_key=llm_api_key)

    # Get response from LLM
    print("Sending prompt to LLM and awaiting response...")
    response = llm.complete(full_prompt)
    print("Received response from LLM.")

    # Send response to the specified Telegram channel
    print(f"Sending response to channel ID: {response_channel_id}")
    await client.send_message(response_channel_id, response)
    print("Response sent successfully.")

# Run the script
with client:
    client.loop.run_until_complete(main())
