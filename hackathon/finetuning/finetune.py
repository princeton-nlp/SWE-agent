import json
import os

# Currently, this file just contains a function that will create training dataset to finetune on.
# Generated file from `create_training_data` can be uploaded to OpenPipe console to finetune the model.
class Finetune():
    def __init__(self):
        # Sample of how to instantiate openpipe client
        # Make sure you have the OPENAI_API_KEY and OPENPIPE_API_KEY set in your environment
        '''
        llmClient = OpenAI(
            api_key = os.getenv("OPENAI_API_KEY"),
            openpipe = {
                "api_key": os.getenv("OPENPIPE_API_KEY"),
            }     
        )
        '''

    def transform_single_to_openai_chat_format(self, one_json_obj, model = "gpt-4o-mini"):
        return {
            # only required field
            "messages" : [
                {
                    "role": "system",
                    # Can add additional context / summarized output here.
                    # As per OpenAI website: 
                    #   "You can define instructions 
                    #   in the user message, but the instructions set in the 
                    #   system message are more effective." 
                    "content": 
                    """You are a seasoned engineer who takes bug descriptions 
                    and generates a patch to fix the bug. For this bug, you 
                    are provided with the following hint(s): """ + one_json_obj["hints_text"],
                },
                {
                    "role": "user",
                    "content": one_json_obj["problem_statement"],
                },
                {
                    "role": "assistant",
                    "content": one_json_obj["patch"],
                }
            ],
        }

    # Upload this output to OpenPipe on console
    def create_training_data(self, jsonData, model = "gpt-4o-mini"):
        f = open("hackathon/finetuning/training_data.jsonl", "a")
        for node in jsonData:
            # write output of transform_single_to_openai_chat_format in a single line to jsonl file
            f.write(str(self.transform_single_to_openai_chat_format(node, model)) + "\n")
        f.close()

if __name__ == "__main__":
    print(os.getcwd())
    # Change this to where the data is stored
    filePath = "tests/test_data/data_sources/swe-bench-dev-easy.json"
    fileObj = open(filePath)
    jsonData = json.load(fileObj)

    Finetune().create_training_data(jsonData)
    
