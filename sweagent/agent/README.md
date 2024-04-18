# Agents
The `agent` folder contains the logic for handling model inference and facilitating their interaction with `SWEEnv`.
The following documentation describing the purpose and classes of each file.

#### `agents.py` 
This file defines the `Agent` class, which facilitates the interaction between an agent and the environment. The `AgentConfig` and `AgentArguments` data classes compile all arguments into a single file.
- `Agent`: Main class for handling model behavior + interaction with environment
    - `__init__`: Sets up model, assistant, configurations, and arguments
    - `state_command`: Getter for bash command for extracting env. state
    - `setup`: Resets cost stats, initializes system message (+ demonstrations), and returns full list of bash commands to define within environment.
    - `forward`: Main inference call to model.
    - `forward_model`: Determines appropriate observation template, then makes inference call to model
    - `forward_with_format_check`: Invokes `forward_model`, with retry calls to handle blocked or malformed actions.
    - `forward_with_error_check`: Wraps `forward_with_format_check` with exception handling.

#### `commands.py`
This file defines the abstraction for custom commands (non-native functions that are implemented in bash) that agents can invoke in `swe-agent` environment. On top of the abstraction, helper functions to extract commands' documentation and compile `.sh` files into separate `Command` objects are provided. There are also fields for establishing the input/output of each action and control flow of actions via templates.
- `AssistantMetadata`: Defines templates for formatting input/output to sub-assistant calls
- `Command`: Defines fields of a custom command
- `ControlMetadata` (WIP): Defines template fields that format the observations for the next agent `forward` inference call
- `generate_command_docs`: Extracts docstrings from each command to form comprehensive documentation.
- `parse_command_file`: Converts bash file content to separate `Command` objects

#### `models.py`
This file defines the abstraction for running inference on API models. In addition, the `BaseModel` abstraction also defines a set of cost-related fields for tracking instance-level and total expenses accumulated across a single model run.
- `AnthropicModel`: Handles inference + cost logging for Anthropic Models
- `BedrockModel`: handles inference + cost logging for Amazon Bedrock-provided models (Anthropic Claude only)
- `APIStats`: Cost tracking fields that are updated per model inference
- `BaseModel`: Abstract class that defines the common logic for updating cost stats
- `get_model`: Returns initialized `[Anthropic|Bedrock|Human|OpenAI]Model` based on given arguments + commands
- `HumanModel`: Handles inference for human task worker
- `ModelArguments`: Model name, hyperparameter, and cost limit arguments
- `OpenAIModel`: Handles inference + cost logging for OpenAI models

#### `parsing.py`
This file defines the abstraction for parsing the output of the model inference. The `Parsing` class is used to extract the relevant information from the model's output and format it into a response that can be used by the `Agent` class.
- `Parsing`: Abstract class that defines the common logic for parsing model output

#### `history_processors.py`
This file defines the abstraction for processing the history of the environment. The `HistoryProcessor` class is used to extract the relevant information from the history of the environment and format it into a response that can be used by the `Agent` class.
- `HistoryProcessor`: Abstract class that defines the common logic for processing the history of the environment
- `DefaultHistoryProcessor`: Default implementation of `HistoryProcessor` that processes the history of the environment

### Environment Usage
* To skip over a task instance, use the `skip` keyword
* To submit for evaluation, use the `submit` keyword
* To exit the `SWEEnv` environment, perform a keyboard interrupt (`^ c`)