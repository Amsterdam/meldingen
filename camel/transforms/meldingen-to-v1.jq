def fieldOrNull($obj; $field):
  if ($obj == null) or (($obj | type) != "object") or (($obj | has($field)) | not) then null else $obj[$field] end;

def valueOrEmpty($value):
  if $value == null then "" else ($value | tostring) end;

def labelNames($melding):
  if fieldOrNull($melding; "labels") == null then []
  else [fieldOrNull($melding; "labels")[]? | fieldOrNull(.; "name")]
  end;

def sourceName($melding):
  (fieldOrNull($melding; "source")) as $source
  | if $source == null then null
    elif ($source | type) == "string" then $source
    else fieldOrNull($source; "name")
    end;

def classification($melding):
  fieldOrNull($melding; "classification");

def categoryName($melding):
  (classification($melding)) as $item
  | if $item == null or fieldOrNull($item; "name") == null then "Onbekend" else fieldOrNull($item; "name") end;

def categoryInstructions($melding):
  (classification($melding)) as $item
  | if $item == null then null else fieldOrNull($item; "instructions") end;

def slugify($value):
  if $value == null then "onbekend"
  else ($value | tostring | ascii_downcase | gsub(" "; "-") | gsub("/"; "-") | gsub("&"; "en") | gsub("\\."; ""))
  end;

def hasContact($melding):
  fieldOrNull($melding; "email") != null or fieldOrNull($melding; "phone") != null;

def hasItems($value):
  $value != null and (($value | type) == "array") and (($value | length) > 0);

def mappedState($state):
  if $state == null then ""
  elif $state == "processing_requested" then "i"
  elif $state == "planned" then "ingepland"
  elif $state == "processing" then "b"
  elif $state == "completed" then "o"
  elif $state == "canceled" or $state == "cancelled" then "a"
  elif $state == "reopen_requested" then "reopen requested"
  elif $state == "reopened" then "reopened"
  elif $state == "submitted" or $state == "new" or $state == "classified" or $state == "questions_answered" or $state == "location_submitted" or $state == "attachments_added" or $state == "contact_info_added" then "m"
  else ""
  end;

def mappedStateDisplay($state):
  if $state == "processing_requested" then "In afwachting van behandeling"
  elif $state == "planned" then "Ingepland"
  elif $state == "processing" then "In behandeling"
  elif $state == "completed" then "Afgehandeld"
  elif $state == "canceled" or $state == "cancelled" then "Geannuleerd"
  elif $state == "reopen_requested" then "Verzoek tot heropenen"
  elif $state == "reopened" then "Heropend"
  elif $state == "submitted" or $state == "new" or $state == "classified" or $state == "questions_answered" or $state == "location_submitted" or $state == "attachments_added" or $state == "contact_info_added" then "Gemeld"
  elif $state == null then "Onbekend"
  else ($state | tostring)
  end;

def mappedPriority($urgency):
  if $urgency == 1 then "high"
  elif $urgency == -1 then "low"
  else "normal"
  end;

def geometry($melding):
  (fieldOrNull($melding; "geo_location")) as $geoLocation
  | if $geoLocation == null then null else fieldOrNull($geoLocation; "geometry") end;

def geometryProperties($melding):
  (fieldOrNull($melding; "geo_location")) as $geoLocation
  | if $geoLocation == null then null else fieldOrNull($geoLocation; "properties") end;

def addressText($melding):
  (valueOrEmpty(fieldOrNull($melding; "street"))) as $street
  | (valueOrEmpty(fieldOrNull($melding; "house_number"))) as $houseNumber
  | (valueOrEmpty(fieldOrNull($melding; "house_number_addition"))) as $houseNumberAddition
  | (valueOrEmpty(fieldOrNull($melding; "postal_code"))) as $postalCode
  | (valueOrEmpty(fieldOrNull($melding; "city"))) as $city
  | (if $street != "" then
       $street + (if $houseNumber != "" then " " + $houseNumber else "" end) + $houseNumberAddition
     elif $postalCode != "" then
       $postalCode
     else
       "Onbekend adres"
     end) as $base
  | $base + (if $city == "" then "" else ", " + $city end);

