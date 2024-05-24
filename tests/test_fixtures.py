"""Test the fixtures used in the tests."""

import json
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Tuple

import pytest
from bs4 import BeautifulSoup
from flask import Flask
from seleniumbase import BaseCase

from tests.conftest import load_config_file
from tests.schema import check_config_schema


def check_files_subset(source_dir: Path, webfiles: Tuple[str, ...]) -> bool:
    """Check if subset of files is found in another directory."""
    # create sets
    source_dir_set = set([str(entry.name) for entry in source_dir.iterdir()])
    webfiles_set = set(webfiles)

    # check subset
    return webfiles_set.issubset(source_dir_set)


@pytest.mark.fixture
def test_websrc_in_project_dir(
    project_dir: Path, website_files: Tuple[str, ...]
) -> None:
    """Simply confirm that the website files are in the project dir path."""
    assert check_files_subset(project_dir, website_files)


@pytest.mark.fixture
def test_websrc_in_temp_dir(
    session_websrc_tmp_dir: Path, website_files: Tuple[str, ...]
) -> None:
    """Simply confirm that the website files are in the temp web source dir."""
    assert check_files_subset(session_websrc_tmp_dir, website_files)


@pytest.mark.fixture
def test_config_keys_in_form_inputs(
    default_user_config: Dict[str, Any], dummy_form_inputs: Dict[str, Any]
) -> None:
    """Check that keys from config.json are present in form input testing fixture."""
    # get types from questions section of config.json
    question_types = [q["type"] for q in default_user_config["questions"]]

    # check config question types missing form inputs (if any)
    missing_keys = set(question_types) - set(dummy_form_inputs)

    # no missing keys
    assert (
        not missing_keys
    ), f"Keys found in config.json are absent from test inputs : {missing_keys}"


@pytest.mark.fixture
def test_hello_world_sb(sb: BaseCase, sb_test_url: str) -> None:
    """Just test if SeleniumBase can work on hello world example from docs."""
    # open the browser to the login example page
    sb.open(sb_test_url)

    # type the username/password and mfa code
    sb.type("#username", "demo_user")
    sb.type("#password", "secret_pass")
    sb.enter_mfa_code("#totpcode", "GAXG2MTEOR3DMMDG")  # 6-digit

    # check that login succeeded
    sb.assert_element("img#image1")
    sb.assert_exact_text("Welcome!", "h1")
    sb.click('a:contains("This Page")')

    # save screenshot for confirmation
    sb.save_screenshot_to_logs()


@pytest.mark.flask
@pytest.mark.fixture
def test_index_route(session_web_app: Flask) -> None:
    """Test the index route."""
    client = session_web_app.test_client()
    response = client.get("/")
    assert response.status_code == 200


@pytest.mark.flask
@pytest.mark.fixture
def test_other_root_files_route(session_web_app: Flask) -> None:
    """Test the route for serving other root files."""
    client = session_web_app.test_client()
    response = client.get("/config.json")
    assert response.status_code == 200


@pytest.mark.flask
@pytest.mark.fixture
def test_serve_styles_route(session_web_app: Flask) -> None:
    """Test the route for serving CSS files."""
    client = session_web_app.test_client()
    response = client.get("/styles/form.css")
    assert response.status_code == 200


@pytest.mark.flask
@pytest.mark.fixture
def test_serve_scripts_route(session_web_app: Flask) -> None:
    """Test the route for serving JavaScript files."""
    client = session_web_app.test_client()
    response = client.get("/scripts/form.js")
    assert response.status_code == 200


@pytest.mark.flask
@pytest.mark.fixture
def test_submit_form_route(
    session_web_app: Flask,
    dummy_form_post_data: Dict[str, Any],
    dummy_txt_file_data_url: str,
) -> None:
    """Test the route for submitting a form."""
    # get client
    client = session_web_app.test_client()

    # submit response
    response = client.post(
        "/submit", data=dummy_form_post_data, content_type="multipart/form-data"
    )

    # assert that the response status code is 200 (OK)
    assert response.status_code == 200

    # get content
    content = response.data.decode("utf-8")

    # check response html header
    assert "Contact Form Response" in content

    # parse the HTML response
    soup = BeautifulSoup(response.data, "html.parser")

    # find the container div
    container = soup.find("div", class_="container")
    assert container is not None, "Container div not found in HTML response"

    # find and extract form data from the HTML
    form_data = {}
    labels = container.find_all("label")
    for label in labels:
        key = label["for"]
        # find the <p> tag associated with the label
        p_tag = label.find_next_sibling("p")
        if p_tag:
            # find the <a> tag within the <p> tag
            a_tag = p_tag.find("a")
            if a_tag:
                # extract the value of the "href" attribute from the <a> tag
                value = a_tag.get("href")
            else:
                # if <a> tag is not found, set value to None
                value = " ".join(p_tag.stripped_strings)
            form_data[key] = value

    # define expected form data
    expected_form_data = {
        "name": dummy_form_post_data["name"],
        "email": dummy_form_post_data["email"],
        "message": dummy_form_post_data["message"],
        "text_file": dummy_txt_file_data_url,
    }

    # assert that the form data matches the expected form data
    for key in expected_form_data:
        assert (
            form_data[key] == expected_form_data[key]
        ), "Form data in HTML response does not match expected form data"


