"""Contract checks for the embedded adapter, without starting Studio."""
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest

BRIDGE = (Path(__file__).parents[1] / 'src/KKStudioSocket.Core/Bridge/mmdd_mcp_bridge.py').read_text()


class Camera:
    def __init__(self, name='old', keyframes=None):
        self.FileName = name
        self.cameraKeyFrames = keyframes or []
        self.enable = True
        self.bindCameraId = None
        self.delay = 0
        self.playbackSpeed = 1

    @property
    def KeyframesForExport(self):
        return self.cameraKeyFrames

    @property
    def maxFrameNo(self):
        return max([k.frameNo for k in self.cameraKeyFrames] or [0])

    def createKeyframeFromCurrentCamera(self, frame, curves):
        return types.SimpleNamespace(frameNo=frame)

    def updateKeyframe(self, keyframe):
        self.cameraKeyFrames = [k for k in self.cameraKeyFrames if k.frameNo != keyframe.frameNo] + [keyframe]


class Director:
    def __init__(self):
        self.isPlaying = False
        self.curFrame = 0
        self.totalFrame = self.EndFrame = 600
        self.StartFrame = 0
        self.playFPS = 30
        self.playTimer = 'record'
        self.cameraControllers = [Camera()]
        self.updates = 0

    def refreshTotalFrame(self):
        self.totalFrame = self.EndFrame = max([600] + [c.maxFrameNo for c in self.cameraControllers])

    def stop(self):
        self.isPlaying = False

    def start(self):
        self.isPlaying = True

    def gotoFrame(self, frame):
        if not self.isPlaying:
            self.curFrame = min(frame, self.totalFrame)

    def update(self, force=False):
        self.updates += 1

    def getEnabledMainCamera(self):
        return next((c for c in self.cameraControllers if c.enable), None)

    def addCameraController(self, camera):
        self.cameraControllers.append(camera)

    def loadCameraKeyframes(self, path, keys):
        camera = Camera(path, keys)
        self.addCameraController(camera)
        return camera

    def enableCameraController(self, camera, enabled):
        for c in self.cameraControllers:
            c.enable = c is camera


class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.mmdd = Director()
        self.game = types.SimpleNamespace(gdata=types.SimpleNamespace(mmdd=self.mmdd))
        sys.modules['vngameengine'] = types.SimpleNamespace(vnge_version='42.9', vnge_game=self.game)
        class VmdLib:
            @staticmethod
            def loadVmd(path):
                return ('camera', [], [], [types.SimpleNamespace(frameNo=900)], [])
            @staticmethod
            def saveVmd(path, bone, morph, camera, ik):
                Path(path).write_bytes(b'camera-test')
                return True, 'ok'
        sys.modules['vmdlib'] = types.SimpleNamespace(CameraController=Camera, VmdLib=VmdLib)

    def request(self, command, **kwargs):
        scope = {'mmdd_request_json': json.dumps(dict(command=command, **kwargs)), 'long': int}
        exec(compile(BRIDGE, 'mmdd_mcp_bridge.py', 'exec'), scope)
        return json.loads(scope['mmdd_response_json'])

    def test_seek_pauses_and_evaluates_same_frame(self):
        self.mmdd.isPlaying = True
        result = self.request('seek', frame=115)
        self.assertEqual(result['data']['frame'], 115)
        self.assertFalse(result['data']['isPlaying'])
        self.request('seek', frame=115)
        self.assertEqual(self.mmdd.updates, 2)

    def test_invalid_seek_does_not_pause_or_clamp(self):
        self.mmdd.isPlaying = True
        for frame in [-1, 601, True, 1.5, None]:
            self.assertEqual(self.request('seek', frame=frame)['type'], 'error')
        self.assertTrue(self.mmdd.isPlaying)
        self.assertEqual(self.mmdd.curFrame, 0)

    def test_loading_retains_tracks_and_activates_new(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'test.vmd')
            Path(path).touch()
            result = self.request('load_camera', path=path)
        self.assertEqual(result['type'], 'success')
        self.assertEqual(len(self.mmdd.cameraControllers), 2)
        self.assertFalse(self.mmdd.cameraControllers[0].enable)
        self.assertTrue(self.mmdd.cameraControllers[1].enable)
        self.assertEqual(self.mmdd.totalFrame, 900)

    def test_record_replaces_keyframe_and_extends_length(self):
        self.request('record_camera', frame=901)
        self.request('record_camera', frame=901)
        self.assertEqual(len(self.mmdd.cameraControllers[0].cameraKeyFrames), 1)
        self.assertEqual(self.mmdd.totalFrame, 901)
        self.assertEqual(self.mmdd.curFrame, 901)

    def test_export_refuses_overwrite(self):
        self.request('record_camera', frame=115)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'new.vmd')
            self.assertEqual(self.request('export_camera', path=path)['type'], 'success')
            self.assertEqual(self.request('export_camera', path=path)['type'], 'error')
            self.assertEqual(Path(path).read_bytes(), b'camera-test')

    def test_missing_runtime_and_wrong_version(self):
        sys.modules['vngameengine'].vnge_game = None
        self.assertEqual(self.request('status')['type'], 'error')
        sys.modules['vngameengine'].vnge_game = self.game
        sys.modules['vngameengine'].vnge_version = '99'
        self.assertEqual(self.request('status')['type'], 'error')

    def test_invalid_camera_index_path_and_unknown_command(self):
        for command, args in [('record_camera', dict(frame=1, cameraIndex=3)),
                              ('record_camera', dict(frame=1, cameraIndex=-1)),
                              ('load_camera', dict(path='relative.vmd')),
                              ('export_camera', dict(path='/missing-folder/out.vmd')),
                              ('eval', dict())]:
            self.assertEqual(self.request(command, **args)['type'], 'error')

    def test_follow_camera_does_not_break_status_or_seek(self):
        follow = types.SimpleNamespace(enable=True, bindCameraId=None)
        self.mmdd.cameraControllers = [follow]
        self.mmdd.refreshTotalFrame = lambda: None
        self.assertEqual(self.request('status')['type'], 'success')
        self.assertEqual(self.request('seek', frame=115)['type'], 'success')
        self.assertEqual(self.request('record_camera', frame=115)['type'], 'error')
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'follow.vmd')
            self.assertEqual(self.request('export_camera', path=path)['type'], 'error')
            self.assertFalse(os.path.exists(path))

    def test_record_rejects_track_time_adjustments(self):
        camera = self.mmdd.cameraControllers[0]
        camera.delay = 1
        self.assertEqual(self.request('record_camera', frame=115)['type'], 'error')
        camera.delay = 0
        camera.playbackSpeed = 2
        self.assertEqual(self.request('record_camera', frame=115)['type'], 'error')
        self.assertEqual(camera.cameraKeyFrames, [])

    def test_record_requires_paused_view(self):
        self.mmdd.isPlaying = True
        self.assertEqual(self.request('record_camera', frame=115)['type'], 'error')
        self.assertEqual(self.mmdd.cameraControllers[0].cameraKeyFrames, [])
        self.assertTrue(self.mmdd.isPlaying)

    def test_play_pause_status(self):
        self.assertTrue(self.request('play')['data']['isPlaying'])
        self.assertFalse(self.request('pause')['data']['isPlaying'])
        self.assertEqual(self.request('status')['data']['vmdFrameRate'], 30)


if __name__ == '__main__':
    unittest.main()
