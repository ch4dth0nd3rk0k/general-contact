"""Test all features of website."""

from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Generator
from typing import List
from typing import Optional
from typing import Tuple

import pytest
import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from seleniumbase import BaseCase

from tests.schema import check_config_schema


def any_required_questions(questions: List[Dict[str, Any]]) -> bool:
    """Determines if any questions are required."""
    return any(q["required"] for q in questions)


def check_required_inputs_border_red(
    red_outlined_required_html: str,
) -> Generator[bool, None, None]:
    """Check if all the required inputs are red outlined."""
    # parse the HTML
    soup = BeautifulSoup(red_outlined_required_html, "html.parser")

    # find all input, textarea, and select elements
    input_elements = soup.find_all(["input", "textarea", "select"])

    # iterate through each input element
    for element in input_elements:
        # check if the 'required' attribute is present
        required = "required" in element.attrs

        # check if the border color is red
        color = "red" in element.get("style", "")

        if required:
            # should be red outlined
            yield required and color
        else:
            # should be left alone
            yield not color


def read_html_file(file_path: Path) -> str:
    """Open an HTML file and return contents as string."""
    with open(file_path, "r") as file:
        html_content = file.read()
    return html_content


def convert_to_isoformat(
    date: Optional[str] = None,
    time: Optional[str] = None,
    period: Optional[str] = None,
    **kwargs,
) -> str:
    """Converts a datetime-local test input into ISO 8601 format."""
    # Initialize variables for date and time objects
    date_obj = None
    time_obj = None

    # Check for valid input
    if date is None and time is None:
        raise ValueError("Either date or time must be provided")

    # Convert date string to datetime object
    if date is not None:
        date_obj = datetime.strptime(date, "%d%m%Y")

    # Convert time string to datetime object
    if time is not None:
        if period is None:
            raise ValueError("Period (AM/PM) must be provided for time conversion")
        time_str = f"{time} {period}"
        time_obj = datetime.strptime(time_str, "%I%M %p")

    # Determine final string based on date and time presence
    final_str = ""
    if date_obj and time_obj:
        final_str = datetime.combine(date_obj.date(), time_obj.time()).strftime(
            "%Y-%m-%dT%H:%M"
        )
    elif date_obj:
        final_str = date_obj.strftime("%Y-%m-%d")
    elif time_obj:
        final_str = time_obj.strftime("%H:%M")

    return final_str


def select_options(question: Dict[str, Any]) -> str:
    """Chose selection from options."""
    # count number of options NOT disabled
    for option in question["options"]:
        # check if disabled present
        if option.get("disabled", False):
            # skip disabled options
            continue

        else:
            # end
            break

    # get the first valid option
    return option["value"]


def fill_out_form(
    form_element: WebElement, config: Dict[str, Any], form_inputs: Dict[str, Any]
) -> Generator[Tuple[str, str], None, None]:
    """Programmatically fill out form and yield name/value pairs."""
    # loop over questions
    for question in config["questions"]:
        # now get element with name
        input_element = form_element.find_element(By.NAME, question["name"])

        # get tag element type
        tag_name = input_element.tag_name.lower()

        # control flow for different types
        if tag_name == "input" or tag_name == "textarea":
            # get the type
            input_type = input_element.get_attribute("type")

            # check input_type
            assert input_type is not None

            # get test value for input type
            test_value = form_inputs[input_type]

            # check if date/time dict
            if isinstance(test_value, dict):
                # now loop over multiple input steps
                for sub_input in test_value.values():
                    # send it
                    input_element.send_keys(sub_input)

                # now update test value
                test_value = convert_to_isoformat(**test_value)

            # check if file tuple
            elif isinstance(test_value, tuple):
                # unpack
                file_path, data_url = test_value

                # send file path
                input_element.send_keys(file_path)

                # update test value
                test_value = data_url

            else:
                # just normal
                input_element.send_keys(test_value)

            # generate
            yield question["name"], test_value

        elif tag_name == "select":
            # get sample selection from options
            sample_option = select_options(question)

            # find all option elements within the select element
            option_elements = input_element.find_elements(By.TAG_NAME, "option")

            # loop through the option elements and select the desired one
            for option_element in option_elements:
                # basically get first option that is not empty (i.e. a default)
                if option_element.get_attribute("value") == sample_option:
                    # click it ...
                    option_element.click()

            # generate
            yield question["name"], sample_option


