{
  fieldOrNull(obj, field)::
    if obj == null || std.type(obj) != 'object' || !std.objectHas(obj, field) then null else obj[field],

  valueOrEmpty(value)::
    if value == null then '' else std.toString(value),

  asString(value)::
    if value == null then null else std.toString(value),

  hasItems(value)::
    value != null && std.type(value) == 'array' && std.length(value) > 0,
}