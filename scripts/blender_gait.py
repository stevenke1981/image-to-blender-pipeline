"""Blender 4.2+ entrypoint; run from a disposable scene/copy, never overwrite input.
blender -b --python scripts/blender_gait.py -- --config examples/gait/biped_adult.json --out /tmp/gait/adult
Existing prepared rig: add --rig-map examples/gait/biped.rig.json --input model.blend
"""
import argparse
import copy
import json
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gait.core import validate, limbs, trajectory, solve_leg, measure, frame_count
import bpy
from mathutils import Matrix, Vector, Euler


def default_map(c):
    return dict(armature='GaitRig', pelvis='pelvis', limbs={
        n:dict(upper=f'{n}.upper', lower=f'{n}.lower', foot=f'{n}.foot',
               sole_offset=[0,0,0], ground_probes=[[0,0,0],[0,.14,0]], bend_sign=1 if not n.startswith('front') else -1)
        for n in limbs(c)})


def test_rig(c, mapping):
    bpy.ops.object.armature_add()
    rig=bpy.context.object
    rig.name=mapping['armature']
    bpy.ops.object.mode_set(mode='EDIT')
    eb=rig.data.edit_bones
    for b in list(eb): eb.remove(b)
    length=c['body']['leg_length_m']; height=length*.88
    pelvis=eb.new(mapping['pelvis']); pelvis.head=(0,0,height); pelvis.tail=(0,0,height+.2)
    for n, m in mapping['limbs'].items():
        x=(-1 if n.endswith('left') else 1)*c['body']['hip_width_m']/2
        y=(c['body']['body_length_m']/2*(1 if n.startswith('front') else -1)
           if c['type']=='quadruped' else 0.)
        upper=length*c['body']['upper_leg_ratio']; lower=length-upper
        hip=[x,y,height]; foot=[x,y,0]
        knee,_=solve_leg(hip,foot,upper,lower,m['bend_sign'])
        parent=pelvis
        for role,head,tail in [('upper',hip,knee),('lower',knee,foot),('foot',foot,[x,y+.14,0])]:
            b=eb.new(m[role]); b.head=head; b.tail=tail; b.parent=parent; parent=b
    bpy.ops.object.mode_set(mode='OBJECT')
    rig.show_in_front=True
    # Renderable bone proxies parented with bone-space inverse; armatures themselves don't render.
    for bone in rig.data.bones:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=4, radius=1)
        proxy=bpy.context.object; proxy.name='preview_'+bone.name
        center=(bone.head_local+bone.tail_local)/2
        proxy.matrix_world=Matrix.Translation(center) @ bone.matrix_local.to_quaternion().to_matrix().to_4x4()
        proxy.scale=(.035, bone.length/2, .035)
        world=proxy.matrix_world.copy()
        proxy.parent=rig; proxy.parent_type='BONE'; proxy.parent_bone=bone.name
        bpy.context.view_layer.update()
        proxy.matrix_world=world
    return rig


def preflight(rig, m, c):
    if rig.type!='ARMATURE': raise ValueError('mapped object is not an armature')
    if rig.animation_data and rig.animation_data.nla_tracks:
        raise ValueError('bake on a rig copy without NLA tracks')
    if rig.constraints or (rig.animation_data and rig.animation_data.drivers):
        raise ValueError('object constraints/drivers unsupported; prepare a clean deform rig copy')
    if any(abs(v-1)>1e-6 for v in rig.scale) or rig.rotation_euler.length>1e-6 or rig.location.length>1e-6:
        raise ValueError('apply object transforms; rig must be at world origin, +Y forward/+Z up')
    if set(m['limbs'])!=set(limbs(c)): raise ValueError('mapping limb set mismatch')
    names=[m['pelvis']]+[v[k] for v in m['limbs'].values() for k in ('upper','lower','foot')]
    if len(names)!=len(set(names)):raise ValueError('bone map contains duplicate roles')
    for n in names:
        if n not in rig.pose.bones:raise ValueError(f'missing bone {n}')
        if rig.pose.bones[n].constraints:raise ValueError(f'{n}: constraints unsupported')
    for n,v in m['limbs'].items():
        u,l,f=[rig.data.bones[v[k]] for k in ('upper','lower','foot')]
        if l.parent!=u or f.parent!=l or u.parent!=rig.data.bones[m['pelvis']]:
            raise ValueError(f'{n}: expected pelvis > upper > lower > foot direct chain')
        if (u.tail_local-l.head_local).length>1e-5 or (l.tail_local-f.head_local).length>1e-5:
            raise ValueError(f'{n}: disconnected chain joints')
        if abs(u.length+l.length-c['body']['leg_length_m'])>1e-4:
            raise ValueError(f'{n}: JSON leg length differs from rig; regenerate profile')
        if abs(u.length/(u.length+l.length)-c['body']['upper_leg_ratio'])>1e-4:
            raise ValueError(f'{n}: upper_leg_ratio differs from rig')
        if v['bend_sign'] not in (-1,1):raise ValueError('bend_sign must be -1 or +1')
        if len(v['sole_offset'])!=3 or not all(math.isfinite(x) for x in v['sole_offset']):
            raise ValueError('sole_offset must be finite bone-local vector')
        probes=v.get('ground_probes')
        if not probes or any(len(q)!=3 or not all(math.isfinite(x) for x in q) for q in probes):
            raise ValueError('ground_probes must contain finite bone-local heel/toe contact points')
        expected_x=(-1 if n.endswith('left') else 1)*c['body']['hip_width_m']/2
        expected_y=(c['body']['body_length_m']/2*(1 if n.startswith('front') else -1) if c['type']=='quadruped' else 0)
        if abs(u.head_local.x-expected_x)>1e-4 or abs(u.head_local.y-expected_y)>1e-4:
            raise ValueError(f'{n}: JSON hip layout differs from rig rest pose')


