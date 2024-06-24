
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

function sendPostRequest() {
    const text = document.getElementById('textInput').value;
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
    })
    .catch((error) => {
        console.error('Error:', error);
    });
}

