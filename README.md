## Theoretical Documentation

This section explains the architecture and functionality of the "GoogleChatSync" program for synchronizing organizational unit hierarchies in Google Workspace Admin Console with Google Chat Spaces.

### Synchronization Objects

The Google Workspace Admin Console allows creating hierarchical organizational units (OUs) within an enterprise. This structure can be used to create a unified communication space, though Google Chat’s native tools may not scale effectively.  
**Synchronization Objects**:
- **Google Workspace Admin Console**: Organizational Units (OUs)
- **Google Chat**: Spaces

### Synchronization Principle

1. **Fetch OUs**: The program retrieves the list of OUs via API and checks for corresponding entries in the local catalog `ou_space_map.json`.
2. **Create/Update Spaces**:
   - If no matching Space exists, a new Space is created via API and mapped in `ou_space_map.json`.
   - If a Space exists, its name is validated and updated if mismatched.
3. **User Membership Sync**:
   - Users in an OU are added to the corresponding Space via API.
   - Users not in an OU are removed from the Space via API.
4. **Tree Traversal Role**: Users assigned the `GoogleChatTreeTraversal` role inherit access to all Spaces in their OU’s subtree (illustrated below).

#### User Assignment Principle

The diagrams below illustrate user assignment principles:  
- **Dark green**: Current user OU path.  
- **Bright green**: Spaces the user is added to.  

**Standard User Assignment**:

![org_chart_1](https://github.com/user-attachments/assets/793befb1-c83f-42ee-90fc-66980fd0a7b2)

**Tree Traversal Role Assignment**:

![org_chart_2](https://github.com/user-attachments/assets/cb337d76-be1b-48d6-8f32-ad8fe15c0080)

---

## Practical Documentation

This section covers prerequisites and usage of the "GoogleChatSync" program. Code structure details are provided in code comments.

### Prerequisites

1. **Google APIs**:
   - Enable **Google Chat API** and **Admin SDK API** in Google Cloud Console.
2. **Service Account**:
   - Create a service account with OAuth2 credentials (JSON key).
   - Grant permissions to access Google Workspace and Chat APIs.
3. **Configuration File** (`config.json`):
   - Populate the file as shown below:

#### Example `config.json`:

```json
{
  "SCOPES": [
    "https://www.googleapis.com/auth/admin.directory.orgunit.readonly",
    "https://www.googleapis.com/auth/admin.directory.user.readonly",
    "https://www.googleapis.com/auth/admin.directory.rolemanagement.readonly",
    "https://www.googleapis.com/auth/chat.spaces",
    "https://www.googleapis.com/auth/chat.memberships"
  ],
  "SERVICE_ACCOUNT_FILE": "oauth2_key.json",
  "ADMIN_USER": "admin@example.com",
  "ADMIN_USER_ID": "0000000000000000000",
  "TREE_TRAVERSAL_ROLE_NAME": "googleChatTreeTraversal",
  "TREE_TRAVERSAL_ROLE_ID": "0000000000000000",
  "OU_ROOT_PATH": "/Company"
}
```

### Logs

| Log Message | Description |
|-------------|-------------|
| `"Request failed \| type: {type}, url: {url}, response: {response.text}"` | Failed API request with error code and response body. |
| `"Request error \| type: {type}, url: {url}, response: {response}"` | Failed API request with exception details. |
| `"Clear map for OU: {ou_id}"` | OU entry removed due to absence in Workspace. |
| `"Failed creating space {displayName}: {response.text}"` | Space creation failed with error details. |
| `"Error creating space {displayName}: {str(e)}"` | Space creation exception. |
| `"Failed updating space {name}: {response.text}"` | Space update failed with error details. |
| `"Error updating space {name}: {str(e)}"` | Space update exception. |
| `"Failed adding user {member_id} to space {space_name}: {response.text}"` | User addition to Space failed. |
| `"Error adding user {member_id}: {str(e)}"` | User addition exception. |
| `"Failed removing user {member_id} from space {space_name}: {response.text}"` | User removal from Space failed. |
| `"Error removing user {member_id}: {str(e)}"` | User removal exception. |
| `"Invalid data for OU ID {ou_id}: skipping."` | Incomplete OU entry skipped. |
