import os
import json
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
from tqdm import tqdm
import time
import argparse
import pandas as pd
# Load environment variables
load_dotenv()

DEFAULT_SYSTEM_PROMPT = """You are an expert data analyst and scenario generator.
Your task is to analyze the provided conversation history between a user and an assistant.
Based on the conversation, you must generate a scenario description object, specific information

IMPORTANT: The content of the values (scenario, user_description, expected_outcome) MUST BE in the SAME LANGUAGE as the input conversation. 
- If the conversation is in Vietnamese, the values must be in Vietnamese.
- If the conversation is in English, the values must be in English.
- The keys (scenario_id, scenario, user_description, expected_outcome) must remain in English.

The output must be a valid JSON object with the following structure:
{
  "scenario_id": "A unique identifier for the scenario (can be based on the topic)",
  "scenario": " A concise title or summary of the scenario (IN INPUT LANGUAGE)",
  "user_description": "A description of the user's role, intent, and persona in this conversation (IN INPUT LANGUAGE)",
  "expected_outcome": "The intended or successful outcome of the conversation (IN INPUT LANGUAGE)"
}
"""

def configure_genai():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables.")
        return False
    genai.configure(api_key=api_key)
    return True

def generate_scenario(model, conversation_history, system_prompt):
    prompt = f"""
    Please analyze the following conversation and generate a scenario according to the system instructions.

    Conversation History:
    {conversation_history}
    """
    
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        print(f"Error generating scenario: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Generate scenarios from conversation history CSV.")
    parser.add_argument("--input", "-i", type=str, default="secom_dt.csv")
    parser.add_argument("--output", "-o", type=str, default="scenarios_output.json")
    parser.add_argument("--system_prompt_file", "-s", type=str, default="system_prompt.txt")
    parser.add_argument("--model", type=str, default="gemini-2.0-flash-lite-001")

    args = parser.parse_args()
    
    # Validate input
    if not os.path.exists(args.input):
        print(f"Error: Input file not found at {args.input}")
        return

    # Load System Prompt
    system_instruction = DEFAULT_SYSTEM_PROMPT
    if args.system_prompt_file:
        if os.path.exists(args.system_prompt_file):
            with open(args.system_prompt_file, 'r', encoding='utf-8') as f:
                system_instruction = f.read()
            print(f"Loaded system prompt from {args.system_prompt_file}")
        else:
            print(f"Warning: System prompt file not found at {args.system_prompt_file}. Using default.")

    # Configure Gemini
    if not configure_genai():
        return

    # Initialize Model with JSON Schema enforcement
    generation_config = {
        "temperature": 0.8,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json",
    }
    
    model = genai.GenerativeModel(
        model_name=args.model,
        generation_config=generation_config,
        system_instruction=system_instruction
    )

    # Process CSV
    print(f"Reading input CSV: {args.input}")
    try:
        df = pd.read_csv(args.input, engine='python', on_bad_lines='warn')
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    if 'input' not in df.columns:
        print("Error format")
        return

    results = []
    
    print(f"Processing {len(df)} records...")
    for index, row in tqdm(df.iterrows(), total=df.shape[0]):
        try:
            convo_raw = row['input']
            # This cleans up any CSV parsing artifacts if needed
            if isinstance(convo_raw, str):
                try:
                    convo_obj = json.loads(convo_raw)
                    convo_text = json.dumps(convo_obj, indent=2)
                except json.JSONDecodeError:
                    convo_text = convo_raw
            else:
                convo_text = str(convo_raw)

            scenario = generate_scenario(model, convo_text, system_instruction)
            
            if scenario:
                # Retain ID from CSV if available
                if 'id' in row:
                    scenario['source_id'] = row['id']
                    # If the LLM didn't generate a scenario_id, use the source id
                    if not scenario.get('scenario_id'):
                        scenario['scenario_id'] = str(row['id'])
                
                results.append(scenario)
            
            # Simple rate limit prevention
            time.sleep(1.0) # increased sleep for free tier

        except Exception as e:
            print(f"Error processing row {index}: {e}")

    # Save Output
    print(f"Saving {len(results)} scenarios to {args.output}...")
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print("Successfully saved output.")
    except Exception as e:
        print(f"Error saving output: {e}")

if __name__ == "__main__":
    main()
