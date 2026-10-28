# Adapter for VNGE 42.9 / MMD Director 2.9.4. Executed on Studio's main thread.
import json
import os


def dispatch(request):
    import vngameengine
    game = vngameengine.vnge_game
    if game is None or not hasattr(game.gdata, 'mmdd'):
        raise ValueError('MMDD is not initialized. Open VNGE > Utilities > MMD Director first.')
    if vngameengine.vnge_version != '42.9':
        raise ValueError('Unsupported VNGE version; this adapter targets 42.9 / MMDD 2.9.4.')
    mmdd = game.gdata.mmdd
    command = request.get('command')
    if command not in ('status', 'pause', 'seek', 'play', 'load_camera', 'record_camera', 'export_camera'):
        raise ValueError('Unsupported MMDD command')

    frame = request.get('frame')
    if command in ('seek', 'record_camera'):
        if isinstance(frame, bool) or not isinstance(frame, (int, long)) or frame < 0:
            raise ValueError('frame must be a non-negative integer')
    index = request.get('cameraIndex')
    if index is not None and (isinstance(index, bool) or not isinstance(index, (int, long)) or index < 0):
        raise ValueError('cameraIndex must be a non-negative integer')
    path = request.get('path')
    if command in ('load_camera', 'export_camera'):
        if not path or not os.path.isabs(path) or os.path.splitext(path)[1].lower() != '.vmd':
            raise ValueError('path must be an absolute game-host .vmd path')
        if command == 'load_camera' and not os.path.isfile(path):
            raise ValueError('Camera VMD does not exist')
        if command == 'export_camera' and (os.path.exists(path) or not os.path.isdir(os.path.dirname(path))):
            raise ValueError('Export requires an existing parent directory and a new filename')

    if command == 'seek':
        mmdd.refreshTotalFrame()
        if frame > mmdd.totalFrame:
            raise ValueError('frame exceeds totalFrame; no clamped seek was performed')
    if command == 'record_camera' and mmdd.isPlaying:
        raise ValueError('Pause MMDD before adjusting and recording the camera')
    if command in ('pause', 'seek', 'load_camera'):
        mmdd.stop()
        if mmdd.isPlaying:
            raise ValueError('MMDD did not pause')

    if command == 'seek':
        mmdd.gotoFrame(frame)
        mmdd.update(True)
    elif command == 'play':
        mmdd.start()
        if not mmdd.isPlaying:
            raise ValueError('MMDD refused playback; check assets and controller verification')
    elif command == 'load_camera':
        from vmdlib import VmdLib
        result = VmdLib.loadVmd(path)
        if len(result) != 5 or not result[3]:
            raise ValueError('Invalid VMD or no camera keyframes')
        controller = mmdd.loadCameraKeyframes(path, result[3])
        if controller is None:
            raise ValueError('MMDD could not construct camera controller')
        mmdd.enableCameraController(controller, True)
        mmdd.refreshTotalFrame()
        mmdd.update(True)
    elif command in ('record_camera', 'export_camera'):
        if index is not None:
            if index >= len(mmdd.cameraControllers):
                raise ValueError('cameraIndex is out of range')
            controller = mmdd.cameraControllers[index]
        else:
            controller = mmdd.getEnabledMainCamera()
        if controller is not None and not hasattr(controller, 'KeyframesForExport'):
            raise ValueError('Selected camera is a follow camera; load or select a VMD camera track first')
        if command == 'record_camera':
            if controller is not None and (controller.delay != 0 or controller.playbackSpeed != 1):
                raise ValueError('Recording requires camera delay=0 and playbackSpeed=1, as in MMDD keyframe editing')
            # Capture before evaluation changes the hand-adjusted view.
            if controller is None:
                from vmdlib import CameraController
                controller = CameraController('MCP Camera', [])
                mmdd.addCameraController(controller)
            if controller.bindCameraId is not None:
                raise ValueError('Recording supports the main Studio camera only')
            keyframe = controller.createKeyframeFromCurrentCamera(frame, None)
            controller.updateKeyframe(keyframe)
            mmdd.refreshTotalFrame()
            mmdd.gotoFrame(frame)
            mmdd.update(True)
        else:
            if controller is None or not controller.KeyframesForExport:
                raise ValueError('No camera keyframes to export')
            from vmdlib import VmdLib
            # Reserve the filename atomically; never overwrite an existing file.
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(descriptor)
            ok, message = VmdLib.saveVmd(path, None, None, controller.KeyframesForExport, None)
            if not ok:
                os.remove(path)
                raise ValueError('VMD export failed: ' + str(message))

    data = {
        'vngeVersion': vngameengine.vnge_version, 'adapterTarget': 'MMDD 2.9.4',
        'isPlaying': bool(mmdd.isPlaying), 'frame': float(mmdd.curFrame),
        'playFPS': float(mmdd.playFPS), 'vmdFrameRate': 30,
        'totalFrame': float(mmdd.totalFrame), 'startFrame': float(mmdd.StartFrame),
        'endFrame': float(mmdd.EndFrame), 'timerMode': mmdd.playTimer,
        'cameras': [{'index': i, 'name': getattr(c, 'FileName', c.__class__.__name__), 'enabled': bool(c.enable),
                     'keyframes': len(c.KeyframesForExport) if hasattr(c, 'KeyframesForExport') else None,
                     'maxFrame': float(c.maxFrameNo) if hasattr(c, 'maxFrameNo') else None,
                     'delay': getattr(c, 'delay', None), 'playbackSpeed': getattr(c, 'playbackSpeed', None)}
                    for i, c in enumerate(mmdd.cameraControllers)]
    }
    return {'type': 'success', 'command': command, 'data': data}


try:
    mmdd_response_json = json.dumps(dispatch(json.loads(mmdd_request_json)))
except Exception as error:
    mmdd_response_json = json.dumps({'type': 'error', 'message': str(error)})
