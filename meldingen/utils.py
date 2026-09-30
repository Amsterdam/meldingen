class SafeTemplateDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def format_safe(template: str, mapping: dict) -> str:
    return template.format_map(SafeTemplateDict(mapping))