def set_segment(pb, start, end):
    rest=pb.bone
    rotation=(rest.tail_local-rest.head_local).rotation_difference(Vector(end)-Vector(start))
    pb.matrix=Matrix.Translation(Vector(start)) @ rotation.to_matrix().to_4x4() @ rest.matrix_local.to_quaternion().to_matrix().to_4x4()
    bpy.context.view_layer.update()


def key(pb, frame):
    pb.rotation_mode='QUATERNION'
    for path in ('location','rotation_quaternion','scale'):pb.keyframe_insert(path,frame=frame,group=pb.name)


def fcurves(action):
    # 4.4+/5.x layered Actions, with legacy 4.2 fallback. Never access removed API on 5.x.
    if hasattr(action,'layers') and len(action.layers):
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    yield from bag.fcurves
    else:
        yield from action.fcurves


def bake(c, rig, m):
    preflight(rig,m,c)
    rig.animation_data_clear()  # caller must use a copy; no NLA/driver rig accepted above
    samples=trajectory(c)
    scene=bpy.context.scene; scene.render.fps=c['fps'];scene.render.fps_base=1
    scene.frame_start=1;scene.frame_end=frame_count(c) # exclude duplicated closing key during playback
    pelvis=rig.pose.bones[m['pelvis']]; rest=pelvis.bone.matrix_local.copy()
    origin=rest.translation.copy()
    for row in samples:
        frame=1+row['time_s']*c['fps']
        scene.frame_set(math.floor(frame),subframe=frame%1)
        rig.location=Vector(row['root']);rig.keyframe_insert('location',frame=frame)
        rot=Euler(row['pelvis_rotation_rad'],'XYZ').to_matrix().to_4x4()
        pm=Matrix.Translation(origin+Vector(row['com'])) @ rot @ rest.to_quaternion().to_matrix().to_4x4()
        pelvis.matrix=pm;bpy.context.view_layer.update(); key(pelvis,frame)
        for n,v in m['limbs'].items():
            u,l,f=[rig.pose.bones[v[k]] for k in ('upper','lower','foot')]
            hip=pm @ rest.inverted() @ u.bone.head_local
            # Foot orientation remains at rest, so bone-local sole offset maps predictably.
            sole=Vector(row['feet'][n]['position'])-Vector(row['root'])
            offset=f.bone.matrix_local.to_3x3() @ Vector(v['sole_offset'])
            ankle=sole-offset
            knee,angles=solve_leg(list(hip),list(ankle),u.bone.length,l.bone.length,v['bend_sign'])
            for joint,angle in angles.items():
                lo,hi=c['joint_limits_rad'][joint]
                if not lo-1e-6<=angle<=hi+1e-6:raise ValueError(f'{n} {joint}: angle {angle} outside limits')
            row['feet'][n]['joint_angles_rad']=angles
            set_segment(u,hip,knee);key(u,frame)
            set_segment(l,knee,ankle);key(l,frame)
            f.matrix=Matrix.Translation(ankle) @ f.bone.matrix_local.to_quaternion().to_matrix().to_4x4()
            bpy.context.view_layer.update();key(f,frame)
    action=rig.animation_data.action;action.name=c['name'];action.use_fake_user=True
    for fc in fcurves(action):
        for kp in fc.keyframe_points:kp.interpolation='LINEAR'
    return samples, action


