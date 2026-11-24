"""Telegram HTML widgets (Bot API 10.4).

Two widgets are used:
* a subscription card with a live "refresh" button;
* a crypto payment card with a built-in TON wallet payment button.

Widget HTML is sandboxed and has no network access; all state changes and
wallet transactions are brokered by the bot through ``widget_query`` updates.
"""

from __future__ import annotations

_SUBSCRIPTION_HTML = """
<html><head><meta charset="utf-8"><style>
body{font-family:system-ui,sans-serif}
.row{display:flex;justify-content:space-between;gap:8px;padding:6px 0}
.hint{color:var(--tg-theme-hint-color);font-size:0.85em}
.chip{display:inline-block;background:var(--tg-theme-secondary-bg-color);
 border-radius:10px;padding:4px 8px;margin:3px 4px 0 0;font-size:0.85em}
button{margin-top:10px}
</style></head><body>
<b>⭐ Zooffer · подписка</b>
<div class="row"><span>Тариф</span><b id="plan">—</b></div>
<div class="row"><span>Действует</span><span id="until">—</span></div>
<div class="row"><span>Свайпы</span><span id="quota">—</span></div>
<div id="features"></div>
<div class="hint" id="status"></div>
<button data-act="refresh">🔄 Обновить</button>
<a href="__BOT_URL__?start=buy">🚀 Выбрать тариф</a>
<script>
var W=window.TelegramWidget;
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]});}
function render(){
  var d={};try{d=JSON.parse(W.chatData||'{}')}catch(e){}
  document.getElementById('plan').textContent=d.plan||'Бесплатный';
  document.getElementById('until').textContent=d.until||'—';
  document.getElementById('quota').textContent=d.quota||'—';
  document.getElementById('features').innerHTML=(d.features||[]).map(
    function(x){return '<span class="chip">'+esc(x)+'</span>'}).join('');
  document.getElementById('status').textContent=d.status||'';
  document.querySelectorAll('[data-act]').forEach(function(b){
    b.onclick=function(){W.HapticFeedback.selectionChanged();W.request(b.dataset.act)};
  });
}
W.onEvent('chatDataChanged',render);render();W.ready();
</script></body></html>
"""

_CRYPTO_HTML = """
<html><head><meta charset="utf-8"><style>
body{font-family:system-ui,sans-serif}
.hint{color:var(--tg-theme-hint-color);font-size:0.85em}
code{user-select:text;-webkit-user-select:text;word-break:break-all}
button{margin-top:12px}
</style></head><body>
<b>💎 Оплата криптой · Zooffer</b>
<div id="summary"></div>
<div class="hint">Кошелёк: <code id="wallet"></code></div>
<div class="hint">Код платежа: <code id="order"></code></div>
<button id="pay" disabled>Оплата кошельком…</button>
<div class="hint" id="status">Нажмите кнопку, чтобы оплатить через
встроенный кошелёк Telegram.</div>
<script>
var W=window.TelegramWidget;
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]});}
var st={};try{st=JSON.parse(W.chatData||'{}')}catch(e){}
document.getElementById('summary').textContent=st.summary||'';
document.getElementById('wallet').textContent=st.wallet||'';
document.getElementById('order').textContent=st.order||'';
var pay=document.getElementById('pay'), status=document.getElementById('status');
if(W.wallet&&st.order){
  pay.disabled=false;pay.textContent='💳 Оплатить '+(st.amount||'')+' TON';
  pay.onclick=function(){
    pay.disabled=true;status.textContent='Отправляем транзакцию…';
    W.request('pay:'+st.order,{wallet:true}).then(function(a){
      return W.wallet.sendTransaction(JSON.parse(a.result),'paid:'+st.order);
    }).then(function(a){
      status.textContent='Транзакция отправлена. Код: '+(a.result||'')+
        '. Напишите в поддержку с кодом платежа для активации.';
    },function(e){status.textContent='Ошибка: '+e.code;pay.disabled=false;});
  };
}else{status.textContent='Встроенный кошелёк недоступен — '
  +'используйте обычный перевод на адрес выше.';}
W.ready();
</script></body></html>
"""


def subscription_widget_html(bot_url: str) -> str:
    return _SUBSCRIPTION_HTML.replace("__BOT_URL__", bot_url)


def crypto_widget_html() -> str:
    return _CRYPTO_HTML
