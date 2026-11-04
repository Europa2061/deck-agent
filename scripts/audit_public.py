"""只读扫描当前待公开文件和所有引用可达历史；仅输出路径、行号和命中类型，不输出原文。"""
import pathlib,re,subprocess,json
root=pathlib.Path(__file__).resolve().parents[1]
import os
os.chdir(root)
patterns={
'private-key':rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
'github-token':rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})',
'provider-key':rb'\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{24,}',
'aws-key':rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
'credential-url':rb'https?://[^\s/:]+:[^\s/@]+@',
'personal-path':rb'/Users/[A-Za-z0-9_-]+/',
'private-ip':rb'\b(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})\b',
}
result={'current':[],'history':[]}
files=subprocess.check_output(['git','ls-files','-co','--exclude-standard','-z']).decode().split('\0')
for name in sorted(set(filter(None,files))):
 p=root/name
 if not p.is_file():continue
 data=p.read_bytes()
 if b'\0' in data[:4096]:continue
 for kind,pat in patterns.items():
  lines=sorted({data[:m.start()].count(b'\n')+1 for m in re.finditer(pat,data)})
  if lines:result['current'].append({'path':name,'kind':kind,'lines':lines})
objects=subprocess.check_output(['git','rev-list','--objects','--all']).decode().splitlines()
blobs=0
for obj in objects:
 oid,_,name=obj.partition(' ')
 if subprocess.check_output(['git','cat-file','-t',oid]).strip()!=b'blob':continue
 blobs+=1
 data=subprocess.check_output(['git','cat-file','blob',oid])
 if b'\0' in data[:4096]:continue
 for kind,pat in patterns.items():
  lines=sorted({data[:m.start()].count(b'\n')+1 for m in re.finditer(pat,data)})
  if lines:result['history'].append({'object':oid[:12],'path':name,'kind':kind,'lines':lines})
result['blobCount']=blobs
print(json.dumps(result,indent=2))
