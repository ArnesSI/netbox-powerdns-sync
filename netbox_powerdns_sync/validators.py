from django.core.validators import RegexValidator


hostname_validator = RegexValidator(
    r"^(?:[a-zA-Z0-9][a-zA-Z0-9\-]{0,63}\.)*$",
    "Only alphanumeric chars, hyphens and dots allowed",
)

zone_validator = RegexValidator(
    r"\.$",
    "Zone name must end with a dot",
)