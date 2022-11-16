from __future__ import print_function
import os
from typing import List, Optional, Tuple

from flask import Flask, request
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt import App
from google_tasks import GoogleTasksList, create_task, create_tasklist, delete_task, get_task, get_tasklist_by_title, get_tasklists, toggle_task_completion, toggle_task_favorite, update_task
import utils
# f rom jinja2 import Environment, FileSystemLoader, TemplateNotFound


# Use the package we installed

flask_app = Flask(__name__)

# Initializes your app with your bot token and signing secret
app = App(
    # token=SLACK_BOT_TOKEN,
    # signing_secret=SLACK_SIGNING_SECRET
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)
handler = SlackRequestHandler(app)


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)


@app.shortcut("new_task_from_message")
def handle_new_task_from_mesage(ack, body, logger, client):
    ack()
    logger.info(body)
    channel_id = body["channel"]["id"]
    ts = body["message"]["ts"]
    text = body.get("message", {}).get("text", "")
    first_line = text if len(text) < 70 else text.split("\n")[0][:70] + "..."
    client.views_open(
        trigger_id=body["trigger_id"],
        view=get_modal(modal_title="Create a task",
                       task_title=first_line,
                       task_description=text,
                       task_link=f":slack: <https://dydu-ai.slack.com/app_redirect?channel={channel_id}&message_ts={ts}|Slack message link>")
    )


@app.shortcut("new_task")
def show_new_task_modal(ack, body, logger, client):
    ack()
    logger.info(body)

    client.views_open(
        trigger_id=body["trigger_id"],
        view=get_modal(modal_title="Create a task")
    )


def get_tasklist_modal():
    return {
        "title": {
            "type": "plain_text",
            "text": "Create a tasklist"
        },
        "submit": {
            "type": "plain_text",
            "text": "Submit"
        },
        "blocks": [
            {
                "type": "input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "tasklist-name",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Enter a task list name"
                    },
                },
                "label": {
                    "type": "plain_text",
                            "text": "Tasklist name",
                    "emoji": True
                }
            }
        ],
        "type": "modal",
        "callback_id": "tasklist-creation"
    }


def get_confirmation_modal(modal_title: str, text: str, external_id: str = ""):
    return {
        "title": {
            "type": "plain_text",
            "text": modal_title
        },
        "external_id": external_id,
        "submit": {
            "type": "plain_text",
            "text": "Submit"
        },
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text
                }
            }
        ],
        "type": "modal",
        "callback_id": "after-confirmation"
    }


def get_modal(modal_title: str, task_title: str = "", task_description: str = "", task_duedate: str = "", task_duetime: str = "", external_id: str = "", tasklistname: str = "", task_link: str = ""):
    tasklists_json = []
    initial_tasklist = None
    for tasklist in get_tasklists():
        item = {
            "text": {
                "type": "plain_text",
                "text": tasklist.name,
                "emoji": True
            },
            "value": tasklist.name
        }
        if tasklistname == tasklist.name:
            initial_tasklist = item
        tasklists_json.append(item)

    modal = {
        "title": {
            "type": "plain_text",
            "text": modal_title
        },
        "external_id": external_id,
        "submit": {
            "type": "plain_text",
            "text": "Submit"
        },
        "blocks": [
            {
                "type": "input",
                "element": {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select an item",
                        "emoji": True
                    },
                    "options": tasklists_json,
                    "action_id": "tasklist-name"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Task list",
                    "emoji": True
                }
            },
            {
                "type": "input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "task-title",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Summary single-line input"
                    },
                    "initial_value": task_title
                },
                "label": {
                    "type": "plain_text",
                    "text": "Task summary"
                },
            },
            {
                "type": "input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "task-description",
                    "multiline": True,
                    "min_length": 0,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Task description"
                    },
                    "initial_value": task_description
                },
                "label": {
                    "type": "plain_text",
                    "text": "Description"
                },
            },
            {
                "type": "section",
                "block_id": "section1234",
                "text": {
                    "type": "mrkdwn",
                    "text": "Pick a date for the deadline."
                },
                "accessory": {
                    "type": "datepicker",
                    "action_id": "task-datepicker",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select a date"
                    }
                },

            },


            # , # time cannot be set or read through task API
            # {
            #    "type": "section",
            #    "block_id": "section_time",
            #    "text": {
            #        "type": "mrkdwn",
            #        "text": "Pick a time for the deadline."
            #    },
            #    "accessory": {
            #        "type": "timepicker",
            #        "action_id": "task-timepicker",
            #        "placeholder": {
            #            "type": "plain_text",
            #            "text": "Select a Time"
            #        }
            #    }
            # }
        ],
        "type": "modal",
        "callback_id": "task-edition"
    }

    if initial_tasklist is not None:
        modal["blocks"][0]["element"]["initial_option"] = initial_tasklist

    if task_duedate != "":
        modal["blocks"][3]["accessory"]["initial_date"] = task_duedate

    if task_link != "":
        modal["blocks"].append(
            {
                "type": "section",
                "block_id": "task-link",
                "text": {
                    "type": "mrkdwn",
                    "text": task_link
                },
            }
        )

    # if task_duetime != "":
    #    modal["blocks"][4]["accessory"]["initial_time"] = task_duetime

    return modal


