import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telethon import TelegramClient
import litellm

# Load environment variables
load_dotenv(override=True)

# Telegram configuration
api_id = os.getenv('TELEGRAM_API_ID')
api_hash = os.getenv('TELEGRAM_API_HASH')
channel_id_1 = str(os.getenv('CHANNEL_ID_1',''))
channel_id_1_days_to_fetch = int(os.getenv('CHANNEL_ID_1_DAYS_TO_FETCH', 3))
channel_id_2 = str(os.getenv('CHANNEL_ID_2',''))
channel_id_2_days_to_fetch = int(os.getenv('CHANNEL_ID_2_DAYS_TO_FETCH', 3))
response_channel_id = str(os.getenv('RESPONSE_CHANNEL_ID', ''))
prompt_text = os.getenv('PROMPT_TEXT')

# LLM configuration
llm_provider = os.getenv('LLM_PROVIDER')
llm_model = os.getenv('LLM_MODEL')
llm_api_key = os.getenv('LLM_API_KEY')

# Initialize Telegram client
client = TelegramClient('session_name', api_id, api_hash)

async def fetch_messages(channel_id, days_to_fetch=7):
    print(f"Fetching messages from channel ID: {channel_id}")
    messages = []
    async for message in client.iter_messages(channel_id, offset_date=datetime.now() - timedelta(days=days_to_fetch), reverse=True):
        if message.is_group:
            sender = await message.get_sender()
            sender_name = sender.first_name if sender else "Unknown"
            messages.append(f"{message.date}: {sender_name}: {message.text}")
            # print(f" - {message.date}: {sender_name}: {message.text}"[:100])
        else:
            messages.append(f"{message.date}: {message.text}")
            # print(f" - {message.date}: {message.text}"[:100])
    print(f"Fetched {len(messages)} messages from channel ID: {channel_id}")
    return "\n".join(messages)

async def main():
    print("Starting Telegram client...")
    await client.start()
    print("Telegram client started.")

    # Prepare the prompt 1
    system_prompt = os.getenv('PROMPT_SYSTEM', 'You are a helpful assistant.') + f". Today is {datetime.now().strftime('%Y-%m-%d')}."
    full_prompt = [
        {'role': 'system', 'content': system_prompt },
    ]
    # Fetch messages from both channels
    print("Fetching messages from both channels...")
    if channel_id_1:
        for channel in [int(c) for c in channel_id_1.split(',') if c]:
            messages = await fetch_messages(channel, channel_id_1_days_to_fetch)
            full_prompt.append({'role': 'user', 'content': messages})
    if channel_id_2:
        for channel in [int(c) for c in channel_id_2.split(',') if c]:
            messages = await fetch_messages(channel, channel_id_2_days_to_fetch)
            full_prompt.append({'role': 'user', 'content': messages})
            
    # Prepare the prompt 2
    print("Preparing the prompt...")
    full_prompt += [
        {'role': 'user', 'content': prompt_text}
    ]

    # Initialize LiteLLM
    print(f"Initializing LiteLLM with provider: {llm_provider}, model: {llm_model}")
    # llm = LiteLLM(api_key=llm_api_key)
    litellm.api_key = llm_api_key
    
    # Get response from LLM
    print("Sending prompt to LLM and awaiting response...")

    response = litellm.completion(messages=full_prompt, model=f"{llm_provider}/{llm_model}")
    print("Received response from LLM.")
    # print(response)

    # Send response to the specified Telegram channel
    print(f"Sending response to channel ID: {response_channel_id}")
    for response_channel in response_channel_id.split(','):
        if response_channel:
            await client.send_message(int(response_channel_id), response.choices[0].message.content)
            
    print("Response sent successfully.")
    print("Completion Cost: $", response._hidden_params["response_cost"])

# Run the script
with client:
    client.loop.run_until_complete(main())
