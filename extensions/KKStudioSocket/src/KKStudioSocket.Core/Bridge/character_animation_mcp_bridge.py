# Fixed adapter for KK CharaStudio + VNGE 42.9; invoked on the Unity main thread.
import json
import math
import hashlib
import datetime
import os


def environment():
    from System import AppDomain
    from System.Diagnostics import Process
    from UnityEngine import Application
    process = Process.GetCurrentProcess()
    versions = {}
    for assembly in AppDomain.CurrentDomain.GetAssemblies():
        name = assembly.GetName()
        if name.Name in ('KK_KKStudioSocket', 'KKAPI', 'BepInEx', 'Unity.Console', 'Assembly-CSharp'):
            versions[str(name.Name)] = str(name.Version)
    inventory = []
    if hasattr(Application, 'dataPath'):
        root = os.path.dirname(str(Application.dataPath))
        for directory in ('mods', os.path.join('BepInEx', 'plugins')):
            for folder, dirs, files in os.walk(os.path.join(root, directory)):
                dirs.sort()
                for filename in sorted(files):
                    if filename.lower().endswith(('.zipmod', '.dll')):
                        path = os.path.join(folder, filename)
                        stat = os.stat(path)
                        inventory.append((os.path.relpath(path, root).replace('\\', '/'), stat.st_size, stat.st_mtime))
    return {'runtimeSession': str(process.Id) + ':' + str(process.StartTime.ToUniversalTime().Ticks),
            'unityVersion': str(Application.unityVersion), 'product': 'KK CharaStudio',
            'vngeVersion': '42.9', 'adapterVersion': '1.2.1', 'assemblies': versions,
            'installationInventoryHash': hashlib.sha256(json.dumps(inventory, ensure_ascii=True).encode('utf-8')).hexdigest(),
            'inventoryFiles': len(inventory),
            'inventoryMethod': 'mods .zipmod and BepInEx/plugins .dll paths, sizes and modification times; not asset content hashes',
            'provenance': 'unknown; catalog includes installed base and MOD entries'}


def integer(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, long)) or value < minimum:
        raise ValueError(label + ' must be an integer >= ' + str(minimum))
    return value


def animation(info, group, category, no):
    # Catalog numbers are the loaded runtime slots, including Sideloader-resolved slots.
    # Use LoadAnime directly; passing these through VNGE's portable-ID conversion twice is wrong.
    try:
        entry = info.dicAnimeLoadInfo[group][category][no]
    except KeyError:
        raise ValueError('Animation slot is not installed: %s/%s/%s' % (group, category, no))
    warnings = []
    group_name, category_name, name = None, None, None
    try:
        names = info.dicAGroupCategory[group]
        group_name = names.name
    except (KeyError, AttributeError):
        warnings.append('missing_group_name')
    try:
        category_name = info.dicAGroupCategory[group].dicCategory[category]
    except (KeyError, AttributeError):
        warnings.append('missing_category_name')
    try:
        name = entry.name
        if not name:
            warnings.append('missing_animation_name')
    except AttributeError:
        warnings.append('missing_animation_name')
    for key, value in [('group', group_name), ('category', category_name), ('animation', name)]:
        if not isinstance(value, basestring) or not value:
            code = 'missing_' + key + '_name'
            if code not in warnings:
                warnings.append(code)
    group_name = group_name if isinstance(group_name, basestring) else None
    category_name = category_name if isinstance(category_name, basestring) else None
    name = name if isinstance(name, basestring) else None
    return {'group': group, 'category': category, 'no': no,
            'groupName': group_name, 'categoryName': category_name, 'name': name,
            'origin': 'unknown', 'warnings': warnings}


def catalog(info, game, refresh=False):
    cached = getattr(game.gdata, 'mcp_animation_catalog', None)
    if cached is not None and cached['source'] == info.dicAnimeLoadInfo and not refresh:
        return cached
    rows, warnings, skipped = [], [], 0
    for group in sorted(info.dicAnimeLoadInfo.Keys):
        for category in sorted(info.dicAnimeLoadInfo[group].Keys):
            for no in sorted(info.dicAnimeLoadInfo[group][category].Keys):
                try:
                    row = animation(info, group, category, no)
                    rows.append(row)
                    if row['warnings']:
                        warnings.append({'group': group, 'category': category, 'no': no,
                                         'codes': row['warnings']})
                except (ValueError, AttributeError, TypeError) as error:
                    skipped += 1
                    warnings.append({'group': group, 'category': category, 'no': no,
                                     'codes': ['skipped_entry'], 'message': str(error)})
    encoded = json.dumps(rows, sort_keys=True, ensure_ascii=True).encode('utf-8')
    metadata = {'schemaVersion': 1, 'exportedAt': datetime.datetime.utcnow().isoformat() + 'Z',
                'environment': environment(), 'catalogHash': hashlib.sha256(encoded).hexdigest(),
                'entries': len(rows), 'skipped': skipped, 'warnings': warnings,
                'complete': skipped == 0, 'namesComplete': not warnings,
                'refreshPolicy': 'refresh after game/MOD/mapping changes; set validates live slots'}
    cached = {'source': info.dicAnimeLoadInfo, 'rows': rows, 'metadata': metadata}
    game.gdata.mcp_animation_catalog = cached
    return cached