def extract_received_form_input(
    response_html: str,
) -> Generator[Tuple[str, str], None, None]:
    """Extract input received from form submission."""
    # parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(response_html, "html.parser")

    # find the container element
    container = soup.find("div", class_="container")

    # find all label elements within the container
    labels = container.find_all("label")

    # iterate over the labels to retrieve the key-value pairs
    for label in labels:
        # get label's "for" attribute as key
        key = label["for"]

        # now find the value element
        value_element = label.find_next_sibling("p")

        # check if sub elements exist within the <p> tag
        sub_elements = value_element.find_all(["a", "img", "video", "audio"])

        # found sub elements ...
        if sub_elements:
            # set storage
            data_url = ""

            # loop over them
            for element in sub_elements:
                # check for "other" type
                if element.name == "a":
                    # get "href" attribute as value
                    data_url = element.get("href", "")

                elif element.name in ["img", "video", "audio"]:
                    # get "src" attribute as value
                    data_url = element.get("src", "")

            # finally convert to tuple
            yield key, data_url

        else:
            # if no sub elements exist, clean and yield the text value
            received_value = value_element.text.strip()
            yield key, received_value


@pytest.mark.website
def test_config_schema(all_default_configs: Dict[str, Any]) -> None:
    """Check that the given config.json schema is correct."""
    assert check_config_schema(all_default_configs)


@pytest.mark.website
def test_normal_display(
    sb: BaseCase, live_session_web_app_url: str, all_default_configs: Dict[str, Any]
) -> None:
    """Simply tests that the website is displaying normally."""
    # update config
    response = requests.post(
        live_session_web_app_url + "/update_config", json=all_default_configs
    )

    # check response
    assert response.status_code == 200

    # get token
    token = response.json().get("token")
    assert token is not None

    # update site URL
    site_url = f"{live_session_web_app_url}?token={token}"

    # open site
    sb.open(site_url)

    # verify that the container element is visible
    sb.assert_element_visible(".container")

    # verify that the form element is present
    sb.assert_element_present("form#contact-form")

    # verify that the instructions element is present
    sb.assert_element_present("#instructions")

    # save screenshot for confirmation
    sb.save_screenshot_to_logs()


@pytest.mark.website
def test_file_uploads_enabled(
    sb: BaseCase,
    live_session_web_app_url: str,
    all_default_configs: Dict[str, Any],
) -> None:
    """Test that the file uploads are enabled on the website."""
    # update config
    response = requests.post(
        live_session_web_app_url + "/update_config", json=all_default_configs
    )

    # check response
    assert response.status_code == 200

    # get token
    token = response.json().get("token")
    assert token is not None

    # update site URL
    site_url = f"{live_session_web_app_url}?token={token}"

    # open site
    sb.open(site_url)

    # check for any input file types
    file_inputs = sb.find_elements("input[type='file']")

    # only if inputs found
    if file_inputs:
        # get form
        form_element = sb.get_element("form")

        # get the enctype attribute
        enctype_value = form_element.get_attribute("enctype")

        # make sure it's multipart
        assert enctype_value == "multipart/form-data"


@pytest.mark.website
def test_custom_title_works(
    sb: BaseCase, live_session_web_app_url: str, all_default_configs: Dict[str, Any]
) -> None:
    """Test that title is dynamically updated from config.json."""
    # update config
    response = requests.post(
        live_session_web_app_url + "/update_config", json=all_default_configs
    )

    # check response
    assert response.status_code == 200

    # get token
    token = response.json().get("token")
    assert token is not None

    # update site URL
    site_url = f"{live_session_web_app_url}?token={token}"

    # open site
    sb.open(site_url)

    # get the title of the webpage
    title = sb.get_title()

    # check email in text
    assert all_default_configs["title"] == title


@pytest.mark.website
def test_form_backend_updated(
    sb: BaseCase, live_session_web_app_url: str, all_default_configs: Dict[str, Any]
) -> None:
    """Check that the form backend url has been updated correctly."""
    # update config
    response = requests.post(
        live_session_web_app_url + "/update_config", json=all_default_configs
    )

    # check response
    assert response.status_code == 200

    # get token
    token = response.json().get("token")
    assert token is not None

    # update site URL
    site_url = f"{live_session_web_app_url}?token={token}"

    # open site
    sb.open(site_url)

    # find the form element
    form_element = sb.get_element("form")

    # make sure it exists
    assert form_element is not None

    # get the value of the "action" attribute of the form element
    form_target = form_element.get_attribute("action")

    # make sure it exists
    assert form_target is not None

    # now check that it is the right url
    assert form_target == live_session_web_app_url + "/submit"


