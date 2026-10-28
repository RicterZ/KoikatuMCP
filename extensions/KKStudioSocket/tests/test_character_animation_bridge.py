"""Adapter contracts; run without Unity, with a minimal Studio/VNGE surface."""
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

BRIDGE = (Path(__file__).parents[1] / 'src/KKStudioSocket.Core/Bridge/character_animation_mcp_bridge.py').read_text()


class Dictionary(dict):
    @property
    def Keys(self):
        return list(self)

    def ContainsKey(self, key):
        return key in self


class Character:
    def __init__(self):
        self.oiCharInfo = types.SimpleNamespace(animeInfo=types.SimpleNamespace(group=0, category=1, no=2))
        self.charAnimeCtrl = types.SimpleNamespace(normalizedTime=.25)

    def LoadAnime(self, group, category, no, time):
        self.oiCharInfo.animeInfo = types.SimpleNamespace(group=group, category=category, no=no)
        self.charAnimeCtrl.normalizedTime = time


class Actor:
    def __init__(self, obj):
        self.objctrl = obj
        self.speed = .5
        self.mode = 3
        self.fk = (True, False, True, False, True, True, False)
        self.ik = (True, True, False, True, False)
        self.text_name = 'test character'

    def get_anime_speed(self): return self.speed
    def set_anime_speed(self, speed): self.speed = speed
    def get_kinematic(self): return self.mode
    def set_kinematic(self, mode, force=0): self.mode = mode
    def get_FK_active(self): return self.fk
    def get_IK_active(self): return self.ik
    def set_FK_active(self, flags, force=0): self.fk = flags
    def set_IK_active(self, flags, force=0): self.ik = flags


class Controller:
    def __init__(self, obj, enabled=True):
        self.ociChar, self.Enable, self.CharName = obj, enabled, 'test motion'

    def setEnable(self, enabled): self.Enable = enabled


