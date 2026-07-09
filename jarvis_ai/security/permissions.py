"""Which command actions require an explicit on-screen confirmation before running."""

DANGEROUS_ACTIONS = frozenset({"shutdown_pc", "restart_pc", "delete_file", "delete_folder"})


def is_dangerous(action: str) -> bool:
    return action in DANGEROUS_ACTIONS
