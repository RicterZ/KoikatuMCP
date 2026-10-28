import json, urllib.request
class Client:
 def __init__(self,url='http://127.0.0.1:8766/'):
  self.url=url;self.session=None;self.id=0
  self.rpc('initialize',{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'stud58-validation','version':'1'}})
  self.rpc('notifications/initialized',notification=True)
 def rpc(self,method,params=None,notification=False):
  self.id+=1
  body={'jsonrpc':'2.0','method':method}
  if not notification:body['id']=self.id
  if params is not None:body['params']=params
  h={'Content-Type':'application/json','Accept':'application/json, text/event-stream'}
  if self.session:h['Mcp-Session-Id']=self.session
  req=urllib.request.Request(self.url,data=json.dumps(body).encode(),headers=h)
  with urllib.request.urlopen(req,timeout=45) as r:
   self.session=r.headers.get('Mcp-Session-Id',self.session);raw=r.read().decode()
  if not raw.strip():return None
  if raw.lstrip().startswith(('event:','data:')):raw='\n'.join(x[5:].strip() for x in raw.splitlines() if x.startswith('data:'))
  result=json.loads(raw)
  if 'error' in result:raise RuntimeError(result['error'])
  return result['result']
 def call(self,name,**args):
  result=self.rpc('tools/call',{'name':name,'arguments':args})
  text='\n'.join(c.get('text','') for c in result.get('content',[]))
  try:return json.loads(text)
  except ValueError:return {'raw':text}