def _get_task_items(body: dict) -> Tuple[str, str, str, Optional[GoogleTasksList]]:
    task_title = utils.get_value_by_action_id(body, "task-title")
    task_description = utils.get_value_by_action_id(
        body, "task-description")
    task_duedate = utils.get_value_by_action_id(
        body, "task-datepicker")
    tasklist: Optional[GoogleTasksList] = get_tasklist_by_title(
        tasklist_title=utils.get_value_by_action_id(body, "tasklist-name"))
    # task_duetime = utils.get_value_by_action_id(
    #    body, "task-timepicker")
    return task_title, task_description, task_duedate, tasklist  # , task_duetime


@app.view("after-confirmation")
def after_confirmation(ack, body, client, logger):
    ack()
    logger.info(body["view"]["state"]["values"])
    completed = False
    split = body["view"]["external_id"].split("-")
    action = split[0]
    tasklist_id = split[1]
    task_id = split[2]
    if action == "delete":
        completed = delete_task(tasklist_id=tasklist_id, task_id=task_id)

    show_tasklists(client, body["user"]["id"], logger, completed=completed)


@app.view("tasklist-creation")
def tasklist_creation(ack, body, client, logger):
    ack()
    logger.info(body["view"]["state"]["values"])
    create_tasklist(utils.get_value_by_action_id(body, "tasklist-name"))

    show_tasklists(client, body["user"]["id"], logger)


@app.view("task-edition")
def view_submission(ack, body, client, logger):
    ack()
    logger.info(body["view"]["state"]["values"])
    completed: bool = False
    task_title, task_description, task_duedate, tasklist = _get_task_items(
        body)
    if tasklist is not None:
        if body["view"]["external_id"] != "":
            # existing task
            split = body["view"]["external_id"].split("-")
            action = split[0]
            old_tasklist_id = split[1]
            task_id = split[2]
            if action == "update":
                completed = update_task(new_tasklist_id=tasklist.tasklist_id,
                                        old_tasklist_id=old_tasklist_id,
                                        task_id=task_id,
                                        task_title=task_title,
                                        task_description=task_description,
                                        task_duedate=task_duedate)
                #                       task_duetime=task_duetime
        else:
            # new task
            #task_links = []
            task_link = utils.get_value_by_block_id(body, "task-link")
            if task_link != "":
                # task links not supported when create a task through API
                """
                task_links.append({
                    "link" : task_link.replace(":slack: ", "").split("|")[0][1:],
                    "type" : "email",
                    "description" : task_link.split("|")[1][:-1]
                })
                """
                task_description += f"\n\n{task_link}"
            create_task(task_title=task_title,
                        tasklist_id=tasklist.tasklist_id,
                        task_description=task_description,
                        task_duedate=task_duedate)
            #           task_links=task_links)
            #           task_duetime=task_duetime)

    show_tasklists(client, body["user"]["id"], logger, completed=completed)


@app.action("app-home-nav-create-a-task")
def create_task_from_home(ack, body, client, logger):
    ack()
    logger.info(body)

    client.views_open(
        trigger_id=body["trigger_id"],
        view=get_modal(modal_title="Create a task")
    )


@app.action("app-home-nav-create-a-task-list")
def create_tasklist_from_home(ack, body, client, logger):
    ack()
    logger.info(body)

    client.views_open(
        trigger_id=body["trigger_id"],
        view=get_tasklist_modal()
    )


