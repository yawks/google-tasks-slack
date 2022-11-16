from datetime import datetime
import timeago


def get_value_by_action_id(view_submission: dict, action_id: str) -> str:
    value: str = ""
    if action_id != "":
        for block in view_submission["view"]["state"]["values"]:
            for entry_name in view_submission["view"]["state"]["values"][block]:
                if entry_name == action_id:
                    entry = view_submission["view"]["state"]["values"][block][entry_name]
                    value = entry.get("value",
                                      entry.get("selected_date",
                                                entry.get("selected_time",
                                                          entry.get("selected_option", {}).get("value", ""))))
                    break

    return value

def get_value_by_block_id(body: dict, block_id: str) -> str:
    value: str = ""
    if block_id != "":
        for block in body["view"]["blocks"]:
            if block["block_id"] == block_id:
                value = block.get("text", {}).get("text", "")
                break

    return value

def get_timeago(dt: datetime) -> str:
    str_timeago: str = ""
    if dt.day == datetime.now().day and dt.month == datetime.now().month and dt.year == datetime.now().year:
        str_timeago = "today"
    elif dt.day == datetime.now().day+1 and dt.month == datetime.now().month and dt.year == datetime.now().year:
        str_timeago = "tomorrow"
    elif dt.day == datetime.now().day-1 and dt.month == datetime.now().month and dt.year == datetime.now().year:
        str_timeago = "yesterday"
    else:
        str_timeago = timeago.format(dt)

    return str_timeago