@pytest.mark.website
def test_form_submission(
    sb: BaseCase,
    live_session_web_app_url: str,
    dummy_form_inputs: Dict[str, Any],
    all_default_configs: Dict[str, Any],
) -> None:
    """Check that the given form upon completion can be succesfully submitted."""
    # update config
    response = requests.post(
        live_session_web_app_url + "/update_config", json=all_default_configs
    )

    # check response
    assert response.status_code == 200

    # get token
    token = response.json().get("token")
    assert token is not None

    # update site URL
    site_url = f"{live_session_web_app_url}?token={token}"

    # open site
    sb.open(site_url)

    # find the form element
    form_element = sb.get_element("form")

    # fill out form
    submitted_input = {
        k: v
        for k, v in fill_out_form(form_element, all_default_configs, dummy_form_inputs)
    }

    # save screeshot for comfirmation of form entries
    sb.save_screenshot_to_logs()

    # get send button ...
    send_button = form_element.find_element(By.ID, "send_button")

    # ... now click it
    send_button.click()

    # check that the form was submitted
    sb.assert_text("Contact Form Response")

    # get the HTML content of the response
    response_html = sb.get_page_source()

    # get received input from Flask response html
    received_input = {k: v for k, v in extract_received_form_input(response_html)}

    # check keys are same
    missing_keys = set(submitted_input) - set(received_input)
    assert not missing_keys, f"Keys are not the same: {missing_keys}"

    # now check values
    for key in submitted_input.keys():
        # get values
        value1 = submitted_input[key]
        value2 = received_input[key]

        # check
        assert (
            value1 == value2
        ), f"Submitted input: {value1} differs from received: {value2}"

    # save screenshot for confirmation of response
    sb.save_screenshot_to_logs()


@pytest.mark.website
def test_form_submission_required_constraint(
    sb: BaseCase,
    live_session_web_app_url: str,
    all_default_configs: Dict[str, Any],
) -> None:
    """Check form denies submission if a required question is unanswered."""
    # update config
    response = requests.post(
        live_session_web_app_url + "/update_config", json=all_default_configs
    )

    # check response
    assert response.status_code == 200

    # get token
    token = response.json().get("token")
    assert token is not None

    # update site URL
    site_url = f"{live_session_web_app_url}?token={token}"

    # open site
    sb.open(site_url)

    # find the form element
    form_element = sb.get_element("form")

    # get send button ...
    send_button = form_element.find_element(By.ID, "send_button")

    # store page source before
    page_source = {"before": sb.get_page_source()}

    # check for required questions
    required_questions_present = any_required_questions(
        all_default_configs["questions"]
    )

    # ... now click it
    send_button.click()

    # check alert message
    if required_questions_present:
        sb.wait_for_and_accept_alert()

    # now store it after
    page_source["after"] = sb.get_page_source()

    # should see red outlined required questions
    assert all(check_required_inputs_border_red(page_source["after"]))

    # save screenshot for confirmation
    sb.save_screenshot_to_logs()


