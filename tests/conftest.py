"""Configuration file for pytest."""

import base64
import json
import os
import shutil
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Generator
from typing import Tuple

import pytest
from flask import Flask
from PIL import Image
from selenium.webdriver.common.keys import Keys
from werkzeug.datastructures import FileStorage

from tests.server import TEST_SERVER_INFO
from tests.server import build_flask_app
from tests.server import run_threaded_flask_app


def pytest_configure(config):
    """For configuring pytest with custom markers."""
    config.addinivalue_line("markers", "debug: custom marker for debugging tests.")
    config.addinivalue_line("markers", "feature: custom marker for form feature tests.")
    config.addinivalue_line("markers", "fixture: custom marker for fixture tests.")
    config.addinivalue_line("markers", "flask: custom marker for flask server tests.")
    config.addinivalue_line("markers", "schema: custom marker for schema tests.")
    config.addinivalue_line("markers", "website: custom marker for website tests.")


def get_server_info() -> Tuple[int, str]:
    """Convenience function to get test server port and submit route."""
    return TEST_SERVER_INFO["port"], TEST_SERVER_INFO["submit_route"]


def base_custom_config() -> Dict[str, Any]:
    """Defines the basic JSON config file attributes."""
    # get port and submit route
    port, submit = get_server_info()

    # build base config
    return {
        "subject": "Testing",
        "title": "Testing",
        "enable_form_download": True,
        "form_backend_url": f"http://localhost:{port}{submit}",
        "ignore_file_upload": False,
        "email": "foo@bar.com",
        "questions": [],
    }


def create_temp_websrc_dir(src: Path, dst: Path, src_files: Tuple[str, ...]) -> Path:
    """Create and populate a temporary directory with static web source files."""
    # create new destination subdir
    sub_dir = dst / "web_src"
    sub_dir.mkdir()

    # copy each file or directory from the project directory to the temporary directory
    for item_name in src_files:
        # get the path to the source file or directory in the project directory
        source_item_path = src / item_name

        # check if directory
        if source_item_path.is_dir():
            # if the item is a directory, recursively copy it
            shutil.copytree(source_item_path, sub_dir / item_name)

        else:
            # if the item is a file, copy it
            shutil.copy(source_item_path, sub_dir)

    return sub_dir


def get_project_directory() -> Path:
    """Get project directory path object."""
    # Get the path of the current file (test_file.py)
    current_file_path = Path(os.path.abspath(__file__))

    # get grand parent dir
    return current_file_path.parents[1]


def load_config_file(directory: Path) -> Dict[str, Any]:
    """Load the JSON config file at directory."""
    # open the config file in the project dir
    with open(directory / "config.json", "r", encoding="utf-8") as config:
        # load the JSON data into dict
        return json.load(config)


def write_config_file(config: Dict[str, Any], src_path: Path) -> None:
    """Write out config.json file to source path."""
    # writing dictionary to JSON file with pretty printing (2 spaces indentation)
    with open(src_path / "config.json", "w") as json_file:
        json.dump(config, json_file, indent=2)