@app.event("app_home_opened")
def update_home_tab(client, event, logger):
    show_tasklists(client, event["user"], logger)


@app.action("app-home-completed-tasks")
def udate_app_home_completed_tasks(ack, body, client, logger):
    ack()
    show_tasklists(client, body["user"]["id"], logger, completed=True)


@app.action("app-home-open-tasks")
def udate_app_home_open_tasks(ack, body, client, logger):
    ack()
    show_tasklists(client, body["user"]["id"], logger, completed=False)


@app.action("menu-overflow-action")
def tasks_clicked(ack, body, client, logger):
    ack()
    external_id = body["actions"][0]["selected_option"]["value"]
    values = external_id.split("-")
    action = values[0]
    tasklist_id = values[1]
    task_id = values[2]
    completed: bool = False
    if action == "edit":
        gtask = get_task(tasklist_id=tasklist_id, task_id=task_id)
        if gtask is not None:
            client.views_open(
                trigger_id=body["trigger_id"],
                view=get_modal(modal_title="Edit task",
                               external_id=f"update-{tasklist_id}-{task_id}",
                               task_title=gtask.title,
                               task_description=gtask.notes,
                               tasklistname=gtask.tasklist.name,
                               task_duedate=gtask.get_due_date())
                # task_duetime=gtask.get_due_time())
            )
        show_tasklists(client, body["user"]["id"], logger, completed=completed)
    elif action in ["complete", "uncomplete"]:
        completed = toggle_task_completion(
            tasklist_id=tasklist_id, task_id=task_id)
        show_tasklists(client, body["user"]["id"], logger, completed=completed)
    elif action in ["favorite", "unfavorite"]:
        completed = toggle_task_favorite(
            tasklist_id=tasklist_id, task_id=task_id)
        show_tasklists(client, body["user"]["id"], logger, completed=completed)
    elif action == "delete":
        gtask = get_task(tasklist_id=tasklist_id, task_id=task_id)
        if gtask is not None:
            client.views_open(
                trigger_id=body["trigger_id"],
                view=get_confirmation_modal(modal_title="Delete task",
                                            external_id=external_id,
                                            text=f"Are you sure to delete the task  \"_{gtask.title}_\" ?",
                                            )
            )


# @app.action("task-timepicker")
# def action_timepicker(ack, body, logger):
#     ack()
#     logger.info(body)

@app.action("task-datepicker")
def eaction_datepicker(ack, body, logger):
    ack()
    logger.info(body)


def show_tasklists(client, user, logger, completed=False):
    try:
        task_lists: List[GoogleTasksList] = get_tasklists(completed)
        nb_tasks = 0
        for task_list in task_lists:
            nb_tasks += task_list.get_open_tasks()
        status = "open" if not completed else "closed"
        view = {
            "type": "home",
            "callback_id": "home_view",
            "blocks": [
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "action_id": "app-home-open-tasks",
                            "text": {
                                "type": "plain_text",
                                "text": "Open tasks",
                                "emoji": True
                            }
                        },
                        {
                            "type": "button",
                            "action_id": "app-home-completed-tasks",
                            "text": {
                                "type": "plain_text",
                                "text": "Completed tasks",
                                "emoji": True
                            }
                        },
                        {
                            "type": "button",
                            "action_id": "app-home-nav-create-a-task",
                            "text": {
                                "type": "plain_text",
                                "text": "Create task",
                                "emoji": True
                            }
                        },
                        {
                            "type": "button",
                            "action_id": "app-home-nav-create-a-task-list",
                            "text": {
                                "type": "plain_text",
                                "text": "Create task list",
                                "emoji": True
                            }
                        }
                    ]
                },
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"You have {nb_tasks} {status} task" + ("s" if nb_tasks > 1 else ""),
                        "emoji": True
                    }
                }
            ]
        }

        for task_list in task_lists:
            view["blocks"].append({
                "type": "divider"
            })
            view["blocks"].append(
                {
                    "type": "header",
                    "text": {
                            "type": "plain_text",
                            "text": task_list.name,
                            "emoji": True
                    }
                })
            view["blocks"].extend(task_list.to_slack_json_obj())

        client.views_publish(
            user_id=user,
            view=view
        )
    except Exception as e:
        logger.error(f"Error publishing home : {e}")


if __name__ == "__main__":
    SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN")).start()
