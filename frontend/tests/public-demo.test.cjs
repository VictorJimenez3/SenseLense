const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
function openPage(saved) {
    const values = new Map(saved ? [['sl-user', JSON.stringify(saved)]] : []);
    let redirected;
    const ctx = {
        localStorage: {getItem: k => values.get(k), setItem: (k,v) => values.set(k,v), removeItem: k => values.delete(k)},
        document: {readyState:'loading', createElement: () => ({}), head:{appendChild() {}}, addEventListener() {}},
        window: {location:{replace: url => {redirected=url;}}},
    };
    vm.createContext(ctx);
    vm.runInContext(fs.readFileSync('frontend/js/auth.js','utf8'),ctx);
    return {ctx,values,redirected};
}
const visitor = openPage();
assert.equal(visitor.redirected, undefined, 'a fresh visitor enters without an account');
assert.equal(visitor.ctx.window.SLAuth?.user.name, 'Demo Visitor');
assert.equal(openPage({name:'Victor'}).ctx.window.SLAuth.user.name, 'Victor');
visitor.ctx.window.SLAuth.logout();
assert.equal(visitor.values.has('sl-user'),false);
console.log('Public visitor, existing profile, and logout passed');