def prepare_default_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Update the default config copy with values approprate for testing."""
    # get port and submit route
    port, submit = get_server_info()

    # update form backend
    config["form_backend_url"] = f"http://localhost:{port}{submit}"

    # update ignore file uploads
    config["ignore_file_upload"] = False

    # update input[type=file] accept attr
    for question in config["questions"]:
        # check type
        if question["type"] == "file":
            # check for custom attr
            if "custom" in question:
                # only update accept attr
                question["custom"]["accept"] = "*"

            else:
                # add custom section with accept attr
                question["custom"] = {"accept": "*"}

    # get updated config data
    return config


@pytest.fixture(scope="session")
def session_tmp_dir(tmp_path_factory) -> Path:
    """Uses temporary path factory to create a session-scoped temp path."""
    # create a temporary directory using tmp_path_factory
    return tmp_path_factory.mktemp("session_temp_dir")


@pytest.fixture(scope="function")
def dummy_txt_file_path(tmp_path) -> Path:
    """Create a dummy temporary text file."""
    # create a temporary directory
    tmpdir = tmp_path / "uploads"
    tmpdir.mkdir()

    # define the file path
    file_path = tmpdir / "test_file.txt"

    # write content to the file
    with open(file_path, "w") as f:
        f.write("This is a test file.")

    return file_path


@pytest.fixture(scope="function")
def dummy_txt_file_stream(dummy_txt_file_path) -> FileStorage:
    """Create a Flask FileStorage object from text file."""
    # create a FileStorage object
    return FileStorage(stream=open(dummy_txt_file_path, "rb"), filename="test_file.txt")


@pytest.fixture(scope="function")
def dummy_txt_file_data_url(dummy_txt_file_path) -> str:
    """Create a data URL for the dummy text file."""
    # read the content of the file
    with open(dummy_txt_file_path, "rb") as f:
        file_content = f.read()

    # encode the file content as base64
    base64_content = base64.b64encode(file_content).decode("utf-8")

    # construct the data URL with the appropriate MIME type
    return f"data:text/plain;base64,{base64_content}"


@pytest.fixture(scope="function")
def dummy_form_post_data(dummy_txt_file_stream) -> Dict[str, Any]:
    """Collection of name/value pairs to simulate form post data."""
    return {
        "name": "John Doe",
        "email": "john@example.com",
        "message": "This is a test message.",
        "text_file": dummy_txt_file_stream,
    }


@pytest.fixture(scope="function")
def dummy_jpg_file_path(tmp_path: Path) -> Path:
    """Create a dummy JPEG image."""
    # create image dir
    img_dir = tmp_path / "images"
    img_dir.mkdir()

    # create a dummy image
    img_path = img_dir / "dummy_image.jpg"
    image = Image.new("RGB", (100, 100), color="red")  # create a red image
    image.save(img_path)

    return img_path


@pytest.fixture(scope="function")
def dummy_jpg_data_url(dummy_jpg_file_path) -> str:
    """Create a data URL for the dummy JPEG file."""
    # read the content of the file
    with open(dummy_jpg_file_path, "rb") as f:
        file_content = f.read()

    # encode the file content as base64
    base64_content = base64.b64encode(file_content).decode("utf-8")

    # construct the data URL with the appropriate MIME type
    return f"data:image/jpeg;base64,{base64_content}"


@pytest.fixture(scope="function")
def dummy_form_inputs(
    dummy_jpg_file_path: Path, dummy_jpg_data_url: str
) -> Dict[str, Any]:
    """Defines the values to be submitted for each input type during form tests."""
    return {
        "date": {"date": "01012000"},
        "datetime-local": {
            "date": "01012000",
            "tab": Keys.TAB,
            "time": "1200",
            "period": "AM",
        },
        "email": "foo@bar.com",
        "file": (str(dummy_jpg_file_path), dummy_jpg_data_url),
        "number": "42",
        "selectbox": None,
        "tel": "18005554444",
        "text": "Sample text for input of type=text.",
        "textarea": "Sample text for Textarea.",
        "time": {"time": "1200", "period": "AM"},
        "url": "http://example.com",
    }


@pytest.fixture(scope="session")
def sb_test_url() -> str:
    """Simply defines the test URL for seleniumbase fixture testing."""
    return "https://seleniumbase.io/realworld/login"


@pytest.fixture(scope="function")
def project_dir() -> Path:
    """Get the path of the project directory."""
    return get_project_directory()


@pytest.fixture(scope="session")
def website_files() -> Tuple[str, ...]:
    """Declare the files necessary for serving the website."""
    # define the files and directories to copy from the project directory
    return ("index.html", "config.json", "styles", "scripts")


@pytest.fixture(scope="session")
def session_websrc_tmp_dir(
    session_tmp_dir: Path, website_files: Tuple[str, ...]
) -> Generator[Path, None, None]:
    """Create a per-session copy of the website source code for editing."""
    # project dir
    project_dir = get_project_directory()

    # create a temporary directory
    temp_dir = create_temp_websrc_dir(project_dir, session_tmp_dir, website_files)

    # get the default config
    default_config = load_config_file(temp_dir)

    # now update config.json with new backend url
    updated_config = prepare_default_config(default_config)

    # write to websrc temp copy
    write_config_file(updated_config, temp_dir)

    # provide the temporary directory path to the test function
    yield temp_dir

    # remove the temporary directory and its contents
    shutil.rmtree(temp_dir)


@pytest.fixture(scope="function")
def default_user_config(project_dir: Path) -> Dict[str, Any]:
    """Load the default config.json file."""
    return load_config_file(project_dir)


@pytest.fixture(scope="function")
def updated_user_config(default_user_config: Dict[str, Any]) -> Dict[str, Any]:
    """Updates the user config file with appropriate testing attributes."""
    return prepare_default_config(default_user_config)


@pytest.fixture(scope="session")
def session_web_app(session_websrc_tmp_dir: Path) -> Flask:
    """Create a session-scoped Flask app for testing with the website source."""
    # create app
    return build_flask_app(session_websrc_tmp_dir)


@pytest.fixture(scope="session")
def live_session_web_app_url(session_web_app: Flask) -> str:
    """Runs session-scoped Flask app in a thread."""
    # get port
    port = session_web_app.config.get("PORT")
    assert port is not None

    # start threaded app
    run_threaded_flask_app(session_web_app)

    # get url
    return f"http://localhost:{port}"


@pytest.fixture(scope="function")
def all_inputs_config(dummy_form_inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Create config file fixture for testing all supported input types."""
    # get base config
    config = base_custom_config()

    # now create questions based on supported input types
    questions = []
    for idx, input_type in enumerate(dummy_form_inputs.keys()):
        # basic question attrs
        q = {
            "label": f"Question{idx+1}",
            "name": f"testing_{input_type}_input_type",
            "type": input_type,
            "required": True,
        }

        # check for selectbox type
        if input_type == "selectbox":
            # setup options
            options = [
                {
                    "label": "--Select option--",
                    "value": "",
                    "selected": True,
                    "disabled": True,
                },
                {"label": "Option1", "value": "Opt1"},
                {"label": "Option2", "value": "Opt2"},
                {"label": "Option3", "value": "Opt3"},
                {"label": "Option4", "value": "Opt4"},
            ]

            # add them
            q["options"] = options

        # update questions
        questions.append(q)

    # now update questions
    config["questions"] = questions

    # done
    return config


