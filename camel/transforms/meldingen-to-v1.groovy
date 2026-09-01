import groovy.json.JsonOutput
import java.util.Locale

def fieldOrNull = { obj, String field ->
    if (!(obj instanceof Map) || !obj.containsKey(field)) {
        return null
    }
    obj[field]
}

def valueOrEmpty = { value ->
    value == null ? "" : value.toString()
}

def labelNames = { melding ->
    def labels = fieldOrNull(melding, "labels")
    if (!(labels instanceof List)) {
        return []
    }
    labels.collect { label -> fieldOrNull(label, "name") }
}

def sourceName = { melding ->
    def source = fieldOrNull(melding, "source")
    if (source == null) {
        return null
    }
    if (source instanceof String) {
        return source
    }
    fieldOrNull(source, "name")
}

def classification = { melding ->
    fieldOrNull(melding, "classification")
}

def categoryName = { melding ->
    def item = classification(melding)
    if (item == null || fieldOrNull(item, "name") == null) {
        return "Onbekend"
    }
    fieldOrNull(item, "name")
}

def categoryInstructions = { melding ->
    def item = classification(melding)
    item == null ? null : fieldOrNull(item, "instructions")
}

def slugify = { value ->
    if (value == null) {
        return "onbekend"
    }
    value
        .toString()
        .toLowerCase(Locale.ROOT)
        .replace(" ", "-")
        .replace("/", "-")
        .replace("&", "en")
        .replace(".", "")
}

def hasContact = { melding ->
    fieldOrNull(melding, "email") != null || fieldOrNull(melding, "phone") != null
}

def hasItems = { value ->
    value instanceof List && !value.isEmpty()
}

def mappedState = { state ->
    if (state == null) {
        return ""
    }
    switch (state.toString()) {
        case "processing_requested":
            return "i"
        case "planned":
            return "ingepland"
        case "processing":
            return "b"
        case "completed":
            return "o"
        case "canceled":
        case "cancelled":
            return "a"
        case "reopen_requested":
            return "reopen requested"
        case "reopened":
            return "reopened"
        case "submitted":
        case "new":
        case "classified":
        case "questions_answered":
        case "location_submitted":
        case "attachments_added":
        case "contact_info_added":
            return "m"
        default:
            return ""
    }
}

def mappedStateDisplay = { state ->
    if (state == null) {
        return "Onbekend"
    }
    switch (state.toString()) {
        case "processing_requested":
            return "In afwachting van behandeling"
        case "planned":
            return "Ingepland"
        case "processing":
            return "In behandeling"
        case "completed":
            return "Afgehandeld"
        case "canceled":
        case "cancelled":
            return "Geannuleerd"
        case "reopen_requested":
            return "Verzoek tot heropenen"
        case "reopened":
            return "Heropend"
        case "submitted":
        case "new":
        case "classified":
        case "questions_answered":
        case "location_submitted":
        case "attachments_added":
        case "contact_info_added":
            return "Gemeld"
        default:
            return state.toString()
    }
}

def mappedPriority = { urgency ->
    if (urgency == 1) {
        return "high"
    }
    if (urgency == -1) {
        return "low"
    }
    "normal"
}

def geometry = { melding ->
    def geoLocation = fieldOrNull(melding, "geo_location")
    geoLocation == null ? null : fieldOrNull(geoLocation, "geometry")
}

def geometryProperties = { melding ->
    def geoLocation = fieldOrNull(melding, "geo_location")
    geoLocation == null ? null : fieldOrNull(geoLocation, "properties")
}

def addressText = { melding ->
    def street = valueOrEmpty(fieldOrNull(melding, "street"))
    def houseNumber = valueOrEmpty(fieldOrNull(melding, "house_number"))
    def houseNumberAddition = valueOrEmpty(fieldOrNull(melding, "house_number_addition"))
    def postalCode = valueOrEmpty(fieldOrNull(melding, "postal_code"))
    def city = valueOrEmpty(fieldOrNull(melding, "city"))
    def base = street != "" ? street + (houseNumber != "" ? " ${houseNumber}" : "") + houseNumberAddition : (postalCode != "" ? postalCode : "Onbekend adres")
    base + (city == "" ? "" : ", ${city}")
}

