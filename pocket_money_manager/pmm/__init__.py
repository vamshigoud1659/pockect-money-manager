"""Pocket Money Manager - core package.

Modules:
    models      - Transaction dataclass and category lists
    validation  - defensive input validation helpers
    storage     - JSON persistence + CSV import/export
    logic       - business logic: balance, summaries, search, warnings
    reports     - Markdown / text audit / CSV report export
    charts      - Matplotlib chart generation
"""

APP_NAME = "Pocket Money Manager"
VERSION = "1.0.0"
