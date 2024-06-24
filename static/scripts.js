
let returnedId = null;
let token = null;

function displayAuthMessage(message, isSuccess) {
    const authMessageDiv = document.getElementById('authMessage');
    authMessageDiv.textContent = message;
    authMessageDiv.style.color = isSuccess ? 'green' : 'red';
}

function authenticate() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    fetch('/v1/api/token', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData.toString()
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Authentication failed');
        }
        return response.json();
    })
    .then(data => {
        token = data.access_token;
        displayAuthMessage('Success', true);
    })
    .catch((error) => {
        console.error('Error:', error);
        displayAuthMessage('FAILURE', false);
    });
}

function logout() {
    token = null;
    displayAuthMessage("You have logged out", true);
}

function sendPostRequest() {
    const text = document.getElementById('textInput').value;

    if (!token) {
        displayAuthMessage('Please log in first.', false);
        return;
    }

    setInputEnabled(false);
    showSpinner(true);

    fetch('/v1/api/query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({query: text})
    })
    .then(response => response.json())
    .then(data => {
        console.log('Success:', data);
        returnedId = data.id;
        pollStatus();
    })
    .catch((error) => {
        console.error('Error:', error);
        setInputEnabled(true);
        showSpinner(false);
    });
}

function showSpinner(show) {
    const spinner = document.getElementById('spinner');
    spinner.style.display = show ? 'block' : 'none';
}

function setInputEnabled(enabled) {
    document.getElementById('textInput').disabled = !enabled;
    document.getElementById('sendButton').disabled = !enabled;
}

function displayResult(data) {
    //data.response = {answer, article_refs[]}
    const resultDiv = document.getElementById('result');
    resultDiv.textContent = data.response.answer;
}

function pollStatus() {
    const url = `/v1/api/query/${returnedId}`;

    pollingInterval = setInterval(() => {
        fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'completed') {
                clearInterval(pollingInterval);
                if (data.id != returnedId) {
                    throw new Error('ID mismatch');
                }
                showSpinner(false);
                setInputEnabled(true);
                displayResult(data);
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            clearInterval(pollingInterval);
            showSpinner(false);
            setInputEnabled(true);
        });
    }, 1000);
}