class AnimationTests(unittest.TestCase):
    def setUp(self):
        self.obj = Character()
        self.actor = Actor(self.obj)
        self.controller = Controller(self.obj)
        self.other = Controller(Character())
        self.disabled = Controller(self.obj, False)
        self.mmdd = types.SimpleNamespace(isPlaying=False, motionControllers={0: self.controller, 1: self.other, 2: self.disabled}, cameraControllers=['unchanged'])
        self.gdata = types.SimpleNamespace(mmdd=self.mmdd)
        self.jobs = []
        self.clock = types.SimpleNamespace(realtimeSinceStartup=0)
        self.objects = Dictionary({5: self.obj, 6: object()})
        info = types.SimpleNamespace(
            dicAnimeLoadInfo=Dictionary({0: Dictionary({1: Dictionary({2: types.SimpleNamespace(name='立ち'), 3: types.SimpleNamespace(name='歩き')})})}),
            dicAGroupCategory=Dictionary({0: types.SimpleNamespace(name='一般', dicCategory=Dictionary({1: '日常'}))}))
        self.modules = {
            'vngameengine': types.SimpleNamespace(vnge_version='42.9', vnge_game=types.SimpleNamespace(gdata=self.gdata, append_update_job=lambda f, p: self.jobs.append((f, p)))),
            'Studio': types.SimpleNamespace(Studio=types.SimpleNamespace(Instance=types.SimpleNamespace(dicObjectCtrl=self.objects)), Info=types.SimpleNamespace(Instance=info), OCIChar=Character),
            'vnactor': types.SimpleNamespace(ActorCharaStudio=lambda obj: self.actor),
            'System': types.SimpleNamespace(AppDomain=types.SimpleNamespace(CurrentDomain=types.SimpleNamespace(GetAssemblies=lambda: []))),
            'System.Diagnostics': types.SimpleNamespace(Process=types.SimpleNamespace(GetCurrentProcess=lambda: types.SimpleNamespace(Id=1, StartTime=types.SimpleNamespace(ToUniversalTime=lambda: types.SimpleNamespace(Ticks=123))))),
            'UnityEngine': types.SimpleNamespace(Application=types.SimpleNamespace(unityVersion='test'), Time=self.clock)}
        self.info = info

    def call(self, command, **kwargs):
        scope = {'mmdd_request_json': json.dumps(dict(type='character_animation', command=command, **kwargs)), 'long': int, 'basestring': str}
        with patch.dict(sys.modules, self.modules):
            exec(compile(BRIDGE, '<animation bridge>', 'exec'), scope)
        return json.loads(scope['mmdd_response_json'])

    def ok(self, command, **kwargs):
        result = self.call(command, **kwargs)
        self.assertEqual(result['type'], 'success', result)
        return result['data']

    def acquire(self): return self.ok('control', characterId=5, mode='builtin')

    def test_catalog_unicode_filter_pagination(self):
        first = self.ok('list', limit=1)
        self.assertEqual((first['total'], first['nextOffset']), (2, 1))
        self.assertEqual(self.ok('list', search='歩')['animations'][0]['no'], 3)
        self.assertEqual(self.ok('list', offset=1)['animations'][0]['name'], '歩き')
        self.assertEqual(self.call('list', limit=101)['type'], 'error')
        self.assertEqual(self.call('list', offset=True)['type'], 'error')
        self.assertEqual(self.call('list', search=False)['type'], 'error')

    def test_missing_names_return_slots_and_explicit_warnings(self):
        self.info.dicAnimeLoadInfo[20] = Dictionary({99: Dictionary({0: types.SimpleNamespace(name='orphan')})})
        self.info.dicAnimeLoadInfo[0][22] = Dictionary({0: types.SimpleNamespace(name='missing category')})
        self.info.dicAnimeLoadInfo[0][1][4] = object()
        result = self.ok('list', limit=2)
        self.assertEqual(result['total'], 5)
        self.assertEqual(result['nextOffset'], 2)
        self.assertTrue(result['metadata']['complete'])
        self.assertFalse(result['metadata']['namesComplete'])
        self.assertEqual(len(result['metadata']['warnings']), 3)
        last = self.ok('list', offset=4, limit=2)
        self.assertIsNone(last['nextOffset'])
        self.assertIsNone(last['animations'][0]['groupName'])
        self.assertEqual(self.ok('list', search='orphan')['total'], 1)
        self.assertEqual(self.ok('list', group=0, category=22)['total'], 1)

    def test_cached_catalog_refresh_and_live_validation(self):
        first = self.ok('list')
        self.info.dicAnimeLoadInfo[0][1][7] = types.SimpleNamespace(name='new mod')
        self.assertEqual(self.ok('list')['total'], 2)
        refreshed = self.ok('list', refresh=True)
        self.assertEqual(refreshed['total'], 3)
        self.assertNotEqual(first['metadata']['catalogHash'], refreshed['metadata']['catalogHash'])
        self.acquire()
        del self.info.dicAnimeLoadInfo[0][1][3]
        self.assertEqual(self.call('set', characterId=5, group=0, category=1, no=3)['type'], 'error')

    def test_deferred_set_resets_actual_animator_before_success(self):
        self.acquire()
        entry = self.info.dicAnimeLoadInfo[0][1][3]
        entry.bundlePath, entry.fileName, entry.clip = 'bundle', 'file', 'walk'
        ready = [False]
        self.obj.loadedAnimeInfo = types.SimpleNamespace(BaseCheck=lambda b, f: ready[0])
        def play(clip, t):
            self.assertEqual(clip, 'walk')
            self.obj.charAnimeCtrl.normalizedTime = t
        self.obj.charAnimeCtrl.Play = play
        self.obj.charAnimeCtrl.animator = types.SimpleNamespace(Update=lambda dt: None)
        received = []
        request = dict(command='set', characterId=5, group=0, category=1, no=3)
        scope = {'mmdd_request_json': json.dumps(request), 'long': int, 'basestring': str,
                 'animation_send_response': received.append}
        with patch.dict(sys.modules, self.modules):
            exec(compile(BRIDGE, '<bridge>', 'exec'), scope)
            self.assertIsNone(scope['mmdd_response_json'])
            self.obj.charAnimeCtrl.normalizedTime = 638
            job, param = self.jobs[0]
            self.assertFalse(job(None, param))
            self.assertFalse(job(None, param))
            self.assertEqual(received, [])
            ready[0] = True
            self.assertTrue(job(None, param))
        result = json.loads(received[0])
        self.assertEqual(result['data']['normalizedTime'], 0)
        self.assertTrue(result['data']['normalizationVerified'])

    def test_deferred_timeout_does_not_claim_success_or_lose_snapshot(self):
        self.acquire()
        entry = self.info.dicAnimeLoadInfo[0][1][3]
        entry.bundlePath, entry.fileName, entry.clip = 'bundle', 'file', 'walk'
        self.obj.loadedAnimeInfo = types.SimpleNamespace(BaseCheck=lambda b, f: False)
        received = []
        scope = {'mmdd_request_json': json.dumps(dict(command='set', characterId=5, group=0, category=1, no=3)),
                 'long': int, 'basestring': str, 'animation_send_response': received.append}
        with patch.dict(sys.modules, self.modules):
            exec(compile(BRIDGE, '<bridge>', 'exec'), scope)
            self.assertEqual(self.call('control', characterId=5, mode='restore')['type'], 'error')
            self.clock.realtimeSinceStartup = 4
            job, param = self.jobs[0]
            self.assertTrue(job(self.modules['vngameengine'].vnge_game, param))
        self.assertEqual(json.loads(received[0])['type'], 'error')
        self.assertTrue(self.ok('get', characterId=5)['snapshotAvailable'])
        self.ok('control', characterId=5, mode='restore')

    def test_switch_and_restore_exact_state_without_other_character_or_camera_changes(self):
        self.acquire()
        self.acquire()  # Must not replace the original snapshot.
        self.assertFalse(self.controller.Enable)
        self.assertTrue(self.other.Enable)
        self.assertEqual(self.actor.mode, 0)
        for no in (2, 3, 2):
            result = self.ok('set', characterId=5, group=0, category=1, no=no, speed=1)
            self.assertEqual(result['animation']['no'], no)
        self.actor.fk = (False,) * 7
        self.ok('control', characterId=5, mode='restore')
        self.assertTrue(self.controller.Enable)
        self.assertFalse(self.disabled.Enable)
        self.assertEqual((self.actor.mode, self.actor.speed), (3, .5))
        self.assertEqual(self.obj.charAnimeCtrl.normalizedTime, .25)
        self.assertEqual(self.mmdd.cameraControllers, ['unchanged'])
        self.assertFalse(self.ok('get', characterId=5)['snapshotAvailable'])

    def test_reject_invalid_character_unknown_animation_and_unacquired_set(self):
        for char_id in (-1, True, 6, 99):
            self.assertEqual(self.call('get', characterId=char_id)['type'], 'error')
        self.assertEqual(self.call('set', characterId=5, group=0, category=1, no=3)['type'], 'error')
        self.acquire()
        for invalid in ({'no': 999}, {'speed': -1}, {'speed': float('nan')}, {'speed': float('inf')}, {'group': True}):
            args = dict(characterId=5, group=0, category=1, no=3)
            args.update(invalid)
            self.assertEqual(self.call('set', **args)['type'], 'error')
        self.assertEqual(self.obj.oiCharInfo.animeInfo.no, 2)

    def test_playing_and_reenabled_controller_block_mutation(self):
        self.mmdd.isPlaying = True
        self.assertEqual(self.call('control', characterId=5, mode='builtin')['type'], 'error')
        self.assertTrue(self.controller.Enable)
        self.mmdd.isPlaying = False
        self.acquire()
        self.controller.Enable = True
        self.assertEqual(self.call('set', characterId=5, group=0, category=1, no=3)['type'], 'error')

    def test_scene_reload_does_not_restore_onto_reused_id(self):
        self.acquire()
        self.objects[5] = Character()
        self.assertEqual(self.call('control', characterId=5, mode='restore')['type'], 'error')

    def test_no_mmdd_required_for_builtin_animation(self):
        del self.gdata.mmdd
        self.assertFalse(self.acquire()['mmddInitialized'])
        self.ok('set', characterId=5, group=0, category=1, no=3)
        self.ok('control', characterId=5, mode='restore')

    def test_restore_failure_retains_snapshot_for_retry(self):
        self.acquire()
        original = self.controller.setEnable
        self.controller.setEnable = lambda value: None
        self.assertEqual(self.call('control', characterId=5, mode='restore')['type'], 'error')
        self.assertTrue(self.ok('get', characterId=5)['snapshotAvailable'])
        self.controller.setEnable = original
        self.ok('control', characterId=5, mode='restore')

    def test_failed_acquisition_rolls_back(self):
        original = self.actor.set_kinematic
        self.actor.set_kinematic = lambda mode, force=0: original(mode, force) if mode != 0 else None
        self.assertEqual(self.call('control', characterId=5, mode='builtin')['type'], 'error')
        self.assertTrue(self.controller.Enable)
        self.assertFalse(self.ok('get', characterId=5)['snapshotAvailable'])


if __name__ == '__main__':
    unittest.main()
