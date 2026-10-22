"""Deterministic artistic walk planner. Metres, seconds, radians; +Y forward, +Z up.
No biomechanics/medical claims. No Blender dependency.
"""
import copy
import json
import math
from pathlib import Path

TAU = 2 * math.pi
SCHEMA = Path(__file__).resolve().parents[2] / 'schemas/gait.schema.json'


def check_schema(value, schema, path='$'):
    """Validate the deliberately small JSON Schema vocabulary used by our contract.

    Also usable inside Blender without installing third-party modules.
    """
    typ = schema.get('type')
    types = {'object': dict, 'array': list, 'string': str, 'number': (int, float),
             'integer': int, 'boolean': bool}
    if typ and (not isinstance(value, types[typ]) or
                (typ in ('number', 'integer') and isinstance(value, bool))):
        raise ValueError(f'{path}: expected {typ}')
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
            raise ValueError(f'{path}: non-finite number')
        for key, test in [('minimum', lambda n: value >= n), ('maximum', lambda n: value <= n),
                          ('exclusiveMinimum', lambda n: value > n)]:
            if key in schema and not test(schema[key]):
                raise ValueError(f'{path}: violates {key}')
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError(f'{path}: invalid enum')
    if 'const' in schema and value != schema['const']:
        raise ValueError(f'{path}: invalid constant')
    if isinstance(value, dict):
        props = schema.get('properties', {})
        missing = set(schema.get('required', [])) - value.keys()
        if missing:
            raise ValueError(f'{path}: missing {sorted(missing)}')
        if schema.get('additionalProperties') is False and value.keys() - props.keys():
            raise ValueError(f'{path}: unknown fields {value.keys() - props.keys()}')
        for key, val in value.items():
            if key in props:
                check_schema(val, props[key], f'{path}.{key}')
    if isinstance(value, list):
        if len(value) < schema.get('minItems', 0) or len(value) > schema.get('maxItems', math.inf):
            raise ValueError(f'{path}: invalid length')
        for i, val in enumerate(value):
            check_schema(val, schema.get('items', {}), f'{path}[{i}]')


def validate(config):
    check_schema(config, json.loads(SCHEMA.read_text()))
    c = config
    if c['type'] == 'serpentine':
        raise NotImplementedError('serpentine is reserved; no walk Action can be generated')
    names = limbs(c)
    if set(c['phase_offsets']) != set(names):
        raise ValueError('phase_offsets must contain exactly the active limbs')
    if abs(c['cycle_s'] * c['cadence_steps_per_s'] - 2) > 1e-6:
        raise ValueError('cadence is alternating step pairs: cycle_s * cadence = 2')
    if abs(c['stride_m'] - 2 * c['step_length_m']) > 1e-6:
        raise ValueError('stride_m must equal two step lengths')
    if abs(c['speed_mps'] * c['cycle_s'] - c['stride_m']) > 1e-6:
        raise ValueError('speed * cycle_s must equal stride_m')
    if abs(c['cycle_s']*c['fps']-round(c['cycle_s']*c['fps']))>1e-6:
        raise ValueError('cycle must span an integer number of frames')
    if abs(c['stance_duration_s']-c['stance_fraction']*c['cycle_s'])>1e-6:
        raise ValueError('stance_duration_s must equal stance_fraction * cycle_s')
    if c['foot_clearance_m'] >= c['body']['leg_length_m'] * .5:
        raise ValueError('foot clearance must be less than half leg length')
    if any(c['joint_limits_rad'][n][0] >= c['joint_limits_rad'][n][1]
           for n in ('hip', 'knee', 'ankle')):
        raise ValueError('joint limits must be ordered')
    return c


def limbs(c):
    return ['left', 'right'] if c['type'] == 'biped' else ['hind_left', 'front_left', 'hind_right', 'front_right']


