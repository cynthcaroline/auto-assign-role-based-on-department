from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict

app = FastAPI(
    title="Provisioning API",
    description="Auto role assignment based on department and position",
    version="1.0.0"
)

# ROLE MAPPING -> department -> position -> roles
ROLE_MAPPING: Dict[str, Dict[str, List[str]]] = {
    "Engineering": {
        "Software Engineer": [
            "msteams",
            "jira-user",
            "github-dev",
        ],
        "DevOps Engineer": [
            "msteams",
            "jira-user",
            "github-admin",
            "aws-admin"
        ],
    },
    "Finance": {
        "Financial Analyst": [
            "msteams",
            "erp-user",
            "excel-online",
            "reporting-user",
        ],
        "Accountant": [
            "msteams",
            "erp-user",
            "excel-online",
            "invoice-user",
        ],
    },
}

# Fallback roles for unknown department/position
DEFAULT_ROLES = ["msteams"]

# Jira ticket template
class EmployeeRequest(BaseModel):
    ticketId:     str = Field(..., min_length=1)
    employeeName: str = Field(..., min_length=1)
    department:   str = Field(..., min_length=1)
    position:     str = Field(..., min_length=1)
    manager:      str = Field(..., min_length=1)


class ProvisionResponse(BaseModel):
    status:         str
    ticketId:       str
    employeeName:   str
    department:     str
    position:       str
    manager:        str
    assigned_roles: List[str]
    role_source:    str   # "exact_match" | "department_default" | "fallback"

# for switch, solve role with this mapping
def resolve_roles(department: str, position: str):
    dept_map = ROLE_MAPPING.get(department)

    if dept_map is None:
        # Unknown department = default roles = fallback
        return DEFAULT_ROLES, "fallback"

    roles = dept_map.get(position)

    if roles is None:
        # Known department, unknown position = department default
        fallback_roles = list(dept_map.values())[0]
        return fallback_roles, "department_default"

    return roles, "exact_match"


# list api with fast api
#list role
@app.get("/roles")
def list_roles():
    return {"role_mapping": ROLE_MAPPING, "default_roles": DEFAULT_ROLES}

#receive and send data to n8n
@app.post(
    "/provision",
    response_model=ProvisionResponse,
    status_code=status.HTTP_201_CREATED,
)
def provision(employee: EmployeeRequest):
    try:
        assigned_roles, role_source = resolve_roles(
            employee.department,
            employee.position,
        )

        return ProvisionResponse(
            status="success",
            ticketId=employee.ticketId,
            employeeName=employee.employeeName,
            department=employee.department,
            position=employee.position,
            manager=employee.manager,
            assigned_roles=assigned_roles,
            role_source=role_source,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Provisioning failed: {str(e)}",
        )

