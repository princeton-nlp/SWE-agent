FROM sweagent/swe-agent:latest

ENV PYTHONBREAKPOINT=ipdb.set_trace

# Install Poetry
RUN pip install poetry

# Copy the Poetry files
COPY evaluation/pyproject.toml evaluation/poetry.lock /evaluation/

# Set the working directory
WORKDIR /evaluation

# Export dependencies to requirements.txt
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes
COPY SWE-bench /SWE-bench

# Install dependencies using pip into the conda environment
RUN pip install -r requirements.txt

COPY evaluation/evaluation.py /evaluation.py