#!/usr/bin/env python3

import os, json
import argparse

from bs4 import BeautifulSoup
from ghapi.core import GhApi
from selenium import webdriver
from selenium.webdriver.common.by import By


gh_token = os.environ.get("GITHUB_TOKEN")
if not gh_token:
    msg = "Please set the GITHUB_TOKEN environment variable."
    raise ValueError(msg)
api = GhApi(token="gh_token")


def get_package_stats(data_tasks, f):
    """
    Get package stats from pypi page

    Args:
        data_tasks (list): List of packages + HTML
        f (str): File to write to
    """
    # Adjust access type if file already exists
    content = None
    access_type = "w"
    if os.path.exists(f):
        with open(f) as fp_:
            content = fp_.read()
            access_type = "a"
            fp_.close()

    # Extra package title, pypi URL, stars, pulls, and github URL
    with open(f, access_type) as fp_:
        for idx, chunk in enumerate(data_tasks):
            # Get package name and pypi URL
            package_name = chunk["title"]
            package_url = chunk["href"]
            if content is not None and package_url in content:
                continue

            # Get github URL
            package_github = None
            driver.get(package_url)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            for link in soup.find_all("a", class_="vertical-tabs__tab--with-icon"):
                found = False
                for x in ["Source", "Code", "Homepage"]:
                    if (
                        x.lower() in link.get_text().lower()
                        and "github" in link["href"].lower()
                    ):
                        package_github = link["href"]
                        found = True
                        break
                if found:
                    break

            # Get stars and pulls from github API
            stars_count, pulls_count = None, None
            if package_github is not None:
                repo_parts = package_github.split("/")[-2:]
                owner, name = repo_parts[0], repo_parts[1]

                try:
                    repo = api.repos.get(owner, name)
                    stars_count = int(repo["stargazers_count"])
                    issues = api.issues.list_for_repo(owner, name)
                    pulls_count = int(issues[0]["number"])
                except:
                    pass

            # Write to file
            print(
                json.dumps(
                    {
                        "rank": idx,
                        "name": package_name,
                        "url": package_url,
                        "github": package_github,
                        "stars": stars_count,
                        "pulls": pulls_count,
                    }
                ),
                file=fp_,
                flush=True,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-repos", help="Maximum number of repos to get", type=int, default=5000)
    args = parser.parse_args()

    # Start selenium driver to get top 5000 pypi page
    url_top_pypi = "https://hugovk.github.io/top-pypi-packages/"
    driver = webdriver.Chrome()
    driver.get(url_top_pypi)
    button = driver.find_element(By.CSS_SELECTOR, 'button[ng-click="show(8000)"]')
    button.click()

    # Retrieve HTML for packages from page
    soup = BeautifulSoup(driver.page_source, "html.parser")
    package_list = soup.find("div", {"class": "list"})
    packages = package_list.find_all("a", class_="ng-scope")

    get_package_stats(packages[:args.max_repos], "pypi_rankings.jsonl")