def displayValue($melding):
  if fieldOrNull($melding; "public_id") != null then fieldOrNull($melding; "public_id")
  elif fieldOrNull($melding; "id") != null then (fieldOrNull($melding; "id") | tostring)
  else "unknown"
  end;

def signalIdentifier($melding):
  if fieldOrNull($melding; "signal_id") != null then fieldOrNull($melding; "signal_id")
  else displayValue($melding)
  end;

def pageLinks:
  if (type) == "object" then fieldOrNull(.; "_links") else null end;

def pageHref($rel):
  pageLinks as $pageLinks
  | fieldOrNull(fieldOrNull($pageLinks; $rel); "href");

def inputResults:
  if (type) == "array" then .
  elif (type) == "object" and has("results") and ((.results | type) == "array") then .results
  else []
  end;

def inputCount:
  if (type) == "object" and has("count") and .count != null then .count
  else (inputResults | length)
  end;

def transformMelding($melding):
  {
    _links: {},
    _display: displayValue($melding),
    id: fieldOrNull($melding; "id"),
    id_display: displayValue($melding),
    signal_id: signalIdentifier($melding),
    text: (if fieldOrNull($melding; "text") == null then "" else fieldOrNull($melding; "text") end),
    status: {
      text: null,
      user: null,
      state: mappedState(fieldOrNull($melding; "state")),
      state_display: mappedStateDisplay(fieldOrNull($melding; "state")),
      target_api: null,
      extra_properties: {
        source_state: fieldOrNull($melding; "state")
      },
      send_email: false,
      created_at: (if fieldOrNull($melding; "updated_at") == null then fieldOrNull($melding; "created_at") else fieldOrNull($melding; "updated_at") end),
      email_override: null
    },
    location: {
      id: fieldOrNull($melding; "id"),
      stadsdeel: null,
      buurt_code: null,
      area_type_code: null,
      area_code: null,
      area_name: null,
      address: null,
      address_text: addressText($melding),
      postcode: fieldOrNull($melding; "postal_code"),
      geometrie: geometry($melding),
      extra_properties: geometryProperties($melding),
      created_by: null,
      bag_validated: false
    },
    category: {
      sub: categoryName($melding),
      sub_slug: slugify(categoryName($melding)),
      main: categoryName($melding),
      main_slug: slugify(categoryName($melding)),
      category_url: null,
      departments: "",
      created_by: null,
      text: categoryInstructions($melding),
      deadline: null,
      deadline_factor_3: null
    },
    reporter: {
      email: fieldOrNull($melding; "email"),
      phone: fieldOrNull($melding; "phone"),
      sharing_allowed: hasContact($melding),
      allows_contact: hasContact($melding)
    },
    priority: {
      priority: mappedPriority(fieldOrNull($melding; "urgency")),
      created_by: null
    },
    created_at: fieldOrNull($melding; "created_at"),
    updated_at: fieldOrNull($melding; "updated_at"),
    incident_date_start: fieldOrNull($melding; "created_at"),
    incident_date_end: null,
    operational_date: null,
    has_attachments: (if hasItems(fieldOrNull($melding; "attachments")) then "true" else "false" end),
    extra_properties: {
      public_id: fieldOrNull($melding; "public_id"),
      urgency: fieldOrNull($melding; "urgency"),
      labels: labelNames($melding),
      source_name: sourceName($melding)
    },
    notes: [],
    directing_departments: [],
    routing_departments: [],
    has_parent: "false",
    has_children: "false",
    assigned_user_email: null
  } + (if sourceName($melding) == null then {} else {source: sourceName($melding)} end);

{
  _links: {
    self: {href: pageHref("self")},
    next: {href: pageHref("next")},
    previous: {href: pageHref("previous")}
  },
  count: inputCount,
  results: [inputResults[] | transformMelding(.)]
}