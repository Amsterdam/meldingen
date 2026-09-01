def normalize_state:
  tostring
  | ascii_downcase
  | gsub(" "; "_")
  | gsub("-"; "_");

def map_state_to_v2:
  . as $normalized
  | if $normalized == "" then []
    elif $normalized == "m" then ["submitted"]
    elif $normalized == "i" then ["processing_requested"]
    elif $normalized == "b" then ["processing"]
    elif $normalized == "ingepland" then ["planned"]
    elif $normalized == "o" then ["completed"]
    elif $normalized == "a" then ["canceled"]
    elif $normalized == "reopen_requested" then ["reopen_requested"]
    elif $normalized == "reopened" then ["reopened"]
    elif $normalized == "submitted" then ["submitted"]
    elif $normalized == "processing_requested" then ["processing_requested"]
    elif $normalized == "processing" then ["processing"]
    elif $normalized == "planned" then ["planned"]
    elif $normalized == "completed" then ["completed"]
    elif $normalized == "canceled" or $normalized == "cancelled" then ["canceled"]
    else [$normalized]
    end;

(. // "")
| tostring
| if . == "" then [] else split(",") end
| map(normalize_state | map_state_to_v2)
| flatten
| join(",")