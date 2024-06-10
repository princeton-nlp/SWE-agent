FROM sweagent/swe-agent:latest

COPY evaluation/evaluation.py /evaluation.py
RUN pip install unidiff
COPY SWE-bench /SWE-bench
RUN pip install -e /SWE-bench
CMD ["python", "/evaluation.py"]
