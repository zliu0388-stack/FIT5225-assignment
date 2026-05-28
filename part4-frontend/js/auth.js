const _pool = new AmazonCognitoIdentity.CognitoUserPool({
    UserPoolId: CONFIG.cognitoUserPoolId,
    ClientId:   CONFIG.cognitoClientId
});

function getSession() {
    return new Promise((resolve, reject) => {
        const user = _pool.getCurrentUser();
        if (!user) return reject(new Error('No authenticated user'));
        user.getSession((err, session) => {
            if (err || !session.isValid()) return reject(err || new Error('Session expired'));
            resolve(session);
        });
    });
}

async function getIdToken() {
    const session = await getSession();
    return session.getIdToken().getJwtToken();
}

async function isAuthenticated() {
    try { await getSession(); return true; } catch { return false; }
}

async function requireAuth() {
    if (!await isAuthenticated()) {
        window.location.href = 'login.html';
        return false;
    }
    return true;
}

function signUp(email, password, firstName, lastName) {
    return new Promise((resolve, reject) => {
        const attrs = [
            new AmazonCognitoIdentity.CognitoUserAttribute({ Name: 'email',       Value: email }),
            new AmazonCognitoIdentity.CognitoUserAttribute({ Name: 'given_name',  Value: firstName }),
            new AmazonCognitoIdentity.CognitoUserAttribute({ Name: 'family_name', Value: lastName })
        ];
        _pool.signUp(email, password, attrs, null, (err, result) => {
            if (err) return reject(err);
            resolve(result);
        });
    });
}

function confirmSignUp(email, code) {
    return new Promise((resolve, reject) => {
        new AmazonCognitoIdentity.CognitoUser({ Username: email, Pool: _pool })
            .confirmRegistration(code, true, (err, result) => {
                if (err) return reject(err);
                resolve(result);
            });
    });
}

function resendCode(email) {
    return new Promise((resolve, reject) => {
        new AmazonCognitoIdentity.CognitoUser({ Username: email, Pool: _pool })
            .resendConfirmationCode((err, result) => {
                if (err) return reject(err);
                resolve(result);
            });
    });
}

function signIn(email, password) {
    return new Promise((resolve, reject) => {
        const user = new AmazonCognitoIdentity.CognitoUser({ Username: email, Pool: _pool });
        user.authenticateUser(
            new AmazonCognitoIdentity.AuthenticationDetails({ Username: email, Password: password }),
            { onSuccess: resolve, onFailure: reject }
        );
    });
}

function signOut() {
    const user = _pool.getCurrentUser();
    if (user) user.signOut();
    window.location.href = 'login.html';
}

async function getCurrentUserInfo() {
    const session = await getSession();
    const p = session.getIdToken().payload;
    return {
        sub:       p.sub        || '',
        email:     p.email      || '',
        firstName: p.given_name  || '',
        lastName:  p.family_name || ''
    };
}
