import json
import re
import requests
import sys

from datetime import datetime

sys.path.append("/n/fs/nlp-jy1682/swe-bench/public/harness")
from utils import get_instances
sys.path = sys.path[:-1]

PATH_TASKS_PVLIB   = "<path to pvlib-python task instances>"
PATH_TASKS_PVLIB_V = "<path to pvlib-python task instances with versions>"
WEBPAGE = "https://pvlib-python.readthedocs.io/en/stable/whatsnew.html"
PATTERN = r'<a class="reference internal nav-link" href="#(.*)">\n\s+v(.*)\n\s+<\/a>'
DATE_FORMAT = "%B %d, %Y"

# Get raw astropy dataset
data_tasks = get_instances(PATH_TASKS_PVLIB)

# Get version to date from astropy homepage
resp = requests.get(WEBPAGE)
matches = re.findall(PATTERN, resp.text)
matches = list(set(matches))

# Get (date, version) pairs
keep_major_minor = lambda x, sep: ".".join(x.strip().split(sep)[:2])

# Iterate through matches, construct (version, date) pairs
times = []
for match in matches:
    match_parts = match[1].split(" (")
    version = '.'.join(match_parts[0].split('.')[:-1])
    date = match_parts[1].strip(')').strip('(')
    date_obj = datetime.strptime(date, DATE_FORMAT)
    times.append((date_obj.strftime("%Y-%m-%d"), version))

# Group times by major/minor version
map_version_to_times = {}
for time in times:
    if time[1] not in map_version_to_times:
        map_version_to_times[time[1]] = []
    map_version_to_times[time[1]].append(time[0])

# Pick the most recent time as the version cut off date
version_to_time = [(k, max(v)) for k, v in map_version_to_times.items()]
version_to_time = sorted(version_to_time, key=lambda x: x[0])[::-1]

# Assign version to each task instance
for task in data_tasks:
    created_at = task["created_at"].split("T")[0]
    for t in version_to_time:
        found = False
        if t[1] < created_at:
            task["version"] = t[0]
            found = True
            break
    if not found:
        task["version"] = version_to_time[-1][0]

# Construct map of versions to task instances
map_v_to_t = {}
for task in data_tasks:
    if task["version"] not in map_v_to_t:
        map_v_to_t[task["version"]] = []
    map_v_to_t[task["version"]].append(t)

# Save matplotlib versioned data to repository
with open(PATH_TASKS_PVLIB_V, "w") as f:
    json.dump(data_tasks, fp=f)