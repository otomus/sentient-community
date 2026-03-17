"""Create an Excel XLSX file from JSON data using openpyxl."""

import json
import os


def run(file_path: str, data: str) -> str:
    """
    Create an Excel file from a JSON array of arrays.

    @param file_path: Output path for the Excel file.
    @param data: JSON string containing an array of arrays, e.g. '[["Name","Age"],["Alice",30]]'.
    @returns: Confirmation message with the output path.
    @throws ImportError: If openpyxl is not installed.
    @throws ValueError: If data is not valid JSON or not an array of arrays.
    """
    try:
        import openpyxl
    except ImportError:
        return "error: " + "openpyxl is required but not installed. "
            "Install it with: pip install openpyxl"

    try:
        rows = json.loads(data)
    except json.JSONDecodeError as err:
        raise ValueError(f"Invalid JSON data: {err}")

    if not isinstance(rows, list):
        raise ValueError("Data must be a JSON array of arrays.")

    resolved = os.path.abspath(file_path)
    parent_dir = os.path.dirname(resolved)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    workbook = openpyxl.Workbook()
    worksheet = workbook.active

    for row in rows:
        if not isinstance(row, list):
            raise ValueError(
                f"Each row must be an array, got {type(row).__name__}."
            )
        worksheet.append(row)

    workbook.save(resolved)
    return f"Excel file created successfully at: {resolved}"
