FROM python:3.9

# Set the working directory
WORKDIR /app

# Copy the application code
COPY . /app

# Install Python dependencies
RUN pip install anthropic config datasets docker gymnasium numpy openai pandas rich ruamel.yaml swebench tenacity unidiff simple-parsing together ollama

# Set the entrypoint
CMD ["python", "run.py"]
