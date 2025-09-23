// capture_cursor.js
const fs = require('fs');
const puppeteer = require('puppeteer');

(async ()=>{
  const url = process.argv[2];
  if(!url){ console.error('Usage: node capture_cursor.js <url>'); process.exit(1); }
  const b = await puppeteer.launch({headless: true, args:['--no-sandbox']});
  const p = await b.newPage();
  const logs = [];
  p.on('console', m => logs.push({type:m.type(),text:m.text()}));
  const requests = [];
  p.on('requestfinished', async req => {
    try{
      const r = req.response();
      const url = req.url();
      const status = r.status();
      const ct = (r.headers()['content-type']||'').toLowerCase();
      let text = '';
      try { if (ct.includes('json') || ct.includes('html')) text = await r.text(); } catch(e){}
      requests.push({url,status,ct,body: text.slice(0,20000)});
    }catch(e){}
  });
  await p.goto(url, {waitUntil:'networkidle2'});
  // click Validation tab
  await p.evaluate(()=> {
    const el = document.querySelector('[onclick*="switchTab(\'validation\')"], [data-tab="validation"]');
    if(el){ el.click(); }
  });
  await new Promise(r=>setTimeout(r,800));
  try { await p.screenshot({path:'page_validation.png', fullPage:true}); } catch {}
  const domVal = await p.evaluate(()=>{
    function info(el){
      if(!el) return null;
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      return {
        tag: el.tagName.toLowerCase(), id: el.id || null, cls: el.className || null,
        display: cs.display, position: cs.position, width: cs.width, height: cs.height,
        offsetWidth: el.offsetWidth, offsetHeight: el.offsetHeight, rect: {x:r.x,y:r.y,width:r.width,height:r.height}
      };
    }
    const g = document.getElementById('validation-gallery') || document.querySelector('.validation-gallery');
    const chain = [];
    let cur = g;
    for(let i=0; i<8 && cur; i++){ chain.push(info(cur)); cur = cur.parentElement; }
    return { galleryInfo: info(g), galleryChain: chain, galleryCount: g ? g.querySelectorAll('img').length : 0 };
  });
  // click GPS tab
  await p.evaluate(()=>{
    const el = document.querySelector('[onclick*="switchTab(\'map\')"], [data-tab="gps"]');
    if(el){ el.click(); }
  });
  await new Promise(r=>setTimeout(r,800));
  try { await p.screenshot({path:'page_map.png', fullPage:true}); } catch {}
  const domMap = await p.evaluate(()=>{
    function info(el){
      if(!el) return null;
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      return { tag: el.tagName.toLowerCase(), id: el.id||null, cls: el.className||null, display: cs.display, width: cs.width, height: cs.height, rect:{x:r.x,y:r.y,width:r.width,height:r.height} };
    }
    const m = document.getElementById('map') || document.getElementById('gps-map') || document.querySelector('.map');
    const chain = [];
    let cur = m;
    for(let i=0; i<8 && cur; i++){ chain.push(info(cur)); cur = cur.parentElement; }
    return { mapInfo: info(m), mapChain: chain };
  });
  const dom = { validation: domVal, map: domMap };
  fs.writeFileSync('capture_dom.json', JSON.stringify(dom, null, 2));
  fs.writeFileSync('capture_meta.json', JSON.stringify({logs, requests}, null, 2));
  console.log('Saved: page_validation.png, page_map.png, capture_dom.json, capture_meta.json');
  await b.close();
})();
