"""PII Classifier and context sanitizer (T-204, Constitution Principle 8: Least Privilege & Privacy)."""

import re
from typing import List, Set
from dforge.tools.profiling.profiler import TableProfile


PII_PATTERNS = [
    r"name",
    r"email",
    r"phone",
    r"ssn",
    r"social_security",
    r"card_number",
    r"credit_card",
    r"password",
    r"secret",
    r"ip_address",
    r"first_name",
    r"last_name",
    r"full_name",
]


class PIIMasker:
    """Detects and masks PII columns before schema summaries reach LLM agent prompts."""

    @staticmethod
    def identify_pii_columns(table_profile: TableProfile) -> Set[str]:
        pii_cols: Set[str] = set()
        for col in table_profile.columns:
            name_lower = col.name.lower()
            for pattern in PII_PATTERNS:
                if re.search(pattern, name_lower):
                    pii_cols.add(col.name)
                    break
        return pii_cols

    @classmethod
    def sanitize_profile_for_llm(cls, table_profile: TableProfile) -> TableProfile:
        """Returns a copy of TableProfile where PII values are redacted from LLM context."""
        pii_cols = cls.identify_pii_columns(table_profile)
        sanitized_cols = []
        for col in table_profile.columns:
            col_dict = col.model_dump()
            if col.name in pii_cols:
                col_dict["min_value"] = "[REDACTED_PII]"
                col_dict["max_value"] = "[REDACTED_PII]"
            sanitized_cols.append(col_dict)

        sanitized_profile_data = table_profile.model_dump()
        sanitized_profile_data["columns"] = sanitized_cols
        return TableProfile.model_validate(sanitized_profile_data)