@pytest.mark.flask
@pytest.mark.fixture
def test_update_config_route(session_web_app: Flask) -> None:
    """Test the route for updating the configuration."""
    client = session_web_app.test_client()

    # send a POST request with JSON data to update the configuration
    new_config = {"key": "value"}
    post_response = client.post("/update_config", json=new_config)

    # check that the POST request was successful (status code 200)
    assert post_response.status_code == 200

    # check json exists
    assert post_response.json is not None

    # retrieve the token from the response
    token = post_response.json.get("token")
    assert token is not None

    # send a GET request to "/config" to retrieve the updated config
    get_response = client.get("/config.json")

    # check if the GET request was successful (status code 200)
    assert get_response.status_code == 200

    # check the response content to verify the updated config data
    config_data = json.loads(get_response.data)
    assert config_data == new_config


@pytest.mark.flask
@pytest.mark.fixture
def test_reset_config_route(session_web_app: Flask) -> None:
    """Test the route for resetting the configuration."""
    client = session_web_app.test_client()

    # store original config data
    old_config_data_response = client.get("/config.json")
    old_config_data = json.loads(old_config_data_response.data)

    # send a POST request with JSON data to update the configuration
    new_config = {"key": "value"}
    post_response = client.post("/update_config", json=new_config)

    # check that the POST request was successful (status code 200)
    assert post_response.status_code == 200

    # now, send a GET request to "/config" to retrieve the updated config
    get_response = client.get("/config.json")

    # check if the GET request was successful (status code 200)
    assert get_response.status_code == 200

    # check the response content to verify the updated config data
    config_data = json.loads(get_response.data)
    assert config_data == new_config

    # send a GET request to reset the configuration
    reset_response = client.get("/reset_config")

    # check that the request was successful (status code 200)
    assert reset_response.status_code == 200

    # now, send a GET request to "/config" to retrieve the reset config
    reset_config_response = client.get("/config.json")

    # check if the GET request for reset config was successful (status code 200)
    assert reset_config_response.status_code == 200

    # check the response content to verify the reset config data
    reset_config_data = json.loads(reset_config_response.data)
    assert reset_config_data == old_config_data


@pytest.mark.flask
@pytest.mark.fixture
def test_port_in_app_config(session_web_app: Flask) -> None:
    """Confirm port has been set in Flask app config."""
    assert "PORT" in session_web_app.config, "PORT key not set"


@pytest.mark.flask
@pytest.mark.fixture
def test_session_config_form_backend_updated(
    session_websrc_tmp_dir: Path, session_web_app: Flask
) -> None:
    """Make sure config file has been updated with url."""
    # load config file
    config = load_config_file(session_websrc_tmp_dir)

    # get config
    client = session_web_app.test_client()
    response = client.get("/config.json")

    # verify the response status code
    assert response.status_code == 200

    # convert the response content to JSON
    json_data = json.loads(response.data)

    # check that key is in config
    key = "form_backend_url"
    assert key in json_data
    assert key in config

    # check configs match
    assert config[key] == json_data[key]


@pytest.mark.fixture
def test_all_inputs_config_schema(all_inputs_config: Dict[str, Any]) -> None:
    """Check that the config.json schema for all inputs config is correct."""
    assert check_config_schema(all_inputs_config)


@pytest.mark.fixture
def test_all_default_configs_upload_files(all_default_configs: Dict[str, Any]) -> None:
    """Check that all the default configs upload files."""
    # check config for file upload attr
    assert not all_default_configs[
        "ignore_file_upload"
    ], "Default site configs should not ignore file uploads."


@pytest.mark.fixture
def test_multi_options_config_schema(
    multiple_select_options_config: Dict[str, Any]
) -> None:
    """Check that the given config.json schema for multi select options is correct."""
    assert check_config_schema(multiple_select_options_config)


@pytest.mark.fixture
def test_multi_options_config_input_type(
    multiple_select_options_config: Dict[str, Any]
) -> None:
    """Check that input[type=selectbox]."""
    assert (
        multiple_select_options_config["questions"][0]["type"] == "selectbox"
    ), "Input type is not selectbox."


@pytest.mark.fixture
def test_multi_opts_config_multiple(
    multiple_select_options_config: Dict[str, Any]
) -> None:
    """Confirm that the multi selection options config has multiple options."""
    # get questions
    question = multiple_select_options_config["questions"][0]

    # check multiple options
    assert len(question["options"]) > 1

    # check custom.multiple attr set
    assert question["custom"]["multiple"]


