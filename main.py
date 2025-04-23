import logging
import time
from datetime import datetime
from google.oauth2 import service_account
import google.auth.transport.requests
import json

config = json.load(open('./config.json', 'r'))

SCOPES = config["SCOPES"]
SERVICE_ACCOUNT_FILE = config["SERVICE_ACCOUNT_FILE"]
ADMIN_USER = config["ADMIN_USER"]
ADMIN_USER_ID = config["ADMIN_USER_ID"]
TREE_TRAVERSAL_ROLE_NAME = config["TREE_TRAVERSAL_ROLE_NAME"]
TREE_TRAVERSAL_ROLE_ID = config["TREE_TRAVERSAL_ROLE_ID"]
OU_ROOT_PATH = config["OU_ROOT_PATH"]

# Initialize the credentials and session
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES
).with_subject(ADMIN_USER)
session = google.auth.transport.requests.AuthorizedSession(credentials)

def create_session(max_time, session, type, url, json=None, params=None):
    timer = 2
    response = None
    while True:
        if type == "fetch":
            response = session.fetch(url, json=json, params=params)
        elif type == "post":
            response = session.post(url, json=json, params=params)
        elif type == "patch":
            response = session.patch(url, json=json, params=params)
        elif type == "delete":
            response = session.delete(url, json=json, params=params)
        elif type == "get":
            response = session.get(url, json=json, params=params)

        if response is not None:
            if response.status_code == 200:
                return response
            elif response.status_code == 500:
                return None
            else:
                if timer < max_time:
                    time.sleep(timer)
                    timer *= timer
                else:
                    log_error(f"Request failed | type: {type}, url: {url}, response: {response.text}")
                    return None
        else:
            log_error(f"Request error | type: {type}, url: {url}, response: {response}")
            return None

# Set up logging
logging.basicConfig(filename='./main.log', level=logging.ERROR)

