# wrangle text out of github repo by 
import requests
import markdown 
from bs4 import BeautifulSoup 



def md_to_text(md):
    html = markdown.markdown(md)
    soup = BeautifulSoup(html, features='html.parser')
    return soup.get_text()


def github_readme_text(github_repo_url):
    # split a github url into the owner and repo components
    # use the github api to try to find the readme text
    # ['https:', '', 'github.com', 'jiggy-ai', 'hn_summary']
    spliturl = github_repo_url.rstrip('/').split('/')
    if len(spliturl) != 5:
        raise Exception(f"Unable to process github url {github_repo_url}")
    owner = spliturl[3]
    repo = spliturl[4]
    contenturl = f'https://api.github.com/repos/{owner}/{repo}/readme'
    resp  = requests.get(contenturl)
    if resp.status_code != 200:
        print(resp.content)
        raise Exception(f"Unable to get readme for {github_repo_url}")
    item = resp.json()
    md = requests.get(item['download_url']).text
    return md_to_text(md)

