"""
LLM utilities module for Telegram Summarizer.
Contains functions for interacting with LLM APIs and processing responses.
"""

import time
import litellm
from loguru import logger

def format_messages_for_prompt(messages, system_prompt, user_prompt, additional_instructions=""):
    """
    Format messages for the LLM prompt.
    
    Args:
        messages (list): List of message dictionaries
        system_prompt (str): System prompt for the LLM
        user_prompt (str): User prompt for the LLM
        additional_instructions (str, optional): Additional instructions for the LLM
        
    Returns:
        list: Formatted messages for the LLM
    """
    # Create the full prompt
    full_prompt = []
    
    # Add system message
    full_prompt.append({
        "role": "system",
        "content": system_prompt
    })
    
    # Add user message with instructions and context
    user_content = user_prompt
    
    # Add additional instructions if provided
    if additional_instructions:
        user_content += f"\n\nAdditional instructions: {additional_instructions}"
    
    # Add message count information
    user_content += f"\n\nYou are analyzing {len(messages)} messages."
    
    # Add the actual messages
    user_content += "\n\nHere are the messages:\n\n"
    for msg in messages:
        user_content += f"{msg['date']}:{msg['sender']}:{msg['text']}\n"
    
    full_prompt.append({
        "role": "user",
        "content": user_content
    })
    
    return full_prompt

def call_llm(full_prompt, provider, model, api_key, mock=False):
    """
    Call the LLM API to generate a summary.
    
    Args:
        full_prompt (list): Formatted messages for the LLM
        provider (str): The LLM provider
        model (str): The LLM model
        api_key (str): The LLM API key
        mock (bool, optional): Whether to use a mock response
        
    Returns:
        tuple: (response, time_taken, prompt_tokens, completion_tokens, total_tokens, raw_cost)
    """
    # Start time for estimation
    start_time = time.time()
    
    # Calculate approximate token count for input
    total_chars = sum(len(msg.get('content', '')) for msg in full_prompt)
    approx_tokens = total_chars / 4  # Rough estimate: ~4 chars per token
    
    logger.debug(f"Sending prompt to LLM: {len(full_prompt)} messages, ~{total_chars:,} characters, ~{int(approx_tokens):,} tokens")
    
    # Log the full prompt structure
    for i, msg in enumerate(full_prompt):
        # Replace newlines with escape sequences
        content = msg['content'].replace("\n", "\\n")
        content_preview = content[:1000] + "..." if len(content) > 1000 else content
        logger.debug(f"Prompt message {i+1} ({msg['role']}): {content_preview}")
    
    # Get response from LLM or use mock
    try:
        if mock:
            # Create a mock response content
            mock_content = f"""
This is a mock response. Here is a summary of the conversations from the Telegram chats.

The discussions over the past few days covered several key topics:

1. **Project Updates**:
   - Team completed the backend API integration
   - Frontend UI redesign is 75% complete
   - QA found 3 critical bugs that need to be addressed before release
...
"""
            # Create a mock response object
            response = type('obj', (object,), {
                'choices': [
                    type('obj', (object,), {
                        'message': type('obj', (object,), {
                            'content': mock_content
                        })
                    })
                ],
                '_hidden_params': {
                    'prompt_tokens': int(approx_tokens),
                    'completion_tokens': int(len(mock_content) / 2.5),
                    'total_tokens': int(approx_tokens) + int(len(mock_content) / 2.5)
                }
            })
        else:
            # Set up LiteLLM
            litellm.api_key = api_key
            
            # Call the LLM API
            response = litellm.completion(
                model=f"{provider}/{model}",
                messages=full_prompt,
                temperature=0.7,
                max_tokens=1500
            )
        
        # Calculate time taken
        time_taken = time.time() - start_time
        
        # Extract token usage and cost
        if mock:
            # Simulate token counts based on string length when using mock
            # Rough estimate: ~4 chars per token for prompt, ~2.5 chars per token for completion
            prompt_chars = sum(len(msg.get('content', '')) for msg in full_prompt)
            completion_chars = len(response.choices[0].message.content)
            
            prompt_tokens = int(prompt_chars / 4)  # Simulate prompt tokens
            completion_tokens = int(completion_chars / 2.5)  # Simulate completion tokens
            total_tokens = prompt_tokens + completion_tokens
            
            # Simulate cost based on token count (using typical GPT-4 rates)
            prompt_cost = prompt_tokens * 0.00001  # $0.01 per 1000 tokens
            completion_cost = completion_tokens * 0.00003  # $0.03 per 1000 tokens
            raw_cost = prompt_cost + completion_cost
        else:
            # Extract token usage from the response object's usage field
            if hasattr(response, 'usage') and response.usage:
                prompt_tokens = getattr(response.usage, 'prompt_tokens', 'N/A')
                completion_tokens = getattr(response.usage, 'completion_tokens', 'N/A')
                total_tokens = getattr(response.usage, 'total_tokens', 'N/A')
            else:
                # Fallback to _hidden_params if usage is not available
                prompt_tokens = response._hidden_params.get('prompt_tokens', 'N/A')
                completion_tokens = response._hidden_params.get('completion_tokens', 'N/A')
                total_tokens = response._hidden_params.get('total_tokens', 'N/A')
            
            # Calculate cost based on token count (using typical GPT-4 rates)
            # This is a simplified calculation and should be adjusted based on the actual model used
            if isinstance(prompt_tokens, (int, float)) and isinstance(completion_tokens, (int, float)):
                prompt_cost = prompt_tokens * 0.00001  # $0.01 per 1000 tokens
                completion_cost = completion_tokens * 0.00003  # $0.03 per 1000 tokens
                raw_cost = prompt_cost + completion_cost
            else:
                raw_cost = 'N/A'
        
        # Format the cost with 5 decimal places
        formatted_cost = f"{float(raw_cost):.10f}" if isinstance(raw_cost, (int, float)) else 'N/A'
        
        logger.debug(f"Token usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")
        logger.debug(f"Cost: ${formatted_cost}")
        
        # Log the summary with escaped newlines
        summary_content = response.choices[0].message.content.replace("\n", "\\n")
        logger.debug(f"AI Response: {summary_content}")
        
        return response, time_taken, prompt_tokens, completion_tokens, total_tokens, raw_cost
        
    except Exception as e:
        logger.error(f"Error calling LLM API: {str(e)}")
        raise
