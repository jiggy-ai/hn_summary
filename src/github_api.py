# wrangle text out of github repo by 
import requests



def github_readme_text(github_repo_url):
    # split a github url into the owner and repo components
    # use the github api to try to find the readme text
    # ['https:', '', 'github.com', 'jiggy-ai', 'hn_summary']
    spliturl = github_repo_url.split('/')
    owner = spliturl[3]
    repo = spliturl[4]
    contenturl = f'https://api.github.com/repos/{owner}/{repo}/contents'
    resp  = requests.get(contenturl)
    if resp.status_code != 200:
        print(resp.content)
        raise Exception(f"Unable to get github contents for {github_repo_url}")
    content_list = resp.json()
    for item in content_list:
        if item['type'] != 'file': continue
        if 'readme' in item['name'].lower():
            return requests.get(item['download_url']).text
    raise Exception(f"No Readme found for {github_repo_url}")