@pytest.mark.website
def test_form_download(
    sb: BaseCase,
    live_session_web_app_url: str,
    dummy_form_inputs: Dict[str, Any],
    all_default_configs: Dict[str, Any],
) -> None:
    """Check that the given form upon completion can be succesfully downloaded."""
    # make sure form downloads are enabled
    if all_default_configs.get("enable_form_download", False):
        # update config
        response = requests.post(
            live_session_web_app_url + "/update_config", json=all_default_configs
        )

        # check response
        assert response.status_code == 200

        # get token
        token = response.json().get("token")
        assert token is not None

        # update site URL
        site_url = f"{live_session_web_app_url}?token={token}"

        # open site
        sb.open(site_url)

        # find the form element
        form_element = sb.get_element("form")

        # fill out form
        submitted_input = {
            k: v
            for k, v in fill_out_form(
                form_element, all_default_configs, dummy_form_inputs
            )
        }

        # save screeshot for comfirmation of form entries
        sb.save_screenshot_to_logs()

        # check download dir
        download_dir = sb.get_downloads_folder()

        # download file name
        dwnld_file = "contact_form_response.html"

        # delete any previousl created downloads
        sb.delete_downloaded_file_if_present(f"{download_dir}/{dwnld_file}")

        # get download button ...
        download_button = form_element.find_element(By.ID, "download_button")

        # ... now click it ...
        download_button.click()

        # ... and make sure file is present in downloads dir
        sb.assert_downloaded_file(dwnld_file)

        # now get path to downloaded form response
        download_path = sb.get_path_of_downloaded_file(dwnld_file)

        # read HTML download file into string
        download_html = read_html_file(download_path)

        # get received input from Flask response html
        received_input = {k: v for k, v in extract_received_form_input(download_html)}

        # check keys are same
        missing_keys = set(submitted_input) - set(received_input)
        assert not missing_keys, f"Keys are not the same: {missing_keys}"

        # now check values
        for key in submitted_input.keys():
            # get values
            value1 = submitted_input[key]
            value2 = received_input[key]

            # check
            assert (
                value1 == value2
            ), f"Submitted input: {value1} differs from received: {value2}"

        # open downloaded file in seleniumbase
        sb.open("file://" + download_path)

        # check download html file opened in browser
        sb.assert_text("Contact Form Response")

        # save screenshot for confirmation
        sb.save_screenshot_to_logs()


@pytest.mark.website
def test_form_download_required_constraint(
    sb: BaseCase,
    live_session_web_app_url: str,
    all_default_configs: Dict[str, Any],
) -> None:
    """Check form denies download if a required question is unanswered."""
    # make sure form downloads are enabled
    if all_default_configs.get("enable_form_download", False):
        # update config
        response = requests.post(
            live_session_web_app_url + "/update_config", json=all_default_configs
        )

        # check response
        assert response.status_code == 200

        # get token
        token = response.json().get("token")
        assert token is not None

        # update site URL
        site_url = f"{live_session_web_app_url}?token={token}"

        # open site
        sb.open(site_url)

        # find the form element
        form_element = sb.get_element("form")

        # get send button ...
        download_button = form_element.find_element(By.ID, "download_button")

        # store page source before
        page_source = {"before": sb.get_page_source()}

        # check for required questions
        required_questions_present = any_required_questions(
            all_default_configs["questions"]
        )

        # ... now click it
        download_button.click()

        # check alert message
        if required_questions_present:
            sb.wait_for_and_accept_alert()

        # now store it after
        page_source["after"] = sb.get_page_source()

        # should see red outlined required questions
        assert all(check_required_inputs_border_red(page_source["after"]))

        # save screenshot for confirmation
        sb.save_screenshot_to_logs()


@pytest.mark.feature
def test_select_multiple_options(
    sb: BaseCase,
    live_session_web_app_url: str,
    multiple_select_options_config: Dict[str, Any],
) -> None:
    """Confirm multiple options can be selected."""
    # update config
    response = requests.post(
        live_session_web_app_url + "/update_config", json=multiple_select_options_config
    )

    # check response
    assert response.status_code == 200

    # get token
    token = response.json().get("token")
    assert token is not None

    # update site URL
    site_url = f"{live_session_web_app_url}?token={token}"

    # open site
    sb.open(site_url)

    # get question name
    question_name = multiple_select_options_config["questions"][0]["name"]

    # get list of options
    options = multiple_select_options_config["questions"][0]["options"]

    # setup submitted input
    submitted_input = {question_name: ""}

    # get selectable values
    values = [attrs["value"] for attrs in options if attrs["value"]]

    # now click all options
    for v in values:
        # select option by value
        sb.select_option_by_value(f"select[name={question_name!r}]", v)

    # now updated submitted input
    submitted_input[question_name] = ", ".join(values)

    # screenshot selected options
    sb.save_screenshot_to_logs()

    # get form
    form_element = sb.get_element("form")

    # get send button ...
    send_button = form_element.find_element(By.ID, "send_button")

    # ... now click it
    send_button.click()

    # check that the form was submitted
    sb.assert_text("Contact Form Response")

    # get the HTML content of the response
    response_html = sb.get_page_source()

    # get received input from Flask response html
    received_input = {k: v for k, v in extract_received_form_input(response_html)}

    # check keys are same
    missing_keys = set(submitted_input) - set(received_input)
    assert not missing_keys, f"Keys are not the same: {missing_keys}"

    # now check values
    for key in submitted_input.keys():
        # get values
        value1 = submitted_input[key]
        value2 = received_input[key]

        # check
        assert (
            value1 == value2
        ), f"Submitted input: {value1} differs from received: {value2}"

    # save screenshot for confirmation of submission
    sb.save_screenshot_to_logs()