@pytest.fixture(
    scope="function",
    params=[
        pytest.param("user"),
        pytest.param("all_inputs"),
    ],
)
def all_default_configs(
    request, updated_user_config: Dict[str, Any], all_inputs_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Parameterized default configs fixture."""
    # get current markers and config type
    config_type = request.param

    # match config to use
    match config_type:
        case "user":
            config = updated_user_config
        case "all_inputs":
            config = all_inputs_config

    # get appropriate config
    return config


@pytest.fixture(scope="function")
def multiple_select_options_config() -> Dict[str, Any]:
    """Custom config file fixture for testing multiple select options."""
    # get base config
    config = base_custom_config()

    # update questions
    config["questions"] = [
        {
            "label": "Select your country",
            "name": "country",
            "type": "selectbox",
            "required": True,
            "options": [
                {
                    "label": "--Select all that apply--",
                    "value": "",
                    "selected": True,
                    "disabled": True,
                },
                {"label": "USA", "value": "USA"},
                {"label": "Canada", "value": "CAN"},
                {"label": "United Kingdom", "value": "UK"},
                {"label": "Australia", "value": "AUS"},
            ],
            "custom": {"multiple": True},
        }
    ]

    # updated
    return config


@pytest.fixture(scope="function")
def ignore_upload_config() -> Dict[str, Any]:
    """Custom config file fixture for testing ignore file uploads."""
    # get base config
    config = base_custom_config()

    # set ignore
    config["ignore_file_upload"] = True

    # update questions
    config["questions"] = [
        {
            "label": "Upload funny memes",
            "name": "meme_imgs",
            "type": "file",
            "required": True,
            "custom": {
                "multiple": True,
                "accept": "*",
            },
        }
    ]

    # updated
    return config


@pytest.fixture(scope="function")
def instructions_config() -> Dict[str, Any]:
    """Custom config file fixture with multiline instructions."""
    # get base config
    config = base_custom_config()

    # set ignore
    config["instructions"] = [
        "<p>",
        "Fill out the form below, and click <b>Send</b> to submit it.",
        "If that should fail, simply click <b>Download Form</b> and manually",
        "email the completed form to:",
        "<strong class='email-placeholder'>[Email Address]</strong>.",
        "</p>",
    ]

    # update questions
    config["questions"] = [
        {
            "label": "Question 1",
            "name": "q1",
            "type": "text",
            "required": True,
        }
    ]

    # updated
    return config


@pytest.fixture(scope="function")
def multiline_question_label_config() -> Dict[str, Any]:
    """Custom config file fixture with multiline question label."""
    # get base config
    config = base_custom_config()

    # set MDN ref
    mdn_ref = "https://developer.mozilla.org/en-US/docs/Web/HTML"

    # update questions
    config["questions"] = [
        {
            "label": [
                "This is a multiline label. It is intended to make it easier to write",
                "multiline questions and include <i>interesting</i>",
                f"<a id='mdn_html_docs' href={mdn_ref!r}>HTML syntax</a>",
                "directly in your <i>question text</i>",
            ],
            "name": "multiline_html_question",
            "type": "text",
            "required": True,
        }
    ]

    # updated
    return config


@pytest.fixture(scope="function")
def disabled_form_download_config() -> Dict[str, Any]:
    """Custom config file fixture disabled form downloads."""
    # get base config
    config = base_custom_config()

    # update form downloads
    config["enable_form_download"] = False

    # update questions
    config["questions"] = [
        {
            "label": "Question 1",
            "name": "q1",
            "type": "text",
            "required": True,
        }
    ]

    # updated
    return config


@pytest.fixture(scope="function")
def missing_email_config() -> Dict[str, Any]:
    """Custom config file fixture for missing email."""
    # get base config
    config = base_custom_config()

    # remove email attr
    del config["email"]

    # update questions
    config["questions"] = [
        {
            "label": "Question 1",
            "name": "q1",
            "type": "text",
            "required": True,
        }
    ]

    # updated
    return config


@pytest.fixture(scope="function")
def custom_buttons_config() -> Dict[str, Any]:
    """Custom config file fixture for button text."""
    # get base config
    config = base_custom_config()

    # update form downloads
    config["enable_form_download"] = True

    # update submit/download button text
    config["send_button_text"] = "Custom Send Text"
    config["download_button_text"] = "Custom Download Text"

    # update questions
    config["questions"] = [
        {
            "label": "Question 1",
            "name": "q1",
            "type": "text",
            "required": True,
        }
    ]

    # updated
    return config


@pytest.fixture(scope="function")
def custom_missing_field_config() -> Dict[str, Any]:
    """Custom config file fixture for missing field alert message text."""
    # get base config
    config = base_custom_config()

    # update form downloads
    config["enable_form_download"] = True

    # update submit/download button text
    config["missing_field_message"] = "Custom Missing Field Alert"

    # update questions
    config["questions"] = [
        {
            "label": "Question 1",
            "name": "q1",
            "type": "text",
            "required": True,
        }
    ]

    # updated
    return config