def evaluated_samples(c,rig,m,planned):
    actual=copy.deepcopy(planned)
    for row in actual:
        frame=1+row['time_s']*c['fps']
        bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1)
        evaluated=rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
        row['pelvis_matrix']=[list(r) for r in evaluated.pose.bones[m['pelvis']].matrix]
        row['bone_matrices']={n:[list(r) for r in b.matrix] for n,b in evaluated.pose.bones.items()}
        for n,v in m['limbs'].items():
            foot=evaluated.pose.bones[v['foot']]
            row['feet'][n]['position']=list(evaluated.matrix_world @ foot.matrix @ Vector(v['sole_offset']))
            row['feet'][n]['ground_probe_z_m']=[(evaluated.matrix_world @ foot.matrix @ Vector(q)).z for q in v['ground_probes']]
    return actual


def render_preview(c,out):
    scene=bpy.context.scene
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.005))
    bpy.ops.object.light_add(type='AREA',location=(2,-2,5));bpy.context.object.data.energy=800;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=5
    bpy.ops.object.camera_add(location=(3,-3,2))
    cam=bpy.context.object; target=Vector((0,c['stride_m']/2,c['body']['leg_length_m']*.5))
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=max(3,c['body']['body_length_m']*2)
    scene.camera=cam;scene.render.engine='BLENDER_EEVEE_NEXT'
    scene.render.resolution_x=640;scene.render.resolution_y=480;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.world.color=(.2,.2,.2)
    for i,frame in enumerate((1,1+frame_count(c)//3,1+2*frame_count(c)//3)):
        scene.frame_set(frame);scene.render.filepath=str(out/f'preview-{i+1}.png');bpy.ops.render.render(write_still=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True)
    p.add_argument('--rig-map');p.add_argument('--input');p.add_argument('--skip-render',action='store_true')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    c=validate(json.loads(Path(args.config).read_text()));out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    # Do not leave a stale PASS report when a subsequent invocation fails.
    (out/'validation.json').write_text(json.dumps(dict(status='RUNNING',blender_version=bpy.app.version_string)))
    try:
        if bool(args.input)!=bool(args.rig_map):raise ValueError('--input and --rig-map must be supplied together')
        if args.input and Path(args.input).resolve()==out/'animation.blend':raise ValueError('output would overwrite input')
        if args.input:bpy.ops.wm.open_mainfile(filepath=str(Path(args.input).resolve()))
        else:bpy.ops.wm.read_factory_settings(use_empty=True)
        m=json.loads(Path(args.rig_map).read_text()) if args.rig_map else default_map(c)
        rig=bpy.data.objects[m['armature']] if args.input else test_rig(c,m)
        planned,action=bake(c,rig,m)
        actual=evaluated_samples(c,rig,m,planned);report=measure(c,actual)
        # Every mapped bone must also close in armature space after one root-motion cycle.
        report['bone_loop_max_matrix_error']=max(abs(actual[-1]['bone_matrices'][n][i][j]-actual[0]['bone_matrices'][n][i][j]) for n in actual[0]['bone_matrices'] for i in range(4) for j in range(4))
        report['ground_probe_penetration_m']=max(0.,max(-z for row in actual for foot in row['feet'].values() for z in foot['ground_probe_z_m']))
        report['passed'] &= report['bone_loop_max_matrix_error']<1e-4 and report['ground_probe_penetration_m']<=.002
        report.update(status='PASS' if report['passed'] else 'FAIL',blender_version=bpy.app.version_string,action=action.name,source='evaluated Blender pose',samples=len(actual))
        (out/'animation-data.json').write_text(json.dumps(actual,indent=2))
        (out/'rig-map.json').write_text(json.dumps(m,indent=2))
        if not args.skip_render:render_preview(c,out)
        bpy.context.scene.frame_set(1)
        bpy.ops.wm.save_as_mainfile(filepath=str(out/'animation.blend'))
        (out/'validation.json').write_text(json.dumps(report,indent=2))
        if not report['passed']:raise RuntimeError('evaluated gait validation failed; see validation.json')
    except Exception as exc:
        (out/'failure.json').write_text(json.dumps(dict(status='FAIL',error=str(exc)),indent=2))
        (out/'validation.json').write_text(json.dumps(dict(status='FAIL',error=str(exc),blender_version=bpy.app.version_string),indent=2))
        raise

if __name__=='__main__':main()