@pytest.mark.feature
def test_first_select_unselects_default(
    sb: BaseCase,
    live_session_web_app_url: str,
    multiple_select_options_config: Dict[str, Any],
    dummy_form_inputs: Dict[str, Any],
) -> None:
    """Confirm default select option is unselected after first selection clicked."""
    # update config
    response = requests.post(
        live_session_web_app_url + "/update_config", json=multiple_select_options_config
    )

    # check response
    assert response.status_code == 200

    # get token
    token = response.json().get("token")
    assert token is not None

    # update site URL
    site_url = f"{live_session_web_app_url}?token={token}"

    # open site
    sb.open(site_url)

    # find the select element using css selector
    select_element = sb.find_element("select")

    # get the selected option
    default_option = select_element.find_element(
        By.CSS_SELECTOR, "option[selected='selected']"
    )

    # make sure default is selected
    assert "Select all that apply" in default_option.text

    # save screeshot for comfirmation of defaults
    sb.save_screenshot_to_logs()

    # find the form element
    form_element = sb.get_element("form")

    # fill out form
    _ = {
        k: v
        for k, v in fill_out_form(
            form_element, multiple_select_options_config, dummy_form_inputs
        )
    }

    # save screeshot for comfirmation of form entries
    sb.save_screenshot_to_logs()

    # get the selected option
    selected_options = select_element.find_elements(
        By.CSS_SELECTOR, "option[selected='selected']"
    )

    # make sure default is NOT selected
    assert any(("Select all that apply" in opt.text for opt in selected_options))


@pytest.mark.feature
def test_select_default_submission_rejected(
    sb: BaseCase,
    live_session_web_app_url: str,
    multiple_select_options_config: Dict[str, Any],
) -> None:
    """Confirm that default select options will not pass for submission."""
    # update config
    response = requests.post(
        live_session_web_app_url + "/update_config", json=multiple_select_options_config
    )

    # check response
    assert response.status_code == 200

    # get token
    token = response.json().get("token")
    assert token is not None

    # update site URL
    site_url = f"{live_session_web_app_url}?token={token}"

    # open site
    sb.open(site_url)

    # get form
    form_element = sb.get_element("form")

    # get send button ...
    send_button = form_element.find_element(By.ID, "send_button")

    # store page source before
    page_source = {"before": sb.get_page_source()}

    # ... now click it
    send_button.click()

    # switch to the alert and get its text
    alert_text = sb.switch_to_alert().text

    # now accept it
    sb.accept_alert()

    # make sure alert texts match
    assert alert_text == "Please fill out all required fields."

    # now store it after
    page_source["after"] = sb.get_page_source()

    # should NOT see contact form response
    assert "Contact Form Response" not in page_source["after"]

    # get screenshot
    sb.save_screenshot_to_logs()


@pytest.mark.feature
def test_ignore_file_uploads(
    sb: BaseCase,
    live_session_web_app_url: str,
    ignore_upload_config: Dict[str, Any],
    dummy_form_inputs: Dict[str, Any],
) -> None:
    """Confirm that setting ignore file upload attrs works."""
    # update config
    response = requests.post(
        live_session_web_app_url + "/update_config", json=ignore_upload_config
    )

    # check response
    assert response.status_code == 200

    # get token
    token = response.json().get("token")
    assert token is not None

    # update site URL
    site_url = f"{live_session_web_app_url}?token={token}"

    # open new site
    sb.open(site_url)

    # get form
    form_element = sb.get_element("form")

    # get the enctype attribute
    enctype_value = form_element.get_attribute("enctype")

    # make sure it's multipart
    assert enctype_value == "application/x-www-form-urlencoded"

    # get dummy file info
    dummy_path, dummy_url = dummy_form_inputs["file"]

    # update
    dummy_form_inputs["file"] = (dummy_path, Path(dummy_path).name)

    # fill out form
    submitted_input = {
        k: v
        for k, v in fill_out_form(form_element, ignore_upload_config, dummy_form_inputs)
    }

    # save screeshot for comfirmation of form entries
    sb.save_screenshot_to_logs()

    # get send button ...
    send_button = form_element.find_element(By.ID, "send_button")

    # ... now click it
    send_button.click()

    # check that the form was submitted
    sb.assert_text("Contact Form Response")

    # get the HTML content of the response
    response_html = sb.get_page_source()

    # get received input from Flask response html
    received_input = {k: v for k, v in extract_received_form_input(response_html)}

    # check keys are same
    missing_keys = set(submitted_input) - set(received_input)
    assert not missing_keys, f"Keys are not the same: {missing_keys}"

    # now check values
    for key in submitted_input.keys():
        # get values
        value1 = submitted_input[key]
        value2 = received_input[key]

        # check
        assert (
            value1 == value2
        ), f"Submitted input: {value1} differs from received: {value2}"

    # save screenshot for confirmation of response
    sb.save_screenshot_to_logs()


