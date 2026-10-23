const fs=require('fs'),path=require('path');
const root='web';
const files=[];
function walk(d){for(const e of fs.readdirSync(d,{withFileTypes:true})){const p=path.join(d,e.name);if(e.isDirectory()){if(e.name==='node_modules'||e.name==='.next')continue;walk(p);}else if(/\.tsx$/.test(e.name))files.push(p);}}
walk('web/components');walk('web/app');
const css=fs.readFileSync('web/app/globals.css','utf8');
const defined=new Set([...css.matchAll(/\.([a-zA-Z][\w-]*)/g)].map(m=>m[1]));
for(const f of files){
  const src=fs.readFileSync(f,'utf8');
  const re=/className\s*=\s*(?:"([^"]*)"|\{`([^`]*)`\}|\{"([^"]*)"\})/g;
  let m; const set=new Set();
  while((m=re.exec(src))){const v=m[1]||m[2]||m[3]||'';for(const t of v.split(/[\s`${}?:'"()]+/)) if(/^[a-zA-Z][\w-]*$/.test(t)&&!defined.has(t)) set.add(t);}
  if(set.size) console.log(f.replace(/\\/g,'/')+': '+[...set].join(' '));
}
