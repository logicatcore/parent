import re
import json
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def post_graphql_endpoint(query_or_mutation, token="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"):
    """
    Calls the POST method with a query or mutation and the provided token for authorisation

    :return: Response of POST call
    """
    api_endpoint = "https://api.github.com/graphql"
    response = requests.post(api_endpoint, json={"query": query_or_mutation},
                             headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})

    if good_response(response):
        return response


def good_response(response):
    """
    Check the response code. If not OK, then print the response code, short description, and long description.
    """
    if response.status_code == 200:
        return True
    else:
        return False


# Step 1: Get the two most recent CSB tags on adcu_proj
def get_tag_query(repo_name, no_of_tags, query):
    """
    Example Response
    {
      "data": {
        "repository": {
          "refs": {
            "nodes": [
              {
                "name": "CSB.00.04.03.48"
              },
              {
                "name": "CSB.00.04.03.47"
              }
            ]
          }
        }
      }
    }
    :param repo_name: Name of the repository
    :param no_of_tags: Number of most recent tags to get
    :param query: filters refs with query on name.
    :return: returns the query
    """
    return """query Tags {{
                repository(owner: "logicatcore", name:"{0}") {{
                  refs(first:{1}, orderBy:{{field:TAG_COMMIT_DATE, direction:DESC}}, query:"{2}", refPrefix:"refs/tags/"){{
                    nodes{{
                      name
                    }}
                  }}
                }}
              }}""".format(repo_name, no_of_tags, query)


tag_response = post_graphql_endpoint(get_tag_query("parent", 2, "CSB"))
tag_response_data = json.loads(tag_response.text)
tags = [x["name"] for x in tag_response_data["data"]["repository"]["refs"]["nodes"]]

print("The last two recent CSB tags on parent repository are: ", tags)
print("Will be creating tags in the sub software components for the tag: ", tags[0])


def submodules_query(ref):
    """
    Example response
    {
  "data": {
    "repository": {
      "ref": {
        "name": "CSB.00.04.03.46",
        "target": {
          "submodules": {
            "nodes": [
              {
                "name": "git-scripts",
                "branch": "feature/CSB-3483/BCR_Gamma_F_BMW",
                "subprojectCommitOid": "0ec1a9db47ebd112c07031066e42b77745b70977"
              },
              {
                "name": "Aurix/plugins/cdd-bai",
                "branch": "feature/CSB-3483/BCR_Gamma_F_BMW",
                "subprojectCommitOid": "281477573a2378c910c505da2d779f2706908f88"
              }...
    :param ref: tag name at which point the submodules data is to be fetched
    :return: returns the query which can be used to fetch submodule details at a particular tag
    """
    return """query GetSubmodulesInfoUsingTag{{
                repository(owner: "logicatcore", name: "parent") {{
                  ref(qualifiedName: "{0}") {{
                    name
                    target {{
                      ... on Commit {{
                        submodules(first: 100) {{
                          nodes {{
                            path
                            subprojectCommitOid
                          }}
                        }}
                      }}
                    }}
                  }}
                }}
              }}""".format(ref)


new_tag_query = submodules_query(tags[0])
new_tag_response = post_graphql_endpoint(new_tag_query)
new_tag_data = json.loads(new_tag_response.text)["data"]["repository"]["ref"]["target"]["submodules"]["nodes"]

old_tag_query = submodules_query(tags[1])
old_tag_response = post_graphql_endpoint(old_tag_query)
old_tag_data = json.loads(old_tag_response.text)["data"]["repository"]["ref"]["target"]["submodules"]["nodes"]


changes = dict()
for new, old in zip(new_tag_data, old_tag_data):
    if new["subprojectCommitOid"] != old["subprojectCommitOid"]:
        changes[new["path"].split("/")[-1]] = {"subprojectCommitOid": new["subprojectCommitOid"]}


def get_repo_id_query(repo_name):
    """
    Example response
        {
      "data": {
        "repository": {
          "id": "MDEwRvcnk1Mzc3MA=="
        }
      }
    }
    :param repo_name: name of the repository whose oID is needed
    :return: returns the query which can be used to fetch a repositories oID
    """
    return """query GetIDsFromSHAs {{
                repository(owner: "logicatcore", name: "{0}"){{
                  id
                }}
              }}""".format(repo_name)


errors = list()
for repo_name in changes.keys():
    change_query = get_repo_id_query(repo_name)
    change_response = post_graphql_endpoint(change_query)
    try:
        change_repo_id = json.loads(change_response.text)["data"]["repository"]["id"]
        json.dump(change_repo_id, open(f"{repo_name}_repo_id.json", 'w'))
        changes[repo_name]["id"] = change_repo_id
    except TypeError:
        errors.append(repo_name)
    
[changes.pop(error) for error in errors]

print("Repositories where a change in SHA-1 is seen upon comparison of submodule statuses of the two parent "
      "tags are: ", changes)


def make_tag(owner, repo_name, body):
    """
    REST api for creating tag so that the tag can be associated with a user

    :param owner:
    :param repo_name:
    :param body:
    :return:
    """
    rest_api_endpoint = f"https://api.github.com/repos/{owner}/{repo_name}/releases"
    password = "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"
    response = requests.post(rest_api_endpoint, json={"tag_name": body}, allow_redirects=True, verify=False, headers={"Content-Type": "application/json", "Authorization": f"Bearer {password}"})
    if good_response(response):
        return response


def get_new_tag(name, change_repo_tags, target_tag):
    """
    New tag creation logic and rules go in here which are repository dependent

    :param name:
    :param change_repo_tags:
    :return:
    """
    return "Voila"


only_nums = re.compile('[0-9]')
for repo_name in changes.keys():
    change_tag_query = get_tag_query(repo_name, 10, "CSB")
    change_tags_response = post_graphql_endpoint(change_tag_query)
    change_tags_data = json.loads(change_tags_response.text)
    # determine the next tag to be made
    change_tags = [x["name"] for x in change_tags_data["data"]["repository"]["refs"]["nodes"]]
    new_tag = get_new_tag(repo_name, change_tags, tags[0])
    new_tag_creation_response = make_tag("logicatcore", repo_name, new_tag)
    if good_response(new_tag_creation_response):
        pass
    else:
        print("Tag creation failed")