def plan(kind='biped', age_years=25., maturity_years=18., leg_length_m=.9,
         body_length_m=.8, hip_width_m=.3, upper_leg_ratio=.5,
         speed_mps=.65, state='neutral', fps=30):
    if kind not in ('biped', 'quadruped') or state not in ('neutral', 'tired', 'energetic'):
        raise ValueError('unsupported gait or state')
    vals = [age_years, maturity_years, leg_length_m, body_length_m, hip_width_m,
            upper_leg_ratio, speed_mps, fps]
    if not all(math.isfinite(x) and x > 0 for x in vals):
        raise ValueError('profile values must be finite and positive')
    # Species-relative age ratio, intentionally an editable art-direction heuristic.
    age_ratio = age_years / maturity_years
    factor = .8 if age_ratio < .7 or age_ratio > 3 else 1.
    factor *= {'neutral': 1., 'tired': .75, 'energetic': 1.1}[state]
    # Keep low-speed walks and two-bone chains reachable. Reject running speeds.
    if speed_mps > 1.5 * math.sqrt(leg_length_m):
        raise ValueError('speed outside supported walk envelope; use a run generator')
    stride = min(leg_length_m * .65 * factor, speed_mps * 2.)
    cycle = stride / speed_mps
    frames = max(8, round(cycle * fps))
    cycle = frames / fps  # quantize duration, then derive every coupled field
    stride = speed_mps * cycle
    c = dict(schema_version='1.0', name=f'{kind}_{state}', type=kind,
             profile=dict(age_years=age_years, maturity_years=maturity_years, state=state),
             body=dict(leg_length_m=leg_length_m, body_length_m=body_length_m,
                       hip_width_m=hip_width_m, upper_leg_ratio=upper_leg_ratio),
             fps=fps, cycle_s=cycle, speed_mps=speed_mps,
             stride_m=stride, step_length_m=stride / 2,
             cadence_steps_per_s=2 / cycle, stance_fraction=.66 if state == 'tired' else .6,
             foot_clearance_m=leg_length_m * (.045 if state == 'tired' else .08),
             pelvis_rotation_rad=[.015, .025, .035],
             com_displacement_m=[hip_width_m * .04, 0., leg_length_m * .008],
             phase_offsets=({'left': 0., 'right': .5} if kind == 'biped' else
                            {'hind_left': 0., 'front_left': .25, 'hind_right': .5, 'front_right': .75}),
             joint_limits_rad={'hip': [-1.5, 1.5], 'knee': [0., 2.6], 'ankle': [-1.5, 1.5]},
             snake_wave=dict(amplitude_m=.1, wavelength_m=1., frequency_hz=1.))
    c["stance_duration_s"] = c["stance_fraction"] * cycle
    return validate(c)


def sample(c, t):
    """Absolute root motion plus periodic body and no-slip stance trajectories."""
    p = (t / c['cycle_s']) % 1.
    com = [a * math.sin(TAU * p * (2 if i == 2 else 1))
           for i, a in enumerate(c['com_displacement_m'])]
    rotation = [a * math.sin(TAU * p) for a in c['pelvis_rotation_rad']]
    feet = {}
    for name in limbs(c):
        u = (t / c['cycle_s'] + c['phase_offsets'][name]) % 1.
        duty = c['stance_fraction']
        if u < duty:
            y = c['stride_m'] * (duty / 2 - u)
            z = 0.
        else:
            q = (u - duty) / (1 - duty)
            # Endpoint velocity equals stance velocity; continuous velocity at contact.
            h = 3*q*q - 2*q*q*q
            y = -c['stride_m'] * duty / 2 - c['stride_m'] * (1-duty)*q + c['stride_m']*h
            z = c['foot_clearance_m'] * math.sin(math.pi * q)**2
        side = -1 if name.endswith('left') else 1
        base_y = (c['body']['body_length_m'] / 2 * (1 if name.startswith('front') else -1)
                  if c['type'] == 'quadruped' else 0.)
        feet[name] = dict(position=[side * c['body']['hip_width_m']/2,
                                    c['speed_mps']*t + base_y + y, z], stance=u < duty)
    return dict(time_s=t, root=[0., c['speed_mps']*t, 0.], com=com,
                pelvis_rotation_rad=rotation, feet=feet)


