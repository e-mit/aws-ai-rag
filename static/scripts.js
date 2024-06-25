
let returnedId = null;
let token = null;
let rootPath = '/';

function extractVN() {
    const pathname = window.location.pathname;
    const regex = /^\/v(\d+)(\/|$)/;
    const match = pathname.match(regex);
    if (match) {
        return ('/v' + match[1]);
    }
    return '/';
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
                if (data.id != returnedId) {
                    throw new Error('ID mismatch');
                }
                setInputEnabled(true);
                displayResponse(data.response.answer, true, data.response.article_refs);
            }
        })
        .catch((error) => {
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
        apiKey: "B4025inDbNz9TWAjMtzvvlRNhEXWKAaBXsr92hKugYKJ/Efd/hqdEFbgaWsNOAgQR+kBDj5N6yQYANjvWHsLr5Y/y75o4ZyfNhex/25NkXjDV55jmRCq/OV/XCAdZnbdrjN/yE7R6D65Abbkha3kCsCWpvRf4yVXjWWeF883XB3gZHho3h/9fhW2/MTM6E4z1y3cHsYSVWSzP8syM6byh9wctMXNTcjApUV6Qx0xqMi0o3g52lBaEs0384ENsCbHD4vie0ONwBlqcjgzwY3GVOdh/lpDVudOdlIEGC4GOan5BbgkjKYGuL7elMQvzqz17pbvFjfos/FFiFi65pbGO7+xZ5LK5OQqIgu5HGDIWyUON3SN11rc5YQsubeTmnswgIwX8BT+U5gn2xUCu+72K9IcXojvmabrBPOH1Muj73DaKoit85rXHoIFyaAYQCzVS4FAHq4GiYhwg129+4Rp5kfB1eOctoH6sO17MWQrZ8sxLsS/66KhzgPByHQ4qf5X9vbaqVWD5x97l9P+WxPkJOE2ZtNZcc42a4aLnVKsIkhQ4ZC/4gEUa0988CZ8WRh+LnBRfPmxiZgU+PgxqnG0ge7GP5IMdViyBUF8tUYaDZD3ADtP7oH/mIuRvCRtBC78f228py8DGaYEceN7A+Up5XmU4e7rERIIoo4uLy+JiS8=_0_1",
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
