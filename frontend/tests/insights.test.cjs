const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync('frontend/session.html','utf8');
const ctx={sentimentLabel:()=>({label:'Neutral'})};vm.createContext(ctx);
vm.runInContext(html.slice(html.indexOf('function generateInsights('),html.indexOf('document.getElementById("btn-delete-session").addEventListener')),ctx);
const tips=ctx.generateInsights({overall_sentiment:null,engagement_score:null},{emotion_samples:0,transcript_chunks:0});
assert.equal(tips.some(tip=>/Low engagement|Neutral sentiment/.test(tip.text)),false,'missing model scores do not become conclusions');
console.log('Missing scores do not generate fabricated insight tips passed');