@pytest.mark.feature
def test_instructions_added(
    sb: BaseCase, live_session_web_app_url: str, instructions_config: Dict[str, Any]
) -> None:
    """Check that instrucstions in config file get added to website."""
    # update config
    response = requests.post(
        live_session_web_app_url + "/update_config", json=instructions_config
    )

    # check response
    assert response.status_code == 200

    # get token
    token = response.json().get("token")
    assert token is not None

    # update site URL
    site_url = f"{live_session_web_app_url}?token={token}"

    # open new site
    sb.open(site_url)

    # get instructions text
    form_instruct_text = sb.get_text("#instructions")

    # confirm no HTML
    soup = BeautifulSoup(form_instruct_text, "html.parser")
    assert len(soup.find_all()) == 0

    # get original instruct multiline str (list)
    original_text = " ".join(instructions_config["instructions"])

    # now get diff ratio
    diff_seq = SequenceMatcher(None, form_instruct_text, original_text)

    # check strings are similar enough
    assert diff_seq.real_quick_ratio()

    # get screenshot
    sb.save_screenshot_to_logs()


@pytest.mark.feature
def test_email_added(
    sb: BaseCase, live_session_web_app_url: str, instructions_config: Dict[str, Any]
) -> None:
    """Confirm email is being added if present."""
    # update config
    response = requests.post(
        live_session_web_app_url + "/update_config", json=instructions_config
    )

    # check response
    assert response.status_code == 200

    # get token
    token = response.json().get("token")
    assert token is not None

    # update site URL
    site_url = f"{live_session_web_app_url}?token={token}"

    # open new site
    sb.open(site_url)

    # get instructions text
    form_instruct_text = sb.get_text("#instructions")

    # check email
    assert instructions_config["email"] in form_instruct_text

    # get screenshot
    sb.save_screenshot_to_logs()


@pytest.mark.feature
def test_html_label_rendered(
    sb: BaseCase,
    live_session_web_app_url: str,
    multiline_question_label_config: Dict[str, Any],
) -> None:
    """Confirm that the HTML label is present and rendered correctly."""
    # update config
    response = requests.post(
        live_session_web_app_url + "/update_config",
        json=multiline_question_label_config,
    )

    # check response
    assert response.status_code == 200

    # get token
    token = response.json().get("token")
    assert token is not None

    # update site URL
    site_url = f"{live_session_web_app_url}?token={token}"

    # open new site
    sb.open(site_url)

    # get screenshot
    sb.save_screenshot_to_logs()

    # get form
    form_element = sb.get_element("form")

    # get label
    label = form_element.find_element(By.TAG_NAME, "label")

    # confirm no HTML
    soup = BeautifulSoup(label.text, "html.parser")
    assert len(soup.find_all()) == 0

    # get question attr
    question = multiline_question_label_config["questions"][0]

    # get unrendered label text
    unrendered_label_text = " ".join(question["label"])

    # now get diff ratio
    diff_seq = SequenceMatcher(None, label.text, unrendered_label_text)

    # check strings are similar enough
    assert diff_seq.real_quick_ratio()

    # now get current URL
    preclick_url = sb.get_current_url()

    # find the link
    link_element = form_element.find_element(By.TAG_NAME, "a")

    # click on the <a> link
    link_element.click()

    # now get new url
    postclick_url = sb.get_current_url()

    # make sure URLs differ
    assert preclick_url != postclick_url

    # check for mozilla
    assert "mozilla" in postclick_url

    # get screenshot
    sb.save_screenshot_to_logs()


