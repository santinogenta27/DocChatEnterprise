# 🔗 Deep CRM Integration - Business AI Support

## Overview

This module provides **deep integration** with major CRM systems (Salesforce, HubSpot, Zendesk) for Business AI Support. It enables the agent to:

- ✅ **Read customer data** from CRM in real-time
- ✅ **Create and update** records automatically
- ✅ **Sync tickets** between internal system and CRM
- ✅ **Maintain accurate customer data** without manual intervention
- ✅ **Execute actions** in CRM based on customer interactions

## Features

### 1. **Contextual Customer Data Access**
- Get customer information (name, email, phone, company) from CRM
- Retrieve full interaction history (cases, tickets, deals)
- Understand customer context before responding

### 2. **Automatic Record Management**
- Create/update contacts automatically
- Sync tickets/cases between systems
- Add notes and comments to records
- Create follow-up tasks

### 3. **Automated Workflows**
- Auto-create CRM cases when tickets are created
- Update contact information from conversations
- Link tickets to existing customers
- Escalate cases automatically

### 4. **Security & Governance**
- Permission-based access control
- Secure API authentication
- Data encryption support (PII)
- Audit logging

## Supported CRMs

### Salesforce
- **Authentication**: Username/Password/Token OR OAuth
- **Features**: Contacts, Accounts, Cases, Leads, Notes, Tasks
- **API**: REST API v58.0

### HubSpot
- **Authentication**: API Key OR OAuth Access Token
- **Features**: Contacts, Companies, Deals, Tickets, Engagements (Notes/Tasks)
- **API**: REST API v3

### Zendesk
- **Authentication**: API Token (Email + Token) OR OAuth
- **Features**: Users, Organizations, Tickets, Comments
- **API**: REST API v2

## Configuration

### Environment Variables

#### Salesforce
```bash
# Option 1: Username/Password/Token
SALESFORCE_USERNAME=your_username
SALESFORCE_PASSWORD=your_password
SALESFORCE_SECURITY_TOKEN=your_security_token

# Option 2: OAuth (Access Token)
SALESFORCE_ACCESS_TOKEN=your_access_token
SALESFORCE_INSTANCE_URL=https://your-instance.salesforce.com

# Optional: Permissions (comma-separated)
SALESFORCE_PERMISSIONS=read_contact,create_contact,update_contact,create_case,update_case
```

#### HubSpot
```bash
# Option 1: API Key
HUBSPOT_API_KEY=your_api_key

# Option 2: OAuth Access Token
HUBSPOT_ACCESS_TOKEN=your_access_token

# Optional: Permissions
HUBSPOT_PERMISSIONS=read_contact,create_contact,update_contact,create_ticket
```

#### Zendesk
```bash
# Required: Subdomain
ZENDESK_SUBDOMAIN=your_subdomain

# Option 1: API Token
ZENDESK_EMAIL=your_email@example.com
ZENDESK_API_TOKEN=your_api_token

# Option 2: OAuth Access Token
ZENDESK_ACCESS_TOKEN=your_access_token

# Optional: Permissions
ZENDESK_PERMISSIONS=read_contact,create_contact,update_contact,create_ticket
```

## Usage

### In Business AI Support Mode

The CRM integration is automatically initialized when CRM credentials are configured. The agent will:

1. **Fetch customer info** from CRM at the start of each conversation
2. **Create/update contacts** when new customers interact
3. **Sync tickets** to CRM when created internally
4. **Update contact fields** (sentiment, lead_score, etc.) based on interactions

### Example: Manual CRM Operations

```python
from docchat.business_ai_support import BusinessAISupportMode
from docchat.config import load_config

config = load_config()
mode = BusinessAISupportMode(config=config)

# Access CRM Tool
if mode.crm_tool and mode.crm_tool.has_crm:
    # Get customer info
    customer_info = mode.crm_tool.get_customer_info("customer@example.com")
    print(customer_info)
    
    # Get customer history
    history = mode.crm_tool.get_customer_history("contact_id_123")
    print(history)
    
    # Create CRM case
    case = mode.crm_tool.create_crm_case(
        case_data={
            "subject": "Support Request",
            "description": "Customer needs help with product",
            "status": "open",
            "priority": "normal"
        },
        contact_email="customer@example.com"
    )
    print(case)
```

## Architecture

```
BusinessAISupportMode
  └── CRMManager
       ├── SalesforceConnector
       ├── HubSpotConnector
       └── ZendeskConnector
            └── CRMTool (wraps for agent use)
                 └── BusinessAIAgent (uses CRM Tool)
```

## Integration Points

### 1. Customer Context Retrieval
- Happens at the start of `handle_message()`
- Searches CRM by email/phone
- Retrieves customer history
- Injects context into agent prompt

### 2. Ticket Synchronization
- When internal ticket is created → Sync to CRM
- Links ticket to customer contact
- Preserves ticket ID mapping

### 3. Contact Management
- Auto-create contacts for new customers
- Update existing contacts with latest info
- Sync sentiment, lead_score, and other metrics

## Security

- **Authentication**: Secure API tokens/OAuth
- **Permissions**: Granular permission control per CRM
- **PII Encryption**: Support for encrypting sensitive data (to be implemented)
- **Audit Logging**: All CRM operations are logged

## Error Handling

The integration gracefully handles errors:
- If CRM is unavailable, agent continues without CRM context
- Errors are logged but don't interrupt conversation flow
- Fallback to internal-only operations if CRM sync fails

## Testing

Test CRM connection:
```python
from docchat.business_ai_support.integrations.crm import CRMManager, CRMConfig, CRMProvider

# Create config
config = CRMConfig(
    provider=CRMProvider.SALESFORCE,
    username="your_username",
    password="your_password",
    security_token="your_token"
)

# Create manager
manager = CRMManager([config])

# Test connection
connector = manager.get_connector(CRMProvider.SALESFORCE)
if connector.test_connection():
    print("✅ CRM connection successful!")
```

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Check credentials in environment variables
   - Verify API tokens are valid
   - For Salesforce: Ensure security token is correct

2. **Connection Timeout**
   - Check network connectivity
   - Verify CRM instance URL/subdomain is correct
   - Check firewall settings

3. **Permission Denied**
   - Verify API user has required permissions
   - Check permission list in environment variables
   - Review CRM user role settings

## Future Enhancements

- [ ] PII encryption/decryption
- [ ] Two-way sync (CRM → Internal system)
- [ ] Webhook support for CRM events
- [ ] Advanced filtering and search
- [ ] Bulk operations support
- [ ] Custom field mapping

## References

- [Salesforce REST API Docs](https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/)
- [HubSpot API Docs](https://developers.hubspot.com/docs/api/overview)
- [Zendesk API Docs](https://developer.zendesk.com/api-reference)

