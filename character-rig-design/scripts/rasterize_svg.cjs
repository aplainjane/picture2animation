// Rasterize project-local SVG paths with Chromium, retaining real alpha.
// node rasterize_svg.cjs manifest.json playwright-module-dir chrome-executable
const fs=require('fs');
const path=require('path');
const {chromium}=require(process.argv[3]||'playwright');
(async()=>{
 const jobs=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
 const browser=await chromium.launch({headless:true,...(process.argv[4]?{executablePath:process.argv[4]}:{})});
 try{const page=await browser.newPage();await page.route('http**://**',route=>route.abort());
 for(const job of jobs){
  const svg=fs.readFileSync(job.svg,'utf8');
  if(/<image\b|<script\b|<foreignObject\b|(?:href|url)\s*\(?\s*["']?https?:/i.test(svg))throw Error('Expected self-contained vector paths');
  const encoded=await page.evaluate(async({svg,w,h})=>{
   const im=new Image();im.src='data:image/svg+xml;base64,'+btoa(unescape(encodeURIComponent(svg)));await im.decode();
   const large=document.createElement('canvas');large.width=w*2;large.height=h*2;large.getContext('2d').drawImage(im,0,0,w*2,h*2);
   const c=document.createElement('canvas');c.width=w;c.height=h;c.getContext('2d').drawImage(large,0,0,w,h);return c.toDataURL('image/png').split(',')[1];
  },{svg,w:job.width,h:job.height});
  fs.mkdirSync(path.dirname(job.png),{recursive:true});fs.writeFileSync(job.png,Buffer.from(encoded,'base64'));
 }
 console.log(JSON.stringify({rendered:jobs.length}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
