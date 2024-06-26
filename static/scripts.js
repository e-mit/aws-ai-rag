
let returnedId = null;
let token = null;
let rootPath = '';

function extractVN() {
    const pathname = window.location.pathname;
    const regex = /^\/v(\d+)(\/|$)/;
    const match = pathname.match(regex);
    if (match) {
        return ('/v' + match[1]);
    }
    return '';
}

window.addEventListener('load', function() {
    rootPath = extractVN();
});

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

    fetch(`${rootPath}/api/token`, {
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
        showAnswerBox(true);
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

function sendQueryRequest() {
    displayResponse("", false, null);

    if (!token) {
        showAnswerBox(false);
        return;
    }

    const text = document.getElementById('textInput').value;
    if (!text) {
        displayResponse("Please enter a query", false, null);
        return
    }

    showSpinner(true);
    setInputEnabled(false);

    fetch(`${rootPath}/api/query`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({query: text})
    })
    .then(response => {
        if (response.status !== 201) {
            showAnswerBox(false);
            return Promise.reject();
        }
        return response.json();
    })
    .then(data => {
        returnedId = data.id;
        displayResponse("Query acknowledged, please wait...", false, null);
        pollStatus();
    })
    .catch((error) => {
        showSpinner(false);
        displayResponse("Error: please retry.", false, null);
        setInputEnabled(true);
    });
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
        fetch(`${rootPath}/api/query/${returnedId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (response.status !== 200) {
                return Promise.reject(new Error(`Request failed with status ${response.status}`));
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'completed') {
                clearInterval(pollingInterval);
                showSpinner(false);
                if (data.id != returnedId) {
                    throw new Error('ID mismatch');
                }
                setInputEnabled(true);
                displayResponse(data.response.answer, true, data.response.article_refs);
            }
        })
        .catch((error) => {
            showSpinner(false);
            clearInterval(pollingInterval);
            displayResponse("Error: please retry.", false, null);
            setInputEnabled(true);
        });
    }, 1500);
}

function setError(error) {
    displayAuthMessage(error.message, false);
}

function generateCaptcha() {
    const container = document.getElementById('captcha-container');
    AwsWafCaptcha.renderCaptcha(container, {
        apiKey: "fRfA4keyACz134NdUif+A4XtEoGI9pkX89WrRZDep5M0Qremi34I/8Kiqe05bslbT+gsA5XXIiY+nm5F5Zu2VtSB5+GRepo58cCdq6PMvYtPtY+9QnPfVFBFkhMz2FVFgHZLFWQMwPbUsBHL+M/FwGk/RT4WQtq6hWa/q/4TJZ5m9Blf/IT9TpWTBtGYMeYb3AgYEQ2LOCtTZVdTuriOM4QPpb5UWOJ6h9GcwM9onDbvqV7xW/pRTK3i0FW8DoATf4nYt/mzoNoezx43ZcAUS4eIr5Z6mOE+jPweAhol94kb4a4C9JWd2FR8cAKYiThX8G0Uw5lOdl6fPakdWw7Ayo8KdjpTs7BtBPfP2e6hIE122qmZIToAB31PRvv1/5uDKE3CuvSf4fcHvu/AHBlPN+IQ/aeOKENSG3jvZ7bk+6jKxLTh1ZRZ4G1wqzs5FM2MyTFAp0uKfo4K97SxO68PSPjjn6oPBZSez5WcNY8Zpld16xa8/PLmDZv495o4wtu+hsPtJ0Y0/890n6U0K/C7ueS5D/EiDdTySkcEIsoCX+F/7KUTOEgCElbYC8390l/0dsZFhFFFfcZXrCe4y3o9NEmY0ZSXA5F4aVRo0holQOxbU7EtexqGK/DNoyjyx5BjjrZd9KmPxTF1mZ1lKMEXcEbfFiUSbVEe9P16CgCKbsI=_0_1",
        onSuccess: () => {
            captchaLogin();
        },
        onError: setError,
        skipTitle: true
    });
}

window.addEventListener('load', function() {
    generateCaptcha();
});

function toggleLoginMethod(event) {
    event.preventDefault();
    const loginBox = document.getElementById('loginBox');
    const captchaBox = document.getElementById('captchaBox');
    const showCaptcha = captchaBox.style.display === 'none';
    loginBox.style.display = showCaptcha ? 'none' : 'grid';
    captchaBox.style.display = showCaptcha ? 'grid' : 'none';
}

function captchaLogin() {
    displayAuthMessage('Authenticating, please wait...', true);
    fetch(`${rootPath}/api/captcha_token`, {
        method: 'GET'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Authentication failed');
        }
        return response.json();
    })
    .then(data => {
        token = data.access_token;
        showAnswerBox(true);
    })
    .catch((error) => {
        token = null
        displayAuthMessage('Error: please check and retry', false);
    })
    .finally(() => {
        generateCaptcha();
    });
}

function showAnswerBox(bShowAnswer) {
    showSpinner(false);
    displayResponse("", false, null);
    if (bShowAnswer) {
        displayAuthMessage('Success', true);
    } else {
        displayAuthMessage('Please authenticate', false);
    }
    const answerBox = document.getElementById('answerBox');
    const authenticationBox = document.getElementById('authenticationBox');
    answerBox.style.display = bShowAnswer ? 'block' : 'none';
    authenticationBox.style.display = bShowAnswer ? 'none' : 'block';
}

function showSpinner(show) {
    const spinner = document.getElementById('spinner');
    spinner.style.display = show ? 'block' : 'none';
}