def solve_leg(hip, foot, upper, lower, bend_sign=1):
    """Sagittal two-link IK; returns knee point and hip/knee/ankle radians.

    Hip/ankle = forward-axis segment inclination; knee = flexion from straight.
    Reject unreachable targets instead of hiding stretch/clipping.
    """
    dx, dy, dz = [foot[i]-hip[i] for i in range(3)]
    d = math.sqrt(dx*dx + dy*dy + dz*dz)
    if not abs(upper-lower)+1e-8 < d < upper+lower-1e-8:
        raise ValueError('unreachable foot target; reduce stride/bob or correct rig proportions')
    a = (upper*upper-lower*lower+d*d)/(2*d)
    h = math.sqrt(max(0., upper*upper-a*a))
    unit = [dx/d, dy/d, dz/d]
    # Forward vector projected perpendicular to the hip-to-foot ray.
    pole = [-unit[1]*v for v in unit]
    pole[1] += 1
    norm = math.sqrt(sum(v*v for v in pole))
    if norm < 1e-8:
        raise ValueError("degenerate leg bend plane")
    knee = [hip[i]+a*unit[i]+bend_sign*h*pole[i]/norm for i in range(3)]
    hip_angle = math.atan2(knee[1]-hip[1], hip[2]-knee[2])
    lower_angle = math.atan2(foot[1]-knee[1], knee[2]-foot[2])
    flex = math.pi-math.acos(max(-1., min(1., (upper*upper+lower*lower-d*d)/(2*upper*lower))))
    return knee, dict(hip=hip_angle, knee=flex, ankle=-lower_angle)


def frame_count(c):
    return round(c['cycle_s'] * c['fps'])


def trajectory(c, subdivisions=8):
    validate(c)
    return [sample(c, i*c['cycle_s']/(frame_count(c)*subdivisions)) for i in range(frame_count(c)*subdivisions+1)]


def measure(c, samples, tolerance=.002):
    """Works on planner OR evaluated Blender sole-point samples, in world metres.

    Caller supplies a second cycle for boundary velocity coverage when desired.
    """
    slide = penetration = seam = velocity_seam = drift = 0.
    for name in limbs(c):
        anchor = None
        for row in samples:
            foot = row['feet'][name]
            if foot['stance']:
                if anchor is None: anchor = foot['position']
                drift = max(drift, math.dist(anchor, foot['position']))
            else:
                anchor = None
        for a,b in zip(samples, samples[1:]):
            fa, fb = a['feet'][name], b['feet'][name]
            penetration = max(penetration, -min(fa['position'][2], fb['position'][2]))
            if fa['stance'] and fb['stance']:
                slide = max(slide, math.dist(fa['position'], fb['position']))
        first, last = samples[0]['feet'][name]['position'], samples[-1]['feet'][name]['position']
        delta = [last[i]-first[i]-(c['stride_m'] if i == 1 else 0) for i in range(3)]
        seam = max(seam, math.dist(delta, [0,0,0]))
        # Compare boundary one-sided velocities (discrete integration tolerance below).
        dt = samples[1]['time_s']-samples[0]['time_s']
        start = [(samples[1]['feet'][name]['position'][i]-first[i])/dt for i in range(3)]
        end = [(last[i]-samples[-2]['feet'][name]['position'][i])/dt for i in range(3)]
        velocity_seam = max(velocity_seam, math.dist(start, end))
    return dict(max_contact_drift_m=drift, max_stance_slide_per_sample_m=slide, max_ground_penetration_m=penetration,
                loop_position_error_m=seam, loop_velocity_error_mps=velocity_seam,
                passed=drift <= tolerance and slide <= tolerance and penetration <= tolerance and seam <= tolerance
                and velocity_seam <= .25)