def displayValue = { melding ->
    if (fieldOrNull(melding, "public_id") != null) {
        return fieldOrNull(melding, "public_id")
    }
    if (fieldOrNull(melding, "id") != null) {
        return fieldOrNull(melding, "id").toString()
    }
    "unknown"
}

def signalIdentifier = { melding ->
    if (fieldOrNull(melding, "signal_id") != null) {
        return fieldOrNull(melding, "signal_id")
    }
    displayValue(melding)
}

def inputBody = body
def pageLinks = inputBody instanceof Map ? fieldOrNull(inputBody, "_links") : null

def pageHref = { String rel ->
    fieldOrNull(fieldOrNull(pageLinks, rel), "href")
}

def inputResults =
    inputBody instanceof List ? inputBody :
        (inputBody instanceof Map && fieldOrNull(inputBody, "results") instanceof List ? fieldOrNull(inputBody, "results") : [])

def inputCount = inputBody instanceof Map && fieldOrNull(inputBody, "count") != null ? fieldOrNull(inputBody, "count") : inputResults.size()

def transformMelding = { melding ->
    def source = sourceName(melding)
    [
        _links: [:],
        _display: displayValue(melding),
        id: fieldOrNull(melding, "id"),
        id_display: displayValue(melding),
        signal_id: signalIdentifier(melding),
        text: fieldOrNull(melding, "text") == null ? "" : fieldOrNull(melding, "text"),
        status: [
            text: null,
            user: null,
            state: mappedState(fieldOrNull(melding, "state")),
            state_display: mappedStateDisplay(fieldOrNull(melding, "state")),
            target_api: null,
            extra_properties: [
                source_state: fieldOrNull(melding, "state"),
            ],
            send_email: false,
            created_at: fieldOrNull(melding, "updated_at") == null ? fieldOrNull(melding, "created_at") : fieldOrNull(melding, "updated_at"),
            email_override: null,
        ],
        location: [
            id: fieldOrNull(melding, "id"),
            stadsdeel: null,
            buurt_code: null,
            area_type_code: null,
            area_code: null,
            area_name: null,
            address: null,
            address_text: addressText(melding),
            postcode: fieldOrNull(melding, "postal_code"),
            geometrie: geometry(melding),
            extra_properties: geometryProperties(melding),
            created_by: null,
            bag_validated: false,
        ],
        category: [
            sub: categoryName(melding),
            sub_slug: slugify(categoryName(melding)),
            main: categoryName(melding),
            main_slug: slugify(categoryName(melding)),
            category_url: null,
            departments: "",
            created_by: null,
            text: categoryInstructions(melding),
            deadline: null,
            deadline_factor_3: null,
        ],
        reporter: [
            email: fieldOrNull(melding, "email"),
            phone: fieldOrNull(melding, "phone"),
            sharing_allowed: hasContact(melding),
            allows_contact: hasContact(melding),
        ],
        priority: [
            priority: mappedPriority(fieldOrNull(melding, "urgency")),
            created_by: null,
        ],
        created_at: fieldOrNull(melding, "created_at"),
        updated_at: fieldOrNull(melding, "updated_at"),
        incident_date_start: fieldOrNull(melding, "created_at"),
        incident_date_end: null,
        operational_date: null,
        has_attachments: hasItems(fieldOrNull(melding, "attachments")) ? "true" : "false",
        extra_properties: [
            public_id: fieldOrNull(melding, "public_id"),
            urgency: fieldOrNull(melding, "urgency"),
            labels: labelNames(melding),
            source_name: source,
        ],
        notes: [],
        directing_departments: [],
        routing_departments: [],
        has_parent: "false",
        has_children: "false",
        assigned_user_email: null,
    ] + (source == null ? [:] : [source: source])
}

def result = [
    _links: [
        self: [href: pageHref("self")],
        next: [href: pageHref("next")],
        previous: [href: pageHref("previous")],
    ],
    count: inputCount,
    results: inputResults.collect { melding -> transformMelding(melding) },
]

JsonOutput.toJson(result)