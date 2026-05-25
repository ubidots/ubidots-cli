ORG_LIST_ROUTE = "/api/v2.0/organizations/"
ORG_DETAIL_ROUTE = "/api/v2.0/organizations/{org_id}/"
ORG_USERS_ROUTE = "/api/v2.0/organizations/{org_id}/users/"

FIELDS_ORG_HELP_TEXT = (
    "Comma-separated fields to process * e.g. field1,field2,field3. "
    "* Available fields: (id, name, label, createdAt, updatedAt, url)."
)

FIELDS_ORG_LIST_DEFAULT = "id,name,label,createdAt"

FIELDS_ORG_USERS_HELP_TEXT = (
    "Comma-separated fields to process * e.g. field1,field2,field3. "
    "* Available fields: (user_id, username, email, role)."
)
