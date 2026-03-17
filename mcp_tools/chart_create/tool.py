"""Create chart images from JSON data using matplotlib."""

import json
import os

SUPPORTED_CHART_TYPES = ("bar", "line", "pie", "scatter")


def run(chart_type: str, data: str, output_path: str, title: str = "") -> str:
    """Create a chart image and save it to the specified path.

    @param chart_type: Type of chart (bar, line, pie, scatter).
    @param data: JSON string containing labels and values.
    @param output_path: File path for the output image.
    @param title: Optional chart title.
    @returns: Confirmation message with the output path.
    @throws ValueError: If chart_type is unsupported or data is malformed.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return "error: " + "matplotlib is required but not installed. "
            "Install it with: pip install matplotlib"

    if chart_type not in SUPPORTED_CHART_TYPES:
        raise ValueError(
            f"Unsupported chart type: {chart_type}. "
            f"Supported types: {', '.join(SUPPORTED_CHART_TYPES)}"
        )

    parsed_data = _parse_chart_data(data)
    labels = parsed_data["labels"]
    values = parsed_data["values"]

    fig, ax = plt.subplots()

    _render_chart(ax, chart_type, labels, values)

    if title:
        ax.set_title(title)

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)

    return f"Chart saved to {output_path}"


def _parse_chart_data(data: str) -> dict:
    """Parse and validate the JSON chart data."""
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as err:
        raise ValueError(f"Invalid JSON data: {err}")

    if "labels" not in parsed or "values" not in parsed:
        raise ValueError("Data must contain 'labels' and 'values' keys")

    if len(parsed["labels"]) != len(parsed["values"]):
        raise ValueError("Labels and values must have the same length")

    return parsed


def _render_chart(
    ax: "matplotlib.axes.Axes",
    chart_type: str,
    labels: list,
    values: list,
) -> None:
    """Render the appropriate chart type onto the axes."""
    if chart_type == "bar":
        ax.bar(labels, values)
    elif chart_type == "line":
        ax.plot(labels, values, marker="o")
    elif chart_type == "pie":
        ax.pie(values, labels=labels, autopct="%1.1f%%")
    elif chart_type == "scatter":
        ax.scatter(labels, values)
