from playwright.async_api import async_playwright
class HorillaReader:
 def __init__(self): self.pw=None; self.browser=None; self.context=None; self.page=None
 async def open(self,url):
  if not url.startswith(('http://localhost','http://127.0.0.1','https://')): raise ValueError('Use a local Horilla URL or trusted HTTPS URL.')
  if not self.pw: self.pw=await async_playwright().start()
  if not self.browser: self.browser=await self.pw.chromium.launch(headless=False)
  if not self.context: self.context=await self.browser.new_context()
  self.page=await self.context.new_page(); await self.page.goto(url,wait_until='domcontentloaded',timeout=60000)
  return {'url':self.page.url,'title':await self.page.title(),'message':'Browser opened. Log in manually, navigate to employee/pay/leave tables, then capture.'}
 async def capture(self):
  if not self.page: raise RuntimeError('Open Horilla browser first.')
  tables=await self.page.locator('table').evaluate_all("els => els.map(t => ({headers:Array.from(t.querySelectorAll('thead th')).map(x=>x.innerText.trim()), rows:Array.from(t.querySelectorAll('tbody tr')).map(tr=>Array.from(tr.querySelectorAll('th,td')).map(td=>td.innerText.trim()))}))")
  return {'url':self.page.url,'title':await self.page.title(),'tables':tables,'text':(await self.page.locator('body').inner_text())[:12000]}
 async def close(self):
  if self.browser: await self.browser.close()
  if self.pw: await self.pw.stop()
  self.pw=self.browser=self.context=self.page=None
reader=HorillaReader()