@pytest.mark.fixture
def test_multi_opts_config_defaults(
    multiple_select_options_config: Dict[str, Any]
) -> None:
    """Check that at least one options is selected and disabled."""
    # get options
    options = multiple_select_options_config["questions"][0]["options"]

    # results store
    results = []

    # loop over options
    for opt in options:
        # check for default
        results.append(opt.get("selected", False) and opt.get("disabled", False))

    # now check results
    assert any(results)


@pytest.mark.fixture
def test_ignore_upload_config_schema(ignore_upload_config: Dict[str, Any]) -> None:
    """Check that the given config.json schema for ignore uploads is correct."""
    assert check_config_schema(ignore_upload_config)


@pytest.mark.fixture
def test_ignore_upload_config_input_type(ignore_upload_config: Dict[str, Any]) -> None:
    """Check that input[type=file]."""
    assert (
        ignore_upload_config["questions"][0]["type"] == "file"
    ), "Input type is not file."


@pytest.mark.fixture
def test_ignore_upload_attr_set(ignore_upload_config: Dict[str, Any]) -> None:
    """Check that the fixture has the correct attribute set."""
    assert ignore_upload_config[
        "ignore_file_upload"
    ], "Not configured to ignore file uploads."


@pytest.mark.fixture
def test_ignore_upload_custom_attrs(ignore_upload_config: Dict[str, Any]) -> None:
    """Check that the cusom attributes are properly set."""
    # get custom attrs
    custom = ignore_upload_config["questions"][0]["custom"]

    # now check
    assert (
        custom["multiple"] and custom["accept"] == "*"
    ), "Custom attributes not properly set."


@pytest.mark.fixture
def test_instructions_config_schema(instructions_config: Dict[str, Any]) -> None:
    """Check that the given config.json schema for iinstructions is correct."""
    assert check_config_schema(instructions_config)


@pytest.mark.fixture
def test_confirm_instructions_attr_set(instructions_config: Dict[str, Any]) -> None:
    """Confirm that the instructions attribute is set."""
    # check exists
    assert instructions_config["instructions"]

    # check type list
    assert isinstance(instructions_config["instructions"], list)


@pytest.mark.fixture
def test_html_instructions_present(instructions_config: Dict[str, Any]) -> None:
    """Check that there is HTML in the instructions."""
    # get instructions
    instruct_text = " ".join(instructions_config["instructions"])

    # confirm HTML
    soup = BeautifulSoup(instruct_text, "html.parser")
    assert len(soup.find_all()) > 0


@pytest.mark.fixture
def test_email_placeholder_present(instructions_config: Dict[str, Any]) -> None:
    """Confirm that the email-placeholder class is present."""
    # convert to full string
    instruction_text = " ".join(instructions_config["instructions"])

    assert "email-placeholder" in instruction_text


@pytest.mark.fixture
def test_label_list_type(multiline_question_label_config: Dict[str, Any]) -> None:
    """Check that the type of the question label is a list."""
    # get question
    question = multiline_question_label_config["questions"][0]

    # now check type of questions
    assert isinstance(question["label"], list)


@pytest.mark.fixture
def test_html_label_present(multiline_question_label_config: Dict[str, Any]) -> None:
    """Check that HTML is present in the question label."""
    # get question
    question = multiline_question_label_config["questions"][0]

    # get instructions
    label_text = " ".join(question["label"])

    # confirm HTML
    soup = BeautifulSoup(label_text, "html.parser")
    assert len(soup.find_all()) > 0


@pytest.mark.fixture
def test_disabled_downloads_config_schema(
    disabled_form_download_config: Dict[str, Any]
) -> None:
    """Check that the given config.json schema for disabled form downloads is good."""
    assert check_config_schema(disabled_form_download_config)


@pytest.mark.fixture
def test_downloads_disabled(disabled_form_download_config: Dict[str, Any]) -> None:
    """Check that the necessary attribute is false."""
    assert not disabled_form_download_config["enable_form_download"]


@pytest.mark.fixture
def test_missing_email_config_schema(missing_email_config: Dict[str, Any]) -> None:
    """Check that the given config.json schema for no email is correct."""
    assert check_config_schema(missing_email_config)


@pytest.mark.fixture
def test_custom_buttons_config_schema(custom_buttons_config: Dict[str, Any]) -> None:
    """Check that the given config.json schema for custom buttons is correct."""
    assert check_config_schema(custom_buttons_config)


@pytest.mark.fixture
def test_custom_missing_field_config_schema(
    custom_missing_field_config: Dict[str, Any]
) -> None:
    """Check that the given config.json schema for missing field is correct."""
    assert check_config_schema(custom_missing_field_config)
