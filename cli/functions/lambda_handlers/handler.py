import json
import traceback


def main(event, context):
    _ = context
    try:
        # ruff: noqa: PLC0415
        import main as function

        main_function = function.main
    except (ImportError, AttributeError) as e:
        return {
            "status_code": 500,
            "body": json.dumps(
                {"error": "The main function could not be loaded.", "detail": str(e)}
            ),
        }

    try:
        return main_function(event)
    except Exception as e:
        return {
            "status_code": 500,
            "body": json.dumps({"error": str(e), "trace": traceback.format_exc()}),
        }
