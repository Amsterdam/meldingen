# Meldingen config

## Mail config

Mail settings are defined in the application settings model and can be overridden
with environment variables using the API_ prefix. For example:

- API_MAIL_SMTP_HOST
- API_MAIL_DEFAULT_SENDER

### SMTP transport

| Setting | Type | Default | Description |
| --- | --- | --- | --- |
| mail_smtp_host | string | mailpit | SMTP server hostname. |
| mail_smtp_port | integer | 1025 | SMTP server port. |
| mail_smtp_username | string \| null | test_smtp_user | SMTP username. Set to null or empty when authentication is not required. |
| mail_smtp_password | string \| null | smtp_secret | SMTP password. Set to null or empty when authentication is not required. |
| mail_smtp_start_tls | boolean | false | Enables STARTTLS on a plain SMTP connection, typically on port 587. |
| mail_smtp_use_tls | boolean | false | Enables implicit TLS, typically on port 465. |
| mail_smtp_timeout | float | 10.0 | Timeout in seconds for SMTP operations. |

TLS flags are mutually exclusive in normal setups:

- Use mail_smtp_start_tls for STARTTLS upgrades.
- Use mail_smtp_use_tls for implicit TLS.
- Keep both false for plain SMTP (for example local Mailpit).

### General mail content

| Setting | Type | Default | Description |
| --- | --- | --- | --- |
| mail_default_sender | string | meldingen@example.com | Sender address used for outgoing messages. |
| mail_disclaimer | string | Dutch default text | Footer/disclaimer text for outgoing mail. |

### Melding confirmation template

| Setting | Type | Default | Description |
| --- | --- | --- | --- |
| mail_melding_confirmation_title | string | Uw melding | Title shown in the confirmation template. |
| mail_melding_confirmation_preview_text | string | Uw melding: `{melding_id}` | Preview text/snippet shown by some clients. |
| mail_melding_confirmation_subject | string | Uw melding `{melding_id}`: melding ontvangen | Subject line for confirmation messages. |
| mail_melding_confirmation_service_belofte_default | string | Dutch default text | Fallback service promise text when no category-specific text is available. |
| mail_melding_confirmation_body_text | string | Dutch markdown body | Main markdown body of the confirmation mail. This value *must* contain a template placeholder `{melding_categorie_service_belofte_tekst}` to use the configured service belofte. |


#### Service belofte

You can override the service belofte text per Classification created.

*Default service belofte from config*  
If a Classification uses the default service belofte value (`-`), the application uses the value from the config.

*Custom service belofte on a Classification*  
If you add custom service belofte text to a Classification, that custom text is used. You can use these two template variables:
- `{melding_categorie_service_belofte_dagen}`
- `{melding_categorie_service_belofte_dag_type}` (dagen of werkdagen)

These values come from the Classification edit screen. For example, with this service belofte text:

```
Wij pakken uw melding binnen {melding_categorie_service_belofte_dagen} {melding_categorie_service_belofte_dag_type} op.
```

The e-mail will then contain:

```
Wij pakken uw melding binnen 5 dagen op.
```


### Melding completed template

| Setting | Type | Default | Description |
| --- | --- | --- | --- |
| mail_melding_completed_title | string | Uw melding `{melding_id}`: melding afgehandeld | Title used for the completed notification. |
| mail_melding_completed_preview_text | string | Uw melding: `{melding_id}` | Preview text/snippet for the completed notification. |
| mail_melding_completed_subject | string | Uw melding: `{melding_id}` afgehandeld | Subject line for completed messages. |

### Template placeholders

The following placeholders are available in mail templates:

| Placeholder | Meaning |
| --- | --- |
| `{melding_tekst}` | Text entered by the user for the melding. |
| `{melding_id}` | Public identifier of the melding. |
| `{melding_categorie_service_belofte_dagen}` | Number of days in the service promise. |
| `{melding_categorie_service_belofte_dag_type}` | Type of day unit in the service promise (for example dagen, werkdagen). |
| `{melding_categorie_service_belofte_tekst}` | Full service promise text for the category. This text may itself include placeholders. |

Template usage by field:

- subject: `{melding_id}`
- title: `{melding_id}`
- preview: `{melding_id}`
- body: `{melding_tekst}, {melding_id}, {melding_categorie_service_belofte_dagen}, {melding_categorie_service_belofte_dag_type}, {melding_categorie_service_belofte_tekst}`

