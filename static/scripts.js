
let returnedId = null;
let token = null;

function displayAuthMessage(message, isSuccess) {
    const authMessageDiv = document.getElementById('authMessage');
    authMessageDiv.textContent = message;
    authMessageDiv.style.color = isSuccess ? 'green' : 'red';
}

function setAuthEnabled(enabled) {
    document.getElementById('username').disabled = !enabled;
    document.getElementById('password').disabled = !enabled;
    document.getElementById('login').disabled = !enabled;
    document.getElementById('logout').disabled = !enabled;
}

function login() {
    setAuthEnabled(false);
    displayAuthMessage('Authenticating, please wait...', true);

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
        token = null
        displayAuthMessage('Error: please check and retry', false);
    })
    .finally(() => {
        setAuthEnabled(true);
    });
}

function logout() {
    token = null;
    displayAuthMessage("You have logged out", true);
}

function sendPostRequest() {
    displayResponse("", false, null);

    if (!token) {
        displayAuthMessage('Please log in', false);
        return;
    }

    const text = document.getElementById('textInput').value;
    if (!text) {
        displayResponse("Please enter a query", false, null);
        return
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
        returnedId = data.id;
        displayResponse("Query acknowledged, please wait...", false, null);
        pollStatus();
    })
    .catch((error) => {
        displayResponse("Error: please retry.", false, null);
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

function displayResponse(text, bFromLLM, article_refs) {
    const resultDiv = document.getElementById('response');
    resultDiv.textContent = text;
    const responseTitle = document.getElementById('responseTitle');
    responseTitle.style.display = bFromLLM ? 'block' : 'none';
    displayReferenceLinks(article_refs);
}

function displayReferenceLinks(article_refs) {
    const refDiv = document.getElementById('references');
    refDiv.innerHTML = '';
    const referencesTitle = document.getElementById('referencesTitle');
    referencesTitle.style.display = 'none';

    if (!article_refs) {
        return;
    }

    referencesTitle.style.display = 'block';
    article_refs.forEach(item => {
        const link = document.createElement('a');
        link.href = item.url;
        link.textContent = item.title;
        link.target = '_blank';
        refDiv.appendChild(link);
    });
}

function pollStatus() {
    pollingInterval = setInterval(() => {
        fetch(`/v1/api/query/${returnedId}`, {
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
                displayResponse(data.response.answer, true, data.response.article_refs);
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            clearInterval(pollingInterval);
            showSpinner(false);
            displayResponse("Error: please retry.", null);
            setInputEnabled(true);
        });
    }, 1500);
}