def controllers(mmdd, obj):
    return [] if mmdd is None else [c for c in mmdd.motionControllers.values()
                                   if getattr(c, 'ociChar', None) == obj]


def restore(actor, snapshot, mmdd):
    obj = actor.objctrl
    group, category, no = snapshot['animation']
    obj.LoadAnime(group, category, no, snapshot['time'])
    actor.set_anime_speed(snapshot['speed'])
    actor.set_kinematic(snapshot['kinematic'], 1)
    actor.set_FK_active(snapshot['fk'], force=1)
    actor.set_IK_active(snapshot['ik'], force=1)
    # VNGE catches some kinematic errors internally; verify before reporting restoration.
    if (actor.get_kinematic() != snapshot['kinematic'] or
            actor.get_FK_active() != snapshot['fk'] or actor.get_IK_active() != snapshot['ik']):
        raise ValueError('IK/FK restoration failed; snapshot retained for retry')
    current = controllers(mmdd, obj)
    for controller, enabled in snapshot['controllers']:
        if controller in current:
            controller.setEnable(enabled)
            if bool(controller.Enable) != enabled:
                raise ValueError('MMDD control restoration failed; snapshot retained for retry')


def dispatch(request):
    import vngameengine
    from Studio import Studio, Info, OCIChar
    from vnactor import ActorCharaStudio
    game = vngameengine.vnge_game
    if game is None or vngameengine.vnge_version != '42.9':
        raise ValueError('Initialize VNGE 42.9 in CharaStudio first')
    info = Info.Instance
    command = request.get('command')
    if command not in ('list', 'get', 'set', 'control'):
        raise ValueError('Unsupported character animation command')

    if command == 'list':
        offset = integer(request.get('offset', 0), 'offset')
        limit = integer(request.get('limit', 50), 'limit', 1)
        if limit > 100:
            raise ValueError('limit must be <= 100')
        group_filter, category_filter = request.get('group'), request.get('category')
        for label, value in [('group', group_filter), ('category', category_filter)]:
            if value is not None:
                integer(value, label)
        search = request.get('search')
        if search is None:
            search = ''
        if not isinstance(search, basestring) or len(search) > 200:
            raise ValueError('search must be a string of at most 200 characters')
        refresh = request.get('refresh', False)
        if not isinstance(refresh, bool):
            raise ValueError('refresh must be boolean')
        cached = catalog(info, game, refresh)
        matches = [row for row in cached['rows']
                   if (group_filter is None or row['group'] == group_filter)
                   and (category_filter is None or row['category'] == category_filter)
                   and search.lower() in ' '.join(row[key] or '' for key in ('groupName', 'categoryName', 'name')).lower()]
        total = len(matches)
        rows = matches[offset:offset + limit]
        return {'type': 'success', 'data': {'animations': rows, 'total': total,
                'offset': offset, 'nextOffset': offset + len(rows) if offset + len(rows) < total else None,
                'metadata': cached['metadata'],
                'idScope': 'current game runtime; requery after mod changes'}}

    char_id = integer(request.get('characterId'), 'characterId')
    objects = Studio.Instance.dicObjectCtrl
    if not objects.ContainsKey(char_id) or not isinstance(objects[char_id], OCIChar):
        raise ValueError('characterId must identify an existing OCIChar in the scene tree')
    obj = objects[char_id]
    actor = ActorCharaStudio(obj)
    mmdd = getattr(game.gdata, 'mmdd', None)
    if not hasattr(game.gdata, 'mcp_animation_snapshots'):
        game.gdata.mcp_animation_snapshots = {}
    snapshots = game.gdata.mcp_animation_snapshots
    # Scene IDs may be reused after load; never restore a snapshot onto a different object.
    for key in list(snapshots.keys()):
        if not objects.ContainsKey(key) or objects[key] != snapshots[key]['obj']:
            del snapshots[key]
    saved = snapshots.get(char_id)
    motion = controllers(mmdd, obj)
    if command in ('control', 'set') and saved is not None and saved.get('loading'):
        raise ValueError('An animation load is still pending; retry after its response')
    if command in ('control', 'set') and mmdd is not None and mmdd.isPlaying:
        raise ValueError('Pause MMDD before changing built-in animation control')

    if command == 'control':
        mode = request.get('mode')
        if mode == 'builtin':
            if saved is not None and (actor.get_kinematic() != 0 or any(c.Enable for c in motion)):
                raise ValueError('Control changed since acquisition; restore and acquire again')
            if saved is None:
                ai = obj.oiCharInfo.animeInfo
                saved = {'obj': obj, 'animation': (ai.group, ai.category, ai.no),
                         'time': float(obj.charAnimeCtrl.normalizedTime),
                         'speed': actor.get_anime_speed(), 'kinematic': actor.get_kinematic(),
                         'fk': actor.get_FK_active(), 'ik': actor.get_IK_active(),
                         'controllers': [(c, bool(c.Enable)) for c in motion]}
                snapshots[char_id] = saved
                try:
                    for c in motion:
                        c.setEnable(False)
                    actor.set_kinematic(0, 1)
                    if actor.get_kinematic() != 0 or any(c.Enable for c in motion):
                        raise ValueError('Could not release IK/FK or MMDD bone control')
                except Exception:
                    # Keep the snapshot on rollback failure so callers can retry restore.
                    restore(actor, saved, mmdd)
                    del snapshots[char_id]
                    raise
        elif mode == 'restore':
            if saved is None:
                raise ValueError('No saved control state for this character')
            restore(actor, saved, mmdd)
            if 'animation_send_response' not in globals():
                del snapshots[char_id]
        else:
            raise ValueError('mode must be builtin or restore')
    elif command == 'set':
        if saved is None:
            raise ValueError('Acquire character_animation_control mode=builtin first')
        if actor.get_kinematic() != 0 or any(c.Enable for c in motion):
            raise ValueError('IK/FK or MMDD control was re-enabled; restore and acquire again')
        group = integer(request.get('group'), 'group')
        category = integer(request.get('category'), 'category')
        no = integer(request.get('no'), 'no')
        animation(info, group, category, no)
        speed = request.get('speed', 1)
        if isinstance(speed, bool) or not isinstance(speed, (int, long, float)) or math.isnan(speed) or not 0 <= speed <= 3:
            raise ValueError('speed must be finite and between 0 and 3')
        obj.LoadAnime(group, category, no, 0)
        actor.set_anime_speed(speed)
        ai = obj.oiCharInfo.animeInfo
        if (ai.group, ai.category, ai.no) != (group, category, no):
            raise ValueError('Studio did not accept the requested animation')

    ai = obj.oiCharInfo.animeInfo
    data = {'characterId': char_id, 'name': actor.text_name,
            'animation': animation(info, ai.group, ai.category, ai.no),
            'speed': float(actor.get_anime_speed()), 'normalizedTime': float(obj.charAnimeCtrl.normalizedTime),
            'kinematicMode': actor.get_kinematic(), 'fk': list(actor.get_FK_active()),
            'ik': list(actor.get_IK_active()), 'snapshotAvailable': char_id in snapshots,
            'mmddInitialized': mmdd is not None,
            'mmddMotionControllers': [{'name': c.CharName, 'enabled': bool(c.Enable)} for c in motion]}
    return {'type': 'success', 'command': command, 'data': data}


