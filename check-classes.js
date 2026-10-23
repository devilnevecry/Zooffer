const fs=require('fs'),path=require('path');
const root='web';
function walk(d){let r=[];for(const e of fs.readdirSync(d,{withFileTypes:true})){const p=path.join(d,e.name);if(e.isDirectory()){if(e.name==='node_modules'||e.name==='.next')continue;r=r.concat(walk(p));}else if(/\.(tsx|ts)$/.test(e.name))r.push(p);}return r;}
const used=new Set();
for(const f of walk(root)){
  const src=fs.readFileSync(f,'utf8');
  const re=/className\s*=\s*(?:"([^"]*)"|\{`([^`]*)`\}|\{"([^"]*)"\})/g;
  let m; while((m=re.exec(src))){const v=m[1]||m[2]||m[3]||''; for(const t of v.split(/[\s`${}?:'"()]+/)) if(/^[a-zA-Z][\w-]*$/.test(t)) used.add(t);}
}
const css=fs.readFileSync('web/app/globals.css','utf8');
const defined=new Set();
for(const m of css.matchAll(/\.([a-zA-Z][\w-]*)/g)) defined.add(m[1]);
const missing=[...used].filter(c=>!defined.has(c)).sort();
console.log(missing.join('\n'));
console.log('--- total used',used.size,'defined',defined.size,'missing',missing.length);
