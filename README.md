[![tests](https://github.com/DiogenesAnalytics/parley/actions/workflows/tests.yml/badge.svg)](https://github.com/DiogenesAnalytics/parley/actions/workflows/tests.yml)
[![docker](https://github.com/DiogenesAnalytics/parley/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/DiogenesAnalytics/parley/actions/workflows/docker-publish.yml)
[![pages-build-deployment](https://github.com/DiogenesAnalytics/parley/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/DiogenesAnalytics/parley/actions/workflows/pages/pages-build-deployment)

# Parley
*(noun)*

**Pronunciation:** /ˈpɑːrli/

**Definition:**
A formal discussion or negotiation between parties, especially enemies, typically to
resolve a conflict or dispute peacefully. It often implies a temporary truce or
cessation of hostilities to facilitate dialogue.

**Example Sentence:**
The warring factions agreed to a parley at the neutral ground to seek a diplomatic
solution to their long-standing conflict.

## Introduction
The motivation behind this software is simple: to develop a completely static
**HTML Form** that can be deployed anywhere (including on **GitHub Pages**), to allow
for simple *configuration* (i.e. no need to edit the **web source** directly) using
a **JSON** file (`config.json`), and for the software to be **RIGOROUSLY** tested
(using `pytest`) to prove the features work. That is what `Parley` is about: a
_"once for all"_ solution for those who need a *simple*, *testable*, and *stable*
*form solution* **now**.

## Features
Here we will attempt to list all the features that are *available* and *tested* in the
software:

+ **configuration through JSON**: the website is meant to be configured/customized
  through the `config.json` file (see below).

+ **HTML in configurable text**: all text meant to be *configured* through the
  `config.json` file work with **HTML** tags (including `instructions`, and
  `question` labels):
  ```JSON
  {
    "instructions": "<i>All</i> work and <b>NO</b> play make Jack a dull boy.",
  }
  ```

+ **multiline strings with arrays**: all text meant to be *configured* through the
  `config.json` file can be of type *string* or type *array* (i.e. `instructions`, and
  `question` labels):
  ```JSON
  {
    "questions": [
      {
        "label": [
          "This is a very long question that could span multiple lines and easily",
          "extend off the page. It can also have an",
          "<a href='https://developer.mozilla.org/en-US/docs/Web/HTML'>HTML Link</a>",
          "embedded into it as mentioned in the previous feature explanation.",
          "You can easily write LONG LONG questions and style or add links to the",
          "questions using <b>HTML syntax</b>."
        ],
        "name": "message",
        "type": "textarea",
        "required": true
      }
    ]
  }
  ```

+ **custom usage instructions**: the *instructions* for using the form have been made
  configurable through the `config.json` file, allowing for a custom usage message to
  be supplied to the client.

+ **email in usage instructions** by adding **HTML tag** with the `class` property set
  to `email-placeholder` placeholder, your *email* will be extracted from the
  `config.json` file and rendered into the text:
  ```HTML
  Send form to: <strong class='email-placeholder'>[Email Address]</strong>.
  ```

## Usage
Here we outline the `Parley` software's *intended* use. Specifically we will go over
the `config.json` schema and what is *supported* vs. *disallowed*.

### Configuration
Below is a minimal *configuration* of the `Parley` software:
```JSON
{
  "instructions": "Your custom form usage instructions",
  "subject": "Your Form Subject",
  "title": "Your Custom Title",
  "send_button_text": "Custom Submit Text",
  "download_button_text": "Custom Download Text",
  "missing_field_message": "Custom Missing Field Alert Message",
  "enable_form_download": true,
  "form_backend_url": null,
  "ignore_file_upload": false,
  "email": "your_email@example.com",
  "questions": [
    {
      "label": "Message",
      "name": "message",
      "type": "textarea",
      "required": true
    }
  ]
}
```
The above *example config* file is written in **JSON**, and each *attribute* will be
explained below in more detail (**NOTE**: attributes with a __*__ mark are
**required**):

+ `instructions`: The (**optional**) custom form usage instructions.
+ `subject`(__*__): The *email subject* that will be submitted by the form.
+ `title`(__*__): The text that will be set in the **title** element.
+ `send_button_text`: Set custom text for send button (**optional**).
+ `download_button_text`: Set custom text for download buttin (**optional**).
+ `missing_field_message`: Set custom missing field alert text (**optional**).
+ `enable_form_download`: Allow form to be downloaded (**optional**).
+ `form_backend_url`: The (**optional**) form backend URL for submitting forms to.
+ `ignore_file_upload`: When true files will not be uploaded (**optional**).
+ `email`: The (**optional**) email used by the **mailto** attribute and used in the
  *instructions* above the form.
+ `questions`(__*__): The questions used to dynamically populate the form.
  + `label`(__*__): The actual *question* text placed above the form input field.
  + `name`(__*__): The *variable* name used as the _"key"_  in the
    *form submission query string*.
  + `type`(__*__): The type of input to expect from the user (discussed below).
  + `required`(__*__): Questions with this value set to **true** must be answered
    before form will submit.

#### Basic Input Types
As discussed above, there are a few different *input types* currently available. These
are listed below:

+ `date`
+ `datetime-local`
+ `email`
+ `file`
+ `number`
+ `selectbox`
+ `tel`
+ `text`
+ `textarea`
+ `time`
+ `url`

Information describing these types can be found in the **MDN Input Element Docs**,[^1]
except for `selectbox` and `textarea` which are custom *input types*.

#### Custom Input Types
While setting the *input type* to `textarea` simply allows you to use a
*textarea element* (as opposed to an *input* element of type `text`), setting the
*input type* to `selectbox` is a little more interesting:
```JSON
{
  "subject": "Your Form Subject",
  "title": "Your Custom Title",
  "form_backend_url": null,
  "email": "your_email@example.com",
  "questions": [
    {
      "label": "Select your country",
      "name": "country",
      "type": "selectbox",
      "required": true,
      "options": [
        {"label": "--Select--", "value": "", "selected": true, "disabled": true},
        {"label": "USA", "value": "USA"},
        {"label": "Canada", "value": "CAN"},
        {"label": "United Kingdom", "value": "UK"},
        {"label": "Australia", "value": "AUS"}
      ],
      "custom": {
        "multiple": true
      }
    }
  ]
}
```
When using the `selectbox` input type, you now have access to the `options` attribute,
where you can set the different options that will be _"selectable"_ by the user. Each
option has 4 possible *attributes* (**NOTE**: attributes with a __*__ mark are
**required**):

+ `label`(__*__): The text displayed to the user in the **selectbox**.
+ `value`(__*__): The text sent upon *form submission* in the _"query string"_.  
+ `selected`: A *boolean* value that initializes this option as *selected* by default.
+ `disabled`: A *boolean* value that prohibits the user from selecting this option.

While you can set the `options` attribute in the `config.json` file for a question
**without** setting the type to `selectbox`, nothing will happen but the website should
function normally.

### Additional Attributes
You will notice in the above section the presence of a `custom` attribute:
```JSON
{
  "custom": {
    "multiple": true
  }
}
```
The role of this *attribute* is to configure **ANY** additional attributes related to
the *form input element* you are using for your _"question."_ In this case we are
setting the **multiple** attribute to **true** for the **select** element (so that the
user can select multiple options in the **selectbox**).

## Development
Here we introduce the various tools related to *developing* the `Parley`
software.

### Make
A `Makefile` is available in the project root, and implements several commands to
make the *development process* easier. All *commands*  are executed by the following
format: `make [COMMAND]`. To see the *contents* of a command that will be executed upon
invocation of the command, simply run `make -n [COMMAND]` (**NOTE**: this serves as a
good way to test a command and see what **exactly** will be executed before running the
command). Below is the list of the commands and their short descriptions:

+ `build`: Build the Docker image
+ `serve`: Serve the website
+ `server-container`: Build server container
+ `pause`: Pause 1 second (to pause between commands)
+ `address`: Get Docker container address/port
+ `stop-server`: Stop the running web server
+ `restart-server`: Restart the running web server
+ `lint`: Run linters
+ `test`: Run full testing suite
+ `pytest`: Run pytest in Docker container
+ `isort`: Run isort in Docker container
+ `black`: Run black in Docker container
+ `flake8`: Run flake8 in Docker container
+ `mypy`: Run mypy in Docker container
+ `shell`: Create interactive shell in Docker container

#### Example Uses
Here we will show some **common use cases** for the `Makefile`:

+ **serve the website locally**: running the `make serve` will serve the website and
  print out the *host*/*address* to your terminal.

+ **test the website locally**: running the `make pytest` will run **ONLY** the *Python*
  tests (written with *pytest*) on the current website.

+ **build docker image**: running `make build` will build the
  `ghcr.io/diogenesanalytics/parley:master` *Docker image* locally.

+ **stop the web server**: running `make stop-server` will stop any currently *running*
  server deployed by `make serve`.

+ **get local server address**: running `make address` will get the *host*/*port* for
  the server deployed previously by `make serve` (if any exist).

+ **run specific tests**: running `make shell` will allow start up a **bash** instance
  inside the `ghcr.io/diogenesanalytics/parley:master` *Docker image*, from which you
  can then run a *specific subset* of tests (**e.g.** `pytest -m website`).

## References
[^1]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input#input_types