def defer_animation_result(request, result, send):
    # LoadAnime uses an asynchronous controller callback. Evaluate the requested state
    # only after the actual controller is ready; never report the previous loop count as reset.
    import vngameengine
    from Studio import Studio, Info
    from UnityEngine import Time
    game = vngameengine.vnge_game
    obj = Studio.Instance.dicObjectCtrl[request['characterId']]
    saved = game.gdata.mcp_animation_snapshots[request['characterId']]
    restoring = request['command'] == 'control'
    group, category, no = saved['animation'] if restoring else (request['group'], request['category'], request['no'])
    target_time = saved['time'] if restoring else 0
    entry = Info.Instance.dicAnimeLoadInfo[group][category][no]
    started = Time.realtimeSinceStartup
    frames = [0]
    saved['loading'] = True

    def finish(game, unused):
        try:
            objects = Studio.Instance.dicObjectCtrl
            if not objects.ContainsKey(request['characterId']) or objects[request['characterId']] != obj:
                raise ValueError('Character changed while loading animation')
            frames[0] += 1
            if Time.realtimeSinceStartup - started > 3:
                raise ValueError('Animation did not load/reset within 3 seconds; restore saved control state')
            if frames[0] < 2 or not obj.loadedAnimeInfo.BaseCheck(entry.bundlePath, entry.fileName):
                return False
            ctrl = obj.charAnimeCtrl
            ctrl.Play(entry.clip, target_time)
            ctrl.animator.Update(0)
            actual = float(ctrl.normalizedTime)
            if abs(actual - target_time) > .05:
                return False
            saved['loading'] = False
            if restoring:
                del game.gdata.mcp_animation_snapshots[request['characterId']]
            verified = dispatch({'command': 'get', 'characterId': request['characterId']})
            verified['command'] = request['command']
            verified['data']['normalizationVerified'] = True
            verified['data']['requestedStartTime'] = target_time
            send(json.dumps(verified))
        except Exception as error:
            saved['loading'] = False
            send(json.dumps({'type': 'error', 'message': str(error)}))
        return True

    game.append_update_job(finish, None)


try:
    request = json.loads(mmdd_request_json)
    result = dispatch(request)
    if (request.get('command') == 'set' or (request.get('command') == 'control' and request.get('mode') == 'restore')) and 'animation_send_response' in globals():
        defer_animation_result(request, result, animation_send_response)
        mmdd_response_json = None
    else:
        mmdd_response_json = json.dumps(result)
except Exception as error:
    mmdd_response_json = json.dumps({'type': 'error', 'message': str(error)})