def log_error(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.error(f"{timestamp} - {message}")

# Additional functions
def save_ou_space_map(ou_space_map):
    with open('./ou_space_map.json', 'w') as f:
        json.dump(ou_space_map, f, indent=4)

def load_ou_space_map():
    try:
        with open('./ou_space_map.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def is_under(user_ou: str, ou_path: str) -> bool:
    def norm(p: str) -> str:
        return p.strip().rstrip('/')

    u = norm(user_ou or '')
    o = norm(ou_path or '')

    if u == o:
        return True
    return u.startswith(o + '/')

def is_upper(user_ou: str, ou_path: str) -> bool:
    pass
# Functions for working with Organizational Units and Spaces mapping

def clear_ou_space_map(ou_space_map, ou_array):
    save_ou_ids = {ou['orgUnitId'] for ou in ou_array}
    delete_ou_ids = set(ou_space_map.keys()) - save_ou_ids
    for ou_id in delete_ou_ids:
        if ou_id == "root":
            continue
        else:
            del ou_space_map[ou_id]
            save_ou_space_map(ou_space_map)
        log_error(f"Clear map for OU: {ou_id}")

def edit_spaces(ou_array, space_array, ou_space_map):
    for ou in ou_array:
        ou_id = ou['orgUnitId']
        if ou_id in ou_space_map:
            if ou_space_map[ou_id].get("orgUnitPath") != ou['orgUnitPath']:
                request_update_space(ou_space_map[ou_id]['name'], ou['orgUnitPath'][1:])
                ou_space_map[ou_id]['orgUnitPath'] = ou['orgUnitPath']
                save_ou_space_map(ou_space_map)
            for space in space_array:
                if space['name'] == ou_space_map[ou_id]['name'] and f"/{space['displayName']}" != ou_space_map[ou_id]['orgUnitPath']:
                    request_update_space(space['name'], ou_space_map[ou_id]['orgUnitPath'])
                    save_ou_space_map(ou_space_map)
                break
        else:
            new_space = request_create_space(ou['orgUnitPath'][1:])
            ou_space_map[ou['orgUnitId']] = {
                "orgUnitPath": ou['orgUnitPath'],
                "name": new_space['name']
            }
            save_ou_space_map(ou_space_map)

def request_create_space(displayName: str):
    url = 'https://chat.googleapis.com/v1/spaces'
    data = {
        'displayName': displayName,
        'spaceType': 'SPACE',
        'externalUserAllowed': False,
    }
    try:
        response = create_session(60, session, "post", url, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            log_error(f"Failed creating space {displayName}: {response.text}")
    except Exception as e:
        log_error(f"Error creating space {displayName}: {str(e)}")

def request_update_space(name: str, displayName: str):
    url = f"https://chat.googleapis.com/v1/{name}"
    try:
        data = create_session(60, session, "get", url).json()
        data['displayName'] = displayName
        response = create_session(60, session, "patch", url, json=data, params={'updateMask': 'displayName'})
        if response.status_code == 200:
            return response.json()
        else:
            log_error(f"Failed updating space {name}: {response.text}")
    except Exception as e:
        log_error(f"Error updating space {name}: {str(e)}")

# Functions for syncing OU members with space members

def sync_ou_space_membership(ou_membership_ids, space_membership_ids, space_name):
    for member_id in ou_membership_ids:
        if member_id not in space_membership_ids:
            request_add_membership(member_id, space_name)

    for member_id in space_membership_ids:
        if member_id not in ou_membership_ids:
            if member_id != ADMIN_USER_ID:
                request_remove_membership(member_id, space_name)

def request_add_membership(member_id, space_name):
    url = f'https://chat.googleapis.com/v1/{space_name}/members'
    try:
        data = {
            'member': {
                'name': f'users/{member_id}',
                'type': 'HUMAN'
            }
        }
        response = create_session(60, session, "post", url, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            log_error(f"Failed adding user {member_id} to space {space_name}: {response.text}")
    except Exception as e:
        log_error(f"Error adding user {member_id}: {str(e)}")

def request_remove_membership(member_id, space_name):
    url = f'https://chat.googleapis.com/v1/{space_name}/members/{member_id}'
    try:
        response = create_session(60, session, "delete", url)
        if response.status_code == 200:
            return response.json()
        else:
            log_error(f"Failed removing user {member_id} from space {space_name}: {response.text}")
    except Exception as e:
        log_error(f"Error removing user {member_id}: {str(e)}")

def request_ou_space_members(orgUnitPath, name):
    ou_members = []
    space_members = []
    tree_traversal_members = []
    try:
        page_token = None

        url = "https://admin.googleapis.com/admin/directory/v1/customer/my_customer/roleassignments"
        response = create_session(60, session, "get", url)
        data = response.json()
        if response.status_code == 200:
            for role in data['items']:
                if role.get('roleId') == TREE_TRAVERSAL_ROLE_ID:
                    tree_traversal_members.append(role['assignedTo'])

        while True:
            url = ('https://admin.googleapis.com/admin/directory/v1/users?customer=my_customer&maxResults=500')
            if page_token:
                url += f"&pageToken={page_token}"
            response = create_session(60, session, "get", url)
            if response.status_code == 200:
                pass
            else:
                log_error(f"Failed reading members from OU {orgUnitPath}: {response.text}")
                return [], []

            data = response.json()
            for user in data.get('users', []):
                user_ou_path = user.get('orgUnitPath')
                user_id = user.get('id')
                if (is_under(user_ou_path, orgUnitPath) or (is_under(orgUnitPath, user_ou_path) and user_id in tree_traversal_members)) or orgUnitPath == OU_ROOT_PATH:
                    ou_members.append(user['id'])

            page_token = data.get('nextPageToken')
            if not page_token:
                break
    except Exception as e:
        log_error(f"Error reading members from OU {orgUnitPath}: {str(e)}")

    try:
        page_token = None

        while True:
            url = f'https://chat.googleapis.com/v1/{name}/members?pageSize=500'
            if page_token:
                url += f"&pageToken={page_token}"
            response = create_session(60, session, "get", url)
            if response.status_code == 200:
                pass
            else:
                log_error(f"Failed reading members from space {name}: {response.text}")
                return [], []

            data = response.json()
            for user in data.get('memberships', []):
                if user.get('deletionTime') is None:
                    space_members.append(user.get('name').split('/')[-1])
            if not page_token:
                break
    except Exception as e:
        log_error(f"Error reading members from space {name}: {str(e)}")

    return ou_members, space_members

# Run the update and sync process
if __name__ == "__main__":
    # Update OU and Space map
    ou_response = create_session(60, session, "get",'https://admin.googleapis.com/admin/directory/v1/customer/my_customer/orgunits', params={"type": "all"})
    space_response = create_session(60, session, "get",'https://chat.googleapis.com/v1/spaces')

    ou_space_map = load_ou_space_map()

    ou_array = ou_response.json().get('organizationUnits', [])
    space_array = space_response.json().get('spaces', [])

    ou_array.append({
        "orgUnitId": "root",
        "orgUnitPath": OU_ROOT_PATH
    })
    clear_ou_space_map(ou_space_map, ou_array)
    edit_spaces(ou_array, space_array, ou_space_map)

    save_ou_space_map(ou_space_map)

    # Sync OU and Space members
    ou_space_map = load_ou_space_map()
    for ou_id, data in ou_space_map.items():
        orgUnitPath = data.get("orgUnitPath")
        name = data.get("name")

        if not orgUnitPath or not name:
            log_error(f"Invalid data for OU ID {ou_id}: skipping.")
            continue

        ou_members, space_members = request_ou_space_members(orgUnitPath, name)
        sync_ou_space_membership(ou_members, space_members, name)