@pytest.mark.feature
def test_form_download_disabled(
    sb: BaseCase,
    live_session_web_app_url: str,
    disabled_form_download_config: Dict[str, Any],
) -> None:
    """Check that the download button is not visible when downloads disabled."""
    # update config
    response = requests.post(
        live_session_web_app_url + "/update_config", json=disabled_form_download_config
    )

    # check response
    assert response.status_code == 200

    # get token
    token = response.json().get("token")
    assert token is not None

    # update site URL
    site_url = f"{live_session_web_app_url}?token={token}"

    # open site
    sb.open(site_url)

    # make sure download is not visible ...
    assert not sb.is_element_visible("button#download_button")

    # ... but that send is visible
    assert sb.is_element_visible("button#send_button")

    # save screenshot for confirmation
    sb.save_screenshot_to_logs()


@pytest.mark.feature
def test_no_email(
    sb: BaseCase,
    live_session_web_app_url: str,
    missing_email_config: Dict[str, Any],
) -> None:
    """Check that the form target is correct if email is missing."""
    # update config
    response = requests.post(
        live_session_web_app_url + "/update_config", json=missing_email_config
    )

    # check response
    assert response.status_code == 200

    # get token
    token = response.json().get("token")
    assert token is not None

    # update site URL
    site_url = f"{live_session_web_app_url}?token={token}"

    # open site
    sb.open(site_url)

    # get form
    form_element = sb.get_element("form")

    # get the enctype attribute
    enctype_value = form_element.get_attribute("enctype")

    # make sure it's multipart
    assert enctype_value == "application/x-www-form-urlencoded"

    # save screenshot for confirmation
    sb.save_screenshot_to_logs()


@pytest.mark.feature
def test_custom_button_text(
    sb: BaseCase,
    live_session_web_app_url: str,
    custom_buttons_config: Dict[str, Any],
) -> None:
    """Check that the form buttons have the right custom text."""
    # update config
    response = requests.post(
        live_session_web_app_url + "/update_config", json=custom_buttons_config
    )

    # check response
    assert response.status_code == 200

    # get token
    token = response.json().get("token")
    assert token is not None

    # update site URL
    site_url = f"{live_session_web_app_url}?token={token}"

    # open site
    sb.open(site_url)

    # get form
    form_element = sb.get_element("form")

    # get send/download buttons ...
    send_button = form_element.find_element(By.ID, "send_button")
    download_button = form_element.find_element(By.ID, "download_button")

    # get custom text from fixture
    expected_send_text = custom_buttons_config["send_button_text"]
    expected_download_text = custom_buttons_config["download_button_text"]

    # check custom text is set
    assert (
        send_button.text == expected_send_text
    ), f"Expected {expected_send_text!r} but got {send_button.text!r}"
    assert (
        download_button.text == expected_download_text
    ), f"Expected {expected_download_text!r} but got '{download_button.text!r}"


@pytest.mark.feature
def test_missing_field_text(
    sb: BaseCase,
    live_session_web_app_url: str,
    custom_missing_field_config: Dict[str, Any],
) -> None:
    """Check that the form buttons have the right custom text."""
    # update config
    response = requests.post(
        live_session_web_app_url + "/update_config", json=custom_missing_field_config
    )

    # check response
    assert response.status_code == 200

    # get token
    token = response.json().get("token")
    assert token is not None

    # update site URL
    site_url = f"{live_session_web_app_url}?token={token}"

    # open site
    sb.open(site_url)

    # get form
    form_element = sb.get_element("form")

    # get send/download buttons ...
    send_button = form_element.find_element(By.ID, "send_button")
    download_button = form_element.find_element(By.ID, "download_button")

    # get custom missing field message
    custom_message = custom_missing_field_config["missing_field_message"]

    # ... now click it
    send_button.click()

    # switch to the alert and get its text
    send_alert_text = sb.switch_to_alert().text

    # now accept it
    sb.accept_alert()

    # make sure alert texts match
    assert (
        send_alert_text == custom_message
    ), f"Expected {custom_message!r} but got {send_alert_text!r}"

    # ... now click it
    download_button.click()

    # switch to the alert and get its text
    dwnld_alert_text = sb.switch_to_alert().text

    # now accept it
    sb.accept_alert()

    # make sure alert texts match
    assert (
        dwnld_alert_text == custom_message
    ), f"Expected {custom_message!r} but got {dwnld_alert_text!r}"
