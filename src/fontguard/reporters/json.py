from fontguard.core.models import ScanResult


def render_json(result: ScanResult) -> str:
    return result.model_dump_json(indent=2) + "\n"
