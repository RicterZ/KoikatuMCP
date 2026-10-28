param([Parameter(Mandatory=$true)][string]$GameDir, [Parameter(Mandatory=$true)][string]$PluginDll)
$ErrorActionPreference = 'Stop'
$lib = Join-Path $GameDir 'BepInEx\plugins\Console'
foreach ($dll in @('Microsoft.Scripting.Core','Microsoft.Scripting','Microsoft.Dynamic','IronPython','IronPython.Modules')) {
 [Reflection.Assembly]::LoadFrom("$lib\$dll.dll") | Out-Null
}
$engine = [IronPython.Hosting.Python]::CreateEngine()
$engine.Runtime.LoadAssembly([Reflection.Assembly]::LoadFrom("$lib\StdLib.dll"))
$paths = $engine.GetSearchPaths()
$paths.Add("$lib\Lib")
$engine.SetSearchPaths($paths)
$assembly = [Reflection.Assembly]::LoadFrom($PluginDll)
$stream = $assembly.GetManifestResourceStream('KKStudioSocket.character_animation_mcp_bridge.py')
$reader = New-Object IO.StreamReader($stream)
$code = $reader.ReadToEnd()
$reader.Dispose()
$scope = $engine.CreateScope()
$scope.SetVariable('game_data_path', (Join-Path $GameDir 'CharaStudio_Data'))
$stub = @'
import sys, types, json
from System import Int32, Object
from System.Collections.Generic import Dictionary
class Box: pass
def box(**kw):
    x = Box()
    for k, v in kw.items(): setattr(x, k, v)
    return x
def dic(kw):
    d = Dictionary[Int32, Object]()
    for k,v in kw.items(): d[k] = v
    return d
class OCIChar:
    def __init__(self):
        self.oiCharInfo = box(animeInfo=box(group=Int32(0),category=Int32(1),no=Int32(2)))
        self.charAnimeCtrl = box(normalizedTime=.25)
    def LoadAnime(self,g,c,n,t):
        self.oiCharInfo.animeInfo = box(group=Int32(g),category=Int32(c),no=Int32(n))
        self.charAnimeCtrl.normalizedTime = t
class Actor:
    def __init__(self, obj):
        self.objctrl = obj
        self.mode = 3
        self.speed = .5
        self.fk = (True,)*7
        self.ik = (True,)*5
        self.text_name = u'character'
    def get_anime_speed(self): return self.speed
    def set_anime_speed(self,speed): self.speed=speed
    def get_kinematic(self): return self.mode
    def set_kinematic(self,mode,force=0): self.mode=mode
    def get_FK_active(self): return self.fk
    def get_IK_active(self): return self.ik
    def set_FK_active(self,flags,force=0): self.fk=flags
    def set_IK_active(self,flags,force=0): self.ik=flags
class Controller:
    def __init__(self,obj):
        self.ociChar=obj
        self.Enable=True
        self.CharName='motion'
    def setEnable(self,value): self.Enable=value
u = types.ModuleType('UnityEngine')
u.Application=box(unityVersion='smoke',dataPath=game_data_path)
u.Time=box(realtimeSinceStartup=0)
sys.modules['UnityEngine']=u
obj = OCIChar()
obj.loadedAnimeInfo=box(baseFile=box(bundlePath='bundle',fileName='file'),BaseCheck=lambda *args: False)
def reset(state,layer,time): obj.charAnimeCtrl.normalizedTime=time
obj.charAnimeCtrl.nameHadh=123
obj.charAnimeCtrl.animator=box(Play=reset,Update=lambda dt: None,GetCurrentAnimatorStateInfo=lambda layer:box(IsName=lambda clip:True))
jobs=[]
received=[]
animation_send_response=received.append
actor = Actor(obj)
controller = Controller(obj)
mmdd = box(isPlaying=False, motionControllers={0:controller})
game = box(gdata=box(mmdd=mmdd), append_update_job=lambda f,p:jobs.append((f,p)))
v = types.ModuleType('vngameengine')
v.vnge_version='42.9'
v.vnge_game=game
sys.modules['vngameengine']=v
s = types.ModuleType('Studio')
s.OCIChar=OCIChar
s.Studio=box(Instance=box(dicObjectCtrl=dic({5:obj})))
s.Info=box(Instance=box(dicAnimeLoadInfo=dic({0:dic({1:dic({2:box(name=u'\u7acb\u3061',bundlePath='bundle',fileName='file',clip='stand'),3:box(name=u'\u6b69\u304d',bundlePath='bundle',fileName='file',clip='walk')})})}),dicAGroupCategory=dic({0:box(name=u'\u4e00\u822c',dicCategory=dic({1:u'\u65e5\u5e38'}))})))
sys.modules['Studio']=s
a = types.ModuleType('vnactor')
a.ActorCharaStudio=lambda obj:actor
sys.modules['vnactor']=a
s.Info.Instance.dicAnimeLoadInfo[50]=dic({99:dic({0:box(name=u'Wei\u00df missing group')})})
'@
$engine.Execute($stub, $scope) | Out-Null
foreach ($request in @(
 '{"command":"list","limit":1}',
 '{"command":"get","characterId":5}',
 '{"command":"control","characterId":5,"mode":"builtin"}',
 '{"command":"set","characterId":5,"group":0,"category":1,"no":3,"speed":1}',
 '{"command":"control","characterId":5,"mode":"restore"}'
)) {
 $scope.SetVariable('mmdd_request_json', $request)
 $engine.Execute($code, $scope) | Out-Null
 $engine.Execute("if mmdd_response_json is None:
    job,param=jobs.pop(0)
    assert not job(game,param)
    assert job(game,param)
    mmdd_response_json=received.pop()", $scope) | Out-Null
 Write-Output ($scope.GetVariable('mmdd_response_json'))
 $engine.Execute("assert json.loads(mmdd_response_json)['type'] == 'success', mmdd_response_json", $scope) | Out-Null
}
$engine.Execute('assert obj.oiCharInfo.animeInfo.no == 2 and actor.mode == 3 and actor.speed == .5 and controller.Enable', $scope) | Out-Null
Write-Output 'PASS: real inventory including Latin-1 paths, false BaseCheck, direct Animator reset; embedded animation adapter with installed IronPython, CLR dictionaries/Int32, Unicode, acquire/set/restore'
