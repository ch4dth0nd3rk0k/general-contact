// Function to convert files to data urls
function handleFileUpload(event, formData, callback) {
    // Extract file input and files from the event
    const fileInput = event.target;
    const files = fileInput.files;

    // Array to store promises for each file upload operation
    const promises = [];

    // Debug statement: Output files to console
    console.log("Files:", files);

    // Iterate over each file in the files array
    for (let i = 0; i < files.length; i++) {
        const file = files[i];

        // Debug statement: Output current file being processed to console
        console.log("Processing file:", file.name);

        // Create a promise for each file upload operation
        const promise = new Promise((resolve) => {
            // Create a FileReader object to read the file content
            const reader = new FileReader();

            // Define onload event handler for the FileReader
            reader.onload = function(event) {
                // Retrieve the file content from the FileReader result
                const fileContent = event.target.result;

                // Debug statement: Output file content to console
                console.log("File content:", fileContent);

                // Create a data URL from the file content
                const dataUrl = `data:${file.type};base64,${btoa(fileContent)}`;

                // Update the formData object with the data URL
                if (Array.isArray(formData[fileInput.name])) {
                    // If formData property is an array, push the data URL to it
                    formData[fileInput.name].push(dataUrl);
                } else {
                    // Otherwise, create a new array with the data URL
                    formData[fileInput.name] = [dataUrl];
                }

                // Debug statement: Output updated formData to console
                console.log("Updated formData:", formData);

                // Resolve the promise when file reading is complete
                resolve();
            };

            // Read the file as binary string
            reader.readAsBinaryString(file);
        });

        // Push the promise to the promises array
        promises.push(promise);
    }

    // Wait for all promises to resolve
    Promise.all(promises).then(() => {
        // Debug statement: Indicate that all file uploads are completed
        console.log("All file uploads completed!");

        // Invoke the callback with the updated formData object
        callback(formData);
    });
}

// Function to generate HTML content
function generateHtmlContent(formData) {
    // Base space
    let indent = "      ";

    // Template
    let htmlContent = `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contact Form Response</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        background-color: #222;
        color: #eee;
        padding: 20px;
      }
      .container {
        max-width: 600px;
        margin: 0 auto;
        background-color: #333;
        color: #eee;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(255, 255, 255, 0.1);
      }
      label {
        font-weight: bold;
      }
      img, video, audio {
        min-width: 100%;
        max-width: 100%;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h2>Contact Form Response</h2>\n`;

    // Add form data to the HTML content
    for (const key in formData) {
        htmlContent += indent + `<label for="${key}">${key}:</label>\n`;

        // If the value is an array (multiple files)
        if (Array.isArray(formData[key])) {
            // First add some extra space between label and value(s)
            htmlContent += indent + `  <p>\n`;

            // Handle multiple file data URLs and the correct tag for the MIME type
            formData[key].forEach(url => {
                // log file
                console.log("Embedding file into HTML: " + url)
                // Get MIME type of the file
                const mimeType = url.split(';')[0].split(':')[1];

                if (mimeType.startsWith('image')) {
                    htmlContent += indent + [
                        `    <img src="${url}" alt="${key}" />`,
                        '    <br>\n'
                    ].join('\n' + indent);
                } else if (mimeType.startsWith('video')) {
                    htmlContent += indent + [
                        '    <video controls>',
                        `      <source src="${url}" type="${mimeType}">`,
                        '      Your browser does not support the video tag.',
                        '    </video>',
                        '    <br>\n'
                    ].join('\n' + indent);
                } else if (mimeType.startsWith('audio')) {
                    htmlContent += indent + [
                        '      <audio controls>',
                        `        <source src="${url}" type="${mimeType}">`,
                        '        Your browser does not support the audio tag.',
                        '      </audio>',
                        '      <br>\n'
                    ].join('\n' + indent);
                } else {
                    htmlContent += indent + `    <a href="${url}">${key}</a>\n`;
                }
            });

            // Close <p> tag
            htmlContent += indent + `  </p>\n`;

        } else {
            // Just normal data
            htmlContent += indent + `  <p>${formData[key]}</p>\n`;
        }
    }

    // Add closing HTML tags
    htmlContent += `    </div>
  </body>
</html>`;

    return htmlContent;
}


// Function to handle errors
function handleConfigError(error) {
  // Display the error message
  const errorMessage = document.createElement('p');
  errorMessage.textContent = 'Error loading configuration: ' + error.message;
  document.body.appendChild(errorMessage);

  // Hide other elements
  const container = document.querySelector('.container');
  container.style.display = 'none';
}

// Function to update email placeholders
function updateEmailPlaceholders(email) {
    const emailPlaceholders = document.querySelectorAll('.email-placeholder');
    emailPlaceholders.forEach(placeholder => {
        placeholder.textContent = email;
    });
}

// Function to copy email to clipboard
function copyEmailToClipboard(email) {
    const tempInput = document.createElement('input');
    tempInput.value = email;
    document.body.appendChild(tempInput);
    tempInput.select();
    document.execCommand('copy');
    document.body.removeChild(tempInput);
    alert('Email copied to clipboard: ' + email);
}

// Function to dynamically deselect the default option
 function createUpdateDefaultOption(selectElement) {
     function updateDefaultOption() {
         const defaultOption = selectElement.querySelector('option[value=""][disabled][selected]');
         if (defaultOption) {
             defaultOption.selected = false;
             console.log("Default option removed.");
             // Remove the event listener after it's been triggered once
             selectElement.removeEventListener('change', updateDefaultOption);
         }
     }
     // Return the closure
     return updateDefaultOption;
 }

 // Function to print information about the select element
 function printSelectInfo(selectElement) {
     const label = selectElement.getAttribute('data-label') || 'No label';
     const selectedCount = Array.from(selectElement.selectedOptions).length;
     console.log('Select element:', label);
     console.log('Number of selected options:', selectedCount);
 }

// Fetching and populating form fields from config.json
fetch('config.json')
.then(response => {
    // Alert user if config.json unreachable
    if (!response.ok) {
        throw new Error('Network response was not ok');
    }
    return response.json();
})
.then(data => {
    // Alert user if email or form_backend_url key not found
    if (!data.email && !data.form_backend_url) {
        throw new Error('Email address or form backend URL not found in config.json');
    }

    // Alert user if title not found
    if (!data.title) {
      throw new Error('Title not found in config.json');
    }

    // Set document title
    document.title = data.title;

    // Check if subject is provided and not empty
    if (!data.subject || data.subject.trim() === '') {
        throw new Error('Subject is required in config.json');
    }

    const form = document.getElementById('contact-form');
    const email = data.email;
    const subject = encodeURIComponent(data.subject); // Encrypt subject
    if (email !== undefined && email !== null) {
      form.setAttribute('action', 'mailto:' + email + '?subject=' + subject);
    }

    const formBackendUrl = data.form_backend_url;
    if (formBackendUrl !== undefined && formBackendUrl !== null) {
      // Set form backend URL and enctype if available and not null
      form.setAttribute('action', formBackendUrl);

      // Check for ignore file upload
      const ignoreFileUpload = data.ignore_file_upload

      // Check if any question has type="file" in config.json
      const hasFileUpload = data.questions.some(question => question.type === 'file');
      if (hasFileUpload && (!ignoreFileUpload)) {
          // If any question involves file upload use multipart encoding
          form.setAttribute('enctype', 'multipart/form-data');
      } else {
          // Otherwise, set enctype for URL encoding
          form.setAttribute('enctype', 'application/x-www-form-urlencoded');
      }
    }

    // Populate instructions element if present
    if (data.instructions) {
        const instructionsElement = document.getElementById('instructions');
        if (Array.isArray(data.instructions)) {
            // If instructions is an array, join its elements with line breaks
            instructionsElement.innerHTML = data.instructions.join(' ');
        } else {
            instructionsElement.innerHTML = data.instructions;
        }

        // Update email placeholder in instructions
        updateEmailPlaceholders(email);
    }

    // Add click event listener to copy email to clipboard
    const emailPlaceholders = document.querySelectorAll('.email-placeholder');
    emailPlaceholders.forEach(placeholder => {
        placeholder.addEventListener('click', () => {
            copyEmailToClipboard(email);
        });
    });

    // Iterate over questions in config.json
    data.questions.forEach(question => {
        // Create labels for each question
        const label = document.createElement('label');
        if (Array.isArray(question.label)) {
            // Concatenate the label array with " " as separator
            label.innerHTML = question.label.join(' ') + ':';
        } else {
            label.innerHTML = question.label + ':';
        }
        label.style.color = '#ddd'; // Light text color
        form.appendChild(label);
        form.appendChild(document.createElement('br'));

        let input;
        // Create input elements for each question
        if (question.type === 'textarea') {
            input = document.createElement('textarea');
            input.setAttribute('rows', '4');
        } else if (question.type === 'selectbox') {
            input = document.createElement('select');
            // Create options for select box
            question.options.forEach(option => {
                const optionElem = document.createElement('option');
                optionElem.textContent = option.label;
                optionElem.setAttribute('value', option.value);
                if (option.selected) {
                    optionElem.setAttribute('selected', 'selected');
                }
                if (option.disabled) {
                    optionElem.setAttribute('disabled', 'disabled');
                }
                input.appendChild(optionElem);
            });

            // Attach event listener to dynamically deselect default option when any other option is selected
            const updateDefaultOption = createUpdateDefaultOption(input);
            input.addEventListener('change', updateDefaultOption);

            // Attach event listener to print the number of selected options
            input.addEventListener('change', () => {
                printSelectInfo(input);
            });
        } else {
            input = document.createElement('input');
            input.setAttribute('type', question.type);
        }

        // Set the attributes common attributes for form processing
        input.setAttribute('name', question.name);
        input.setAttribute('data-label', question.label); // Store label
        if (question.required) {
            input.setAttribute('required', '');
        }

        // Add custom attributes
        if (question.custom) {
            Object.entries(question.custom).forEach(([key, value]) => {
                input.setAttribute(key, value);
            });
        }

        // Add to form
        form.appendChild(input);
        form.appendChild(document.createElement('br'));
    });

    // Setup form submission button
    const send_button = document.createElement('button');
    send_button.setAttribute('type', 'submit');
    send_button.textContent = data.send_button_text || 'Send';
    send_button.setAttribute('id', 'send_button'); // Add id attribute
    form.appendChild(send_button);

    // Custom validation
    send_button.addEventListener('click', function(event) {
        // Prevent the default form submission behavior
        event.preventDefault();

        // Check if the form element is selected correctly
        const contactForm = document.getElementById("contact-form");
        const inputs = contactForm.querySelectorAll('input, textarea, select');
        let customValidationFailed = false;

        // Log to console
        console.log("Beginning custom form validation");

        // Begin input checking ...
        inputs.forEach(input => {
            let fieldValue = input.value;

            if (input.tagName === 'SELECT') {
                if (input.hasAttribute('multiple')) {
                    // Handle <select multiple> elements
                    const selectedOptions = Array.from(input.selectedOptions);
                    const selectedValues = selectedOptions.map(option => option.value);

                    // Check if any selected option has an empty string value
                    if (selectedValues.includes('')) {
                        fieldValue = ''; // Set fieldValue to an empty string
                    }
                } else {
                    // Handle single-selection <select> elements
                    fieldValue = input.value;
                }
            }

            if (input.hasAttribute('required') && (!fieldValue || !fieldValue.trim())) {
                // Highlight required fields in red
                input.style.borderColor = 'red';

                // Set the flag to indicate custom validation failure
                customValidationFailed = true;
            } else {
                input.style.borderColor = '#555'; // Reset border color
            }
        });

        if (customValidationFailed) {
            console.log("Validation failed.")
            alert(data.missing_field_message || 'Please fill out all required fields.');
            return; // Exit the function without submitting the form
        }

        // If custom validation passes, manually submit the form
        if (contactForm.reportValidity()) {
          console.log("Validation passed. Submitting form...");
          contactForm.submit();
        }
        else {
          console.log("Validation failed. Builtin validation triggered...");
        }
    });

    // Setup form download button
    const download_html_button = document.createElement('button');
    download_html_button.setAttribute('type', 'button');
    download_html_button.textContent = data.download_button_text || 'Download';
    download_html_button.setAttribute('id', 'download_button'); // Add id attribute

    // Check if data.enable_form_download is true
    if (data.enable_form_download) {
        // Add event to listen for click
        download_html_button.addEventListener('click', () => {

            // Get inputs to store
            const formData = {};
            const inputs = form.querySelectorAll('input, textarea, select');
            let valid = true;

            // Log to console
            console.log("Beginning download validation");

            inputs.forEach(input => {
                let fieldValue = input.value;

                if (input.tagName === 'SELECT' && input.hasAttribute('multiple')) {
                    const selectedOptions = Array.from(input.selectedOptions);

                    // Convert array to string
                    fieldValue = selectedOptions.map(option => option.value).join(', ');
                }

                if (input.hasAttribute('required') && (!fieldValue || !fieldValue.trim())) {
                    valid = false;
                    input.style.borderColor = 'red'; // Highlight required fields in red
                } else {
                    input.style.borderColor = '#555'; // Reset border color
                }

                // Store form data
                formData[input.getAttribute('name')] = fieldValue;
            });

            if (valid) {
                // Log to console
                console.log("Validation passed. Downloading form...");

                // Initialize an array to store all promises
                const promises = [];

                // Handle file uploads sequentially
                const fileInputs = form.querySelectorAll('input[type="file"]');
                fileInputs.forEach(fileInput => {
                  // Create a promise for each file upload operation
                  const promise = new Promise((resolve) => {
                      handleFileUpload({ target: fileInput }, formData, updatedFormData => {
                          console.log("Callback formData updated:", updatedFormData);
                          resolve();
                      });
                  });
                  promises.push(promise);
                });

                // Wait for all promises to resolve
                Promise.all(promises).then(() => {
                  // Generate HTML content
                  const htmlContent = generateHtmlContent(formData);

                  // Create a Blob containing the HTML content
                  const blob = new Blob([htmlContent], { type: 'text/html' });

                  // Create a download link
                  const link = document.createElement('a');
                  link.href = URL.createObjectURL(blob);
                  link.download = 'contact_form_response.html';

                  // Append the link to the body and click it programmatically
                  document.body.appendChild(link);
                  link.click();

                  // Remove the link from the body
                  document.body.removeChild(link);
                });

            } else {
                alert(data.missing_field_message || 'Please fill out all required fields.');
            }
        });

        // If true display the download button
        form.appendChild(download_html_button);
    }
    else {
        // If not hide the download button
        download_html_button.style.display = 'none';
    }

    // Show the instructions/form when JavaScript is enabled
    document.querySelector(".container").style.display = "block";
})
.catch(error => {
    handleConfigError(error);
});
